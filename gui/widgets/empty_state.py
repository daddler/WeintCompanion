"""
WeintCompanion 2.0
Der Leerzustand

Regel des Entwurfs (§6.5): **jeder Leerzustand hat genau einen
nächsten Schritt.**

Das ist keine Gestaltungsvorliebe. Ein leerer Bereich mit drei
gleichwertigen Knöpfen verschiebt die Entscheidung, welcher der
richtige ist, auf den Nutzer - und zwar in dem Moment, in dem er am
wenigsten weiß, weil ja gerade nichts da ist. Deshalb nimmt dieses
Widget genau **einen** Hauptknopf entgegen; ein zweiter ist nur als
zurückhaltender Nebenweg vorgesehen (`secondary_action`), etwa
"Protokoll ansehen" neben "Erneut verbinden".

Aufbau: Symbolplakette 44 px, Rubrik, Titel, Erklärung (höchstens
420 px breit, damit die Zeilen lesbar kurz bleiben), ein Knopf.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.icons import tinted_pixmap
from gui.theme.restyle import restyle
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.status_dot import StatusDot
from gui.widgets.wrapped_label import WrappedLabel


#
# Die Erklärung wird umgebrochen, nicht gestreckt: eine Zeile über die
# volle Fensterbreite ist bei 1440 px rund 200 Zeichen lang und damit
# unlesbar.
#

EXPLANATION_WIDTH = 420


class EmptyState(QWidget):

    actionTriggered = Signal()

    secondaryTriggered = Signal()

    def __init__(
        self,
        eyebrow: str = "",
        title: str = "",
        explanation: str = "",
        action: str = "",
        icon: str = "",
        state: str = "",
        secondary_action: str = "",
        parent=None,
    ):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[2])

        root.addStretch(1)

        #
        # Symbolplakette - oder, wenn der Zustand eine Bedeutung hat,
        # ein Statuspunkt. "Keine Verbindung zum Bot" ist ein Fehler
        # und soll als solcher erkennbar sein, "kein Raid aktiv" ist
        # keiner.
        #

        if icon:

            self.badge = QLabel()

            self.badge.setFixedSize(44, 44)

            self.badge.setAlignment(Qt.AlignCenter)

            self.badge.setPixmap(
                tinted_pixmap(icon, tokens.TEXT["muted"], 22)
            )

            restyle(
                self.badge,
                f"""
                QLabel{{
                    background:{tokens.SURFACE["card"]};
                    border-radius:{tokens.RADIUS["md"]}px;
                }}
                """,
            )

            root.addWidget(self.badge, alignment=Qt.AlignHCenter)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(8)

        header.addStretch(1)

        if state:

            header.addWidget(
                StatusDot(state),
                alignment=Qt.AlignVCenter,
            )

        self.eyebrow = eyebrow_label(
            eyebrow,
            tokens.STATE_TEXT.get(state, tokens.TEXT["muted"]),
        )

        header.addWidget(self.eyebrow)

        header.addStretch(1)

        root.addLayout(header)

        self.title = QLabel(title)

        self.title.setFont(font("section"))

        self.title.setAlignment(Qt.AlignCenter)

        restyle(
            self.title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        root.addWidget(self.title)

        #
        # WrappedLabel statt QLabel: ein umbrechendes QLabel meldet in
        # einem senkrechten Layout die Höhe einer einzigen Zeile und
        # lässt die folgenden Widgets über sich zeichnen. Siehe
        # gui/widgets/wrapped_label.py.
        #

        self.explanation = WrappedLabel(explanation, EXPLANATION_WIDTH)

        self.explanation.setAlignment(Qt.AlignCenter)

        self.explanation.setFont(font("small"))

        restyle(
            self.explanation,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(
            self.explanation,
            alignment=Qt.AlignHCenter,
        )

        root.addSpacing(tokens.SPACE[1])

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[1])

        buttons.addStretch(1)

        self.button = QPushButton(action)

        self.button.setVisible(bool(action))

        self.button.setCursor(Qt.PointingHandCursor)

        self.button.clicked.connect(self.actionTriggered.emit)

        buttons.addWidget(self.button)

        self.secondary = QPushButton(secondary_action)

        self.secondary.setObjectName("secondary")

        self.secondary.setVisible(bool(secondary_action))

        self.secondary.setCursor(Qt.PointingHandCursor)

        self.secondary.clicked.connect(self.secondaryTriggered.emit)

        buttons.addWidget(self.secondary)

        buttons.addStretch(1)

        root.addLayout(buttons)

        root.addStretch(1)

    # --------------------------------------------------

    def update_texts(
        self,
        eyebrow: str | None = None,
        title: str | None = None,
        explanation: str | None = None,
        action: str | None = None,
    ):
        """
        Denselben Leerzustand für eine andere Lage beschriften, statt
        ihn neu zu bauen.
        """

        if eyebrow is not None:
            self.eyebrow.setText(eyebrow)

        if title is not None:
            self.title.setText(title)

        if explanation is not None:
            self.explanation.setText(explanation)

        if action is not None:

            self.button.setText(action)

            self.button.setVisible(bool(action))
