from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics


class Card(QFrame):
    """
    Flaches Karten-Panel im "Command Deck"-Stil:
    einfarbiger Hintergrund, 1px Rahmen, keine Farbverläufe/Glows.
    """

    def __init__(self, accent: bool = False, parent=None):
        super().__init__(parent)

        self.setObjectName("card")

        border_color = (
            Colors.BORDER_ACCENT
            if accent
            else Colors.BORDER
        )

        self.setStyleSheet(f"""
        QFrame#card{{
            background:{Colors.CARD};
            border:1px solid {border_color};
            border-radius:{Metrics.RADIUS_CARD}px;
        }}
        """)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(20, 18, 20, 18)
        self.root.setSpacing(14)

    # --------------------------------------------------

    def addWidget(self, widget):
        self.root.addWidget(widget)

    def addLayout(self, layout):
        self.root.addLayout(layout)

    def addSpacing(self, value):
        self.root.addSpacing(value)

    def addStretch(self):
        self.root.addStretch()
