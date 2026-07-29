"""
Die Seitenregistrierung der Anwendung.

Vorher war die Navigation an drei Stellen beschrieben: die
Reihenfolge im QStackedWidget (main_window), die Reihenfolge der
Rail-Icons (sidebar) und die Zielseiten der Dashboard-Karten als
nackte Zahlen (`pageRequested.emit(3)`). Diese drei Listen mussten
von Hand deckungsgleich gehalten werden - eine neue Seite an der
falschen Position hätte die Dashboard-Karten stillschweigend auf
die falschen Ziele umgeleitet.

Hier gibt es nur noch eine Quelle: `PageId` legt die Reihenfolge
fest, `build_page_specs()` beschreibt jede Seite genau einmal.
Sidebar und Seitenstapel werden beide daraus aufgebaut und können
deshalb nicht mehr auseinanderlaufen. Ein neuer Bereich ist ein
Eintrag im Enum plus ein Eintrag in der Liste.

Zu den Importen: `build_page_specs()` importiert die Seitenklassen
absichtlich erst im Funktionsrumpf. Die Seiten brauchen ihrerseits
`PageId` (um Navigationsziele zu benennen), ein Import auf Modulebene
wäre also ein Zirkelbezug. Die Funktion wird genau einmal beim Aufbau
des Hauptfensters aufgerufen - zu diesem Zeitpunkt ist dieses Modul
längst vollständig geladen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable


class PageId(IntEnum):
    """
    Reihenfolge der Hauptbereiche.

    Der Wert IST der Index im QStackedWidget und in der Rail. Weil
    IntEnum von int erbt, funktioniert er unverändert mit
    `Signal(int)` und `setCurrentIndex()`.
    """

    DASHBOARD = 0
    ADDON = 1
    SYNC = 2
    WEINTTV = 3
    ACADEMY = 4
    SETTINGS = 5
    LOGS = 6


@dataclass(frozen=True)
class PageSpec:
    """
    Beschreibung einer Seite.

    `icon_factory` und `page_factory` sind bewusst Funktionen und
    keine fertigen Objekte: das Icon wird erst beim Aufbau der Rail
    aufgelöst (dasselbe Vorgehen wie bei TOUR_PAGES im
    Was-ist-neu-Dialog), die Seite erst beim Aufbau des Stapels.

    `scroll` steuert, ob die Seite in einen QScrollArea-Wrapper
    kommt. Das Dashboard bekommt bewusst keinen - siehe den
    ausführlichen Kommentar in main_window.py.
    """

    page_id: PageId

    tooltip: str

    icon_factory: Callable[[], str]

    page_factory: Callable[[object], object]

    scroll: bool = True

    #
    # Name des Attributs, unter dem MainWindow die Seite zusätzlich
    # ablegt (self.dashboard, self.settings, ...). Bestehender Code
    # spricht die Seiten so an; das bleibt unverändert erhalten.
    #

    attribute: str = ""


def build_page_specs() -> tuple[PageSpec, ...]:
    """
    Die vollständige Seitenliste, in Navigationsreihenfolge.
    """

    from core.resources import Resources

    from gui.pages.academy import AcademyPage
    from gui.pages.addon import AddonPage
    from gui.pages.dashboard import DashboardPage
    from gui.pages.logs import LogsPage
    from gui.pages.settings import SettingsPage
    from gui.pages.sync import SyncPage
    from gui.pages.weinttv import WeintTvPage

    return (

        PageSpec(
            page_id=PageId.DASHBOARD,
            tooltip="Dashboard",
            icon_factory=Resources.dashboard,
            page_factory=DashboardPage,
            scroll=False,
            attribute="dashboard",
        ),

        PageSpec(
            page_id=PageId.ADDON,
            tooltip="Software",
            icon_factory=Resources.software,
            page_factory=AddonPage,
            attribute="addon",
        ),

        PageSpec(
            page_id=PageId.SYNC,
            tooltip="Synchronisation",
            icon_factory=Resources.sync,
            page_factory=SyncPage,
            attribute="sync",
        ),

        PageSpec(
            page_id=PageId.WEINTTV,
            tooltip="WeintTV",
            icon_factory=Resources.weinttv,
            page_factory=WeintTvPage,
            attribute="weinttv",
        ),

        PageSpec(
            page_id=PageId.ACADEMY,
            tooltip="WeintAcademy",
            icon_factory=Resources.academy,
            page_factory=AcademyPage,
            attribute="academy",
        ),

        PageSpec(
            page_id=PageId.SETTINGS,
            tooltip="Einstellungen",
            icon_factory=Resources.settings,
            page_factory=SettingsPage,
            attribute="settings",
        ),

        PageSpec(
            page_id=PageId.LOGS,
            tooltip="Logs",
            icon_factory=Resources.logs,
            page_factory=LogsPage,
            attribute="logs",
        ),

    )
