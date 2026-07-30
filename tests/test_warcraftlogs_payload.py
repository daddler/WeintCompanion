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
    _format_report_date,
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


def test_raid_and_heal_cooldowns_are_optional():
    """
    Wie mechanics/consumables liefert WarcraftLogs auch das nicht von
    selbst - der Bot leitet es aus der Casts-Tabelle ab (siehe
    services/warcraftlogs.py::_build_cooldowns).
    """

    without = snapshot_from_payload(_payload(), LABEL)

    assert without.raid_cooldowns == ()
    assert without.heal_cooldowns == ()

    with_data = snapshot_from_payload(
        _payload(
            raid_cooldowns=[{
                "name": "Rallying Cry",
                "actor_name": "Grimmzahn",
                "ready": True,
            }],
            heal_cooldowns=[{
                "name": "Healing Tide Totem",
                "actor_name": "Kaldrun (2×)",
                "ready": True,
            }],
        ),
        LABEL,
    )

    assert with_data.raid_cooldowns[0].name == "Rallying Cry"
    assert with_data.raid_cooldowns[0].actor_name == "Grimmzahn"
    assert with_data.raid_cooldowns[0].ready is True

    assert with_data.heal_cooldowns[0].name == "Healing Tide Totem"
    assert with_data.heal_cooldowns[0].actor_name == "Kaldrun (2×)"


def test_cooldowns_without_name_or_actor_are_dropped():
    snapshot = snapshot_from_payload(
        _payload(raid_cooldowns=[
            {"name": "", "actor_name": "Grimmzahn"},
            {"name": "Rallying Cry", "actor_name": ""},
            {"actor_name": "Grimmzahn"},
        ]),
        LABEL,
    )

    assert snapshot.raid_cooldowns == ()


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
# Archiv: Report-Datum im Dropdown-Label
# --------------------------------------------------


def test_format_report_date_parses_utc_timestamp():

    import datetime

    formatted = _format_report_date("2026-07-23T19:05:00Z")

    parsed = datetime.datetime.strptime(formatted, "%d.%m.%Y %H:%M")

    # In lokale Zeit umgerechnet - nur die Rundreise pruefen (zurueck
    # nach UTC ergibt wieder den Ausgangszeitpunkt), da die konkrete
    # Uhrzeit von der Zeitzone des Testrechners abhaengt.
    assert parsed.astimezone(datetime.timezone.utc).replace(
        tzinfo=None
    ) == datetime.datetime(2026, 7, 23, 19, 5)


def test_format_report_date_empty_for_missing_value():

    assert _format_report_date("") == ""
    assert _format_report_date(None) == ""


def test_format_report_date_empty_for_invalid_value():

    assert _format_report_date("nicht-ein-datum") == ""


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
    # Die Zeit selbst haengt von der lokalen Zeitzone des Testrechners
    # ab (siehe _format_report_date) - hier wird nur geprueft, dass
    # das Datum dem restlichen Label vorangestellt wird.
    assert report.label == (
        _format_report_date("2026-07-23T19:05:00Z")
        + " · Mittwochsraid · Thron des Donners"
    )
    assert report.label.endswith("· Mittwochsraid · Thron des Donners")


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


#
# --------------------------------------------------
# Tiefenauswertung
# --------------------------------------------------
#
# Alle Blöcke sind optional. Der wichtigste Test dieser Gruppe ist
# deshalb nicht, dass sie richtig gelesen werden - sondern dass ihr
# Fehlen folgenlos bleibt. Der Bot liefert sie heute noch nicht, und
# jede neue Karte in WeintTV muss trotzdem stumm auf "keine Daten"
# gehen statt eine Ausnahme auszulösen.
#


def _deep_payload():

    return _payload(
        fight={
            "name": "Horridon",
            "duration": 200.0,
            "raid_size": 2,
            "in_progress": False,
            "boss_percentage": 0.5,
            "pull_number": 4,
            "battle_res_max": 3,
        },
        players=[
            {
                "name": "Pyrothal",
                "class": "Mage",
                "spec": "Feuer",
                "role": "dps",
                "damage_total": 20000000.0,
                "active_time": 190.0,
                "casts": 300,
                "movement_units": 43744.0,
                "damage_taken_abilities": [
                    {"ability": "Double Swipe", "amount": 96000.0, "hits": 2},
                    {"ability": "Dire Call", "amount": 54000.0, "hits": 3},
                ],
                "dots": [
                    {"aura": "Ignite", "uptime_percent": 86.0,
                     "applications": 12, "expected_percent": 85.0},
                ],
                "cooldowns": [
                    {"name": "Combustion", "casts": [22.0, 99.0],
                     "cooldown": 45.0},
                ],
            },
            {
                "name": "Elvenne",
                "class": "Druid",
                "role": "healer",
                "healing_total": 9000000.0,
                "hots": [
                    {"aura": "Lifebloom", "uptime_percent": 96.0},
                ],
            },
        ],
        heroism_windows=[
            {"start": 90.0, "end": 130.0, "source": "Kaldrun"},
        ],
        resurrects=[
            {"target": "Krallenwut", "caster": "Elvenne", "at": 78.0,
             "ability": "Wiedergeburt"},
        ],
        interrupts=[
            {"actor": "Pyrothal", "at": 40.0, "target": "Add",
             "ability": "Counterspell"},
        ],
        dispels=[
            {"actor": "Elvenne", "at": 55.0, "target": "Pyrothal"},
        ],
    )


def test_deep_analysis_blocks_are_mapped():

    snapshot = snapshot_from_payload(_deep_payload(), "Bot")

    assert snapshot.has_analysis is True

    activity = snapshot.activity_of("Pyrothal")

    assert activity is not None
    assert round(activity.active_percent) == 95
    assert activity.casts == 300
    assert round(activity.apm) == 90

    assert snapshot.uptimes_of("Pyrothal")[0].ability == "Ignite"
    assert snapshot.uptimes_of("Elvenne", "hot")[0].ability == "Lifebloom"

    movement = snapshot.movement_of("Pyrothal")

    assert movement is not None
    assert round(movement.meters) == 400
    assert movement.estimated is True

    assert len(snapshot.interrupts) == 1
    assert len(snapshot.dispels) == 1


def test_damage_taken_is_classified_using_the_fight_name():
    """
    Die Einordnung macht der Companion, nicht der Bot - sie hängt
    deshalb am Bossnamen aus dem Kampf.
    """

    snapshot = snapshot_from_payload(_deep_payload(), "Bot")

    entry = snapshot.damage_taken_of("Pyrothal")

    assert entry is not None
    assert entry.avoidable == 96000.0
    assert entry.unavoidable == 54000.0
    assert entry.avoidable_hits == 2

    #
    # Und daraus entsteht ein Mechanikfehler mit Kategorie.
    #

    assert any(
        issue.actor_name == "Pyrothal" and issue.category
        for issue in snapshot.mechanics
    )


def test_cooldown_usage_counts_possible_uses_and_burst_alignment():

    snapshot = snapshot_from_payload(_deep_payload(), "Bot")

    usage = snapshot.cooldowns_of("Pyrothal")[0]

    assert usage.ability == "Combustion"
    assert usage.uses == 2

    #
    # 200 Sekunden Kampf, 45 Sekunden Abklingzeit: der erste Einsatz
    # zählt immer mit (Kampfbeginn), danach je vollständig
    # abgelaufener Abklingzeit einer mehr - also bei 0, 45, 90, 135
    # und 180 Sekunden. Der Companion rechnet das selbst aus; der Bot
    # liefert nur die Tatsachen.
    #

    assert usage.possible == 5

    #
    # Ein Einsatz lag im Heldentum-Fenster (90-130 s).
    #

    assert usage.in_burst == 1


def test_heroism_is_derived_from_the_windows_when_the_flag_is_missing():

    snapshot = snapshot_from_payload(_deep_payload(), "Bot")

    assert snapshot.heroism_used is True
    assert snapshot.heroism_windows[0].start == 90.0


def test_battle_res_charges_are_derived_from_the_resurrections():
    """
    Fehlt die Restanzahl, ist die Differenz die ehrlichere Angabe als
    eine Null - die sähe aus, als wären alle Ladungen verbraucht.
    """

    snapshot = snapshot_from_payload(_deep_payload(), "Bot")

    assert snapshot.battle_res_max == 3
    assert snapshot.battle_res_charges == 2


def test_an_explicit_charge_count_wins_over_the_derivation():

    payload = _deep_payload()

    payload["fight"]["battle_res_charges"] = 1

    assert snapshot_from_payload(payload, "Bot").battle_res_charges == 1


def test_a_payload_without_any_deep_block_degrades_silently():
    """
    Der heutige Bot liefert nichts davon. Jede neue Karte muss dann
    stumm auf "keine Daten" gehen.
    """

    snapshot = snapshot_from_payload(_payload(), "Bot")

    assert snapshot.has_analysis is False

    assert snapshot.activity == ()
    assert snapshot.dot_uptimes == ()
    assert snapshot.movement == ()
    assert snapshot.damage_taken == ()
    assert snapshot.cooldown_usage == ()
    assert snapshot.heroism_windows == ()

    #
    # Und die vorhandenen Angaben bleiben unberührt.
    #

    assert snapshot.top_damage


@pytest.mark.parametrize(
    "overrides",
    [
        {"heroism_windows": "kaputt"},
        {"heroism_windows": [{"start": 50.0}]},
        {"heroism_windows": [{"start": 100.0, "end": 20.0}]},
        {"resurrects": [{"caster": "X"}]},
        {"interrupts": [{}, None]},
        {"players": [{"name": "A", "dots": "kaputt"}]},
        {"players": [{"name": "A", "cooldowns": [{"casts": [1]}]}]},
        {"players": [{"name": "A", "damage_taken_abilities": [{"amount": 5}]}]},
        {"players": [{"name": "A", "movement_units": "viel"}]},
    ],
)
def test_broken_deep_blocks_are_dropped_instead_of_raising(overrides):

    snapshot = snapshot_from_payload(_payload(**overrides), "Bot")

    assert isinstance(snapshot, RaidSnapshot)


def test_a_window_without_a_usable_span_is_dropped():

    snapshot = snapshot_from_payload(
        _payload(heroism_windows=[{"start": 100.0, "end": 20.0}]),
        "Bot",
    )

    assert snapshot.heroism_windows == ()
