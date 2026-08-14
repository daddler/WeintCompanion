"""
Der letzte Pull der Übersicht.

Ohne Qt und ohne Netz, wie `core/last_pull.py` selbst. Der Fehler,
den diese Datei festhält, war kein Absturz und keine Fehlermeldung:
die Karte sagte "Noch kein Pull", weil sie in einer Liste nachsah, die
sich nur während einer laufenden Sitzung füllt - am Tag nach dem Raid
also immer.
"""

from datetime import datetime, time, timedelta

from core.last_pull import (
    WEEKDAYS,
    from_fights,
    from_history,
    parse_last_pull,
    result_text,
    source_text,
    when_text,
)


CACHE = {
    "report": {
        "code": "aBcDeF12",
        "title": "Mittwochsraid",
        "zone": "Schlacht um Orgrimmar",
        "start": "2026-08-13T19:05:00Z",
    },
    "fights": [
        {
            "id": 1,
            "encounter_id": 1602,
            "name": "Immerseus",
            "kill": True,
            "boss_percentage": 0.0,
            "duration": 320.0,
            "pull_number": 1,
            "difficulty_name": "Heroisch",
        },
        {
            "id": 2,
            "encounter_id": 1603,
            "name": "Der Fallenmeister",
            "kill": False,
            "boss_percentage": 62.0,
            "duration": 140.0,
            "pull_number": 1,
            "difficulty_name": "Heroisch",
        },
        {
            "id": 3,
            "encounter_id": 1603,
            "name": "Der Fallenmeister",
            "kill": False,
            "boss_percentage": 12.0,
            "duration": 372.0,
            "pull_number": 2,
            "difficulty_name": "Heroisch",
        },
    ],
}


class _Summary:
    """
    So viel von `PullSummary`, wie die Übersicht liest - und mit
    genau dessen Feldnamen. Der zweite Teil des Fehlers war, dass die
    Karte `boss` und `boss_percent` las, die es dort nie gab.
    """

    def __init__(self, name, percent, pull=1, duration=300.0):

        self.encounter_name = name
        self.boss_health_percent = percent
        self.pull_number = pull
        self.duration = duration

    @property
    def killed(self):
        return self.boss_health_percent <= 1.0


# --------------------------------------------------
# Aus dem Archiv
# --------------------------------------------------


def test_nothing_at_all_stays_nothing():

    for value in (None, {}, [], "nein", {"fights": []}):

        pull = parse_last_pull(value)

        assert not pull.known

        assert result_text(pull) == ""

        assert when_text(pull) == ""


def test_the_last_entry_is_the_last_pull():
    """
    Und nicht der mit der höchsten Pullnummer: die zählt je Boss, und
    wer am Abend von Boss zu Boss zieht, bekäme sonst den Kampf mit
    den meisten Versuchen statt den zuletzt gespielten.
    """

    pull = parse_last_pull(CACHE)

    assert pull.known

    assert pull.boss == "Der Fallenmeister"

    assert pull.pull_number == 2

    assert not pull.kill

    assert pull.report_code == "aBcDeF12"


def test_the_curve_holds_only_the_same_boss():
    """
    Pulls verschiedener Bosse in eine Linie zu legen ergäbe eine
    Kurve, die nichts verbindet. Gezeichnet wird der geschaffte
    Anteil, damit "es wird besser" nach oben zeigt.
    """

    pull = parse_last_pull(CACHE)

    assert pull.trend == (38.0, 88.0)


def test_the_difficulty_survives_the_cache():
    """
    Der Bot schickt eine Zahl, `build_fight_list()` übersetzt sie in
    einen Namen, und zurückrechnen ließe sich das nicht. Der Name
    reist deshalb mit - über die Fight-ID zugeordnet, nicht über die
    Position, weil Trash aus der Liste fällt.
    """

    assert parse_last_pull(CACHE).difficulty == "Heroisch"

    assert result_text(parse_last_pull(CACHE)) == (
        "Heroisch · Wipe bei 12 % · 06:12 · Pull 2"
    )


def test_trash_is_not_a_pull():
    """
    `encounter_id == 0` ist Trash. Wäre sie der letzte Eintrag, stünde
    in der Übersicht der Name irgendeines Mobs als "dein letzter
    Pull".
    """

    data = {
        "report": CACHE["report"],
        "fights": CACHE["fights"] + [
            {
                "id": 9,
                "encounter_id": 0,
                "name": "Kor'kron-Wache",
                "duration": 40.0,
            }
        ],
    }

    assert parse_last_pull(data).boss == "Der Fallenmeister"


def test_a_kill_reads_as_a_kill_and_a_wipe_names_its_percent():
    """
    Kein nacktes "Wipe": der Unterschied zwischen 62 % und 12 % ist
    der ganze Abend.
    """

    assert not from_fights(()).known

    kill = parse_last_pull({
        "report": CACHE["report"],
        "fights": CACHE["fights"][:1],
    })

    assert result_text(kill) == "Heroisch · Kill · 05:20 · Pull 1"


# --------------------------------------------------
# Aus der laufenden Sitzung
# --------------------------------------------------


def test_the_session_reads_the_fields_that_actually_exist():
    """
    `PullSummary` heißt `encounter_name`/`boss_health_percent`. Die
    Karte las `boss`/`boss_percent` per `getattr` mit Rückfall, fand
    beides nie und zeigte selbst mit gefüllter Historie "Kampf" ohne
    Kurve - ein stiller Fehler, weil ein `getattr` mit Standardwert
    wie eine erlaubte Lücke aussieht.
    """

    history = [
        _Summary("Der Fallenmeister", 62.0, pull=1),
        _Summary("Der Fallenmeister", 12.0, pull=2),
    ]

    pull = from_history(history)

    assert pull.known

    assert pull.live

    assert pull.boss == "Der Fallenmeister"

    assert pull.pull_number == 2

    assert pull.trend == (38.0, 88.0)

    assert when_text(pull) == "DIESE SITZUNG"

    assert source_text(pull) == ""


def test_an_empty_session_is_not_a_pull():

    assert not from_history([]).known

    assert not from_history(None).known


# --------------------------------------------------
# Beschriftung
# --------------------------------------------------


def test_the_day_is_named_relative_to_today():
    """
    Gerechnet wird gegen den Tag des Berichts, nicht gegen ein
    festes Datum: `"…Z"` wird in die lokale Zeitzone gebracht, und
    ein fest verdrahtetes "13.08." wäre auf einer Maschine in Sydney
    ein anderer Tag - der Test hinge dann an der Uhr des Prüfers.
    """

    pull = parse_last_pull(CACHE)

    day = pull.started.date()

    def at(offset: int, hour: int) -> datetime:

        return datetime.combine(
            day + timedelta(days=offset),
            time(hour, 0),
        )

    assert when_text(pull, at(0, 22)) == "HEUTE"

    assert when_text(pull, at(1, 9)) == "GESTERN"

    assert when_text(pull, at(7, 9)) == (
        f"{WEEKDAYS[day.weekday()]} · {day.strftime('%d.%m.')}"
    )


def test_a_zulu_timestamp_is_a_timestamp():
    """
    WarcraftLogs meldet den Beginn mit `Z`. Vor Python 3.11 versteht
    `fromisoformat()` das nicht - unbehandelt wäre der Bericht ohne
    Datum, und die Karte trüge dauerhaft keine Rubrik.
    """

    pull = parse_last_pull(CACHE)

    assert pull.started is not None

    assert pull.started.tzinfo is not None


def test_a_report_without_a_start_gets_no_label():
    """
    Kein Datum heißt keine Rubrik - ein "GESTERN" auf Verdacht wäre
    von einem gemeldeten nicht zu unterscheiden.
    """

    data = {
        "report": {"code": "x", "title": "Ohne Datum"},
        "fights": CACHE["fights"],
    }

    pull = parse_last_pull(data)

    assert pull.known

    assert when_text(pull) == ""

    assert source_text(pull) == "Ohne Datum"
