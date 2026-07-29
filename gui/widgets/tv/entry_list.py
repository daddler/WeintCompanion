"""
Einfache Liste aus farbig markierten Einträgen.

Benutzt für Mechanikfehler, Warnungen und die Pull-Historie. Der
farbige Punkt links übernimmt dieselbe Rolle wie die Stufenfarben
im Log-Widget: er macht die Dringlichkeit erkennbar, bevor man den
Text gelesen hat.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors


#
# Stufen wie beim Logger, damit dieselben Begriffe dieselbe Farbe
# ergeben - egal ob im Log oder in WeintTV.
#

LEVEL_COLORS: dict[str, str] = {

    "info": Colors.INFO,
    "success": Colors.SUCCESS,
    "warning": Colors.WARNING,
    "error": Colors.ERROR,

}


@dataclass(frozen=True)
class EntryData:

    title: str

    detail: str = ""

    level: str = "info"

    trailing: str = ""


class _Entry(QWidget):

    DOT_SIZE = 8

    def __init__(self, parent=None):

        super().__init__(parent)

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(10)

        self.dot = QLabel()

        self.dot.setFixedSize(self.DOT_SIZE, self.DOT_SIZE)

        root.addWidget(self.dot, alignment=Qt.AlignTop)

        #
        # Der Punkt sitzt optisch besser, wenn er auf Höhe der ersten
        # Textzeile liegt statt an deren Oberkante.
        #

        self.dot.setContentsMargins(0, 0, 0, 0)

        text_col = QVBoxLayout()

        text_col.setContentsMargins(0, 0, 0, 0)

        text_col.setSpacing(2)

        self.title = QLabel("-")

        self.title.setWordWrap(True)

        self.title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{Colors.TEXT};"
            "background:transparent;"
        )

        text_col.addWidget(self.title)

        self.detail = QLabel("")

        self.detail.setWordWrap(True)

        self.detail.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        text_col.addWidget(self.detail)

        root.addLayout(text_col, 1)

        self.trailing = QLabel("")

        self.trailing.setAlignment(Qt.AlignRight | Qt.AlignTop)

        self.trailing.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;"
        )

        root.addWidget(self.trailing)

    # --------------------------------------------------

    def apply(self, data: EntryData):

        color = LEVEL_COLORS.get(data.level, Colors.INFO)

        self.dot.setStyleSheet(f"""
        QLabel{{
            background:{color};
            border-radius:{self.DOT_SIZE // 2}px;
        }}
        """)

        self.title.setText(data.title)

        self.detail.setText(data.detail)

        self.detail.setVisible(bool(data.detail))

        self.trailing.setText(data.trailing)

        self.trailing.setVisible(bool(data.trailing))

        self.setVisible(True)


class EntryList(QWidget):

    def __init__(
        self,
        capacity: int = 8,
        placeholder: str = "Nichts zu melden.",
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        self._entries: list[_Entry] = []

        for _index in range(capacity):

            entry = _Entry()

            entry.setVisible(False)

            root.addWidget(entry)

            self._entries.append(entry)

        self.placeholder = QLabel(placeholder)

        self.placeholder.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        root.addWidget(self.placeholder)

    # --------------------------------------------------

    def setEntries(self, entries):

        entries = list(entries)[: len(self._entries)]

        for index, widget in enumerate(self._entries):

            if index < len(entries):

                widget.apply(entries[index])

            else:

                widget.setVisible(False)

        self.placeholder.setVisible(not entries)
