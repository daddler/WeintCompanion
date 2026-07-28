"""
Pillenförmige Zeit-/Statusanzeige im Mono-Font.

Benutzt für Pull-Timer, Heldentum-Restzeit und den Kampfzustand.
Die getönten Hintergründe folgen der Schreibweise, die im Repo
bereits für Statusfarben verwendet wird (rgba(...) mit niedriger
Deckkraft, siehe STATE_COLORS in gui/widgets/status_card.py).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from gui.theme.colors import Colors


#
# Zustand -> (Textfarbe, Hintergrund, Rahmen)
#

CHIP_STATES: dict[str, tuple[str, str, str]] = {

    "neutral": (
        Colors.TEXT_SECONDARY,
        "rgba(255,255,255,12)",
        "rgba(255,255,255,24)",
    ),

    "primary": (
        Colors.PRIMARY_HOVER,
        "rgba(168,85,247,38)",
        Colors.PRIMARY,
    ),

    "success": (
        Colors.SUCCESS_LIGHT,
        "rgba(124,192,110,18)",
        "rgba(124,192,110,60)",
    ),

    "warning": (
        Colors.WARNING_LIGHT,
        "rgba(212,162,74,18)",
        "rgba(212,162,74,60)",
    ),

    "error": (
        Colors.ERROR_LIGHT,
        "rgba(229,107,107,18)",
        "rgba(229,107,107,60)",
    ),

    "info": (
        Colors.INFO_LIGHT,
        "rgba(139,149,245,18)",
        "rgba(139,149,245,60)",
    ),

}


class TimerChip(QLabel):

    def __init__(
        self,
        text: str = "-",
        state: str = "neutral",
        parent=None,
    ):

        super().__init__(text, parent)

        self.setAlignment(Qt.AlignCenter)

        self.setFixedHeight(26)

        self.setMinimumWidth(72)

        self._state = ""

        self.setState(state)

    # --------------------------------------------------

    def setState(self, state: str):

        if state == self._state:
            return

        self._state = state

        color, background, border = CHIP_STATES.get(
            state,
            CHIP_STATES["neutral"],
        )

        self.setStyleSheet(f"""
        QLabel{{
            background:{background};
            border:1px solid {border};
            color:{color};
            border-radius:13px;
            padding-left:12px;
            padding-right:12px;
            font-family:"JetBrains Mono";
            font-size:12px;
            font-weight:700;
            letter-spacing:0.05em;
        }}
        """)

    def state(self) -> str:

        return self._state

    # --------------------------------------------------

    def setValue(self, text: str, state: str = ""):
        """
        Text und Zustand in einem Aufruf - der übliche Fall beim
        Aktualisieren aus einem Snapshot.
        """

        if self.text() != text:

            self.setText(text)

        if state:

            self.setState(state)
