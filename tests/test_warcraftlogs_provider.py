"""
Der WarcraftLogs-Provider ist die einzige Quelle mit eigenem
Hintergrund-Thread. Geprüft wird deshalb vor allem sein Verhalten an
den Rändern: dass snapshot() nie blockiert und nie wirft, dass ein
fehlgeschlagener Abruf die Quelle nicht dauerhaft stumm schaltet und
dass ein veralteter Bericht verworfen statt weiter als aktuell
ausgegeben wird.
"""

import threading
import time

from analyzer.models import RaidSnapshot
from analyzer.providers import warcraftlogs as module
from analyzer.providers.base import RaidDataProvider
from analyzer.providers.warcraftlogs import (
    FetchResult,
    WarcraftLogsProvider,
)


PAYLOAD = {

    "report": {
        "code": "aBcDeF12",
        "zone": "Thron des Donners",
    },

    "fight": {
        "name": "Horridon",
        "duration": 120.0,
        "in_progress": True,
        "raid_size": 25,
        "boss_percentage": 55.0,
        "pull_number": 3,
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


class FakeFetch:
    """
    Ersetzt den HTTP-Abruf. Meldet über ein Event, dass sie
    aufgerufen wurde - so warten die Tests auf ein Ereignis statt auf
    eine geschätzte Zeitspanne.
    """

    def __init__(self, result=None, error=None):

        self.result = result

        self.error = error

        self.calls = 0

        self.called = threading.Event()

    def __call__(self):

        self.calls += 1

        self.called.set()

        if self.error is not None:
            raise self.error

        return self.result


def _wait_for(event, timeout=5.0):

    assert event.wait(timeout), "Abruf ist nicht erfolgt"


def _started(provider):
    """
    Startet den Provider und stellt sicher, dass er am Ende des
    Tests wieder beendet wird.
    """

    provider.start()

    return provider


# --------------------------------------------------
# Vertrag
# --------------------------------------------------


def test_implements_the_provider_interface():

    provider = WarcraftLogsProvider(FakeFetch())

    assert isinstance(provider, RaidDataProvider)

    assert provider.live is True
    assert provider.source_label == "WarcraftLogs"


def test_snapshot_before_start_is_empty_but_valid():

    provider = WarcraftLogsProvider(FakeFetch())

    snapshot = provider.snapshot()

    assert isinstance(snapshot, RaidSnapshot)
    assert snapshot.has_data is False
    assert snapshot.source_label == "WarcraftLogs"


# --------------------------------------------------
# Lebenszyklus
# --------------------------------------------------


def test_start_is_idempotent_and_starts_only_one_worker():
    """
    Der RaidDataService ruft start() bei JEDEM Poll auf - ohne
    Idempotenz entstünde im Sekundentakt ein neuer Thread.
    """

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    try:

        before = threading.active_count()

        for _ in range(5):
            provider.start()

        _wait_for(fetch.called)

        assert threading.active_count() <= before + 1

    finally:
        provider.stop()


def test_stop_releases_the_cached_report():

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    _wait_for(fetch.called)

    assert provider.snapshot().has_data is True

    provider.stop()

    assert provider.snapshot().has_data is False


def test_stop_is_idempotent():

    provider = WarcraftLogsProvider(FakeFetch())

    provider.stop()
    provider.stop()

    assert provider.snapshot().has_data is False


def test_restart_does_not_leave_a_second_worker_behind():
    """
    Folgen stop() und start() dicht aufeinander, darf der alte
    Abruf-Thread nicht neben dem neuen weiterlaufen.
    """

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    try:

        before = threading.active_count()

        for _ in range(5):

            provider.start()
            provider.stop()

        provider.start()

        _wait_for(fetch.called)

        assert threading.active_count() <= before + 1

    finally:
        provider.stop()


# --------------------------------------------------
# Daten
# --------------------------------------------------


def test_fetched_report_becomes_a_snapshot():

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        snapshot = provider.snapshot()

        assert snapshot.live is True
        assert snapshot.in_combat is True
        assert snapshot.encounter_name == "Horridon"
        assert snapshot.pull_number == 3
        assert snapshot.top_damage[0].name == "Pyrothal"

    finally:
        provider.stop()


def test_snapshot_is_served_from_the_cache_without_fetching():
    """
    Der Service fragt im Sekundentakt, WarcraftLogs liefert aber nur
    alle paar Sekunden Neues. snapshot() darf deshalb nie selbst
    abrufen - sonst entstünde pro Sekunde eine HTTP-Anfrage.
    """

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        calls = fetch.calls

        for _ in range(20):
            provider.snapshot()

        assert fetch.calls == calls

    finally:
        provider.stop()


def test_status_text_names_the_report():

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        status = provider.status_text

        assert "Thron des Donners" in status
        assert "aBcDeF12" in status

    finally:
        provider.stop()


# --------------------------------------------------
# Fehlerfälle
# --------------------------------------------------


def test_a_failing_fetch_becomes_a_status_text_not_an_exception():

    fetch = FakeFetch(error=RuntimeError("Netzwerk weg"))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        assert provider.snapshot().has_data is False

        assert "Netzwerk weg" in provider.status_text

    finally:
        provider.stop()


def test_a_failing_fetch_does_not_kill_the_worker():
    """
    Würde die Ausnahme den Thread beenden, bliebe die Quelle nach
    einer einzigen Störung dauerhaft stumm.
    """

    fetch = FakeFetch(error=RuntimeError("kurzzeitig"))

    provider = WarcraftLogsProvider(fetch, fetch_interval=0.01)

    _started(provider)

    try:

        _wait_for(fetch.called)

        deadline = time.monotonic() + 5.0

        while fetch.calls < 3 and time.monotonic() < deadline:
            time.sleep(0.01)

        assert fetch.calls >= 3

    finally:
        provider.stop()


def test_an_unexpected_return_value_is_handled():

    fetch = FakeFetch(result="kein FetchResult")

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        assert provider.snapshot().has_data is False

        assert provider.status_text

    finally:
        provider.stop()


def test_a_reason_without_payload_keeps_the_previous_report():
    """
    Ein einzelner erfolgloser Abruf (Bot kurz nicht erreichbar) darf
    den zuletzt bekannten Stand nicht wegwerfen - er ist immer noch
    die beste verfügbare Auskunft.
    """

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=0.01)

    _started(provider)

    try:

        _wait_for(fetch.called)

        fetch.result = FetchResult(reason="Bot nicht erreichbar")

        deadline = time.monotonic() + 5.0

        while fetch.calls < 3 and time.monotonic() < deadline:
            time.sleep(0.01)

        assert provider.snapshot().encounter_name == "Horridon"

    finally:
        provider.stop()


def test_a_stale_report_is_dropped():
    """
    Nach einem beendeten Raid soll WeintTV nicht stundenlang
    denselben eingefrorenen Pull zeigen, als liefe er noch.
    """

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(
        fetch,
        fetch_interval=60.0,
        max_age=1.0,
    )

    _started(provider)

    try:

        _wait_for(fetch.called)

        assert provider.snapshot().has_data is True

        #
        # Statt zu warten wird der Abrufzeitpunkt zurückdatiert - das
        # macht den Test unabhängig von echter Zeit.
        #

        provider._fetched_at -= 10.0

        assert provider.snapshot().has_data is False

        assert "Live-Logging" in provider.status_text

    finally:
        provider.stop()


def test_snapshot_never_raises_even_if_the_mapper_fails(monkeypatch):
    """
    Der Vertrag aus providers/base.py gilt ausnahmslos - eine
    Ausnahme hier würde den Poll-Thread des Service beenden.
    """

    def explode(*args, **kwargs):
        raise ValueError("unerwartet")

    monkeypatch.setattr(module, "snapshot_from_payload", explode)

    fetch = FakeFetch(FetchResult(payload=PAYLOAD))

    provider = WarcraftLogsProvider(fetch, fetch_interval=60.0)

    _started(provider)

    try:

        _wait_for(fetch.called)

        snapshot = provider.snapshot()

        assert isinstance(snapshot, RaidSnapshot)
        assert snapshot.has_data is False

    finally:
        provider.stop()


# --------------------------------------------------
# Registrierung
# --------------------------------------------------


def test_the_source_is_registered_in_the_service():
    """
    Ohne den Eintrag in der Registry wäre die Quelle nicht
    auswählbar - und der Service fiele stillschweigend auf die
    Simulation zurück.
    """

    from core.raid_data_service import (
        SOURCE_DESCRIPTIONS,
        SOURCE_LABELS,
        SOURCE_WARCRAFTLOGS,
        PROVIDER_FACTORIES,
    )

    assert SOURCE_WARCRAFTLOGS in PROVIDER_FACTORIES
    assert SOURCE_WARCRAFTLOGS in SOURCE_LABELS
    assert SOURCE_WARCRAFTLOGS in SOURCE_DESCRIPTIONS


def test_the_factory_builds_a_provider_without_arguments():
    """
    Die Registry ruft jede Fabrik ohne Argumente auf.
    """

    from core.raid_data_service import (
        SOURCE_WARCRAFTLOGS,
        PROVIDER_FACTORIES,
    )

    provider = PROVIDER_FACTORIES[SOURCE_WARCRAFTLOGS]()

    assert isinstance(provider, WarcraftLogsProvider)

    #
    # Ohne Start darf nichts abgerufen werden - insbesondere darf das
    # bloße Erzeugen keine Netzwerkverbindung aufbauen.
    #

    assert provider.snapshot().has_data is False
