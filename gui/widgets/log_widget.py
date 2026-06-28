from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
)

from core.logger import LogEntry


class LogWidget(QListWidget):

    MAX_ENTRIES = 250

    def __init__(self, logger):
        super().__init__()

        self.logger = logger

        self.setAlternatingRowColors(False)

        self.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.setFocusPolicy(Qt.NoFocus)

        #
        # Bestehende History laden
        #

        self.refresh()

        #
        # Logger abonnieren
        #

        self.logger.subscribe(
            self.add_entry
        )

    # --------------------------------------------------

    def refresh(self):

        self.clear()

        for entry in self.logger.entries():

            self.add_entry(entry)

    # --------------------------------------------------

    def add_entry(self, entry: LogEntry):

        time = entry.timestamp.strftime("%H:%M:%S")

        icons = {
            "info": "ℹ️",
            "success": "🟢",
            "warning": "🟡",
            "error": "🔴",
        }

        colors = {
            "info": QColor("#D8D8D8"),
            "success": QColor("#7ED957"),
            "warning": QColor("#DDB94D"),
            "error": QColor("#E65A5A"),
        }

        icon = icons.get(entry.level, "•")

        item = QListWidgetItem(
            f"{time}    {icon}    {entry.message}"
        )

        item.setForeground(
            colors.get(
                entry.level,
                QColor("white"),
            )
        )

        self.addItem(item)

        self.scrollToBottom()

        #
        # Maximalgröße
        #

        while self.count() > self.MAX_ENTRIES:

            self.takeItem(0)

    # --------------------------------------------------

    def closeEvent(self, event):

        self.logger.unsubscribe(
            self.add_entry
        )

        super().closeEvent(event)