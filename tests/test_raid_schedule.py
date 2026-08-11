"""
Der Raidtermin der Übersicht - Einlesen, Restzeit, Beschriftung.

Ohne Qt und ohne Netz, wie der Rest von `core/raid_schedule.py`. Die
Uhr wird übergeben; ein Test, der die echte liest, ist am Mittwoch
abend ein anderer als am Montag.
"""

from datetime import datetime

from core.raid_schedule import (
    countdown_text,
    day_text,
    parse_schedule,
    signup_text,
)


def _moment(text: str) -> datetime:

    return datetime.fromisoformat(text)


PAYLOAD = {
    "status": "ok",
    "raid_id": 7,
    "title": "Siege of Orgrimmar",
    "raid_type": "standard",
    "signup_status": "open",
    "raid_size": 25,
    "timezone": "Europe/Berlin",
    "days": [
        {
            "key": "wednesday",
            "label": "Mittwoch",
            "date": "2026-08-12",
            "time": "20:00",
            "starts_at": "2026-08-12T20:00:00+02:00",
            "signups": {
                "active": 18,
                "tentative": 2,
                "bench": 1,
                "absent": 3,
            },
        },
        {
            "key": "thursday",
            "label": "Donnerstag",
            "date": "2026-08-13",
            "time": "20:00",
            "starts_at": "2026-08-13T20:00:00+02:00",
            "signups": {
                "active": 20,
                "tentative": 0,
                "bench": 0,
                "absent": 2,
            },
        },
    ],
}


def test_idle_is_not_a_schedule():
    """
    "Kein Raid" muss von "Raid, aber noch nichts geladen" nicht
    unterscheidbar sein - beide Male ist nichts bekannt, und die
    Übersicht sagt genau das.
    """

    schedule = parse_schedule(
        {"status": "idle", "detail": "Kein aktiver Raid."}
    )

    assert not schedule.known
    assert schedule.next_day() is None
    assert countdown_text(None) == "KEIN TERMIN BEKANNT"


def test_garbage_does_not_raise():

    for value in (None, [], "nein", {}, {"status": "ok"}):
        parse_schedule(value)


def test_the_next_day_is_the_first_one_still_ahead():

    schedule = parse_schedule(PAYLOAD)

    assert schedule.known
    assert schedule.title == "Siege of Orgrimmar"
    assert schedule.raid_size == 25

    day = schedule.next_day(_moment("2026-08-11T18:30:00+02:00"))

    assert day.key == "wednesday"

    #
    # Nach dem Mittwoch zeigt die Übersicht den Donnerstag, nicht den
    # Mittwoch der nächsten Woche - der steht so gar nicht in der
    # Antwort, und genau deshalb sortiert `next_day()` selbst.
    #

    later = schedule.next_day(_moment("2026-08-13T09:00:00+02:00"))

    assert later.key == "thursday"


def test_a_running_raid_is_the_next_one_and_says_so():

    schedule = parse_schedule(PAYLOAD)

    now = _moment("2026-08-12T21:00:00+02:00")

    day = schedule.next_day(now)

    assert day.key == "wednesday"
    assert day.is_running(now)
    assert countdown_text(day, now) == "RAID LÄUFT"


def test_every_day_behind_us_means_no_termin():
    """
    Alle Termine vorbei: der Chip fällt auf "kein Termin bekannt"
    zurück, statt eine negative Restzeit anzuzeigen.
    """

    schedule = parse_schedule(PAYLOAD)

    now = _moment("2026-08-20T12:00:00+02:00")

    assert schedule.next_day(now) is None
    assert countdown_text(schedule.next_day(now), now) == (
        "KEIN TERMIN BEKANNT"
    )


def test_countdown_is_coarse_by_design():

    schedule = parse_schedule(PAYLOAD)

    day = schedule.days[0]

    cases = {
        "2026-08-12T19:45:00+02:00": "IN 15 MIN",
        "2026-08-12T17:00:00+02:00": "IN 3 STD",
        "2026-08-12T16:30:00+02:00": "IN 3 STD 30 MIN",
        "2026-08-11T20:00:00+02:00": "IN 1 T",
        "2026-08-10T18:00:00+02:00": "IN 2 T 2 STD",
    }

    for stamp, expected in cases.items():
        assert countdown_text(day, _moment(stamp)) == expected


def test_labels_read_like_a_sentence():

    schedule = parse_schedule(PAYLOAD)

    day = schedule.days[0]

    assert day_text(day) == "Mittwoch, 12.08. um 20:00 Uhr"

    assert signup_text(day, 25) == (
        "18 von 25 zugesagt · 2 vielleicht · 1 Ersatzbank"
    )

    #
    # Ohne bekannte Raidgröße kein "von 25" - eine erfundene
    # Obergrenze ließe die Zusagen knapp oder üppig aussehen.
    #

    assert signup_text(day, 0) == (
        "18 zugesagt · 2 vielleicht · 1 Ersatzbank"
    )

    assert signup_text(schedule.days[1], 25) == "20 von 25 zugesagt"


def test_a_day_without_a_timestamp_is_not_a_day():
    """
    Ein Termin ohne lesbaren Zeitpunkt zählt nicht als der nächste -
    sonst stünde in der Übersicht ein Titel ohne Datum, und der Chip
    rechnete gegen nichts.
    """

    schedule = parse_schedule({
        "status": "ok",
        "title": "Ordos",
        "raid_size": 10,
        "days": [
            {
                "key": "special",
                "label": "Samstag",
                "starts_at": "",
                "signups": {"active": 4},
            }
        ],
    })

    assert schedule.known
    assert schedule.next_day() is None
    assert schedule.days[0].active == 4


# --------------------------------------------------
# Wo die Anmeldung steht
# --------------------------------------------------


def test_the_signup_location_is_read_as_strings():
    """
    Der `discord`-Block nennt Gilde, Kanal und Nachricht der
    Anmeldung. Jede Kennung als Zeichenkette - aus `1.23e+18` wird
    nie wieder ein Link.
    """

    schedule = parse_schedule({
        **PAYLOAD,
        "discord": {
            "guild_id": 1311060525555257364,
            "channel_id": "1311325324008751225",
            "message_id": "  1400000000000000000  ",
        },
    })

    assert schedule.signup == {
        "guild_id": "1311060525555257364",
        "channel_id": "1311325324008751225",
        "message_id": "1400000000000000000",
    }


def test_an_older_bot_reports_no_location():
    """
    Kein Block, kein Fundort - und nichts Zusammengesetztes, das wie
    eine Adresse aussieht. Die Übersicht hat dafür ihren eigenen
    Rückfall.
    """

    assert parse_schedule(PAYLOAD).signup == {}

    for broken in ("", [], {"channel_id": ""}, {"channel_id": None}):

        assert parse_schedule({**PAYLOAD, "discord": broken}).signup == {}


def test_a_signup_that_is_gone_is_not_a_raid():
    """
    Der Bot antwortet "idle", sobald die Anmeldenachricht im Kanal
    fehlt - bis 2.0.2 nannte die Übersicht einen längst gelöschten
    Testraid nach jedem Neustart wieder als nächsten Termin.
    """

    schedule = parse_schedule({
        "status": "idle",
        "detail": "Zu diesem Raid gibt es im Anmelde-Kanal keine Nachricht mehr.",
    })

    assert not schedule.known

    assert schedule.next_day() is None

    assert "Anmelde-Kanal" in schedule.detail
