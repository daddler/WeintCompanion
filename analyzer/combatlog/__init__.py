"""
Zugriff auf das Combat-Log von World of Warcraft.

Iteration 1 enthält hier ausschließlich die Pfadsuche
(`locator`). Der eigentliche inkrementelle Leser sowie der
Event-Parser folgen in einem eigenen Schritt - bis dahin liefert
`analyzer.providers.mock.MockRaidDataProvider` die Daten.
"""

from analyzer.combatlog.locator import (
    CombatLogLocation,
    find_combat_log,
    logs_directory,
)

__all__ = [
    "CombatLogLocation",
    "find_combat_log",
    "logs_directory",
]
