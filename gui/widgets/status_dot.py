"""
WeintCompanion 2.0
Der Statuspunkt

Er ersetzt **alle** Status-Emoji. Bis 1.7 stand in der Oberfläche an
fünfunddreißig Stellen ein 🟢, 🟡 oder 🔴 - mit drei Nachteilen, die
sich nicht wegkonfigurieren lassen: die Zeichen kommen aus der
Emoji-Schrift des Betriebssystems und sehen auf jedem Rechner anders
aus, ihre Farbe ist nicht die des Themes, und sie skalieren nicht mit
der Dichte.

Zustände (§5):

    ok / warn / error / info   gefüllt in der Bedeutungsfarbe
    live                       wie error, aber pulsierend
    empty                      **nicht** gefüllt, nur 1-px-Kontur

`empty` ist der wichtige Sonderfall. Ein grauer gefüllter Punkt sähe
aus wie ein eigener Zustand ("neutral", "unbekannt-aber-gemessen");
gemeint ist aber "hier liegt keine Angabe vor". Die Kontur ohne
Füllung sagt das - dieselbe Unterscheidung, die im Analyzer
`stars == 0` von einer schlechten Bewertung trennt.

Bei reduzierter Bewegung pulst der LIVE-Punkt nicht, sondern wird zum
**Quadrat**: die Form muss die Information übernehmen, die sonst die
Bewegung trägt, sonst ist ein LIVE-Punkt von einem Fehlerpunkt nicht
mehr zu unterscheiden - beide sind rot.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.motion.pulse_clock import KIND_LIVE, KIND_WARN, pulse_clock
from gui.theme import tokens
from gui.theme.motion import is_reduced


#
# Die beiden Größen aus §5. `LARGE` steht in Kopfzeilen und
# Leerzuständen, `NORMAL` überall sonst.
#

SIZE_NORMAL = 7

SIZE_LARGE = 9


class StatusDot(QWidget):

    def __init__(self, state: str = "empty", size: int = SIZE_NORMAL, parent=None):

        super().__init__(parent)

        self._state = state

        self._size = size

        #
        # Ob dieses Widget bei der Pulsuhr angemeldet ist. Die
        # Anmeldung hängt an der **Sichtbarkeit**, nicht am Bau: ein
        # LIVE-Punkt auf einer Seite, die niemand geöffnet hat, ist
        # keine sichtbare Pulsquelle und darf die Warnungen anderswo
        # nicht stillstellen.
        #

        self._subscribed = False

        self.setFixedSize(size, size)

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # --------------------------------------------------

    def state(self) -> str:

        return self._state

    def setState(self, state: str):

        if state == self._state:
            return

        #
        # Ab- und wieder anmelden, denn die Art hat sich geändert:
        # aus einem Warnpunkt wird ein LIVE-Punkt oder umgekehrt, und
        # davon hängt der Vorrang ab.
        #

        was_subscribed = self._subscribed

        if was_subscribed:
            self._release()

        self._state = state

        if was_subscribed:
            self._claim()

        self.update()

    def setDotSize(self, size: int):

        if size == self._size:
            return

        self._size = size

        self.setFixedSize(size, size)

        self.update()

    # --------------------------------------------------
    # Pulsquelle
    # --------------------------------------------------

    def _pulse_kind(self) -> str | None:
        """
        Als welche Art dieser Punkt pulst - oder None.
        """

        if self._state == "live":
            return KIND_LIVE

        if self._state == "warn":
            return KIND_WARN

        return None

    def _claim(self):

        kind = self._pulse_kind()

        if kind is None or self._subscribed:
            return

        clock = pulse_clock()

        clock.subscribe(kind)

        clock.tick.connect(self.update)

        self._subscribed = True

    def _release(self):

        if not self._subscribed:
            return

        kind = self._pulse_kind()

        clock = pulse_clock()

        if kind is not None:
            clock.unsubscribe(kind)

        try:
            clock.tick.disconnect(self.update)

        except (RuntimeError, TypeError):
            #
            # Bereits getrennt - beim Abbau der Seite kann Qt die
            # Verbindung vor uns gelöst haben.
            #
            pass

        self._subscribed = False

    def showEvent(self, event):

        super().showEvent(event)

        self._claim()

    def hideEvent(self, event):

        super().hideEvent(event)

        self._release()

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        color = tokens.STATE.get(self._state)

        #
        # Kein Wert heißt "keine Angabe": nur Kontur, keine Füllung.
        #

        if color is None:

            painter.setBrush(Qt.NoBrush)

            painter.setPen(
                QPen(QColor(tokens.STATE_EMPTY_OUTLINE), 1)
            )

            inset = 0.5

            painter.drawEllipse(
                QRectF(
                    inset,
                    inset,
                    self._size - 2 * inset,
                    self._size - 2 * inset,
                )
            )

            return

        kind = self._pulse_kind()

        reduced = is_reduced()

        opacity = 1.0

        scale = 1.0

        if kind is not None and not reduced:

            clock = pulse_clock()

            opacity = clock.opacity(kind)

            scale = clock.scale(kind)

        painter.setOpacity(opacity)

        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor(color))

        side = self._size * scale

        offset = (self._size - side) / 2.0

        rect = QRectF(offset, offset, side, side)

        #
        # Reduzierte Bewegung: der LIVE-Punkt wird zum Quadrat, damit
        # die Form trägt, was sonst der Puls trägt. Ein Warnpunkt
        # bleibt rund - er ist an seiner Farbe zu erkennen.
        #

        if reduced and self._state == "live":

            painter.drawRoundedRect(
                rect,
                tokens.RADIUS["sm"] / 2.0,
                tokens.RADIUS["sm"] / 2.0,
            )

            return

        painter.drawEllipse(rect)
