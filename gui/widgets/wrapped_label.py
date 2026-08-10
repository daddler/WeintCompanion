"""
Ein umbrechendes Label, das seine Höhe kennt.

`QLabel` mit `setWordWrap(True)` ist in senkrechten Layouts eine
verlässliche Fehlerquelle: seine `sizeHint()` beschreibt die Größe
**einer** Zeile, die tatsächliche Höhe ergibt sich aber erst aus der
Breite, die das Layout ihm zuteilt (`heightForWidth`). Ein
`QVBoxLayout` fragt das nicht immer ab - besonders dann nicht, wenn
das Element mit einer Ausrichtung hinzugefügt wurde. Das Ergebnis ist
ein Label, das mehr Zeilen zeichnet, als es für sich reklamiert hat,
und die folgenden Widgets überschreibt.

Sichtbar war das als Erklärungstext, der quer durch Titel und Knopf
eines Leerzustands lief.

Die Lösung hier ist absichtlich stumpf: die Breite steht fest, und die
Höhe wird bei jeder Textänderung mit `QFontMetrics` **ausgemessen**
statt geschätzt. Das ist der einzige Weg, der nicht davon abhängt,
wann und ob das Layout `heightForWidth` aufruft.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy


def enable_wrap(label: QLabel) -> QLabel:
    """
    Umbruch für ein Label mit **veränderlicher** Breite.

    `WrappedLabel` misst gegen eine feste Breite und ist deshalb der
    falsche Weg, sobald das Label mitwachsen soll. Hier hilft nur, Qt
    zu sagen, dass die Höhe von der Breite abhängt: `QLabel` beherrscht
    `heightForWidth()`, wenn `wordWrap` gesetzt ist, aber ein
    `QVBoxLayout` fragt es nur ab, wenn die **Größenrichtlinie** das
    ankündigt. Ohne dieses eine Flag meldet das Label die Höhe einer
    Zeile, und die folgenden Widgets werden darüber gezeichnet - genau
    die Überlagerung, die auf der Übersicht bei 960 px auftrat.
    """

    label.setWordWrap(True)

    policy = label.sizePolicy()

    policy.setHeightForWidth(True)

    label.setSizePolicy(policy)

    return label


class WrappedLabel(QLabel):

    def __init__(self, text: str = "", width: int = 420, parent=None):

        super().__init__(text, parent)

        self._wrap_width = width

        self.setWordWrap(True)

        self.setFixedWidth(width)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        self._measure()

    # --------------------------------------------------

    def setText(self, text: str):

        if text == self.text():
            return

        super().setText(text)

        self._measure()

    def setWrapWidth(self, width: int):

        if width == self._wrap_width:
            return

        self._wrap_width = width

        self.setFixedWidth(width)

        self._measure()

    def setFont(self, font):

        super().setFont(font)

        #
        # Die Schrift bestimmt die Höhe mit - nach einem Wechsel der
        # Dichte oder der Schriftrolle muss neu gemessen werden.
        #

        self._measure()

    # --------------------------------------------------

    def _measure(self):

        metrics = self.fontMetrics()

        rect = metrics.boundingRect(
            QRect(0, 0, self._wrap_width, 0),
            Qt.TextWordWrap | int(self.alignment()),
            self.text(),
        )

        self.setMinimumHeight(rect.height())
