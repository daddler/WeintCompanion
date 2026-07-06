from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPen,
)

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractItemView,
    QGraphicsDropShadowEffect,
)

from core.logger import LogEntry
from core.resources import Resources
from PySide6.QtSvgWidgets import QSvgWidget


CARD_RADIUS = 20


class LogWidget(QWidget):

    MAX_ENTRIES = 250

    def __init__(self, logger):

        super().__init__()

        self.logger = logger

        #
        # Shadow
        #

        shadow = QGraphicsDropShadowEffect(self)

        shadow.setBlurRadius(28)

        shadow.setOffset(0, 12)

        shadow.setColor(QColor(0, 0, 0, 90))

        self.setGraphicsEffect(shadow)

        #
        # Root
        #

        root = QVBoxLayout(self)

        root.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        root.setSpacing(18)

        #
        # Header
        #

        header = QHBoxLayout()

        header.setSpacing(10)

        root.addLayout(header)

        #
        # Titel
        #

        icon = QSvgWidget(Resources.logs())
        icon.setFixedSize(22, 22)

        header.addWidget(icon)

        self.title = QLabel("Live-Protokoll")

        self.title.setStyleSheet("""
        QLabel{

            color:white;

            font-size:18px;

            font-weight:700;

            background:transparent;
        }
        """)

        header.addWidget(self.title)

        header.addStretch()

        #
        # Live Badge
        #

        self.live = QLabel("● LIVE")

        self.live.setAlignment(Qt.AlignCenter)

        self.live.setFixedHeight(28)

        self.live.setStyleSheet("""
        QLabel{

            background:rgba(67,192,122,22);

            color:#7DDB9E;

            border:1px solid rgba(67,192,122,65);

            border-radius:14px;

            padding-left:12px;

            padding-right:12px;

            font-size:11px;

            font-weight:700;
        }
        """)

        header.addWidget(self.live)

        #
        # Log Liste
        #

        self.list = QListWidget()

        self.list.setAlternatingRowColors(False)

        self.list.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.list.setFocusPolicy(
            Qt.NoFocus
        )

        self.list.setFrameShape(
            QListWidget.NoFrame
        )

        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.list.setStyleSheet("""
        QListWidget{

            background:transparent;

            border:none;

            color:white;

            outline:none;

            font-size:13px;
        }

        QListWidget::item{

            padding:10px;

            border-bottom:1px solid rgba(255,255,255,8);
        }

        QListWidget::item:last{

            border:none;
        }
        """)

        root.addWidget(
            self.list,
            1,
        )

        #
        # History laden
        #

        self.refresh()

        #
        # Logger abonnieren
        #

        self.logger.subscribe(
            self.add_entry
        )

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

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
            CARD_RADIUS,
            CARD_RADIUS,
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
            QColor("#252933"),
        )

        gradient.setColorAt(
            0.45,
            QColor("#1C2028"),
        )

        gradient.setColorAt(
            1,
            QColor("#171A21"),
        )

        painter.fillPath(
            path,
            gradient,
        )

        #
        # Goldener Glow links oben
        #

        glow = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left() + 250,
            rect.top() + 170,
        )

        glow.setColorAt(
            0,
            QColor(212, 175, 55, 35),
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
        # Rahmen
        #

        border = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        border.setColorAt(
            0,
            QColor("#6F5D2E"),
        )

        border.setColorAt(
            0.5,
            QColor("#3D404A"),
        )

        border.setColorAt(
            1,
            QColor("#6F5D2E"),
        )

        painter.setPen(
            QPen(
                border,
                1.4,
            )
        )

        painter.drawRoundedRect(
            rect,
            CARD_RADIUS,
            CARD_RADIUS,
        )

        painter.end()

    # --------------------------------------------------
    # Refresh
    # --------------------------------------------------

    def refresh(self):

        self.list.clear()

        for entry in self.logger.entries():

            self.add_entry(entry)

    # --------------------------------------------------
    # Add Entry
    # --------------------------------------------------

    def add_entry(self, entry: LogEntry):

        timestamp = entry.timestamp.strftime(
            "%H:%M:%S"
        )

        icons = {

            "info": "ℹ",

            "success": "✓",

            "warning": "⚠",

            "error": "✕",
        }

        colors = {

            "info": "#C8CDD8",

            "success": "#7ED957",

            "warning": "#E8C96D",

            "error": "#F08C8C",
        }

        icon = icons.get(
            entry.level,
            "•",
        )

        item = QListWidgetItem(
            f"{timestamp}    {icon}    {entry.message}"
        )

        item.setForeground(
            QColor(
                colors.get(
                    entry.level,
                    "#FFFFFF",
                )
            )
        )

        self.list.addItem(item)

        self.list.scrollToBottom()

        while (
            self.list.count()
            > self.MAX_ENTRIES
        ):

            self.list.takeItem(0)

        # --------------------------------------------------
    # Clear
    # --------------------------------------------------

    def clear(self):
        """Leert das Protokoll."""

        self.list.clear()

    # --------------------------------------------------
    # Live Badge
    # --------------------------------------------------

    def set_live(self, active: bool = True):

        if active:

            self.live.setText("● LIVE")

            self.live.setStyleSheet("""
            QLabel{

                background:rgba(67,192,122,22);

                color:#7DDB9E;

                border:1px solid rgba(67,192,122,65);

                border-radius:14px;

                padding-left:12px;
                padding-right:12px;

                font-size:11px;

                font-weight:700;
            }
            """)

        else:

            self.live.setText("● PAUSIERT")

            self.live.setStyleSheet("""
            QLabel{

                background:rgba(212,175,55,20);

                color:#E8C96D;

                border:1px solid rgba(212,175,55,70);

                border-radius:14px;

                padding-left:12px;
                padding-right:12px;

                font-size:11px;

                font-weight:700;
            }
            """)

    # --------------------------------------------------
    # Scroll
    # --------------------------------------------------

    def scroll_to_bottom(self):

        self.list.scrollToBottom()

    # --------------------------------------------------
    # Logger trennen
    # --------------------------------------------------

    def closeEvent(self, event):

        self.logger.unsubscribe(
            self.add_entry
        )

        super().closeEvent(event)