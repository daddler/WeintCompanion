"""
Simulierte Raid-Daten.

Diese Quelle erzeugt einen vollständigen, sich bewegenden Pull, ohne
dass World of Warcraft laufen muss. Sie erfüllt zwei Zwecke:

1. WeintTV ist von Tag eins an bedienbar und begutachtbar - auch
   außerhalb der Raidzeiten und auf Rechnern ohne WoW-Installation.
2. Sie ist der Gegenbeweis dafür, dass die Oberfläche wirklich nur
   `RaidSnapshot` liest: läuft WeintTV gegen den Mock genauso wie
   gegen das echte Combat-Log, ist der Vertrag sauber.

Alle Werte werden deterministisch aus der verstrichenen Zeit
berechnet - kein Zufall. Derselbe Zeitpunkt liefert immer denselben
Snapshot, was die Simulation testbar macht und ein nervöses
Flackern der Oberfläche vermeidet.
"""

from __future__ import annotations

import math
import threading
import time

from dataclasses import replace

from analyzer.analysis import damage as damage_analysis
from analyzer.data import avoidable as avoidable_data
from analyzer.data import encounters
from analyzer.providers import mock_schedule as schedule
from analyzer.providers.base import RaidDataProvider
from analyzer.models import (
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    SUPPORT_DISPEL,
    SUPPORT_INTERRUPT,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    ActivityEntry,
    Actor,
    CombatEvent,
    ConsumableState,
    CooldownState,
    CooldownUsage,
    DeathEntry,
    HeroismWindow,
    MechanicIssue,
    MetricEntry,
    MovementEntry,
    RaidSnapshot,
    ResurrectionEvent,
    SupportEvent,
    TankEntry,
    UptimeEntry,
)


#
# --------------------------------------------------
# Zeitplan eines simulierten Zyklus
# --------------------------------------------------
#
# Vorbereitung -> Pull -> Auswertung, danach beginnt der nächste
# Pull mit erhöhter Pull-Nummer.
#

PREPARE_SECONDS = 12.0

PULL_SECONDS = 180.0

AFTER_SECONDS = 18.0

CYCLE_SECONDS = PREPARE_SECONDS + PULL_SECONDS + AFTER_SECONDS


#
# Zeitpunkte innerhalb des Pulls
#

HEROISM_AT = 96.0

HEROISM_DURATION = 40.0

RAID_SIZE = 25

BATTLE_RES_MAX = 3


#
# --------------------------------------------------
# Roster
# --------------------------------------------------
#
# (Name, Klasse, Spezialisierung, Rolle, Grundwert pro Sekunde)
#
# Der Grundwert ist die Kennzahl, um die der Spieler pendelt - bei
# Tanks und DPS die Schadensleistung, bei Heilern die Heilleistung.
#

_ROSTER: tuple[tuple[str, str, str, str, float], ...] = (

    #
    # Tanks
    #

    ("Bramborn", "Warrior", "Schutz", ROLE_TANK, 41000.0),
    ("Sigmara", "Monk", "Braumeister", ROLE_TANK, 38500.0),

    #
    # Heiler
    #

    ("Elvenne", "Druid", "Wiederherstellung", ROLE_HEALER, 74000.0),
    ("Torvald", "Paladin", "Heilig", ROLE_HEALER, 69500.0),
    ("Miraia", "Priest", "Disziplin", ROLE_HEALER, 66000.0),
    ("Kaldrun", "Shaman", "Wiederherstellung", ROLE_HEALER, 71500.0),
    ("Yunwei", "Monk", "Nebelwirker", ROLE_HEALER, 63500.0),

    #
    # Schadensausteiler
    #

    ("Nachtblatt", "Druid", "Gleichgewicht", ROLE_DPS, 128000.0),
    ("Pyrothal", "Mage", "Feuer", ROLE_DPS, 134500.0),
    ("Grimmzahn", "Warrior", "Waffen", ROLE_DPS, 121000.0),
    ("Silbermond", "Rogue", "Meucheln", ROLE_DPS, 126500.0),
    ("Falkenauge", "Hunter", "Treffsicherheit", ROLE_DPS, 119500.0),
    ("Verdammnis", "Warlock", "Gebrechen", ROLE_DPS, 131000.0),
    ("Schattenruf", "Priest", "Schatten", ROLE_DPS, 117500.0),
    ("Sturmklinge", "Shaman", "Elementar", ROLE_DPS, 114000.0),
    ("Lichthammer", "Paladin", "Vergeltung", ROLE_DPS, 112500.0),
    ("Seuchenherz", "Death Knight", "Unheilig", ROLE_DPS, 123500.0),
    ("Windschritt", "Monk", "Windwandler", ROLE_DPS, 116000.0),
    ("Krallenwut", "Druid", "Wilder Kampf", ROLE_DPS, 109500.0),
    ("Arkanis", "Mage", "Arkan", ROLE_DPS, 122000.0),
    ("Dolchtanz", "Rogue", "Kampf", ROLE_DPS, 113500.0),
    ("Feuerbrand", "Warlock", "Zerstörung", ROLE_DPS, 118000.0),
    ("Frostgrimm", "Death Knight", "Frost", ROLE_DPS, 110500.0),
    ("Bestienrufer", "Hunter", "Tierherrschaft", ROLE_DPS, 107500.0),
    ("Donnerfaust", "Shaman", "Verstärkung", ROLE_DPS, 115500.0),

)


def _build_actors() -> tuple[tuple[Actor, float], ...]:

    return tuple(
        (
            Actor(
                name=name,
                class_name=class_name,
                spec=spec,
                role=role,
            ),
            base,
        )
        for name, class_name, spec, role, base in _ROSTER
    )


_ACTORS = _build_actors()


#
# --------------------------------------------------
# Feste Ereignisse innerhalb eines Pulls
# --------------------------------------------------
#
# Die Fahrpläne stehen in mock_schedule.py: mit der Tiefenauswertung
# sind daraus über dreihundert Zeilen Festdaten geworden, in denen die
# eigentliche Logik dieses Anbieters untergegangen wäre. Die Aliase
# hier halten die bisherigen Namen am Leben, damit der Rest der Datei
# unverändert lesbar bleibt.
#

_DEATH_SCHEDULE = schedule.DEATH_SCHEDULE

_MECHANIC_SCHEDULE = schedule.MECHANIC_SCHEDULE

_RAID_COOLDOWNS = schedule.RAID_COOLDOWNS

_HEAL_COOLDOWNS = schedule.HEAL_COOLDOWNS


#
# --------------------------------------------------
# Provider
# --------------------------------------------------
#


def _rate_of(rows: tuple[MetricEntry, ...], name: str) -> float:
    """
    Der Wert pro Sekunde eines Spielers aus einer Rangliste - 0.0,
    wenn er nicht darin vorkommt (Heiler stehen nicht im
    Schadensranking).
    """

    for entry in rows:

        if entry.actor.name == name:
            return entry.value

    return 0.0


class MockRaidDataProvider(RaidDataProvider):
    """
    Deterministische Simulation eines 25er-Raids.
    """

    ENCOUNTER_NAME = "Horridon"

    ENCOUNTER_ID = 0

    def __init__(self, encounter_name: str = ""):

        self._lock = threading.Lock()

        self._started_at: float | None = None

        self._encounter_name = encounter_name or self.ENCOUNTER_NAME

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def start(self) -> None:

        with self._lock:

            if self._started_at is None:

                self._started_at = time.monotonic()

    def stop(self) -> None:

        with self._lock:

            self._started_at = None

    # --------------------------------------------------
    # Beschreibung
    # --------------------------------------------------

    @property
    def source_label(self) -> str:

        return "Simulation"

    @property
    def live(self) -> bool:

        return False

    @property
    def status_text(self) -> str:

        return (
            "Simulierte Daten - echte Werte liefert das Combat-Log, "
            "sobald die Live-Auswertung aktiv ist."
        )

    # --------------------------------------------------
    # Snapshot
    # --------------------------------------------------

    def snapshot(self) -> RaidSnapshot:

        with self._lock:

            started_at = self._started_at

        if started_at is None:

            return RaidSnapshot.empty(self.source_label)

        elapsed = time.monotonic() - started_at

        #
        # Position innerhalb des Zyklus + laufende Pull-Nummer
        #

        cycle_index = int(elapsed // CYCLE_SECONDS)

        position = elapsed % CYCLE_SECONDS

        pull_number = cycle_index + 1

        if position < PREPARE_SECONDS:

            return self._prepare_snapshot(pull_number)

        if position < PREPARE_SECONDS + PULL_SECONDS:

            return self._combat_snapshot(
                pull_number,
                position - PREPARE_SECONDS,
            )

        return self._after_snapshot(pull_number)

    # --------------------------------------------------
    # Wiedergabe
    # --------------------------------------------------

    def timeline(self, pull_number: int = 1):
        """
        Der ganze simulierte Pull als Zeitleiste.

        Ohne das wäre die Wiedergabe erst vorführbar, wenn der Bot den
        Zeitleisten-Endpunkt liefert - und damit wäre die
        aufwendigste Neuerung von WeintTV monatelang unbegutachtbar.

        Die Reihen entstehen, indem dieselben Funktionen abgetastet
        werden, die auch den Live-Snapshot bauen. Dadurch stimmt die
        Wiedergabe mit dem Live-Bild an jedem Zeitpunkt überein -
        anders als bei einer zweiten, eigens gebauten Datenreihe, die
        langsam auseinanderliefe.
        """

        from analyzer.analysis.movement import COORD_UNITS_PER_METER
        from analyzer.replay.models import (
            AvoidableHit,
            FightTimeline,
            PlayerSeries,
        )

        interval = 1.0

        steps = int(PULL_SECONDS / interval) + 1

        stamps = [index * interval for index in range(steps)]

        #
        # Die Snapshots einmal je Takt bauen und danach auslesen. Ein
        # Aufruf je Spieler und Takt wäre fünfundzwanzigmal so teuer,
        # ohne ein anderes Ergebnis zu liefern.
        #

        frames = [
            self._combat_snapshot(pull_number, at)
            for at in stamps
        ]

        players = []

        for actor, _base in _ACTORS:

            damage = []
            healing = []
            taken = []
            units = []
            active = []
            casts = []

            #
            # Schaden und Heilung werden aus der Kurve *aufsummiert*
            # statt aus `MetricEntry.total` übernommen.
            #
            # Grund: der Live-Snapshot rechnet total = Wert pro
            # Sekunde × Kampfzeit, und der Wert pro Sekunde schwankt
            # bewusst leicht (damit sich die Rangfolge bewegt). Diese
            # Multiplikation ergibt deshalb keine monoton wachsende
            # Summe - beim Vorspulen könnte der Schaden eines
            # Spielers sinken. Die aufsummierte Kurve ist das echte
            # Integral und kann das nicht.
            #

            damage_sum = 0.0

            healing_sum = 0.0

            for at, frame in zip(stamps, frames):

                damage_sum += _rate_of(frame.top_damage, actor.name) * interval

                healing_sum += _rate_of(frame.top_healing, actor.name) * interval

                damage.append(damage_sum)

                healing.append(healing_sum)

                entry = frame.damage_taken_of(actor.name)

                taken.append(entry.total if entry else 0.0)

                movement = frame.movement_of(actor.name)

                units.append(
                    movement.meters * COORD_UNITS_PER_METER
                    if movement
                    else 0.0
                )

                activity = frame.activity_of(actor.name)

                active.append(
                    activity.active_percent / 100.0 * at
                    if activity
                    else 0.0
                )

                casts.append(float(activity.casts) if activity else 0.0)

            players.append(
                PlayerSeries(
                    actor=actor,
                    damage=tuple(damage),
                    healing=tuple(healing),
                    damage_taken=tuple(taken),
                    movement_units=tuple(units),
                    active_seconds=tuple(active),
                    casts=tuple(casts),
                )
            )

        final = frames[-1]

        #
        # Vermeidbare Treffer einzeln mit Zeitpunkt - nur so kann die
        # Academy aus einem Befund an genau diese Sekunde springen.
        #

        hits = []

        for name, ability, times, per_hit in schedule.DAMAGE_TAKEN:

            rule = avoidable_data.classify(self._encounter_name, ability)

            if rule is None or rule.verdict != avoidable_data.VERDICT_AVOIDABLE:
                continue

            for at in times:

                hits.append(
                    AvoidableHit(
                        actor_name=name,
                        ability=ability,
                        at_seconds=at,
                        amount=per_hit,
                        note=rule.note,
                    )
                )

        hits.sort(key=lambda hit: hit.at_seconds)

        return FightTimeline(
            encounter=self._encounter(),
            source_label=f"Wiedergabe · {self._encounter_name}",
            pull_number=pull_number,
            duration=PULL_SECONDS,
            interval=interval,
            raid_size=RAID_SIZE,
            battle_res_max=BATTLE_RES_MAX,
            boss_health=tuple(
                frame.boss_health_percent
                for frame in frames
            ),
            players=tuple(players),
            deaths=final.deaths,
            resurrections=final.resurrections,
            heroism_windows=final.heroism_windows,
            cooldown_usage=final.cooldown_usage,
            avoidable_hits=tuple(hits),
            interrupts=final.interrupts,
            dispels=final.dispels,
            mechanics=final.mechanics,
            events=final.events,
            damage_taken_totals=final.damage_taken,
            dot_uptimes=final.dot_uptimes,
            hot_uptimes=final.hot_uptimes,
            buff_uptimes=final.buff_uptimes,
            aggregate=self._after_snapshot(pull_number),
        )

    # --------------------------------------------------
    # Phasen
    # --------------------------------------------------

    def _encounter(self):

        return encounters.lookup(
            encounter_id=self.ENCOUNTER_ID,
            name=self._encounter_name,
            difficulty_id=6,
            raid_size=RAID_SIZE,
        )

    def _prepare_snapshot(self, pull_number: int) -> RaidSnapshot:
        """
        Zwischen den Pulls: Raid steht, Buffs werden kontrolliert.
        """

        return RaidSnapshot(
            source_label=self.source_label,
            live=False,
            in_combat=False,
            encounter=self._encounter(),
            pull_number=pull_number,
            pull_seconds=0.0,
            boss_health_percent=100.0,
            raid_size=RAID_SIZE,
            battle_res_charges=BATTLE_RES_MAX,
            battle_res_max=BATTLE_RES_MAX,
            tanks=self._tanks(0.0),
            raid_cooldowns=self._cooldowns(_RAID_COOLDOWNS, 0.0),
            heal_cooldowns=self._cooldowns(_HEAL_COOLDOWNS, 0.0),
            consumables=self._consumables(0.0),
            warnings=(
                "Raid bereitet sich vor - Buffs und Flasks prüfen.",
            ),
        )

    def _after_snapshot(self, pull_number: int) -> RaidSnapshot:
        """
        Direkt nach dem Pull: Werte bleiben stehen, damit die
        Raidleitung sie noch lesen kann.
        """

        snapshot = self._combat_snapshot(pull_number, PULL_SECONDS)

        #
        # `replace()` statt einer Feld-für-Feld-Kopie: die frühere
        # Fassung listete jedes Feld einzeln auf, sodass ein neu zum
        # Snapshot hinzugekommenes Feld hier stillschweigend
        # verschwand - die gesamte Tiefenauswertung wäre nach dem
        # Pull einfach leer gewesen, ohne dass irgendetwas
        # fehlschlägt.
        #

        return replace(
            snapshot,
            in_combat=False,
            heroism_remaining=0.0,
            warnings=(
                "Pull beendet - Auswertung steht bis zum nächsten Pull.",
            ),
        )

    def _combat_snapshot(
        self,
        pull_number: int,
        seconds: float,
    ) -> RaidSnapshot:

        deaths = self._deaths(seconds)

        resurrections = self._resurrections(seconds)

        damage, healing = self._metrics(seconds, deaths)

        windows = self._heroism_windows(seconds)

        damage_taken = self._damage_taken(seconds)

        #
        # Dieselbe Verdrahtung wie beim echten Anbieter: die vom
        # "Bot" gelieferten Mechanikfehler und die aus vermeidbaren
        # Treffern abgeleiteten werden zusammengeführt, wobei der Bot
        # gewinnt. Dadurch läuft in der Simulation auch die Regel
        # gegen Doppelzählung tatsächlich durch.
        #

        mechanics = damage_analysis.merge_mechanics(
            damage_analysis.bot_mechanics(self._mechanics(seconds)),
            damage_analysis.derive_mechanics(damage_taken, self._encounter_name),
        )

        return RaidSnapshot(
            source_label=self.source_label,
            live=False,
            in_combat=True,
            encounter=self._encounter(),
            pull_number=pull_number,
            pull_seconds=seconds,
            boss_health_percent=self._boss_health(seconds),
            raid_size=RAID_SIZE,
            deaths=deaths,
            battle_res_charges=max(
                0,
                BATTLE_RES_MAX - len(resurrections),
            ),
            battle_res_max=BATTLE_RES_MAX,
            heroism_used=seconds >= HEROISM_AT,
            heroism_remaining=self._heroism_remaining(seconds),
            top_damage=damage,
            top_healing=healing,
            tanks=self._tanks(seconds),
            raid_cooldowns=self._cooldowns(_RAID_COOLDOWNS, seconds),
            heal_cooldowns=self._cooldowns(_HEAL_COOLDOWNS, seconds),
            consumables=self._consumables(seconds),
            mechanics=mechanics,
            warnings=self._warnings(seconds, deaths),
            activity=self._activity(seconds),
            dot_uptimes=self._uptimes(seconds, UPTIME_DOT),
            hot_uptimes=self._uptimes(seconds, UPTIME_HOT),
            buff_uptimes=self._uptimes(seconds, UPTIME_BUFF),
            movement=self._movement(seconds, damage_taken),
            damage_taken=damage_taken,
            cooldown_usage=self._cooldown_usage(seconds, windows),
            heroism_windows=windows,
            resurrections=resurrections,
            interrupts=self._support(
                schedule.INTERRUPTS,
                SUPPORT_INTERRUPT,
                seconds,
            ),
            dispels=self._support(
                schedule.DISPELS,
                SUPPORT_DISPEL,
                seconds,
            ),
            events=self._events(seconds),
        )

    # --------------------------------------------------
    # Einzelwerte
    # --------------------------------------------------

    def _boss_health(self, seconds: float) -> float:
        """
        Fällt über den Pull von 100 % auf knapp über 0 %, mit einer
        leichten Delle - so wirkt die Kurve wie ein echter Kampf und
        nicht wie eine Gerade.
        """

        progress = max(0.0, min(1.0, seconds / PULL_SECONDS))

        wobble = 0.03 * math.sin(progress * math.pi * 3.0)

        percent = (1.0 - progress + wobble) * 100.0

        return max(0.6, min(100.0, percent))

    def _heroism_remaining(self, seconds: float) -> float:

        if seconds < HEROISM_AT:
            return 0.0

        remaining = HEROISM_DURATION - (seconds - HEROISM_AT)

        return max(0.0, remaining)

    def _ramp(self, seconds: float) -> float:
        """
        In den ersten Sekunden eines Pulls sind Werte pro Sekunde
        naturgemäß unruhig. Der Anlauf glättet das, statt absurde
        Spitzenwerte bei Sekunde 1 zu zeigen.
        """

        return max(0.3, min(1.0, 0.4 + seconds / 30.0))

    def _factor(self, index: int, seconds: float) -> float:
        """
        Deterministische Schwankung um den Grundwert. Jeder Spieler
        bekommt eine eigene Phase, damit sich die Reihenfolge im
        Ranking im Laufe des Pulls tatsächlich verschiebt.
        """

        phase = index * 0.7

        slow = math.sin(seconds / 17.0 + phase) * 0.09

        fast = math.sin(seconds / 5.5 + phase * 2.0) * 0.04

        return 1.0 + slow + fast

    def _is_dead(self, name: str, deaths: tuple[DeathEntry, ...]) -> bool:

        return any(entry.actor_name == name for entry in deaths)

    # --------------------------------------------------

    def _metrics(
        self,
        seconds: float,
        deaths: tuple[DeathEntry, ...],
    ) -> tuple[tuple[MetricEntry, ...], tuple[MetricEntry, ...]]:
        """
        Baut Schadens- und Heilranking in einem Durchgang, damit die
        Anteile (`share`) zur selben Gesamtsumme passen.
        """

        ramp = self._ramp(seconds)

        heroism_bonus = (
            1.28
            if self._heroism_remaining(seconds) > 0.0
            else 1.0
        )

        damage_rows: list[tuple[Actor, float]] = []

        healing_rows: list[tuple[Actor, float]] = []

        for index, (actor, base) in enumerate(_ACTORS):

            #
            # Heldentum hebt Schaden und Heilung gleichermaßen an.
            #

            value = (
                base
                * self._factor(index, seconds)
                * ramp
                * heroism_bonus
            )

            #
            # Tote tragen ab ihrem Tod nichts mehr bei - ihr
            # Durchschnitt sinkt dadurch sichtbar.
            #

            if self._is_dead(actor.name, deaths):

                value *= 0.45

            if actor.is_healer:

                healing_rows.append((actor, value))

            else:

                damage_rows.append((actor, value))

        return (
            self._to_entries(damage_rows, seconds),
            self._to_entries(healing_rows, seconds),
        )

    def _to_entries(
        self,
        rows: list[tuple[Actor, float]],
        seconds: float,
    ) -> tuple[MetricEntry, ...]:

        total_value = sum(value for _actor, value in rows)

        rows = sorted(rows, key=lambda row: row[1], reverse=True)

        entries = []

        for actor, value in rows:

            entries.append(
                MetricEntry(
                    actor=actor,
                    value=value,
                    total=value * max(1.0, seconds),
                    share=(
                        value / total_value
                        if total_value > 0
                        else 0.0
                    ),
                )
            )

        return tuple(entries)

    # --------------------------------------------------

    def _tanks(self, seconds: float) -> tuple[TankEntry, ...]:

        entries = []

        for index, (actor, base) in enumerate(_ACTORS):

            if not actor.is_tank:
                continue

            #
            # Tank-Leben pendelt zwischen ca. 45 % und 100 % - der
            # typische Rhythmus aus Bossschlag und Gegenheilung.
            #

            swing = math.sin(seconds / 4.0 + index * 1.6)

            health = 72.0 + swing * 27.0

            entries.append(
                TankEntry(
                    actor=actor,
                    health_percent=max(12.0, min(100.0, health)),
                    damage_taken=base * max(1.0, seconds) * 0.9,
                    active_mitigation=swing > -0.2,
                )
            )

        return tuple(entries)

    # --------------------------------------------------

    def _deaths(self, seconds: float) -> tuple[DeathEntry, ...]:

        return tuple(
            DeathEntry(
                actor_name=name,
                at_seconds=at,
                cause=cause,
            )
            for at, name, cause in _DEATH_SCHEDULE
            if seconds >= at
        )

    # --------------------------------------------------

    def _mechanics(self, seconds: float) -> tuple[MechanicIssue, ...]:

        return tuple(
            MechanicIssue(
                actor_name=name,
                mechanic=mechanic,
                count=count,
                severity=severity,
                category=category,
                at_seconds=at,
            )
            for at, name, mechanic, count, severity, category
            in _MECHANIC_SCHEDULE
            if seconds >= at
        )

    # --------------------------------------------------

    def _cooldowns(
        self,
        table: tuple[tuple[str, str, float, tuple[float, ...]], ...],
        seconds: float,
    ) -> tuple[CooldownState, ...]:

        states = []

        for name, actor_name, duration, casts in table:

            used_at = [at for at in casts if at <= seconds]

            if not used_at:

                states.append(
                    CooldownState(
                        name=name,
                        actor_name=actor_name,
                        ready=True,
                        remaining=0.0,
                        duration=duration,
                    )
                )

                continue

            since = seconds - used_at[-1]

            remaining = duration - since

            states.append(
                CooldownState(
                    name=name,
                    actor_name=actor_name,
                    ready=remaining <= 0.0,
                    remaining=max(0.0, remaining),
                    duration=duration,
                )
            )

        return tuple(states)

    # --------------------------------------------------

    def _consumables(self, seconds: float) -> tuple[ConsumableState, ...]:

        #
        # Flask und Bufffood stehen vor dem Pull fest; Kampftränke
        # werden im Verlauf getrunken.
        #

        potion_users = min(
            RAID_SIZE,
            int(RAID_SIZE * max(0.0, min(1.0, seconds / 90.0))),
        )

        return (

            ConsumableState(
                label="Flask",
                used=24,
                total=RAID_SIZE,
                missing=("Bestienrufer",),
            ),

            ConsumableState(
                label="Bufffood",
                used=23,
                total=RAID_SIZE,
                missing=("Bestienrufer", "Dolchtanz"),
            ),

            ConsumableState(
                label="Kampftrank",
                used=potion_users,
                total=RAID_SIZE,
                missing=(),
            ),

        )

    # --------------------------------------------------
    # Tiefenauswertung
    # --------------------------------------------------
    #
    # Alles ab hier wächst mit der Pull-Sekunde: nach zehn Sekunden
    # ist ein Zehntel des Laufwegs gelaufen und noch kaum ein
    # Cooldown gewirkt. Ohne dieses Mitwachsen sähe die Wiedergabe
    # eines Pulls von der ersten Sekunde an fertig aus.
    #

    def _progress(self, seconds: float) -> float:
        """
        Anteil des Pulls, der vorbei ist (0.0 - 1.0).
        """

        return max(0.0, min(1.0, seconds / PULL_SECONDS))

    # --------------------------------------------------

    def _activity(self, seconds: float) -> tuple[ActivityEntry, ...]:

        if seconds <= 0:
            return ()

        entries = []

        for actor, _base in _ACTORS:

            _meters, active = schedule.movement_for(actor.name)

            if active <= 0:
                continue

            apm = schedule.APM_BY_ROLE.get(actor.role, 40.0)

            #
            # Ein Toter drückt keine Knöpfe mehr: seine Aktivzeit
            # verwässert mit jeder weiteren Sekunde des Kampfes.
            #

            death_at = self._death_time(actor.name, seconds)

            if death_at is not None and seconds > death_at:

                factor = death_at / seconds

                active *= factor

                apm *= factor

            entries.append(
                ActivityEntry(
                    actor_name=actor.name,
                    active_percent=active,
                    casts=int(apm * seconds / 60.0),
                    apm=apm,
                    longest_gap=max(
                        0.0,
                        (100.0 - active) / 100.0 * 12.0,
                    ),
                )
            )

        entries.sort(key=lambda entry: entry.active_percent, reverse=True)

        return tuple(entries)

    # --------------------------------------------------

    def _uptimes(self, seconds: float, kind: str) -> tuple[UptimeEntry, ...]:

        if seconds <= 0:
            return ()

        #
        # Am Anfang eines Pulls ist jede Uptime unruhig (der erste
        # Zauber muss erst laufen). Nach einer Aufbauphase pendelt sie
        # sich auf den Zielwert ein - so wirkt die Kurve wie ein
        # echter Kampf und die Bewertung wird nicht von den ersten
        # Sekunden verzerrt.
        #

        ramp = max(0.0, min(1.0, seconds / 20.0))

        entries = []

        for actor, _base in _ACTORS:

            for ability, reached, expected in schedule.uptimes_for(
                actor.name,
                kind,
            ):

                entries.append(
                    UptimeEntry(
                        actor_name=actor.name,
                        ability=ability,
                        uptime_percent=reached * ramp,
                        kind=kind,
                        applications=max(
                            1,
                            int(seconds / 18.0) + 1,
                        ),
                        target=(
                            self._encounter_name
                            if kind == UPTIME_DOT
                            else ""
                        ),
                        expected_percent=expected,
                    )
                )

        entries.sort(key=lambda entry: entry.uptime_percent, reverse=True)

        return tuple(entries)

    # --------------------------------------------------

    def _movement(
        self,
        seconds: float,
        damage_taken: tuple,
    ) -> tuple[MovementEntry, ...]:

        if seconds <= 0:
            return ()

        progress = self._progress(seconds)

        hits_by_name = {
            entry.actor_name: entry.avoidable_hits
            for entry in damage_taken
        }

        entries = []

        for actor, _base in _ACTORS:

            meters, _active = schedule.movement_for(actor.name)

            if meters <= 0:
                continue

            #
            # Ein Toter läuft nicht weiter - sein Laufweg friert zum
            # Todeszeitpunkt ein.
            #

            death_at = self._death_time(actor.name, seconds)

            share = (
                self._progress(death_at)
                if death_at is not None
                else progress
            )

            walked = meters * share

            entries.append(
                MovementEntry(
                    actor_name=actor.name,
                    meters=walked,
                    meters_per_second=(
                        walked / seconds
                        if seconds > 0
                        else 0.0
                    ),
                    avoidable_hits=hits_by_name.get(actor.name, 0),
                    estimated=True,
                )
            )

        entries.sort(key=lambda entry: entry.meters, reverse=True)

        return tuple(entries)

    # --------------------------------------------------

    def _damage_taken(self, seconds: float) -> tuple:

        if seconds <= 0:
            return ()

        entries = []

        for actor, _base in _ACTORS:

            rows = []

            for ability, times, per_hit in schedule.damage_taken_for(
                actor.name
            ):

                hits = sum(1 for at in times if at <= seconds)

                if hits <= 0:
                    continue

                rows.append(
                    (ability, per_hit * hits, hits, self._encounter_name)
                )

            if not rows:
                continue

            entries.append(
                damage_analysis.build_damage_taken(
                    actor_name=actor.name,
                    encounter_name=self._encounter_name,
                    rows=tuple(rows),
                    role=actor.role,
                )
            )

        entries.sort(key=lambda entry: entry.total, reverse=True)

        return tuple(entries)

    # --------------------------------------------------

    def _cooldown_usage(
        self,
        seconds: float,
        windows: tuple[HeroismWindow, ...],
    ) -> tuple[CooldownUsage, ...]:

        if seconds <= 0:
            return ()

        entries = []

        for actor, _base in _ACTORS:

            for ability, cooldown, category, casts in schedule.cooldowns_for(
                actor.name
            ):

                used = tuple(at for at in casts if at <= seconds)

                entries.append(
                    CooldownUsage(
                        actor_name=actor.name,
                        ability=ability,
                        cast_times=used,
                        cooldown=cooldown,
                        possible=(
                            int(seconds // cooldown) + 1
                            if cooldown > 0
                            else 0
                        ),
                        in_burst=sum(
                            1
                            for at in used
                            if any(
                                window.contains(at)
                                for window in windows
                            )
                        ),
                        category=category,
                    )
                )

        return tuple(entries)

    # --------------------------------------------------

    def _heroism_windows(self, seconds: float) -> tuple[HeroismWindow, ...]:
        """
        Nur bereits begonnene Fenster - ein Fenster, das erst in
        dreißig Sekunden anfängt, hat im Snapshot dieses Zeitpunkts
        nichts verloren.
        """

        return tuple(
            HeroismWindow(
                start=start,
                end=end,
                source=source,
                label=label,
            )
            for start, end, source, label in schedule.HEROISM_WINDOWS
            if seconds >= start
        )

    # --------------------------------------------------

    def _resurrections(self, seconds: float) -> tuple[ResurrectionEvent, ...]:

        return tuple(
            ResurrectionEvent(
                target=target,
                caster=caster,
                at_seconds=at,
                ability=ability,
            )
            for at, target, caster, ability in schedule.RESURRECT_SCHEDULE
            if seconds >= at
        )

    # --------------------------------------------------

    def _support(
        self,
        table: tuple[tuple[str, float, str, str], ...],
        kind: str,
        seconds: float,
    ) -> tuple[SupportEvent, ...]:

        return tuple(
            SupportEvent(
                actor_name=name,
                kind=kind,
                at_seconds=at,
                target=target,
                ability=ability,
            )
            for name, at, target, ability in table
            if seconds >= at
        )

    def _events(self, seconds: float) -> tuple[CombatEvent, ...]:
        """
        Die Ereignisse bis zur laufenden Sekunde - dieselbe Regel wie
        bei Toden und Unterbrechungen.
        """

        return tuple(
            CombatEvent(
                at_seconds=at,
                kind=kind,
                actor_name=actor,
                target=target,
                ability=ability,
                detail=detail,
                severity=severity,
            )
            for at, kind, actor, target, ability, detail, severity
            in schedule.EVENT_SCHEDULE
            if seconds >= at
        )

    # --------------------------------------------------

    def _death_time(self, name: str, seconds: float) -> float | None:
        """
        Wann der Spieler gestorben ist, sofern er zum Zeitpunkt
        `seconds` tot ist und nicht wiederbelebt wurde.
        """

        died_at = None

        for at, dead_name, _cause in _DEATH_SCHEDULE:

            if dead_name == name and seconds >= at:
                died_at = at

        if died_at is None:
            return None

        for at, target, _caster, _ability in schedule.RESURRECT_SCHEDULE:

            if target == name and at <= seconds and at >= died_at:
                return None

        return died_at

    # --------------------------------------------------

    def _warnings(
        self,
        seconds: float,
        deaths: tuple[DeathEntry, ...],
    ) -> tuple[str, ...]:

        warnings: list[str] = []

        if self._heroism_remaining(seconds) > 0.0:

            warnings.append(
                "Heldentum läuft - Cooldowns jetzt einsetzen."
            )

        elif seconds < HEROISM_AT:

            warnings.append(
                f"Heldentum geplant bei {int(HEROISM_AT)}s."
            )

        if deaths:

            warnings.append(
                f"{len(deaths)} Ausfälle - Kampfwiederbelebung prüfen."
            )

        if self._boss_health(seconds) < 25.0:

            warnings.append(
                "Boss unter 25 % - Endphase, Verteidigungen bereithalten."
            )

        return tuple(warnings)
