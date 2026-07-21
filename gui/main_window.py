from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QStackedWidget,
    QScrollArea,
)

from core.companion_manager import CompanionManager
from core.resources import Resources

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics

from gui.widgets.sidebar import Sidebar

from gui.pages.dashboard import DashboardPage
from gui.pages.addon import AddonPage
from gui.pages.sync import SyncPage
from gui.pages.settings import SettingsPage
from gui.pages.logs import LogsPage


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        #
        # --------------------------------------------------
        # Fenster
        # --------------------------------------------------
        #

        self.setWindowTitle("WeintCompanion")

        self.resize(
            Metrics.WINDOW_MIN_WIDTH,
            Metrics.WINDOW_MIN_HEIGHT,
        )

        self.setMinimumSize(
            Metrics.WINDOW_MIN_WIDTH,
            Metrics.WINDOW_MIN_HEIGHT,
        )

        self.setWindowIcon(
            QIcon(Resources.icon())
        )

        #
        # --------------------------------------------------
        # Companion Manager
        # --------------------------------------------------
        #

        self.manager = CompanionManager()

        self.manager.initialize()

        #
        # --------------------------------------------------
        # Root Widget
        # --------------------------------------------------
        #

        root = QWidget()

        #
        # Ohne einen expliziten, opaken Hintergrund bleibt dieses
        # zentrale Widget (und alles, was sich per "background:
        # transparent" darauf verlässt) im echten Rendering-Backing-
        # Store transparent (Alpha 0) statt dunkel gefüllt - auf dem
        # Bildschirm bisher zufällig unsichtbar, weil der Alpha-Kanal
        # dort ignoriert wird, aber z. B. bei Screenshots/Grabs oder
        # Compositing-Fenstermanagern als weißer/durchsichtiger
        # Hintergrund sichtbar. WA_StyledBackground erzwingt, dass
        # das "background"-Stylesheet dieses Widgets tatsächlich
        # gemalt wird.
        #

        root.setObjectName("rootWidget")

        root.setAttribute(Qt.WA_StyledBackground, True)

        root.setStyleSheet(
            f"QWidget#rootWidget{{background:{Colors.BACKGROUND};}}"
        )

        self.setCentralWidget(root)

        self.root_layout = QHBoxLayout(root)

        self.root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.root_layout.setSpacing(0)

        #
        # --------------------------------------------------
        # Sidebar
        # --------------------------------------------------
        #

        self.sidebar = Sidebar(
            self.manager
        )

        self.root_layout.addWidget(
            self.sidebar
        )

        #
        # --------------------------------------------------
        # Content Container
        # --------------------------------------------------
        #

        self.content = QFrame()

        self.content.setObjectName(
            "contentContainer"
        )

        self.content.setAttribute(
            Qt.WA_StyledBackground, True
        )

        self.content.setStyleSheet(
            f"QFrame#contentContainer{{background:{Colors.BACKGROUND};}}"
        )

        self.content_layout = QVBoxLayout(
            self.content
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.content_layout.setSpacing(0)

        self.root_layout.addWidget(
            self.content,
            1,
        )

        #
        # --------------------------------------------------
        # Seiten
        # --------------------------------------------------
        #

        self.pages = QStackedWidget()

        self.content_layout.addWidget(
            self.pages
        )

        self.dashboard = DashboardPage(
            self.manager
        )

        self.addon = AddonPage(
            self.manager
        )

        self.sync = SyncPage(
            self.manager
        )

        self.settings = SettingsPage(
            self.manager
        )

        self.logs = LogsPage(
            self.manager
        )

        #
        # ScrollContainer
        #
        # Das Dashboard bekommt bewusst KEINEN Scroll-Wrapper: das
        # Fenster ist auf Metrics.WINDOW_MIN_HEIGHT dimensioniert,
        # damit der komplette Dashboard-Inhalt (inkl. Changelog-Karte)
        # immer ohne Scrollen der Hauptseite passt - lediglich die
        # Changelog-Karte selbst darf bei längerem Text intern
        # scrollen (siehe ChangelogCard/QTextEdit).
        #

        self.pages.addWidget(
            self.dashboard
        )

        self.pages.addWidget(
            self.wrap_page(
                self.addon
            )
        )

        self.pages.addWidget(
            self.wrap_page(
                self.sync
            )
        )

        self.SETTINGS_PAGE_INDEX = self.pages.count()

        self.pages.addWidget(
            self.wrap_page(
                self.settings
            )
        )

        self.pages.addWidget(
            self.wrap_page(
                self.logs
            )
        )

        #
        # Navigation
        #

        self.sidebar.pageChanged.connect(
            self.change_page
        )

        self.sidebar.avatarClicked.connect(
            self.open_discord_settings
        )

        self.dashboard.pageRequested.connect(
            self.change_page
        )

        #
        # Startseite
        #

        self.change_page(0)

    # --------------------------------------------------
    # Scroll Wrapper
    # --------------------------------------------------

    def wrap_page(self, widget):

        scroll = QScrollArea()

        scroll.setWidget(widget)

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QScrollArea.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        scroll.setStyleSheet("""
        QScrollArea{

            background:transparent;

            border:none;
        }

        QWidget{

            background:transparent;
        }
        """)

        return scroll

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def change_page(self, index: int):

        #
        # Sidebar aktualisieren
        #

        for i, item in enumerate(self.sidebar.items):

            item.setActive(i == index)

        #
        # Seite wechseln
        #

        self.pages.setCurrentIndex(index)

        #
        # Aktuelle Seite holen
        #

        current = self.pages.currentWidget()

        if current is None:
            return

        #
        # Die meisten Seiten stecken in einem QScrollArea-Wrapper
        # (siehe wrap_page) - das Dashboard bewusst nicht (siehe
        # Kommentar bei dessen addWidget-Aufruf oben).
        #

        page = (
            current.widget()
            if isinstance(current, QScrollArea)
            else current
        )

        #
        # Refresh
        #

        if hasattr(page, "refresh"):

            page.refresh()

        #
        # Sidebar ebenfalls aktualisieren
        #

        self.sidebar.refresh()

    # --------------------------------------------------
    # Discord-Statusbutton
    # --------------------------------------------------

    def open_discord_settings(self):

        self.change_page(
            self.SETTINGS_PAGE_INDEX
        )

        if hasattr(self.settings, "show_section"):

            self.settings.show_section("discord")

