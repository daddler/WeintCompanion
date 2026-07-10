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

from gui.theme.metrics import Metrics

from gui.widgets.sidebar import Sidebar
from gui.widgets.discord_status_button import DiscordStatusButton

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

        self.setCentralWidget(root)

        self.root_layout = QHBoxLayout(root)

        self.root_layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        self.root_layout.setSpacing(18)

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
        # Kopfzeile (Discord-Status, auf jeder Seite sichtbar)
        # --------------------------------------------------
        #

        header_row = QHBoxLayout()

        header_row.setContentsMargins(
            0,
            16,
            20,
            10,
        )

        header_row.addStretch()

        self.discord_status_button = DiscordStatusButton(
            self.manager
        )

        self.discord_status_button.clicked.connect(
            self.open_discord_settings
        )

        header_row.addWidget(
            self.discord_status_button
        )

        self.content_layout.addLayout(
            header_row
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

        self.pages.addWidget(
            self.wrap_page(
                self.dashboard
            )
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

        page = current.widget()

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

    # --------------------------------------------------
    # Resize
    # --------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        #
        # Platz für spätere Responsive-Anpassungen
        #

        if self.width() < 1280:

            self.root_layout.setContentsMargins(
                10,
                10,
                10,
                10,
            )

            self.root_layout.setSpacing(12)

        else:

            self.root_layout.setContentsMargins(
                16,
                16,
                16,
                16,
            )

            self.root_layout.setSpacing(18)