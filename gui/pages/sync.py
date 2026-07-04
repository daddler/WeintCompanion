from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
)

from gui.widgets.hero_banner import HeroButton
from gui.widgets.section_card import SectionCard
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

        # --------------------------------------------------
        # Statuskarten
        # --------------------------------------------------

        self.status_card = StatusCard(
            "🔄",
            "Synchronisation",
            "Bereit",
            "Noch keine Prüfung durchgeführt.",
        )

        self.wow_card = StatusCard(
            "🎮",
            "World of Warcraft",
            "-",
            "-",
        )

        self.addon_card = StatusCard(
            "📦",
            "WeintCodex",
            "-",
            "-",
        )

        self.discord_card = StatusCard(
            "💬",
            "Discord Bot",
            "-",
            "-",
        )

        cards = QGridLayout()

        cards.setHorizontalSpacing(18)
        cards.setVerticalSpacing(18)

        cards.addWidget(
            self.status_card,
            0,
            0,
        )

        cards.addWidget(
            self.wow_card,
            0,
            1,
        )

        cards.addWidget(
            self.addon_card,
            0,
            2,
        )

        cards.addWidget(
            self.discord_card,
            1,
            0,
            1,
            3,
        )

        for column in range(3):
            cards.setColumnStretch(column, 1)

        layout.addLayout(cards)

        #
        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------
        #

        # --------------------------------------------------
        # Aktionen
        # --------------------------------------------------

        self.connection_button = HeroButton(
            "Verbindung prüfen",
            primary=False,
        )

        self.sync_button = HeroButton(
            "Synchronisation testen",
            primary=True,
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(14)

        button_row.addWidget(self.connection_button)
        button_row.addWidget(self.sync_button)
        button_row.addStretch()

        layout.addLayout(button_row)

        #
        # --------------------------------------------------
        # Log
        # --------------------------------------------------
        #

        self.logs = LogWidget(manager.logger)

        log_card = SectionCard(
            "📜 Live-Protokoll"
        )

        log_card.addWidget(self.logs)

        layout.addWidget(log_card)

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

        self.manager.full_refresh()

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

        #
        # Discord Bot
        #

        if state.discord_connected:

            self.discord_card.set_state(
                "normal"
            )

            self.discord_card.set_status(
                "🟢 Online"
            )

            self.discord_card.set_value(
                state.discord_name
            )

            self.discord_card.set_details(
                "\n".join([
                    f"Server: {state.discord_guilds}",
                    f"Ping: {state.discord_latency} ms",
                ])
            )

        else:

            self.discord_card.set_state(
                "error"
            )

            self.discord_card.set_status(
                "🔴 Offline"
            )

            self.discord_card.set_value("")

            self.discord_card.set_details(
                "Bot konnte nicht erreicht werden."
            )

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