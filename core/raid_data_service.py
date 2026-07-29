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
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from analyzer.combatlog.locator import CombatLogLocation, find_combat_log
from analyzer.models import PullSummary, RaidSnapshot
from analyzer.providers.mock import MockRaidDataProvider
from analyzer.providers.warcraftlogs import FetchResult, WarcraftLogsProvider
from analyzer.providers.warcraftlogs_payload import (
    FightSummary,
    ReportSummary,
    snapshot_from_payload,
)


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

SOURCE_WARCRAFTLOGS = "warcraftlogs"


def _create_warcraftlogs_provider():
    """
    Verdrahtet die WarcraftLogs-Quelle mit ihrem Abruf.

    Die Trennung ist Absicht: der Provider liegt im Analyzer und
    kennt nur ein Callable, der HTTP-Teil liegt in core. So bleibt
    der Analyzer frei von Netzwerk und Bot-Wissen - und die Fabrik
    hier bleibt trotzdem argumentlos, wie die Registry es verlangt.
    """

    from core.warcraftlogs_client import WarcraftLogsClient

    return WarcraftLogsProvider(WarcraftLogsClient().fetch)


PROVIDER_FACTORIES = {

    SOURCE_MOCK: MockRaidDataProvider,

    SOURCE_WARCRAFTLOGS: _create_warcraftlogs_provider,

}


#
# Anzeigenamen der Quellen für die Einstellungen. Hier und nicht in
# der Oberfläche, damit eine neue Quelle wirklich nur diese eine
# Datei berührt.
#

SOURCE_LABELS = {

    SOURCE_MOCK: "Simulation",

    SOURCE_WARCRAFTLOGS: "WarcraftLogs",

}


SOURCE_DESCRIPTIONS = {

    SOURCE_MOCK: (
        "WeintTV zeigt einen vollständigen, berechneten "
        "Beispiel-Pull. So lassen sich alle Ansichten auch außerhalb "
        "der Raidzeiten prüfen."
    ),

    SOURCE_WARCRAFTLOGS: (
        "Liest den laufenden Livelog-Bericht über den WeintCodex-Bot. "
        "Gilt für den ganzen Raid - dieser Rechner muss nicht selbst "
        "mitschreiben. Die Werte sind einige Sekunden alt, weil "
        "WarcraftLogs in Abständen überträgt."
    ),

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


#
# --------------------------------------------------
# Archiv-Modus
# --------------------------------------------------
#
# Zusätzlich zum Live-Feed kann WeintTV/die Academy einen einzelnen,
# längst abgeschlossenen WarcraftLogs-Fight ansehen (Report wählen ->
# Pull darin wählen). "Verlauf" ist als Name bewusst vermieden - das
# bezeichnet in WeintTV bereits die abgeschlossenen Pulls DIESER
# Live-Sitzung (siehe history()/PullSummary oben); ein zweites
# "Verlauf" für etwas völlig anderes (ein beliebiger vergangener
# Report) wäre verwirrend.
#
# Der Modus ist bewusst global im Service verankert statt in einer
# einzelnen Seite: WeintTV und die Academy sollen beim Blick ins
# Archiv denselben Pull sehen, aus demselben Grund, aus dem sie schon
# denselben Live-Snapshot teilen.
#

MODE_LIVE = "live"

MODE_ARCHIVE = "archive"


@dataclass(frozen=True)
class ArchiveState:
    """
    Zustand der Archiv-Auswahl - ein Wert, den `ArchivePicker` in
    beiden Seiten unverändert übernehmen kann.

    Getrennte *_loading/*_error-Felder pro Schritt (Reports laden,
    Fights eines Reports laden, einen Fight laden), weil jeder Schritt
    unabhängig fehlschlagen oder noch laufen kann - ein einzelnes
    "loading"-Flag könnte nicht ausdrücken, dass z. B. die Reportliste
    längst da ist, aber gerade ein Fight nachlädt.
    """

    mode: str = MODE_LIVE

    reports: tuple[ReportSummary, ...] = ()

    reports_loading: bool = False

    reports_error: str = ""

    selected_report: str = ""

    fights: tuple[FightSummary, ...] = ()

    fights_loading: bool = False

    fights_error: str = ""

    selected_fight: int | None = None

    fight_loading: bool = False

    fight_error: str = ""


class RaidDataService(QObject):

    #
    # Trägt einen RaidSnapshot. `object` statt eines konkreten Typs,
    # weil Qt-Signale nur registrierte Typen kennen - dasselbe
    # Vorgehen wie bei _LogBridge.new_entry.
    #

    snapshotChanged = Signal(object)

    #
    # Wird bei jeder Änderung der Archiv-Auswahl emittiert (Modus,
    # Report-/Fight-Liste, Auswahl, Lade-/Fehlerzustand) - `object`
    # aus demselben Grund wie bei snapshotChanged. Ohne konkreten
    # Payload, weil ArchivePicker ohnehin archive_state() neu abruft;
    # ein eigener Payload würde nur zu einer zweiten Quelle für
    # denselben Zustand führen.
    #

    archiveChanged = Signal()

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

        #
        # Archiv-Modus (siehe ArchiveState oben).
        #

        self._archive = ArchiveState()

        self._archive_client = None

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
        # Zustand der neuen Quelle statt der alten Werte - außer im
        # Archiv-Modus: eine Einstellungsänderung an der LIVE-Quelle
        # hat mit dem gerade betrachteten vergangenen Fight nichts zu
        # tun und darf ihn nicht verdrängen.
        #

        if self._listeners > 0 and self._archive.mode == MODE_LIVE:

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

        with self._lock:

            #
            # Im Archiv-Modus wird der gepinnte Snapshot NICHT vom
            # Live-Poll überschrieben - der Poll läuft im Hintergrund
            # trotzdem weiter (harmlos: Mock rechnet nur, der
            # WarcraftLogs-Provider liest aus seinem eigenen Cache),
            # damit beim Zurückwechseln auf Live sofort ein aktueller
            # Wert bereitsteht, statt bis zum nächsten Takt zu warten.
            #

            if self._archive.mode == MODE_ARCHIVE:
                return

        self._publish(snapshot)

    def _publish(self, snapshot: RaidSnapshot, track: bool = True):
        """
        `track=False` für Snapshots, die keinem echten, gerade
        laufenden Pull dieser Sitzung entsprechen (z. B. ein aus dem
        Archiv geladener Fight) - sie gehören nicht in die
        Pull-Historie von WeintTVs "Verlauf"-Tab.
        """

        with self._lock:

            self._snapshot = snapshot

            if track:
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
    # Archiv: vergangene Reports/Fights ansehen
    # --------------------------------------------------
    #
    # Ablauf, das ArchivePicker-Widget bildet ihn direkt ab:
    #
    #   enter_archive_mode()               -> Reportliste lädt
    #   select_archive_report(code)        -> Fightliste dieses Reports lädt
    #   select_archive_fight(code, id)      -> Fight lädt, wird zum
    #                                          angezeigten Snapshot
    #   show_live()                        -> zurück zum Live-Feed
    #
    # Jeder Ladeschritt läuft in einem eigenen kurzlebigen Thread
    # (dasselbe Muster wie WarcraftLogsProvider), damit ein HTTP-
    # Abruf nie die Oberfläche einfriert. Zwischenstände werden über
    # archiveChanged bekanntgegeben; die Seiten lesen archive_state()
    # neu, statt Daten im Signal mitzuführen.
    #

    def _ensure_archive_client(self):

        with self._lock:

            if self._archive_client is None:

                from core.warcraftlogs_archive_client import (
                    WarcraftLogsArchiveClient,
                )

                self._archive_client = WarcraftLogsArchiveClient()

            return self._archive_client

    def archive_state(self) -> ArchiveState:

        with self._lock:

            return self._archive

    # --------------------------------------------------

    def enter_archive_mode(self):
        """
        Wechselt in den Archiv-Modus. Ist er es schon, passiert außer
        einem eventuellen erneuten Nachladen der Reportliste nichts -
        ein erneutes Öffnen des Tabs soll die laufende Auswahl nicht
        verwerfen.
        """

        with self._lock:

            already_active = self._archive.mode == MODE_ARCHIVE

            if not already_active:

                self._archive = replace(self._archive, mode=MODE_ARCHIVE)

            need_reports = (
                not self._archive.reports
                and not self._archive.reports_loading
                and not self._archive.reports_error
            )

        if not already_active:

            self._publish(RaidSnapshot.empty("Archiv"), track=False)

        self.archiveChanged.emit()

        if need_reports:

            self.refresh_reports()

    def show_live(self):
        """
        Wechselt zurück zum Live-Feed und veröffentlicht sofort den
        aktuellen Stand der konfigurierten Live-Quelle, statt bis zum
        nächsten Poll-Takt zu warten.
        """

        with self._lock:

            if self._archive.mode == MODE_LIVE:
                return

            self._archive = replace(self._archive, mode=MODE_LIVE)

        self.archiveChanged.emit()

        self._poll_once()

    # --------------------------------------------------

    def refresh_reports(self):

        with self._lock:

            if self._archive.reports_loading:
                return

            self._archive = replace(
                self._archive,
                reports_loading=True,
                reports_error="",
            )

        self.archiveChanged.emit()

        threading.Thread(
            target=self._fetch_reports_worker,
            daemon=True,
            name="WarcraftLogsReportsFetch",
        ).start()

    def _fetch_reports_worker(self):

        try:

            result = self._ensure_archive_client().fetch_reports()

            reports, reason = result.reports, result.reason

        except Exception as exc:

            reports, reason = (), f"Unerwarteter Fehler: {exc}"

        with self._lock:

            self._archive = replace(
                self._archive,
                reports=reports,
                reports_loading=False,
                reports_error=reason,
            )

        self.archiveChanged.emit()

    # --------------------------------------------------

    def select_archive_report(self, report_code: str):
        """
        Wählt einen Report aus und lädt seine Fight-Liste. Ist er
        bereits gewählt (und geladen/am Laden), passiert nichts - ein
        erneutes Antippen desselben Eintrags im Dropdown soll nicht
        jedes Mal neu abfragen.

        Setzt den Modus selbst auf Archiv, statt sich auf einen
        vorherigen enter_archive_mode()-Aufruf zu verlassen - eine
        Reportauswahl OHNE Archiv-Modus wäre ein inkonsistenter
        Zustand, den kein Aufrufer erzeugen können soll.
        """

        with self._lock:

            same_selection = (
                self._archive.mode == MODE_ARCHIVE
                and self._archive.selected_report == report_code
                and (self._archive.fights or self._archive.fights_loading)
            )

            if same_selection:
                return

            self._archive = replace(
                self._archive,
                mode=MODE_ARCHIVE,
                selected_report=report_code,
                fights=(),
                fights_loading=True,
                fights_error="",
                selected_fight=None,
                fight_error="",
            )

        self.archiveChanged.emit()

        threading.Thread(
            target=self._fetch_fights_worker,
            args=(report_code,),
            daemon=True,
            name="WarcraftLogsFightsFetch",
        ).start()

    def _fetch_fights_worker(self, report_code: str):

        try:

            result = self._ensure_archive_client().fetch_fights(report_code)

            fights, reason = result.fights, result.reason

        except Exception as exc:

            fights, reason = (), f"Unerwarteter Fehler: {exc}"

        with self._lock:

            #
            # Zwischenzeitlich könnte bereits ein anderer Report
            # gewählt worden sein - dieses Ergebnis gehört dann nicht
            # mehr zur aktuellen Auswahl und wird verworfen.
            #

            if self._archive.selected_report != report_code:
                return

            self._archive = replace(
                self._archive,
                fights=fights,
                fights_loading=False,
                fights_error=reason,
            )

        self.archiveChanged.emit()

    # --------------------------------------------------

    def select_archive_fight(self, report_code: str, fight_id: int):
        """
        Lädt einen einzelnen Fight und macht ihn zum angezeigten
        Snapshot - der eigentliche Zweck des Archiv-Modus.

        Setzt den Modus wie select_archive_report() defensiv selbst
        auf Archiv.
        """

        with self._lock:

            self._archive = replace(
                self._archive,
                mode=MODE_ARCHIVE,
                selected_report=report_code,
                selected_fight=fight_id,
                fight_loading=True,
                fight_error="",
            )

            label = self._archive_report_label(report_code)

        self.archiveChanged.emit()

        threading.Thread(
            target=self._fetch_fight_worker,
            args=(report_code, fight_id, label),
            daemon=True,
            name="WarcraftLogsFightFetch",
        ).start()

    def _archive_report_label(self, report_code: str) -> str:
        """
        Nur unter gehaltenem Lock aufrufen.
        """

        for report in self._archive.reports:

            if report.code == report_code:
                return report.label

        return report_code

    def _fetch_fight_worker(
        self,
        report_code: str,
        fight_id: int,
        label: str,
    ):

        try:

            result = self._ensure_archive_client().fetch_fight(
                report_code,
                fight_id,
            )

        except Exception as exc:

            result = FetchResult(reason=f"Unerwarteter Fehler: {exc}")

        with self._lock:

            #
            # Zwischenzeitlich könnte bereits ein anderer Pull
            # gewählt worden sein - ein spätes Ergebnis für eine alte
            # Auswahl darf die inzwischen getroffene nicht
            # überschreiben.
            #

            stale = (
                self._archive.selected_report != report_code
                or self._archive.selected_fight != fight_id
            )

        if stale:
            return

        if not result.ok:

            with self._lock:

                self._archive = replace(
                    self._archive,
                    fight_loading=False,
                    fight_error=result.reason,
                )

            self.archiveChanged.emit()

            return

        snapshot = snapshot_from_payload(
            result.payload,
            source_label=f"Archiv · {label}",
            live=False,
        )

        self._publish(snapshot, track=False)

        with self._lock:

            self._archive = replace(
                self._archive,
                fight_loading=False,
                fight_error="",
            )

        self.archiveChanged.emit()

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
