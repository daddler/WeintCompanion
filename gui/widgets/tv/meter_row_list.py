"""
Liste aus Zeilen mit Balken.

Ein Baustein für drei sehr ähnliche Darstellungen in WeintTV:
Tank-Leben, Verbrauchsgüter und Cooldown-Restzeiten. Sie
unterscheiden sich nur in Beschriftung und Farbe, nicht im Aufbau -
also gibt es sie genau einmal und nicht dreimal.

Wie bei der RankingList werden die Zeilen einmal angelegt und danach
nur noch neu beschriftet.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.widgets.tv.meter_bar import MeterBar


@dataclass(frozen=True)
class MeterRowData:
    """
    Inhalt einer Zeile.

    `ratio` ist der Balkenwert von 0.0 bis 1.0, `color` leer bedeutet
    den Akzent-Farbverlauf des Designs.
    """

    title: str

    detail: str = ""

    value: str = ""

    ratio: float = 0.0

    color: str = ""


class _MeterRow(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(5)

        head = QHBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(8)

        self.title = QLabel("-")

        self.title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{Colors.TEXT};"
            "background:transparent;"
        )

        head.addWidget(self.title)

        self.detail = QLabel("")

        self.detail.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        head.addWidget(self.detail)

        head.addStretch()

        self.value = QLabel("")

        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.value.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;font-weight:700;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;"
        )

        head.addWidget(self.value)

        root.addLayout(head)

        self.bar = MeterBar(height=6)

        root.addWidget(self.bar)

    # --------------------------------------------------

    def apply(self, data: MeterRowData):

        self.title.setText(data.title)

        self.detail.setText(data.detail)

        self.detail.setVisible(bool(data.detail))

        self.value.setText(data.value)

        self.value.setVisible(bool(data.value))

        self.bar.setColor(data.color)

        self.bar.setValue(data.ratio)

        self.setVisible(True)


class MeterRowList(QWidget):
    """
    `capacity` legt fest, wie viele Zeilen höchstens dargestellt
    werden. Mehr Einträge werden abgeschnitten - eine Live-Ansicht
    soll nicht unbegrenzt wachsen.
    """

    def __init__(
        self,
        capacity: int = 6,
        placeholder: str = "Keine Daten.",
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        self._rows: list[_MeterRow] = []

        for _index in range(capacity):

            row = _MeterRow()

            row.setVisible(False)

            root.addWidget(row)

            self._rows.append(row)

        self.placeholder = QLabel(placeholder)

        self.placeholder.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        root.addWidget(self.placeholder)

    # --------------------------------------------------

    def setPlaceholder(self, text: str):
        """
        Der Text, der bei leerer Liste steht.

        Vergleicht vorher: `setText` prüft nicht selbst und stößt sonst
        bei jedem Bild ein Neuzeichnen an - dieselbe Falle wie bei
        `setStyleSheet` (siehe gui/theme/restyle.py), nur eine Ebene
        harmloser.
        """

        if text and text != self.placeholder.text():
            self.placeholder.setText(text)

    def setRows(self, rows):

        rows = list(rows)[: len(self._rows)]

        for index, row in enumerate(self._rows):

            if index < len(rows):

                row.apply(rows[index])

            else:

                row.setVisible(False)

        self.placeholder.setVisible(not rows)
