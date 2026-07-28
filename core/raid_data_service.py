"""
Zentrale Bezugsquelle für Raid-Daten.

Dies ist der einzige Ort, an dem die Anwendung eine Datenquelle
auswählt und abfragt. WeintTV und die WeintAcademy hängen beide hier
dran - dadurch kann es keine zweite, abweichende Auswertung geben.

Ablauf:

    Seite ruft attach()      -> Poll-Thread startet (falls noch keiner läuft)
    Thread pollt provider    -> snapshotChanged wird emittiert
    Seite ruft detach()      -> Thread endet, sobald niemand mehr zuhört

Der Referenzzähler ist wichtig: WeintTV soll nur pollen, solange die
Seite auch sichtbar ist. Ohne ihn liefe der Thread den ganzen Tag
weiter, obwohl niemand hinsieht.

Threading folgt exakt dem Muster des Repos (siehe
core/companion_manager.py): ein einfacher threading.Thread, und die
Zustellung in den Qt-Hauptthread passiert über ein Signal. Ein
Signal wird immer über die Event-Loop des EMPFÄNGER-Threads
zugestellt - der Service wird deshalb im Hauptthread erzeugt
(CompanionManager.__init__), obwohl er aus dem Worker emittiert.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from analyzer.combatlog.locator import CombatLogLocation, find_combat_log
from analyzer.models import PullSummary, RaidSnapshot
from analyzer.providers.mock import MockRaidDataProvider


#
# --------------------------------------------------
# Bekannte Datenquellen
# --------------------------------------------------
#
# Die Registry ist der Erweiterungspunkt: eine neue Quelle (Live-
# Combat-Log, WarcraftLogs, Bot-Backend) ist ein weiterer Eintrag
# hier plus eine Klasse, die RaidDataProvider implementiert. Weder
# der Service noch eine Seite müssen dafür angefasst werden.
#

SOURCE_MOCK = "mock"

SOURCE_COMBATLOG = "combatlog"


PROVIDER_FACTORIES = {

    SOURCE_MOCK: MockRaidDataProvider,

}


#
# Abstand zwischen zwei Abfragen. Bewusst ein eigener Takt und nicht
# der 5-Sekunden-Sync-Timer des CompanionManagers: der ist für
# HTTP-Synchronisation gedacht, ein Live-Dashboard braucht deutlich
# feinere Auflösung.
#

POLL_INTERVAL = 1.0


#
# Wie viele abgeschlossene Pulls vorgehalten werden. Ein Raidabend
# hat selten mehr Versuche an einem Boss, und die Liste soll über
# Stunden hinweg nicht unbegrenzt wachsen.
#

HISTORY_LIMIT = 25


class RaidDataService(QObject):

    #
    # Trägt einen RaidSnapshot. `object` statt eines konkreten Typs,
    # weil Qt-Signale nur registrierte Typen kennen - dasselbe
    # Vorgehen wie bei _LogBridge.new_entry.
    #

    snapshotChanged = Signal(object)

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self._provider = None

        self._provider_source = ""

        self._snapshot = RaidSnapshot.empty()

        #
        # Abgeschlossene Pulls. Sie entstehen hier und nicht in
        # WeintTV, damit Academy und Verlaufsansicht dieselbe
        # Historie sehen.
        #

        self._history: list[PullSummary] = []

        self._pending_pull = None

        self._lock = threading.Lock()

        self._listeners = 0

        self._thread = None

        self._stop_event = threading.Event()

    # --------------------------------------------------
    # Datenquelle
    # --------------------------------------------------

    def configured_source(self) -> str:

        return self.manager.config.data.get(
            "raid_data_source",
            SOURCE_MOCK,
        )

    def _create_provider(self):
        """
        Erzeugt den Provider zur konfigurierten Quelle. Ist die
        Quelle unbekannt (z. B. eine per Hand eingetragene, noch nicht
        implementierte), wird das protokolliert und die Simulation
        genutzt - die Oberfläche bleibt so in jedem Fall bedienbar.
        """

        source = self.configured_source()

        factory = PROVIDER_FACTORIES.get(source)

        if factory is None:

            self.manager.logger.warning(
                f"Unbekannte Raid-Datenquelle '{source}' - "
                f"es wird die Simulation verwendet."
            )

            source = SOURCE_MOCK

            factory = PROVIDER_FACTORIES[SOURCE_MOCK]

        self._provider_source = source

        return factory()

    def _ensure_provider(self):

        if self._provider is None:

            self._provider = self._create_provider()

        return self._provider

    def reload_provider(self):
        """
        Nach einer Änderung der Einstellung: alten Provider sauber
        beenden und beim nächsten Poll einen neuen erzeugen.
        """

        with self._lock:

            provider = self._provider

            self._provider = None

            #
            # Die Historie gehört zur alten Quelle - sie mit Daten
            # einer anderen Quelle zu vermischen, wäre irreführend.
            #

            self._history.clear()

            self._pending_pull = None

        if provider is not None:

            try:
                provider.stop()

            except Exception as exc:

                self.manager.logger.error(
                    f"Datenquelle konnte nicht beendet werden: {exc}"
                )

        #
        # Läuft gerade jemand mit, bekommt er sofort den neutralen
        # Zustand der neuen Quelle statt der alten Werte.
        #

        if self._listeners > 0:

            self._publish(RaidSnapshot.empty())

    # --------------------------------------------------
    # Zustand
    # --------------------------------------------------

    def current(self) -> RaidSnapshot:
        """
        Zuletzt veröffentlichter Snapshot. Erlaubt es einer Seite,
        beim Öffnen sofort etwas zu zeichnen, statt bis zum ersten
        Poll leer zu bleiben.
        """

        with self._lock:

            return self._snapshot

    def source_label(self) -> str:

        provider = self._provider

        if provider is None:
            return "Keine Datenquelle"

        return provider.source_label

    def status_text(self) -> str:

        provider = self._provider

        if provider is None:
            return ""

        return provider.status_text

    def is_running(self) -> bool:

        return self._thread is not None and self._thread.is_alive()

    # --------------------------------------------------
    # Combat-Log-Erkennung
    # --------------------------------------------------

    def locate_combat_log(self) -> CombatLogLocation:
        """
        Sucht die Combat-Log-Datei der erkannten WoW-Installation.

        Wird von den Einstellungen angezeigt und ist zugleich die
        Vorarbeit für die Live-Auswertung.
        """

        configured = self.manager.config.data.get(
            "combatlog_path",
            "",
        )

        if configured:

            path = Path(configured)

            if path.is_file():

                try:
                    size = path.stat().st_size

                except OSError:
                    size = 0

                return CombatLogLocation(path=path, size=size)

            return CombatLogLocation(
                reason=(
                    "Der in den Einstellungen hinterlegte Pfad "
                    "existiert nicht mehr."
                ),
            )

        return find_combat_log(
            self.manager.state.wow_path
        )

    # --------------------------------------------------
    # An-/Abmelden
    # --------------------------------------------------

    def attach(self):
        """
        Meldet einen Interessenten an. Der erste startet den Poll.
        """

        with self._lock:

            self._listeners += 1

            start_needed = self._listeners == 1

        if start_needed:

            self._start_thread()

    def detach(self):
        """
        Meldet einen Interessenten ab. Der letzte beendet den Poll.
        """

        with self._lock:

            if self._listeners > 0:

                self._listeners -= 1

            stop_needed = self._listeners == 0

        if stop_needed:

            self._stop_thread()

    # --------------------------------------------------
    # Poll-Thread
    # --------------------------------------------------

    def _start_thread(self):

        if self.is_running():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._poll_worker,
            daemon=True,
            name="RaidDataThread",
        )

        self._thread.start()

    def _stop_thread(self):

        self._stop_event.set()

        thread = self._thread

        self._thread = None

        #
        # Kein join() im Hauptthread: der Worker schläft bis zu
        # POLL_INTERVAL Sekunden, und die Oberfläche darf dafür nicht
        # einfrieren. Er ist ein Daemon und beendet sich selbst,
        # sobald das Event gesetzt ist.
        #

        if thread is None:
            return

        provider = self._provider

        if provider is not None:

            try:
                provider.stop()

            except Exception as exc:

                self.manager.logger.error(
                    f"Datenquelle konnte nicht beendet werden: {exc}"
                )

    def _poll_worker(self):

        try:

            while not self._stop_event.is_set():

                self._poll_once()

                #
                # wait() statt sleep(): so reagiert das Beenden sofort
                # und nicht erst nach Ablauf des Intervalls.
                #

                self._stop_event.wait(POLL_INTERVAL)

        except Exception as exc:

            self.manager.logger.error(
                f"Raid-Daten-Auswertung abgebrochen: {exc}"
            )

    def _poll_once(self):
        """
        Ein Abfragezyklus. Fehler einer Datenquelle dürfen den Poll
        nie beenden - dieselbe Regel wie beim Sync im
        CompanionManager: ein defekter Teil reißt nicht den Rest mit.
        """

        try:

            with self._lock:

                provider = self._ensure_provider()

            provider.start()

            snapshot = provider.snapshot()

        except Exception as exc:

            self.manager.logger.error(
                f"Raid-Daten konnten nicht gelesen werden: {exc}"
            )

            snapshot = RaidSnapshot.empty()

        self._publish(snapshot)

    def _publish(self, snapshot: RaidSnapshot):

        with self._lock:

            self._snapshot = snapshot

            self._track_history(snapshot)

        self.snapshotChanged.emit(snapshot)

    def _track_history(self, snapshot: RaidSnapshot):
        """
        Erkennt das Ende eines Pulls und schreibt ihn in die Historie.

        Verfahren: der jeweils letzte Snapshot MIT Kampf wird
        vorgemerkt. Sobald eine neue Pull-Nummer auftaucht, war der
        vorgemerkte Snapshot der letzte Stand des vorherigen Pulls -
        genau der gehört in die Historie.

        Wird nur aus _publish() unter gehaltenem Lock aufgerufen.
        """

        pending = self._pending_pull

        if (
            pending is not None
            and snapshot.pull_number != pending.pull_number
        ):

            self._history.append(
                PullSummary.from_snapshot(pending)
            )

            del self._history[:-HISTORY_LIMIT]

            self._pending_pull = None

        if snapshot.in_combat and snapshot.has_data:

            self._pending_pull = snapshot

    # --------------------------------------------------

    def history(self) -> tuple[PullSummary, ...]:
        """
        Abgeschlossene Pulls, neuester zuerst.
        """

        with self._lock:

            return tuple(reversed(self._history))

    # --------------------------------------------------
    # Abschluss
    # --------------------------------------------------

    def shutdown(self):
        """
        Wird beim Beenden der Anwendung aufgerufen. Setzt den Zähler
        hart zurück, damit ein vergessenes detach() den Thread nicht
        am Leben hält.
        """

        with self._lock:

            self._listeners = 0

        self._stop_thread()
