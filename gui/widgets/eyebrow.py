"""
Kleine, gesperrte Mono-Überschrift ("Eyebrow").

Zwei Gründe für eine eigene Funktion, beide aus echten Fehlern:

**Die Laufweite.** Der Entwurf sperrt diese Labels weit (0.18em bei
11 px, 0.16em bei 10 px) - genau das gibt ihnen ihren Charakter. Bis
1.7 stand das hier als `letter-spacing` im Stylesheet, und **Qt kennt
diese Eigenschaft nicht**: sie wurde bei jedem `setStyleSheet`
kommentarlos verworfen. Die Rubriklabels waren also nie gesperrt, ohne
dass es irgendwo aufgefallen wäre. Gesetzt wird sie seit 2.0 über
`QFont.setLetterSpacing`, siehe `gui/theme/fonts.py`.

**Die Umlaute.** Bei 10 px ragen die Punkte über einem großgeschriebenen
Umlaut höher als die von der Schriftart angegebene Oberlänge. QLabel
berechnet seine Höhe aber genau aus dieser Angabe - die Punkte werden
abgeschnitten, und aus "NÄCHSTE" wird sichtbar "NACHSTE", aus
"RAIDGRÖSSE" wird "RAIDGROSSE". Da praktisch jede deutsche Beschriftung
Umlaute enthalten kann, gehört die Korrektur an genau eine Stelle: die
Mindesthöhe wird aus der tatsächlichen Ausdehnung von "ÄÖÜ" berechnet
statt aus der deklarierten Oberlänge.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from gui.theme import tokens
from gui.theme.fonts import font


#
# Referenzzeichen zur Messung. Alle drei deutschen Großumlaute,
# damit der höchste von ihnen die Mindesthöhe bestimmt.
#

UMLAUT_SAMPLE = "ÄÖÜ"


def eyebrow_label(
    text: str,
    color: str | None = None,
    token: str = "micro",
) -> QLabel:
    """
    Ein Rubriklabel.

    `token` ist "micro" (10 px, in Kacheln) oder "eyebrow" (11 px, über
    Abschnitten) - die beiden Größen aus §2.5. Die Größe folgt der
    eingestellten Dichte, die Laufweite kommt aus dem Token.
    """

    label = QLabel(text)

    label.setObjectName("eyebrow")

    label.setFont(font(token))

    label.setStyleSheet(
        f"color:{color or tokens.TEXT['muted']};"
        "background:transparent;border:none;"
    )

    #
    # ensurePolished() erzwingt, dass die Schrift bereits gesetzt ist -
    # ohne den Aufruf würde noch die Standardschrift vermessen.
    #

    label.ensurePolished()

    metrics = label.fontMetrics()

    #
    # top() ist negativ und gibt an, wie weit die Zeichen über die
    # Grundlinie hinausragen.
    #

    ink_top = metrics.tightBoundingRect(UMLAUT_SAMPLE).top()

    label.setMinimumHeight(
        max(
            metrics.height(),
            -ink_top + metrics.descent() + 2,
        )
    )

    return label
