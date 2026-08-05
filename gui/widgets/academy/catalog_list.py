"""
Katalogliste mit An-/Abwahl je Lektion.

Der Katalog war bisher eine reine Anzeige. Jetzt entscheidet er, was
im Trainingsplan überhaupt auftauchen darf - deshalb braucht jede
Zeile einen Schalter.

Standardmäßig ist alles an. Das ist keine Bequemlichkeit, sondern
folgt der Speicherung: der Dienst merkt sich die **abgewählten**
Lektionen, nicht die gewählten. Dadurch ist eine neu hinzugefügte
Lektion für alle sofort aktiv, ohne Migration bestehender Dateien.

Aufbau wie bei allen Listen dieses Projekts: Zeilen einmal anlegen,
danach nur noch neu beschriften.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.widgets.toggle_switch import ToggleSwitch


#
# Farbe des Statuspunkts je Prüfergebnis.
#

STATUS_COLORS = {
    "passed": Colors.SUCCESS,
    "failed": Colors.ERROR,
    "unknown": Colors.TEXT_FAINT,
}


@dataclass(frozen=True)
class CatalogRowData:
    """
    Eine Katalogzeile.

    `status` ist das Prüfergebnis aus dem gewählten Log, `completed`
    der selbst gesetzte Haken - beides nur als Anzeige, geschaltet
    wird ausschließlich `active`.
    """

    lesson_id: str

    title: str

    detail: str = ""

    active: bool = True

    completed: bool = False

    status: str = "unknown"


class _CatalogRow(QWidget):

    activeChanged = Signal(str, bool)

    def __init__(self, parent=None):

        super().__init__(parent)

        self._lesson_id = ""

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 4, 0, 4)

        root.setSpacing(10)

        #
        # Statuspunkt - dasselbe Vokabular wie in der EntryList.
        #

        self.dot = QLabel("●")

        self.dot.setFixedWidth(12)

        self.dot.setAlignment(Qt.AlignTop)

        root.addWidget(self.dot)

        text_col = QVBoxLayout()

        text_col.setSpacing(2)

        self.title = QLabel("")

        self.title.setWordWrap(True)

        text_col.addWidget(self.title)

        self.detail = QLabel("")

        self.detail.setWordWrap(True)

        self.detail.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        text_col.addWidget(self.detail)

        root.addLayout(text_col, 1)

        self.toggle = ToggleSwitch(True)

        self.toggle.toggled.connect(self._on_toggled)

        root.addWidget(self.toggle)

    # --------------------------------------------------

    def _on_toggled(self, checked: bool):

        if self._lesson_id:

            self.activeChanged.emit(self._lesson_id, checked)

    def apply(self, data: CatalogRowData):

        self._lesson_id = data.lesson_id

        self.title.setText(data.title)

        #
        # Abgewählte Lektionen bleiben lesbar, treten aber deutlich
        # zurück - sonst sähe eine halb abgewählte Liste aus wie ein
        # Darstellungsfehler.
        #

        restyle(
            self.title,
            "font-size:13px;font-weight:600;"
            f"color:{Colors.TEXT if data.active else Colors.TEXT_FAINT};"
            "background:transparent;border:none;",
        )

        self.detail.setText(data.detail)

        self.detail.setVisible(bool(data.detail))

        restyle(
            self.dot,
            f"color:{STATUS_COLORS.get(data.status, Colors.TEXT_FAINT)};"
            "font-size:10px;background:transparent;border:none;",
        )

        self.toggle.blockSignals(True)

        self.toggle.setChecked(data.active)

        self.toggle.blockSignals(False)

        self.setVisible(True)


class CatalogList(QWidget):

    #
    # (lesson_id, aktiv)
    #

    activeChanged = Signal(str, bool)

    def __init__(
        self,
        capacity: int = 12,
        placeholder: str = "Keine Lektionen in diesem Bereich.",
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(2)

        self._rows: list[_CatalogRow] = []

        for _index in range(max(1, capacity)):

            row = _CatalogRow()

            row.setVisible(False)

            row.activeChanged.connect(self.activeChanged)

            root.addWidget(row)

            self._rows.append(row)

        self.placeholder = QLabel(placeholder)

        self.placeholder.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        root.addWidget(self.placeholder)

    # --------------------------------------------------

    def setRows(self, rows):

        rows = tuple(rows)[: len(self._rows)]

        for index, row in enumerate(self._rows):

            if index < len(rows):
                row.apply(rows[index])
            else:
                row.setVisible(False)

        self.placeholder.setVisible(not rows)
