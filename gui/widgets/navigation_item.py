from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
)


RADIUS = 16


class NavigationItem(QFrame):

    clicked = Signal()

    def __init__(self, icon_path: str, text: str):

        super().__init__()

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
        QFrame{
            background:transparent;
            border:none;
        }
        """)

        self.active = False
        self.hover = False

        self.setCursor(
            QCursor(Qt.PointingHandCursor)
        )

        self.setFixedHeight(56)

        self.layout = QHBoxLayout(self)

        self.layout.setContentsMargins(
            16,
            10,
            16,
            10,
        )

        self.layout.setSpacing(12)

        #
        # Linker Indicator
        #

        self.indicator = QFrame()

        self.indicator.setFixedSize(
            3,
            30,
        )

        self.indicator.setStyleSheet("""
        QFrame{

            background:transparent;

            border-radius:1px;
        }
        """)

        self.layout.addWidget(
            self.indicator
        )

        #
        # Icon
        #

        self.icon = QLabel()

        icon = QIcon(icon_path)

        self.icon.setPixmap(
            icon.pixmap(
                22,
                22,
            )
        )

        self.icon.setStyleSheet("""
        QLabel{
            background:transparent;
        }
        """)

        self.layout.addWidget(
            self.icon
        )

        #
        # Text
        #

        self.label = QLabel(text)

        self.label.setStyleSheet("""
        QLabel{

            color:white;

            background:transparent;

            font-size:14px;

            font-weight:600;
        }
        """)

        self.layout.addWidget(
            self.label
        )

        self.layout.addStretch()
    
    # -------------------------------------------------
    # Paint
    # -------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        rect = self.rect().adjusted(
            1,
            1,
            -1,
            -1,
        )

        path = QPainterPath()

        path.addRoundedRect(
            rect,
            RADIUS,
            RADIUS,
        )

        #
        # Hintergrund
        #

        if self.active:

            background = QLinearGradient(
                rect.topLeft(),
                rect.bottomRight(),
            )

            background.setColorAt(
                0,
                QColor("#3A2F58"),
            )

            background.setColorAt(
                1,
                QColor("#2B2342"),
            )

            painter.fillPath(
                path,
                background,
            )

            #
            # Violetter Glow links
            #

            glow = QLinearGradient(
                rect.left(),
                rect.top(),
                rect.left() + 40,
                rect.top(),
            )

            glow.setColorAt(
                0,
                QColor(150, 95, 255, 170),
            )

            glow.setColorAt(
                1,
                QColor(150, 95, 255, 0),
            )

            painter.fillRect(
                rect.adjusted(0, 8, -rect.width() + 6, -8),
                glow,
            )

            #
            # dezenter Rahmen
            #

            painter.setPen(
                QPen(
                    QColor(170, 120, 255, 80),
                    1,
                )
            )

            painter.drawRoundedRect(
                rect,
                RADIUS,
                RADIUS,
            )

        elif self.hover:

            background = QLinearGradient(
                rect.topLeft(),
                rect.bottomLeft(),
            )

            background.setColorAt(
                0,
                QColor(255, 255, 255, 14),
            )

            background.setColorAt(
                1,
                QColor(255, 255, 255, 6),
            )

            painter.fillPath(
                path,
                background,
            )

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

        if active:

            #
            # linker Glow-Indikator
            #

            self.indicator.setStyleSheet("""
            QFrame{

                background:#A66CFF;

                border-radius:1px;
            }
            """)

            self.label.setStyleSheet("""
            QLabel{

                color:white;

                background:transparent;

                font-size:14px;

                font-weight:700;
            }
            """)

            self.icon.setStyleSheet("""
            QLabel{

                background:transparent;
            }
            """)

        else:

            self.indicator.setStyleSheet("""
            QFrame{

                background:transparent;
            }
            """)

            self.label.setStyleSheet("""
            QLabel{

                color:#B7BDC9;

                background:transparent;

                font-size:14px;

                font-weight:600;
            }
            """)

            self.icon.setStyleSheet("""
            QLabel{

                background:transparent;

                opacity:0.75;
            }
            """)

        self.update()

    # -------------------------------------------------
    # Size
    # -------------------------------------------------

    def sizeHint(self):

        return self.minimumSizeHint()

    def minimumSizeHint(self):

        return self.layout.minimumSize()