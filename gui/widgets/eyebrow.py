"""
Kleine, gesperrte Mono-Überschrift ("Eyebrow").

Warum es dafür eine eigene Funktion gibt: bei 10px Schriftgröße
ragen die Punkte über einem großgeschriebenen Umlaut höher als die
von der Schriftart angegebene Oberlänge. QLabel berechnet seine
Höhe aber genau aus dieser Angabe - die Punkte werden dadurch
abgeschnitten, und aus "NÄCHSTE" wird sichtbar "NACHSTE", aus
"RAIDGRÖSSE" wird "RAIDGROSSE".

Da praktisch jede deutsche Beschriftung Umlaute enthalten kann,
gehört die Korrektur an genau eine Stelle: die Mindesthöhe wird aus
der tatsächlichen Ausdehnung von "ÄÖÜ" berechnet statt aus der
deklarierten Oberlänge.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from gui.theme.colors import Colors


#
# Referenzzeichen zur Messung. Alle drei deutschen Großumlaute,
# damit der höchste von ihnen die Mindesthöhe bestimmt.
#

UMLAUT_SAMPLE = "ÄÖÜ"


def eyebrow_label(
    text: str,
    color: str = Colors.TEXT_MUTED,
    size: int = 10,
    letter_spacing: str = "0.15em",
) -> QLabel:

    label = QLabel(text)

    label.setStyleSheet(
        'font-family:"JetBrains Mono";'
        f"font-size:{size}px;color:{color};"
        f"letter-spacing:{letter_spacing};"
        "background:transparent;border:none;"
    )

    #
    # ensurePolished() erzwingt, dass die Stylesheet-Schriftgröße
    # bereits gesetzt ist - ohne den Aufruf würde noch die
    # Standardschrift des Systems vermessen.
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
