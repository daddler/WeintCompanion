"""
WeintCompanion 2.0
Auswahlfeld

Ein `QComboBox` in der Form des Entwurfs: 36 px hoch, `radius.sm`,
eingelassene Fläche (`surface.sunken`), 1-px-Rahmen, im Fokus in
Akzentfarbe.

Eingabefelder sind neben dem Fenster selbst die **einzigen** Elemente,
die einen echten umlaufenden Rahmen behalten. Bei ihnen trägt er
Bedeutung ("hier kann ich etwas ändern") und grenzt nicht bloß ab -
genau der Unterschied, wegen dem Karten keinen mehr haben.

Das meiste davon steht schon im globalen Stylesheet. Diese Klasse
existiert für die zwei Dinge, die es nicht kann: den gemalten Pfeil
und - wichtiger - die Signaturprüfung beim Neufüllen.

**Warum die Signaturprüfung hier steht**: der Archiv-Auswahlkasten
hängt an `replayChanged` und wird bei laufender Wiedergabe vier Mal je
Sekunde aufgefordert, sich zu aktualisieren. Ein unbedingtes
`clear()` + `addItems()` schließt dabei jedes offene Aufklappmenü -
während der Wiedergabe ließ sich schlicht kein anderer Pull mehr
auswählen, weil die Liste viermal je Sekunde unter dem Mauszeiger
zuklappte. `set_items()` vergleicht deshalb zuerst und tut nichts,
wenn sich nichts geändert hat.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QComboBox

from gui.theme import tokens
from gui.theme.fonts import font


class Select(QComboBox):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setCursor(Qt.PointingHandCursor)

        self.setFont(font("small"))

        self.setFixedHeight(36)

        #
        # Ein sehr langer Berichtsname darf das Feld nicht über die
        # Spalte hinaus wachsen lassen.
        #

        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)

        self.setMinimumContentsLength(12)

    # --------------------------------------------------

    def set_items(self, items, current=None) -> bool:
        """
        Die Liste setzen - aber nur, wenn sie sich geändert hat.

        `items` ist eine Folge aus (Beschriftung, Wert). Gibt zurück,
        ob tatsächlich neu gefüllt wurde.
        """

        items = list(items)

        signature = [
            (str(label), value)
            for label, value in items
        ]

        existing = [
            (self.itemText(index), self.itemData(index))
            for index in range(self.count())
        ]

        if signature == existing:

            #
            # Nur die Auswahl nachziehen, ohne die Liste anzufassen.
            #

            if current is not None:
                self.select_value(current)

            return False

        blocked = self.blockSignals(True)

        self.clear()

        for label, value in items:

            self.addItem(str(label), value)

        if current is not None:
            self.select_value(current)

        self.blockSignals(blocked)

        return True

    def select_value(self, value) -> bool:

        index = self.findData(value)

        if index < 0:
            return False

        if index == self.currentIndex():
            return True

        blocked = self.blockSignals(True)

        self.setCurrentIndex(index)

        self.blockSignals(blocked)

        return True

    def value(self):

        return self.currentData()

    # --------------------------------------------------

    def paintEvent(self, event):

        super().paintEvent(event)

        #
        # Der Pfeil. Qt zeichnet an dieser Stelle sonst das Element
        # des Systemstils, das zwischen den dunklen Flächen wie ein
        # Fremdkörper wirkt - und dessen Farbe sich nicht aus dem
        # Theme setzen lässt.
        #

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        size = 4.0

        x = self.width() - 16

        y = self.height() / 2.0 - 1

        pen = QPen(
            QColor(
                tokens.TEXT["muted"]
                if self.isEnabled()
                else tokens.TEXT["faint"]
            ),
            1.4,
        )

        pen.setCapStyle(Qt.RoundCap)

        pen.setJoinStyle(Qt.RoundJoin)

        painter.setPen(pen)

        painter.setBrush(Qt.NoBrush)

        painter.drawPolyline(
            QPolygonF(
                [
                    QRectF(x - size, y - size / 2, 0, 0).topLeft(),
                    QRectF(x, y + size / 2, 0, 0).topLeft(),
                    QRectF(x + size, y - size / 2, 0, 0).topLeft(),
                ]
            )
        )
