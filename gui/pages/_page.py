"""
Gemeinsames Gerüst der Seiten.

Jede Seite hat denselben Kopf: eine Rubrik in `type.micro`, darunter
einen Titel in `type.title`, der **ein Satz** ist, und rechts Platz für
Handlungen. Der Titel als Satz ist eine bewusste Vorgabe des Entwurfs -
"Übersicht" ist eine Beschriftung, "Raid um 20:00. Du bist angemeldet."
ist eine Auskunft. Die Seite soll das Naheliegende sagen, nicht ihren
eigenen Namen wiederholen.

Die Ränder (24 px oben, 32 px seitlich) stehen hier und nicht in jeder
Seite einzeln, damit sie nicht auseinanderlaufen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.eyebrow import eyebrow_label


class PageHeader(QWidget):
    """
    Rubrik, Titel und rechts ein freier Bereich für Handlungen.
    """

    def __init__(self, eyebrow: str = "", title: str = "", parent=None):

        super().__init__(parent)

        self.setFixedHeight(60)

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[3])

        column = QVBoxLayout()

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(2)

        column.addStretch(1)

        self.eyebrow = eyebrow_label(eyebrow)

        column.addWidget(self.eyebrow)

        self.title = QLabel(title)

        self.title.setFont(font("title"))

        restyle(
            self.title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        column.addWidget(self.title)

        column.addStretch(1)

        root.addLayout(column, 1)

        #
        # Rechts: der Bereich, in den eine Seite ihre Handlungen hängt
        # (Countdown-Chip, "Erneut prüfen", ein SegmentedControl).
        #

        self.actions = QHBoxLayout()

        self.actions.setContentsMargins(0, 0, 0, 0)

        self.actions.setSpacing(tokens.SPACE[1])

        root.addLayout(self.actions)

    # --------------------------------------------------

    def setEyebrow(self, text: str):

        #
        # Vergleichen wie in setTitle(): die Übersicht setzt ihre
        # Begrüßung im Minutentakt und bei jeder Zustandsmeldung neu,
        # und `setText()` verwirft die Stilrechnung des Labels auch
        # dann, wenn derselbe Text ankommt (siehe gui/theme/restyle.py).
        #

        if self.eyebrow.text() == text:
            return

        self.eyebrow.setText(text)

    def setTitle(self, text: str):

        if self.title.text() == text:
            return

        self.title.setText(text)

    def addAction(self, widget):

        self.actions.addWidget(widget, alignment=Qt.AlignVCenter)


class Page(QWidget):
    """
    Basisklasse: Kopf plus ein senkrechter Inhaltsbereich.
    """

    pageRequested = Signal(int)

    openSettingsSection = Signal(str)

    def __init__(self, manager, eyebrow: str = "", title: str = "", parent=None):

        super().__init__(parent)

        self.manager = manager

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            tokens.SPACE[5],
            tokens.SPACE[4],
            tokens.SPACE[5],
            tokens.SPACE[4],
        )

        self.root.setSpacing(20)

        self.header = PageHeader(eyebrow, title)

        self.root.addWidget(self.header)

        self.body = QVBoxLayout()

        self.body.setContentsMargins(0, 0, 0, 0)

        self.body.setSpacing(20)

        self.root.addLayout(self.body, 1)

    # --------------------------------------------------

    def addWidget(self, widget, *args, **kwargs):

        self.body.addWidget(widget, *args, **kwargs)

    def addLayout(self, layout, *args, **kwargs):

        self.body.addLayout(layout, *args, **kwargs)
