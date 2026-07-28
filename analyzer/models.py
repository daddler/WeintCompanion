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
        )
