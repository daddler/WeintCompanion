"""
Raidlog Analyzer - die Auswertungsschicht des Weint-Ökosystems.

Dieses Paket ist bewusst framework-agnostisch: es importiert weder
PySide6 noch sonst etwas aus gui/. Damit bleibt es ohne laufende
Oberfläche testbar und könnte später unverändert in ein eigenes
Package/Repo wandern.

Der einzige Vertrag zur Oberfläche ist `RaidSnapshot` (siehe
analyzer.models): ein unveränderliches Gesamtbild eines Zeitpunkts.
Kein Widget kennt jemals ein einzelnes Combat-Log-Event.

Einzige Ausnahme, und sie ist bewusst eng gezogen: `FightTimeline`
(analyzer.replay) beschreibt einen ganzen Kampf statt eines
Zeitpunkts, weil eine Wiedergabe ohne Zeitreihe nicht möglich ist.
Sie erreicht aber ebenfalls kein Widget - nur `snapshot_at()` liest
sie und liefert daraus wieder einen gewöhnlichen `RaidSnapshot`.
"""

from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_OTHER,
    MECHANIC_POSITIONING,
    MECHANIC_SOURCE_BOT,
    MECHANIC_SOURCE_LOCAL,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    SUPPORT_DISPEL,
    SUPPORT_INTERRUPT,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    AbilityDamage,
    ActivityEntry,
    Actor,
    ConsumableState,
    CooldownState,
    CooldownUsage,
    DamageTakenEntry,
    DeathEntry,
    EncounterInfo,
    HeroismWindow,
    MechanicIssue,
    MetricEntry,
    MovementEntry,
    PullSummary,
    RaidSnapshot,
    ResurrectionEvent,
    SupportEvent,
    TankEntry,
    UptimeEntry,
)

__all__ = [
    "AbilityDamage",
    "ActivityEntry",
    "Actor",
    "CD_DEFENSIVE",
    "CD_HEAL",
    "CD_PERSONAL",
    "CD_RAID",
    "ConsumableState",
    "CooldownState",
    "CooldownUsage",
    "DamageTakenEntry",
    "DeathEntry",
    "EncounterInfo",
    "HeroismWindow",
    "MECHANIC_DEFENSIVE",
    "MECHANIC_INTERRUPT",
    "MECHANIC_MOVEMENT",
    "MECHANIC_OTHER",
    "MECHANIC_POSITIONING",
    "MECHANIC_SOURCE_BOT",
    "MECHANIC_SOURCE_LOCAL",
    "MechanicIssue",
    "MetricEntry",
    "MovementEntry",
    "PullSummary",
    "ROLE_DPS",
    "ROLE_HEALER",
    "ROLE_TANK",
    "RaidSnapshot",
    "ResurrectionEvent",
    "SUPPORT_DISPEL",
    "SUPPORT_INTERRUPT",
    "SupportEvent",
    "TankEntry",
    "UPTIME_BUFF",
    "UPTIME_DOT",
    "UPTIME_HOT",
    "UptimeEntry",
]
