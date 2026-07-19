from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.logger import LogEntry
from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.card import Card
from gui.widgets.hero_banner import HeroButton


MAX_ROWS = 16

LEVEL_STYLE = {

    "success": ("✓", Colors.SUCCESS, "rgba(124,192,110,18)"),
    "warning": ("▲", Colors.WARNING, "rgba(212,162,74,18)"),
    "error": ("✕", Colors.ERROR, "rgba(229,107,107,18)"),
    "info": ("i", Colors.DISCORD, "rgba(139,149,245,18)"),
}


class _ActivityBridge(QObject):
    new_entry = Signal(object)


class _ActivityRow(QFrame):

    def __init__(self, entry: LogEntry):

        super().__init__()

        glyph, color, bg = LEVEL_STYLE.get(
            entry.level,
            LEVEL_STYLE["info"],
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        chip = QLabel(glyph)

        chip.setFixedSize(28, 28)

        chip.setAlignment(Qt.AlignCenter)

        chip.setStyleSheet(f"""
        QLabel{{
            background:{bg};
            color:{color};
            border-radius:8px;
            font-size:12px;
            font-weight:700;
        }}
        """)

        layout.addWidget(chip)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        message = QLabel(entry.message)

        message.setWordWrap(True)

        message.setStyleSheet(
            f"color:{Colors.TEXT};font-size:13px;"
        )

        text_col.addWidget(message)

        timestamp = QLabel(
            entry.timestamp.strftime("%H:%M:%S")
        )

        timestamp.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_MUTED};"
        )

        text_col.addWidget(timestamp)

        layout.addLayout(text_col, 1)


class ActivityPanel(QWidget):
    """
    Rechte Spalte des Dashboards - Live-Feed der letzten Ereignisse,
    siehe "Activity"-Panel im Design.
    """

    openLogsRequested = Signal()

    def __init__(self, logger):

        super().__init__()

        self.logger = logger

        self.setFixedWidth(Metrics.ACTIVITY_PANEL_WIDTH)

        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.card = Card()

        root.addWidget(self.card)

        #
        # Header
        #

        header = QHBoxLayout()

        title = QLabel("Activity")

        title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{Colors.WHITE};"
        )

        header.addWidget(title)

        header.addStretch()

        live = QLabel("● LIVE")

        live.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.SUCCESS};"
        )

        header.addWidget(live)

        self.card.addLayout(header)

        #
        # Feed
        #

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QWidget{background:transparent;}"
        )

        self.feed_container = QWidget()

        self.feed_layout = QVBoxLayout(self.feed_container)

        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(0)

        self.feed_layout.addStretch()

        scroll.setWidget(self.feed_container)

        self.card.addWidget(scroll)

        #
        # Footer
        #

        self.open_logs_button = HeroButton(
            "Vollständige Logs öffnen →",
            primary=False,
        )

        self.open_logs_button.clicked.connect(
            self.openLogsRequested.emit
        )

        self.card.addWidget(self.open_logs_button)

        #
        # Thread-sichere Anbindung an den Logger
        #

        self._bridge = _ActivityBridge(self)
        self._bridge.new_entry.connect(self._add_entry)

        self.refresh()

        self.logger.subscribe(
            self._bridge.new_entry.emit
        )

    # --------------------------------------------------

    def refresh(self):

        while self.feed_layout.count() > 1:

            item = self.feed_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        for entry in self.logger.entries()[-MAX_ROWS:][::-1]:

            self._insert_row(entry)

    def _add_entry(self, entry: LogEntry):

        self._insert_row(entry)

        while self.feed_layout.count() - 1 > MAX_ROWS:

            item = self.feed_layout.takeAt(
                self.feed_layout.count() - 2
            )

            if item.widget():
                item.widget().deleteLater()

    def _insert_row(self, entry: LogEntry):

        row = _ActivityRow(entry)

        self.feed_layout.insertWidget(0, row)

        separator = QFrame()

        separator.setFixedHeight(1)

        separator.setStyleSheet(
            f"background:{Colors.BORDER};"
        )

        self.feed_layout.insertWidget(1, separator)

    # --------------------------------------------------

    def closeEvent(self, event):

        self.logger.unsubscribe(
            self._bridge.new_entry.emit
        )

        super().closeEvent(event)
