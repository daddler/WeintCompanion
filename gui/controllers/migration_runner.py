"""
Den Generationswechsel auslösen - an einer Stelle für alle Knöpfe.

Gebaut wie `gui/controllers/update_runner.py`, und aus demselben
Grund: der Ablauf lädt herunter, prüft und installiert, das gehört
in einen Hintergrund-Thread, und das Ergebnis muss über ein Signal
zurück in den Hauptthread - ein direkter Aufruf von dort würde
Widgets aus dem falschen Thread anfassen.

**Der Läufer entscheidet nichts.** Er kennt weder den Schalter noch
den Zustand noch die Plattform; das alles steht in
`core/migration/service.py`. Er startet den Thread, reicht den
Fortschritt durch und meldet das Ende. Die Trennung ist der Grund,
warum die Fachlogik ohne Qt getestet werden kann.

Der Fortschritt kommt aus einem fremden Thread und wird deshalb über
`Signal` weitergereicht, nicht über den Rückruf selbst - wer an
`progress` hängt, bekommt es im Hauptthread.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal


class MigrationRunner(QObject):
    """
    `progress(state, text)` während des Wechsels,
    `finished(success, message)` am Ende.
    """

    started = Signal()

    progress = Signal(str, str)

    finished = Signal(bool, str)

    def __init__(self, service, parent=None):

        super().__init__(parent)

        self.service = service

        self._busy = False

        self._result = None

    # --------------------------------------------------

    def busy(self) -> bool:
        return self._busy

    def result(self):
        """
        Das letzte Ergebnis (`MigrationResult`) - für Oberflächen,
        die mehr wissen wollen als den Satz aus `finished`.
        """

        return self._result

    # --------------------------------------------------

    def start(self):

        if self._busy:
            return

        self._busy = True

        self.started.emit()

        thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="ForeverMigrationThread",
        )

        thread.start()

    # --------------------------------------------------

    def _worker(self):

        try:

            result = self.service.migrate(progress=self._on_progress)

            message = result.message

            success = bool(result.success)

        except Exception as exc:

            #
            # Der Dienst fängt selbst alles ab, was er kennt. Was
            # hier ankommt, ist ein Fehler im Dienst - und der darf
            # den Thread nicht still beenden, sonst wartet der
            # Dialog für immer auf sein `finished`.
            #

            result = None

            message = str(exc)

            success = False

        self._result = result

        self._busy = False

        self.finished.emit(success, message)

    # --------------------------------------------------

    def _on_progress(self, state, text):

        value = getattr(state, "value", str(state))

        self.progress.emit(str(value), str(text))
