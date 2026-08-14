"""
Die Begrüßung im Kopf der Übersicht.

Zwei Dinge, die hier still falsch werden könnten und in der Anzeige
nicht als Fehler zu erkennen wären:

**Die Tagesrechnung.** "Morgen" ist eine Aussage über den Kalender,
nicht über 24 Stunden. Um 23:00 Uhr liegt ein Raid am Folgetag um
20:00 Uhr nur 21 Stunden entfernt - er ist trotzdem *morgen*, und
"Heute um 20:00 Uhr ist Raid" wäre um 23:00 Uhr schlicht falsch.

**Die Zurückhaltung.** Ohne bekannten Termin, ohne bekannten Namen und
für einen Termin, der Wochen entfernt ist, darf nichts erfunden
werden - dieselbe Regel wie überall im Projekt.
"""

from datetime import datetime, timedelta

from core.greeting import (
    daypart,
    days_until,
    greeting,
    headline,
    raid_phrase,
    update_sentence,
)
from core.raid_schedule import RaidDay


def _at(text: str) -> datetime:

    return datetime.fromisoformat(text).astimezone()


def _day(text: str) -> RaidDay:

    return RaidDay(key="wed", label="Mittwoch", starts_at=_at(text))


# --------------------------------------------------
# Tageszeit
# --------------------------------------------------


def test_the_daypart_follows_the_clock():

    assert daypart(_at("2026-08-14T07:30")) == "Guten Morgen"

    assert daypart(_at("2026-08-14T12:00")) == "Guten Tag"

    assert daypart(_at("2026-08-14T20:15")) == "Guten Abend"

    assert daypart(_at("2026-08-14T02:00")) == "Gute Nacht"

    assert daypart(_at("2026-08-14T23:30")) == "Gute Nacht"


def test_the_boundaries_belong_to_the_later_part():
    """
    Um genau 11 Uhr ist der Morgen vorbei, um 18 Uhr der Tag.
    """

    assert daypart(_at("2026-08-14T10:59")) == "Guten Morgen"

    assert daypart(_at("2026-08-14T11:00")) == "Guten Tag"

    assert daypart(_at("2026-08-14T17:59")) == "Guten Tag"

    assert daypart(_at("2026-08-14T18:00")) == "Guten Abend"


def test_without_a_name_there_is_no_comma():
    """
    Ein Komma ohne Anrede dahinter sieht aus wie ein abgeschnittener
    Text - und ein geratener Name wäre schlimmer als keiner.
    """

    assert greeting("", _at("2026-08-14T20:00")) == "Guten Abend"

    assert greeting("   ", _at("2026-08-14T20:00")) == "Guten Abend"

    assert (
        greeting("Krallenwut", _at("2026-08-14T20:00"))
        == "Guten Abend, Krallenwut"
    )


# --------------------------------------------------
# Der nächste Raid
# --------------------------------------------------


def test_days_are_counted_over_midnight_not_in_blocks():
    """
    Der Fall, wegen dem `days_until()` auf Datumsgrenzen rechnet.
    """

    day = _day("2026-08-19T20:00")

    assert days_until(day, _at("2026-08-18T23:00")) == 1

    assert days_until(day, _at("2026-08-19T09:00")) == 0

    assert days_until(day, _at("2026-08-17T06:00")) == 2


def test_the_phrase_names_today_tomorrow_and_the_day_after():

    day = _day("2026-08-19T20:00")

    assert (
        raid_phrase(day, _at("2026-08-19T09:00"))
        == "Heute um 20:00 Uhr ist Raid"
    )

    assert (
        raid_phrase(day, _at("2026-08-18T23:00"))
        == "Morgen um 20:00 Uhr ist Raid"
    )

    assert (
        raid_phrase(day, _at("2026-08-17T10:00"))
        == "Übermorgen um 20:00 Uhr ist Raid"
    )


def test_three_to_six_days_are_counted_in_words():

    day = _day("2026-08-19T20:00")

    assert (
        raid_phrase(day, _at("2026-08-15T10:00"))
        == "Noch vier Tage bis zum nächsten Raid"
    )


def test_a_faraway_or_missing_date_says_nothing():
    """
    Leer heißt "dazu ist nichts zu sagen" - der Aufrufer setzt dann
    seinen eigenen Satz.
    """

    assert raid_phrase(None) == ""

    assert raid_phrase(RaidDay()) == ""

    assert raid_phrase(_day("2026-09-19T20:00"), _at("2026-08-14T10:00")) == ""


def test_a_running_raid_is_named_as_such():

    now = datetime.now().astimezone()

    day = RaidDay(starts_at=now - timedelta(minutes=30))

    assert raid_phrase(day) == "Der Raid läuft gerade"


def test_a_finished_raid_is_not_announced_again():
    """
    Ein Termin, der lange vorbei ist, ist kein "nächster".
    """

    now = datetime.now().astimezone()

    day = RaidDay(starts_at=now - timedelta(hours=12))

    assert raid_phrase(day) == ""


# --------------------------------------------------
# Der Satz im Kopf
# --------------------------------------------------


def test_a_missing_wow_comes_before_everything_else():

    assert (
        headline(_day("2026-08-19T20:00"), wow_found=False)
        == "World of Warcraft wurde noch nicht gefunden."
    )


def test_without_a_date_the_old_sentence_stands():

    assert headline(None) == "Alles bereit für den nächsten Raid."


def test_an_update_is_named_by_component():
    """
    Die beiden Kanäle sind unabhängig - "es gibt ein Update" ließe
    offen, welches gemeint ist.
    """

    assert update_sentence(True, False).startswith("Für das Addon")

    assert update_sentence(False, True).startswith("Für die App")

    assert update_sentence(True, True) == (
        "Für Addon und App gibt es neue Versionen."
    )

    assert update_sentence(False, False) == ""

    assert headline(None, app_update=True) == (
        "Für die App liegt eine neue Version bereit."
    )


def test_the_raid_wins_and_the_update_rides_along():
    """
    Der Termin verdrängt das Update nicht und umgekehrt: die
    Update-Karte direkt darunter nennt es ohnehin beim Namen.

    Die Uhrzeit weicht dafür - der Titel ist 28 px groß, steht auf
    einer Zeile und wird bei 960 px Fensterbreite abgeschnitten.
    """

    day = _day("2026-08-19T20:00")

    assert headline(
        day,
        addon_update=True,
        now=_at("2026-08-18T19:00"),
    ) == "Morgen ist Raid - ein Update wartet."

    assert headline(
        day,
        addon_update=True,
        app_update=True,
        now=_at("2026-08-18T19:00"),
    ) == "Morgen ist Raid - zwei Updates warten."

    assert headline(
        day,
        now=_at("2026-08-18T19:00"),
    ) == "Morgen um 20:00 Uhr ist Raid."


def test_a_faraway_raid_does_not_carry_the_update_along():
    """
    "Noch vier Tage bis zum nächsten Raid - ein Update wartet."
    wäre eine Zeile, die kein Fenster dieser App vollständig zeigt.
    Der Termin gewinnt, das Update steht in der Karte darunter.
    """

    assert headline(
        _day("2026-08-19T20:00"),
        addon_update=True,
        now=_at("2026-08-15T10:00"),
    ) == "Noch vier Tage bis zum nächsten Raid."


def test_the_longest_possible_title_stays_short():
    """
    Eine Obergrenze als Zahl, weil die Zeile sonst schleichend
    wächst: der Titel ist 28 px groß, steht auf einer Zeile und wird
    bei 960 px Fensterbreite (`tokens.WINDOW_MIN`) abgeschnitten statt
    umgebrochen. Messlatte ist der längste Satz, den der Kopf schon
    bis 2.0.7 tragen konnte - was darüber hinausgeht, verschwindet auf
    einem kleinen Fenster am rechten Rand.
    """

    day = _day("2026-08-19T20:00")

    longest = max(
        (
            headline(
                day,
                addon_update=addon,
                app_update=app,
                now=_at(moment),
            )
            for addon in (False, True)
            for app in (False, True)
            for moment in (
                "2026-08-19T09:00",
                "2026-08-18T19:00",
                "2026-08-17T10:00",
                "2026-08-15T10:00",
                "2026-08-01T10:00",
            )
        ),
        key=len,
    )

    assert len(longest) <= len(
        "Für das Addon liegt eine neue Version bereit."
    ), longest
