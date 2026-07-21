from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QScrollArea,
    QSystemTrayIcon,
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
        # System-Tray ("In Tray minimieren")
        # --------------------------------------------------
        #

        self._force_quit = False

        self._tray_hint_shown = False

        self.tray_icon = None

        self._init_tray()

        self.manager.tray_settings_changed.connect(
            self._on_tray_setting_changed
        )

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
            lambda: self.open_settings_section("discord")
        )

        self.dashboard.pageRequested.connect(
            self.change_page
        )

        self.dashboard.openSettingsSection.connect(
            self.open_settings_section
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
    # Zu einem Settings-Unterabschnitt springen
    # --------------------------------------------------
    # Genutzt vom Discord-Statusbutton in der Sidebar sowie vom
    # "WoW starten"-Button im Dashboard, wenn unter Linux noch kein
    # Start-Befehl hinterlegt ist.

    def open_settings_section(self, key: str):

        self.change_page(
            self.SETTINGS_PAGE_INDEX
        )

        if hasattr(self.settings, "show_section"):

            self.settings.show_section(key)

    # --------------------------------------------------
    # System-Tray
    # --------------------------------------------------

    def _init_tray(self):

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(
            QIcon(Resources.icon()),
            self,
        )

        self.tray_icon.setToolTip("WeintCompanion")

        menu = QMenu()

        open_action = QAction("Öffnen", menu)

        open_action.triggered.connect(
            self._restore_from_tray
        )

        menu.addAction(open_action)

        menu.addSeparator()

        quit_action = QAction("Beenden", menu)

        quit_action.triggered.connect(
            self._quit_from_tray
        )

        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

        self.tray_icon.activated.connect(
            self._on_tray_activated
        )

        self._apply_tray_visibility()

    def _apply_tray_visibility(self):

        if self.tray_icon is None:
            return

        enabled = self.manager.config.data.get(
            "minimize_to_tray",
            False,
        )

        self.tray_icon.setVisible(enabled)

    def _on_tray_setting_changed(self, enabled: bool):

        self._apply_tray_visibility()

        #
        # Wird das Feature deaktiviert, während das Fenster gerade
        # im Tray "geparkt" ist, würde es sonst unerreichbar bleiben
        # (kein Tray-Icon mehr, kein sichtbares Fenster).
        #

        if not enabled and not self.isVisible():

            self._restore_from_tray()

    def _on_tray_activated(self, reason):

        if reason not in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        ):
            return

        if self.isVisible() and not self.isMinimized():

            self.hide()

        else:

            self._restore_from_tray()

    def _restore_from_tray(self):

        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self):

        self._force_quit = True

        QApplication.quit()

    # --------------------------------------------------
    # Fenster minimieren/schließen -> Tray
    # --------------------------------------------------

    def changeEvent(self, event):

        if event.type() == QEvent.WindowStateChange:

            minimize_to_tray = self.manager.config.data.get(
                "minimize_to_tray",
                False,
            )

            if (
                self.isMinimized()
                and minimize_to_tray
                and self.tray_icon is not None
                and self.tray_icon.isVisible()
            ):

                #
                # Direktes hide() aus dem Minimieren-Übergang heraus
                # verhält sich auf manchen Compositorn unzuverlässig
                # (Taskleisten-Icon bleibt hängen) - ein Tick später
                # im nächsten Event-Loop-Durchlauf ist der sichere Weg.
                #

                QTimer.singleShot(0, self.hide)

        super().changeEvent(event)

    def closeEvent(self, event):

        minimize_to_tray = self.manager.config.data.get(
            "minimize_to_tray",
            False,
        )

        if (
            not self._force_quit
            and minimize_to_tray
            and self.tray_icon is not None
            and self.tray_icon.isVisible()
        ):

            event.ignore()

            self.hide()

            if not self._tray_hint_shown:

                self.tray_icon.showMessage(
                    "WeintCompanion",
                    "Läuft im Hintergrund weiter - über das "
                    "Tray-Symbol wieder öffnen.",
                    QSystemTrayIcon.Information,
                    3000,
                )

                self._tray_hint_shown = True

            return

        super().closeEvent(event)

