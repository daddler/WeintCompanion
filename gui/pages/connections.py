"""
Verbindungen.

Der Bereich, der bis 1.7 "Synchronisation" hieß. Der neue Name ist
keine Kosmetik: die Seite zeigt nicht nur den Materialsync, sondern
den Zustand **aller** Verbindungen dieser App - Discord-Konto, Bot,
Addon-Postfach und die einzelnen Brücken dazwischen.

Die Seite selbst ist unverändert `SyncPage`; sie wird beim Umbau der
Bildschirme auf das 2.0-Kartenbild gezogen. Der Alias steht hier
statt eines Imports von `gui.pages.sync` in `navigation.py`, damit
die Registry schon jetzt den endgültigen Namen nennt und der spätere
Umbau nur noch diese eine Datei betrifft.
"""

from __future__ import annotations

from gui.pages.sync import SyncPage


class ConnectionsPage(SyncPage):
    pass
