"""
Kommt an, was im Hintergrund gefunden wird?

Zwei Auskünfte der Übersicht wurden bis 2.3.2 genau einmal geholt -
beim Start - und danach nur noch, wenn jemand "Erneut prüfen" drückte:
ob eine neue Fassung bereitliegt, und wie der Stand der Anmeldungen
ist. Beide Anzeigen hängen an `CompanionManager.state_changed`, und das
kam nach dem Start schlicht nicht mehr. Wer die Anwendung morgens
öffnete und abends damit raidete, sah abends den Stand vom Morgen -
ohne dass irgendetwas fehlgeschlagen wäre.

Geprüft werden die drei Teile, aus denen die Behebung besteht:

- `refresh_interval()` - der Takt des Terminabrufs richtet sich nach
  dem Termin (Minutentakt am Raidtag, sonst träge).
- `RaidScheduleSync.process()` / `UpdateWatch.process()` - beide melden
  **die Änderung**, nicht den Abruf. Ein Abruf mit gleichem Ergebnis
  darf die Oberfläche nicht neu zeichnen lassen.
- `CompanionManager._run_sync_worker()` - macht aus dieser Meldung
  genau ein `state_changed`, und bei einem Durchgang ohne Änderung
  keines.
"""

import types
from datetime import datetime, timedelta, timezone

import pytest

from core.raid_schedule import RaidDay, RaidSchedule, RosterSlot
from core.raid_schedule_sync import (
    REFRESH_SECONDS,
    REFRESH_SECONDS_SOON,
    refresh_interval,
)


class _Logger:

    def __init__(self):
        self.lines = []

    def _note(self, text):
        self.lines.append(str(text))

    info = success = warning = error = _note


def _schedule(minutes_ahead: int | None, **extra) -> RaidSchedule:
    """
    Ein Raid, der in `minutes_ahead` Minuten beginnt (negativ: er
    läuft schon). `None` heißt "Termin bekannt, Zeitpunkt nicht".
    """

    starts_at = (
        None
        if minutes_ahead is None
        else datetime.now(timezone.utc) + timedelta(minutes=minutes_ahead)
    )

    day = RaidDay(
        key="mi",
        label="Mittwoch",
        starts_at=starts_at,
        **extra,
    )

    return RaidSchedule(
        known=True,
        title="Siege of Orgrimmar",
        raid_size=25,
        days=(day,),
    )


# --------------------------------------------------
# Der Takt des Terminabrufs
# --------------------------------------------------


def test_ohne_termin_bleibt_es_beim_traegen_takt():
    """
    Für eine Auskunft, die es nicht gibt, lohnt kein Minutentakt.
    """

    assert refresh_interval(RaidSchedule()) == REFRESH_SECONDS

    assert refresh_interval(None) == REFRESH_SECONDS


def test_ein_raid_in_zwei_tagen_wird_traege_abgefragt():

    assert refresh_interval(_schedule(2 * 24 * 60)) == REFRESH_SECONDS


def test_am_raidtag_wird_im_minutentakt_gefragt():
    """
    Der Stand der Anmeldungen ist die Auskunft, wegen der jemand kurz
    vor dem Raid überhaupt hinsieht - fünf Minuten alte Zahlen sehen
    dort aus wie eine kaputte Karte.
    """

    assert refresh_interval(_schedule(90)) == REFRESH_SECONDS_SOON


def test_waehrend_des_laufenden_raids_ebenfalls():
    """
    `is_running()` zieht die hintere Grenze: solange gespielt wird,
    ändern sich Ersatzbank und Absagen weiter.
    """

    assert refresh_interval(_schedule(-30)) == REFRESH_SECONDS_SOON


# --------------------------------------------------
# Meldet der Terminabruf die Änderung - und nur die?
# --------------------------------------------------


class _Response:

    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


#
# Fest und nicht `now() + 2 Tage`: der Bot schickt einen festen
# Zeitpunkt, und zwei Aufrufe dürfen sich nicht um Mikrosekunden
# unterscheiden - sonst sähe jeder Abruf wie ein neuer Termin aus.
#

STARTS_AT = "2099-03-04T19:00:00+01:00"


def _payload(active: int, status: str = "open") -> dict:

    return {
        "status": "ok",
        "title": "Siege of Orgrimmar",
        "raid_size": 25,
        "signup_status": status,
        "days": [
            {
                "key": "mi",
                "label": "Mittwoch",
                "starts_at": STARTS_AT,
                "signups": {"active": active},
            }
        ],
    }


def _sync(monkeypatch, tmp_path, answers):
    """
    Ein `RaidScheduleSync` mit verknüpftem Konto, eigenem
    Zwischenspeicher-Verzeichnis und einer festen Folge von Antworten.
    """

    from core import raid_schedule_sync as module

    monkeypatch.setattr(
        module.Paths,
        "cache",
        staticmethod(lambda: tmp_path),
    )

    monkeypatch.setattr(
        module.DiscordAccountStore,
        "load",
        lambda self: {"companion_token": "t"},
    )

    calls = []

    def _get(url, **kwargs):
        calls.append(url)
        return answers[min(len(calls) - 1, len(answers) - 1)]

    monkeypatch.setattr(module.httpx, "get", _get)

    manager = types.SimpleNamespace(logger=_Logger())

    sync = module.RaidScheduleSync(manager)

    return sync, calls


def test_der_erste_abruf_meldet_eine_aenderung(monkeypatch, tmp_path):

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21))],
    )

    assert sync.process() is True


def test_ein_gleicher_stand_meldet_keine_aenderung(monkeypatch, tmp_path):
    """
    Sonst zeichnete die Oberfläche sich neu, ohne dass sich etwas
    geändert hat - und `_announce_updates()` liefe erneut durch.
    """

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21))],
    )

    assert sync.process() is True

    sync.invalidate()

    assert sync.process() is False


def test_eine_neue_zusage_meldet_eine_aenderung(monkeypatch, tmp_path):

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21)), _Response(_payload(22))],
    )

    assert sync.process() is True

    sync.invalidate()

    assert sync.process() is True


def test_eine_geschlossene_anmeldung_meldet_eine_aenderung(
    monkeypatch,
    tmp_path,
):
    """
    `signup_status` stand nicht im alten Vergleich (`known`/`days`/
    `title`) - dass die Anmeldung geschlossen wurde, blieb damit
    unsichtbar, obwohl die Karte es anzeigt.
    """

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [
            _Response(_payload(21)),
            _Response(_payload(21, status="locked")),
        ],
    )

    assert sync.process() is True

    sync.invalidate()

    assert sync.process() is True


def test_der_takt_haelt_einen_zweiten_abruf_zurueck(monkeypatch, tmp_path):

    sync, calls = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21))],
    )

    sync.process()

    assert sync.process() is False

    assert len(calls) == 1


def test_ein_nicht_erreichbarer_bot_meldet_nichts(monkeypatch, tmp_path):
    """
    Und löscht nichts: der zuletzt bekannte Termin bleibt stehen.
    """

    from core import raid_schedule_sync as module

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21))],
    )

    assert sync.process() is True

    before = sync.schedule

    def _boom(url, **kwargs):
        raise OSError("kein Netz")

    monkeypatch.setattr(module.httpx, "get", _boom)

    sync.invalidate()

    assert sync.process() is False

    assert sync.schedule == before


def test_der_logeintrag_haengt_am_termin_nicht_an_den_zusagen(
    monkeypatch,
    tmp_path,
):
    """
    Am Raidtag wird jede Minute gefragt. Eine Zeile "Raidtermin
    übernommen" je Zu- oder Absage machte aus dem Protokoll Lärm.
    """

    sync, _ = _sync(
        monkeypatch,
        tmp_path,
        [_Response(_payload(21)), _Response(_payload(22))],
    )

    sync.process()

    sync.manager.logger.lines.clear()

    sync.invalidate()

    assert sync.process() is True

    assert sync.manager.logger.lines == []


# --------------------------------------------------
# Die Update-Wache
# --------------------------------------------------


class _Github:

    def __init__(self):
        self.invalidated = 0

    def invalidate_cache(self):
        self.invalidated += 1


def _watch(state):

    from core.update_watch import UpdateWatch

    #
    # `quiet` wird mitgeschrieben statt ignoriert: dass die Wache
    # leise prüft, ist eine Zusage und keine Nebensache (siehe
    # test_die_wache_prueft_leise).
    #

    quiet = []

    manager = types.SimpleNamespace(
        state=state,
        logger=_Logger(),
        github=_Github(),
        companion_updater=types.SimpleNamespace(
            github=_Github(),
            check_for_update=lambda quiet=False: quiet_note(quiet),
        ),
        detect_addon=lambda: None,
        check_github=lambda quiet=False: quiet_note(quiet),
    )

    def quiet_note(value):
        quiet.append(value)

    manager.quiet = quiet

    return UpdateWatch(manager), manager


def _state(**fields):

    base = dict(
        addon_version="1.0.0",
        github_version="1.0.0",
        update_available=False,
        companion_latest_version="2.3.3",
        companion_update_available=False,
    )

    base.update(fields)

    return types.SimpleNamespace(**base)


def test_die_wache_meldet_ein_neu_gefundenes_update():

    state = _state()

    watch, manager = _watch(state)

    def _found(quiet=False):
        state.github_version = "1.1.0"
        state.update_available = True

    manager.check_github = _found

    assert watch.process() is True


def test_die_wache_meldet_nichts_wenn_sich_nichts_geaendert_hat():
    """
    Sonst liefe bei jeder Prüfung die ganze Anzeige neu.
    """

    watch, _ = _watch(_state())

    assert watch.process() is False


def test_die_wache_verwirft_beide_zwischenspeicher():
    """
    `GitHubUpdater` hält seine Antwort 15 Minuten - bei gleich langem
    Takt käme sonst regelmässig die gespeicherte Antwort zurück, und
    die Prüfung wäre eine, die nie etwas Neues erfahren kann.
    """

    watch, manager = _watch(_state())

    watch.process()

    assert manager.github.invalidated == 1

    assert manager.companion_updater.github.invalidated == 1


def test_die_wache_prueft_leise():
    """
    Alle fünfzehn Minuten "ist aktuell" ins Protokoll zu schreiben,
    machte aus der Protokollseite eine Liste von Nichtereignissen -
    und ein unerreichbares GitHub ist im Hintergrund der Normalfall
    eines Rechners, der gerade offline ist, keine Störung.
    """

    watch, manager = _watch(_state())

    watch.process()

    assert manager.quiet == [True, True]


def test_die_wache_haelt_ihren_takt_ein():

    watch, manager = _watch(_state())

    watch.process()

    assert watch.process() is False

    assert manager.github.invalidated == 1


def test_note_checked_verhindert_die_doppelte_pruefung():
    """
    `full_refresh()` fragt beim Start dieselben beiden Endpunkte ab -
    ohne diesen Vermerk zöge die Wache fünf Sekunden später ein
    zweites Mal los.
    """

    watch, manager = _watch(_state())

    watch.note_checked()

    assert watch.process() is False

    assert manager.github.invalidated == 0


def test_invalidate_gibt_die_naechste_pruefung_frei():

    watch, manager = _watch(_state())

    watch.note_checked()

    watch.invalidate()

    watch.process()

    assert manager.github.invalidated == 1


# --------------------------------------------------
# Wird daraus genau ein state_changed?
# --------------------------------------------------


class _Signal:

    def __init__(self):
        self.emitted = 0

    def emit(self):
        self.emitted += 1


def _worker(schedule_changed: bool, update_changed: bool,
            storage_changed: bool = False):
    """
    Ruft den echten `_run_sync_worker()` auf einem Platzhalter auf.

    Ohne `CompanionManager()` selbst zu bauen: der zieht Konfiguration,
    Protokoll, Inbox und den RaidDataService hoch, und geprüft werden
    soll allein die Verdrahtung von "hat sich etwas geändert" auf
    `state_changed`.
    """

    pytest.importorskip("PySide6")

    import threading

    from core.companion_manager import CompanionManager

    nothing = types.SimpleNamespace(process=lambda: None)

    fake = types.SimpleNamespace(
        logger=_Logger(),
        config=types.SimpleNamespace(data={}),
        sync=nothing,
        access_profile_sync=nothing,
        discord_roster_sync=nothing,
        last_pull_sync=nothing,
        weakaura_guild_sync=nothing,
        weakaura_sync=nothing,
        addon_analysis_sync=nothing,
        addon_inbox=types.SimpleNamespace(reassert=lambda: None),
        update_watch=types.SimpleNamespace(
            process=lambda: update_changed
        ),
        raid_schedule_sync=types.SimpleNamespace(
            process=lambda: schedule_changed
        ),
        storage_watch=types.SimpleNamespace(
            process=lambda: storage_changed
        ),
        state_changed=_Signal(),
        _sync_lock=threading.Lock(),
        _sync_busy=True,
    )

    CompanionManager._run_sync_worker(fake)

    return fake


def test_ein_durchgang_ohne_aenderung_meldet_nichts():

    fake = _worker(False, False)

    assert fake.state_changed.emitted == 0

    assert fake._sync_busy is False


def test_ein_neuer_anmeldestand_zieht_die_anzeige_nach():

    assert _worker(True, False).state_changed.emitted == 1


def test_ein_gefundenes_update_zieht_die_anzeige_nach():

    assert _worker(False, True).state_changed.emitted == 1


def test_zwei_aenderungen_ergeben_trotzdem_nur_eine_meldung():
    """
    `state_changed` zeichnet die sichtbare Seite - zweimal
    hintereinander wäre die doppelte Arbeit für dasselbe Bild.
    """

    assert _worker(True, True).state_changed.emitted == 1


def test_volle_ordner_ziehen_die_anzeige_ebenfalls_nach():
    """
    Die Meldung "hier sammelt sich etwas an" hängt an derselben
    Verdrahtung wie ein wartendes Update - also muss auch sie einen
    Durchgang als "es hat sich etwas geändert" melden können.
    """

    assert _worker(False, False, True).state_changed.emitted == 1
