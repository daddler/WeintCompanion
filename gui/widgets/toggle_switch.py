from __future__ import annotations

from PySide6.QtCore import (
    Qt,
    QSize,
    QRectF,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)

from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
)

from PySide6.QtWidgets import QAbstractButton

from gui.theme.colors import Colors


class ToggleSwitch(QAbstractButton):
    """
    Pill-Toggle mit animiertem Thumb, wie im Design
    (Gradient lila->indigo wenn an, dunkelgrau wenn aus).
    """

    WIDTH = 36
    HEIGHT = 20
    THUMB_MARGIN = 2

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setChecked(checked)

        self.setCursor(Qt.PointingHandCursor)

        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._thumb_position = (
            1.0 if checked else 0.0
        )

        self._animation = QPropertyAnimation(
            self,
            b"thumbPosition",
        )

        self._animation.setDuration(160)
        self._animation.setEasingCurve(
            QEasingCurve.InOutQuad
        )

        self.toggled.connect(
            self._animate_to_state
        )

    # --------------------------------------------------
    # Property fürs Thumb
    # --------------------------------------------------

    def getThumbPosition(self):
        return self._thumb_position

    def setThumbPosition(self, value):
        self._thumb_position = value
        self.update()

    thumbPosition = Property(
        float,
        getThumbPosition,
        setThumbPosition,
    )

    def _animate_to_state(self, checked: bool):

        self._animation.stop()

        self._animation.setStartValue(
            self._thumb_position
        )

        self._animation.setEndValue(
            1.0 if checked else 0.0
        )

        self._animation.start()

    # --------------------------------------------------

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(
            0,
            0,
            self.WIDTH,
            self.HEIGHT,
        )

        radius = self.HEIGHT / 2

        if not self.isEnabled():

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Colors.SURFACE_LIGHT))
            painter.drawRoundedRect(rect, radius, radius)

        elif self._thumb_position > 0.001:

            gradient = QLinearGradient(
                rect.left(),
                0,
                rect.right(),
                0,
            )

            gradient.setColorAt(0, QColor(Colors.PRIMARY))
            gradient.setColorAt(1, QColor(Colors.PRIMARY_2))

            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, radius, radius)

        else:

            painter.setPen(
                QColor(Colors.BORDER_LIGHT)
            )

            painter.setBrush(
                QColor(Colors.SURFACE_LIGHT)
            )

            painter.drawRoundedRect(
                rect.adjusted(0.5, 0.5, -0.5, -0.5),
                radius,
                radius,
            )

        #
        # Thumb
        #

        diameter = self.HEIGHT - self.THUMB_MARGIN * 2

        travel = self.WIDTH - diameter - self.THUMB_MARGIN * 2

        x = self.THUMB_MARGIN + travel * self._thumb_position

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QColor(Colors.WHITE)
            if self.isEnabled()
            else QColor(Colors.TEXT_MUTED)
        )

        painter.drawEllipse(
            QRectF(
                x,
                self.THUMB_MARGIN,
                diameter,
                diameter,
            )
        )

        painter.end()
