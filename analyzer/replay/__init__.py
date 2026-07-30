"""
Wiedergabe eines abgeschlossenen Kampfes.

Dies ist die eine, bewusst eng gezogene Ausnahme vom Grundsatz "der
`RaidSnapshot` ist der einzige Vertrag": eine Wiedergabe braucht den
ganzen Kampf, nicht einen Zeitpunkt. `FightTimeline` beschreibt
deshalb den vollständigen Verlauf.

Sie erreicht trotzdem nie ein Widget. Der einzige Leser ist
`snapshot_at()`, und der liefert wieder einen ganz gewöhnlichen
`RaidSnapshot` zurück. Für WeintTV und die WeintAcademy ist eine
Wiedergabe deshalb ununterscheidbar von einem Live-Feed - sie sehen
Sekunde für Sekunde einen normalen Snapshot und rechnen wie immer
nichts selbst aus.

Genau daraus entsteht die Verzahnung beider Bereiche: weil die
Academy jede Kennzahl aus dem Snapshot liest, bewertet sie während
der Wiedergabe automatisch den Stand zur gerade gezeigten Sekunde -
ohne eine einzige Zeile Wiedergabe-Code auf ihrer Seite.

Wie der ganze Analyzer: kein Qt, kein Netzwerk. Die Uhr, die
`snapshot_at()` viermal pro Sekunde aufruft, sitzt in
core/raid_data_service.py.
"""

from analyzer.replay.models import (
    AvoidableHit,
    FightTimeline,
    PlayerSeries,
    TimelineEvent,
)
from analyzer.replay.reconstruct import snapshot_at

__all__ = [
    "AvoidableHit",
    "FightTimeline",
    "PlayerSeries",
    "TimelineEvent",
    "snapshot_at",
]
