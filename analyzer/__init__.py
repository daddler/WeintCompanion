"""
Raidlog Analyzer - die Auswertungsschicht des Weint-Ökosystems.

Dieses Paket ist bewusst framework-agnostisch: es importiert weder
PySide6 noch sonst etwas aus gui/. Damit bleibt es ohne laufende
Oberfläche testbar und könnte später unverändert in ein eigenes
Package/Repo wandern.

Der einzige Vertrag zur Oberfläche ist `RaidSnapshot` (siehe
analyzer.models): ein unveränderliches Gesamtbild eines Zeitpunkts.
Kein Widget kennt jemals ein einzelnes Combat-Log-Event.
"""

from analyzer.models import (
    Actor,
    ConsumableState,
    CooldownState,
    DeathEntry,
    EncounterInfo,
    MechanicIssue,
    MetricEntry,
    RaidSnapshot,
    TankEntry,
)

__all__ = [
    "Actor",
    "ConsumableState",
    "CooldownState",
    "DeathEntry",
    "EncounterInfo",
    "MechanicIssue",
    "MetricEntry",
    "RaidSnapshot",
    "TankEntry",
]
