"""
Die Wiedergabe ist die einzige Stelle, an der aus einer Zeitreihe
wieder ein Snapshot wird. Rechnet sie falsch, zeigt WeintTV einen
Kampf, den es so nie gab - und die Academy bewertet einen Spieler
anhand erfundener Zahlen.

Geprüft wird deshalb vor allem: monotone Werte, exakte Ereigniszeiten,
saubere Ränder (Sekunde 0, Kampfende, darüber hinaus) und die
bewusste Selbstbeschränkung, unbekannte Größen leer zu lassen statt
sie zu schätzen.
"""

import pytest

from analyzer.models import RaidSnapshot
from analyzer.providers.mock import (
    BATTLE_RES_MAX,
    PULL_SECONDS,
    MockRaidDataProvider,
)
from analyzer.replay import snapshot_at
from analyzer.replay.models import FightTimeline
from analyzer.replay.payload import timeline_from_payload


def _timeline() -> FightTimeline:

    return MockRaidDataProvider().timeline()


#
# --------------------------------------------------
# Zeitleiste der Simulation
# --------------------------------------------------
#


def test_mock_timeline_covers_the_whole_pull():

    timeline = _timeline()

    assert timeline.has_data is True
    assert timeline.duration == PULL_SECONDS
    assert timeline.sample_count == int(PULL_SECONDS) + 1
    assert len(timeline.players) == 25
    assert timeline.avoidable_hits


def test_timeline_is_deterministic():
    """
    Zweimal dieselbe Zeitleiste zu bauen muss dieselben Reihen
    ergeben - sonst würde ein erneutes Öffnen der Wiedergabe andere
    Zahlen zeigen als beim ersten Mal.
    """

    first = MockRaidDataProvider().timeline()
    second = MockRaidDataProvider().timeline()

    assert first.boss_health == second.boss_health

    for left, right in zip(first.players, second.players):

        assert left.actor == right.actor
        assert left.damage == right.damage
        assert left.damage_taken == right.damage_taken


#
# --------------------------------------------------
# Rekonstruktion
# --------------------------------------------------
#


def test_snapshot_at_never_raises_on_an_empty_timeline():
    """
    `snapshot_at` wird viermal pro Sekunde aufgerufen. Eine Ausnahme
    darin würde die Wiedergabe mitten im Abspielen abreißen lassen.
    """

    snapshot = snapshot_at(FightTimeline(), 42.0, "Wiedergabe")

    assert isinstance(snapshot, RaidSnapshot)
    assert snapshot.has_data is False
    assert snapshot.source_label == "Wiedergabe"


@pytest.mark.parametrize(
    "seconds",
    [-50.0, 0.0, 0.5, 37.0, 96.0, 179.9, PULL_SECONDS, PULL_SECONDS + 500.0],
)
def test_snapshot_at_stays_within_bounds_at_every_position(seconds):
    """
    Ein Schieberegler darf nicht aus dem Kampf herauslaufen können.
    """

    snapshot = snapshot_at(_timeline(), seconds)

    assert 0.0 <= snapshot.pull_seconds <= PULL_SECONDS
    assert 0.0 <= snapshot.boss_health_percent <= 100.0
    assert snapshot.battle_res_charges >= 0


def test_same_position_yields_identical_values():

    timeline = _timeline()

    first = snapshot_at(timeline, 88.0)
    second = snapshot_at(timeline, 88.0)

    assert first.boss_health_percent == second.boss_health_percent
    assert first.death_count == second.death_count

    assert [entry.total for entry in first.top_damage] == [
        entry.total for entry in second.top_damage
    ]


def test_totals_only_grow_over_the_pull():
    """
    Kumulative Reihen dürfen niemals kleiner werden. Täten sie es,
    würde beim Vorspulen der Schaden eines Spielers sinken.
    """

    timeline = _timeline()

    previous = 0.0

    previous_movement = 0.0

    for at in range(0, int(PULL_SECONDS) + 1, 10):

        snapshot = snapshot_at(timeline, float(at))

        total = sum(entry.total for entry in snapshot.top_damage)

        assert total >= previous - 0.01

        assert snapshot.movement_average >= previous_movement - 0.01

        previous = total

        previous_movement = snapshot.movement_average


def test_boss_health_falls_over_the_pull():

    timeline = _timeline()

    assert snapshot_at(timeline, 0.0).boss_health_percent > 95.0
    assert snapshot_at(timeline, PULL_SECONDS).boss_health_percent < 5.0


#
# --------------------------------------------------
# Ereignisse
# --------------------------------------------------
#


def test_events_appear_exactly_at_their_timestamp():

    timeline = _timeline()

    first_death = min(death.at_seconds for death in timeline.deaths)

    assert snapshot_at(timeline, first_death - 0.5).death_count == 0
    assert snapshot_at(timeline, first_death).death_count == 1


def test_combat_events_reach_the_snapshot_up_to_the_current_second():
    """
    Die Zeitleiste trug ihre sonstigen Ereignisse (Phasenwechsel,
    angesagte Bossfähigkeiten) bisher nur mit sich herum: gelesen hat
    sie niemand, also zeigte die Wiedergabe sie auch nicht an. Sie
    gehören in den Snapshot, und zwar nach derselben Regel wie Tode -
    nur bis zur laufenden Sekunde.
    """

    timeline = _timeline()

    assert timeline.events

    first = timeline.events[0].at_seconds

    later = max(event.at_seconds for event in timeline.events)

    assert len(snapshot_at(timeline, first).events) >= 1

    assert snapshot_at(timeline, later).events == timeline.events

    #
    # Und nichts aus der Zukunft.
    #

    middle = snapshot_at(timeline, (first + later) / 2.0)

    assert all(
        event.at_seconds <= (first + later) / 2.0
        for event in middle.events
    )

    assert len(middle.events) < len(timeline.events)


def test_resurrections_return_a_battle_res_charge_over_time():
    """
    Vor dem Rezz sind alle Ladungen da, danach eine weniger - genau
    die Information, die die reine Ladungsanzeige bisher nicht
    erklären konnte.
    """

    timeline = _timeline()

    event = timeline.resurrections[0]

    before = snapshot_at(timeline, event.at_seconds - 1.0)
    after = snapshot_at(timeline, event.at_seconds)

    assert before.battle_res_charges == BATTLE_RES_MAX
    assert after.battle_res_charges == BATTLE_RES_MAX - 1

    assert after.resurrections[0].target == event.target
    assert after.resurrections[0].caster == event.caster


def test_heroism_window_is_reported_with_its_remaining_time():

    timeline = _timeline()

    window = timeline.heroism_windows[0]

    before = snapshot_at(timeline, window.start - 5.0)
    during = snapshot_at(timeline, window.start + 10.0)
    after = snapshot_at(timeline, window.end + 5.0)

    assert before.heroism_used is False
    assert before.heroism_windows == ()

    assert during.heroism_used is True
    assert during.heroism_remaining == pytest.approx(window.duration - 10.0)

    assert after.heroism_used is True
    assert after.heroism_remaining == 0.0


def test_cooldowns_are_truncated_to_the_current_position():
    """
    Nach zehn Sekunden darf kein Einsatz auftauchen, der erst später
    stattfand - und "möglich" muss gegen die bisher vergangene Zeit
    gerechnet werden, sonst sähe jeder Spieler am Anfang so aus, als
    hätte er alles verschenkt.
    """

    timeline = _timeline()

    early = snapshot_at(timeline, 20.0)

    for usage in early.cooldown_usage:

        assert all(at <= 20.0 for at in usage.cast_times)

        if usage.cooldown > 0:
            assert usage.possible == int(20.0 // usage.cooldown) + 1


def test_live_cooldown_lists_are_derived_from_the_cast_times():
    """
    Der Kniff, der WeintTVs bestehende Cooldown-Karten unverändert
    weiterarbeiten lässt: sie bekommen auch in der Wiedergabe die
    Struktur, die sie aus dem Live-Betrieb kennen.
    """

    timeline = _timeline()

    #
    # "Stampeding Roar" wird in der Simulation bei Sekunde 26 gewirkt
    # und hat 120 Sekunden Abklingzeit.
    #

    snapshot = snapshot_at(timeline, 40.0)

    roar = next(
        state
        for state in snapshot.raid_cooldowns
        if state.name == "Stampeding Roar"
    )

    assert roar.ready is False
    assert roar.remaining == pytest.approx(120.0 - (40.0 - 26.0))

    before = snapshot_at(timeline, 10.0)

    assert next(
        state
        for state in before.raid_cooldowns
        if state.name == "Stampeding Roar"
    ).ready is True


#
# --------------------------------------------------
# Bewusste Selbstbeschränkung
# --------------------------------------------------
#


def test_unreconstructable_fields_stay_empty_instead_of_being_guessed():
    """
    Verbrauchsgüter gelten für den ganzen Kampf und lassen sich nicht
    auf eine Sekunde herunterbrechen. Sie zu schätzen wäre genau die
    Sorte erfundener Zahl, die eine tiefgründige Analyse
    unglaubwürdig macht.
    """

    timeline = _timeline()

    assert snapshot_at(timeline, 60.0).consumables == ()

    #
    # Am Ende kommen sie aus dem Gesamtstand.
    #

    assert snapshot_at(timeline, PULL_SECONDS).consumables


def test_replay_snapshots_are_marked_as_reconstructed():
    """
    Eine Raidleitung darf eine Wiedergabe nie für den Live-Stand
    halten.
    """

    snapshot = snapshot_at(_timeline(), 60.0)

    assert snapshot.live is False
    assert any("Wiedergabe" in text for text in snapshot.warnings)


def test_end_of_replay_matches_the_archive_view():
    """
    Wer die Wiedergabe bis zum Ende laufen lässt, muss denselben
    Stand sehen wie beim direkten Blick ins Archiv - sonst wirkt eine
    der beiden Ansichten falsch.
    """

    timeline = _timeline()

    final = snapshot_at(timeline, PULL_SECONDS)

    assert final.in_combat is False
    assert final.damage_taken == timeline.damage_taken_totals
    assert final.death_count == len(timeline.deaths)


#
# --------------------------------------------------
# Bot-Antwort
# --------------------------------------------------
#


def test_timeline_payload_survives_an_empty_answer():

    timeline = timeline_from_payload({}, "Wiedergabe")

    assert isinstance(timeline, FightTimeline)
    assert timeline.has_data is False

    #
    # Und bleibt damit für die Wiedergabe unschädlich.
    #

    assert snapshot_at(timeline, 30.0).has_data is False


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"fight": None, "players": None},
        {"players": "kaputt", "boss_health": {"a": 1}},
        {"players": [{"name": None}, {}], "interval": 0},
        {"interval": "abc", "boss_health": [None, "x", 42]},
    ],
)
def test_timeline_payload_never_raises(payload):
    """
    Eine unvollständige oder kaputte Antwort ist kein Fehler - sie
    darf die Wiedergabe nur leer lassen, nicht die Anwendung
    abstürzen lassen.
    """

    timeline = timeline_from_payload(payload, "Wiedergabe")

    assert isinstance(timeline, FightTimeline)

    assert isinstance(snapshot_at(timeline, 12.0), RaidSnapshot)


def test_timeline_payload_tolerates_series_of_different_lengths():
    """
    Bossleben mit 4 Werten, Schaden mit 2: das darf keinen
    IndexError geben, egal an welcher Stelle gelesen wird.
    """

    timeline = timeline_from_payload(
        {
            "interval": 1.0,
            "fight": {"name": "Horridon", "duration": 4.0, "raid_size": 1},
            "boss_health": [100.0, 80.0, 60.0, 40.0],
            "players": [
                {
                    "name": "Testheld",
                    "class": "Mage",
                    "role": "dps",
                    "damage": [0.0, 500.0],
                }
            ],
        },
        "Wiedergabe",
    )

    for at in (0.0, 1.5, 3.0, 4.0, 10.0):

        snapshot = snapshot_at(timeline, at)

        assert isinstance(snapshot, RaidSnapshot)
