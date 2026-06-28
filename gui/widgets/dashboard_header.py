from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from core.resources import Resources


class DashboardHeader(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("dashboardHeader")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(12)

        #
        # -------------------------------------------------
        # Banner
        # -------------------------------------------------
        #

        self.banner = QLabel()
        self.banner.setAlignment(Qt.AlignCenter)

        pix = QPixmap(Resources.banner())

        if not pix.isNull():

            self.banner.setPixmap(
                pix.scaledToWidth(
                    900,
                    Qt.SmoothTransformation,
                )
            )

        layout.addWidget(self.banner)

        #
        # -------------------------------------------------
        # Titel
        # -------------------------------------------------
        #

        self.title = QLabel("Dashboard")
        self.title.setObjectName("title")

        layout.addWidget(self.title)

        #
        # -------------------------------------------------
        # Untertitel
        # -------------------------------------------------
        #

        self.subtitle = QLabel(
            "Verwalte deinen WeintCodex, installiere Updates und behalte deine Installation im Blick."
        )

        self.subtitle.setObjectName("subtitle")
        self.subtitle.setWordWrap(True)

        layout.addWidget(self.subtitle)

        #
        # -------------------------------------------------
        # Trennlinie
        # -------------------------------------------------
        #

        self.divider = QFrame()

        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Plain)

        self.divider.setStyleSheet("""
            background:#323542;
            min-height:1px;
            max-height:1px;
            border:none;
        """)

        layout.addWidget(self.divider)