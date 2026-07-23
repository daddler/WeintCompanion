from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.resources import Resources
from gui.theme.colors import Colors
from gui.widgets.card import Card
from gui.widgets.hero_banner import HeroButton
from gui.widgets.log_widget import LogWidget
from gui.widgets.toggle_switch import ToggleSwitch


class _BridgeCard(Card):

    def __init__(
        self,
        title: str,
        description: str,
        real: bool,
        checked: bool = False,
    ):
        super().__init__()

        self.real = real

        top_row = QHBoxLayout()

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        title_color = Colors.WHITE if real else Colors.TEXT_SECONDARY

        title_label = QLabel(title)

        title_label.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{title_color};"
        )

        text_col.addWidget(title_label)

        description_label = QLabel(description)

        description_label.setWordWrap(True)

        description_label.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
        )

        text_col.addWidget(description_label)

        top_row.addLayout(text_col, 1)

        self.toggle = ToggleSwitch(checked=checked)

        if not real:
            self.toggle.setEnabled(False)

        top_row.addWidget(self.toggle, alignment=Qt.AlignTop)

        self.addLayout(top_row)

        caption_text = (
            "Aktiv"
            if real
            else "Geplant - noch nicht implementiert"
        )

        caption = QLabel(caption_text)

        caption.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_FAINT};"
        )

        self.addWidget(caption)


class SyncPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)

        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        #
        # --------------------------------------------------
        # Kopfzeile
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        eyebrow = QLabel("SYNCHRONISATION · DISCORD ↔ SPIEL")
        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Bridges")
        title.setObjectName("title")

        title_col.addWidget(title)

        subtitle = QLabel(
            "Was zwischen deinem Discord-Server und WoW synchronisiert wird."
        )
        subtitle.setObjectName("subtitle")

        title_col.addWidget(subtitle)

        header.addLayout(title_col)

        header.addStretch()

        self.sync_button = HeroButton(
            "Jetzt synchronisieren",
            primary=True,
        )

        header.addWidget(self.sync_button, alignment=Qt.AlignTop)

        layout.addLayout(header)

        #
        # --------------------------------------------------
        # Flow-Visual
        # --------------------------------------------------
        #

        self.flow_card = Card()

        flow_row = QHBoxLayout()

        flow_row.setSpacing(24)

        #
        # WoW
        #

        wow_col = QHBoxLayout()
        wow_col.setSpacing(14)

        wow_text = QVBoxLayout()
        wow_text.setSpacing(2)

        self.wow_title = QLabel("World of Warcraft")

        self.wow_title.setStyleSheet(
            f"font-size:15px;font-weight:600;color:{Colors.WHITE};"
        )

        wow_text.addWidget(self.wow_title)

        self.wow_meta = QLabel("-")

        self.wow_meta.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        wow_text.addWidget(self.wow_meta)

        wow_col.addLayout(wow_text)

        self.wow_icon_box = QLabel()

        self.wow_icon_box.setFixedSize(48, 48)

        wow_icon_layout = QHBoxLayout(self.wow_icon_box)
        wow_icon_layout.setContentsMargins(0, 0, 0, 0)

        wow_icon = QSvgWidget(Resources.game())
        wow_icon.setFixedSize(20, 20)

        wow_icon_layout.addWidget(wow_icon, alignment=Qt.AlignCenter)

        wow_col.addWidget(self.wow_icon_box)

        flow_row.addLayout(wow_col, 1)

        #
        # Mitte: Latenz
        #

        middle_col = QVBoxLayout()
        middle_col.setSpacing(4)

        arrow = QLabel("↔")

        arrow.setAlignment(Qt.AlignCenter)

        arrow.setStyleSheet(
            f"color:{Colors.PRIMARY};font-size:20px;"
        )

        middle_col.addWidget(arrow)

        self.latency_label = QLabel("- ms")

        self.latency_label.setAlignment(Qt.AlignCenter)

        self.latency_label.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_MUTED};"
        )

        middle_col.addWidget(self.latency_label)

        flow_row.addLayout(middle_col)

        #
        # Discord
        #

        discord_col = QHBoxLayout()
        discord_col.setSpacing(14)

        self.discord_icon_box = QLabel()

        self.discord_icon_box.setFixedSize(48, 48)

        discord_icon_layout = QHBoxLayout(self.discord_icon_box)
        discord_icon_layout.setContentsMargins(0, 0, 0, 0)

        discord_icon = QSvgWidget(Resources.discord())
        discord_icon.setFixedSize(20, 20)

        discord_icon_layout.addWidget(
            discord_icon,
            alignment=Qt.AlignCenter,
        )

        discord_col.addWidget(self.discord_icon_box)

        discord_text = QVBoxLayout()
        discord_text.setSpacing(2)

        self.discord_title = QLabel("Discord")

        self.discord_title.setStyleSheet(
            f"font-size:15px;font-weight:600;color:{Colors.WHITE};"
        )

        discord_text.addWidget(self.discord_title)

        self.discord_meta = QLabel("-")

        self.discord_meta.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        discord_text.addWidget(self.discord_meta)

        discord_col.addLayout(discord_text)

        flow_row.addLayout(discord_col, 1)

        self.flow_card.addLayout(flow_row)

        layout.addWidget(self.flow_card)

        #
        # --------------------------------------------------
        # Bridges
        # --------------------------------------------------
        #

        bridge_grid = QGridLayout()

        bridge_grid.setHorizontalSpacing(14)
        bridge_grid.setVerticalSpacing(14)

        self.calendar_bridge = _BridgeCard(
            "Gilden-Kalender",
            "Raid-Anmeldungen → Ingame-Kalender",
            real=True,
            checked=self.manager.config.data.get(
                "roster_sync_enabled", True,
            ),
        )

        self.roster_bridge = _BridgeCard(
            "Charakter-Roster",
            "Twinkverwaltung → Charakter-Datenbank des Bots",
            real=True,
            checked=self.manager.config.data.get(
                "character_roster_sync_enabled", True,
            ),
        )

        self.loot_bridge = _BridgeCard(
            "Loot-Verteilung",
            "Loot-Log → Discord-Channel #loot",
            real=True,
            checked=self.manager.config.data.get(
                "loot_sync_enabled", False,
            ),
        )

        self.chat_bridge = _BridgeCard(
            "Chat-Bridge",
            "Guild-Chat ↔ Discord-Channel",
            real=False,
        )

        bridge_grid.addWidget(self.calendar_bridge, 0, 0)
        bridge_grid.addWidget(self.roster_bridge, 0, 1)
        bridge_grid.addWidget(self.loot_bridge, 1, 0)
        bridge_grid.addWidget(self.chat_bridge, 1, 1)

        bridge_grid.setColumnStretch(0, 1)
        bridge_grid.setColumnStretch(1, 1)

        layout.addLayout(bridge_grid)

        #
        # --------------------------------------------------
        # Live-Tail
        # --------------------------------------------------
        #

        self.logs = LogWidget(manager.logger)

        self.logs.title.setText("Sync-Events")

        layout.addWidget(self.logs, 1)

        #
        # Signale
        #

        self.sync_button.clicked.connect(self.sync_now)

        self.calendar_bridge.toggle.toggled.connect(
            self.set_roster_sync_enabled
        )

        self.loot_bridge.toggle.toggled.connect(
            self.set_loot_sync_enabled
        )

        self.roster_bridge.toggle.toggled.connect(
            self.set_character_roster_sync_enabled
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

            self.wow_meta.setText(
                f"MoP Classic · {state.wow_path.name}"
            )

        else:

            self.wow_meta.setText("Nicht gefunden")

        #
        # Discord
        #

        if state.discord_connected:

            self.discord_meta.setText(state.discord_name)

        else:

            self.discord_meta.setText("Offline")

        if state.discord_latency is not None:

            self.latency_label.setText(f"{state.discord_latency} ms")

        else:

            self.latency_label.setText("- ms")

    # --------------------------------------------------

    def set_roster_sync_enabled(self, enabled: bool):
        """
        Der Config-Key heißt weiterhin "roster_sync_enabled" (siehe
        core/companion_manager.py: DiscordRosterSync), auch wenn er hier
        über die Gilden-Kalender-Karte gesteuert wird - er bezeichnete
        historisch die Roster-Übertragung, tatsächlich treibt er aber
        den Raid-Anmeldung-zu-Ingame-Kalender-Export an.
        """

        self.manager.config.data["roster_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:

            self.manager.logger.success(
                "Gilden-Kalender-Sync aktiviert."
            )

        else:

            self.manager.logger.info(
                "Gilden-Kalender-Sync deaktiviert."
            )

    # --------------------------------------------------

    def set_loot_sync_enabled(self, enabled: bool):

        self.manager.config.data["loot_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:

            self.manager.logger.success(
                "Loot-Sync aktiviert."
            )

        else:

            self.manager.logger.info(
                "Loot-Sync deaktiviert."
            )

    # --------------------------------------------------

    def set_character_roster_sync_enabled(self, enabled: bool):

        self.manager.config.data["character_roster_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:

            self.manager.logger.success(
                "Charakter-Roster-Sync aktiviert."
            )

        else:

            self.manager.logger.info(
                "Charakter-Roster-Sync deaktiviert."
            )

    # --------------------------------------------------

    def sync_now(self):

        self.manager.logger.info(
            "Starte Synchronisationstest..."
        )

        self.refresh()

        state = self.manager.state

        if not state.wow_found:

            self.manager.logger.error(
                "Keine WoW-Installation gefunden."
            )

            return

        if not state.addon_found:

            self.manager.logger.warning(
                "Addon wurde nicht gefunden."
            )

            return

        self.manager.run_auto_sync()

        self.manager.logger.success(
            "Synchronisation angestoßen."
        )
