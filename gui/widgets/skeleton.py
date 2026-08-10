"""
WeintCompanion 2.0
Skelettflächen

Der Ladezustand, der die Form des kommenden Inhalts vorwegnimmt.

**Die 250-ms-Verzögerung ist der eigentliche Punkt** (§3, §6.5). Ein
Skelett, das sofort erscheint, blitzt bei jedem schnellen Abruf kurz
auf und macht die Oberfläche unruhiger, als wenn gar nichts passiert
wäre. Umgekehrt braucht ein Archivabruf real **bis zu drei Minuten** -
dort wäre eine leere Fläche ohne Erklärung schlicht ein kaputtes
Programm.

Die Schwelle trennt beides: unter 250 ms sieht der Nutzer nie ein
Skelett, darüber sieht er sofort, dass gearbeitet wird. Deshalb hat
dieses Widget einen eigenen Timer und wird **sichtbar gemacht statt
gebaut** - wer es erst nach 250 ms erzeugt, hat die Wartezeit schon
verloren.

Bei reduzierter Bewegung entfällt der Schimmer und die Fläche steht
ruhig in `surface.raised`. Die Verzögerung bleibt: sie ist keine
Animation, sondern eine Entscheidung darüber, wann etwas erscheint.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.motion import MOTION, SKELETON_DELAY, SKELETON_TRAVEL, is_reduced


#
# Schrittweite des Schimmers je Tick. Die Wanderung von -320 auf +320
# dauert motion.skeleton (1200 ms).
#

TICK_MS = 32


class Skeleton(QWidget):
    """
    Eine einzelne Skelettfläche.

    `height` ist 12 px für eine Textzeile oder die Blockhöhe für eine
    Karte; `width_percent` staffelt mehrere Textzeilen (100 / 82 / 64),
    damit sie nicht wie ein Block wirken.
    """

    def __init__(
        self,
        height: int = 12,
        width_percent: int = 100,
        radius: int | None = None,
        parent=None,
    ):

        super().__init__(parent)

        self._width_percent = max(1, min(100, width_percent))

        self._offset = -SKELETON_TRAVEL

        self.setFixedHeight(height)

        self._radius = (
            radius
            if radius is not None
            else tokens.RADIUS["sm"]
        )

        self._timer = QTimer(self)

        self._timer.setInterval(TICK_MS)

        self._timer.timeout.connect(self._advance)

    # --------------------------------------------------

    def showEvent(self, event):

        super().showEvent(event)

        if not is_reduced():
            self._timer.start()

    def hideEvent(self, event):

        super().hideEvent(event)

        self._timer.stop()

    def _advance(self):

        step = (
            2 * SKELETON_TRAVEL
            / max(1, MOTION["skeleton"].duration / TICK_MS)
        )

        self._offset += step

        if self._offset > SKELETON_TRAVEL:
            self._offset = -SKELETON_TRAVEL

        self.update()

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        width = self.width() * self._width_percent / 100.0

        rect = QRectF(0, 0, width, self.height())

        painter.setPen(Qt.NoPen)

        if is_reduced():

            painter.setBrush(QColor(tokens.SURFACE["raised"]))

            painter.drawRoundedRect(rect, self._radius, self._radius)

            return

        gradient = QLinearGradient(
            self._offset,
            0,
            self._offset + SKELETON_TRAVEL,
            0,
        )

        gradient.setColorAt(0.0, QColor(tokens.SURFACE["card"]))
        gradient.setColorAt(0.5, QColor(tokens.SURFACE_EXTRA["shimmer"]))
        gradient.setColorAt(1.0, QColor(tokens.SURFACE["card"]))

        painter.setBrush(gradient)

        painter.drawRoundedRect(rect, self._radius, self._radius)


class SkeletonGroup(QWidget):
    """
    Mehrere Skelette samt der 250-ms-Verzögerung.

    Der Aufrufer schaltet `begin()` / `end()` und braucht sich um die
    Schwelle nicht zu kümmern - genau deshalb liegt sie hier und nicht
    an jeder Abrufstelle einzeln.
    """

    def __init__(
        self,
        lines: tuple[int, ...] = (100, 82, 64),
        blocks: int = 0,
        block_height: int = 74,
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[1])

        for percent in lines:

            root.addWidget(Skeleton(12, percent))

        if blocks:

            root.addSpacing(tokens.SPACE[1])

            for _ in range(blocks):

                root.addWidget(
                    Skeleton(block_height, 100, tokens.RADIUS["md"])
                )

        self._delay = QTimer(self)

        self._delay.setSingleShot(True)

        self._delay.setInterval(SKELETON_DELAY)

        self._delay.timeout.connect(lambda: self.setVisible(True))

        self.setVisible(False)

    # --------------------------------------------------

    def begin(self):
        """
        Ein Abruf hat begonnen. Sichtbar wird das Skelett erst, wenn
        er länger als 250 ms dauert.
        """

        if self.isVisible() or self._delay.isActive():
            return

        self._delay.start()

    def end(self):
        """
        Der Abruf ist beendet - gleich, ob erfolgreich oder nicht.
        """

        self._delay.stop()

        self.setVisible(False)
