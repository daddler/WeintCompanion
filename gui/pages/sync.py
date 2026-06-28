from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.log_widget import LogWidget
from gui.widgets.status_card import StatusCard


class SyncPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        title = QLabel("Synchronisation")
        title.setObjectName("title")

        subtitle = QLabel(
            "Überprüfe die Verbindung zwischen WeintCompanion, WeintCodex und zukünftigen Diensten."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        #
        # --------------------------------------------------
        # Status
        # --------------------------------------------------
        #

        self.status_card = StatusCard(
            "🔄",
            "Synchronisation",
            "Bereit",
            "Noch keine Prüfung durchgeführt.",
        )

        layout.addWidget(self.status_card)

        #
        # --------------------------------------------------
        # World of Warcraft
        # --------------------------------------------------
        #

        self.wow_card = StatusCard(
            "🎮",
            "World of Warcraft",
            "-",
            "-",
        )

        layout.addWidget(self.wow_card)

        #
        # --------------------------------------------------
        # WeintCodex
        # --------------------------------------------------
        #

        self.addon_card = StatusCard(
            "📦",
            "WeintCodex",
            "-",
            "-",
        )

        layout.addWidget(self.addon_card)

        #
        # --------------------------------------------------
        # Discord
        # --------------------------------------------------
        #

        self.discord_card = StatusCard(
            "💬",
            "Discord Bot",
            "Nicht verbunden",
            "Diese Funktion wird später ergänzt.",
        )

        layout.addWidget(self.discord_card)

        #
        # --------------------------------------------------
        # Companion
        # --------------------------------------------------
        #

        self.companion_card = StatusCard(
            "🖥",
            "WeintCompanion",
            "Bereit",
            "Synchronisationsdienst verfügbar.",
        )

        layout.addWidget(self.companion_card)

        #
        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------
        #

        self.sync_button = QPushButton(
            "🔄 Synchronisation testen"
        )

        self.connection_button = QPushButton(
            "🔎 Verbindung prüfen"
        )

        layout.addWidget(self.sync_button)
        layout.addWidget(self.connection_button)

        #
        # --------------------------------------------------
        # Log
        # --------------------------------------------------
        #

        self.logs = LogWidget(
            manager.logger
        )

        layout.addWidget(self.logs)

        layout.addStretch()

        #
        # Signale
        #

        self.sync_button.clicked.connect(
            self.sync_now
        )

        self.connection_button.clicked.connect(
            self.check_connection
        )

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        state = self.manager.state

        #
        # WoW
        #

        if state.wow_found:

            self.wow_card.set_status(
                "🟢 Gefunden"
            )

            self.wow_card.set_details(
                str(state.wow_path)
            )

        else:

            self.wow_card.set_status(
                "🔴 Nicht gefunden"
            )

            self.wow_card.set_details(
                "Bitte Classic auswählen."
            )

        #
        # Addon
        #

        if state.addon_found:

            self.addon_card.set_status(
                "🟢 Installiert"
            )

            self.addon_card.set_details(
                f"Version {state.addon_version}"
            )

        else:

            self.addon_card.set_status(
                "🔴 Nicht installiert"
            )

            self.addon_card.set_details("-")

    # --------------------------------------------------

    def check_connection(self):

        self.manager.logger.info(
            "Prüfe Synchronisationsvoraussetzungen..."
        )

        self.refresh()

        self.manager.logger.success(
            "Prüfung abgeschlossen."
        )

    # --------------------------------------------------

    def sync_now(self):

        self.manager.logger.info(
            "Starte Synchronisationstest..."
        )

        self.refresh()

        state = self.manager.state

        if not state.wow_found:

            self.status_card.set_status(
                "🔴 Nicht bereit"
            )

            self.status_card.set_details(
                "World of Warcraft wurde nicht gefunden."
            )

            self.manager.logger.error(
                "Keine WoW-Installation gefunden."
            )

            return

        if not state.addon_found:

            self.status_card.set_status(
                "🟡 Teilweise bereit"
            )

            self.status_card.set_details(
                "WeintCodex ist nicht installiert."
            )

            self.manager.logger.warning(
                "Addon wurde nicht gefunden."
            )

            return

        self.status_card.set_status(
            "🟢 Bereit"
        )

        self.status_card.set_details(
            "Alle Voraussetzungen sind erfüllt."
        )

        self.manager.logger.success(
            "Synchronisationstest erfolgreich."
        )