"""
Datenmodell der Wiedergabe.

Alle Zeitreihen sind **kumulativ**, nicht als Zuwachs je Takt. Das hat
drei Gründe, und alle drei sind für eine flüssige Wiedergabe
entscheidend:

1. `snapshot_at()` braucht Summen bis zum Zeitpunkt X, um daraus
   Werte pro Sekunde und Anteile zu bauen. Aus kumulativen Reihen ist
   das ein Lesezugriff, aus Zuwächsen eine Summierung über alle
   bisherigen Takte - bei viermal pro Sekunde und 25 Spielern ein
   spürbarer Unterschied.
2. Springen im Kampf (Scrubbing) wird dadurch gleich teuer wie
   Abspielen. Mit Zuwächsen müsste jeder Sprung von vorn aufsummieren.
3. Zwischen zwei Stützpunkten lässt sich sauber interpolieren. Ohne
   das würde die Bossleiste bei achtfacher Geschwindigkeit sichtbar
   ruckeln.

Alles ist eingefroren und benutzt Tupel - dieselbe Begründung wie bei
`RaidSnapshot`: die Zeitleiste wird in einem Hintergrund-Thread
geladen und im Qt-Hauptthread gelesen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analyzer.models import (
    Actor,
    CooldownUsage,
    DamageTakenEntry,
    DeathEntry,
    EncounterInfo,
    HeroismWindow,
    MechanicIssue,
    RaidSnapshot,
    ResurrectionEvent,
    SupportEvent,
    UptimeEntry,
)


#
# --------------------------------------------------
# Bausteine
# --------------------------------------------------
#


@dataclass(frozen=True)
class PlayerSeries:
    """
    Der Verlauf eines Spielers über den Kampf.

    Jede Reihe ist kumulativ und im Takt von `FightTimeline.interval`
    abgetastet. Fehlt eine Reihe, ist sie leer - `snapshot_at()`
    liefert dann für dieses Feld nichts, statt zu raten.
    """

    actor: Actor

    damage: tuple[float, ...] = ()

    healing: tuple[float, ...] = ()

    damage_taken: tuple[float, ...] = ()

    movement_units: tuple[float, ...] = ()

    active_seconds: tuple[float, ...] = ()

    casts: tuple[float, ...] = ()

    @property
    def name(self) -> str:

        return self.actor.name


@dataclass(frozen=True)
class AvoidableHit:
    """
    Ein einzelner vermeidbarer Treffer mit Zeitpunkt.

    Der Zeitpunkt ist der Grund, warum diese Ereignisse einzeln und
    nicht als Summe geführt werden: nur so kann die Academy aus einem
    Befund heraus an genau diese Sekunde der Wiedergabe springen.
    """

    actor_name: str

    ability: str

    at_seconds: float = 0.0

    amount: float = 0.0

    note: str = ""


@dataclass(frozen=True)
class TimelineEvent:
    """
    Ein sonstiges Ereignis, das die Wiedergabe anzeigen soll.

    Bewusst frei gehalten (`kind` als Zeichenkette): der Bot darf
    Ereignisarten nachliefern, ohne dass der Companion sie kennen
    muss - unbekannte Arten laufen einfach in die Ereignisliste.
    """

    at_seconds: float

    kind: str

    actor_name: str = ""

    target: str = ""

    ability: str = ""

    detail: str = ""

    severity: str = "info"


#
# --------------------------------------------------
# Zeitleiste
# --------------------------------------------------
#


@dataclass(frozen=True)
class FightTimeline:
    """
    Der vollständige Verlauf eines Kampfes.

    `aggregate` ist der Gesamtschnappschuss des fertigen Kampfes und
    die Rückfallebene für alles, was sich pro Sekunde nicht ehrlich
    rekonstruieren lässt (Verbrauchsgüter etwa, oder die vollständige
    Fähigkeitsaufschlüsselung des erhaltenen Schadens). Am Ende der
    Wiedergabe zeigt die Oberfläche denselben Stand wie im Archiv.
    """

    encounter: EncounterInfo | None = None

    source_label: str = ""

    pull_number: int = 0

    duration: float = 0.0

    interval: float = 1.0

    raid_size: int = 0

    battle_res_max: int = 0

    #
    # Verlauf
    #

    boss_health: tuple[float, ...] = ()

    players: tuple[PlayerSeries, ...] = ()

    #
    # Ereignisse
    #

    deaths: tuple[DeathEntry, ...] = ()

    resurrections: tuple[ResurrectionEvent, ...] = ()

    heroism_windows: tuple[HeroismWindow, ...] = ()

    cooldown_usage: tuple[CooldownUsage, ...] = ()

    avoidable_hits: tuple[AvoidableHit, ...] = ()

    interrupts: tuple[SupportEvent, ...] = ()

    dispels: tuple[SupportEvent, ...] = ()

    mechanics: tuple[MechanicIssue, ...] = ()

    events: tuple[TimelineEvent, ...] = ()

    #
    # Gesamtstand
    #

    damage_taken_totals: tuple[DamageTakenEntry, ...] = ()

    dot_uptimes: tuple[UptimeEntry, ...] = ()

    hot_uptimes: tuple[UptimeEntry, ...] = ()

    aggregate: RaidSnapshot = field(default_factory=RaidSnapshot)

    # --------------------------------------------------

    @property
    def has_data(self) -> bool:
        """
        Ob sich daraus überhaupt eine Wiedergabe bauen lässt.
        """

        return self.duration > 0 and bool(self.players)

    @property
    def sample_count(self) -> int:

        return len(self.boss_health)

    @property
    def encounter_name(self) -> str:

        if self.encounter is None:
            return "Kein Kampf"

        return self.encounter.name

    @property
    def clock(self) -> str:
        """
        Gesamtdauer als MM:SS.
        """

        total = max(0, int(self.duration))

        return f"{total // 60:02d}:{total % 60:02d}"

    def series_for(self, name: str) -> PlayerSeries | None:

        for series in self.players:

            if series.actor.name == name:
                return series

        return None
