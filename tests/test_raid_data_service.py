"""
Die Live/Archiv-Zustandsmaschine des RaidDataService.

core/raid_data_service.py importiert PySide6 auf Modulebene
(RaidDataService ist ein QObject), core/warcraftlogs_archive_client.py
importiert httpx - die CI-Testumgebung installiert laut CLAUDE.md aber
bewusst nur pytest, weil die Testsuite nur die Qt-freien Teile
abdecken soll (siehe auch tests/test_warcraftlogs_provider.py). Anders
als dort ist der Skip hier bewusst auf MODULEBENE plaziert statt je
Testfunktion: jeder einzelne Test in dieser Datei prüft
RaidDataService und braucht PySide6 damit zwangsläufig - ein
Mischbetrieb wie in test_warcraftlogs_provider.py (ein paar Qt-freie
Tests neben ein paar Qt-gebundenen) gibt es hier nicht. Ein
Pro-Funktion-Guard würde außerdem zu spät greifen: mehrere Tests
bauen ihr _FakeArchiveClient-Objekt bereits als Argument-Ausdruck für
_make_service(...), also BEVOR dessen Rumpf überhaupt liefe - und
_FakeArchiveClient importiert seinerseits aus
core.warcraftlogs_archive_client (httpx).

Geprüft wird vor allem, was beim Zusammenspiel von Live- und
Archiv-Modus schiefgehen könnte: dass der Live-Poll einen gepinnten
Archiv-Snapshot nicht überschreibt, dass ein archivierter Fight nicht
in die Pull-Historie der laufenden Sitzung einfließt, und dass ein
verspätetes Ergebnis einer inzwischen verlassenen Auswahl nichts mehr
überschreibt.
"""

import os
import threading
import time

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("httpx")


PAYLOAD = {
    "fight": {
        "name": "Horridon",
        "duration": 180.0,
        "in_progress": False,
        "boss_percentage": 42.5,
        "pull_number": 7,
    },
    "players": [
        {
            "name": "Pyrothal",
            "class": "Mage",
            "role": "dps",
            "damage_total": 12000000.0,
        },
    ],
}


#
# Eine winzige, aber vollständige Zeitleiste: zwei Spieler, sechs
# Sekunden. Groß genug, damit Interpolation, Ereignisse und
# Rangliste durchlaufen, klein genug, um sie im Test zu überblicken.
#

TIMELINE_PAYLOAD = {
    "interval": 1.0,
    "fight": {
        "name": "Horridon",
        "duration": 6.0,
        "raid_size": 2,
        "pull_number": 7,
        "battle_res_max": 3,
    },
    "boss_health": [100.0, 90.0, 80.0, 60.0, 40.0, 20.0, 0.5],
    "players": [
        {
            "name": "Pyrothal",
            "class": "Mage",
            "role": "dps",
            "damage": [0.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0],
        },
        {
            "name": "Elvenne",
            "class": "Druid",
            "role": "healer",
            "healing": [0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0],
        },
    ],
    "deaths": [{"name": "Pyrothal", "at": 4.0, "ability": "Double Swipe"}],
}


class _Logger:

    def info(self, message):
        pass

    def error(self, message):
        pass

    def warning(self, message):
        pass

    def success(self, message):
        pass


class _Config:

    def __init__(self):
        self.data = {"raid_data_source": "mock"}


class _Manager:

    def __init__(self):
        self.logger = _Logger()
        self.config = _Config()


class _FakeArchiveClient:
    """
    Ersetzt WarcraftLogsArchiveClient. Jede Methode kann per
    Konstruktor-Argument ein fest verdrahtetes Ergebnis oder eine
    Ausnahme liefern, um Fehlerpfade zu prüfen.
    """

    def __init__(
        self,
        reports_result=None,
        fights_result=None,
        fight_result=None,
        timeline_result=None,
        timeline_gate=None,
    ):

        from core.warcraftlogs_archive_client import (
            FightsFetchResult,
            ReportsFetchResult,
        )
        from analyzer.providers.warcraftlogs_payload import (
            FightSummary,
            ReportSummary,
        )

        self.reports_result = reports_result or ReportsFetchResult(
            reports=(
                ReportSummary(code="aBc", title="Mittwoch", zone="Thron des Donners"),
            ),
        )

        self.fights_result = fights_result or FightsFetchResult(
            fights=(
                FightSummary(fight_id=12, encounter_name="Horridon", pull_number=7),
            ),
        )

        self.fight_result = fight_result

        self.timeline_result = timeline_result

        #
        # Ein optionales threading.Event, auf das fetch_timeline
        # wartet. Nötig, seit die Zeitleiste schon beim Wählen eines
        # Pulls im Hintergrund geladen wird: ohne eine Bremse wäre
        # nicht vorhersagbar, ob dieser Abruf zum Zeitpunkt einer
        # Zusicherung schon durch ist.
        #

        self.timeline_gate = timeline_gate

        self.report_calls = 0
        self.fights_calls = 0
        self.fight_calls = 0
        self.timeline_calls = 0

    def fetch_reports(self):

        self.report_calls += 1

        return self.reports_result

    def fetch_fights(self, report_code):

        self.fights_calls += 1

        return self.fights_result

    def fetch_fight(self, report_code, fight_id):

        from analyzer.providers.warcraftlogs import FetchResult

        self.fight_calls += 1

        if self.fight_result is not None:
            return self.fight_result

        return FetchResult(payload=PAYLOAD)

    def fetch_timeline(self, report_code, fight_id):

        from analyzer.providers.warcraftlogs import FetchResult

        self.timeline_calls += 1

        if self.timeline_gate is not None:
            self.timeline_gate.wait(5.0)

        if self.timeline_result is not None:
            return self.timeline_result

        return FetchResult(payload=TIMELINE_PAYLOAD)


def _wait_until(condition, timeout=5.0):
    """
    Wartet auf `condition()`, verarbeitet dabei fortlaufend die
    Qt-Event-Loop.

    Nötig, weil snapshotChanged/archiveChanged aus einem
    Hintergrund-Thread emittiert werden - Qt liefert eine solche
    Cross-Thread-Verbindung als "queued connection" erst zu, wenn die
    Event-Loop des EMPFÄNGER-Threads (hier: des Haupt-/Testthreads)
    tatsächlich läuft. Ohne dieses Pumpen bliebe jeder auf ein Signal
    wartende Test für immer hängen, obwohl der interne Zustand
    (archive_state()/current()) längst aktualisiert ist.
    """

    from PySide6.QtWidgets import QApplication

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:

        app = QApplication.instance()

        if app is not None:
            app.processEvents()

        if condition():
            return True

        time.sleep(0.01)

    return False


#
# Jeder im Test erzeugte Dienst, damit die Nachbereitung ihn
# garantiert herunterfahren kann.
#

_SERVICES = []


@pytest.fixture(autouse=True)
def _shutdown_services():
    """
    Nach jedem Test alle erzeugten Dienste beenden.

    Nicht bloß Ordnungsliebe: ein Dienst mit laufender Wiedergabe hat
    einen aktiven QTimer. Wird das Objekt später eingesammelt, während
    gerade ein Arbeitsthread rechnet (die Speicherbereinigung läuft in
    dem Thread, der die Zuteilung auslöst), läuft der QObject-
    Destruktor im FALSCHEN Thread - Qt meldet "Timers cannot be
    stopped from another thread" und der Prozess stürzt ab. In der
    Anwendung kann das nicht passieren: dort hält der
    CompanionManager den Dienst und ruft shutdown() beim Beenden.
    """

    yield

    from PySide6.QtWidgets import QApplication

    while _SERVICES:

        _SERVICES.pop().shutdown()

    #
    # Noch anstehende Cross-Thread-Signale zustellen, solange die
    # Objekte sicher am Leben sind.
    #

    app = QApplication.instance()

    if app is not None:
        app.processEvents()


def _make_service(archive_client=None):

    from PySide6.QtWidgets import QApplication
    from core.raid_data_service import RaidDataService

    #
    # Eine QApplication ist Voraussetzung dafür, dass Qt
    # Cross-Thread-Signale überhaupt zustellen kann (siehe
    # _wait_until) - pro Prozess darf nur eine einzige existieren,
    # daher die Wiederverwendung über QApplication.instance().
    #
    # "offscreen" (nur gesetzt, falls nichts anderes konfiguriert
    # ist): in einer Umgebung ohne echtes Display würde Qt beim
    # Erzeugen der QApplication sonst abstürzen.
    #

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    if QApplication.instance() is None:
        QApplication([])

    service = RaidDataService(_Manager())

    service._archive_client = archive_client or _FakeArchiveClient()

    _SERVICES.append(service)

    return service


# --------------------------------------------------
# Grundzustand
# --------------------------------------------------


def test_starts_in_live_mode():

    from core.raid_data_service import MODE_LIVE

    service = _make_service()

    assert service.archive_state().mode == MODE_LIVE


def test_show_live_is_a_no_op_when_already_live():

    service = _make_service()

    service.show_live()

    assert service.archive_state().mode == "live"


# --------------------------------------------------
# Reports laden
# --------------------------------------------------


def test_enter_archive_mode_loads_the_report_list():

    from core.raid_data_service import MODE_ARCHIVE

    service = _make_service()

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    state = service.archive_state()

    assert state.mode == MODE_ARCHIVE
    assert state.reports[0].code == "aBc"
    assert state.reports_error == ""


def test_entering_archive_mode_pins_an_empty_snapshot_immediately():
    """
    Bis ein Fight gewählt ist, soll die Oberfläche nicht den letzten
    Live-Stand stehen lassen - das sähe aus wie noch aktive Live-Daten.
    """

    received = []

    service = _make_service()

    service.snapshotChanged.connect(lambda snapshot: received.append(snapshot))

    service.enter_archive_mode()

    assert received
    assert received[-1].has_data is False


def test_reentering_archive_mode_keeps_the_current_selection():
    """
    Ein erneutes Öffnen des Archiv-Tabs darf eine laufende Auswahl
    nicht verwerfen.
    """

    service = _make_service()

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.enter_archive_mode()

    state = service.archive_state()

    assert state.selected_report == "aBc"
    assert state.fights


def test_a_failing_reports_fetch_surfaces_its_reason():

    from core.warcraftlogs_archive_client import ReportsFetchResult

    client = _FakeArchiveClient(
        reports_result=ReportsFetchResult(reason="Bot nicht erreichbar"),
    )

    service = _make_service(client)

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports_error)

    state = service.archive_state()

    assert state.reports == ()
    assert "Bot nicht erreichbar" in state.reports_error


def test_a_broken_client_does_not_leave_loading_stuck():
    """
    Ein Client, der entgegen seines Vertrags wirft, darf das
    "loading"-Flag nicht für immer auf True stehen lassen - sonst
    zeigt die Oberfläche endlos einen Ladezustand.
    """

    class ExplodingClient:

        def fetch_reports(self):
            raise RuntimeError("unerwartet")

    service = _make_service(ExplodingClient())

    service.enter_archive_mode()

    assert _wait_until(lambda: not service.archive_state().reports_loading)

    assert "unerwartet" in service.archive_state().reports_error


# --------------------------------------------------
# Fights laden
# --------------------------------------------------


def test_select_archive_report_loads_its_fight_list():

    service = _make_service()

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    state = service.archive_state()

    assert state.selected_report == "aBc"
    assert state.fights[0].fight_id == 12
    #
    # Ein Reportwechsel setzt eine zuvor getroffene Fight-Auswahl
    # zurück - sie gehörte zum alten Report.
    #
    assert state.selected_fight is None


def test_a_stale_fights_result_is_discarded():
    """
    Wird zwischen Anfrage und Antwort bereits ein anderer Report
    gewählt, gehört das alte Ergebnis nicht mehr zur aktuellen
    Auswahl.
    """

    release = threading.Event()

    class SlowClient(_FakeArchiveClient):

        def fetch_fights(self, report_code):

            release.wait(2.0)

            return super().fetch_fights(report_code)

    service = _make_service(SlowClient())

    service.select_archive_report("aBc")

    service.select_archive_report("andererReport")

    release.set()

    time.sleep(0.2)

    state = service.archive_state()

    assert state.selected_report == "andererReport"


# --------------------------------------------------
# Einen Fight laden
# --------------------------------------------------


def test_selecting_a_fight_publishes_an_archived_snapshot():

    received = []

    service = _make_service()

    service.snapshotChanged.connect(lambda snapshot: received.append(snapshot))

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: received and received[-1].encounter_name == "Horridon")

    snapshot = received[-1]

    assert snapshot.live is False
    assert snapshot.source_label.startswith("Archiv ·")

    assert service.archive_state().fight_error == ""


def test_archived_snapshot_does_not_enter_the_pull_history():
    """
    Ein aus dem Archiv angesehener Pull ist kein Pull, der gerade in
    dieser Sitzung passiert - er darf WeintTVs "Verlauf"-Tab (die
    Pulls dieser Live-Sitzung) nicht verfälschen.
    """

    service = _make_service()

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.current().encounter_name == "Horridon"
    )

    assert service.history() == ()


def test_a_failing_fight_fetch_keeps_the_previous_snapshot_and_reports_why():

    from analyzer.providers.warcraftlogs import FetchResult

    client = _FakeArchiveClient(
        fight_result=FetchResult(reason="Pull nicht gefunden"),
    )

    service = _make_service(client)

    before = service.current()

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: service.archive_state().fight_error)

    assert service.current() is before
    assert "Pull nicht gefunden" in service.archive_state().fight_error


def test_a_stale_fight_result_does_not_override_a_newer_selection():

    release = threading.Event()

    class SlowFightClient(_FakeArchiveClient):

        def fetch_fight(self, report_code, fight_id):

            release.wait(2.0)

            return super().fetch_fight(report_code, fight_id)

    service = _make_service(SlowFightClient())

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    #
    # Vor Ablauf des künstlichen Verzögerns wird ein anderer Pull
    # gewählt - das späte Ergebnis des ersten Aufrufs gehört danach
    # nicht mehr zur aktuellen Auswahl.
    #

    service.select_archive_fight("aBc", 99)

    release.set()

    time.sleep(0.3)

    assert service.archive_state().selected_fight == 99


# --------------------------------------------------
# Zusammenspiel mit dem Live-Poll
# --------------------------------------------------


def test_live_poll_does_not_overwrite_a_pinned_archive_snapshot():

    received = []

    service = _make_service()

    service.snapshotChanged.connect(lambda snapshot: received.append(snapshot))

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: received and received[-1].encounter_name == "Horridon")

    #
    # Ein manueller Poll-Zyklus (wie ihn der Hintergrund-Thread
    # ständig ausführt) darf den gepinnten Snapshot nicht ersetzen.
    #

    service._poll_once()

    assert service.current().encounter_name == "Horridon"
    assert service.current().live is False


def test_show_live_immediately_restores_the_live_snapshot():

    service = _make_service()

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.current().encounter_name == "Horridon"
    )

    service.show_live()

    assert service.archive_state().mode == "live"
    #
    # Kein Warten auf den nächsten Poll-Takt nötig - show_live() holt
    # sofort einen frischen Stand.
    #
    assert service.current().source_label == "Simulation"


def test_reload_provider_does_not_disturb_an_active_archive_view():
    """
    Ein Wechsel der LIVE-Quelle in den Einstellungen hat mit dem
    gerade betrachteten Archiv-Pull nichts zu tun.
    """

    service = _make_service()

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.current().encounter_name == "Horridon"
    )

    service._listeners = 1

    service.reload_provider()

    assert service.current().encounter_name == "Horridon"


# --------------------------------------------------
# Wiedergabe
# --------------------------------------------------
#
# Die Wiedergabe ist der dritte Modus derselben Zustandsmaschine.
# Gefährlich daran ist genau das, was schon beim Archiv gefährlich
# war: dass der Live-Poll dazwischenfunkt, dass ein spätes Ergebnis
# eine neuere Auswahl überschreibt, und dass wiedergegebene Sekunden
# in der Pull-Historie landen. Abgespielt wird über
# service._advance_replay(delta) statt über eine echte Uhr - sonst
# hinge jeder Test an der Wanduhr.
#


def _replaying_service():
    """
    Ein Service, der bereits einen Pull aus dem Archiv wiedergibt.
    """

    from core.raid_data_service import MODE_REPLAY

    service = _make_service()

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.archive_state().selected_fight == 12
        and not service.archive_state().fight_loading
    )

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    return service


def test_start_replay_loads_the_timeline_and_begins_at_zero():

    service = _replaying_service()

    state = service.replay_state()

    assert state.loading is False
    assert state.error == ""
    assert state.duration == 6.0
    assert state.position == 0.0
    assert state.playing is True

    assert service.current().pull_seconds == 0.0


def test_replay_advances_and_stops_at_the_end():
    """
    Am Ende bleibt die Wiedergabe stehen statt zurückzuspringen - der
    letzte Stand ist das Ergebnis des Pulls.
    """

    service = _replaying_service()

    service._advance_replay(3.0)

    assert service.replay_state().position == 3.0
    assert service.current().pull_seconds == 3.0

    service._advance_replay(10.0)

    state = service.replay_state()

    assert state.position == 6.0
    assert state.playing is False


def test_replay_speed_multiplies_the_step():

    service = _replaying_service()

    service.set_replay_speed(4.0)

    service._advance_replay(1.0)

    assert service.replay_state().position == 4.0


def test_replay_speed_ignores_unknown_values():
    """
    Eine Geschwindigkeit von 0 würde die Wiedergabe stillstehen
    lassen, ohne dass die Oberfläche das erklären könnte.
    """

    service = _replaying_service()

    service.set_replay_speed(0.0)
    service.set_replay_speed(99.0)

    assert service.replay_state().speed == 1.0


def test_seeking_publishes_immediately_even_while_paused():
    """
    Ohne sofortige Veröffentlichung würde das Ziehen am
    Schieberegler nichts zeigen.
    """

    service = _replaying_service()

    service.set_replay_playing(False)

    service.seek_replay(5.0)

    assert service.current().pull_seconds == 5.0


def test_seeking_is_clamped_to_the_fight():

    service = _replaying_service()

    service.seek_replay(-40.0)
    assert service.replay_state().position == 0.0

    service.seek_replay(9999.0)
    assert service.replay_state().position == 6.0


def test_live_poll_does_not_overwrite_a_replay_frame():
    """
    Der Poll-Thread läuft während der Wiedergabe absichtlich weiter,
    damit die Rückkehr zu Live sofort geht. Er darf dabei aber
    niemals das gerade gezeigte Bild überschreiben.
    """

    service = _replaying_service()

    service.seek_replay(2.0)

    before = service.current()

    service._poll_once()

    assert service.current() is before


def test_replayed_seconds_never_enter_the_pull_history():
    """
    Die Pull-Nummer ändert sich während einer Wiedergabe nie - liefe
    sie durch die Historie, entstünde bei jedem Takt ein Eintrag.
    """

    service = _replaying_service()

    for _ in range(10):
        service._advance_replay(1.0)

    assert service.history() == ()


def test_stopping_the_replay_returns_to_the_archived_pull():
    """
    Und zwar ohne den Fight erneut abzurufen - der Snapshot ist
    gemerkt.
    """

    from core.raid_data_service import MODE_ARCHIVE

    service = _replaying_service()

    calls_before = service._archive_client.fight_calls

    service.stop_replay()

    assert service.archive_state().mode == MODE_ARCHIVE

    assert service._archive_client.fight_calls == calls_before

    assert service.current().source_label.startswith("Archiv ·")


def test_show_live_ends_a_running_replay():

    from core.raid_data_service import MODE_LIVE

    service = _replaying_service()

    service.show_live()

    assert service.archive_state().mode == MODE_LIVE

    assert service.replay_state().playing is False

    assert _wait_until(
        lambda: service.current().source_label == "Simulation"
    )


def test_a_failing_timeline_fetch_reports_a_reason_instead_of_raising():

    from analyzer.providers.warcraftlogs import FetchResult
    from core.raid_data_service import MODE_ARCHIVE

    client = _FakeArchiveClient(
        timeline_result=FetchResult(reason="Bot nicht erreichbar."),
    )

    service = _make_service(client)

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.archive_state().selected_fight == 12
    )

    service.start_replay()

    assert _wait_until(
        lambda: service.replay_state().error == "Bot nicht erreichbar."
    )

    #
    # Und der Modus bleibt, wo er war - eine gescheiterte Wiedergabe
    # darf die Archiv-Ansicht nicht verlassen.
    #

    assert service.archive_state().mode == MODE_ARCHIVE
    assert service.replay_state().loading is False


def test_an_exploding_timeline_client_does_not_leave_loading_stuck():

    class _Exploding(_FakeArchiveClient):

        def fetch_timeline(self, report_code, fight_id):
            raise RuntimeError("kaputt")

    service = _make_service(_Exploding())

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.archive_state().selected_fight == 12
    )

    service.start_replay()

    assert _wait_until(lambda: service.replay_state().error != "")

    assert service.replay_state().loading is False


def test_replay_can_be_started_from_the_live_simulation():
    """
    Ohne diesen Weg wäre die Wiedergabe erst vorführbar, sobald der
    Bot den Zeitleisten-Endpunkt liefert.
    """

    from core.raid_data_service import MODE_LIVE, MODE_REPLAY

    service = _make_service()

    assert service.archive_state().mode == MODE_LIVE

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    assert service.replay_state().duration > 0

    #
    # Und das Beenden führt zurück zum Live-Feed, nicht ins Archiv.
    #

    service.stop_replay()

    assert service.archive_state().mode == MODE_LIVE


def test_replay_availability_follows_the_selection():

    service = _make_service()

    service.enter_archive_mode()

    assert _wait_until(lambda: service.archive_state().reports)

    #
    # Im Archiv ohne gewählten Pull gibt es nichts abzuspielen.
    #

    assert service.replay_available() is False

    service.select_archive_report("aBc")

    assert _wait_until(lambda: service.archive_state().fights)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(
        lambda: service.archive_state().selected_fight == 12
    )

    assert service.replay_available() is True


def test_the_replay_clock_actually_runs_after_a_worker_thread_load():
    """
    Der Fehler, der die Wiedergabe unbedienbar machte.

    Die Zeitleiste wird in einem Arbeitsthread geladen, und dort
    wurde die Uhr auch gestartet. Ein QTimer darf aber nur in seinem
    Besitzerthread bedient werden: Qt lehnt das mit einer Meldung auf
    stderr ab und wirft dabei KEINE Ausnahme - die Wiedergabe blieb
    also stumm bei 00:00 stehen, obwohl Zustand und Oberfläche
    "läuft" anzeigten.

    Deshalb prüft dieser Test nicht den Zustand (der war schon vorher
    richtig), sondern den Timer selbst.
    """

    from core.raid_data_service import MODE_REPLAY

    service = _make_service()

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    #
    # Die Uhr wird über ein Signal in den Hauptthread gereicht -
    # _wait_until pumpt die Event-Loop, hier wird also genau die
    # Zustellung mitgeprüft.
    #

    assert _wait_until(lambda: service._replay_timer.isActive())

    service.stop_replay()

    assert service._replay_timer.isActive() is False


def test_choosing_another_pull_discards_the_loaded_timeline():
    """
    Sonst spielt der Wiedergabe-Knopf den vorherigen Kampf ab.

    `start_replay()` erkennt eine bereits geladene Zeitleiste und
    spult sie nur zurück, statt neu zu laden. Blieb sie beim Wechsel
    der Auswahl liegen, gehörte sie zum falschen Pull - und weil der
    Moduswechsel dabei ausblieb, stand die Wiedergabe zusätzlich bei
    00:00 still.
    """

    from core.raid_data_service import MODE_ARCHIVE, MODE_REPLAY

    #
    # Die Vorabladung der neuen Auswahl wird angehalten, damit hier
    # sicher der Zustand UNMITTELBAR nach dem Wechsel geprüft wird
    # und nicht zufällig schon der der neu geladenen Zeitleiste.
    #

    gate = threading.Event()

    service = _make_service(_FakeArchiveClient(timeline_gate=gate))

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    service.select_archive_fight("aBc", 12)

    assert service._timeline is None

    assert service.archive_state().mode == MODE_ARCHIVE

    assert service.replay_state().duration == 0.0

    gate.set()


def test_restarting_a_loaded_replay_returns_to_replay_mode():
    """
    Ein zweiter Druck auf Wiedergabe spult zurück - und muss den
    Modus wieder setzen, sonst rührt sich der Takt nicht.
    """

    from core.raid_data_service import MODE_REPLAY

    service = _make_service()

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    service._advance_replay(10.0)

    assert service.replay_state().position == 10.0

    #
    # Pausieren, ohne die Zeitleiste zu verwerfen - der Zustand, in
    # dem der Knopf ein zweites Mal gedrückt werden kann.
    #

    service.set_replay_playing(False)

    service.start_replay()

    assert service.archive_state().mode == MODE_REPLAY

    assert service.replay_state().position == 0.0

    service._advance_replay(2.0)

    assert service.replay_state().position == 2.0


def test_replay_is_offered_before_the_poll_thread_ever_ran():
    """
    Der Grund, aus dem der Wiedergabe-Knopf im Live-Modus unsichtbar
    blieb.

    `replay_available()` fragte den Provider ab, erzeugte ihn aber
    nicht - und beim Aufbau der Seite existiert er noch nicht, weil
    ihn erst der Poll-Thread anlegt. Die Antwort war deshalb "nein",
    und die Oberfläche fragt danach nie wieder.
    """

    service = _make_service()

    assert service._provider is None

    assert service.replay_available() is True


def test_a_source_without_a_timeline_offers_no_replay():
    """
    Die Gegenprobe: `hasattr(provider, "timeline")` war immer wahr,
    weil die Basisklasse die Methode mitbringt. Gefragt ist, ob die
    Quelle sie überschreibt.
    """

    from analyzer.models import RaidSnapshot
    from analyzer.providers.base import RaidDataProvider

    class _Summen(RaidDataProvider):

        def start(self):
            pass

        def stop(self):
            pass

        def snapshot(self):
            return RaidSnapshot.empty("Nur Summen")

        @property
        def source_label(self):
            return "Nur Summen"

    service = _make_service()

    service._provider = _Summen()

    assert service.replay_available() is False


def test_switching_the_data_source_discards_the_replay():
    """
    Eine Zeitleiste gehört der Quelle, aus der sie stammt.
    """

    from core.raid_data_service import MODE_LIVE, MODE_REPLAY

    service = _make_service()

    service.start_replay()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    service.reload_provider()

    assert service._timeline is None

    assert service.replay_state().duration == 0.0

    #
    # Und zurück in die Ansicht, aus der abgespielt wurde - wer aus
    # dem Live-Feed heraus gestartet hat, soll nicht ungefragt in der
    # Archiv-Auswahl landen.
    #

    assert service.archive_state().mode == MODE_LIVE


# --------------------------------------------------
# Wiedergabe: Vorabladen und vorgemerkter Start
# --------------------------------------------------


def test_choosing_a_pull_preloads_its_timeline():
    """
    Der Grund, aus dem der Wiedergabe-Knopf sich lange "kaputt"
    anfühlte: die mit Abstand größte Antwort des Bots wurde erst auf
    Knopfdruck angefordert. Die Wartezeit lag damit vollständig hinter
    dem Klick.

    Jetzt läuft der Abruf parallel zum Laden des Pulls - und darf
    dabei weder den Modus wechseln noch etwas abspielen.
    """

    from core.raid_data_service import MODE_ARCHIVE

    client = _FakeArchiveClient()

    service = _make_service(client)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: service._timeline is not None)

    assert client.timeline_calls == 1

    assert service.archive_state().mode == MODE_ARCHIVE

    assert service.replay_state().playing is False

    assert service.replay_state().duration > 0.0


def test_a_preloaded_timeline_makes_the_play_button_instant():
    """
    Nach dem Vorabladen darf der Druck auf Wiedergabe keinen zweiten
    Abruf mehr auslösen - er spult nur noch zurück und startet.
    """

    from core.raid_data_service import MODE_REPLAY

    client = _FakeArchiveClient()

    service = _make_service(client)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: service._timeline is not None)

    service.start_replay()

    assert service.archive_state().mode == MODE_REPLAY

    assert service.replay_state().playing is True

    assert client.timeline_calls == 1


def test_pressing_play_during_the_preload_remembers_the_start():
    """
    Der Fall, in dem der Knopf vorher wortlos nichts tat.

    `start_replay()` brach bei laufendem Abruf ab. Seit die Zeitleiste
    schon beim Wählen des Pulls geholt wird, ist genau das der
    wahrscheinlichste Moment für einen Klick - er wird deshalb
    vorgemerkt und beim Eintreffen der Daten ausgeführt.
    """

    from core.raid_data_service import MODE_REPLAY

    gate = threading.Event()

    client = _FakeArchiveClient(timeline_gate=gate)

    service = _make_service(client)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: client.timeline_calls == 1)

    assert service.replay_state().loading is True

    assert service.replay_state().starting is False

    service.start_replay()

    assert service.replay_state().starting is True

    gate.set()

    assert _wait_until(
        lambda: service.archive_state().mode == MODE_REPLAY
    )

    assert service.replay_state().playing is True

    #
    # Und wirklich nur ein einziger Abruf, kein zweiter durch den
    # Klick.
    #

    assert client.timeline_calls == 1


def test_a_failed_preload_stays_quiet_and_can_be_retried():
    """
    Eine im Hintergrund gescheiterte Vorabladung ist keine
    Fehlermeldung wert - der Nutzer hat nichts angefordert. Der Knopf
    muss danach aber erneut anfragen können.
    """

    from analyzer.providers.warcraftlogs import FetchResult

    client = _FakeArchiveClient(
        timeline_result=FetchResult(reason="Bot nicht erreichbar"),
    )

    service = _make_service(client)

    service.select_archive_fight("aBc", 12)

    assert _wait_until(lambda: client.timeline_calls == 1)

    assert _wait_until(
        lambda: service.replay_state().loading is False
    )

    assert service.replay_state().error == ""

    #
    # Jetzt der ausdrückliche Wunsch - und diesmal wird der Fehler
    # auch benannt.
    #

    service.start_replay()

    assert _wait_until(
        lambda: service.replay_state().error == "Bot nicht erreichbar"
    )

    assert client.timeline_calls == 2
