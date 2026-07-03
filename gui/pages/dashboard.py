from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
)
from gui.widgets.dashboard_cards import DashboardCards
from gui.widgets.log_widget import LogWidget
from gui.widgets.hero_banner import HeroBanner

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
        layout.addWidget(self.hero)

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

        layout.addWidget(self.cards)

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

        self.hero.set_busy(True)

        try:

            state = self.manager.state

            #
            # Companion aktualisieren
            #

            if self.hero.mode == "companion_update":

                self.manager.logger.info(
                    "Companion-Update wird gestartet..."
                )

                self.manager.companion_updater.install_update()

                return

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