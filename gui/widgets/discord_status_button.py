from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from core.resources import Resources

#
# Discord "Blurple" - verbunden - und ein neutraler Grauton -
# nicht verbunden -, damit der Zustand auf einen Blick erkennbar ist.
#

CONNECTED_STYLE = """
QPushButton{
    background:rgba(88,101,242,35);
    color:#C9CDFB;
    border:1px solid rgba(88,101,242,120);
    border-radius:16px;
    padding-left:14px;
    padding-right:14px;
    font-size:12px;
    font-weight:700;
}
QPushButton:hover{
    background:rgba(88,101,242,55);
}
"""

DISCONNECTED_STYLE = """
QPushButton{
    background:rgba(255,255,255,10);
    color:#AEB4C2;
    border:1px solid rgba(255,255,255,30);
    border-radius:16px;
    padding-left:14px;
    padding-right:14px;
    font-size:12px;
    font-weight:700;
}
QPushButton:hover{
    background:rgba(255,255,255,20);
}
"""


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
            QIcon(Resources.discord())
        )

        self.setIconSize(QSize(16, 16))

        self.setFixedHeight(32)

        self.setFlat(True)

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
                "  Nicht verbunden"
            )

            self.setStyleSheet(
                DISCONNECTED_STYLE
            )

            self.setToolTip(
                "Nicht mit Discord verbunden - Klicken zum Verbinden"
            )
