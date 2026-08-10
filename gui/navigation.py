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
Navigationsspalte und Seitenstapel werden beide daraus aufgebaut und
können deshalb nicht mehr auseinanderlaufen. Ein neuer Bereich ist ein
Eintrag im Enum plus ein Eintrag in der Liste.

Zu den Importen: `build_page_specs()` importiert die Seitenklassen
absichtlich erst im Funktionsrumpf. Die Seiten brauchen ihrerseits
`PageId` (um Navigationsziele zu benennen), ein Import auf Modulebene
wäre also ein Zirkelbezug. Die Funktion wird genau einmal beim Aufbau
des Hauptfensters aufgerufen - zu diesem Zeitpunkt ist dieses Modul
längst vollständig geladen.

Neu in 2.0: die Bereiche sind **gruppiert** (RAID / CHARAKTER /
SYSTEM). Die Gruppe steht am `PageSpec` und nicht in der
Navigationsspalte, damit auch sie aus derselben einen Liste entsteht -
sonst gäbe es wieder zwei Reihenfolgen, die zusammenpassen müssen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable


class PageId(IntEnum):
    """
    Reihenfolge der Hauptbereiche.

    Der Wert IST der Index im QStackedWidget und in der
    Navigationsspalte. Weil IntEnum von int erbt, funktioniert er
    unverändert mit `Signal(int)` und `setCurrentIndex()`.
    """

    #
    # RAID
    #

    OVERVIEW = 0
    WEINTTV = 1
    ACADEMY = 2
    ARCHIVE = 3

    #
    # CHARAKTER
    #

    CHARACTERS = 4
    PREPARATION = 5

    #
    # SYSTEM
    #

    ADDON = 6
    CONNECTIONS = 7
    SETTINGS = 8
    LOGS = 9


#
# Gruppenlabels, in Reihenfolge. Sie erscheinen als `type.micro` über
# dem ersten Eintrag ihrer Gruppe.
#

GROUP_RAID = "RAID"

GROUP_CHARACTER = "CHARAKTER"

GROUP_SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class PageSpec:
    """
    Beschreibung einer Seite.

    `icon_factory` und `page_factory` sind bewusst Funktionen und
    keine fertigen Objekte: das Icon wird erst beim Aufbau der
    Navigationsspalte aufgelöst (dasselbe Vorgehen wie bei TOUR_PAGES
    im Was-ist-neu-Dialog), die Seite erst beim Aufbau des Stapels.

    `scroll` steuert, ob die Seite in einen QScrollArea-Wrapper
    kommt. Übersicht und WeintTV bekommen bewusst keinen - siehe den
    ausführlichen Kommentar in main_window.py.
    """

    page_id: PageId

    #
    # Beschriftung in der ausgeklappten Spalte. Eingeklappt (72 px)
    # wird sie zum Tooltip.
    #

    label: str

    group: str

    icon: str

    page_factory: Callable[[object], object]

    scroll: bool = True

    #
    # Name des Attributs, unter dem MainWindow die Seite zusätzlich
    # ablegt (self.overview, self.settings, ...). Bestehender Code
    # spricht die Seiten so an; das bleibt unverändert erhalten.
    #

    attribute: str = ""

    #
    # Bereiche, die dichter sind als der Rest, verlangen die volle
    # Breite: WeintTV muss 25 Zeilen ohne Scrollen unterbringen und
    # klappt die Navigationsspalte deshalb immer ein, unabhängig von
    # der Fensterbreite.
    #

    force_collapsed_nav: bool = False


def build_page_specs() -> tuple[PageSpec, ...]:
    """
    Die vollständige Seitenliste, in Navigationsreihenfolge.
    """

    from gui.pages.academy import AcademyPage
    from gui.pages.addon import AddonPage
    from gui.pages.archive import ArchivePage
    from gui.pages.characters import CharactersPage
    from gui.pages.connections import ConnectionsPage
    from gui.pages.logs import LogsPage
    from gui.pages.overview import OverviewPage
    from gui.pages.preparation import PreparationPage
    from gui.pages.settings import SettingsPage
    from gui.pages.weinttv import WeintTvPage

    return (

        PageSpec(
            page_id=PageId.OVERVIEW,
            label="Übersicht",
            group=GROUP_RAID,
            icon="dashboard",
            page_factory=OverviewPage,
            scroll=False,
            attribute="overview",
        ),

        PageSpec(
            page_id=PageId.WEINTTV,
            label="WeintTV",
            group=GROUP_RAID,
            icon="weinttv",
            page_factory=WeintTvPage,
            #
            # Der Entwurf verlangt für WeintTV `scroll=False`: 25
            # Zeilen sollen bei 1440 x 900 ohne Scrollen passen, und
            # das geht nur, wenn die Seite die volle Höhe bekommt
            # statt eines Scrollbereichs. Solange die Seite noch die
            # Anordnung aus 1.7 trägt (Zeilenhöhen und feste Höhen aus
            # einer Zeit, in der jede Schrift versehentlich 14 px war),
            # würde das ihren unteren Teil abschneiden. Der Wechsel auf
            # False gehört mit dem Umbau der Seite zusammen, nicht
            # davor.
            #
            scroll=True,
            attribute="weinttv",
            force_collapsed_nav=True,
        ),

        PageSpec(
            page_id=PageId.ACADEMY,
            label="Academy",
            group=GROUP_RAID,
            icon="academy",
            page_factory=AcademyPage,
            attribute="academy",
        ),

        PageSpec(
            page_id=PageId.ARCHIVE,
            label="Archiv",
            group=GROUP_RAID,
            icon="archiv",
            page_factory=ArchivePage,
            scroll=False,
            attribute="archive",
            force_collapsed_nav=True,
        ),

        PageSpec(
            page_id=PageId.CHARACTERS,
            label="Meine Charaktere",
            group=GROUP_CHARACTER,
            icon="charaktere",
            page_factory=CharactersPage,
            attribute="characters",
        ),

        PageSpec(
            page_id=PageId.PREPARATION,
            label="Vorbereitung",
            group=GROUP_CHARACTER,
            icon="vorbereitung",
            page_factory=PreparationPage,
            attribute="preparation",
        ),

        PageSpec(
            page_id=PageId.ADDON,
            label="Addon & Updates",
            group=GROUP_SYSTEM,
            icon="software",
            page_factory=AddonPage,
            attribute="addon",
        ),

        PageSpec(
            page_id=PageId.CONNECTIONS,
            label="Verbindungen",
            group=GROUP_SYSTEM,
            icon="sync",
            page_factory=ConnectionsPage,
            attribute="connections",
        ),

        PageSpec(
            page_id=PageId.SETTINGS,
            label="Einstellungen",
            group=GROUP_SYSTEM,
            icon="settings",
            page_factory=SettingsPage,
            attribute="settings",
        ),

        PageSpec(
            page_id=PageId.LOGS,
            label="Protokoll",
            group=GROUP_SYSTEM,
            icon="logs",
            page_factory=LogsPage,
            attribute="logs",
        ),

    )
