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

from PySide6.QtCore import QObject, QTimer, Signal

from analyzer.combatlog.locator import CombatLogLocation, find_combat_log
from analyzer.models import PullSummary, RaidSnapshot
from analyzer.providers.base import RaidDataProvider
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


#
# Wiedergabe: ein archivierter Pull wird Sekunde für Sekunde
# abgespielt. Bewusst ein weiterer Wert desselben `mode`-Feldes und
# kein zweites Flag - sonst gäbe es zwei Antworten auf die Frage
# "darf der Live-Poll gerade veröffentlichen?", und irgendwann
# überschreibt der Poll ein Wiedergabebild.
#

MODE_REPLAY = "replay"


#
# Wählbare Abspielgeschwindigkeiten.
#

REPLAY_SPEEDS = (1.0, 2.0, 4.0, 8.0)


#
# Taktrate der Wiedergabe-Uhr in Millisekunden. Viermal pro Sekunde
# ist flüssig genug fürs Auge und günstig genug, dass die
# Rekonstruktion (reine Rechnung auf höchstens 25 Spielern) im
# Hauptthread laufen kann, statt einen weiteren Thread zu brauchen.
#

REPLAY_TICK_MS = 250


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

    # --------------------------------------------------

    @property
    def is_live(self) -> bool:

        return self.mode == MODE_LIVE

    @property
    def browsing(self) -> bool:
        """
        Ob gerade etwas anderes als der Live-Feed gezeigt wird - der
        eine Schalter, an dem der Live-Poll erkennt, dass er sein
        Ergebnis verwerfen muss.
        """

        return self.mode != MODE_LIVE


@dataclass(frozen=True)
class ReplayState:
    """
    Zustand der Wiedergabe - der Wert, den `ReplayBar` unverändert
    übernimmt.

    Getrennt von `ArchiveState`, obwohl der Modus in dessen `mode`
    steckt: die Archiv-Auswahl (welcher Bericht, welcher Pull) bleibt
    während der Wiedergabe unverändert bestehen, damit das Beenden
    der Wiedergabe wieder genau dort landet, wo man war.
    """

    #
    # `loading` heißt "eine Zeitleiste wird gerade geholt", `starting`
    # zusätzlich "und danach soll sofort abgespielt werden".
    #
    # Die Trennung ist nötig, seit die Zeitleiste bereits mit der Wahl
    # des Pulls im Hintergrund geladen wird (siehe
    # RaidDataService.select_archive_fight): währenddessen ist
    # `loading` wahr, ohne dass der Nutzer irgendetwas gedrückt hätte.
    # Der Wiedergabe-Knopf darf dann weder ausgegraut sein noch "Wird
    # geladen …" behaupten - er soll drückbar bleiben und den Start
    # eben vormerken.
    #

    loading: bool = False

    starting: bool = False

    error: str = ""

    duration: float = 0.0

    position: float = 0.0

    playing: bool = False

    speed: float = 1.0

    label: str = ""

    report_code: str = ""

    fight_id: int | None = None

    #
    # Modus, aus dem die Wiedergabe gestartet wurde - dorthin führt
    # das Beenden zurück.
    #

    origin: str = MODE_ARCHIVE

    # --------------------------------------------------

    @property
    def available(self) -> bool:

        return self.duration > 0

    @property
    def progress(self) -> float:

        if self.duration <= 0:
            return 0.0

        return max(0.0, min(1.0, self.position / self.duration))

    @property
    def clock(self) -> str:

        return _clock(self.position)

    @property
    def total_clock(self) -> str:

        return _clock(self.duration)


def _clock(value: float) -> str:

    total = max(0, int(value))

    return f"{total // 60:02d}:{total % 60:02d}"


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

    #
    # Wird bei jeder Änderung der Wiedergabe emittiert (geladen,
    # Position, Geschwindigkeit, Play/Pause). Ebenfalls ohne Payload,
    # aus demselben Grund wie archiveChanged: ReplayBar liest
    # replay_state() neu.
    #

    replayChanged = Signal()

    #
    # Rein interner Kanal: "bring die Wiedergabe-Uhr in Einklang mit
    # dem Zustand".
    #
    # Er ist nötig, weil ein QTimer nur in dem Thread bedient werden
    # darf, dem er gehört - hier der Hauptthread. Die Zeitleiste wird
    # aber in einem kurzlebigen Arbeitsthread geladen, und der rief
    # bisher direkt `QTimer.start()` auf. Qt lehnt das ab
    # ("Timers cannot be started from another thread"), OHNE eine
    # Ausnahme zu werfen: die Wiedergabe blieb stumm bei 00:00 stehen,
    # und der Wiedergabe-Knopf sah schlicht kaputt aus.
    #
    # Über ein Signal wird der Aufruf in den Besitzerthread
    # zugestellt. Aus dem Hauptthread heraus bleibt er direkt und
    # damit synchron - dieselbe Mechanik wie bei
    # _AutoSyncStarter.requested im CompanionManager.
    #
    # Bewusst OHNE "starten/anhalten" als Nutzlast: aus einem
    # Arbeitsthread wird das Signal in die Warteschlange gelegt und
    # erst später zugestellt. Ein mitgeschicktes "starten" könnte bis
    # dahin überholt sein und die Uhr für eine längst beendete
    # Wiedergabe anwerfen. Der Empfänger liest den Zustand deshalb
    # selbst - eine späte Zustellung ist dann höchstens überflüssig,
    # nie falsch.
    #

    _clockRequested = Signal()

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

        #
        # Der zuletzt aus dem Archiv geladene Snapshot. Er wird
        # gemerkt, damit das Beenden der Wiedergabe sofort wieder
        # dorthin zurückführt, statt den Fight erneut abzurufen.
        #

        self._archive_snapshot = None

        #
        # Wiedergabe (siehe ReplayState oben).
        #

        self._replay = ReplayState()

        self._timeline = None

        #
        # Die Uhr der Wiedergabe. Ein QTimer im Hauptthread und kein
        # weiterer Thread: die Rekonstruktion ist reine Rechnung auf
        # höchstens 25 Spielern, und ein Thread müsste seine
        # Ergebnisse ohnehin wieder über ein Signal zurückreichen.
        # Dasselbe Muster wie der Sync-Timer im CompanionManager.
        #

        self._replay_timer = QTimer(self)

        self._replay_timer.setInterval(REPLAY_TICK_MS)

        self._replay_timer.timeout.connect(self._on_replay_tick)

        self._clockRequested.connect(self._apply_replay_clock)

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

        #
        # Eine aus der alten Quelle gebaute Zeitleiste gehört ihr -
        # sie in der neuen weiterlaufen zu lassen wäre dieselbe
        # Vermischung, die weiter unten für die Historie ausgeschlossen
        # wird.
        #

        self._discard_replay()

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

            if self._archive.browsing:
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

        self._discard_replay()

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

        #
        # Eine geladene Zeitleiste gehört zum bisher gewählten Pull
        # und darf einen anderen Bericht nicht überdauern.
        #

        self._discard_replay()

        with self._lock:

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

        #
        # Wie beim Bericht: die Zeitleiste des zuvor gewählten Pulls
        # verwerfen, sonst spielt der Wiedergabe-Knopf den falschen
        # Kampf ab.
        #

        self._discard_replay()

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

        #
        # Die Zeitleiste wird ebenfalls im Voraus geholt, aber erst
        # NACHDEM der Pull da ist - siehe das Ende von
        # _fetch_fight_worker().
        #

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

            #
            # Für die Rückkehr aus der Wiedergabe merken, damit sie
            # ohne erneuten Abruf sofort wieder hier landet.
            #

            self._archive_snapshot = snapshot

        self.archiveChanged.emit()

        #
        # Erst jetzt die Zeitleiste vorladen - nicht parallel zum
        # Pull.
        #
        # Beide Abrufe lesen beim Bot dieselben Ereignisströme eines
        # ganzen Kampfes, und der Bot läuft auf 0,15 vCPU. Parallel
        # gestartet konkurrierten sie um genau die Anfrage, auf die
        # der Nutzer gerade wartet: die Auswahl eines Pulls endete
        # dann mit "Bot nicht erreichbar: The read operation timed
        # out", während im Bot-Log zu sehen war, dass der Pull kurz
        # darauf sehr wohl fertig wurde.
        #
        # Der Zweck des Vorladens bleibt erhalten: die Wartezeit liegt
        # weiterhin vor dem Wiedergabe-Knopf statt hinter ihm - sie
        # beginnt nur eine Antwort später. Bei einem Fehlschlag wird
        # gar nicht erst vorgeladen: ein Bot, der den kleineren Abruf
        # nicht beantworten konnte, soll nicht sofort mit dem größten
        # belegt werden.
        #

        self.prefetch_timeline(report_code, fight_id)

    # --------------------------------------------------
    # Wiedergabe
    # --------------------------------------------------
    #
    # Ablauf, die ReplayBar bildet ihn direkt ab:
    #
    #   start_replay()          -> Zeitleiste lädt, Wiedergabe beginnt
    #   set_replay_playing()    -> Pause / Fortsetzen
    #   seek_replay(seconds)    -> Springen im Kampf
    #   set_replay_speed(x)     -> 1x bis 8x
    #   stop_replay()           -> zurück zum Ausgangsmodus
    #
    # Die Uhr ist ein QTimer im Hauptthread (siehe __init__). Das
    # Laden der Zeitleiste läuft dagegen in einem kurzlebigen Thread,
    # nach demselben Muster wie die Archiv-Abrufe - ein langsamer Bot
    # darf die Oberfläche nie einfrieren.
    #

    def replay_state(self) -> ReplayState:

        with self._lock:

            return self._replay

    def replay_available(self) -> bool:
        """
        Ob für die aktuelle Auswahl überhaupt eine Wiedergabe in
        Frage kommt - im Archiv, sobald ein Pull gewählt ist, live
        nur bei Quellen, die eine Zeitleiste liefern können.

        Zwei frühere Fehler stecken in dieser kleinen Methode:

        `hasattr(provider, "timeline")` war immer wahr, weil
        RaidDataProvider die Methode selbst mitbringt (und None
        zurückgibt). Der Wiedergabe-Knopf erschien damit auch für
        Quellen, die gar keine Zeitleiste liefern können, und
        quittierte den Druck mit einer Fehlermeldung. Gefragt ist,
        ob die Klasse sie ÜBERSCHREIBT - das bleibt automatisch
        richtig, wenn eine neue Quelle dazukommt.

        Und der Provider wurde nur geprüft, nicht erzeugt: beim
        Aufbau der Seite existiert er noch nicht (er entsteht erst im
        Poll-Thread), also war die Antwort "nein" und der Knopf blieb
        unsichtbar. Die Konstruktoren machen keine Ein-/Ausgabe,
        deshalb ist das Erzeugen hier unbedenklich.
        """

        with self._lock:

            if self._archive.mode == MODE_REPLAY:
                return True

            if self._archive.mode == MODE_ARCHIVE:
                return self._archive.selected_fight is not None

            try:
                provider = self._ensure_provider()

            except Exception as exc:

                self.manager.logger.error(
                    f"Datenquelle konnte nicht erzeugt werden: {exc}"
                )

                return False

        return (
            type(provider).timeline
            is not RaidDataProvider.timeline
        )

    # --------------------------------------------------

    def start_replay(self):
        """
        Startet die Wiedergabe des gerade gewählten Pulls.

        Zwei Wege, ein Ziel: im Archiv wird die Zeitleiste beim Bot
        angefragt, live liefert der Provider sie direkt (bei der
        Simulation ist das reine Rechnung). Ist bereits eine
        Wiedergabe geladen, wird sie nur zurückgespult - ein
        erneuter Abruf derselben Daten wäre Verschwendung. Im Archiv
        ist das inzwischen der Regelfall: die Zeitleiste wird schon
        beim Wählen des Pulls im Hintergrund geholt (siehe
        select_archive_fight), der Druck auf Wiedergabe startet dann
        ohne jede Wartezeit.

        Läuft dieser Abruf noch, wird der Start nur VORGEMERKT statt
        verworfen. Vorher endete der Aufruf in dem Fall wortlos - der
        Knopf sah kaputt aus, weil ein Druck zum falschen Zeitpunkt
        schlicht nichts tat.
        """

        with self._lock:

            if self._replay.loading:

                if self._replay.starting:
                    return

                self._replay = replace(
                    self._replay,
                    starting=True,
                    error="",
                )

                pending = True

            else:

                pending = False

        if pending:

            self.replayChanged.emit()

            return

        with self._lock:

            if self._timeline is not None:

                self._replay = replace(
                    self._replay,
                    position=0.0,
                    playing=True,
                    error="",
                )

                #
                # Auch beim Zurückspulen den Modus setzen. Ohne das
                # blieb ein Neustart aus dem Archiv heraus in
                # MODE_ARCHIVE stehen - und _advance_replay() rührt
                # sich in jedem anderen Modus als MODE_REPLAY nicht,
                # die Wiedergabe stand also bei 00:00 still.
                #

                self._archive = replace(self._archive, mode=MODE_REPLAY)

                restart = True

            else:

                restart = False

                report_code = self._archive.selected_report

                fight_id = self._archive.selected_fight

                origin = (
                    MODE_ARCHIVE
                    if self._archive.mode == MODE_ARCHIVE
                    else MODE_LIVE
                )

                label = self._archive_report_label(report_code)

                self._replay = replace(
                    self._replay,
                    loading=True,
                    starting=True,
                    error="",
                    report_code=report_code,
                    fight_id=fight_id,
                    origin=origin,
                )

        if restart:

            self._sync_replay_clock()

            self._publish_replay_frame()

            self.archiveChanged.emit()

            self.replayChanged.emit()

            return

        self.replayChanged.emit()

        #
        # Beide Wege laden in einem eigenen kurzlebigen Thread. Beim
        # Archiv ist das ein HTTP-Abruf, live eine Rechnung über den
        # ganzen Kampf (25 Spieler mal 180 Sekunden) - beides gehört
        # nicht in den Klick-Handler, sonst steht die Oberfläche.
        #

        if origin == MODE_LIVE:

            threading.Thread(
                target=self._begin_live_replay,
                daemon=True,
                name="ReplayTimelineBuild",
            ).start()

            return

        threading.Thread(
            target=self._fetch_timeline_worker,
            args=(report_code, fight_id, label),
            daemon=True,
            name="WarcraftLogsTimelineFetch",
        ).start()

    # --------------------------------------------------

    def prefetch_timeline(self, report_code: str, fight_id: int):
        """
        Holt die Zeitleiste eines Pulls im Voraus, ohne sie
        abzuspielen.

        Der Grund ist die gefühlte Ladezeit. Bis hierher lagen
        zwischen "Archiv öffnen" und "es läuft" vier Abrufe beim Bot,
        die alle erst nacheinander starteten: Berichte, Pulls, der
        Pull selbst - und erst auf Knopfdruck die Zeitleiste, mit
        Abstand die größte Antwort von allen. Die Wartezeit lag damit
        vollständig HINTER dem Druck auf Wiedergabe, also genau dort,
        wo sie am meisten stört.

        Jetzt läuft der Zeitleisten-Abruf parallel zum Abruf des
        Pulls: sichtbar wird zuerst weiter der Pull (die kleinere und
        schnellere Antwort), und wer danach auf Wiedergabe drückt,
        wartet im Normalfall gar nicht mehr.

        Schlägt der Abruf fehl, bleibt das absichtlich still - der
        Nutzer hat nichts angefordert. Der Knopf versucht es dann bei
        Bedarf erneut und meldet den Fehler dort, wo er zu einer
        Handlung gehört.
        """

        if not report_code or fight_id is None:
            return

        with self._lock:

            if self._replay.loading or self._timeline is not None:
                return

            label = self._archive_report_label(report_code)

            self._replay = replace(
                self._replay,
                loading=True,
                starting=False,
                error="",
                report_code=report_code,
                fight_id=fight_id,
                origin=MODE_ARCHIVE,
            )

        self.replayChanged.emit()

        threading.Thread(
            target=self._fetch_timeline_worker,
            args=(report_code, fight_id, label),
            daemon=True,
            name="WarcraftLogsTimelinePrefetch",
        ).start()

    def _begin_live_replay(self):
        """
        Wiedergabe aus der laufenden Quelle - für die Simulation der
        einzige Weg, die Wiedergabe ohne Bot vorzuführen.
        """

        with self._lock:

            #
            # Unter dem Lock wie im Poll: sonst könnten Klick und
            # Poll-Takt gleichzeitig je einen Provider erzeugen, und
            # die Wiedergabe käme aus einem anderen Objekt als das
            # Live-Bild.
            #

            provider = self._ensure_provider()

        timeline = None

        reason = ""

        try:

            timeline = provider.timeline()

        except Exception as exc:

            reason = f"Wiedergabe konnte nicht gebaut werden: {exc}"

        if timeline is None or not timeline.has_data:

            self._fail_replay(
                reason
                or "Diese Datenquelle liefert keine Wiedergabe."
            )

            return

        self._begin_replay(timeline)

    def _fetch_timeline_worker(
        self,
        report_code: str,
        fight_id: int,
        label: str,
    ):

        try:

            result = self._ensure_archive_client().fetch_timeline(
                report_code,
                fight_id,
            )

        except Exception as exc:

            result = FetchResult(reason=f"Unerwarteter Fehler: {exc}")

        with self._lock:

            #
            # Wie bei den Archiv-Abrufen: ein spätes Ergebnis für eine
            # inzwischen verworfene Auswahl darf nichts überschreiben.
            #

            stale = (
                self._replay.report_code != report_code
                or self._replay.fight_id != fight_id
            )

        if stale:
            return

        if not result.ok:

            self._fail_replay(result.reason)

            return

        from analyzer.replay.payload import timeline_from_payload

        try:

            timeline = timeline_from_payload(
                result.payload,
                source_label=f"Wiedergabe · {label}",
            )

        except Exception as exc:

            self._fail_replay(f"Zeitleiste unlesbar: {exc}")

            return

        if not timeline.has_data:

            self._fail_replay(
                "Für diesen Pull liegt keine Zeitleiste vor."
            )

            return

        self._begin_replay(timeline)

    def _begin_replay(self, timeline):
        """
        Die geladene Zeitleiste übernehmen.

        Ob dabei auch losgespielt wird, entscheidet `starting` und
        nicht der Aufrufer: der Abruf kann eine Vorabladung gewesen
        sein (dann bleibt alles stehen, wie es ist), oder der Nutzer
        hat währenddessen auf Wiedergabe gedrückt - dann steht das
        Flag längst, und genau dafür wurde es gesetzt.
        """

        with self._lock:

            self._timeline = timeline

            play = self._replay.starting

            if play:

                self._archive = replace(self._archive, mode=MODE_REPLAY)

            self._replay = replace(
                self._replay,
                loading=False,
                starting=False,
                error="",
                duration=timeline.duration,
                position=0.0,
                playing=play,
                label=timeline.source_label,
            )

        if not play:

            #
            # Eine Vorabladung darf das gezeigte Bild nicht anfassen -
            # auf dem Schirm steht der Pull aus dem Archiv, und der
            # bleibt stehen, bis jemand Wiedergabe drückt.
            #

            self.replayChanged.emit()

            return

        self._publish_replay_frame()

        self._sync_replay_clock()

        self.archiveChanged.emit()

        self.replayChanged.emit()

    def _fail_replay(self, reason: str):
        """
        Ein gescheiterter Zeitleisten-Abruf.

        Der Text erscheint nur, wenn tatsächlich jemand auf
        Wiedergabe gedrückt hat. Eine im Hintergrund gescheiterte
        Vorabladung wird protokolliert und sonst verschwiegen: eine
        Fehlermeldung für etwas, das der Nutzer nie angefordert hat,
        wäre nur beunruhigend - und der Knopf fragt beim nächsten
        Druck ohnehin erneut an.
        """

        with self._lock:

            announce = self._replay.starting

            self._replay = replace(
                self._replay,
                loading=False,
                starting=False,
                playing=False,
                error=reason if announce else "",
            )

        if not announce:

            self.manager.logger.warning(
                f"Zeitleiste konnte nicht vorgeladen werden: {reason}"
            )

        self.replayChanged.emit()

    # --------------------------------------------------

    def stop_replay(self):
        """
        Beendet die Wiedergabe und kehrt dorthin zurück, wo sie
        gestartet wurde.
        """

        with self._lock:

            if self._archive.mode != MODE_REPLAY:
                return

            origin = self._replay.origin

            self._timeline = None

            self._replay = ReplayState(speed=self._replay.speed)

            self._archive = replace(self._archive, mode=origin)

            archived = self._archive_snapshot

        self._sync_replay_clock()

        #
        # Der gemerkte Archiv-Snapshot macht die Rückkehr sofortig -
        # ohne ihn müsste der Fight erneut beim Bot abgerufen werden.
        #

        if origin == MODE_ARCHIVE and archived is not None:

            self._publish(archived, track=False)

        elif origin == MODE_LIVE:

            self._poll_once()

        self.archiveChanged.emit()

        self.replayChanged.emit()

    def set_replay_playing(self, playing: bool):
        """
        Play/Pause. Am Ende angekommen spult "Play" zuerst zurück -
        sonst sähe die Schaltfläche kaputt aus.
        """

        with self._lock:

            if self._archive.mode != MODE_REPLAY:
                return

            position = self._replay.position

            if playing and position >= self._replay.duration:
                position = 0.0

            self._replay = replace(
                self._replay,
                playing=playing,
                position=position,
            )

        self._sync_replay_clock()

        self._publish_replay_frame()

        self.replayChanged.emit()

    def toggle_replay(self):

        with self._lock:

            playing = self._replay.playing

        self.set_replay_playing(not playing)

    def seek_replay(self, seconds: float):
        """
        Springt an eine Stelle im Kampf.

        Veröffentlicht sofort, auch im pausierten Zustand - sonst
        würde das Ziehen am Schieberegler nichts zeigen.
        """

        with self._lock:

            if self._archive.mode != MODE_REPLAY:
                return

            self._replay = replace(
                self._replay,
                position=max(
                    0.0,
                    min(self._replay.duration, seconds),
                ),
            )

        self._publish_replay_frame()

        self.replayChanged.emit()

    def set_replay_speed(self, speed: float):
        """
        Unbekannte Werte werden verworfen statt übernommen - eine
        Geschwindigkeit von 0 würde die Wiedergabe stillstehen
        lassen, ohne dass die Oberfläche das erklären könnte.
        """

        if speed not in REPLAY_SPEEDS:
            return

        with self._lock:

            if self._replay.speed == speed:
                return

            self._replay = replace(self._replay, speed=speed)

        self.replayChanged.emit()

    # --------------------------------------------------

    def _apply_replay_clock(self):
        """
        Die Uhr läuft genau dann, wenn eine Wiedergabe läuft.

        Läuft immer im Besitzerthread des Timers (siehe
        _clockRequested) und leitet die Antwort aus dem Zustand ab,
        statt sie sich sagen zu lassen.
        """

        with self._lock:

            running = (
                self._archive.mode == MODE_REPLAY
                and self._replay.playing
            )

        if running:

            if not self._replay_timer.isActive():
                self._replay_timer.start()

            return

        if self._replay_timer.isActive():
            self._replay_timer.stop()

    def _sync_replay_clock(self):
        """
        Nach jeder Zustandsänderung der Wiedergabe aufzurufen -
        gleichgültig aus welchem Thread.
        """

        self._clockRequested.emit()

    def _discard_replay(self):
        """
        Zeitleiste und Wiedergabezustand verwerfen.

        Wird vor jedem Wechsel der Auswahl gerufen (anderer Bericht,
        anderer Pull, andere Datenquelle). Ohne das überlebte die
        Zeitleiste des vorherigen Pulls: `start_replay()` hätte sie
        als "schon geladen" erkannt und statt der neuen Auswahl den
        ALTEN Kampf abgespielt - im Archiv-Modus, in dem die Uhr gar
        nicht läuft, also als Standbild bei 00:00.
        """

        with self._lock:

            was_replaying = self._archive.mode == MODE_REPLAY

            if (
                self._timeline is None
                and not was_replaying
                and self._replay == ReplayState(speed=self._replay.speed)
            ):
                return

            #
            # Zurück in die Ansicht, aus der die Wiedergabe gestartet
            # wurde. Pauschal ins Archiv zu wechseln hätte einen
            # Nutzer, der aus dem Live-Feed heraus abgespielt hat,
            # ohne sein Zutun in der Archiv-Auswahl abgesetzt.
            #

            origin = self._replay.origin

            self._timeline = None

            self._replay = ReplayState(speed=self._replay.speed)

            if was_replaying:

                self._archive = replace(self._archive, mode=origin)

        self._sync_replay_clock()

        self.replayChanged.emit()

    def _on_replay_tick(self):

        self._advance_replay(REPLAY_TICK_MS / 1000.0)

    def _advance_replay(self, delta: float):
        """
        Ein Takt der Wiedergabe.

        Bewusst als eigene Methode und nicht im Timer-Slot: so können
        Tests die Wiedergabe Schritt für Schritt durchlaufen, ohne auf
        eine echte Uhr zu warten.
        """

        with self._lock:

            if self._archive.mode != MODE_REPLAY:
                return

            if not self._replay.playing:
                return

            position = self._replay.position + delta * self._replay.speed

            finished = position >= self._replay.duration

            self._replay = replace(
                self._replay,
                position=min(position, self._replay.duration),
                playing=not finished,
            )

        if finished:

            #
            # Am Ende stehen bleiben statt zurückzuspringen: der
            # letzte Stand ist das Ergebnis des Pulls und genau das,
            # was man danach ansehen will. Dieselbe Überlegung wie
            # bei der Nachlaufphase der Simulation.
            #

            self._sync_replay_clock()

        self._publish_replay_frame()

        self.replayChanged.emit()

    def _publish_replay_frame(self):

        with self._lock:

            timeline = self._timeline

            position = self._replay.position

            label = self._replay.label

        if timeline is None:
            return

        from analyzer.replay import snapshot_at

        #
        # track=False: ein wiedergegebener Pull findet nicht jetzt
        # statt. Ließe man ihn in die Historie, entstünde bei jedem
        # Takt ein Eintrag - die Pull-Nummer ändert sich ja nie.
        #

        self._publish(
            snapshot_at(timeline, position, label),
            track=False,
        )

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

        #
        # Erst die Wiedergabe verwerfen, dann die Uhr angleichen: sie
        # leitet ihren Lauf aus dem Zustand ab, ein bloßes "anhalten"
        # gäbe es hier gar nicht mehr.
        #

        self._discard_replay()

        self._stop_thread()
