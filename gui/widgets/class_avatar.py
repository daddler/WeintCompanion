"""
Das Charakterbild.

In WeintCodex trägt die Charakterrubrik links oben ein Porträt: ein
`PlayerModel`, also der tatsächlich angemeldete Charakter in 3D. Auf
dem Desktop gibt es dieses Modell nicht - die Client-Grafik liegt in
CASC, nicht als Datei, und der Ausrüstungsbericht (`character_sheet`)
trägt weder Volk noch Geschlecht, aus denen sich eines bauen ließe.

Was er trägt, ist die **Klasse**, und die ist im Spiel ohnehin das,
was ein Porträt auf einen Blick beantwortet. Diese Kachel zeichnet
deshalb das Klassenwappen in Klassenfarbe auf einer in dieselbe Farbe
getönten Fläche - dieselbe Stelle, dieselbe Größe und dieselbe Rolle
wie das Porträt im Spiel, nur mit der Auskunft, die auf diesem Rechner
tatsächlich vorliegt.

Drei Dinge, die dabei nicht Geschmack sind:

* **Eine unbekannte Klasse bekommt kein Wappen.** `class_icon()`
  liefert dann `None`, und die Kachel zeigt ein neutrales Zeichen in
  gedämpfter Farbe. Ein geratenes Wappen wäre von einem gemeldeten
  nicht zu unterscheiden - dieselbe Regel wie `stars == 0` im
  Analyzer.
* **Die Fläche wird gemischt, nicht überlagert.** `tokens.mix()`
  liefert einen deckenden Wert; eine `rgba`-Tönung ist für das
  Stylesheet gedacht, hier wird gemalt.
* **Die Farbe wird im `paintEvent` gelesen.** Sie hängt zwar an der
  Klasse und nicht am Akzent, aber die Grundfläche kommt aus den
  Tokens, und ein im `__init__` eingefrorener Wert ist genau der
  Fehler, den das Theme an sechs Stellen schon einmal hatte.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme import tokens
from gui.theme.icons import tinted_pixmap
from gui.theme.wow_colors import class_color, class_icon, class_label


#
# Das Wappen füllt nicht die ganze Kachel: es steht wie ein Porträt in
# einem Rahmen, und der Rand ringsum ist der Unterschied zwischen
# "Bild" und "großes Symbol".
#

GLYPH_RATIO = 0.58


class ClassAvatar(QWidget):
    """
    Eine quadratische Kachel mit dem Klassenwappen.
    """

    def __init__(self, class_name: str, size: int = 56, parent=None):

        super().__init__(parent)

        self._class = class_name or ""

        self._size = size

        self.setFixedSize(size, size)

        #
        # Für die Maus: die Klasse steht zwar auch als Text unter dem
        # Namen, aber wer auf das Bild zeigt, fragt nach dem Bild.
        #

        self.setToolTip(
            class_label(self._class) or "Unbekannte Klasse"
        )

    # --------------------------------------------------

    def setClass(self, class_name: str):

        class_name = class_name or ""

        if class_name == self._class:
            return

        self._class = class_name

        self.setToolTip(
            class_label(self._class) or "Unbekannte Klasse"
        )

        self.update()

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        radius = tokens.RADIUS["md"]

        icon = class_icon(self._class)

        #
        # Ohne gemeldete Klasse bleibt die Kachel neutral. Sie
        # verschwindet nicht: die Karte behält ihre Form, und der
        # leere Platz wäre die zweite Behauptung nach dem falschen
        # Wappen.
        #

        color = (
            class_color(self._class)
            if icon is not None
            else tokens.TEXT["muted"]
        )

        #
        # Fläche: die Klassenfarbe, weit in den Kartengrund gezogen.
        #

        gradient = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left(),
            rect.bottom(),
        )

        gradient.setColorAt(
            0.0,
            QColor(tokens.mix(color, tokens.SURFACE["card"], 0.22)),
        )

        gradient.setColorAt(
            1.0,
            QColor(tokens.mix(color, tokens.SURFACE["card"], 0.07)),
        )

        painter.setPen(Qt.NoPen)

        painter.setBrush(gradient)

        painter.drawRoundedRect(rect, radius, radius)

        #
        # Rahmen
        #

        pen = QPen(
            QColor(tokens.mix(color, tokens.BORDER["base"], 0.38)),
            1,
        )

        painter.setPen(pen)

        painter.setBrush(Qt.NoBrush)

        painter.drawRoundedRect(rect, radius, radius)

        #
        # Wappen
        #

        glyph = int(round(self._size * GLYPH_RATIO))

        pixmap = tinted_pixmap(
            icon if icon is not None else "charaktere",
            color,
            glyph,
        )

        painter.drawPixmap(
            (self._size - glyph) // 2,
            (self._size - glyph) // 2,
            pixmap,
        )
