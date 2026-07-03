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
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)

from gui.widgets.navigation_item import NavigationItem
from core.resources import Resources
from core.version import VERSION


SIDEBAR_RADIUS = 26


class Sidebar(QFrame):

    pageChanged = Signal(int)

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.setFixedWidth(305)

        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        #
        # Root
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
        # -------------------------------------------------
        # Header
        # -------------------------------------------------
        #

        header = QVBoxLayout()

        header.setSpacing(8)

        self.root.addLayout(header)

        #
        # Logo
        #

        self.logo = QLabel()

        self.logo.setAlignment(Qt.AlignCenter)

        pix = QPixmap(Resources.logo())

        if not pix.isNull():

            self.logo.setPixmap(

                pix.scaled(

                    126,

                    126,

                    Qt.KeepAspectRatio,

                    Qt.SmoothTransformation,

                )

            )

        header.addWidget(self.logo)

        #
        # Titel
        #

        self.title = QLabel(
            "WeintCompanion"
        )

        self.title.setAlignment(
            Qt.AlignCenter
        )

        self.title.setStyleSheet("""
        QLabel{

            color:white;

            font-size:22px;

            font-weight:800;

            letter-spacing:0.4px;

            background:transparent;
        }
        """)

        header.addWidget(self.title)

        #
        # Badge
        #

        self.badge = QLabel(
            "MoP CLASSIC"
        )

        self.badge.setAlignment(
            Qt.AlignCenter
        )

        self.badge.setFixedHeight(28)

        self.badge.setFixedWidth(118)

        self.badge.setStyleSheet("""
        QLabel{

            background:rgba(214,176,77,18);

            color:#E6C86B;

            border:1px solid rgba(214,176,77,55);

            border-radius:14px;

            font-size:10px;

            font-weight:700;

            letter-spacing:0.8px;
        }
        """)

        header.addWidget(
            self.badge,
            alignment=Qt.AlignCenter,
        )

        #
        # Version
        #

        self.version_label = QLabel(
            f"Version {VERSION}"
        )

        self.version_label.setAlignment(
            Qt.AlignCenter
        )

        self.version_label.setStyleSheet("""
        QLabel{

            color:#8F97A6;

            background:transparent;

            font-size:12px;
        }
        """)

        header.addWidget(
            self.version_label
        )

        self.root.addSpacing(20)

        #
        # Navigation
        #

        self.navigation = QVBoxLayout()

        self.navigation.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.navigation.setSpacing(6)

        self.root.addLayout(
            self.navigation
        )

        self.items = []

        pages = [

            (Resources.home(), "Dashboard"),

            (Resources.package(), "WeintCodex"),

            (Resources.sync(), "Synchronisation"),

            (Resources.settings(), "Einstellungen"),

            (Resources.logs(), "Logs"),

        ]

                #
        # Navigation
        #

        for index, (icon, text) in enumerate(pages):

            item = NavigationItem(icon, text)

            item.clicked.connect(
                lambda i=index: self.change_page(i)
            )

            self.navigation.addWidget(item)

            self.items.append(item)

        self.navigation.addStretch()

        #
        # -------------------------------------------------
        # Status Card
        # -------------------------------------------------
        #

        self.status = QFrame()

        self.status.setMinimumHeight(150)

        self.status.setStyleSheet("""
        QFrame{

            background:qlineargradient(
                x1:0,
                y1:0,
                x2:0,
                y2:1,
                stop:0 #262A33,
                stop:1 #1B1E25
            );

            border:1px solid rgba(255,255,255,18);

            border-radius:18px;
        }
        """)

        status_layout = QVBoxLayout(self.status)

        status_layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        status_layout.setSpacing(8)

        #
        # Status Titel
        #

        status_title = QLabel(
            "● Companion bereit"
        )

        status_title.setStyleSheet("""
        QLabel{

            color:#74D98E;

            font-size:13px;

            font-weight:700;

            background:transparent;
        }
        """)

        status_layout.addWidget(status_title)

        #
        # Version
        #

        self.status_version = QLabel(
            f"Version {VERSION}"
        )

        self.status_version.setStyleSheet("""
        QLabel{

            color:white;

            font-size:22px;

            font-weight:700;

            background:transparent;
        }
        """)

        status_layout.addWidget(
            self.status_version
        )

        #
        # Addon Status
        #

        self.addon = QLabel(
            "📦 WeintCodex\nWird geprüft..."
        )

        self.addon.setWordWrap(True)

        self.addon.setStyleSheet("""
        QLabel{

            color:#9EA5B3;

            font-size:12px;

            line-height:18px;

            background:transparent;
        }
        """)

        status_layout.addWidget(
            self.addon
        )

        status_layout.addStretch()

        self.root.addWidget(
            self.status
        )

        #
        # Footer
        #

        footer = QLabel(
            "© Bis einer weint"
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setStyleSheet("""
        QLabel{

            color:#707785;

            font-size:12px;

            background:transparent;
        }
        """)

        self.root.addWidget(
            footer
        )

        #
        # Dashboard aktiv
        #

        self.refresh()

        self.items[0].setActive(True)

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

        gradient = QLinearGradient(
            rect.topLeft(),
            rect.bottomLeft(),
        )

        gradient.setColorAt(
            0,
            QColor("#23262F"),
        )

        gradient.setColorAt(
            0.45,
            QColor("#1B1E26"),
        )

        gradient.setColorAt(
            1,
            QColor("#15181E"),
        )

        painter.fillPath(
            path,
            gradient,
        )

        #
        # Goldener Glow oben
        #

        glow = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left() + 260,
            rect.top() + 200,
        )

        glow.setColorAt(
            0,
            QColor(212, 175, 55, 28),
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
            QColor("#3C3F49"),
        )

        border.setColorAt(
            1,
            QColor("#6E5A2B"),
        )

        painter.setPen(
            QPen(
                border,
                1.4,
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

        self.version_label.setText(
            f"Version {VERSION}"
        )

        self.status_version.setText(
            f"Version {VERSION}"
        )

        if state.addon_found:

            self.addon.setText(
                f"📦 WeintCodex\nVersion {state.addon_version}"
            )

        else:

            self.addon.setText(
                "📦 WeintCodex\nNicht installiert"
            )