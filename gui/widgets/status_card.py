from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.effects.attention import AttentionEffect


class StatusCard(QFrame):

    clicked = Signal()

    def __init__(
        self,
        icon: str,
        title: str,
        status: str,
        details: str,
        button_text: str = "",
    ):
        super().__init__()

        self.setObjectName("card")
        self.setMinimumHeight(140)

        self.setCursor(
            QCursor(Qt.PointingHandCursor)
        )

        self.setMouseTracking(True)

        self._hover = False
        self._state = "normal"

        self.effect = AttentionEffect(self)

        root = QHBoxLayout(self)
        root.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        root.setSpacing(20)

        #
        # Icon
        #

        self.icon_container = QFrame()

        self.icon_container.setFixedSize(
            72,
            72,
        )

        self.icon_container.setStyleSheet("""
            QFrame{
                background:#313440;
                border-radius:18px;
            }
        """)

        icon_layout = QVBoxLayout(
            self.icon_container
        )

        icon_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.icon_label = QLabel(icon)

        self.icon_label.setAlignment(
            Qt.AlignCenter
        )

        self.icon_label.setStyleSheet("""
            font-size:36px;
            background:transparent;
        """)

        icon_layout.addWidget(
            self.icon_label
        )

        root.addWidget(
            self.icon_container
        )

        #
        # Informationen
        #

        info = QVBoxLayout()
        info.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName(
            "cardTitle"
        )

        self.status_label = QLabel(status)
        self.status_label.setObjectName(
            "cardValue"
        )

        self.details_label = QLabel(details)

        self.details_label.setWordWrap(True)

        self.details_label.setStyleSheet("""
            color:#AEB4C2;
            font-size:13px;
        """)

        info.addWidget(
            self.title_label
        )

        info.addWidget(
            self.status_label
        )

        info.addWidget(
            self.details_label
        )

        info.addStretch()

        root.addLayout(
            info,
            1,
        )

        #
        # Button
        #

        self.button = QPushButton(
            button_text
        )

        self.button.setMinimumWidth(220)
        self.button.setMinimumHeight(48)

        if not button_text:

            self.button.hide()

        root.addWidget(
            self.button,
            alignment=Qt.AlignRight
            | Qt.AlignBottom,
        )

        self.update_style()

    # --------------------------------------------------

    def update_style(
        self,
        hover=None,
    ):

        if hover is not None:

            self._hover = hover

        border = "#353947"
        width = 1

        #
        # Status
        #

        if self._state == "warning":

            border = "#DDB94D"
            width = 2

        elif self._state == "error":

            border = "#E65A5A"
            width = 2

        #
        # Hover überschreibt nur normal
        #

        elif self._hover:

            border = "#7A61FF"
            width = 2

        self.setStyleSheet(f"""
            QFrame#card{{
                background:#262933;
                border:{width}px solid {border};
                border-radius:16px;
            }}
        """)

    # --------------------------------------------------

    def enterEvent(self, event):

        self.effect.hover()

        super().enterEvent(event)

    # --------------------------------------------------

    def leaveEvent(self, event):

        self.effect.normal()

        super().leaveEvent(event)

    # --------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.clicked.emit()

        super().mousePressEvent(event)

    # --------------------------------------------------

    def set_state(
        self,
        state,
    ):

        self._state = state

        self.update_style()

    # --------------------------------------------------

    def set_status(self, text):

        self.status_label.setText(text)

        if "🟢" in text:

            color = "#7ED957"

        elif "🟡" in text:

            color = "#DDB94D"

        elif "🔴" in text:

            color = "#E65A5A"

        else:

            color = "white"

        self.status_label.setStyleSheet(f"""
            color:{color};
            font-size:16px;
            font-weight:600;
        """)

    # --------------------------------------------------

    def set_details(self, text):

        self.details_label.setText(text)

    # --------------------------------------------------

    def set_title(self, text):

        self.title_label.setText(text)

    # --------------------------------------------------

    def set_icon(self, text):

        self.icon_label.setText(text)

    # --------------------------------------------------

    def set_tooltip(self, text):

        self.details_label.setToolTip(text)

    # --------------------------------------------------

    def get_button(self):

        return self.button