"""
Sternebewertung (★★★☆☆).

Selbst gezeichnet statt als Text mit Unicode-Sternen: welche
Schriftart welches Sternzeichen wie breit rendert, ist zwischen
Linux und Windows unterschiedlich, und die Farbe ließe sich pro
Stern nicht sauber trennen. Ein gezeichneter Stern sieht überall
gleich aus und nimmt die Goldtöne des Designs an.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QWidget

from gui.theme.colors import Colors


class StarRating(QWidget):

    SPACING = 4

    def __init__(
        self,
        stars: int = 0,
        maximum: int = 5,
        size: int = 15,
        parent=None,
    ):

        super().__init__(parent)

        self._stars = max(0, min(maximum, stars))

        self._maximum = maximum

        self._size = size

        self.setFixedSize(self.sizeHint())

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

        for index in range(self._maximum):

            center_x = (
                index * (self._size + self.SPACING)
                + radius
            )

            polygon = self._star_polygon(center_x, center_y, radius)

            if index < self._stars:

                painter.setPen(Qt.NoPen)

                painter.setBrush(QColor(Colors.GOLD_LIGHT))

            else:

                painter.setPen(QColor(Colors.TEXT_FAINT))

                painter.setBrush(Qt.NoBrush)

            painter.drawPolygon(polygon)

        painter.end()
