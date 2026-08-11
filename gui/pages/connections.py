"""
Verbindungen.

Bis 1.7 hieß dieser Bereich „Synchronisation" (`SyncPage`) und zeigte
denselben Inhalt: den Fluss zwischen WoW/Addon und Discord, die
einzelnen Brücken einzeln ein- und ausschaltbar, ein Live-Protokoll.
Der neue Name ist keine Kosmetik - die Seite beantwortet nicht nur
„läuft der Sync gerade", sondern „stehen alle Verbindungen, die diese
App braucht": Discord-Konto, Bot, Addon-Postfach, und dann erst die
einzelnen Brücken dazwischen.

Diese Datei ersetzt `gui/pages/sync.py`, das damit entfällt - es gab
keinen zweiten Verwendungszweck für die alte Seite, `connections.py`
war zuvor nur ein Alias darauf (`class ConnectionsPage(SyncPage): pass`).
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.resources import Resources
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.icons import tinted_pixmap
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.log_widget import LogWidget
from gui.widgets.status_dot import StatusDot
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.wrapped_label import enable_wrap


class _Endpoint(QHBoxLayout):
    """
    Ein Ende der Flusskarte: Symbol, Name, Zustandszeile mit
    `StatusDot`. `reverse=True` spiegelt die Anordnung, damit Discord
    auf der rechten Seite zur Mitte hin ausgerichtet bleibt.
    """

    def __init__(self, icon: str, name: str, reverse: bool = False):

        super().__init__()

        self.setSpacing(tokens.SPACE[2])

        badge = QLabel()

        badge.setFixedSize(48, 48)

        badge.setAlignment(Qt.AlignCenter)

        badge.setPixmap(tinted_pixmap(icon, tokens.TEXT["secondary"], 22))

        restyle(
            badge,
            f"""
            QLabel{{
                background:{tokens.SURFACE["raised"]};
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        text_col = QVBoxLayout()

        text_col.setContentsMargins(0, 0, 0, 0)

        text_col.setSpacing(2)

        title = QLabel(name)

        title.setFont(font("card"))

        restyle(title, f"color:{tokens.WHITE};background:transparent;")

        text_col.addWidget(title)

        status_row = QHBoxLayout()

        status_row.setContentsMargins(0, 0, 0, 0)

        status_row.setSpacing(6)

        self.dot = StatusDot("empty")

        status_row.addWidget(self.dot)

        self.meta = QLabel("-")

        self.meta.setFont(font("mono"))

        restyle(self.meta, f"color:{tokens.TEXT['muted']};background:transparent;")

        status_row.addWidget(self.meta)

        status_row.addStretch(1)

        text_col.addLayout(status_row)

        if reverse:

            self.addLayout(text_col, 1)

            self.addWidget(badge)

        else:

            self.addWidget(badge)

            self.addLayout(text_col, 1)

    def set_state(self, state: str, meta: str):

        self.dot.setState(state)

        self.meta.setText(meta)


class _BridgeCard(Card):
    """
    Eine Brücke: Name, Beschreibung, Schalter, Zustandschip.
    """

    def __init__(
        self,
        title: str,
        description: str,
        real: bool,
        checked: bool = False,
        parent=None,
    ):

        super().__init__(parent=parent)

        self.real = real

        top_row = QHBoxLayout()

        top_row.setContentsMargins(0, 0, 0, 0)

        top_row.setSpacing(tokens.SPACE[2])

        text_col = QVBoxLayout()

        text_col.setContentsMargins(0, 0, 0, 0)

        text_col.setSpacing(4)

        title_label = QLabel(title)

        title_label.setFont(font("card"))

        restyle(
            title_label,
            f"color:{tokens.WHITE if real else tokens.TEXT['secondary']};"
            "background:transparent;",
        )

        text_col.addWidget(title_label)

        description_label = enable_wrap(QLabel(description))

        description_label.setFont(font("small"))

        restyle(
            description_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        text_col.addWidget(description_label)

        top_row.addLayout(text_col, 1)

        self.toggle = ToggleSwitch(checked=checked)

        if not real:
            self.toggle.setEnabled(False)

        top_row.addWidget(self.toggle, alignment=Qt.AlignTop)

        self.addLayout(top_row)

        self.state_chip = Chip(
            "AKTIV" if real else "GEPLANT",
            "ok" if real else "neutral",
        )

        chip_row = QHBoxLayout()

        chip_row.setContentsMargins(0, 0, 0, 0)

        chip_row.addWidget(self.state_chip)

        chip_row.addStretch(1)

        self.addLayout(chip_row)


class ConnectionsPage(Page):

    #
    # Beides wird aus dem Prüf-Thread gemeldet und über die Event-Loop
    # des Hauptthreads zugestellt (siehe `_sync_worker`). Ein QTimer
    # oder ein Widget darf nicht aus einem fremden Thread angefasst
    # werden.
    #

    syncRequested = Signal()

    syncFinished = Signal()

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "VERBINDUNGEN · DISCORD ↔ SPIEL",
            "Was zwischen deinem Discord-Server und WoW läuft.",
            parent,
        )

        self._sync_thread: threading.Thread | None = None

        self.syncRequested.connect(self._on_sync_requested)

        self.syncFinished.connect(self._on_sync_finished)

        self.sync_button = self._make_sync_button()

        self.header.addAction(self.sync_button)

        #
        # Flusskarte
        #

        self.flow_card = Card()

        flow_row = QHBoxLayout()

        flow_row.setContentsMargins(0, 0, 0, 0)

        flow_row.setSpacing(tokens.SPACE[4])

        self.wow_endpoint = _Endpoint("game", "World of Warcraft")

        flow_row.addLayout(self.wow_endpoint, 1)

        middle = QVBoxLayout()

        middle.setContentsMargins(0, 0, 0, 0)

        middle.setSpacing(2)

        arrow = QLabel("↔")

        arrow.setAlignment(Qt.AlignCenter)

        restyle(arrow, f"color:{tokens.TEXT['faint']};background:transparent;")

        middle.addWidget(arrow)

        self.latency_label = eyebrow_label("- MS")

        self.latency_label.setAlignment(Qt.AlignCenter)

        middle.addWidget(self.latency_label)

        flow_row.addLayout(middle)

        self.discord_endpoint = _Endpoint("discord", "Discord", reverse=True)

        flow_row.addLayout(self.discord_endpoint, 1)

        self.flow_card.addLayout(flow_row)

        self.addWidget(self.flow_card)

        #
        # Brücken
        #

        bridge_grid = QGridLayout()

        bridge_grid.setContentsMargins(0, 0, 0, 0)

        bridge_grid.setHorizontalSpacing(tokens.SPACE[3])

        bridge_grid.setVerticalSpacing(tokens.SPACE[3])

        self.calendar_bridge = _BridgeCard(
            "Gilden-Kalender",
            "Raid-Anmeldungen → Ingame-Kalender",
            real=True,
            checked=self.manager.config.data.get("roster_sync_enabled", True),
        )

        self.roster_bridge = _BridgeCard(
            "Charakter-Roster",
            "Twinkverwaltung → Charakter-Datenbank des Bots",
            real=True,
            checked=self.manager.config.data.get(
                "character_roster_sync_enabled", True
            ),
        )

        self.loot_bridge = _BridgeCard(
            "Loot-Verteilung",
            "Loot-Log → Discord-Channel #loot",
            real=True,
            checked=self.manager.config.data.get("loot_sync_enabled", False),
        )

        self.analysis_bridge = _BridgeCard(
            "WeintTV & Academy ingame",
            "Letzte Auswertung → Addon",
            real=True,
            checked=self.manager.config.data.get(
                "addon_analysis_sync_enabled", True
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
        bridge_grid.addWidget(self.analysis_bridge, 1, 1)
        bridge_grid.addWidget(self.chat_bridge, 2, 0)

        bridge_grid.setColumnStretch(0, 1)
        bridge_grid.setColumnStretch(1, 1)

        self.addLayout(bridge_grid)

        #
        # Live-Protokoll
        #

        self.logs = LogWidget(manager.logger)

        self.logs.title.setText("Sync-Ereignisse")

        self.addWidget(self.logs, 1)

        #
        # Signale
        #

        self.sync_button.clicked.connect(self.sync_now)

        self.calendar_bridge.toggle.toggled.connect(
            self.set_roster_sync_enabled
        )

        self.loot_bridge.toggle.toggled.connect(self.set_loot_sync_enabled)

        self.roster_bridge.toggle.toggled.connect(
            self.set_character_roster_sync_enabled
        )

        self.analysis_bridge.toggle.toggled.connect(
            self.set_addon_analysis_sync_enabled
        )

        self.refresh()

    # --------------------------------------------------

    def _make_sync_button(self):

        button = QPushButton("Jetzt synchronisieren")

        button.setCursor(Qt.PointingHandCursor)

        return button

    # --------------------------------------------------

    def refresh(self):
        """
        Nur zeichnen.

        Hier stand ein `self.manager.full_refresh()` - ein vollständiger
        Netzdurchgang (GitHub, Discord, Sync) **blockierend im
        Hauptthread**, und zwar in einer Methode, die `change_page()`
        bei jedem Betreten der Seite aufruft und die der Konstruktor
        gleich mit. Das Fenster stand damit jedes Mal, wenn man
        "Verbindungen" öffnete.

        Seit es `CompanionManager.state_changed` gibt, war es zusätzlich
        eine Endlosschleife: `full_refresh()` meldet am Ende seinen
        neuen Zustand, das Fenster zeichnet daraufhin die sichtbare
        Seite neu - und die fing wieder von vorne an.

        Die Prüfung gehört zu der Handlung, die sie verlangt: dem Knopf
        "Jetzt synchronisieren" (siehe `sync_now()`). Ihr Ergebnis
        erreicht diese Seite von selbst über `state_changed`.
        """

        state = self.manager.state

        if state.wow_found:

            self.wow_endpoint.set_state(
                "ok", f"MoP Classic · {state.wow_path.name}"
            )

        else:

            self.wow_endpoint.set_state("error", "Nicht gefunden")

        if state.discord_connected:

            self.discord_endpoint.set_state("ok", state.discord_name)

        else:

            self.discord_endpoint.set_state("empty", "Offline")

        if state.discord_latency is not None:

            self.latency_label.setText(f"{state.discord_latency} MS")

        else:

            self.latency_label.setText("- MS")

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
            self.manager.logger.success("Gilden-Kalender-Sync aktiviert.")

        else:
            self.manager.logger.info("Gilden-Kalender-Sync deaktiviert.")

    def set_loot_sync_enabled(self, enabled: bool):

        self.manager.config.data["loot_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:
            self.manager.logger.success("Loot-Sync aktiviert.")

        else:
            self.manager.logger.info("Loot-Sync deaktiviert.")

    def set_addon_analysis_sync_enabled(self, enabled: bool):
        """
        Stellt die zuletzt ausgewertete Analyse ins Addon, damit
        WeintTV und die Academy auch im Spiel nachlesbar sind (siehe
        core/addon_analysis_sync.py). Ausgeschaltet wird nichts mehr
        zugestellt; bereits im Addon gespeicherte Berichte bleiben
        dort, sie werden nur nicht mehr aktualisiert.
        """

        self.manager.config.data["addon_analysis_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:
            self.manager.logger.success("Ingame-Auswertung aktiviert.")

        else:
            self.manager.logger.info("Ingame-Auswertung deaktiviert.")

    def set_character_roster_sync_enabled(self, enabled: bool):

        self.manager.config.data["character_roster_sync_enabled"] = enabled

        self.manager.config.save()

        if enabled:
            self.manager.logger.success("Charakter-Roster-Sync aktiviert.")

        else:
            self.manager.logger.info("Charakter-Roster-Sync deaktiviert.")

    def sync_now(self):
        """
        Alles neu prüfen und dann synchronisieren.

        In einem eigenen kurzlebigen Thread - dasselbe Vorgehen wie bei
        den Archiv-Abrufen. `full_refresh()` fragt GitHub und den Bot,
        das sind Sekunden, und die gehören nicht in einen Klick-Handler.
        Die Anzeige zieht am Ende von selbst nach, weil `full_refresh()`
        `state_changed` meldet.
        """

        if self._sync_thread is not None and self._sync_thread.is_alive():

            #
            # Zweimal drücken soll nicht zwei Durchgänge starten - der
            # zweite würde dieselben Anfragen doppelt stellen.
            #

            return

        self.manager.logger.info("Starte Synchronisationstest...")

        self.sync_button.setEnabled(False)

        self._sync_thread = threading.Thread(
            target=self._sync_worker,
            daemon=True,
            name="ConnectionsSyncTest",
        )

        self._sync_thread.start()

    def _sync_worker(self):

        try:

            self.manager.full_refresh()

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

            #
            # Über das Signal in den Hauptthread: run_auto_sync() legt
            # einen QTimer-gestützten Ablauf an, und ein QObject darf
            # nicht aus einem fremden Thread angestoßen werden.
            #

            self.syncRequested.emit()

        except Exception as exc:

            self.manager.logger.error(
                f"Synchronisationstest fehlgeschlagen: {exc}"
            )

        finally:

            self.syncFinished.emit()

    def _on_sync_requested(self):

        self.manager.run_auto_sync()

        self.manager.logger.success("Synchronisation angestoßen.")

    def _on_sync_finished(self):

        self.sync_button.setEnabled(True)
