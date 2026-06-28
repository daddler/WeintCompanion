from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
)


class NavigationItem(QFrame):

    clicked = Signal()

    def __init__(self, icon_path: str, text: str):
        super().__init__()

        self.active = False

        self.setFixedHeight(58)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setStyleSheet(self.normal_style())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        #
        # Icon
        #

        self.icon = QLabel()

        icon = QIcon(icon_path)

        self.icon.setPixmap(
            icon.pixmap(26, 26)
        )

        layout.addWidget(self.icon)

        #
        # Text
        #

        self.label = QLabel(text)

        self.label.setStyleSheet("""
            color:white;
            font-size:15px;
            font-weight:600;
            background:transparent;
        """)

        layout.addWidget(self.label)

        layout.addStretch()

    # -------------------------------------------------

    def normal_style(self):

        return """
        QFrame{

            background:transparent;

            border-radius:14px;

        }
        """

    # -------------------------------------------------

    def hover_style(self):

        return """
        QFrame{

            background:#2D303A;

            border-radius:14px;

        }
        """

    # -------------------------------------------------

    def active_style(self):

        return """
        QFrame{

            background:#8B5CF6;

            border:1px solid #B28CFF;

            border-radius:14px;

        }
        """

    # -------------------------------------------------

    def enterEvent(self, event):

        if not self.active:

            self.setStyleSheet(
                self.hover_style()
            )

    # -------------------------------------------------

    def leaveEvent(self, event):

        if not self.active:

            self.setStyleSheet(
                self.normal_style()
            )

    # -------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.clicked.emit()

    # -------------------------------------------------

    def setActive(self, active: bool):

        self.active = active

        if active:

            self.setStyleSheet(
                self.active_style()
            )

        else:

            self.setStyleSheet(
                self.normal_style()
            )