"""
WeintCompanion 2.0
Sparkline

Eine Polylinie, 2 px, in Akzentfarbe, mit einem gefüllten Punkt am
letzten Wert. **Keine Achsen, keine Beschriftung, kein Füllbereich.**

Der Verzicht ist die Aussage: eine Sparkline steht neben einer Zahl
und beantwortet genau eine Frage - "in welche Richtung geht das?".
Sobald sie Achsen bekommt, behauptet sie Ablesbarkeit, die sie auf
132 x 40 px nicht einlösen kann, und der Blick bleibt an ihr hängen,
statt bei der Zahl daneben.

Zwei Sonderfälle, die kein Diagramm ergeben und deshalb auch keines
zeichnen: weniger als zwei Werte, und alle Werte gleich. Im zweiten
Fall wird eine waagerechte Linie auf halber Höhe gezogen - ohne
Sonderfall stünde sie am unteren Rand, weil die Spanne 0 ist.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from gui.theme.theme_manager import theme


class Sparkline(QWidget):

    def __init__(
        self,
        width: int = 132,
        height: int = 40,
        parent=None,
    ):

        super().__init__(parent)

        self._values: list[float] = []

        self.setFixedSize(width, height)

        theme().accent_changed.connect(lambda _n: self.update())

    # --------------------------------------------------

    def setValues(self, values):

        values = [float(v) for v in (values or [])]

        if values == self._values:
            return

        self._values = values

        self.update()

    def values(self) -> list[float]:

        return list(self._values)

    # --------------------------------------------------

    def paintEvent(self, event):

        if len(self._values) < 2:
            return

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        #
        # 2 px Linienstärke heißt: 1 px Rand oben und unten, sonst
        # wird die Linie an den Extremwerten halb abgeschnitten.
        #

        margin = 2.0

        width = self.width() - 2 * margin

        height = self.height() - 2 * margin

        low = min(self._values)

        high = max(self._values)

        span = high - low

        points = QPolygonF()

        step = width / (len(self._values) - 1)

        for index, value in enumerate(self._values):

            if span <= 0:

                ratio = 0.5

            else:

                ratio = (value - low) / span

            points.append(
                QPointF(
                    margin + index * step,
                    margin + (1.0 - ratio) * height,
                )
            )

        color = QColor(theme().accent_base())

        pen = QPen(color, 2)

        pen.setJoinStyle(Qt.RoundJoin)

        pen.setCapStyle(Qt.RoundCap)

        painter.setPen(pen)

        painter.setBrush(Qt.NoBrush)

        painter.drawPolyline(points)

        #
        # Der letzte Wert bekommt einen Punkt: er ist der aktuelle,
        # und ohne ihn endet die Linie beliebig am rechten Rand.
        #

        painter.setPen(Qt.NoPen)

        painter.setBrush(color)

        painter.drawEllipse(points[-1], 3.0, 3.0)
