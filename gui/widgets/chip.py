"""
WeintCompanion 2.0
Chip

Eine kurze, gerahmte Angabe in Versalien: `LIVE`, `HEROISCH`,
`KEINE DATEN`, `IN 02:14:31`. Zusammen mit dem `StatusDot` ersetzt er
die Emoji als Zustandsanzeige - der Punkt sagt *wie es steht*, der Chip
sagt *was es ist*.

Getönte Fläche statt Vollfläche: Grundfarbe mit rund 13 % Deckkraft,
1-px-Rahmen mit rund 38 % derselben Farbe, Text in der aufgehellten
Variante (§2.3). Eine vollflächig rote Fläche mit weißer Schrift wäre
in dieser Oberfläche ein Fremdkörper - und bei fünf Chips
nebeneinander eine Ampelanlage.

Die Variante `neutral` ist die für **"keine Daten"**: weiß bei 5 %,
Rahmen weiß bei 12 %, Text `text.secondary`. Sie darf nie rot sein -
fehlende Evidenz ist kein schlechtes Ergebnis, und ein rotes
`KEINE DATEN` würde eine Datenlücke als Befund ausgeben.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.status_dot import StatusDot


#
# Höhe aus §5. Der Chip ist eine Pille, seine Höhe ändert sich nicht
# mit der Dichte - er steht meist neben Text, dessen Zeilenhöhe sie
# ohnehin bestimmt.
#

CHIP_HEIGHT = 26


class Chip(QWidget):
    """
    `variant` ist eine der Bedeutungsfarben (ok/warn/error/live/info),
    `accent`, `neutral` oder `disabled`.
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "neutral",
        dot: bool = False,
        parent=None,
    ):

        super().__init__(parent)

        self.setObjectName("chip")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setFixedHeight(CHIP_HEIGHT)

        self._variant = variant

        root = QHBoxLayout(self)

        root.setContentsMargins(10, 0, 10, 0)

        root.setSpacing(6)

        #
        # Der Punkt ist optional und gehört zum Chip, nicht daneben:
        # ein LIVE-Chip ohne Punkt hätte keine Bewegung, und ein Punkt
        # neben dem Chip stünde in eigener Ausrichtung.
        #

        self.dot = StatusDot(
            variant if variant in tokens.STATE else "empty"
        )

        self.dot.setVisible(dot)

        root.addWidget(self.dot)

        self.label = QLabel(text)

        self.label.setFont(font("mono"))

        root.addWidget(self.label)

        self._apply()

    # --------------------------------------------------

    def setText(self, text: str):

        if self.label.text() == text:
            return

        self.label.setText(text)

    def text(self) -> str:

        return self.label.text()

    def setVariant(self, variant: str):

        if variant == self._variant:
            return

        self._variant = variant

        if self.dot.isVisible():

            self.dot.setState(
                variant if variant in tokens.STATE else "empty"
            )

        self._apply()

    def setDotVisible(self, visible: bool):

        self.dot.setVisible(visible)

    # --------------------------------------------------

    def _colors(self) -> tuple[str, str, str]:
        """
        Fläche, Rahmen, Text für die aktuelle Variante.
        """

        variant = self._variant

        if variant == "accent":

            base = theme().accent_base()

            return (
                tokens.tint(base, tokens.TINT_SURFACE),
                tokens.tint(base, tokens.TINT_BORDER),
                theme().accent_light(),
            )

        if variant == "disabled":

            return (
                "transparent",
                tokens.BORDER["base"],
                tokens.TEXT["faint"],
            )

        base = tokens.STATE.get(variant)

        if base is None:

            #
            # `neutral` und alles Unbekannte: weiß, sehr schwach. Das
            # ist der Zustand "keine Daten" - er darf keine
            # Bedeutungsfarbe tragen.
            #

            return (
                "rgba(255,255,255,0.050)",
                "rgba(255,255,255,0.120)",
                tokens.TEXT["secondary"],
            )

        return (
            tokens.tint(base, tokens.TINT_SURFACE),
            tokens.tint(base, tokens.TINT_BORDER),
            tokens.STATE_TEXT.get(variant, tokens.TEXT["primary"]),
        )

    def _apply(self):

        surface, border, text_color = self._colors()

        #
        # restyle() statt setStyleSheet(): Chips stehen in Kopfzeilen,
        # die im Sekundentakt neu beschriftet werden. setStyleSheet
        # vergleicht nicht, sondern verwirft die Stilrechnung und malt
        # neu - auch wenn sich nichts geändert hat.
        #

        restyle(
            self,
            f"""
            QWidget#chip{{
                background:{surface};
                border:1px solid {border};
                border-radius:{CHIP_HEIGHT // 2}px;
            }}
            """,
        )

        restyle(
            self.label,
            f"color:{text_color};background:transparent;border:none;",
        )
