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

    def __init__(self, reports_result=None, fights_result=None, fight_result=None):

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

        self.report_calls = 0
        self.fights_calls = 0
        self.fight_calls = 0

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
