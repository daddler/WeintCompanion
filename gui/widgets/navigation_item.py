from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPainterPath

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from gui.theme.colors import Colors

RADIUS = 8


class NavigationItem(QFrame):
    """
    Text-Navigationselement, wie im Design's `.nav-item` (Settings-
    Unternavigation): flache Fläche, linker Gradient-Balken im
    aktiven Zustand, kein Icon.
    """

    clicked = Signal()

    def __init__(self, text: str):

        super().__init__()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self.active = False
        self.hover = False

        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setFixedHeight(38)

        self.layout = QHBoxLayout(self)

        self.layout.setContentsMargins(12, 8, 12, 8)

        self.layout.setSpacing(0)

        self.label = QLabel(text)

        self.label.setStyleSheet(
            f"color:{Colors.TEXT_MUTED};"
            "font-size:13px;"
            "font-weight:500;"
            "background:transparent;"
        )

        self.layout.addWidget(self.label)

        self.layout.addStretch()

    # -------------------------------------------------
    # Paint
    # -------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)

        if self.active:

            painter.fillPath(path, QColor(Colors.SURFACE_LIGHT))

            glow = QLinearGradient(
                0, rect.top() + 6, 0, rect.bottom() - 6,
            )

            glow.setColorAt(0, QColor(Colors.PRIMARY))
            glow.setColorAt(1, QColor(Colors.PRIMARY_2))

            painter.fillRect(
                rect.left(),
                rect.top() + 6,
                3,
                rect.height() - 12,
                glow,
            )

        elif self.hover:

            painter.fillPath(path, QColor(Colors.SURFACE_LIGHT))

        painter.end()

    # -------------------------------------------------
    # Hover
    # -------------------------------------------------

    def enterEvent(self, event):

        self.hover = True
        self.update()

        super().enterEvent(event)

    def leaveEvent(self, event):

        self.hover = False
        self.update()

        super().leaveEvent(event)

    # -------------------------------------------------
    # Click
    # -------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)

    # -------------------------------------------------
    # Active
    # -------------------------------------------------

    def setActive(self, active: bool):

        self.active = active

        color = Colors.WHITE if active else Colors.TEXT_MUTED

        weight = 600 if active else 500

        self.label.setStyleSheet(
            f"color:{color};"
            f"font-size:13px;"
            f"font-weight:{weight};"
            "background:transparent;"
        )

        self.update()

    # -------------------------------------------------
    # Size
    # -------------------------------------------------

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return self.layout.minimumSize()
