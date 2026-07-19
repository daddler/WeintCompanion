from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from gui.widgets.rail_item import RailItem
from core.resources import Resources
from gui.theme.colors import Colors
from gui.theme.metrics import Metrics


RAIL_BORDER = Colors.SURFACE_LIGHT


class _AvatarButton(QFrame):
    """
    Runder Discord-Avatar unten in der Rail - Klick öffnet die
    Discord-Einstellungen (ersetzt den alten DiscordStatusButton).
    """

    clicked = Signal()

    SIZE = 36

    def __init__(self):

        super().__init__()

        self.setFixedSize(self.SIZE, self.SIZE)

        self.setCursor(QCursor(Qt.PointingHandCursor))

        self._connected = False
        self._initial = "?"

    def setState(self, connected: bool, initial: str, tooltip: str):

        self._connected = connected
        self._initial = initial or "?"

        self.setToolTip(tooltip)

        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        gradient = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        if self._connected:

            gradient.setColorAt(0, QColor("#5865F2"))
            gradient.setColorAt(1, QColor("#7983F5"))

        else:

            gradient.setColorAt(0, QColor(Colors.SURFACE_LIGHT))
            gradient.setColorAt(1, QColor(Colors.BORDER_LIGHT))

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(rect)

        painter.setPen(QColor(Colors.WHITE))

        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(
            rect,
            Qt.AlignCenter,
            self._initial[:1].upper(),
        )

        #
        # Präsenz-Punkt
        #

        dot_color = (
            QColor(Colors.SUCCESS)
            if self._connected
            else QColor(Colors.TEXT_FAINT)
        )

        painter.setBrush(dot_color)

        painter.setPen(QColor(Colors.SIDEBAR))

        painter.drawEllipse(
            rect.width() - 10,
            rect.height() - 10,
            9,
            9,
        )

        painter.end()

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)


class Sidebar(QFrame):
    """
    Icon-only Rail-Sidebar (72px), siehe Design's linke `<aside>`-Spalte.
    """

    pageChanged = Signal(int)
    avatarClicked = Signal()

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.setObjectName("Sidebar")

        self.setFixedWidth(Metrics.RAIL_WIDTH)

        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        self.setStyleSheet(f"""
        QFrame#Sidebar{{
            background:{Colors.SIDEBAR};
            border:none;
            border-right:1px solid {RAIL_BORDER};
        }}
        """)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(14, 16, 14, 16)

        self.root.setSpacing(6)

        #
        # Logo
        #

        self.mark = QLabel("W")

        self.mark.setFixedSize(40, 40)

        self.mark.setAlignment(Qt.AlignCenter)

        self.mark.setStyleSheet(f"""
        QLabel{{
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 {Colors.PRIMARY},
                stop:1 {Colors.PRIMARY_2}
            );
            color:white;
            font-size:15px;
            font-weight:800;
            border-radius:10px;
        }}
        """)

        self.root.addWidget(
            self.mark,
            alignment=Qt.AlignCenter,
        )

        self.root.addSpacing(6)

        #
        # Navigation
        #

        self.items: list[RailItem] = []

        pages = [

            (Resources.dashboard(), "Dashboard"),
            (Resources.software(), "Software"),
            (Resources.sync(), "Synchronisation"),
            (Resources.settings(), "Einstellungen"),
            (Resources.logs(), "Logs"),

        ]

        for index, (icon, tooltip) in enumerate(pages):

            item = RailItem(icon, tooltip)

            item.clicked.connect(
                lambda i=index: self.change_page(i)
            )

            self.root.addWidget(
                item,
                alignment=Qt.AlignCenter,
            )

            self.items.append(item)

        self.root.addStretch()

        #
        # Avatar
        #

        self.avatar = _AvatarButton()

        self.avatar.clicked.connect(
            self.avatarClicked.emit
        )

        self.root.addWidget(
            self.avatar,
            alignment=Qt.AlignCenter,
        )

        #
        # Initialisieren
        #

        self.refresh()

        if self.items:
            self.items[0].setActive(True)

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def change_page(self, index):

        for item in self.items:
            item.setActive(False)

        self.items[index].setActive(True)

        self.pageChanged.emit(index)

    # ---------------------------------------------------------
    # Refresh
    # ---------------------------------------------------------

    def refresh(self):

        state = self.manager.state

        account = self.manager.discord_account.load()

        if account:

            username = account.get("username", "Discord")

            self.avatar.setState(
                connected=True,
                initial=username,
                tooltip=f"Mit Discord verbunden als {username}",
            )

        elif state.discord_connected:

            self.avatar.setState(
                connected=True,
                initial=state.discord_name or "D",
                tooltip=f"Discord-Bot online: {state.discord_name}",
            )

        else:

            self.avatar.setState(
                connected=False,
                initial="?",
                tooltip="Nicht mit Discord verbunden",
            )
