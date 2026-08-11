"""
WeintCompanion 2.0
Fortschrittsring

Rinne 8 px, Bogen in Akzentfarbe, runde Enden, Start bei -90° (oben).

Der Wert wird animiert (motion.progress, 300 ms) - aber nur er, nicht
die Beschriftung in seiner Mitte. Eine mitlaufende Zahl neben einem
mitlaufenden Bogen liest sich als Flackern; die Zahl steht deshalb
sofort auf ihrem Endwert, während der Bogen sie einholt. Dieselbe
Regel gilt bei `BarRow`.

Die Akzentfarbe wird im `paintEvent` gelesen, nicht im Konstruktor:
sonst behielte ein einmal gebauter Ring seine Farbe über einen
Akzentwechsel hinweg.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme import tokens
from gui.theme.motion import curve, duration
from gui.theme.theme_manager import theme


class ProgressRing(QWidget):

    def __init__(
        self,
        diameter: int = 96,
        thickness: int = 8,
        parent=None,
    ):

        super().__init__(parent)

        self._diameter = diameter

        self._thickness = thickness

        self._value = 0.0

        self._animation: QPropertyAnimation | None = None

        self.setFixedSize(diameter, diameter)

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

    def value(self) -> float:

        return self._value

    def setValue(self, value: float, animate: bool = True):
        """
        `value` ist ein Anteil zwischen 0.0 und 1.0.
        """

        value = max(0.0, min(1.0, float(value)))

        if value == self._value:
            return

        ms = duration("progress") if animate else 0

        if ms <= 0:

            self.ringValue = value

            return

        if self._animation is not None:
            self._animation.stop()

        animation = QPropertyAnimation(self, b"ringValue", self)

        animation.setDuration(ms)

        animation.setEasingCurve(QEasingCurve(curve("progress")))

        animation.setStartValue(self._value)

        animation.setEndValue(value)

        animation.start()

        self._animation = animation

    def _get_value(self) -> float:

        return self._value

    def _set_value(self, value: float):

        self._value = value

        self.update()

    ringValue = Property(float, _get_value, _set_value)

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        inset = self._thickness / 2.0

        rect = QRectF(
            inset,
            inset,
            self._diameter - self._thickness,
            self._diameter - self._thickness,
        )

        #
        # Rinne
        #

        pen = QPen(QColor(tokens.BORDER["base"]), self._thickness)

        pen.setCapStyle(Qt.FlatCap)

        painter.setPen(pen)

        painter.drawArc(rect, 0, 360 * 16)

        if self._value <= 0:
            return

        #
        # Bogen. Qt zählt Winkel in Sechzehntelgrad und gegen den
        # Uhrzeigersinn; -90° ist oben, das Minus dreht die Richtung
        # wieder mit dem Uhrzeigersinn.
        #

        pen = QPen(QColor(theme().accent_base()), self._thickness)

        pen.setCapStyle(Qt.RoundCap)

        painter.setPen(pen)

        painter.drawArc(
            rect,
            90 * 16,
            int(-self._value * 360 * 16),
        )
