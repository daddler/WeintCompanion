"""
Datenmodelle des Raidlog Analyzers.

Alles hier ist eingefroren (`frozen=True`) und benutzt Tupel statt
Listen. Grund: ein `RaidSnapshot` wird aus einem Hintergrund-Thread
erzeugt und im Qt-Hauptthread gelesen. Ist er unveränderlich, kann
ihn kein Widget versehentlich verändern, während der nächste bereits
gebaut wird - es braucht dafür keinerlei Sperren.

Diese Modelle sind der einzige Vertrag zwischen Analyzer und
Oberfläche. Sowohl WeintTV als auch die WeintAcademy lesen
ausschließlich diese Strukturen; damit gibt es keine Möglichkeit,
Auswertungslogik doppelt zu implementieren.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


#
# --------------------------------------------------
# Rollen
# --------------------------------------------------
#

ROLE_TANK = "tank"
ROLE_HEALER = "healer"
ROLE_DPS = "dps"


#
# --------------------------------------------------
# Kategorien von Mechanikfehlern
# --------------------------------------------------
#
# Die Kategorie ist der Grund, warum die WeintAcademy aus einem
# Kampf überhaupt eine Bewertung ableiten kann: sie ordnet jeden
# Fehler einem trainierbaren Bereich zu. Ohne sie müsste die
# Academy Fehlertexte nach Stichworten durchsuchen - fehleranfällig
# und in zwei Sprachen doppelt gepflegt.
#

MECHANIC_MOVEMENT = "movement"
MECHANIC_POSITIONING = "positioning"
MECHANIC_INTERRUPT = "interrupt"
MECHANIC_DEFENSIVE = "defensive"
MECHANIC_OTHER = "other"


#
# --------------------------------------------------
# Arten von Wirkungsdauern
# --------------------------------------------------
#
# DoTs liegen auf Gegnern, HoTs und Buffs auf Verbündeten. Die
# Unterscheidung steckt im Eintrag und nicht in getrennten Listen,
# damit eine Auswertung ("mittlere Uptime meiner Kernfähigkeiten")
# über eine einzige Schleife laufen kann.
#

UPTIME_DOT = "dot"
UPTIME_HOT = "hot"
UPTIME_BUFF = "buff"


#
# --------------------------------------------------
# Arten von Cooldowns
# --------------------------------------------------
#
# Getrennt von den MECHANIC_*-Kategorien: dort geht es um Fehler,
# hier um die Einordnung einer Fähigkeit. Ein nicht genutzter
# Defensiv-Cooldown ist beides - eine CooldownUsage mit
# CD_DEFENSIVE und (abgeleitet) ein MechanicIssue mit
# MECHANIC_DEFENSIVE.
#

CD_RAID = "raid"
CD_HEAL = "heal"
CD_PERSONAL = "personal"
CD_DEFENSIVE = "defensive"


#
# --------------------------------------------------
# Arten von Unterstützungsereignissen
# --------------------------------------------------
#

SUPPORT_INTERRUPT = "interrupt"
SUPPORT_DISPEL = "dispel"


#
# --------------------------------------------------
# Herkunft eines Mechanikfehlers
# --------------------------------------------------
#
# Der Bot darf eigene, handverlesene Regeln mitschicken; zusätzlich
# leitet der Analyzer Fehler aus dem erhaltenen Schaden ab. Beim
# Zusammenführen gewinnt der Bot - siehe analyzer.analysis.damage.
#

MECHANIC_SOURCE_BOT = "bot"
MECHANIC_SOURCE_LOCAL = "local"


#
# --------------------------------------------------
# Teilnehmer
# --------------------------------------------------
#


@dataclass(frozen=True)
class Actor:
    """
    Ein Raidmitglied. `class_name` ist bewusst der englische
    Klassenname ("Druid", "Monk", ...), weil das die Schreibweise
    ist, die im Combat-Log und in der Klassenfarben-Tabelle
    (gui/theme/wow_colors.py) vorkommt.
    """

    name: str

    class_name: str

    spec: str = ""

    role: str = ROLE_DPS

    @property
    def is_tank(self) -> bool:

        return self.role == ROLE_TANK

    @property
    def is_healer(self) -> bool:

        return self.role == ROLE_HEALER


#
# --------------------------------------------------
# Kennzahlen
# --------------------------------------------------
#


@dataclass(frozen=True)
class MetricEntry:
    """
    Ein Ranking-Eintrag (Top DPS bzw. Top HPS).

    `value` ist der Wert pro Sekunde, `total` die Gesamtsumme,
    `share` der Anteil am Raid-Gesamtwert (0.0 - 1.0).
    """

    actor: Actor

    value: float

    total: float = 0.0

    share: float = 0.0

    @property
    def name(self) -> str:

        return self.actor.name


@dataclass(frozen=True)
class TankEntry:
    """
    Eine Zeile der Tank-Übersicht.
    """

    actor: Actor

    health_percent: float

    damage_taken: float = 0.0

    active_mitigation: bool = False


@dataclass(frozen=True)
class DeathEntry:
    """
    Ein Tod innerhalb des laufenden Pulls.
    """

    actor_name: str

    at_seconds: float

    cause: str = ""


@dataclass(frozen=True)
class CooldownState:
    """
    Zustand eines Raid- oder Heal-Cooldowns.

    `remaining` ist die Restzeit in Sekunden, bis der Cooldown
    wieder einsatzbereit ist; bei `ready=True` ist sie 0.
    """

    name: str

    actor_name: str

    ready: bool = True

    remaining: float = 0.0

    duration: float = 0.0

    @property
    def progress(self) -> float:
        """
        Fortschritt der Abklingzeit als 0.0 - 1.0 (1.0 = bereit).
        """

        if self.ready or self.duration <= 0:
            return 1.0

        used = self.duration - self.remaining

        return max(0.0, min(1.0, used / self.duration))


@dataclass(frozen=True)
class ConsumableState:
    """
    Verbrauchsgegenstände (Flask, Bufffood, Kampftrank).

    `missing` listet die Namen der Spieler ohne den jeweiligen Buff -
    genau die Information, die die Raidleitung im Pull braucht.
    """

    label: str

    used: int = 0

    total: int = 0

    missing: tuple[str, ...] = ()

    @property
    def ratio(self) -> float:

        if self.total <= 0:
            return 0.0

        return max(0.0, min(1.0, self.used / self.total))


@dataclass(frozen=True)
class MechanicIssue:
    """
    Ein erkannter Mechanikfehler ("steht im Feuer", "Add nicht
    unterbrochen", ...).

    `severity` ist eine der Logger-Stufen (info/warning/error), damit
    die Oberfläche sie ohne Übersetzungstabelle einfärben kann.

    `category` ordnet den Fehler einem trainierbaren Bereich zu und
    ist die Grundlage der Academy-Bewertung (siehe die Konstanten
    MECHANIC_* oben).
    """

    actor_name: str

    mechanic: str

    count: int = 1

    severity: str = "warning"

    category: str = MECHANIC_OTHER

    #
    # Woher der Fehler stammt. Der Bot darf eigene, handverlesene
    # Regeln mitschicken; zusätzlich leitet der Analyzer Fehler aus
    # dem erhaltenen Schaden ab. Ohne dieses Feld ließe sich beim
    # Zusammenführen nicht entscheiden, welche Zeile Vorrang hat -
    # und derselbe Fehler stünde zweimal in der Liste.
    #

    source: str = MECHANIC_SOURCE_BOT

    #
    # Zeitpunkt im Pull, -1 wenn unbekannt. Er ist die Grundlage für
    # den Sprung aus der Academy an genau diese Stelle der Wiedergabe.
    #

    at_seconds: float = -1.0


#
# --------------------------------------------------
# Tiefenauswertung
# --------------------------------------------------
#
# Alles ab hier beantwortet nicht mehr "wie viel", sondern "wie gut":
# Wirkungsdauern, Laufwege, erhaltener Schaden, Cooldown-Einsätze.
# Bewusst je Spieler und je Fähigkeit statt als Raidsumme - eine
# Analyse, die nur Summen kennt, kann niemandem sagen, was er anders
# machen soll.
#


@dataclass(frozen=True)
class ActivityEntry:
    """
    Wie durchgehend ein Spieler tatsächlich Knöpfe gedrückt hat.

    Das ist die Grundlage der Rotationsbewertung - und zwar bewusst
    getrennt vom Schadenswert: hoher Schaden bei löchriger Aktivzeit
    heißt gute Ausrüstung, nicht gutes Spiel, und umgekehrt.

    `active_percent` ist 0-100, `longest_gap` die längste Pause in
    Sekunden (verrät mehr als der Durchschnitt: zehn kurze Lücken
    sind Bewegung, eine lange Lücke ist ein Fehler).
    """

    actor_name: str

    active_percent: float = 0.0

    casts: int = 0

    apm: float = 0.0

    longest_gap: float = 0.0


@dataclass(frozen=True)
class UptimeEntry:
    """
    Die Wirkungsdauer einer Fähigkeit auf einem Ziel.

    DoTs liegen auf Gegnern, HoTs und Buffs auf Verbündeten - die Art
    steckt in `kind` (siehe UPTIME_* oben) statt in getrennten
    Strukturen, damit eine Auswertung über alle laufen kann.

    `expected_percent` ist der Richtwert, ab dem die Uptime als gut
    gilt (0 = kein Richtwert bekannt). Er steht hier und nicht in der
    Oberfläche, damit WeintTV und die Academy denselben Maßstab
    benutzen.
    """

    actor_name: str

    ability: str

    uptime_percent: float = 0.0

    kind: str = UPTIME_DOT

    applications: int = 0

    target: str = ""

    expected_percent: float = 0.0


@dataclass(frozen=True)
class MovementEntry:
    """
    Der Laufweg eines Spielers im Kampf.

    `estimated` ist bewusst standardmäßig True und wird auch so
    angezeigt: WarcraftLogs kennt keine Distanzmetrik, der Wert
    entsteht aus den Positionsangaben aufeinanderfolgender Ereignisse
    und unterschätzt echtes Ausweichen deshalb systematisch. Als
    Vergleich innerhalb eines Pulls ist er belastbar, als absolute
    Zahl nicht - und genau das muss die Oberfläche sagen dürfen.
    """

    actor_name: str

    meters: float = 0.0

    meters_per_second: float = 0.0

    avoidable_hits: int = 0

    estimated: bool = True


@dataclass(frozen=True)
class AbilityDamage:
    """
    Was eine einzelne Fähigkeit einem Spieler angetan hat.

    `verdict` ist einer der VERDICT_*-Werte aus
    analyzer.data.avoidable und bewusst dreiwertig: unbekannt ist
    nicht dasselbe wie unvermeidbar. Würde Unbekanntes als
    unvermeidbar gelten, bekäme jeder Boss ohne Referenzdaten
    automatisch eine tadellose Bewertung.

    `source_name` ist der Verursacher (NPC) - derselbe
    Fähigkeitsname kommt in mehreren Kämpfen vor.
    """

    ability: str

    amount: float = 0.0

    hits: int = 0

    verdict: str = "unknown"

    note: str = ""

    source_name: str = ""

    @property
    def avoidable(self) -> bool:

        return self.verdict == "avoidable"


@dataclass(frozen=True)
class DamageTakenEntry:
    """
    Der erhaltene Schaden eines Spielers, aufgeteilt nach
    Vermeidbarkeit.

    Drei Töpfe statt zwei: `total` minus `avoidable` minus
    `unavoidable` ist der noch nicht eingeordnete Rest
    (`unclassified`). Solange der überwiegt, darf daraus keine
    Bewertung entstehen - dafür gibt es `classified_share`.
    """

    actor_name: str

    total: float = 0.0

    avoidable: float = 0.0

    unavoidable: float = 0.0

    hits: int = 0

    avoidable_hits: int = 0

    abilities: tuple[AbilityDamage, ...] = ()

    @property
    def unclassified(self) -> float:

        return max(0.0, self.total - self.avoidable - self.unavoidable)

    @property
    def avoidable_share(self) -> float:

        if self.total <= 0:
            return 0.0

        return max(0.0, min(1.0, self.avoidable / self.total))

    @property
    def classified_share(self) -> float:
        """
        Wie viel des erhaltenen Schadens überhaupt eingeordnet werden
        konnte. Unter einem Mindestwert ist jede Aussage über
        "vermeidbar" wertlos.
        """

        if self.total <= 0:
            return 0.0

        classified = self.avoidable + self.unavoidable

        return max(0.0, min(1.0, classified / self.total))


@dataclass(frozen=True)
class CooldownUsage:
    """
    Die Einsätze eines Cooldowns über einen ganzen Kampf.

    Bewusst getrennt von `CooldownState`: der beschreibt den
    Live-Countdown ("noch 42 Sekunden"), dieser die Rückschau ("4 von
    6 möglichen Einsätzen, 2 davon im Heldentum"). Beide Sichten aus
    einer Struktur zu bedienen hieße, für einen beendeten Pull eine
    Restzeit zu erfinden.
    """

    actor_name: str

    ability: str

    cast_times: tuple[float, ...] = ()

    cooldown: float = 0.0

    possible: int = 0

    in_burst: int = 0

    category: str = CD_PERSONAL

    @property
    def uses(self) -> int:

        return len(self.cast_times)

    @property
    def efficiency(self) -> float:
        """
        Genutzte von möglichen Einsätzen als 0.0 - 1.0.
        """

        if self.possible <= 0:
            return 0.0

        return max(0.0, min(1.0, self.uses / self.possible))

    @property
    def wasted(self) -> int:

        return max(0, self.possible - self.uses)

    @property
    def burst_share(self) -> float:
        """
        Anteil der Einsätze, die in ein Burstfenster fielen.
        """

        if not self.cast_times:
            return 0.0

        return max(0.0, min(1.0, self.in_burst / len(self.cast_times)))

    @property
    def first_cast(self) -> float:

        return self.cast_times[0] if self.cast_times else -1.0


@dataclass(frozen=True)
class HeroismWindow:
    """
    Ein Heldentum-/Kampfrausch-Fenster mit seinem Zeitpunkt.

    Der Zeitpunkt ist der Grund, warum die Academy Cooldown-Einsätze
    überhaupt bewerten kann: "genutzt" ist wenig wert, "im richtigen
    Fenster genutzt" ist die eigentliche Frage.
    """

    start: float = 0.0

    end: float = 0.0

    source: str = ""

    label: str = "Heldentum"

    @property
    def duration(self) -> float:

        return max(0.0, self.end - self.start)

    def contains(self, seconds: float) -> bool:

        return self.start <= seconds <= self.end

    @property
    def clock(self) -> str:
        """
        Fenster als MM:SS - MM:SS.
        """

        def stamp(value: float) -> str:

            total = max(0, int(value))

            return f"{total // 60:02d}:{total % 60:02d}"

        return f"{stamp(self.start)} - {stamp(self.end)}"


@dataclass(frozen=True)
class ResurrectionEvent:
    """
    Eine im Kampf gewirkte Wiederbelebung.

    Beantwortet die Frage, die die reine Ladungsanzeige offen lässt:
    auf wen, von wem, wann.
    """

    target: str

    caster: str = ""

    at_seconds: float = 0.0

    ability: str = ""

    @property
    def clock(self) -> str:

        total = max(0, int(self.at_seconds))

        return f"{total // 60:02d}:{total % 60:02d}"


@dataclass(frozen=True)
class SupportEvent:
    """
    Eine Unterbrechung oder ein entfernter Effekt.

    Als Einzelereignis mit Zeitpunkt statt als Zähler, weil beides
    daraus ableitbar ist - umgekehrt nicht - und weil nur der
    Zeitpunkt den Sprung aus der Academy in die Wiedergabe erlaubt.
    """

    actor_name: str

    kind: str = SUPPORT_INTERRUPT

    at_seconds: float = 0.0

    target: str = ""

    ability: str = ""


@dataclass(frozen=True)
class CombatEvent:
    """
    Ein sonstiges Kampfereignis mit Zeitpunkt.

    Bewusst frei gehalten (`kind` als Zeichenkette): eine Datenquelle
    darf Ereignisarten nachliefern, ohne dass der Companion sie kennen
    muss - unbekannte Arten laufen einfach in die Ereignisliste von
    WeintTV. Was der Analyzer selbst auswertet (Tode, Kampf-Rezz,
    Unterbrechungen, Dispels) hat dagegen einen eigenen, typisierten
    Platz im Snapshot; hier landet nur, was die Quelle zusätzlich
    erzählt - Phasenwechsel, angesagte Bossfähigkeiten, Adds.

    Liegt in `analyzer/models.py` und nicht bei der Wiedergabe, weil
    beide Wege dieselbe Art Ereignis meinen: die Zeitleiste eines
    archivierten Pulls liefert sie ebenso wie später der Live-
    Combat-Log. Ein zweiter Typ dafür wäre genau die Doppelung, die
    WeintTV und die Academy auseinanderlaufen ließe.
    """

    at_seconds: float

    kind: str

    actor_name: str = ""

    target: str = ""

    ability: str = ""

    detail: str = ""

    severity: str = "info"

    @property
    def clock(self) -> str:

        total = max(0, int(self.at_seconds))

        return f"{total // 60:02d}:{total % 60:02d}"


#
# --------------------------------------------------
# Encounter
# --------------------------------------------------
#


@dataclass(frozen=True)
class EncounterInfo:
    """
    Der aktuell gepullte Boss.

    `encounter_id` und `name` stammen im Live-Betrieb direkt aus dem
    ENCOUNTER_START-Eintrag des Combat-Logs; `instance` wird über
    analyzer.data.encounters nachgeschlagen.
    """

    encounter_id: int

    name: str

    instance: str = ""

    difficulty: str = ""

    raid_size: int = 0


#
# --------------------------------------------------
# Snapshot
# --------------------------------------------------
#


@dataclass(frozen=True)
class RaidSnapshot:
    """
    Ein vollständiges, in sich konsistentes Bild eines Zeitpunkts.

    Die Oberfläche rendert immer genau einen Snapshot und rechnet
    selbst nichts aus. Fehlt eine Information (z. B. weil gerade kein
    Kampf läuft), stehen die Felder auf ihren neutralen Defaults -
    die Oberfläche muss also nie mit None-Sonderfällen umgehen.
    """

    captured_at: float = field(default_factory=time.time)

    #
    # Herkunft
    #

    source_label: str = "Keine Datenquelle"

    live: bool = False

    #
    # Kampfzustand
    #

    in_combat: bool = False

    encounter: EncounterInfo | None = None

    pull_number: int = 0

    pull_seconds: float = 0.0

    boss_health_percent: float = 100.0

    #
    # Raid
    #

    raid_size: int = 0

    deaths: tuple[DeathEntry, ...] = ()

    battle_res_charges: int = 0

    battle_res_max: int = 0

    heroism_used: bool = False

    heroism_remaining: float = 0.0

    #
    # Auswertung
    #

    top_damage: tuple[MetricEntry, ...] = ()

    top_healing: tuple[MetricEntry, ...] = ()

    tanks: tuple[TankEntry, ...] = ()

    raid_cooldowns: tuple[CooldownState, ...] = ()

    heal_cooldowns: tuple[CooldownState, ...] = ()

    consumables: tuple[ConsumableState, ...] = ()

    mechanics: tuple[MechanicIssue, ...] = ()

    warnings: tuple[str, ...] = ()

    #
    # Tiefenauswertung
    #
    # Alle neu und alle mit leerem Default: eine Datenquelle, die
    # davon nichts liefert, erzeugt dadurch keinen Sonderfall - die
    # Oberfläche zeigt schlicht ihren Platzhaltertext. Genau deshalb
    # ist auch nichts hiervon Pflicht.
    #

    activity: tuple[ActivityEntry, ...] = ()

    dot_uptimes: tuple[UptimeEntry, ...] = ()

    hot_uptimes: tuple[UptimeEntry, ...] = ()

    #
    # Eigene Buffs - und damit die einzige Kennzahl, die den
    # Tankbeitrag überhaupt messbar macht: die aktive
    # Schadensminderung (Schildblock, Mischen, Schild des
    # Rechtschaffenen, Knochenschild) ist weder ein DoT noch ein HoT.
    # Ohne eine eigene Liste landete sie entweder bei den HoTs, wo sie
    # nur für Heiler ausgewertet wird, oder gar nicht - und ein Tank
    # wurde in "Rotation" allein an seiner Aktivzeit gemessen, also an
    # der einen Zahl, die über seine eigentliche Aufgabe nichts sagt.
    #

    buff_uptimes: tuple[UptimeEntry, ...] = ()

    movement: tuple[MovementEntry, ...] = ()

    damage_taken: tuple[DamageTakenEntry, ...] = ()

    cooldown_usage: tuple[CooldownUsage, ...] = ()

    heroism_windows: tuple[HeroismWindow, ...] = ()

    resurrections: tuple[ResurrectionEvent, ...] = ()

    interrupts: tuple[SupportEvent, ...] = ()

    dispels: tuple[SupportEvent, ...] = ()

    #
    # Alles, was die Quelle darüber hinaus erzählt (Phasenwechsel,
    # angesagte Bossfähigkeiten, Adds). Getrennt von den typisierten
    # Listen darüber, weil der Companion diese Ereignisse nicht
    # auswertet, sondern nur zeigt - siehe CombatEvent.
    #

    events: tuple[CombatEvent, ...] = ()

    # --------------------------------------------------

    @property
    def death_count(self) -> int:

        return len(self.deaths)

    @property
    def encounter_name(self) -> str:

        if self.encounter is None:
            return "Kein Kampf"

        return self.encounter.name

    @property
    def has_data(self) -> bool:
        """
        Ob überhaupt ein Raid erkannt wurde. Unterscheidet "verbunden,
        aber gerade nichts los" von "keine Datenquelle".
        """

        return self.raid_size > 0

    @property
    def pull_clock(self) -> str:
        """
        Pull-Zeit als MM:SS - die Formatierung gehört hierher und
        nicht in jedes Widget, das sie anzeigt.
        """

        total = max(0, int(self.pull_seconds))

        return f"{total // 60:02d}:{total % 60:02d}"

    @property
    def has_analysis(self) -> bool:
        """
        Ob überhaupt Tiefenauswertung vorliegt.

        Der einzige Schalter, den die Oberfläche braucht, um eine
        ganze Karte auf "keine Daten" zu stellen - statt in jedem
        Widget einzeln auf leere Tupel zu prüfen.
        """

        return bool(
            self.activity
            or self.dot_uptimes
            or self.hot_uptimes
            or self.buff_uptimes
            or self.movement
            or self.damage_taken
            or self.cooldown_usage
        )

    # --------------------------------------------------
    # Nachschlagen je Spieler
    # --------------------------------------------------
    #
    # Lineare Suche über höchstens 25 Einträge - billiger als jede
    # Indexstruktur und, weil der Snapshot eingefroren ist, ohne
    # Gefahr, dass Index und Daten auseinanderlaufen. Eine
    # `cached_property` wäre hier nicht möglich: sie müsste in ein
    # frozen-Objekt schreiben.
    #

    def activity_of(self, name: str) -> ActivityEntry | None:

        for entry in self.activity:

            if entry.actor_name == name:
                return entry

        return None

    def movement_of(self, name: str) -> MovementEntry | None:

        for entry in self.movement:

            if entry.actor_name == name:
                return entry

        return None

    def damage_taken_of(self, name: str) -> DamageTakenEntry | None:

        for entry in self.damage_taken:

            if entry.actor_name == name:
                return entry

        return None

    def uptimes_of(
        self,
        name: str,
        kind: str = UPTIME_DOT,
    ) -> tuple[UptimeEntry, ...]:

        rows = {
            UPTIME_HOT: self.hot_uptimes,
            UPTIME_BUFF: self.buff_uptimes,
        }.get(kind, self.dot_uptimes)

        return tuple(
            entry
            for entry in rows
            if entry.actor_name == name
        )

    def cooldowns_of(self, name: str) -> tuple[CooldownUsage, ...]:

        return tuple(
            entry
            for entry in self.cooldown_usage
            if entry.actor_name == name
        )

    def interrupts_of(self, name: str) -> tuple[SupportEvent, ...]:

        return tuple(
            event
            for event in self.interrupts
            if event.actor_name == name
        )

    def dispels_of(self, name: str) -> tuple[SupportEvent, ...]:

        return tuple(
            event
            for event in self.dispels
            if event.actor_name == name
        )

    def deaths_of(self, name: str) -> tuple[DeathEntry, ...]:

        return tuple(
            death
            for death in self.deaths
            if death.actor_name == name
        )

    def heroism_window_at(self, seconds: float) -> HeroismWindow | None:

        for window in self.heroism_windows:

            if window.contains(seconds):
                return window

        return None

    # --------------------------------------------------
    # Raidweite Bezugsgrößen
    # --------------------------------------------------

    @property
    def movement_average(self) -> float:
        """
        Mittlerer Laufweg des Raids.

        Eine Eigenschaft und kein Feld, damit der Schnitt nie im
        Widerspruch zu den Zeilen stehen kann, aus denen er entsteht.
        """

        if not self.movement:
            return 0.0

        return sum(entry.meters for entry in self.movement) / len(self.movement)

    @property
    def damage_taken_total(self) -> float:

        return sum(entry.total for entry in self.damage_taken)

    @property
    def avoidable_total(self) -> float:

        return sum(entry.avoidable for entry in self.damage_taken)

    @property
    def actor_names(self) -> tuple[str, ...]:
        """
        Alle bekannten Spielernamen des Snapshots, sortiert.
        """

        names = set()

        for entry in self.top_damage + self.top_healing:
            names.add(entry.actor.name)

        for tank in self.tanks:
            names.add(tank.actor.name)

        return tuple(sorted(names))

    # --------------------------------------------------

    @classmethod
    def empty(cls, source_label: str = "Keine Datenquelle") -> "RaidSnapshot":
        """
        Neutraler Snapshot für "noch keine Daten" - so kann die
        Oberfläche vom ersten Frame an dieselbe Renderlogik nutzen.
        """

        return cls(
            source_label=source_label,
            live=False,
        )


#
# --------------------------------------------------
# Pull-Historie
# --------------------------------------------------
#


@dataclass(frozen=True)
class PullSummary:
    """
    Das Ergebnis eines abgeschlossenen Pulls.

    Ein Snapshot beschreibt einen Zeitpunkt, eine PullSummary einen
    ganzen Versuch. Sie ist die Grundlage für Pull-Vergleich und
    Leistungsentwicklung und wird zentral vom RaidDataService
    geführt - nicht von einer einzelnen Seite, damit jede Ansicht
    dieselbe Historie sieht.
    """

    pull_number: int

    encounter_name: str = ""

    duration: float = 0.0

    boss_health_percent: float = 100.0

    death_count: int = 0

    best_damage_name: str = ""

    best_damage_value: float = 0.0

    #
    # Aus der Tiefenauswertung übernommen, damit der Verlauf-Tab
    # Entwicklung über mehrere Pulls zeigen kann und nicht nur
    # Kill/Wipe. 0.0, wenn die Quelle nichts dazu liefert.
    #

    avoidable_damage: float = 0.0

    movement_average: float = 0.0

    #
    # Ab wann ein Pull als Erfolg gilt. Der letzte Prozentpunkt
    # Bossleben verschwindet im Log oft zwischen zwei Ereignissen -
    # eine harte Null wäre deshalb zu streng.
    #

    KILL_THRESHOLD = 1.0

    @property
    def killed(self) -> bool:

        return self.boss_health_percent <= self.KILL_THRESHOLD

    @property
    def clock(self) -> str:

        total = max(0, int(self.duration))

        return f"{total // 60:02d}:{total % 60:02d}"

    # --------------------------------------------------

    @classmethod
    def from_snapshot(cls, snapshot: "RaidSnapshot") -> "PullSummary":

        best = (
            snapshot.top_damage[0]
            if snapshot.top_damage
            else None
        )

        return cls(
            pull_number=snapshot.pull_number,
            encounter_name=snapshot.encounter_name,
            duration=snapshot.pull_seconds,
            boss_health_percent=snapshot.boss_health_percent,
            death_count=snapshot.death_count,
            best_damage_name=best.actor.name if best else "",
            best_damage_value=best.value if best else 0.0,
            avoidable_damage=snapshot.avoidable_total,
            movement_average=snapshot.movement_average,
        )
