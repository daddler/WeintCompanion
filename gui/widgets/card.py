"""
WeintCompanion 2.0
Die Karte

Der sichtbarste Unterschied zu 1.7 und der Kern der Leitidee: **eine
Karte hat keinen umlaufenden Rahmen.**

Bis 1.7 war jede Karte eine einfarbige Fläche mit einem 1-px-Rahmen
ringsum. Bei zwei Karten sieht das ordentlich aus; bei einem Dashboard
aus zwölf Karten, Kacheln und Abschnitten entsteht ein Gitter aus
Kästen, in dem nichts mehr vor oder hinter etwas anderem liegt - genau
der "Bootstrap-Admin-Panel im Dark Mode"-Eindruck, den der Entwurf
ausdrücklich vermeiden will.

Höhe entsteht hier stattdessen aus zwei gemalten Mitteln:

1. **Ein senkrechter Verlauf** `#121217 -> #0C0C0F`, oben heller. Eine
   gleichmäßig gefüllte Fläche wirkt flach, sobald ihr der Rahmen
   fehlt; der Verlauf gibt ihr eine Richtung.
2. **Eine 1-px-Oberkante** in Weiß bei 6 %. Sie liest sich als Licht,
   das von oben auf eine erhabene Fläche fällt - und ersetzt damit den
   Schatten, den Qt nur als teuren Einzeleffekt je Widget könnte.

Beides wird in `paintEvent` gemalt und nicht über das Stylesheet
gesetzt: Qt kann eine Kante nicht auf eine einzelne Seite einer
abgerundeten Fläche legen, ohne dass sie an den Ecken über die Rundung
hinausläuft.

Die Variante `accent` ist für die **eine** Karte je Ansicht, die eine
Handlung trägt (die nächste Lektion, das laufende Update): dieselbe
Form, aber die Oberkante in Akzentfarbe und eine leicht getönte Fläche.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QVBoxLayout

from gui.theme import tokens
from gui.theme.theme_manager import theme


class Card(QFrame):
    """
    Basisklasse für alle Karten und Kacheln.
    """

    def __init__(
        self,
        accent: bool = False,
        radius: int | None = None,
        parent=None,
    ):

        super().__init__(parent)

        self.setObjectName("card")

        self._accent = accent

        self._radius = (
            radius
            if radius is not None
            else tokens.RADIUS["lg"]
        )

        #
        # Eine eigene Oberkantenfarbe - gesetzt von Karten, die einen
        # Zustand tragen (die hervorgehobene Bewertungskachel der
        # Academy trägt `state.error` bei 28 %).
        #

        self._edge_override: str | None = None

        self._surface_override: tuple[str, str] | None = None

        density = theme().density()

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            density["pad_h"],
            density["pad_v"],
            density["pad_h"],
            density["pad_v"],
        )

        self.root.setSpacing(density["gap"] // 2)

        #
        # Der Akzentwechsel färbt die Oberkante der Akzentkarte um.
        # Gelesen wird die Farbe im paintEvent, hier wird nur das
        # Neuzeichnen angestoßen.
        #

        theme().accent_changed.connect(self._on_accent_changed)

    # --------------------------------------------------

    def _on_accent_changed(self, _name: str):

        if self._accent:
            self.update()

    # --------------------------------------------------

    def setAccent(self, accent: bool):

        if accent == self._accent:
            return

        self._accent = accent

        self.update()

    def setEdgeColor(self, color: str | None):
        """
        Die Oberkante einfärben - für Karten, die einen Zustand tragen.
        `None` stellt die neutrale Kante wieder her.
        """

        if color == self._edge_override:
            return

        self._edge_override = color

        self.update()

    def setSurface(self, top: str | None, bottom: str | None = None):
        """
        Die Fläche überschreiben. Für die hervorgehobene Kachel, deren
        Grund leicht in die Zustandsfarbe gezogen ist.
        """

        override = None if top is None else (top, bottom or top)

        if override == self._surface_override:
            return

        self._surface_override = override

        self.update()

    # --------------------------------------------------
    # Weiterreichen an das eigene Layout
    # --------------------------------------------------

    def addWidget(self, widget, *args, **kwargs):
        self.root.addWidget(widget, *args, **kwargs)

    def addLayout(self, layout, *args, **kwargs):
        self.root.addLayout(layout, *args, **kwargs)

    def addSpacing(self, value):
        self.root.addSpacing(value)

    def addStretch(self, value: int = 0):
        self.root.addStretch(value)

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.0, 0.0, -0.5, -0.5)

        #
        # Fläche
        #

        if self._surface_override is not None:
            top, bottom = self._surface_override

        elif self._accent:
            top, bottom = tokens.CARD_GRADIENT_ACCENT

        else:
            top, bottom = tokens.CARD_GRADIENT

        gradient = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left(),
            rect.bottom(),
        )

        gradient.setColorAt(0.0, QColor(top))
        gradient.setColorAt(1.0, QColor(bottom))

        painter.setPen(Qt.NoPen)

        painter.setBrush(gradient)

        painter.drawRoundedRect(rect, self._radius, self._radius)

        #
        # Oberkante
        #
        # Sie läuft nicht über die volle Breite, sondern endet an den
        # Rundungen - sonst stünde an beiden oberen Ecken ein heller
        # Punkt außerhalb der Fläche.
        #

        edge = self._edge_color()

        if edge is None:
            return

        painter.setBrush(Qt.NoBrush)

        pen = QPen(QColor(edge), 1)

        pen.setCapStyle(Qt.FlatCap)

        painter.setPen(pen)

        inset = self._radius * 0.55

        y = rect.top() + 0.5

        painter.drawLine(
            QRectF(rect.left() + inset, y, 0, 0).topLeft(),
            QRectF(rect.right() - inset, y, 0, 0).topLeft(),
        )

    def _edge_color(self) -> str | None:

        if self._edge_override is not None:
            return self._edge_override

        if self._accent:

            return tokens.tint(theme().accent_base(), 0.34)

        return tokens.EDGE_TOP
