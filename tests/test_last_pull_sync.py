"""
Der Abruf des letzten Pulls beim Bot.

Ohne Netz: der Archiv-Client wird als Doppel übergeben (`LastPullSync`
nimmt ihn dafür entgegen). Geprüft wird das Verhalten, das über die
Anzeige entscheidet - was passiert, wenn der Bot **nicht** antwortet,
wenn er leer antwortet und wenn er ablehnt. Alle drei sahen in der
Oberfläche bisher gleich aus, nämlich wie "kein Pull".
"""

import pytest

#
# Der Archiv-Client selbst braucht `httpx`, auch wenn hier keine
# einzige Anfrage hinausgeht - dieselbe Regel wie in
# `test_raid_data_service.py`: fehlt die Abhängigkeit, überspringt
# sich die Datei, statt zu scheitern.
#

pytest.importorskip("httpx")

from analyzer.providers.warcraftlogs_payload import (  # noqa: E402
    FightSummary,
    ReportSummary,
)
from core.last_pull_sync import LastPullSync  # noqa: E402
from core.paths import Paths  # noqa: E402
from core.warcraftlogs_archive_client import (  # noqa: E402
    FightsFetchResult,
    ReportsFetchResult,
)


class _Logger:

    def __init__(self):
        self.lines = []

    def info(self, text=""):
        self.lines.append(("info", text))

    def warning(self, text=""):
        self.lines.append(("warning", text))

    def error(self, text=""):
        self.lines.append(("error", text))

    def success(self, text=""):
        self.lines.append(("success", text))


class _Manager:

    def __init__(self):
        self.logger = _Logger()


class _Client:
    """
    Ein Archiv-Client, der zählt, wie oft er gefragt wurde - die
    Rückfallregeln hängen genau daran.
    """

    def __init__(self, reports=None, fights=None, linked=True):

        self._reports = reports if reports is not None else ReportsFetchResult()

        self._fights = fights or {}

        self._linked = linked

        self.report_calls = 0

        self.fight_calls = []

    def is_linked(self):
        return self._linked

    def fetch_reports(self):

        self.report_calls += 1

        return self._reports

    def fetch_fights(self, code):

        self.fight_calls.append(code)

        return self._fights.get(code, FightsFetchResult())


def _report(code, title="Mittwochsraid"):

    return ReportSummary(
        code=code,
        title=title,
        zone="Schlacht um Orgrimmar",
        start="2026-08-13T19:05:00Z",
    )


def _fight(fight_id, name="Der Fallenmeister", percent=12.0, pull=2):

    return FightSummary(
        fight_id=fight_id,
        encounter_name=name,
        encounter_id=1603,
        difficulty="Heroisch",
        kill=False,
        boss_percentage=percent,
        duration=372.0,
        pull_number=pull,
    )


@pytest.fixture(autouse=True)
def _cache(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "cache", staticmethod(lambda: tmp_path))

    return tmp_path


# --------------------------------------------------


def test_the_newest_report_with_a_boss_fight_wins():
    """
    Der neueste Bericht ist fast immer der richtige - besteht er aber
    nur aus Trash (die Fightliste wirft ihn heraus), wird der nächste
    genommen, statt die Karte leer zu lassen.
    """

    client = _Client(
        reports=ReportsFetchResult(
            reports=(_report("neu"), _report("aelter")),
        ),
        fights={
            "neu": FightsFetchResult(fights=()),
            "aelter": FightsFetchResult(fights=(_fight(3),)),
        },
    )

    sync = LastPullSync(_Manager(), client)

    sync.process()

    assert sync.pull.known

    assert sync.pull.boss == "Der Fallenmeister"

    assert sync.pull.report_code == "aelter"

    assert client.fight_calls == ["neu", "aelter"]


def test_the_answer_is_cached_and_survives_a_restart():
    """
    Ohne Zwischenspeicher stünde die Übersicht nach jedem Start
    zwanzig Minuten lang auf "Noch kein Pull" - und offline dauerhaft.
    """

    client = _Client(
        reports=ReportsFetchResult(reports=(_report("abc"),)),
        fights={"abc": FightsFetchResult(fights=(_fight(3),))},
    )

    LastPullSync(_Manager(), client).process()

    #
    # Ein neuer Dienst liest allein die Datei - er fragt nicht.
    #

    fresh = LastPullSync(_Manager(), _Client(linked=False))

    assert fresh.pull.known

    assert fresh.pull.boss == "Der Fallenmeister"

    assert fresh.pull.difficulty == "Heroisch"


def test_a_failure_never_clears_what_is_known():
    """
    Ein kurz nicht erreichbarer Bot macht den letzten Pull nicht
    falsch. Und eine **leere** Berichtsliste auch nicht: sie umfasst
    nur die letzten Wochen, ein Raid, der aus ihr fällt, hat trotzdem
    stattgefunden.
    """

    good = _Client(
        reports=ReportsFetchResult(reports=(_report("abc"),)),
        fights={"abc": FightsFetchResult(fights=(_fight(3),))},
    )

    sync = LastPullSync(_Manager(), good)

    sync.process()

    known = sync.pull

    for broken in (
        ReportsFetchResult(reason="Bot nicht erreichbar: timeout"),
        ReportsFetchResult(reports=()),
    ):

        sync.client = _Client(reports=broken)

        sync.invalidate()

        sync.process()

        assert sync.pull == known


def test_a_denied_archive_is_asked_once_and_not_again():
    """
    Das Archiv setzt eine Rolle im Discord voraus. Wer sie nicht hat,
    bekäme sonst alle zwanzig Minuten dieselbe abschlägige Antwort -
    und im Protokoll eine Zeile dazu.
    """

    client = _Client(
        reports=ReportsFetchResult(
            reason=(
                "Keine Berechtigung für das Log-Archiv - dafür ist "
                "eine Rolle im Discord nötig."
            ),
        ),
    )

    sync = LastPullSync(_Manager(), client)

    sync.process()

    sync._last_fetch = None

    sync.process()

    assert client.report_calls == 1


def test_without_a_linked_account_nothing_is_asked_at_all():

    client = _Client(linked=False)

    sync = LastPullSync(_Manager(), client)

    sync.process()

    assert client.report_calls == 0

    assert not sync.pull.known


def test_the_interval_holds():
    """
    Zwei Abrufe je Durchlauf im Fünf-Sekunden-Takt wären Last für eine
    Auskunft, die sich pro Pull einmal ändert.
    """

    client = _Client(
        reports=ReportsFetchResult(reports=(_report("abc"),)),
        fights={"abc": FightsFetchResult(fights=(_fight(3),))},
    )

    sync = LastPullSync(_Manager(), client)

    for _ in range(5):
        sync.process()

    assert client.report_calls == 1
