from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QLinearGradient,
    QPainter,
    QPainterPath,
)

from PySide6.QtSvgWidgets import QSvgWidget

from PySide6.QtWidgets import QFrame, QVBoxLayout

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics


class RailItem(QFrame):
    """
    Icon-only Navigationselement der Rail-Sidebar (44x44), mit
    linkem Gradient-Balken im aktiven Zustand - siehe .rail-item(.active)
    im Design.
    """

    clicked = Signal()

    def __init__(self, icon: str, tooltip: str):

        super().__init__()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self.active = False
        self.hover = False

        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setFixedSize(
            Metrics.RAIL_ITEM_SIZE,
            Metrics.RAIL_ITEM_SIZE,
        )

        self.setToolTip(tooltip)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        self.icon = QSvgWidget(icon)

        self.icon.setFixedSize(18, 18)

        layout.addWidget(
            self.icon,
            alignment=Qt.AlignCenter,
        )

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)

        if self.active:

            painter.fillPath(
                path,
                QColor(Colors.SURFACE_LIGHT),
            )

            glow = QLinearGradient(
                0,
                rect.top() + 10,
                0,
                rect.bottom() - 10,
            )

            glow.setColorAt(0, QColor(Colors.PRIMARY))
            glow.setColorAt(1, QColor(Colors.PRIMARY_2))

            painter.fillRect(
                rect.left() - 2,
                rect.top() + 10,
                3,
                rect.height() - 20,
                glow,
            )

        elif self.hover:

            painter.fillPath(
                path,
                QColor(Colors.SURFACE_LIGHT),
            )

        painter.end()

    # --------------------------------------------------
    # Hover
    # --------------------------------------------------

    def enterEvent(self, event):

        self.hover = True
        self.update()

        super().enterEvent(event)

    def leaveEvent(self, event):

        self.hover = False
        self.update()

        super().leaveEvent(event)

    # --------------------------------------------------
    # Click
    # --------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.clicked.emit()

        super().mousePressEvent(event)

    # --------------------------------------------------
    # Active
    # --------------------------------------------------

    def setActive(self, active: bool):

        self.active = active

        self.update()
