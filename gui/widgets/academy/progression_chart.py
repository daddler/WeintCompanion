"""
Die Lernkurve als Bild.

Zwei Polylinien über die letzten Pulls, wie im Entwurf (§6.3): die
**Gesamtbewertung** durchgezogen in Akzentfarbe, ein einzelner
**Bereich** gestrichelt in `state.info`, dahinter drei waagerechte
Hilfslinien.

Drei Entscheidungen, die nicht Geschmack sind:

- **Die Achse steht fest von 0 bis `MAX_STARS`.** Mit einer Skala,
  die sich an die Werte anpasst, sähe eine Kurve, die zwischen 4,1
  und 4,3 pendelt, genauso dramatisch aus wie eine von 1 auf 5 - und
  das ist bei einer Lernkurve die eine Aussage, auf die es ankommt.
  Deshalb auch die Hilfslinien bei 1, 3 und 5: sie geben der Fläche
  einen Massstab, ohne eine Achsenbeschriftung zu behaupten.
- **Die Farbe wird im `paintEvent` gelesen**, nie im Konstruktor. Ein
  im Konstruktor eingefrorener Akzent überlebt jeden Wechsel, und
  zwar lautlos (siehe CLAUDE.md).
- **Verbunden wird ein gebundener Slot, keine Lambda.** Der
  ThemeManager ist ein Singleton und lebt so lange wie das Programm;
  eine Lambda darin hielte dieses Widget für immer fest.

Was hier **nicht** gezeichnet wird, ist ein Punkt für einen Pull ohne
Bewertung. Solche Pulls kommen gar nicht erst an (siehe
`analyzer/academy/progression.py`) - eine Lücke als Null zu zeichnen
wäre von einem eingebrochenen Ergebnis nicht zu unterscheiden.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from analyzer.academy.models import MAX_STARS

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.theme_manager import theme


#
# Innenabstand. Oben etwas mehr, weil die Linie bei fünf Sternen sonst
# am Rand klebt, unten Platz für die beiden Datumsangaben.
#

PAD_LEFT = 8

PAD_RIGHT = 12

PAD_TOP = 12

PAD_BOTTOM = 22


#
# Wo die Hilfslinien liegen. Drei, nicht fünf: sie sollen den Blick
# einordnen und nicht das Bild in ein Raster zerlegen.
#

GUIDES = (1, 3, 5)


class ProgressionChart(QWidget):

    def __init__(self, height: int = 150, parent=None):

        super().__init__(parent)

        self.setMinimumHeight(height)

        self._overall: tuple[float, ...] = ()

        self._area: tuple[float, ...] = ()

        self._first_label = ""

        self._last_label = ""

        #
        # Gebundener Slot, keine Lambda - siehe Modulkopf.
        #

        theme().accent_changed.connect(self.update)

    # --------------------------------------------------

    def setSeries(
        self,
        overall,
        area=(),
        first_label: str = "",
        last_label: str = "",
    ):
        """
        Die beiden Linien setzen. `area` darf leer sein - dann steht
        nur die Gesamtlinie da, was der Normalfall ist, solange ein
        Bereich zu wenige Punkte hat.
        """

        overall = tuple(float(value) for value in overall or ())

        area = tuple(float(value) for value in area or ())

        unveraendert = (
            overall == self._overall
            and area == self._area
            and first_label == self._first_label
            and last_label == self._last_label
        )

        if unveraendert:
            return

        self._overall = overall

        self._area = area

        self._first_label = first_label

        self._last_label = last_label

        self.update()

    # --------------------------------------------------

    def _points(self, values, rect_left, rect_top, width, height):
        """
        Werte in Bildpunkte umrechnen.

        Ein einzelner Wert wird in die Mitte gesetzt statt an den
        linken Rand: eine Linie aus einem Punkt gibt es nicht, aber
        der Punkt selbst soll zu sehen sein.
        """

        if not values:
            return []

        if len(values) == 1:

            return [
                QPointF(
                    rect_left + width / 2,
                    rect_top + height * (1 - values[0] / MAX_STARS),
                )
            ]

        schritt = width / (len(values) - 1)

        return [
            QPointF(
                rect_left + index * schritt,
                rect_top + height * (
                    1 - max(0.0, min(float(MAX_STARS), value)) / MAX_STARS
                ),
            )
            for index, value in enumerate(values)
        ]

    def paintEvent(self, event):

        if not self._overall:
            return

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        left = PAD_LEFT

        top = PAD_TOP

        width = max(1.0, self.width() - PAD_LEFT - PAD_RIGHT)

        height = max(1.0, self.height() - PAD_TOP - PAD_BOTTOM)

        #
        # Hilfslinien
        #

        painter.setPen(QPen(QColor(tokens.BORDER["base"]), 1))

        for stars in GUIDES:

            y = top + height * (1 - stars / MAX_STARS)

            painter.drawLine(
                QPointF(left, y),
                QPointF(left + width, y),
            )

        #
        # Der Bereich zuerst, damit die Gesamtlinie darüber liegt -
        # sie ist die Hauptaussage.
        #

        if len(self._area) > 1:

            stift = QPen(QColor(tokens.STATE["info"]), 2)

            stift.setStyle(Qt.DashLine)

            stift.setCapStyle(Qt.RoundCap)

            painter.setPen(stift)

            painter.drawPolyline(
                QPolygonF(
                    self._points(self._area, left, top, width, height)
                )
            )

        #
        # Die Gesamtlinie - Akzentfarbe, **hier** gelesen.
        #

        akzent = QColor(theme().accent_base())

        punkte = self._points(self._overall, left, top, width, height)

        if len(punkte) > 1:

            stift = QPen(akzent, 2)

            stift.setCapStyle(Qt.RoundCap)

            stift.setJoinStyle(Qt.RoundJoin)

            painter.setPen(stift)

            painter.drawPolyline(QPolygonF(punkte))

        #
        # Der letzte Wert bekommt einen Punkt: er ist der aktuelle
        # Stand, und der ist die Zahl, neben der die Kurve steht.
        #

        painter.setPen(Qt.NoPen)

        painter.setBrush(akzent)

        painter.drawEllipse(punkte[-1], 3.5, 3.5)

        painter.setBrush(Qt.NoBrush)

        #
        # Die beiden Tage. Sie stehen unter den Enden der Kurve und
        # bleiben weg, wenn sie unbekannt sind - ein erfundenes Datum
        # wäre von einem gemessenen nicht zu unterscheiden.
        #

        painter.setFont(font("mono"))

        painter.setPen(QColor(tokens.TEXT["muted"]))

        boden = self.height() - 6

        if self._first_label:

            painter.drawText(
                int(left),
                int(boden),
                self._first_label,
            )

        if self._last_label and self._last_label != self._first_label:

            breite = painter.fontMetrics().horizontalAdvance(
                self._last_label
            )

            painter.drawText(
                int(left + width - breite),
                int(boden),
                self._last_label,
            )

        painter.end()
