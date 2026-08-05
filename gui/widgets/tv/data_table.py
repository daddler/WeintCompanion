"""
Tabelle mit festen Spalten.

Die Tiefenauswertung braucht Darstellungen, für die weder RankingList
(Rang + Name + ein Wert) noch MeterRowList (Titel + ein Balken)
reichen: erhaltener Schaden mit Gesamt, Vermeidbarem und Anteil,
Cooldown-Nutzung mit Einsätzen, möglichen Einsätzen und Zeitpunkten.
Das sind echte Tabellen.

Bewusst kein QTableWidget: das bringt eigene Kopfzeilen, eigene
Auswahl und eigenes Scrollen mit, kämpft gegen die globale Regel
`QWidget { background: transparent; }` und müsste vollständig
umgestylt werden. Stattdessen dasselbe Muster wie bei allen anderen
Listen dieses Pakets - ein QGridLayout mit einmal angelegten Zeilen,
die nur noch neu beschriftet werden. Das hält das Neuzeichnen im
Sekundentakt flackerfrei.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.tv.meter_bar import MeterBar


#
# Farben je Stufe - dasselbe Vokabular wie in EntryList und im Logger,
# damit eine Warnung überall gleich aussieht.
#

LEVEL_COLORS = {
    "info": Colors.TEXT_SECONDARY,
    "success": Colors.SUCCESS,
    "warning": Colors.WARNING,
    "error": Colors.ERROR,
}


@dataclass(frozen=True)
class TableColumn:
    """
    Eine Spalte.

    `weight` steuert, wie sich überschüssige Breite verteilt - die
    Namensspalte soll wachsen, eine Zahlenspalte nicht.
    """

    title: str

    weight: int = 0

    align: str = "left"

    mono: bool = False


@dataclass(frozen=True)
class TableCell:
    """
    Eine Zelle.

    `ratio` ab 0.0 zeichnet zusätzlich einen schmalen Balken unter den
    Text - damit lässt sich ein Anteil zeigen, ohne eine eigene
    Spalte dafür zu opfern. -1.0 bedeutet "kein Balken".
    """

    text: str = ""

    color: str = ""

    ratio: float = -1.0


@dataclass(frozen=True)
class TableRowData:
    """
    Eine Zeile.

    `key` ist der Spielername und damit der Griff für die Verzahnung
    mit der Academy: ein Klick auf die Zeile soll genau diesen
    Spieler dort öffnen können.
    """

    cells: tuple[TableCell, ...] = ()

    key: str = ""

    level: str = "info"


class _Cell(QWidget):
    """
    Eine Zelle mit optionalem Balken darunter.
    """

    def __init__(self, column: TableColumn, parent=None):

        super().__init__(parent)

        self._column = column

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(3)

        self.label = QLabel("")

        alignment = Qt.AlignVCenter | (
            Qt.AlignRight
            if column.align == "right"
            else Qt.AlignLeft
        )

        self.label.setAlignment(alignment)

        root.addWidget(self.label)

        self.bar = MeterBar(height=3)

        self.bar.setVisible(False)

        root.addWidget(self.bar)

        self._base_style = (
            ('font-family:"JetBrains Mono";' if column.mono else "")
            + "font-size:12px;"
            + ("font-weight:600;" if column.mono else "")
            + "background:transparent;border:none;"
        )

        self.apply(TableCell())

    def apply(self, cell: TableCell):

        self.label.setText(cell.text)

        #
        # restyle() statt setStyleSheet(): der Text einer Zelle
        # ändert sich im Takt, ihre Farbe fast nie. Qt prüft das
        # nicht selbst und würde bei jedem Bild neu parsen und
        # polishen (siehe gui/theme/restyle.py).
        #

        restyle(
            self.label,
            self._base_style
            + f"color:{cell.color or Colors.TEXT_SECONDARY};",
        )

        show_bar = cell.ratio >= 0.0

        self.bar.setVisible(show_bar)

        if show_bar:

            self.bar.setColor(cell.color)

            self.bar.setValue(cell.ratio)


class _Row(QWidget):
    """
    Eine anklickbare Zeile.

    Eigener Hintergrund heißt: objectName + WA_StyledBackground + eine
    auf die ID bezogene Regel. Ohne das würde die globale
    Transparenz-Regel des Stylesheets jede Einfärbung schlucken.
    """

    clicked = Signal(str)

    def __init__(self, columns: tuple[TableColumn, ...], parent=None):

        super().__init__(parent)

        self.setObjectName("dataTableRow")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(
            "#dataTableRow { background: transparent; border: none; "
            "border-radius: 6px; }"
            "#dataTableRow:hover { background: " + Colors.SURFACE_LIGHT + "; }"
        )

        self._key = ""

        root = QHBoxLayout(self)

        root.setContentsMargins(8, 6, 8, 6)

        root.setSpacing(12)

        self.cells: list[_Cell] = []

        for column in columns:

            cell = _Cell(column)

            root.addWidget(cell, max(0, column.weight))

            self.cells.append(cell)

    # --------------------------------------------------

    def apply(self, data: TableRowData):

        self._key = data.key

        self.setCursor(
            Qt.PointingHandCursor
            if data.key
            else Qt.ArrowCursor
        )

        for index, cell in enumerate(self.cells):

            cell.apply(
                data.cells[index]
                if index < len(data.cells)
                else TableCell()
            )

        self.setVisible(True)

    def mouseReleaseEvent(self, event):

        if self._key and event.button() == Qt.LeftButton:

            self.clicked.emit(self._key)

        super().mouseReleaseEvent(event)


class DataTable(QWidget):
    """
    `capacity` begrenzt die Zeilenzahl. Ein Raid hat 25 Spieler, eine
    Aufschlüsselung nach Fähigkeit schnell ein Vielfaches davon - eine
    Karte in einer Übersicht soll trotzdem nicht endlos wachsen.
    """

    rowActivated = Signal(str)

    def __init__(
        self,
        columns: tuple[TableColumn, ...],
        capacity: int = 12,
        placeholder: str = "Keine Daten.",
        parent=None,
    ):

        super().__init__(parent)

        self._columns = tuple(columns)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(2)

        #
        # Kopfzeile. Die Beschriftungen entstehen über eyebrow_label(),
        # weil bei zehn Pixeln Schriftgröße sonst die Punkte auf
        # Großbuchstaben-Umlauten abgeschnitten werden ("FÄHIGKEIT"
        # würde als "FAHIGKEIT" erscheinen).
        #

        header = QWidget()

        header_layout = QHBoxLayout(header)

        header_layout.setContentsMargins(8, 0, 8, 4)

        header_layout.setSpacing(12)

        for column in self._columns:

            label = eyebrow_label(column.title.upper())

            label.setAlignment(
                Qt.AlignVCenter | (
                    Qt.AlignRight
                    if column.align == "right"
                    else Qt.AlignLeft
                )
            )

            header_layout.addWidget(label, max(0, column.weight))

        root.addWidget(header)

        self._rows: list[_Row] = []

        for _index in range(max(1, capacity)):

            row = _Row(self._columns)

            row.setVisible(False)

            row.clicked.connect(self.rowActivated)

            root.addWidget(row)

            self._rows.append(row)

        self.placeholder = QLabel(placeholder)

        self.placeholder.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        root.addWidget(self.placeholder)

    # --------------------------------------------------

    def setPlaceholder(self, text: str):
        """
        Wie bei MeterRowList: nur setzen, wenn er sich geändert hat.
        """

        if text and text != self.placeholder.text():
            self.placeholder.setText(text)

    def setRows(self, rows):

        rows = tuple(rows)[: len(self._rows)]

        for index, row in enumerate(self._rows):

            if index < len(rows):
                row.apply(rows[index])
            else:
                row.setVisible(False)

        self.placeholder.setVisible(not rows)

    def clear(self):

        self.setRows(())
