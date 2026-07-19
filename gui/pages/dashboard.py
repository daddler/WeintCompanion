from pathlib import Path
import threading

from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from core.platform import open_folder
from gui.widgets.activity_panel import ActivityPanel
from gui.widgets.dashboard_cards import DashboardCards
from gui.widgets.hero_banner import HeroButton
from gui.widgets.priority_banner import PriorityBanner


class _CompanionUpdateBridge(QObject):
    """
    Meldet das Ergebnis des Companion-Updates thread-sicher an den
    Hauptthread zurück (siehe LogWidget._LogBridge fürs gleiche Muster).
    """

    finished = Signal(bool)


class _UpdateCheckBridge(QObject):
    """
    Meldet das Ende der manuellen Update-Prüfung (Refresh-Button)
    thread-sicher an den Hauptthread zurück.
    """

    finished = Signal()


class DashboardPage(QWidget):

    pageRequested = Signal(int)

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        root = QHBoxLayout(self)

        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)

        #
        # --------------------------------------------------
        # Hauptspalte
        # --------------------------------------------------
        #

        main_column = QVBoxLayout()

        main_column.setSpacing(20)

        root.addLayout(main_column, 1)

        #
        # Kopfzeile
        #

        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        eyebrow = QLabel(
            "DASHBOARD · MISTS OF PANDARIA CLASSIC"
        )

        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Willkommen zurück.")

        title.setObjectName("title")

        title_col.addWidget(title)

        header.addLayout(title_col)

        header.addStretch()

        self.check_updates_button = HeroButton(
            "Nach Updates suchen",
            primary=False,
        )

        self.check_updates_button.clicked.connect(
            self.start_update_check
        )

        header.addWidget(
            self.check_updates_button,
            alignment=Qt.AlignVCenter,
        )

        main_column.addLayout(header)

        #
        # Priority-Banner (ersetzt den alten HeroBanner)
        #

        self.hero = PriorityBanner()

        self.hero.primaryClicked.connect(
            self.install_or_update
        )

        self.hero.secondaryClicked.connect(
            self.open_addon
        )

        self.hero.refreshClicked.connect(
            self.start_update_check
        )

        main_column.addWidget(self.hero)

        #
        # Bridge fürs Companion-Update (läuft im Hintergrund-Thread)
        #

        self._update_bridge = _CompanionUpdateBridge(self)
        self._update_bridge.finished.connect(
            self._on_companion_update_finished
        )

        self._update_check_bridge = _UpdateCheckBridge(self)
        self._update_check_bridge.finished.connect(
            self._on_update_check_finished
        )

        #
        # Modul-Grid (Statuskarten)
        #

        self.cards = DashboardCards(manager)

        self.cards.folderRequested.connect(
            self.choose_classic_folder
        )

        self.cards.pageRequested.connect(
            self.pageRequested.emit
        )

        main_column.addWidget(self.cards)

        #
        # Quick Actions
        #

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        self.open_addon_button = HeroButton(
            "Addon-Ordner öffnen",
            primary=False,
        )

        self.open_addon_button.clicked.connect(
            self.open_addon_folder
        )

        self.start_wow_button = HeroButton(
            "WoW starten",
            primary=False,
        )

        self.start_wow_button.setEnabled(False)

        self.start_wow_button.setToolTip(
            "Geplant - noch nicht verfügbar."
        )

        self.sync_now_button = HeroButton(
            "Jetzt synchronisieren",
            primary=False,
        )

        self.sync_now_button.clicked.connect(
            self.sync_now_quick
        )

        for button in (
            self.open_addon_button,
            self.start_wow_button,
            self.sync_now_button,
        ):

            quick_row.addWidget(button, 1)

        main_column.addStretch()

        main_column.addLayout(quick_row)

        #
        # --------------------------------------------------
        # Activity-Panel
        # --------------------------------------------------
        #

        self.activity = ActivityPanel(manager.logger)

        self.activity.openLogsRequested.connect(
            lambda: self.pageRequested.emit(4)
        )

        root.addWidget(self.activity)

        #
        # Initialer Zustand
        #

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        self.manager.refresh()

        self.cards.refresh()

        self.hero.updateFromState(
            self.manager.state
        )

    # --------------------------------------------------

    def install_or_update(self):

        state = self.manager.state

        #
        # Companion aktualisieren
        #
        # Läuft bewusst NICHT im try/finally unten mit, weil Download
        # und Installation in einem Hintergrund-Thread laufen (siehe
        # _start_companion_update) - set_busy(False) passiert dort erst,
        # wenn der Thread wirklich fertig ist, statt sofort nach dem Start.
        #

        if self.hero.mode == "companion_update":

            self._start_companion_update()
            return

        self.hero.set_busy(True)

        try:

            #
            # WoW fehlt
            #

            if not state.wow_found:

                self.choose_classic_folder()
                return

            #
            # Addon installieren / aktualisieren
            #

            if state.addon_found:

                self.manager.logger.info(
                    "Addon-Aktualisierung wird gestartet..."
                )

            else:

                self.manager.logger.info(
                    "Addon-Installation wird gestartet..."
                )

            self.manager.install_or_update()

            self.manager.logger.success(
                "Installation abgeschlossen."
            )

        except Exception as exc:

            self.manager.logger.error(
                str(exc)
            )

        finally:

            self.hero.set_busy(False)

            self.refresh()

    # --------------------------------------------------
    # Companion-Update (Download + Installation im Hintergrund)
    # --------------------------------------------------
    # Download und Installation können bei großen Dateien/langsamen
    # Verbindungen mehrere Sekunden bis Minuten dauern. Liefe das im
    # GUI-Thread, würde die Event-Loop solange blockieren - das Fenster
    # wirkt eingefroren und der "Bitte warten"-Zustand kann sich nicht
    # einmal selbst zeichnen. Deshalb läuft der eigentliche Download/
    # Install-Aufruf in einem Hintergrund-Thread, das Ergebnis kommt
    # über ein Qt-Signal (thread-sicher) zurück in den Hauptthread.

    def _start_companion_update(self):

        self.hero.set_busy(True)
        self.hero.setUpdateInProgress()

        self.manager.logger.info(
            "Companion-Update wird heruntergeladen..."
        )

        #
        # WICHTIG: stop_auto_sync() fasst ein QTimer-Objekt an, das
        # dem Hauptthread gehört (self.manager.sync_timer). Das muss
        # deshalb HIER, im Hauptthread, passieren - nicht im Worker
        # unten. Ein Cross-Thread-Zugriff auf QTimer.stop() hat genau
        # das eingefrorene Fenster ("reagiert nicht") verursacht, das
        # vorher beim Companion-Update auftrat.
        #

        self.manager.stop_auto_sync()

        thread = threading.Thread(
            target=self._companion_update_worker,
            daemon=True,
            name="CompanionUpdateThread",
        )

        thread.start()

    def _companion_update_worker(self):

        try:

            success = (
                self.manager.companion_updater
                .install_update()
            )

        except Exception as exc:

            self.manager.logger.error(
                f"Companion-Update fehlgeschlagen: {exc}"
            )

            success = False

        self._update_bridge.finished.emit(success)

    def _on_companion_update_finished(self, success: bool):

        self.hero.set_busy(False)

        if success:

            #
            # QApplication.quit() gehört ebenfalls in den Hauptthread
            # (dieser Slot läuft dort, da das Signal per Queued
            # Connection über Thread-Grenzen zugestellt wird). Eine
            # kurze Verzögerung gibt dem gerade gestarteten Updater/
            # Installer einen Moment Luft, bevor das Fenster
            # verschwindet.
            #

            QTimer.singleShot(
                300,
                QApplication.quit,
            )

            return

        #
        # Fehlschlag: die App läuft weiter, also muss die zu Beginn
        # gestoppte Auto-Sync auch wieder anlaufen - sonst bleibt sie
        # für den Rest der Sitzung stumm (keine periodischen Syncs
        # mehr), bis die App neu gestartet wird.
        #

        self.manager.start_auto_sync()

        #
        # refresh() holt den echten Zustand aus dem AppState
        # (companion_update_available ist weiterhin True) und zeigt so
        # wieder korrekt "Update verfügbar" statt fälschlich
        # "Alles aktuell".
        #

        self.refresh()

    # --------------------------------------------------
    # Manuelle Update-Prüfung (Refresh-Button im Banner)
    # --------------------------------------------------
    # Macht zwei Netzwerkanfragen an GitHub (bis zu 15s Timeout je
    # Anfrage, siehe GitHubUpdater) - läuft deshalb ebenfalls im
    # Hintergrund-Thread, statt die UI währenddessen einfrieren zu
    # lassen.

    def start_update_check(self):

        self.hero.set_refresh_busy(True)

        self.manager.logger.info(
            "Suche nach Updates..."
        )

        thread = threading.Thread(
            target=self._update_check_worker,
            daemon=True,
            name="UpdateCheckThread",
        )

        thread.start()

    def _update_check_worker(self):

        try:

            self.manager.refresh_update_status()

        except Exception as exc:

            self.manager.logger.error(
                f"Update-Prüfung fehlgeschlagen: {exc}"
            )

        self._update_check_bridge.finished.emit()

    def _on_update_check_finished(self):

        self.hero.set_refresh_busy(False)

        self.refresh()

    # --------------------------------------------------

    def open_addon(self):

        self.pageRequested.emit(1)

    # --------------------------------------------------

    def choose_classic_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "MoP Classic auswählen",
        )

        if not folder:
            return

        folder = Path(folder)

        #
        # Benutzer hat den WoW-Hauptordner gewählt?
        #

        if (
            folder.name == "World of Warcraft"
            and (folder / "_classic_").exists()
        ):
            folder = folder / "_classic_"

        interface = folder / "Interface"
        addons = interface / "AddOns"
        wtf = folder / "WTF"

        if not (
            interface.exists()
            and
            addons.exists()
            and
            wtf.exists()
        ):

            self.manager.logger.error(
                "Kein gültiger MoP-Classic-Ordner."
            )

            return

        self.manager.config.set_classic_path(folder)

        self.manager.logger.success(
            f"Classic-Pfad gespeichert: {folder}"
        )

        self.refresh()

    # --------------------------------------------------
    # Quick Actions
    # --------------------------------------------------

    def open_addon_folder(self):

        state = self.manager.state

        if not state.addon_found:

            self.manager.logger.error(
                "Addon-Ordner nicht gefunden."
            )

            return

        open_folder(state.addon_path)

    def sync_now_quick(self):

        self.manager.logger.info(
            "Manuelle Synchronisation gestartet..."
        )

        self.manager.run_auto_sync()