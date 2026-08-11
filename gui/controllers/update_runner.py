"""
Ein Update auslösen - an einer Stelle für alle Knöpfe.

**Warum es das gibt.** Bis 2.0.1 stand der Ablauf ("Karte auf `lädt`,
`processEvents()`, blockierender Aufruf, Protokoll, Karte zurück" bzw.
"Auto-Sync anhalten, Thread starten, Ergebnis über ein Signal
zurückholen, bei Erfolg beenden") vollständig in `gui/pages/addon.py`.
Der Update-Hinweis auf der Übersicht braucht denselben Ablauf, und ihn
ein zweites Mal zu schreiben hieße: zwei Wege, ein Update zu starten,
die beim ersten Sonderfall auseinanderlaufen - und die Sonderfälle
sind hier keine Kleinigkeiten (`stop_auto_sync()` fasst einen QTimer
des Hauptthreads an, ein Fehlschlag muss ihn wieder anwerfen, und ein
erfolgreiches Companion-Update beendet den Prozess).

Der Läufer kennt keine Karten und keine Seiten. Er meldet nur, was
gerade passiert (`started`/`finished`); wie sich das anfühlt,
entscheidet jede Oberfläche für sich - die Karte unter "Addon &
Updates" trägt einen "LÄDT"-Chip, der Hinweis auf der Übersicht
sperrt seinen Knopf.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

#
# Dieselben beiden Schlüssel wie in `core/changelog_source.py`, von
# dort übernommen statt hier ein zweites Mal geschrieben: die
# Übersicht reicht denselben Wert an beide weiter (Update auslösen und
# Changelog nachschlagen), und zwei gleichlautende Konstanten wären
# genau die Art Verdopplung, die still auseinanderläuft.
#

from core.changelog_source import ADDON, COMPANION


class UpdateRunner(QObject):
    """
    Beide Update-Kanäle, einmal.

    `finished` trägt die Komponente, den Erfolg und einen Satz für die
    Oberfläche - kein Aufrufer soll die Fehlermeldung ein zweites Mal
    formulieren müssen.
    """

    started = Signal(str)

    finished = Signal(str, bool, str)

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self._busy = False

        #
        # Das Ergebnis des Companion-Threads kommt über ein Signal
        # zurück in den Hauptthread. Ein direkter Aufruf von dort
        # würde Widgets aus dem falschen Thread anfassen - dieselbe
        # Regel wie bei `CompanionManager.state_changed`.
        #

        self.finished.connect(self._on_finished)

    # --------------------------------------------------

    def busy(self) -> bool:
        return self._busy

    # --------------------------------------------------

    def install_addon(self):
        """
        Addon installieren oder aktualisieren.

        Bewusst blockierend im Hauptthread, wie bisher: der Vorgang
        ist kurz, und `install_or_update()` schreibt in denselben
        Addon-Ordner, den die Oberfläche gleich darauf ausliest.
        `QApplication.processEvents()` sorgt allein dafür, dass der
        "lädt"-Zustand vor der Blockade auch gezeichnet wird.
        """

        if self._busy:
            return

        self._busy = True

        state = self.manager.state

        updating = state.addon_found

        self.started.emit(ADDON)

        QApplication.processEvents()

        self.manager.logger.info(
            "Starte Addon-Aktualisierung..."
            if updating
            else "Starte Addon-Installation..."
        )

        try:

            self.manager.install_or_update()

        except Exception as exc:

            self.manager.logger.error(f"Fehler: {exc}")

            self._busy = False

            self.finished.emit(ADDON, False, str(exc))

            return

        message = (
            "Addon erfolgreich aktualisiert."
            if updating
            else "Addon erfolgreich installiert."
        )

        self.manager.logger.success(message)

        self._busy = False

        self.finished.emit(ADDON, True, message)

    # --------------------------------------------------

    def update_companion(self):
        """
        Die Anwendung selbst aktualisieren.

        Im Hintergrund-Thread, weil hier ein Download hängt. Bei
        Erfolg beendet sich die Anwendung - der Updater übernimmt.
        """

        if self._busy:
            return

        self._busy = True

        self.started.emit(COMPANION)

        self.manager.logger.info(
            "Companion-Update wird heruntergeladen..."
        )

        #
        # stop_auto_sync() fasst einen QTimer an, der dem Hauptthread
        # gehört - muss deshalb HIER passieren, nicht im Worker.
        #

        self.manager.stop_auto_sync()

        thread = threading.Thread(
            target=self._companion_worker,
            daemon=True,
            name="CompanionUpdateThread",
        )

        thread.start()

    def _companion_worker(self):

        message = ""

        try:

            success = bool(
                self.manager.companion_updater.install_update()
            )

        except Exception as exc:

            message = str(exc)

            self.manager.logger.error(
                f"Companion-Update fehlgeschlagen: {exc}"
            )

            success = False

        self._busy = False

        self.finished.emit(COMPANION, success, message)

    # --------------------------------------------------

    def _on_finished(self, component: str, success: bool, _message: str):

        if component != COMPANION:
            return

        if success:

            #
            # Kurz warten, damit die Oberfläche den Endzustand noch
            # zeichnet, bevor das Fenster verschwindet.
            #

            QTimer.singleShot(300, QApplication.quit)

            return

        #
        # Fehlschlag: der Auto-Sync wurde oben angehalten und muss
        # wieder anlaufen, sonst steht die Synchronisierung bis zum
        # nächsten Start still.
        #

        self.manager.start_auto_sync()
