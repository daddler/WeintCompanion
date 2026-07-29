"""
Der Payload-Mapper ist die Stelle, an der fremde Daten in die
Anwendung eintreten. Zwei Dinge müssen deshalb belegt sein: dass eine
vollständige Antwort korrekt übersetzt wird, und dass eine
unvollständige oder kaputte Antwort trotzdem einen gültigen Snapshot
ergibt statt einer Ausnahme.
"""

import pytest

from analyzer.models import (
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    RaidSnapshot,
)
from analyzer.providers.warcraftlogs_payload import (
    STALE_AFTER,
    build_fight_list,
    build_metrics,
    build_report_list,
    class_name,
    report_label,
    role_name,
    snapshot_from_payload,
)


LABEL = "WarcraftLogs"


def _payload(**overrides):
    """
    Eine vollständige, realistische Antwort des Bots.
    """

    payload = {

        "status": "ok",

        "report": {
            "code": "aBcDeF12",
            "title": "Mittwochsraid",
            "zone": "Thron des Donners",
        },

        "fight": {
            "id": 12,
            "encounter_id": 1640,
            "name": "Horridon",
            "difficulty_id": 6,
            "raid_size": 25,
            "duration": 180.0,
            "in_progress": True,
            "kill": False,
            "boss_percentage": 42.5,
            "pull_number": 7,
            "battle_res_charges": 2,
            "battle_res_max": 3,
            "heroism_used": True,
            "heroism_remaining": 12.0,
        },

        "players": [
            {
                "name": "Bramborn",
                "class": "Warrior",
                "spec": "Protection",
                "role": "tank",
                "damage_total": 3600000.0,
                "damage_taken": 8200000.0,
                "health_percent": 71.0,
            },
            {
                "name": "Pyrothal",
                "class": "Mage",
                "spec": "Fire",
                "role": "dps",
                "damage_total": 24000000.0,
            },
            {
                "name": "Seuchenherz",
                "class": "DeathKnight",
                "spec": "Unholy",
                "role": "dps",
                "damage_total": 18000000.0,
            },
            {
                "name": "Elvenne",
                "class": "Druid",
                "spec": "Restoration",
                "role": "healer",
                "healing_total": 12000000.0,
                "damage_total": 900000.0,
            },
        ],

        "deaths": [
            {
                "name": "Seuchenherz",
                "at": 63.0,
                "ability": "Verheerender Schlag",
            },
        ],

    }

    payload.update(overrides)

    return payload


# --------------------------------------------------
# Schreibweisen
# --------------------------------------------------


def test_class_names_are_normalised_to_the_combat_log_spelling():
    """
    WarcraftLogs schreibt "DeathKnight", der Rest der Anwendung
    "Death Knight". Ohne die Umschreibung fände die Klassenfarbe
    ihren Eintrag nicht.
    """

    assert class_name("DeathKnight") == "Death Knight"
    assert class_name("deathknight") == "Death Knight"
    assert class_name("Mage") == "Mage"


def test_unknown_classes_survive_unchanged():

    assert class_name("Evoker") == "Evoker"


def test_roles_fall_back_to_the_values_when_not_reported():

    assert role_name("healer") == ROLE_HEALER
    assert role_name("Tanks") == ROLE_TANK

    #
    # Ohne Rollenangabe entscheidet der größere Wert.
    #

    assert role_name("", damage=100.0, healing=900.0) == ROLE_HEALER
    assert role_name(None, damage=900.0, healing=100.0) == ROLE_DPS


# --------------------------------------------------
# Vollständige Antwort
# --------------------------------------------------


def test_full_payload_becomes_a_complete_snapshot():

    snapshot = snapshot_from_payload(_payload(), LABEL)

    assert isinstance(snapshot, RaidSnapshot)

    assert snapshot.live is True
    assert snapshot.in_combat is True
    assert snapshot.source_label == LABEL

    assert snapshot.encounter_name == "Horridon"
    assert snapshot.pull_number == 7
    assert snapshot.raid_size == 25
    assert snapshot.boss_health_percent == 42.5

    assert snapshot.battle_res_charges == 2
    assert snapshot.heroism_used is True

    assert snapshot.death_count == 1
    assert snapshot.deaths[0].actor_name == "Seuchenherz"


def test_encounter_is_enriched_with_the_instance():
    """
    Die Instanz liefert WarcraftLogs nicht in der Form, die die
    Oberfläche zeigt - sie kommt aus analyzer.data.encounters.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL)

    assert snapshot.encounter.instance == "Thron des Donners"
    assert snapshot.encounter.difficulty == "25 Heroisch"


def test_healers_appear_only_in_the_healing_ranking():
    """
    Ein Heiler, der auch Schaden fährt, darf nicht in beiden
    Ranglisten stehen - sonst ergäben die Anteile zusammen mehr als
    100 %.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL)

    damage_names = [entry.name for entry in snapshot.top_damage]
    healing_names = [entry.name for entry in snapshot.top_healing]

    assert "Elvenne" in healing_names
    assert "Elvenne" not in damage_names


def test_rankings_are_sorted_and_shares_sum_to_one():

    snapshot = snapshot_from_payload(_payload(), LABEL)

    for rows in (snapshot.top_damage, snapshot.top_healing):

        values = [entry.value for entry in rows]

        assert values == sorted(values, reverse=True)

        assert abs(sum(entry.share for entry in rows) - 1.0) < 1e-6


def test_value_is_the_rate_per_second_and_total_the_sum():
    """
    `value` muss dieselbe Bedeutung haben wie beim Mock, sonst
    zeigten WeintTV und Academy je nach Quelle andere Größenordnungen.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL)

    top = snapshot.top_damage[0]

    assert top.name == "Pyrothal"
    assert top.total == 24000000.0
    assert top.value == pytest.approx(24000000.0 / 180.0)


def test_tanks_are_reported_with_health_and_damage_taken():

    snapshot = snapshot_from_payload(_payload(), LABEL)

    assert len(snapshot.tanks) == 1

    tank = snapshot.tanks[0]

    assert tank.actor.name == "Bramborn"
    assert tank.health_percent == 71.0
    assert tank.damage_taken == 8200000.0


def test_tanks_stay_in_the_damage_ranking():
    """
    Die Academy vergleicht Tanks untereinander und zieht diese
    Gruppe aus top_damage - fehlten sie dort, gäbe es nichts zu
    vergleichen.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL)

    assert "Bramborn" in [entry.name for entry in snapshot.top_damage]


# --------------------------------------------------
# Alter der Daten
# --------------------------------------------------


def test_pull_clock_advances_with_the_age_while_in_combat():
    """
    Zwischen zwei Abrufen soll die Uhr weiterlaufen, statt stehen zu
    bleiben.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL, age_seconds=20.0)

    assert snapshot.pull_seconds == pytest.approx(200.0)


def test_pull_clock_stands_still_when_the_fight_has_ended():

    payload = _payload()

    payload["fight"]["in_progress"] = False

    snapshot = snapshot_from_payload(payload, LABEL, age_seconds=20.0)

    assert snapshot.pull_seconds == pytest.approx(180.0)


def test_stale_data_is_announced_in_the_warnings():
    """
    Eine Raidleitung, die veraltete Zahlen für taggenau hält, trifft
    Entscheidungen auf falscher Grundlage - der Verzug muss sichtbar
    sein.
    """

    fresh = snapshot_from_payload(_payload(), LABEL, age_seconds=5.0)

    stale = snapshot_from_payload(
        _payload(),
        LABEL,
        age_seconds=STALE_AFTER + 10.0,
    )

    assert not any("alt" in text for text in fresh.warnings)

    assert any("alt" in text for text in stale.warnings)


# --------------------------------------------------
# Unvollständige und kaputte Antworten
# --------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"fight": None, "players": None},
        {"fight": {}, "players": []},
        {"fight": "unerwartet", "players": "unerwartet"},
        {"players": [None, "kaputt", {}]},
        {"fight": {"duration": 0}, "players": [{"name": "A"}]},
        {"fight": {"duration": None, "boss_percentage": None}},
    ],
)
def test_incomplete_payloads_still_yield_a_valid_snapshot(payload):
    """
    Der Bot darf jederzeit ein Feld weglassen. Nichts davon darf zu
    einer Ausnahme führen - snapshot() wirft nie.
    """

    snapshot = snapshot_from_payload(payload, LABEL)

    assert isinstance(snapshot, RaidSnapshot)

    assert snapshot.source_label == LABEL

    assert 0.0 <= snapshot.boss_health_percent <= 100.0

    assert snapshot.pull_clock


def test_players_without_a_name_are_dropped():

    payload = _payload(players=[
        {"name": "", "damage_total": 100.0},
        {"name": "Pyrothal", "damage_total": 200.0},
    ])

    snapshot = snapshot_from_payload(payload, LABEL)

    assert [entry.name for entry in snapshot.top_damage] == ["Pyrothal"]


def test_nonsense_numbers_do_not_reach_the_snapshot():
    """
    NaN oder Unendlich würden sich durch Sortierung, Anteile und
    Balkenbreiten ziehen und die Oberfläche unbrauchbar machen.
    """

    payload = _payload()

    payload["fight"]["boss_percentage"] = "keine Zahl"
    payload["fight"]["duration"] = float("nan")

    snapshot = snapshot_from_payload(payload, LABEL)

    assert snapshot.boss_health_percent == 100.0

    for entry in snapshot.top_damage:

        assert entry.value == entry.value
        assert entry.share == entry.share


def test_boss_percentage_is_clamped():

    for value, expected in ((-20.0, 0.0), (250.0, 100.0)):

        payload = _payload()

        payload["fight"]["boss_percentage"] = value

        snapshot = snapshot_from_payload(payload, LABEL)

        assert snapshot.boss_health_percent == expected


def test_raid_size_falls_back_to_the_number_of_players():

    payload = _payload()

    del payload["fight"]["raid_size"]

    snapshot = snapshot_from_payload(payload, LABEL)

    assert snapshot.raid_size == 4


def test_mechanics_and_consumables_are_optional():
    """
    WarcraftLogs liefert beides nicht von selbst. Die Felder sind im
    Vertrag vorgesehen, damit der Bot sie später ohne Änderung an
    dieser App nachliefern kann.
    """

    without = snapshot_from_payload(_payload(), LABEL)

    assert without.mechanics == ()
    assert without.consumables == ()

    with_data = snapshot_from_payload(
        _payload(
            mechanics=[{
                "name": "Pyrothal",
                "mechanic": "Im Feuer stehen geblieben",
                "count": 2,
                "category": "positioning",
            }],
            consumables=[{
                "label": "Flask",
                "used": 24,
                "total": 25,
                "missing": ["Seuchenherz"],
            }],
        ),
        LABEL,
    )

    assert with_data.mechanics[0].actor_name == "Pyrothal"
    assert with_data.mechanics[0].count == 2

    assert with_data.consumables[0].label == "Flask"
    assert with_data.consumables[0].missing == ("Seuchenherz",)


# --------------------------------------------------
# Herkunft
# --------------------------------------------------


def test_report_label_names_zone_and_code():

    label = report_label(_payload())

    assert "Thron des Donners" in label
    assert "aBcDeF12" in label


def test_report_label_survives_a_missing_report():

    assert report_label({}) == ""


# --------------------------------------------------
# Direktzugriff
# --------------------------------------------------


def test_build_metrics_handles_an_empty_roster():

    damage, healing = build_metrics([], duration=10.0)

    assert damage == ()
    assert healing == ()


# --------------------------------------------------
# Archiv: live-Flag
# --------------------------------------------------


def test_archived_fights_are_never_marked_live():
    """
    Ein aus dem Archiv geladener Fight ist per Definition beendet -
    selbst wenn `in_progress` aus historischen Gründen zufällig
    true wäre, darf das WeintTV nicht als "LIVE" anzeigen.
    """

    payload = _payload()

    payload["fight"]["in_progress"] = True

    snapshot = snapshot_from_payload(payload, LABEL, live=False)

    assert snapshot.live is False
    assert snapshot.in_combat is True


def test_live_defaults_to_true_for_backward_compatibility():
    """
    Der Live-Provider ruft snapshot_from_payload() ohne das neue
    live-Argument auf - das darf sein bisheriges Verhalten nicht
    ändern.
    """

    snapshot = snapshot_from_payload(_payload(), LABEL)

    assert snapshot.live is True


# --------------------------------------------------
# Archiv: Report- und Fight-Listen
# --------------------------------------------------


def test_build_report_list_maps_known_fields():

    reports = build_report_list({
        "reports": [
            {
                "code": "aBcDeF12",
                "title": "Mittwochsraid",
                "zone": "Thron des Donners",
                "start": "2026-07-23T19:05:00Z",
            },
        ],
    })

    assert len(reports) == 1

    report = reports[0]

    assert report.code == "aBcDeF12"
    assert report.title == "Mittwochsraid"
    assert report.zone == "Thron des Donners"
    assert report.label == "Mittwochsraid · Thron des Donners"


def test_build_report_list_drops_entries_without_a_code():
    """
    Ohne Code lässt sich der Report später nicht abrufen - ein
    Eintrag wäre nur ein nutzloser Listenplatz.
    """

    reports = build_report_list({
        "reports": [
            {"title": "kein Code"},
            {"code": "gueltig"},
        ],
    })

    assert [report.code for report in reports] == ["gueltig"]


def test_build_report_list_survives_malformed_input():

    assert build_report_list({}) == ()
    assert build_report_list({"reports": "kaputt"}) == ()
    assert build_report_list({"reports": [None, "kaputt", {}]}) == ()


def test_report_label_falls_back_to_the_code():

    from analyzer.providers.warcraftlogs_payload import ReportSummary

    report = ReportSummary(code="aBcDeF12")

    assert report.label == "aBcDeF12"


def test_build_fight_list_maps_known_fields():

    fights = build_fight_list({
        "fights": [
            {
                "id": 12,
                "name": "Horridon",
                "difficulty_id": 6,
                "kill": False,
                "boss_percentage": 42.5,
                "duration": 187.4,
                "pull_number": 7,
            },
        ],
    })

    assert len(fights) == 1

    fight = fights[0]

    assert fight.fight_id == 12
    assert fight.encounter_name == "Horridon"
    assert fight.difficulty == "25 Heroisch"
    assert fight.kill is False
    assert fight.boss_percentage == 42.5
    assert fight.pull_number == 7
    assert fight.label == "Pull 7 · Horridon · 42 % · 03:07"


def test_build_fight_list_labels_a_kill_without_a_percentage():

    fights = build_fight_list({
        "fights": [
            {"id": 1, "name": "Horridon", "kill": True, "duration": 200.0},
        ],
    })

    assert "Kill" in fights[0].label


def test_build_fight_list_drops_entries_without_a_usable_id():

    fights = build_fight_list({
        "fights": [
            {"name": "ohne id"},
            {"id": 3, "name": "gueltig"},
        ],
    })

    assert [fight.fight_id for fight in fights] == [3]


def test_build_fight_list_survives_malformed_input():
    """
    None/String-Einträge und ein leeres Dict (fehlende "id" -> -1,
    wird verworfen) dürfen keine Ausnahme auslösen.
    """

    assert build_fight_list({}) == ()
    assert build_fight_list({"fights": "kaputt"}) == ()
    assert build_fight_list({"fights": [None, "kaputt", {}]}) == ()
