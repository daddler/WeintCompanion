"""
Datenquellen des Analyzers.

Jede Quelle - der Mock, der spätere Live-Leser des Combat-Logs, ein
denkbarer WarcraftLogs- oder Bot-Adapter - implementiert dieselbe
Schnittstelle `RaidDataProvider`. Die Oberfläche kennt ausschließlich
diese Schnittstelle und nie eine konkrete Quelle; eine neue Quelle
hinzuzufügen bedeutet daher keinen Umbau, sondern eine weitere Klasse.
"""

from analyzer.providers.base import RaidDataProvider
from analyzer.providers.mock import MockRaidDataProvider

__all__ = [
    "RaidDataProvider",
    "MockRaidDataProvider",
]
