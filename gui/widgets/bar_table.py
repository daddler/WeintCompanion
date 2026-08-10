"""
WeintCompanion 2.0
Die Rangliste

25 `BarRow` untereinander, 2 px Abstand, darüber eine Kopfzeile aus
Rubrik und rechter Summe.

Das Bauprinzip ist dasselbe wie bei den Listen aus 1.7 und aus
demselben Grund: **die Zeilen werden einmal angelegt und danach nur
noch beschriftet.** Würde die Liste bei jedem Snapshot neu aufgebaut,
entstünde im Sekundentakt eine komplette Widget-Hierarchie - das
flackert sichtbar und belastet den Hauptthread ohne Not. Bei laufender
Wiedergabe kommt das vier Mal je Sekunde vor.

Neu gegenüber 1.7 ist nur, dass hier alle 25 Zeilen vorgehalten werden
statt fünf: dank der 24-px-Zeile passen sie, und eine Rangliste, die
nach dem fünften Platz aufhört, beantwortet die Frage "wo stehe ich"
für zwanzig von fünfundzwanzig Leuten gerade nicht.

**Umsortieren wird nicht animiert** (§6.2). Nur die Balkenbreite läuft.
Zeilen, die während eines Pulls ständig die Plätze tauschen, wären
sonst dauernd in Bewegung, und der Blick fände nichts wieder.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.bar_row import BarRow
from gui.widgets.eyebrow import eyebrow_label


ROW_GAP = 2

DEFAULT_ROWS = 25


def format_per_second(value: float) -> str:
    """
    Kennzahlen im Raid-Umfeld werden in Tausendern gelesen.
    """

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"{value / 1_000:.1f}k"

    return f"{value:.0f}"


class BarTable(QWidget):
    """
    Eine Rangliste mit Kopfzeile.
    """

    rowActivated = Signal(str)

    def __init__(
        self,
        title: str = "",
        rows: int = DEFAULT_ROWS,
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(ROW_GAP)

        #
        # Kopfzeile: Rubrik links, Summe rechts.
        #

        header = QHBoxLayout()

        header.setContentsMargins(tokens.SPACE[1], 0, tokens.SPACE[1], 4)

        header.setSpacing(tokens.SPACE[1])

        self.title = eyebrow_label(title)

        header.addWidget(self.title)

        header.addStretch(1)

        self.total = eyebrow_label("", tokens.TEXT["secondary"])

        header.addWidget(self.total)

        root.addLayout(header)

        self._rows: list[BarRow] = []

        for _ in range(rows):

            row = BarRow()

            row.setVisible(False)

            root.addWidget(row)

            self._rows.append(row)

        #
        # Platzhalter, solange keine Daten vorliegen. Ohne ihn wäre die
        # Liste bei "kein Kampf" komplett leer und wirkte defekt.
        #

        from PySide6.QtWidgets import QLabel

        self.placeholder = QLabel("Noch keine Kampfdaten.")

        self.placeholder.setFont(font("small"))

        restyle(
            self.placeholder,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        root.addWidget(self.placeholder)

        root.addStretch(1)

    # --------------------------------------------------

    def setTitle(self, text: str):

        self.title.setText(text)

    def setTotal(self, text: str):

        self.total.setText(text)

    # --------------------------------------------------

    def set_entries(
        self,
        entries,
        me: str = "",
        deaths: dict | None = None,
        animate: bool = True,
    ):
        """
        Die Liste beschriften.

        `entries` ist eine Folge von `MetricEntry`; `me` der Name der
        eigenen Zeile; `deaths` bildet Spielernamen auf den
        Todeszeitpunkt in Sekunden ab.
        """

        from gui.theme.wow_colors import class_color

        deaths = deaths or {}

        visible = list(entries)[: len(self._rows)]

        best = visible[0].value if visible else 0.0

        for index, row in enumerate(self._rows):

            if index >= len(visible):

                row.setVisible(False)

                continue

            entry = visible[index]

            actor = entry.actor

            row.set_row(
                rank=index + 1,
                name=actor.name,
                spec=actor.spec,
                value=format_per_second(entry.value),
                fraction=(entry.value / best) if best > 0 else 0.0,
                color=class_color(actor.class_name),
                is_self=bool(me) and actor.name == me,
                dead_at=deaths.get(actor.name),
                animate=animate,
            )

            row.setVisible(True)

        self.placeholder.setVisible(not visible)

    def clear(self):

        for row in self._rows:
            row.setVisible(False)

        self.placeholder.setVisible(True)
