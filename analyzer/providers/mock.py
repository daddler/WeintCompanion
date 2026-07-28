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

from analyzer.data import encounters
from analyzer.providers.base import RaidDataProvider
from analyzer.models import (
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_POSITIONING,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    Actor,
    ConsumableState,
    CooldownState,
    DeathEntry,
    MechanicIssue,
    MetricEntry,
    RaidSnapshot,
    TankEntry,
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

_DEATH_SCHEDULE: tuple[tuple[float, str, str], ...] = (

    (63.0, "Krallenwut", "Verheerender Schlag"),
    (129.0, "Bestienrufer", "Arkane Entladung"),

)


_MECHANIC_SCHEDULE: tuple[tuple[float, str, str, int, str, str], ...] = (

    (
        34.0, "Dolchtanz",
        "Im Flächenschaden stehen geblieben",
        2, "warning", MECHANIC_POSITIONING,
    ),
    (
        71.0, "Frostgrimm",
        "Unterbrechung verpasst",
        1, "error", MECHANIC_INTERRUPT,
    ),
    (
        108.0, "Windschritt",
        "Wirbel nicht ausgewichen",
        3, "warning", MECHANIC_MOVEMENT,
    ),
    (
        147.0, "Arkanis",
        "Defensivfähigkeit nicht genutzt",
        1, "info", MECHANIC_DEFENSIVE,
    ),
    (
        158.0, "Krallenwut",
        "Zu spät aus der Zone gelaufen",
        1, "warning", MECHANIC_MOVEMENT,
    ),

)


#
# Raid- und Heilcooldowns mit ihren Einsatzzeitpunkten.
#
# (Name, Spieler, Abklingzeit, Einsatzzeitpunkte)
#

_RAID_COOLDOWNS: tuple[tuple[str, str, float, tuple[float, ...]], ...] = (

    ("Rallying Cry", "Grimmzahn", 180.0, (44.0,)),
    ("Anti-Magic Zone", "Seuchenherz", 120.0, (58.0, 141.0)),
    ("Spirit Link Totem", "Kaldrun", 180.0, (77.0,)),
    ("Power Word: Barrier", "Miraia", 180.0, (112.0,)),
    ("Smoke Bomb", "Silbermond", 180.0, (134.0,)),
    ("Stampeding Roar", "Krallenwut", 120.0, (26.0,)),

)


_HEAL_COOLDOWNS: tuple[tuple[str, str, float, tuple[float, ...]], ...] = (

    ("Tranquility", "Elvenne", 180.0, (52.0,)),
    ("Divine Hymn", "Miraia", 180.0, (89.0,)),
    ("Healing Tide Totem", "Kaldrun", 180.0, (38.0, 158.0)),
    ("Revival", "Yunwei", 180.0, (121.0,)),
    ("Aura Mastery", "Torvald", 180.0, (103.0,)),

)


#
# --------------------------------------------------
# Provider
# --------------------------------------------------
#


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

        return RaidSnapshot(
            captured_at=snapshot.captured_at,
            source_label=snapshot.source_label,
            live=snapshot.live,
            in_combat=False,
            encounter=snapshot.encounter,
            pull_number=snapshot.pull_number,
            pull_seconds=snapshot.pull_seconds,
            boss_health_percent=snapshot.boss_health_percent,
            raid_size=snapshot.raid_size,
            deaths=snapshot.deaths,
            battle_res_charges=snapshot.battle_res_charges,
            battle_res_max=snapshot.battle_res_max,
            heroism_used=snapshot.heroism_used,
            heroism_remaining=0.0,
            top_damage=snapshot.top_damage,
            top_healing=snapshot.top_healing,
            tanks=snapshot.tanks,
            raid_cooldowns=snapshot.raid_cooldowns,
            heal_cooldowns=snapshot.heal_cooldowns,
            consumables=snapshot.consumables,
            mechanics=snapshot.mechanics,
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

        damage, healing = self._metrics(seconds, deaths)

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
            battle_res_charges=max(0, BATTLE_RES_MAX - len(deaths)),
            battle_res_max=BATTLE_RES_MAX,
            heroism_used=seconds >= HEROISM_AT,
            heroism_remaining=self._heroism_remaining(seconds),
            top_damage=damage,
            top_healing=healing,
            tanks=self._tanks(seconds),
            raid_cooldowns=self._cooldowns(_RAID_COOLDOWNS, seconds),
            heal_cooldowns=self._cooldowns(_HEAL_COOLDOWNS, seconds),
            consumables=self._consumables(seconds),
            mechanics=self._mechanics(seconds),
            warnings=self._warnings(seconds, deaths),
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
