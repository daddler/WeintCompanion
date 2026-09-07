"""
Der Archivbrowser entscheidet nichts über einen Kampf - er entscheidet,
welche Zeilen dastehen und wie sie heissen. Genau das wird hier
geprüft, ohne Fenster: die Gruppierung, die Suche, der beste Versuch
und die Zurückhaltung bei fehlenden Angaben.
"""

import pytest

from analyzer.providers.warcraftlogs_payload import (
    build_fight_list,
    build_report_list,
)

from core import archive_index as ai


def _fights(*rows):

    return build_fight_list({"fights": list(rows)})


def _fight(**overrides):

    row = {
        "id": 1,
        "encounter_id": 1623,
        "name": "Garrosh Höllschrei",
        "difficulty_id": 5,
        "kill": False,
        "boss_percentage": 42.0,
        "duration": 300.0,
        "start": "2026-09-05T19:47:03Z",
        "size": 25,
        "pull_number": 1,
    }
    row.update(overrides)
    return row


# --------------------------------------------------
# Gruppierung
# --------------------------------------------------


def test_pulls_are_grouped_by_boss_in_the_order_of_the_evening():
    """
    Nicht alphabetisch: ein Bericht erzählt einen Abend, und wer den
    letzten Boss sucht, scrollt nach unten.
    """

    fights = _fights(
        _fight(id=1, encounter_id=1621, name="Malkorok"),
        _fight(id=2, encounter_id=1623, name="Garrosh"),
        _fight(id=3, encounter_id=1621, name="Malkorok", pull_number=2),
    )

    groups = ai.group_fights(fights)

    assert [group.name for group in groups] == ["Malkorok", "Garrosh"]
    assert len(groups[0].fights) == 2


def test_only_kills_drops_the_boss_instead_of_leaving_an_empty_heading():

    fights = _fights(
        _fight(id=1, encounter_id=1621, name="Malkorok", kill=True, boss_percentage=0),
        _fight(id=2, encounter_id=1623, name="Garrosh"),
    )

    groups = ai.group_fights(fights, kills_only=True)

    assert [group.name for group in groups] == ["Malkorok"]


def test_a_group_says_how_many_tries_and_how_it_ended():

    fights = _fights(
        _fight(id=1, boss_percentage=42.0),
        _fight(id=2, boss_percentage=4.0, pull_number=2),
    )

    assert ai.group_fights(fights)[0].summary == "2 Versuche · bester Versuch 4 %"


def test_a_killed_boss_says_kill_rather_than_a_percentage():

    fights = _fights(
        _fight(id=1, boss_percentage=42.0),
        _fight(id=2, kill=True, boss_percentage=0.0, pull_number=2),
    )

    group = ai.group_fights(fights)[0]

    assert group.killed
    assert group.summary == "2 Versuche · Kill"


def test_one_try_is_singular():

    assert ai.group_fights(_fights(_fight()))[0].summary.startswith("1 Versuch ·")


# --------------------------------------------------
# Bester Versuch
# --------------------------------------------------


def test_a_kill_beats_every_wipe_however_close():

    fights = _fights(
        _fight(id=1, boss_percentage=0.4),
        _fight(id=2, kill=True, boss_percentage=0.0, pull_number=2),
    )

    assert ai.best_try(fights).fight_id == 2


def test_among_wipes_the_lowest_boss_share_wins():

    fights = _fights(
        _fight(id=1, boss_percentage=42.0),
        _fight(id=2, boss_percentage=4.0, pull_number=2),
        _fight(id=3, boss_percentage=18.0, pull_number=3),
    )

    assert ai.best_try(fights).fight_id == 2


def test_at_the_same_share_the_longer_fight_wins():
    """
    Gleicher Anteil, längerer Kampf: dort ist mehr passiert.
    """

    fights = _fights(
        _fight(id=1, boss_percentage=12.0, duration=200.0),
        _fight(id=2, boss_percentage=12.0, duration=400.0, pull_number=2),
    )

    assert ai.best_try(fights).fight_id == 2


def test_no_fights_means_no_best_try_rather_than_a_placeholder():

    assert ai.best_try(()) is None


# --------------------------------------------------
# Suche
# --------------------------------------------------


def test_every_word_has_to_occur_but_not_side_by_side():
    """
    "garrosh kill" findet den Kill auf Garrosh, obwohl die beiden
    Wörter auf der Zeile nicht nebeneinander stehen.
    """

    fights = _fights(
        _fight(id=1, name="Garrosh", kill=True, boss_percentage=0.0),
        _fight(id=2, encounter_id=1621, name="Malkorok", kill=True, boss_percentage=0.0),
        _fight(id=3, encounter_id=1623, name="Garrosh", pull_number=2),
    )

    found = ai.group_fights(fights, "garrosh kill")

    assert [group.name for group in found] == ["Garrosh"]
    assert [fight.fight_id for fight in found[0].fights] == [1]


def test_the_search_ignores_umlauts_in_both_directions():

    fights = _fights(_fight(name="Sha des Zorns"))

    assert ai.group_fights(fights, "sha")
    assert ai.group_fights(_fights(_fight(name="Kriegsschmied Blackfuse")), "blackfuse")

    umlaut = _fights(_fight(name="Garrosh Höllschrei"))

    assert ai.group_fights(umlaut, "hollschrei")
    assert ai.group_fights(umlaut, "höllschrei")


def test_an_empty_search_keeps_everything():

    fights = _fights(_fight(id=1), _fight(id=2, encounter_id=1621, name="Malkorok"))

    assert ai.fight_count(ai.group_fights(fights, "   ")) == 2


def test_the_search_reaches_the_time_of_day_that_is_on_the_row():
    """
    Gesucht wird über das, was auf der Zeile steht - eine Suche über
    unsichtbare Felder liefert Treffer, die niemand erklären kann.
    """

    fights = _fights(
        _fight(id=1, start="2026-09-05T19:47:03Z"),
        _fight(id=2, start="2026-09-05T21:12:00Z", pull_number=2),
    )

    hits = [
        fight.fight_id
        for group in ai.group_fights(fights, fights[1].time_label)
        for fight in group.fights
    ]

    assert hits == [2]


# --------------------------------------------------
# Berichte
# --------------------------------------------------


def test_reports_are_grouped_by_evening_with_the_weekday_in_front():

    reports = build_report_list({
        "reports": [
            {"code": "a", "title": "Mittwoch", "start": "2026-09-02T18:30:00Z"},
            {"code": "b", "title": "Mittwoch 2", "start": "2026-09-02T21:30:00Z"},
            {"code": "c", "title": "Donnerstag", "start": "2026-09-03T18:30:00Z"},
        ]
    })

    days = ai.group_reports_by_day(reports)

    assert len(days) == 2
    assert days[0].label.startswith("Mittwoch, ")
    assert len(days[0].reports) == 2
    assert days[1].label.startswith("Donnerstag, ")


def test_a_report_without_a_date_lands_at_the_end_and_says_so():
    """
    Ein geratener Tag wäre von einem echten nicht zu unterscheiden -
    dieselbe Linie wie `stars == 0`.
    """

    reports = build_report_list({
        "reports": [
            {"code": "a", "title": "Ohne"},
            {"code": "b", "title": "Mit", "start": "2026-09-02T18:30:00Z"},
        ]
    })

    days = ai.group_reports_by_day(reports)

    assert [day.label for day in days][-1] == "Ohne Datum"


def test_the_report_code_stays_findable_because_discord_links_carry_it():

    reports = build_report_list({
        "reports": [{"code": "aBcDeF12", "title": "Mittwoch", "zone": "Belagerung"}]
    })

    assert ai.group_reports_by_day(reports, "abcdef12")
    assert "aBcDeF12" in ai.report_subtitle(reports[0])


def test_the_zone_is_not_repeated_when_it_is_already_the_title():

    reports = build_report_list({
        "reports": [{"code": "x", "title": "Belagerung", "zone": "Belagerung"}]
    })

    assert ai.report_subtitle(reports[0]) == "x"


# --------------------------------------------------
# Uhrzeit eines Pulls
# --------------------------------------------------


def test_a_pull_without_a_time_claims_none_instead_of_midnight():
    """
    "00:00" wäre von einer echten Uhrzeit nicht zu unterscheiden, und
    ein Pull um Mitternacht ist an einem Raidabend nicht abwegig.
    """

    assert _fights(_fight(start=None))[0].time_label == ""
    assert _fights(_fight(start="unlesbar"))[0].time_label == ""


def test_a_pull_with_a_time_shows_it_in_the_local_zone():

    assert _fights(_fight(start="2026-09-05T19:47:03Z"))[0].time_label.count(":") == 1


# --------------------------------------------------
# Was ist geladen?
# --------------------------------------------------


class _State:

    def __init__(self, reports=(), fights=(), selected_report="", selected_fight=None):

        self.reports = reports
        self.fights = fights
        self.selected_report = selected_report
        self.selected_fight = selected_fight


def test_the_source_line_names_the_evening_and_the_pull():

    reports = build_report_list({
        "reports": [{"code": "a", "title": "Mittwoch", "start": "2026-09-02T18:30:00Z"}]
    })

    fights = _fights(_fight(id=7, name="Garrosh", pull_number=14))

    text = ai.selection_text(
        _State(reports, fights, selected_report="a", selected_fight=7)
    )

    assert text.startswith("Mittwoch, ")
    assert "Pull 14 · Garrosh" in text


def test_without_a_selection_the_source_line_stays_empty():
    """
    Der Aufrufer setzt dann seinen eigenen Hinweis - ob das ein Mangel
    ist, hängt vom Modus ab.
    """

    assert ai.selection_text(_State()) == ""


def test_a_chosen_report_without_a_pull_names_only_the_evening():

    reports = build_report_list({
        "reports": [{"code": "a", "title": "Mittwoch", "start": "2026-09-02T18:30:00Z"}]
    })

    text = ai.selection_text(_State(reports, selected_report="a"))

    assert text.startswith("Mittwoch, ")
    assert "Pull" not in text
