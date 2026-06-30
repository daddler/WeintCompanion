from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QWidget,
)

from core.companion_manager import CompanionManager

from gui.widgets.sidebar import Sidebar

from gui.pages.dashboard import DashboardPage
from gui.pages.addon import AddonPage
from gui.pages.sync import SyncPage
from gui.pages.settings import SettingsPage
from gui.pages.logs import LogsPage
from core.resources import Resources


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        #
        # Fenster
        #

        self.setWindowTitle("Weint Companion")
        self.resize(1200, 750)
        self.setMinimumSize(1050, 680)

        self.setWindowIcon(
            QIcon(Resources.icon())
        )

        #
        # Zentraler CompanionManager
        #

        self.manager = CompanionManager()
        self.manager.initialize()

        #
        # Root Widget
        #

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        #
        # Sidebar
        #

        self.sidebar = Sidebar(self.manager)
        layout.addWidget(self.sidebar)

        #
        # Seiten
        #

        self.pages = QStackedWidget()

        self.dashboard = DashboardPage(self.manager)
        self.addon = AddonPage(self.manager)
        self.sync = SyncPage(self.manager)
        self.settings = SettingsPage(self.manager)
        self.logs = LogsPage(self.manager)

        self.pages.addWidget(
            self.wrap_page(self.dashboard)
        )

        self.pages.addWidget(
            self.wrap_page(self.addon)
        )

        self.pages.addWidget(
            self.wrap_page(self.sync)
        )

        self.pages.addWidget(
            self.wrap_page(self.settings)
        )

        self.pages.addWidget(
            self.wrap_page(self.logs)
        )

        layout.addWidget(self.pages)

        #
        # Navigation
        #

        self.sidebar.pageChanged.connect(
            self.change_page
        )

        self.dashboard.pageRequested.connect(
            self.change_page
        )

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

        return scroll

    # --------------------------------------------------

    def change_page(self, index):

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
        # Seite aktualisieren
        #

        scroll = self.pages.currentWidget()

        page = scroll.widget()

        if hasattr(page, "refresh"):

            page.refresh()

        self.sidebar.refresh()