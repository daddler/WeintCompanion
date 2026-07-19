from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractItemView,
)

from core.logger import LogEntry
from gui.theme.colors import Colors


class _LogBridge(QObject):
    new_entry = Signal(object)


CARD_RADIUS = 12

LEVEL_TAGS = {

    "info": ("INFO", Colors.DISCORD),
    "success": ("SUCCESS", Colors.SUCCESS),
    "warning": ("WARN", Colors.WARNING),
    "error": ("ERROR", Colors.ERROR),
}


class LogWidget(QWidget):

    MAX_ENTRIES = 250

    def __init__(self, logger):

        super().__init__()

        self.logger = logger

        self._level_filter = None
        self._text_filter = ""

        #
        # Root
        #

        root = QVBoxLayout(self)

        root.setContentsMargins(20, 18, 20, 18)

        root.setSpacing(12)

        self.setObjectName("logWidget")

        self.setStyleSheet(f"""
        QWidget#logWidget{{
            background:{Colors.CARD};
            border:1px solid {Colors.BORDER};
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        #
        # Header
        #

        header = QHBoxLayout()

        header.setSpacing(10)

        root.addLayout(header)

        self.title = QLabel("Live-Protokoll")

        self.title.setStyleSheet(f"""
        QLabel{{
            color:{Colors.WHITE};
            font-size:14px;
            font-weight:600;
            background:transparent;
        }}
        """)

        header.addWidget(self.title)

        header.addStretch()

        self.live = QLabel("● LIVE")

        self.live.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.SUCCESS};"
        )

        header.addWidget(self.live)

        #
        # Log Liste
        #

        self.list = QListWidget()

        self.list.setAlternatingRowColors(False)

        self.list.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.list.setFocusPolicy(Qt.NoFocus)

        self.list.setFrameShape(QListWidget.NoFrame)

        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.list.setStyleSheet(f"""
        QListWidget{{
            background:transparent;
            border:none;
            color:{Colors.TEXT};
            outline:none;
            font-family:"JetBrains Mono";
            font-size:12.5px;
        }}
        QListWidget::item{{
            padding:6px 4px;
            border-bottom:1px solid {Colors.BORDER};
        }}
        QListWidget::item:last{{
            border:none;
        }}
        """)

        root.addWidget(self.list, 1)

        #
        # Thread-sicherer Bridge für Logger-Events
        #

        self._bridge = _LogBridge(self)
        self._bridge.new_entry.connect(self._on_new_entry)

        #
        # History laden
        #

        self.refresh()

        #
        # Logger abonnieren (thread-sicher via Signal)
        #

        self.logger.subscribe(
            self._bridge.new_entry.emit
        )

    # --------------------------------------------------
    # Refresh
    # --------------------------------------------------

    def refresh(self):

        self._rebuild()

    def _rebuild(self):

        self.list.clear()

        for entry in self.logger.entries():

            if self._matches(entry):

                self._append_item(entry)

        self.list.scrollToBottom()

    def _matches(self, entry: LogEntry) -> bool:

        if (
            self._level_filter is not None
            and entry.level != self._level_filter
        ):
            return False

        if (
            self._text_filter
            and self._text_filter.lower() not in entry.message.lower()
        ):
            return False

        return True

    # --------------------------------------------------
    # Filter
    # --------------------------------------------------

    def set_level_filter(self, level: str | None):

        self._level_filter = level

        self._rebuild()

    def set_text_filter(self, text: str):

        self._text_filter = text

        self._rebuild()

    # --------------------------------------------------
    # Add Entry (immer im Hauptthread via Bridge)
    # --------------------------------------------------

    def _on_new_entry(self, entry: LogEntry):

        if not self._matches(entry):
            return

        self._append_item(entry)

        self.list.scrollToBottom()

        while self.list.count() > self.MAX_ENTRIES:

            self.list.takeItem(0)

    def _append_item(self, entry: LogEntry):

        timestamp = entry.timestamp.strftime("%H:%M:%S")

        tag, color = LEVEL_TAGS.get(
            entry.level,
            ("INFO", Colors.TEXT_SECONDARY),
        )

        item = QListWidgetItem(
            f"{timestamp}  {tag:<8}{entry.message}"
        )

        item.setForeground(QColor(color))

        self.list.addItem(item)

    # --------------------------------------------------
    # Clear
    # --------------------------------------------------

    def clear(self):
        self.list.clear()

    # --------------------------------------------------
    # Live Badge
    # --------------------------------------------------

    def set_live(self, active: bool = True):

        if active:

            self.live.setText("● LIVE")

            self.live.setStyleSheet(
                'font-family:"JetBrains Mono";'
                f"font-size:10px;color:{Colors.SUCCESS};"
            )

        else:

            self.live.setText("● PAUSIERT")

            self.live.setStyleSheet(
                'font-family:"JetBrains Mono";'
                f"font-size:10px;color:{Colors.WARNING};"
            )

    # --------------------------------------------------
    # Scroll
    # --------------------------------------------------

    def scroll_to_bottom(self):
        self.list.scrollToBottom()

    # --------------------------------------------------
    # Logger trennen
    # --------------------------------------------------

    def closeEvent(self, event):

        self.logger.unsubscribe(
            self._bridge.new_entry.emit
        )

        super().closeEvent(event)
