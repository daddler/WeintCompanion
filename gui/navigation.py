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

Neu in 4.0: **RAID hat zwei Einträge statt vier.** WeintTV, die
Academy und das Archiv waren drei gleichwertige Hauptbereiche, die
sich unsichtbar eine Datenquelle, einen Snapshot und eine
Archivauswahl teilten - der Nutzer musste selbst wissen, wann er
welchen öffnet, und um von einem analysierten Pull zur passenden
Lektion zu kommen, ging er über die Seitenleiste und wählte dort
Charakter und Pull erneut. Die drei sind zu **vier Perspektiven eines
Bereichs** geworden (Live, Analyse, Lernen, Quelle), die sich einen
Kopfblock und damit einen Pull teilen: `gui/pages/raid_center.py`. Die
Namen WeintTV und WeintAcademy bleiben als Module bestehen (sie
stehen in den Einstellungen, im Addon und auf dem Discord), nur sind
sie keine Orte mehr, an die man gehen muss.

`RaidView` und `RaidLink` weiter unten gehören mit dazu: ein
Tiefenverweis auf einen Pull ist ein Navigationsziel wie eine Seite,
und er gehört deshalb in dieselbe Datei wie `PageId` - nicht als
Sammlung von Schlüsselwortargumenten, die jede rufende Seite selbst
zusammensetzt.
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
    # Zwei Einträge, nicht vier: WeintTV, Academy und Archiv sind
    # Perspektiven des Raid Centers und keine eigenen Orte mehr.
    #

    OVERVIEW = 0
    RAID_CENTER = 1

    #
    # CHARAKTER
    #

    CHARACTERS = 2
    PREPARATION = 3
    SIM = 4
    WEAKAURAS = 5
    CHARACTER_LINKS = 6

    #
    # SYSTEM
    #

    ADDON = 7
    CONNECTIONS = 8
    SETTINGS = 9
    LOGS = 10


#
# Gruppenlabels, in Reihenfolge. Sie erscheinen als `type.micro` über
# dem ersten Eintrag ihrer Gruppe.
#

GROUP_RAID = "RAID"

GROUP_CHARACTER = "CHARAKTER"

GROUP_SYSTEM = "SYSTEM"


#
# ==========================================================
# Die vier Perspektiven des Raid Centers
# ==========================================================
#
# Sie sind **keine** PageIds: ein Perspektivwechsel ist kein
# Seitenwechsel. Der Unterschied ist der ganze Punkt des Umbaus - der
# Kopfblock mit Boss, Pull und Ausgang bleibt stehen, es wechselt nur
# der Blick darauf. Wären sie vier Seiten, wäre auch der Kopfblock
# viermal da, und dann wäre er viermal etwas anderes.
#
# Die Schlüssel sind Zeichenketten und keine Zahlen: sie stehen in
# Tiefenverweisen ("öffne die Analyse dieses Pulls"), und eine 2 in
# einem Signal ist beim nächsten Umbau eine andere Ansicht als vorher.
#

RAID_VIEW_LIVE = "live"

RAID_VIEW_ANALYSIS = "analysis"

RAID_VIEW_LEARN = "learn"

RAID_VIEW_SOURCE = "source"


#
# Reihenfolge und Beschriftung der Umschaltleiste. Sie steht hier und
# nicht in der Seite, aus demselben Grund wie `PageSpec`: die Leiste
# und die Reiter des Stapels entstehen beide daraus und können nicht
# auseinanderlaufen.
#
# Die Beschriftungen benennen **Aufgaben** und nicht Module. "WeintTV"
# und "Academy" sagen, welches Teil der Anwendung antwortet; "Live"
# und "Lernen" sagen, welche Frage man stellt - und nur die zweite
# Auskunft hilft jemandem, der die Anwendung nicht gebaut hat.
#

RAID_VIEWS: tuple[tuple[str, str, str], ...] = (

    (
        RAID_VIEW_LIVE,
        "Live",
        "Was gerade passiert: Bossleben, Pulldauer, Schaden und "
        "Heilung je Spieler, Tode, Cooldowns.",
    ),

    (
        RAID_VIEW_ANALYSIS,
        "Analyse",
        "Die Tiefenauswertung dieses Pulls - Schaden erlitten, "
        "Wirkzeiten, Aktivzeit, Cooldown-Nutzung mit Zeitstrahl.",
    ),

    (
        RAID_VIEW_LEARN,
        "Lernen",
        "Was du als Nächstes verbessern solltest - aus genau diesem "
        "Pull abgeleitet, mit der Lektion dazu.",
    ),

    (
        RAID_VIEW_SOURCE,
        "Quelle",
        "Welchen vergangenen Kampf willst du ansehen? Raidabend, "
        "Boss und Pull - oder zurück zum laufenden Raid.",
    ),

)


RAID_VIEW_KEYS = tuple(key for key, _label, _hint in RAID_VIEWS)

RAID_VIEW_LABELS = {key: label for key, label, _hint in RAID_VIEWS}

RAID_VIEW_HINTS = {key: hint for key, _label, hint in RAID_VIEWS}


@dataclass(frozen=True)
class RaidLink:
    """
    Ein Tiefenverweis auf einen Pull - "zeig mir *das* dort".

    Jedes Feld ist ein Wunsch und keine Vorgabe: was leer bleibt,
    lässt den bestehenden Kontext unberührt. Das ist die
    Voraussetzung dafür, dass ein Wechsel der Perspektive den Pull
    nicht verliert - `RaidLink(view=RAID_VIEW_LEARN)` heisst "derselbe
    Kampf, anderer Blick" und nicht "irgendein Kampf".

    `seconds` ist der Sprung in die Wiedergabe: die Academy weiss, dass
    ein vermeidbarer Treffer bei 03:41 lag, und der Verweis trägt genau
    diese Sekunde mit. `None` heisst "nicht springen" und nicht
    "Sekunde 0" - dieselbe Linie wie bei `at == -1` im Analyzer.
    """

    view: str = ""

    #
    # Welcher Pull. Beide zusammen oder keiner - eine halbe Kennung
    # könnte nichts laden und würde die bestehende Auswahl trotzdem
    # verwerfen.
    #

    report_code: str = ""

    fight_id: int | None = None

    #
    # Auf wen sich Bewertung und Analyse beziehen sollen.
    #

    player: str = ""

    #
    # Sekunde der Wiedergabe.
    #

    seconds: float | None = None

    # --------------------------------------------------

    @property
    def has_pull(self) -> bool:

        return bool(self.report_code) and self.fight_id is not None


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

    from gui.pages.addon import AddonPage
    from gui.pages.character_links import CharacterLinksPage
    from gui.pages.characters import CharactersPage
    from gui.pages.connections import ConnectionsPage
    from gui.pages.logs import LogsPage
    from gui.pages.overview import OverviewPage
    from gui.pages.preparation import PreparationPage
    from gui.pages.raid_center import RaidCenterPage
    from gui.pages.settings import SettingsPage
    from gui.pages.sim import SimPage
    from gui.pages.weakauras import WeakAurasPage

    return (

        PageSpec(
            page_id=PageId.OVERVIEW,
            label="Übersicht",
            group=GROUP_RAID,
            icon="dashboard",
            page_factory=OverviewPage,
            #
            # Mit Scrollbereich. Bei der Entwurfsgröße passt die
            # Übersicht ohne Scrollbalken - bei 960 x 640 aber nicht,
            # und dort ist Scrollen die richtige Antwort: die vier
            # Blöcke haben eine Mindesthöhe, unter die sie nicht
            # gestaucht werden dürfen, ohne unlesbar zu werden.
            #
            # Die Scrollfreiheit ist ausdrücklich nur für WeintTV
            # gefordert (§8), wo sie den Zweck der Ansicht ausmacht.
            #
            scroll=True,
            attribute="overview",
        ),

        #
        # Das Raid Center - ein Bereich, vier Perspektiven.
        #
        # `scroll=False` ist hier nicht Feinheit, sondern die Bedingung
        # des ganzen Umbaus: der Kopfblock mit Boss, Pull und Ausgang
        # muss stehen bleiben, wenn man zwischen Live, Analyse, Lernen
        # und Quelle wechselt. In einem Scrollbereich der ganzen Seite
        # würde er beim ersten Rollen verschwinden - und dann wäre er
        # wieder vier verschiedene Kopfzeilen. Gescrollt wird deshalb
        # **innerhalb** jeder Ansicht (siehe gui/pages/raid_center.py),
        # was zugleich die Bedingung aus §8 erfüllt, dass die Live-
        # Ranglisten 25 Zeilen ohne Scrollen der Seite tragen.
        #
        # `force_collapsed_nav`, weil die dichteste der vier Ansichten
        # die Breite braucht - das war schon für WeintTV und das Archiv
        # so und gilt für ihren gemeinsamen Nachfolger unverändert.
        #

        PageSpec(
            page_id=PageId.RAID_CENTER,
            label="Raid Center",
            group=GROUP_RAID,
            icon="weinttv",
            page_factory=RaidCenterPage,
            scroll=False,
            attribute="raid_center",
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

        #
        # Simmen steht zwischen "Vorbereitung" und "WeakAuras", weil
        # es dasselbe ist: etwas, das man sich vor dem Raid einrichtet.
        # Die Seite simmt nicht selbst (siehe gui/pages/sim.py), sie
        # bringt das Ergebnis von wowsims ins Addon - und genau
        # deshalb steht sie hier und nicht unter SYSTEM: sie handelt
        # von einem Charakter, nicht von der Anwendung.
        #

        PageSpec(
            page_id=PageId.SIM,
            label="Simmen",
            group=GROUP_CHARACTER,
            icon="sim",
            page_factory=SimPage,
            attribute="sim",
        ),

        #
        # WeakAuras stehen bei CHARAKTER und nicht bei RAID: sie
        # gehoeren zu dem, was man sich fuer den Raid einrichtet -
        # dieselbe Gruppe wie "Vorbereitung", direkt daneben. Ingame
        # hat der Bereich eine eigene Rubrik in der Navigationsspalte;
        # dass er hier bei den Charaktersachen liegt, ist kein
        # Widerspruch, sondern folgt der Gruppierung dieser App.
        #

        PageSpec(
            page_id=PageId.WEAKAURAS,
            label="WeakAuras",
            group=GROUP_CHARACTER,
            icon="weakauras",
            page_factory=WeakAurasPage,
            #
            # Ohne Seiten-Wrapper: Liste und Bearbeitungsspalte haben
            # ihre eigenen Scrollbereiche und sollen unter einem
            # stehenden Kopf laufen, nicht mit ihm zusammen - dieselbe
            # Ueberlegung wie bei der Charakterzuordnung.
            #
            scroll=False,
            attribute="weakauras",
        ),

        #
        # Die Charakterzuordnung ist Werkzeug der Raidleitung, steht
        # aber bei allen in der Spalte: ohne die Rolle antwortet der
        # Bot mit 403, und dann erklaert die Seite, wofuer sie da
        # waere. Dieselbe Regel wie im Addon (core/access.lua:
        # "lock, don't hide") - ein Bereich, der je nach Rolle
        # verschwindet, laesst sich weder erklaeren noch danach
        # fragen. Sie haengt an CHARAKTER und nicht an RAID, weil sie
        # von Charakteren handelt und weil die Gruppe RAID die
        # Auswertungsbereiche zusammenhaelt.
        #

        PageSpec(
            page_id=PageId.CHARACTER_LINKS,
            label="Charakterzuordnung",
            group=GROUP_CHARACTER,
            icon="charaktere",
            page_factory=CharacterLinksPage,
            scroll=False,
            attribute="character_links",
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
