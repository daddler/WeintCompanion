"""
Die Wartekarte: was gerade geholt wird, wie weit es ist, und was
danach passiert.

Gemeldet wurde, dass beim Auswerten eines Logs *nirgends* steht, dass
man warten muss - nur "bei großen Pulls dauert das etwas", ohne Zahl,
ohne Bewegung, ohne Ansage, ab wann man weiterarbeiten kann. Wer das
liest, klickt nach zehn Sekunden auf den nächsten Pull, was den Abruf
von vorn beginnen lässt, und hält die Anwendung danach für kaputt.

Diese Karte beantwortet die drei Fragen, die man in dem Moment hat,
in genau dieser Reihenfolge:

1. **Läuft überhaupt noch etwas?** Ein Balken, der sich jede Sekunde
   bewegt, und eine mitlaufende Sekundenzahl.
2. **Wie lange noch?** Die Schätzung aus `core/loading_progress.py` -
   aus der Länge dieses Pulls und den bisher gemessenen Abrufen.
3. **Und dann?** Der Satz, den es bisher nirgends gab: es füllt sich
   von selbst, es ist nichts weiter anzuklicken.

Drei Festlegungen, die nicht Geschmack sind:

* **Der Takt läuft nur, solange die Karte sichtbar ist.** Ein
  QTimer, der auf einer verlassenen Seite weiterläuft, zeichnet
  stündlich 3600-mal ins Nichts. `showEvent`/`hideEvent` starten und
  stoppen ihn - und die Aufräumarbeit steht in einer eigenen,
  ereignisfreien Methode, weil man einem Qt-Handler nie das Ereignis
  eines anderen geben darf (siehe CLAUDE.md).
* **Die Karte rechnet nichts.** Schätzung, Anteil und Satz kommen aus
  `core/loading_progress.py`; dieselbe Rechnung ein zweites Mal in
  einem Widget wäre genau die Doppelung, die die Archivseite und die
  Quellenzeile schon einmal auseinanderlaufen liess.
* **Sie zeigt sich selbst an und aus.** Die Seiten fragen nicht "lädt
  gerade etwas" - sie hängen die Karte in ihr Layout, und die Karte
  entscheidet. Drei Seiten mit je eigener Sichtbarkeitslogik wären
  drei Gelegenheiten, sie stehen zu lassen.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

from core import loading_progress
from core.raid_data_service import MODE_LIVE

from gui.theme.colors import Colors
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.tv.meter_bar import MeterBar


#
# Wie oft der Balken nachgezogen wird. Einmal je Sekunde: die Zahl
# daneben ist in Sekunden, alles Feinere wäre Bewegung ohne Aussage.
#

TICK_MS = 1000


class LoadingCard(Card):
    """
    Hängt an `RaidDataService.archiveChanged` und zeigt sich nur,
    solange ein Pull geholt wird.
    """

    def __init__(self, service, parent=None):

        super().__init__(accent=True, parent=parent)

        self.service = service

        self.addWidget(
            eyebrow_label("WIRD GELESEN", Colors.PRIMARY_HOVER)
        )

        self.title = QLabel("")

        self.title.setWordWrap(True)

        self.title.setStyleSheet(
            f"font-size:17px;font-weight:700;color:{Colors.WHITE};"
            "background:transparent;border:none;"
        )

        self.addWidget(self.title)

        self.bar = MeterBar(height=8)

        self.addWidget(self.bar)

        self.status = QLabel("")

        self.status.setWordWrap(True)

        self.status.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        self.addWidget(self.status)

        self.note = QLabel(
            loading_progress.WHY_NOTE + " " + loading_progress.READY_NOTE
        )

        self.note.setWordWrap(True)

        self.note.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        self.addWidget(self.note)

        #
        # Der Takt. Er wird erst in `showEvent` gestartet - ein Timer,
        # der schon im Konstruktor läuft, tickt auf jeder Seite, die
        # diese Karte nur vorsorglich anlegt.
        #

        self._timer = QTimer(self)

        self._timer.setInterval(TICK_MS)

        self._timer.timeout.connect(self._tick)

        service.archiveChanged.connect(self._refresh)

        self.setVisible(False)

        self._refresh()

    # --------------------------------------------------
    # Sichtbarkeit und Takt
    # --------------------------------------------------

    def showEvent(self, event):

        super().showEvent(event)

        self._sync_timer()

    def hideEvent(self, event):

        super().hideEvent(event)

        #
        # Kein `event` weiterreichen: die gemeinsame Arbeit steht in
        # einer ereignisfreien Methode, weil ein an den falschen
        # Handler gereichtes Qt-Ereignis ohne Traceback abstürzt.
        #

        self._stop()

    def _stop(self):
        """
        Idempotent - darf mehrfach kommen.
        """

        self._timer.stop()

    def _sync_timer(self):

        if self.isVisible() and self._loading():

            if not self._timer.isActive():
                self._timer.start()

        else:

            self._stop()

    def _loading(self) -> bool:

        state = self.service.archive_state()

        return bool(state.fight_loading and state.mode != MODE_LIVE)

    # --------------------------------------------------
    # Inhalt
    # --------------------------------------------------

    def _tick(self):

        self._apply()

    def _refresh(self):

        self._apply()

        self._sync_timer()

    def _apply(self):

        state = self.service.archive_state()

        if not self._loading():

            self.setVisible(False)

            return

        elapsed = state.elapsed(time.monotonic())

        expected = state.fight_expected

        self.title.setText(
            f"{state.fight_label or 'Der Pull'} wird ausgewertet"
        )

        self.bar.setValue(loading_progress.share(elapsed, expected))

        #
        # Leere Farbe heisst "Akzentverlauf" (siehe MeterBar) - die
        # Warnfarbe erst, wenn es länger dauert als geschätzt.
        #

        self.bar.setColor(
            Colors.WARNING
            if loading_progress.overdue(elapsed, expected)
            else ""
        )

        self.status.setText(
            loading_progress.progress_text(
                elapsed,
                expected,
                "Der Kampf",
            )
        )

        self.setVisible(True)
