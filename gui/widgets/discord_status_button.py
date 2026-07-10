from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from core.resources import Resources

#
# Discord "Blurple" (#5865F2, die offizielle Markenfarbe) durchgehend
# als Hintergrund - so wie Discords eigene "Mit Discord verbinden"-
# Buttons. Der Verbindungsstatus wird stattdessen über einen kleinen
# Präsenz-Punkt (grün/grau, wie Discords Online-Indikator) und den
# Text unterschieden, nicht über eine andere Grundfarbe.
#

BASE_STYLE = """
QPushButton{{
    background:{bg};
    color:#FFFFFF;
    border:none;
    border-radius:16px;
    padding-left:12px;
    padding-right:14px;
    font-size:12px;
    font-weight:700;
    text-align:left;
}}
QPushButton:hover{{
    background:{bg_hover};
}}
QPushButton:pressed{{
    background:{bg_pressed};
}}
"""

CONNECTED_STYLE = BASE_STYLE.format(
    bg="#5865F2",
    bg_hover="#6A75F5",
    bg_pressed="#4752C4",
)

DISCONNECTED_STYLE = BASE_STYLE.format(
    bg="#454B54",
    bg_hover="#50565F",
    bg_pressed="#3A3F47",
)


class DiscordStatusButton(QPushButton):
    """
    Persistenter Discord-Verbindungsstatus oben rechts, auf jeder
    Seite sichtbar. Klick öffnet die Einstellungen (dort lässt sich
    die Verknüpfung herstellen/trennen).
    """

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.setCursor(Qt.PointingHandCursor)

        self.setIcon(
            QIcon(Resources.discord_mark())
        )

        self.setIconSize(QSize(18, 18))

        self.setFixedHeight(34)

        self.setMinimumWidth(120)

        #
        # Lokale Datei ist billig zu lesen - ein einfacher Timer
        # reicht, statt jede Login/Unlink-Stelle einzeln zu verdrahten.
        #

        self._timer = QTimer(self)

        self._timer.timeout.connect(
            self.refresh
        )

        self._timer.start(3000)

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        account = self.manager.discord_account.load()

        if account:

            username = account.get(
                "username",
                "Discord",
            )

            self.setText(
                f"  {username}"
            )

            self.setStyleSheet(
                CONNECTED_STYLE
            )

            self.setToolTip(
                "Mit Discord verbunden - Klicken für Einstellungen"
            )

        else:

            self.setText(
                "  Discord verbinden"
            )

            self.setStyleSheet(
                DISCONNECTED_STYLE
            )

            self.setToolTip(
                "Nicht mit Discord verbunden - Klicken zum Verbinden"
            )
