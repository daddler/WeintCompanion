"""
WeintCompanion 2.0
Die eine Pulsquelle

Der Entwurf erlaubt ausdruecklich **hoechstens eine sichtbare
Pulsquelle gleichzeitig** (§3, §8). Das ist keine Sparsamkeit, sondern
der Zweck des Pulses: er sagt "hier passiert gerade etwas". Zwei
Dinge, die gleichzeitig atmen, sagen nichts mehr - und drei sind
Unruhe neben einem Vollbildspiel.

Zwei getrennte Probleme loest dieses Modul, und beide entstehen, sobald
jedes Widget seinen eigenen Timer bekommt:

**Gleichlauf.** Zwei Timer mit 16 ms starten zu verschiedenen
Zeitpunkten und laufen dadurch dauerhaft gegeneinander. Selbst wenn nur
zwei Punkte sichtbar sind, sieht das aus wie ein Fehler. Hier gibt es
eine Phase, und alle lesen dieselbe.

**Vorrang.** "Hoechstens eine Quelle" laesst sich nicht lokal
entscheiden - ein Warnpunkt kann nicht wissen, ob anderswo ein
LIVE-Zeichen sichtbar ist. Deshalb melden sich Abonnenten mit ihrer
Art an, und die Uhr entscheidet: **ist ein LIVE-Zeichen sichtbar,
pulsen Warnungen nicht.**

Bei reduzierter Bewegung steht die Uhr still und liefert dauerhaft
Phase 1.0 (volle Deckkraft). Die Punkte bleiben damit sichtbar - sie
atmen nur nicht mehr.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, QTimer, Signal


#
# Die Arten, in denen gepulst werden darf, in absteigendem Vorrang.
# Ein Abonnent nennt beim Anmelden seine Art.
#

KIND_LIVE = "live"

KIND_WARN = "warn"

PRIORITY = (KIND_LIVE, KIND_WARN)


#
# 16 ms entsprechen rund 60 Bildern je Sekunde. Der Puls selbst dauert
# 1000 ms (motion.pulse).
#

TICK_MS = 16

PERIOD_MS = 1000


class PulseClock(QObject):
    """
    Eine Phase, viele Punkte.
    """

    #
    # Wird bei jedem Tick gesendet. Abonnenten verbinden sich damit auf
    # `update()` - der Wert selbst wird ueber `opacity()` und `scale()`
    # im `paintEvent` gelesen, denn nur dort ist bekannt, ob das Widget
    # ueberhaupt sichtbar ist.
    #

    tick = Signal()

    def __init__(self):

        super().__init__()

        self._timer = QTimer(self)

        self._timer.setInterval(TICK_MS)

        self._timer.timeout.connect(self._on_tick)

        self._elapsed = 0

        #
        # Wie viele Abonnenten je Art gerade sichtbar sind. Zaehler
        # statt Mengen, weil dasselbe Widget mehrfach ein- und
        # ausgeblendet werden kann und ein Zaehler das ohne Buchhaltung
        # ueber Objektidentitaeten aushaelt.
        #

        self._counts = {kind: 0 for kind in PRIORITY}

    # --------------------------------------------------
    # An- und Abmelden
    # --------------------------------------------------

    def subscribe(self, kind: str = KIND_LIVE):
        """
        Einen sichtbaren Pulspunkt anmelden.

        Aufzurufen, wenn der Punkt sichtbar wird - nicht wenn er
        gebaut wird. Ein Punkt auf einer Seite, die niemand geoeffnet
        hat, ist keine sichtbare Quelle.
        """

        if kind not in self._counts:
            kind = KIND_WARN

        self._counts[kind] += 1

        self._update_running()

    def unsubscribe(self, kind: str = KIND_LIVE):

        if kind not in self._counts:
            kind = KIND_WARN

        self._counts[kind] = max(0, self._counts[kind] - 1)

        self._update_running()

    # --------------------------------------------------
    # Vorrang
    # --------------------------------------------------

    def active_kind(self) -> str | None:
        """
        Die Art, die gerade pulsen darf - oder None.
        """

        for kind in PRIORITY:

            if self._counts.get(kind, 0) > 0:
                return kind

        return None

    def may_pulse(self, kind: str) -> bool:
        """
        Ob ein Punkt dieser Art gerade pulsen darf.

        Ein Warnpunkt, der nicht darf, verschwindet nicht - er steht
        nur still. Das ist der Unterschied zwischen "unwichtig" und
        "nicht das, was hier gerade die Aufmerksamkeit verdient".
        """

        return self.active_kind() == kind

    # --------------------------------------------------
    # Phase
    # --------------------------------------------------

    def phase(self) -> float:
        """
        Die Phase im Puls, 0.0 bis 1.0.
        """

        if not self._timer.isActive():
            return 0.0

        return (self._elapsed % PERIOD_MS) / PERIOD_MS

    def opacity(self, kind: str = KIND_LIVE) -> float:
        """
        Die Deckkraft eines Punktes dieser Art: 1.0 bis 0.35 und
        zurueck (motion.pulse), sinusfoermig.
        """

        if not self.may_pulse(kind):
            return 1.0

        return self._eased(1.0, 0.35)

    def scale(self, kind: str = KIND_LIVE) -> float:
        """
        Die Skalierung eines Punktes dieser Art: 1.0 bis 0.82.
        """

        if not self.may_pulse(kind):
            return 1.0

        return self._eased(1.0, 0.82)

    def _eased(self, high: float, low: float) -> float:

        #
        # InOutSine ueber eine volle Periode: bei Phase 0 und 1 oben,
        # bei 0.5 unten. cos() liefert genau das, ohne dass dafuer eine
        # QEasingCurve ausgewertet werden muesste - und diese Funktion
        # laeuft sechzig Mal je Sekunde.
        #

        t = (1.0 - math.cos(self.phase() * 2.0 * math.pi)) / 2.0

        return high + (low - high) * t

    # --------------------------------------------------

    def _on_tick(self):

        self._elapsed += TICK_MS

        self.tick.emit()

    def _update_running(self):
        """
        Die Uhr laeuft nur, solange ueberhaupt jemand pulst.

        Ein Timer mit 16 ms, der ins Leere tickt, weckt den Prozess
        sechzig Mal je Sekunde - auf einem Rechner, der daneben ein
        Vollbildspiel bedient.
        """

        from gui.theme.motion import is_reduced

        should_run = (
            self.active_kind() is not None
            and not is_reduced()
        )

        if should_run and not self._timer.isActive():

            self._elapsed = 0

            self._timer.start()

            return

        if not should_run and self._timer.isActive():

            self._timer.stop()

            #
            # Beim Anhalten ein letztes Mal melden, damit die Punkte
            # in voller Deckkraft stehenbleiben statt in dem
            # zufaelligen Zwischenwert des letzten Ticks.
            #

            self.tick.emit()

    def stop(self):
        """
        Anhalten - beim Beenden der Anwendung.
        """

        self._timer.stop()


# ==========================================================
# Zugriff
# ==========================================================

_clock: PulseClock | None = None


def pulse_clock() -> PulseClock:
    """
    Die eine Pulsuhr der Anwendung.
    """

    global _clock

    if _clock is None:
        _clock = PulseClock()

    return _clock
