from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
)
from PySide6.QtSvgWidgets import QSvgWidget
from pathlib import Path

from gui.theme.colors import Colors

CARD_RADIUS = 12

STATE_COLORS = {

    "normal": (Colors.SUCCESS, "rgba(124,192,110,18)", "INSTALLIERT"),
    "warning": (Colors.WARNING, "rgba(212,162,74,18)", "UPDATE"),
    "error": (Colors.ERROR, "rgba(229,107,107,18)", "OFFLINE"),
    "info": (Colors.DISCORD, "rgba(139,149,245,18)", "INFO"),
}


class StatusCard(QFrame):

    HERO_MODE = "hero"
    NORMAL_MODE = "normal"

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

        self._display_mode = self.NORMAL_MODE
        self._state = "normal"
        self._hover = False

        self.setObjectName("statusCard")

        self.setCursor(
            QCursor(Qt.PointingHandCursor)
        )

        self.setMouseTracking(True)

        self.setFixedHeight(150)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        #
        # Root
        #

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(18, 16, 18, 16)

        self.root.setSpacing(10)

        #
        # Header
        #

        header = QHBoxLayout()

        header.setSpacing(10)

        self.root.addLayout(header)

        self.icon_container = QFrame()

        self.icon_container.setFixedSize(32, 32)

        icon_layout = QVBoxLayout(self.icon_container)

        icon_layout.setContentsMargins(0, 0, 0, 0)

        self.icon_label = QSvgWidget()

        self.icon_label.setFixedSize(16, 16)

        self.set_icon(icon)

        icon_layout.addWidget(
            self.icon_label,
            alignment=Qt.AlignCenter,
        )

        header.addWidget(self.icon_container)

        title_layout = QVBoxLayout()

        title_layout.setSpacing(0)

        header.addLayout(title_layout, 1)

        self.title_label = QLabel(title)

        self.title_label.setStyleSheet(f"""
        QLabel{{
            color:{Colors.WHITE};
            font-size:13px;
            font-weight:600;
        }}
        """)

        title_layout.addWidget(self.title_label)

        header.addStretch()

        self.badge = QLabel("")

        self.badge.setAlignment(Qt.AlignCenter)

        header.addWidget(
            self.badge,
            alignment=Qt.AlignTop,
        )

        #
        # Value
        #

        self.value_label = QLabel()

        self.value_label.setStyleSheet(f"""
        QLabel{{
            color:{Colors.WHITE};
            font-family:"JetBrains Mono";
            font-size:20px;
            font-weight:600;
            letter-spacing:-0.02em;
        }}
        """)

        self.value_label.hide()

        self.root.addWidget(self.value_label)

        #
        # Status / Details
        #

        self.status_label = QLabel(status)

        self.status_label.setStyleSheet(f"""
        QLabel{{
            color:{Colors.TEXT_SECONDARY};
            font-size:12px;
        }}
        """)

        self.root.addWidget(self.status_label)

        self.details_label = QLabel(details)

        self.details_label.setWordWrap(True)

        self.details_label.setStyleSheet(f"""
        QLabel{{
            color:{Colors.TEXT_MUTED};
            font-size:12px;
        }}
        """)

        self.root.addWidget(self.details_label)

        self.root.addStretch()

        #
        # Button
        #

        bottom = QHBoxLayout()

        bottom.setContentsMargins(0, 0, 0, 0)

        self.button = QPushButton(button_text)

        self.button.setMinimumHeight(36)

        self.button.setCursor(Qt.PointingHandCursor)

        self.button.setStyleSheet(f"""
        QPushButton{{
            background:{Colors.SURFACE_LIGHT};
            color:{Colors.TEXT};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:6px;
            padding-left:14px;
            padding-right:14px;
            font-size:12px;
            font-weight:500;
        }}
        QPushButton:hover{{
            background:{Colors.BORDER_LIGHT};
        }}
        QPushButton:disabled{{
            color:{Colors.TEXT_MUTED};
        }}
        """)

        if not button_text:
            self.button.hide()

        bottom.addStretch()
        bottom.addWidget(self.button)

        self.root.addLayout(bottom)

        self.setStyleSheet(f"""
        QFrame#statusCard{{
            background:{Colors.CARD};
            border:1px solid {Colors.BORDER};
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        self.set_status(status)

    # --------------------------------------------------

    def sizeHint(self):
        return QSize(300, 150)

    # --------------------------------------------------
    # Hover
    # --------------------------------------------------

    def enterEvent(self, event):

        self._hover = True

        self.setStyleSheet(f"""
        QFrame#statusCard{{
            background:{Colors.CARD_HOVER};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        super().enterEvent(event)

    def leaveEvent(self, event):

        self._hover = False

        self.setStyleSheet(f"""
        QFrame#statusCard{{
            background:{Colors.CARD};
            border:1px solid {Colors.BORDER};
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def set_state(self, state: str):

        self._state = state.lower()
        self.update()

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(text)

        lower = text.lower()

        #
        # Negative Formulierungen ("Nicht installiert", "Nicht
        # gefunden") enthalten dieselben Teilworte wie die positiven
        # Zustände ("installiert", "gefunden") - deshalb müssen die
        # negativen/warnenden Prüfungen zuerst kommen, sonst gewinnt
        # immer fälschlich der grüne "normal"-Zustand.
        #

        if (
            "🔴" in text
            or "nicht" in lower
            or "offline" in lower
            or "error" in lower
            or "fehler" in lower
        ):
            key = "error"

        elif (
            "🟡" in text
            or "update" in lower
            or "warn" in lower
        ):
            key = "warning"

        elif (
            "🟢" in text
            or "installiert" in lower
            or "aktuell" in lower
            or "gefunden" in lower
            or "vorhanden" in lower
        ):
            key = "normal"

        else:
            key = "info"

        color, bg, badge_text = STATE_COLORS[key]

        self.badge.setText(badge_text)

        self.badge.setStyleSheet(f"""
        QLabel{{
            background:{bg};
            color:{color};
            border-radius:4px;
            padding:3px 8px;
            font-family:"JetBrains Mono";
            font-size:10px;
            font-weight:700;
        }}
        """)

        self.icon_container.setStyleSheet(f"""
        QFrame{{
            background:{bg};
            border-radius:8px;
        }}
        """)

    # --------------------------------------------------

    def set_value(self, value: str):

        value = str(value).strip()

        self.value_label.setVisible(bool(value))
        self.value_label.setText(value)

    def set_details(self, text: str):
        self.details_label.setText(text)

    def set_title(self, text: str):
        self.title_label.setText(text)

    def set_icon(self, icon: str):

        if Path(icon).exists():
            self.icon_label.load(icon)

    def set_tooltip(self, text: str):

        self.setToolTip(text)
        self.details_label.setToolTip(text)
        self.status_label.setToolTip(text)

    def set_button_text(self, text: str):

        self.button.setText(text)
        self.button.setVisible(bool(text))

    def set_button_enabled(self, enabled: bool):
        self.button.setEnabled(enabled)

    def show_button(self):
        self.button.show()

    def hide_button(self):
        self.button.hide()

    def get_button(self):
        return self.button

    def setDisplayMode(self, mode: str):
        self._display_mode = mode
