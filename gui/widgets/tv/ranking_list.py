"""
Ranking-Liste für Schaden und Heilung.

Wichtig für ein Live-Dashboard: die Zeilen werden EINMAL angelegt
und danach nur noch beschriftet. Würde die Liste bei jedem Snapshot
neu aufgebaut, entstünde im Sekundentakt eine komplette
Widget-Hierarchie - das flackert sichtbar und belastet den
Hauptthread ohne Not.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from analyzer.models import MetricEntry

from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.theme.wow_colors import class_color

from gui.widgets.tv.meter_bar import MeterBar


def format_per_second(value: float) -> str:
    """
    Kennzahlen im Raid-Umfeld werden in Tausendern gelesen.
    """

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"{value / 1_000:.1f}k"

    return f"{value:.0f}"


class _RankingRow(QWidget):
    """
    Eine Zeile: Platz, Name, Wert und darunter der Anteilsbalken.
    """

    def __init__(self, position: int, parent=None):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(5)

        head = QHBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(10)

        self.position = QLabel(f"{position}")

        self.position.setFixedWidth(18)

        self.position.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        head.addWidget(self.position)

        self.name = QLabel("-")

        self.name.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{Colors.TEXT};"
            "background:transparent;"
        )

        head.addWidget(self.name)

        self.spec = QLabel("")

        self.spec.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        head.addWidget(self.spec)

        head.addStretch()

        self.value = QLabel("-")

        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.value.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:12px;font-weight:700;color:{Colors.WHITE};"
            "background:transparent;"
        )

        head.addWidget(self.value)

        root.addLayout(head)

        self.bar = MeterBar(height=4)

        root.addWidget(self.bar)

    # --------------------------------------------------

    def apply(self, entry: MetricEntry, best: float):

        color = class_color(entry.actor.class_name)

        self.name.setText(entry.actor.name)

        #
        # restyle() statt setStyleSheet(): die Klassenfarbe eines
        # Platzes wechselt nur, wenn dort jemand anders steht (siehe
        # gui/theme/restyle.py).
        #

        restyle(
            self.name,
            f"font-size:13px;font-weight:600;color:{color};"
            "background:transparent;",
        )

        self.spec.setText(entry.actor.spec)

        self.value.setText(format_per_second(entry.value))

        self.bar.setColor(color)

        self.bar.setValue(
            entry.value / best
            if best > 0
            else 0.0
        )

        self.setVisible(True)

    def clear(self):

        self.setVisible(False)


class RankingList(QWidget):
    """
    Zeigt die besten `limit` Einträge einer Kennzahl.
    """

    def __init__(self, limit: int = 5, parent=None):

        super().__init__(parent)

        self._limit = limit

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        self._rows: list[_RankingRow] = []

        for position in range(1, limit + 1):

            row = _RankingRow(position)

            row.setVisible(False)

            root.addWidget(row)

            self._rows.append(row)

        #
        # Platzhalter, solange keine Daten vorliegen. Ohne ihn wäre
        # die Karte bei "kein Kampf" komplett leer und wirkte defekt.
        #

        self.placeholder = QLabel("Noch keine Kampfdaten.")

        self.placeholder.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;"
        )

        root.addWidget(self.placeholder)

        root.addStretch()

    # --------------------------------------------------

    def setEntries(self, entries: tuple[MetricEntry, ...]):

        visible = entries[: self._limit]

        best = visible[0].value if visible else 0.0

        for index, row in enumerate(self._rows):

            if index < len(visible):

                row.apply(visible[index], best)

            else:

                row.clear()

        self.placeholder.setVisible(not visible)
