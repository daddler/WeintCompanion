from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from gui.widgets.navigation_item import NavigationItem
from core.resources import Resources
from core.version import VERSION


SIDEBAR_WIDTH = 305
SIDEBAR_RADIUS = 26


class Sidebar(QFrame):

    pageChanged = Signal(int)

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.setObjectName("Sidebar")

        self.setFixedWidth(
            SIDEBAR_WIDTH
        )

        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        #
        # Root Layout
        #

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            22,
            22,
            22,
            22,
        )

        self.root.setSpacing(18)

        #
        # Bereiche
        #

        self.build_header()

        self.build_navigation()

        self.build_status()

        self.build_footer()

        #
        # Initialisieren
        #

        self.refresh()

        if self.items:

            self.items[0].setActive(True)

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------

    def build_header(self):

        header = QVBoxLayout()

        header.setContentsMargins(
            0,
            4,
            0,
            0,
        )

        header.setSpacing(8)

        #
        # Logo
        #

        self.logo = QLabel()

        self.logo.setAlignment(
            Qt.AlignCenter
        )

        pix = QPixmap(
            Resources.logo()
        )

        if not pix.isNull():

            self.logo.setPixmap(

                pix.scaled(

                    170,
                    170,

                    Qt.KeepAspectRatio,

                    Qt.SmoothTransformation,

                )

            )

        header.addWidget(
            self.logo,
            alignment=Qt.AlignCenter,
        )

        #
        # Titel
        #

        title = QLabel(
            "WeintCompanion"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setObjectName(
            "sidebarTitle"
        )

        title.setStyleSheet("""
        QLabel{

            color:white;

            font-size:21px;

            font-weight:800;

            background:transparent;
        }
        """)

        header.addWidget(title)

        #
        # Badge
        #

        badge = QLabel(
            "MISTS OF PANDARIA CLASSIC"
        )

        badge.setAlignment(
            Qt.AlignCenter
        )

        badge.setFixedHeight(
            28
        )

        badge.setStyleSheet("""
        QLabel{

            background:rgba(214,176,77,18);

            color:#E6C86B;

            border:1px solid rgba(214,176,77,45);

            border-radius:14px;

            font-size:10px;

            font-weight:700;

            padding-left:14px;

            padding-right:14px;
        }
        """)

        header.addWidget(
            badge,
            alignment=Qt.AlignCenter,
        )

        #
        # Version
        #

        self.version = QLabel(
            f"Version {VERSION}"
        )

        self.version.setAlignment(
            Qt.AlignCenter
        )

        self.version.setStyleSheet("""
        QLabel{

            color:#8E96A4;

            font-size:12px;

            background:transparent;
        }
        """)

        header.addWidget(
            self.version
        )

        self.root.addLayout(
            header
        )

        self.root.addSpacing(
            18
        )
    
    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def build_navigation(self):

        self.navigation = QVBoxLayout()

        self.navigation.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.navigation.setSpacing(
            8
        )

        self.root.addLayout(
            self.navigation
        )

        self.items = []

        pages = [

            (Resources.dashboard(), "Dashboard"),
            (Resources.software(), "Software"),
            (Resources.sync(), "Synchronisation"),
            (Resources.settings(), "Einstellungen"),
            (Resources.logs(), "Logs"),

        ]

        for index, (icon, text) in enumerate(pages):

            item = NavigationItem(
                icon,
                text,
            )

            #
            # NavigationItem.clicked besitzt
            # keine Parameter.
            #

            item.clicked.connect(
                lambda i=index: self.change_page(i)
            )

            self.navigation.addWidget(
                item
            )

            self.items.append(
                item
            )

        #
        # Trennlinie
        #

        separator = QFrame()

        separator.setFixedHeight(
            1
        )

        separator.setStyleSheet("""
        QFrame{

            background:#323743;

            border:none;
        }
        """)

        self.navigation.addSpacing(
            12
        )

        self.navigation.addWidget(
            separator
        )

        self.navigation.addSpacing(
            14
        )

    # ---------------------------------------------------------
    # Systemstatus
    # ---------------------------------------------------------

    def build_status(self):

        from PySide6.QtSvgWidgets import QSvgWidget
        from PySide6.QtWidgets import QHBoxLayout

        self.status = QFrame()

        self.status.setObjectName(
            "sidebarStatus"
        )

        self.status.setStyleSheet("""
        QFrame#sidebarStatus{

            background:qlineargradient(
                x1:0,
                y1:0,
                x2:0,
                y2:1,
                stop:0 #242933,
                stop:1 #1A1E25
            );

            border:1px solid #383D48;

            border-radius:18px;
        }
        """)

        layout = QVBoxLayout(self.status)

        layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        layout.setSpacing(14)

        #
        # Titel
        #

        title = QLabel("SYSTEMSTATUS")

        title.setStyleSheet("""
        QLabel{
            color:#C9CFD9;
            font-size:11px;
            font-weight:700;
            letter-spacing:1px;
            background:transparent;
        }
        """)

        layout.addWidget(title)

        #
        # Helfer
        #

        def create_status_row(icon_path):

            row = QHBoxLayout()
            row.setSpacing(10)

            icon = QSvgWidget(icon_path)
            icon.setFixedSize(18, 18)

            label = QLabel()

            label.setStyleSheet("""
            QLabel{
                color:white;
                font-size:13px;
                background:transparent;
            }
            """)

            row.addWidget(icon)
            row.addWidget(label, 1)

            return row, label

        #
        # Companion
        #

        row, self.companion_status = create_status_row(
            Resources.companion()
        )

        layout.addLayout(row)

        #
        # WeintCodex
        #

        row, self.addon_status = create_status_row(
            Resources.software()
        )

        layout.addLayout(row)

        #
        # WoW
        #

        row, self.wow_status = create_status_row(
            Resources.game()
        )

        layout.addLayout(row)

        #
        # Discord
        #

        row, self.discord_status = create_status_row(
            Resources.discord()
        )

        layout.addLayout(row)

        self.root.addWidget(
            self.status
        )

        self.root.addStretch()
    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------

    def build_footer(self):

        line = QFrame()

        line.setFixedHeight(1)

        line.setStyleSheet("""
        QFrame{

            background:#323743;

            border:none;
        }
        """)

        self.root.addWidget(
            line
        )

        self.root.addSpacing(
            12
        )

        footer = QLabel(
            "Powered by Daddler2419"
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setStyleSheet("""
        QLabel{

            color:#707785;

            font-size:11px;

            background:transparent;
        }
        """)

        self.root.addWidget(
            footer
        )

    # ---------------------------------------------------------
    # Paint
    # ---------------------------------------------------------

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
            SIDEBAR_RADIUS,
            SIDEBAR_RADIUS,
        )

        #
        # Hintergrund
        #

        background = QLinearGradient(
            rect.topLeft(),
            rect.bottomLeft(),
        )

        background.setColorAt(
            0,
            QColor("#23262F"),
        )

        background.setColorAt(
            0.45,
            QColor("#1B1F27"),
        )

        background.setColorAt(
            1,
            QColor("#15181E"),
        )

        painter.fillPath(
            path,
            background,
        )

        #
        # Goldener Glow oben
        #

        glow = QLinearGradient(

            rect.left(),

            rect.top(),

            rect.left() + 260,

            rect.top() + 180,

        )

        glow.setColorAt(
            0,
            QColor(212, 175, 55, 24),
        )

        glow.setColorAt(
            1,
            QColor(212, 175, 55, 0),
        )

        painter.fillPath(
            path,
            glow,
        )

        #
        # Rand
        #

        border = QLinearGradient(

            rect.topLeft(),

            rect.bottomRight(),

        )

        border.setColorAt(
            0,
            QColor("#6E5A2B"),
        )

        border.setColorAt(
            0.5,
            QColor("#3A3E47"),
        )

        border.setColorAt(
            1,
            QColor("#6E5A2B"),
        )

        painter.setPen(

            QPen(
                border,
                1.3,
            )

        )

        painter.drawRoundedRect(

            rect,

            SIDEBAR_RADIUS,

            SIDEBAR_RADIUS,

        )

        painter.end()

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

        #
        # Version
        #

        self.version.setText(
            f"Version {state.companion_version}"
        )

        #
        # Companion
        #

        if state.companion_update_available:

            self.companion_status.setText(
                f"Companion  v{VERSION}\nUpdate verfügbar"
            )

        else:

            self.companion_status.setText(
                f"Companion  v{VERSION}"
            )

        #
        # World of Warcraft
        #

        if state.wow_found:

            self.wow_status.setText(
                "World of Warcraft\nClassic gefunden"
            )

        else:

            self.wow_status.setText(
                "World of Warcraft\nNicht gefunden"
            )

        #
        # WeintCodex
        #

        if state.addon_found:

            self.addon_status.setText(
                f"WeintCodex\nVersion {state.addon_version}"
            )

        else:

            self.addon_status.setText(
                "WeintCodex\nNicht installiert"
            )

        #
        # Discord
        #

        if state.discord_connected:

            if state.discord_latency is not None:

                self.discord_status.setText(
                    f"Discord Bot\n{state.discord_name}\n{state.discord_latency} ms"
                )

            else:

                self.discord_status.setText(
                    f"Discord Bot\n{state.discord_name}"
                )

        else:

            self.discord_status.setText(
                "Discord Bot\nOffline"
            )