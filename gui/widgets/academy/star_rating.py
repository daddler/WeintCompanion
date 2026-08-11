"""
Sternebewertung (★★★☆☆) mit ihrem dritten Zustand.

Selbst gezeichnet statt als Text mit Unicode-Sternen: welche
Schriftart welches Sternzeichen wie breit rendert, ist zwischen
Linux und Windows unterschiedlich, und die Farbe ließe sich pro
Stern nicht sauber trennen. Ein gezeichneter Stern sieht überall
gleich aus und nimmt die Akzentfarbe des Themes an.

**Der dritte Zustand ist der wichtige.** Eine Bewertung kennt nicht
nur "gut" und "schlecht", sondern auch "dazu liegen keine Daten vor" -
im Analyzer ist das `stars == 0`, und die Regel dort lautet
ausdrücklich: null Sterne heißt *keine Daten*, nicht *schlecht*.

Sichtbar gemacht wird das hier auf zwei Arten gleichzeitig, weil eine
allein missverstanden würde:

1. Die Sterne stehen in `#1E1E24` - noch blasser als ein leerer Stern
   (`#2A2A34`). Eine Reihe leerer Sterne allein läse sich als
   "null von fünf", also als vernichtendes Urteil.
2. Daneben steht ein Chip `KEINE DATEN` in **neutral** - weiß bei 5 %,
   nie rot. Ein rotes "keine Daten" würde eine Lücke in der
   Datenquelle als Befund über den Spieler ausgeben.

Damit die beiden nicht auseinanderlaufen können, gibt es `Rating`:
Sterne und Chip in einem Widget, das den Zustand einmal entgegennimmt.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.theme_manager import theme


#
# Die Farbe der Sterne im Zustand "keine Daten". Bewusst dieselbe wie
# `border.base`: sie soll als Struktur gelesen werden, nicht als Wert.
#

NO_DATA_COLOR = tokens.BORDER["base"]

EMPTY_COLOR = tokens.BORDER["strong"]


class StarRating(QWidget):

    SPACING = 4

    def __init__(
        self,
        stars: int = 0,
        maximum: int = 5,
        size: int = 13,
        parent=None,
    ):

        super().__init__(parent)

        self._stars = max(0, min(maximum, stars))

        self._maximum = maximum

        self._size = size

        self.setFixedSize(self.sizeHint())

        #
        # `self.update` als gebundener Slot und NICHT
        # `lambda _n: self.update()`: eine Lambda hält eine harte
        # Referenz auf `self`, und der ThemeManager ist ein Singleton,
        # der ewig lebt - das Widget würde damit nie mehr freigegeben.
        # Wird sein C++-Objekt trotzdem zerstört, weil ein Elternteil
        # abgebaut wird, feuert die Lambda in ein gelöschtes Objekt und
        # Qt meldet "Internal C++ object already deleted". Einen
        # gebundenen Slot trennt Qt beim Zerstören des Empfängers
        # selbst.
        #

        theme().accent_changed.connect(self.update)

    # --------------------------------------------------

    def sizeHint(self) -> QSize:

        width = (
            self._maximum * self._size
            + (self._maximum - 1) * self.SPACING
        )

        return QSize(width, self._size)

    # --------------------------------------------------
    # API
    # --------------------------------------------------

    def setStars(self, stars: int):

        stars = max(0, min(self._maximum, int(stars)))

        if stars == self._stars:
            return

        self._stars = stars

        self.update()

    def stars(self) -> int:

        return self._stars

    def has_data(self) -> bool:
        """
        Null Sterne heißt "keine Daten" - siehe Modulkommentar.
        """

        return self._stars > 0

    # --------------------------------------------------
    # Zeichnen
    # --------------------------------------------------

    def _star_polygon(self, center_x: float, center_y: float, radius: float):
        """
        Klassischer Fünfzackstern: abwechselnd äußerer und innerer
        Radius, beginnend an der Spitze.
        """

        inner = radius * 0.42

        points = []

        for index in range(10):

            #
            # -90 Grad, damit die erste Spitze nach oben zeigt.
            #

            angle = math.radians(index * 36.0 - 90.0)

            current = radius if index % 2 == 0 else inner

            points.append(
                QPointF(
                    center_x + math.cos(angle) * current,
                    center_y + math.sin(angle) * current,
                )
            )

        return QPolygonF(points)

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        radius = self._size / 2.0

        center_y = self.height() / 2.0

        no_data = not self.has_data()

        filled = QColor(theme().accent_light())

        for index in range(self._maximum):

            center_x = (
                index * (self._size + self.SPACING)
                + radius
            )

            polygon = self._star_polygon(center_x, center_y, radius)

            painter.setPen(Qt.NoPen)

            if no_data:

                #
                # Keine Daten: alle Sterne gefüllt, aber in der
                # blassesten Struktur-Farbe. Gefüllt und nicht als
                # Kontur, damit sie nicht wie "leer, also null von
                # fünf" wirken.
                #

                painter.setBrush(QColor(NO_DATA_COLOR))

            elif index < self._stars:

                painter.setBrush(filled)

            else:

                painter.setBrush(QColor(EMPTY_COLOR))

            painter.drawPolygon(polygon)

        painter.end()


class Rating(QWidget):
    """
    Sterne und - falls keine Daten vorliegen - der Chip daneben.

    Es gibt sie, damit die beiden Hälften des Nullzustands nicht
    getrennt gesetzt werden können. Eine Seite, die nur `StarRating`
    benutzt und den Chip vergisst, zeigt fünf blasse Sterne ohne
    Erklärung - und das sieht aus wie ein Darstellungsfehler.
    """

    def __init__(self, stars: int = 0, size: int = 13, parent=None):

        super().__init__(parent)

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[1])

        self.stars = StarRating(stars, size=size)

        root.addWidget(self.stars)

        #
        # Der Import steht im Rumpf: `chip.py` liest `status_dot.py`,
        # und dieses Modul wird aus der Academy heraus geladen -
        # ein Import auf Modulebene zöge die Kette bei jedem Import
        # dieser Datei mit, auch wenn nur die Sterne gebraucht werden.
        #

        from gui.widgets.chip import Chip

        self.chip = Chip("KEINE DATEN", "neutral")

        root.addWidget(self.chip)

        root.addStretch(1)

        self._apply()

    def setStars(self, stars: int):

        self.stars.setStars(stars)

        self._apply()

    def _apply(self):

        self.chip.setVisible(not self.stars.has_data())
