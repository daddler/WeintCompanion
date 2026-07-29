"""
Schmaler Fortschrittsbalken.

Wird für Boss-Leben, Ranking-Anteile, Verbrauchsgüter und
Cooldown-Restzeiten benutzt. Bewusst selbst gezeichnet statt
QProgressBar: die globale Stylesheet formatiert QProgressBar nicht,
und ein gezeichneter Balken kann den Akzent-Farbverlauf des Designs
übernehmen, den eine Stylesheet-Lösung hier nicht sauber hinbekommt.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

from gui.theme.colors import Colors


class MeterBar(QWidget):

    DEFAULT_HEIGHT = 8

    def __init__(
        self,
        height: int = DEFAULT_HEIGHT,
        color: str = "",
        parent=None,
    ):
        """
        `color` leer bedeutet: der Akzent-Farbverlauf des Designs
        (Lila -> Indigo). Eine gesetzte Farbe wird einfarbig gemalt -
        so lassen sich Zustände (Erfolg/Warnung/Fehler) abbilden.
        """

        super().__init__(parent)

        self._value = 0.0

        self._color = color

        self._track = Colors.SURFACE_LIGHT

        self.setFixedHeight(height)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

    # --------------------------------------------------
    # API
    # --------------------------------------------------

    def setValue(self, value: float):
        """
        `value` ist ein Anteil zwischen 0.0 und 1.0.
        """

        value = max(0.0, min(1.0, float(value)))

        if value == self._value:
            return

        self._value = value

        self.update()

    def value(self) -> float:

        return self._value

    def setColor(self, color: str):

        if color == self._color:
            return

        self._color = color

        self.update()

    def setTrackColor(self, color: str):

        self._track = color

        self.update()

    # --------------------------------------------------
    # Zeichnen
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())

        radius = rect.height() / 2.0

        #
        # Hintergrundschiene
        #

        track_path = QPainterPath()

        track_path.addRoundedRect(rect, radius, radius)

        painter.fillPath(
            track_path,
            QColor(self._track),
        )

        #
        # Füllung
        #

        if self._value > 0.0:

            fill_width = rect.width() * self._value

            #
            # Unterhalb der Eckrundung sähe ein Balken wie ein
            # abgeschnittener Kreis aus - eine Mindestbreite hält ihn
            # auch bei sehr kleinen Werten als Pille lesbar.
            #

            fill_width = max(fill_width, rect.height())

            fill_rect = QRectF(
                rect.left(),
                rect.top(),
                fill_width,
                rect.height(),
            )

            fill_path = QPainterPath()

            fill_path.addRoundedRect(fill_rect, radius, radius)

            painter.setClipPath(track_path)

            if self._color:

                painter.fillPath(
                    fill_path,
                    QColor(self._color),
                )

            else:

                gradient = QLinearGradient(
                    fill_rect.topLeft(),
                    fill_rect.topRight(),
                )

                gradient.setColorAt(0, QColor(Colors.PRIMARY))
                gradient.setColorAt(1, QColor(Colors.PRIMARY_2))

                painter.fillPath(fill_path, gradient)

        painter.end()
