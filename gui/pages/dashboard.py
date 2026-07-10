from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
)
from gui.widgets.dashboard_cards import DashboardCards
from gui.widgets.log_widget import LogWidget
from gui.widgets.hero_banner import HeroBanner


class _CompanionUpdateBridge(QObject):
    """
    Meldet das Ergebnis des Companion-Updates thread-sicher an den
    Hauptthread zurück (siehe LogWidget._LogBridge fürs gleiche Muster).
    """

    finished = Signal(bool)


class DashboardPage(QWidget):

    pageRequested = Signal(int)

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)

        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(22)

        #
        # Hero Banner
        #

        self.hero = HeroBanner()
        self.hero.primaryClicked.connect(
            self.install_or_update
        )

        self.hero.secondaryClicked.connect(
            self.open_addon
        )
        layout.addWidget(self.hero)

        #
        # Bridge fürs Companion-Update (läuft im Hintergrund-Thread)
        #

        self._update_bridge = _CompanionUpdateBridge(self)
        self._update_bridge.finished.connect(
            self._on_companion_update_finished
        )

        #
        # Statuskarten
        #

        self.cards = DashboardCards(manager)

        self.cards.folderRequested.connect(
            self.choose_classic_folder
        )

        self.cards.pageRequested.connect(
            self.pageRequested.emit
        )

        #
        # Karten in den Hero integrieren
        #

        self.hero.addDashboardCards(
            self.cards
        )

        #
        # Log Widget
        #

        self.logs = LogWidget(
            manager.logger
        )

        layout.addWidget(self.logs)

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

        #
        # Bei Erfolg beendet sich die App gleich selbst
        # (QApplication.quit() wurde bereits im Worker aufgerufen) -
        # der Reset ist dann irrelevant, schadet aber nicht.
        #
        # Bei Fehlschlag holt refresh() den echten Zustand aus dem
        # AppState (companion_update_available ist weiterhin True) und
        # zeigt so wieder korrekt "Update verfügbar" statt fälschlich
        # "Alles aktuell".
        #

        self.hero.set_busy(False)

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