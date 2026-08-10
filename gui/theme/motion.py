"""
WeintCompanion 2.0
Bewegung

Qt kennt weder `transition` noch `@keyframes`: jede Bewegung in dieser
Anwendung ist Python. Der Entwurf beschreibt sie deshalb nicht als CSS,
sondern als **Zustand A -> Zustand B, Dauer, Kurve** - und genau in
dieser Form stehen die Token hier.

Die eine Regel, die dieses Modul durchsetzt:

    Jede Dauer laeuft durch `duration()`.

Denn "Bewegung reduzieren" ist keine Abschwaechung, sondern eine
Abschaltung: alle Dauern werden 0 ms, Werte werden gesetzt statt
animiert. Wer eine Dauer direkt aus der Tabelle liest, umgeht das - und
zwar unsichtbar, bis jemand mit Vestibulaerstoerung die Einstellung
benutzt und feststellt, dass ein Teil der Oberflaeche sie ignoriert.

Der zweite Fall, in dem nicht animiert wird, hat nichts mit
Barrierefreiheit zu tun: **was sich mehrmals pro Sekunde aendert, wird
direkt gesetzt.** Eine Archiv-Wiedergabe tickt mit 4 Hz; eine 240 ms
lange Zahlenanimation waere dann dauerhaft unterwegs und nie am Ziel.
Dafuer gibt es `suspend_value_animation()`.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve


@dataclass(frozen=True)
class MotionToken:
    """
    Eine benannte Bewegung: Dauer in Millisekunden und Kurve.
    """

    duration: int

    curve: QEasingCurve.Type = QEasingCurve.OutCubic


MOTION = {
    #
    # Bereichswechsel: Deckkraft 0->1 und Versatz von +-12 px in
    # Navigationsrichtung, parallel.
    #
    "page": MotionToken(180, QEasingCurve.OutCubic),

    #
    # Zahlen laufen auf ihren neuen Wert zu - ausser bei sehr grossen
    # Spruengen, siehe `should_animate_number()`.
    #
    "number": MotionToken(240, QEasingCurve.OutQuad),

    #
    # Balkenbreite. Der beschriftete Wert wird sofort gesetzt: eine
    # mitlaufende Zahl neben einem mitlaufenden Balken liest sich als
    # Flackern, nicht als Bewegung.
    #
    "bar": MotionToken(220, QEasingCurve.OutCubic),

    #
    # Schimmer eines Skeletts, endlos.
    #
    "skeleton": MotionToken(1200, QEasingCurve.Linear),

    #
    # Puls des LIVE-Punktes, endlos. Siehe gui/motion/pulse_clock.py -
    # es gibt genau eine Quelle dafuer.
    #
    "pulse": MotionToken(1000, QEasingCurve.InOutSine),

    "toast_in": MotionToken(160, QEasingCurve.OutCubic),
    "toast_out": MotionToken(200, QEasingCurve.InCubic),

    "hover": MotionToken(120, QEasingCurve.Linear),

    "progress": MotionToken(300, QEasingCurve.OutCubic),

    #
    # Navigationsspalte 232 <-> 72 und der wandernde Indikator.
    #
    "nav": MotionToken(180, QEasingCurve.OutCubic),

    "toggle": MotionToken(140, QEasingCurve.OutCubic),

    #
    # Aufklappen der Systemzeile auf der Uebersicht.
    #
    "expand": MotionToken(180, QEasingCurve.OutCubic),

    #
    # Schublade unter 1280 px, von rechts.
    #
    "drawer": MotionToken(180, QEasingCurve.OutCubic),
}


#
# Wartezeit, bevor ein Skelett ueberhaupt erscheint. Ein Abruf, der
# schneller antwortet, zeigt nie eines - ein aufblitzendes Skelett ist
# unruhiger als ein kurzer Moment ohne Inhalt.
#
# Der Wert ist kein Geschmack: ein Archivabruf dauert real bis zu drei
# Minuten, ein Zwischenspeichertreffer wenige Millisekunden. Ohne diese
# Schwelle blinkt derselbe Bereich bei jedem zweiten Aufruf.
#

SKELETON_DELAY = 250

#
# Standzeit einer Meldung. Fehlermeldungen bekommen bewusst keine und
# bleiben bis zum Klick stehen.
#

TOAST_DWELL = 4000

#
# Wanderung des Schimmers, in Pixeln (-320 -> +320).
#

SKELETON_TRAVEL = 320

#
# Ab dieser Aenderungsrate wird nicht mehr animiert, sondern gesetzt.
#

MAX_ANIMATED_RATE_HZ = 2.0

#
# Ein Sprung um mehr als diesen Anteil des Wertes wird sofort gesetzt.
# Eine Zahl, die von 0 auf 4.700.000 laeuft, ist keine Bewegung mehr,
# sondern eine Wartezeit.
#

NUMBER_JUMP_THRESHOLD = 0.40


def _reduced(theme=None) -> bool:

    if theme is None:

        from gui.theme.theme_manager import theme as current_theme

        theme = current_theme()

    return theme.motion_reduced()


def duration(name: str, theme=None) -> int:
    """
    Die Dauer eines Bewegungstokens in Millisekunden - **0**, wenn
    Bewegung reduziert ist.

    Eine Dauer von 0 ms ist bei `QVariantAnimation` und
    `QPropertyAnimation` kein Sonderfall: die Animation springt sofort
    auf den Endwert und meldet `finished`. Aufrufer brauchen deshalb
    keine Fallunterscheidung, solange sie den Endzustand im
    `finished`-Zweig herstellen und nicht nur waehrend der Bewegung.
    """

    token = MOTION.get(name)

    if token is None:
        return 0

    if _reduced(theme):
        return 0

    return token.duration


def curve(name: str) -> QEasingCurve.Type:
    """
    Die Kurve eines Bewegungstokens.
    """

    token = MOTION.get(name)

    if token is None:
        return QEasingCurve.OutCubic

    return token.curve


def is_reduced(theme=None) -> bool:
    """
    Ob Bewegung reduziert ist.

    Fuer die Faelle, in denen nicht nur die Dauer entfaellt, sondern
    die Darstellung selbst eine andere ist: der LIVE-Punkt wird zum
    Quadrat, ein Skelett zeigt eine ruhige Flaeche statt eines
    Schimmers, ein Bereichswechsel verzichtet auf den Versatz.
    """

    return _reduced(theme)


def should_animate_number(old: float, new: float) -> bool:
    """
    Ob eine Zahlenaenderung animiert werden darf.

    Grosse Spruenge werden gesetzt: der erste Messwert eines Pulls
    kommt aus dem Nichts, und eine Zahl, die 240 ms lang von 0
    hochlaeuft, behauptet eine Entwicklung, die es nicht gab.
    """

    if old == new:
        return False

    reference = max(abs(old), abs(new))

    if reference <= 0:
        return False

    return abs(new - old) / reference <= NUMBER_JUMP_THRESHOLD


def suspend_value_animation(rate_hz: float) -> bool:
    """
    Ob Zahlen- und Balkenbewegung bei dieser Datenrate auszusetzen ist.

    Gilt fuer die Wiedergabe (4 Hz) und fuer jede Live-Quelle, die
    schneller als 2 Hz liefert.
    """

    return rate_hz > MAX_ANIMATED_RATE_HZ
