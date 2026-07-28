"""
Der Mock-Provider ist die Referenz-Datenquelle: WeintTV und die
Academy werden gegen ihn entwickelt. Bricht seine Zusicherung
(deterministisch, in sich konsistent), sind alle darauf aufbauenden
Ansichten unzuverlässig.
"""

from analyzer.models import RaidSnapshot
from analyzer.providers.base import RaidDataProvider
from analyzer.providers.mock import (
    BATTLE_RES_MAX,
    HEROISM_AT,
    PULL_SECONDS,
    RAID_SIZE,
    MockRaidDataProvider,
)


def test_implements_the_provider_interface():

    assert issubclass(MockRaidDataProvider, RaidDataProvider)

    provider = MockRaidDataProvider()

    assert provider.live is False
    assert provider.source_label


def test_snapshot_before_start_is_empty_but_valid():
    """
    Die Oberfläche muss auch ohne gestartete Quelle etwas zeichnen
    können - deshalb ein neutraler Snapshot statt None.
    """

    provider = MockRaidDataProvider()

    snapshot = provider.snapshot()

    assert isinstance(snapshot, RaidSnapshot)
    assert snapshot.has_data is False
    assert snapshot.top_damage == ()
    assert snapshot.pull_clock == "00:00"


def test_start_and_stop_are_idempotent():

    provider = MockRaidDataProvider()

    provider.start()
    provider.start()

    assert provider.snapshot() is not None

    provider.stop()
    provider.stop()

    assert provider.snapshot().has_data is False


def test_same_moment_yields_identical_values():
    """
    Ohne Determinismus würde die Oberfläche im Sekundentakt
    flackern, und Tests wären nicht wiederholbar.
    """

    provider = MockRaidDataProvider()

    first = provider._combat_snapshot(1, 90.0)
    second = provider._combat_snapshot(1, 90.0)

    assert first.boss_health_percent == second.boss_health_percent

    assert [entry.value for entry in first.top_damage] == [
        entry.value for entry in second.top_damage
    ]


def test_roster_is_split_into_damage_and_healing_without_loss():

    provider = MockRaidDataProvider()

    snapshot = provider._combat_snapshot(1, 60.0)

    assert snapshot.raid_size == RAID_SIZE

    assert (
        len(snapshot.top_damage) + len(snapshot.top_healing)
        == RAID_SIZE
    )


def test_rankings_are_sorted_and_shares_sum_to_one():

    provider = MockRaidDataProvider()

    snapshot = provider._combat_snapshot(1, 75.0)

    for rows in (snapshot.top_damage, snapshot.top_healing):

        values = [entry.value for entry in rows]

        assert values == sorted(values, reverse=True)

        assert abs(sum(entry.share for entry in rows) - 1.0) < 1e-6


def test_boss_health_falls_over_the_pull_and_never_leaves_bounds():

    provider = MockRaidDataProvider()

    start = provider._combat_snapshot(1, 1.0).boss_health_percent
    end = provider._combat_snapshot(1, PULL_SECONDS).boss_health_percent

    assert start > end

    for seconds in range(0, int(PULL_SECONDS) + 1, 5):

        percent = provider._combat_snapshot(1, seconds).boss_health_percent

        assert 0.0 < percent <= 100.0


def test_deaths_accumulate_and_consume_battle_res_charges():

    provider = MockRaidDataProvider()

    early = provider._combat_snapshot(1, 10.0)
    late = provider._combat_snapshot(1, 170.0)

    assert early.death_count == 0
    assert early.battle_res_charges == BATTLE_RES_MAX

    assert late.death_count > 0
    assert late.battle_res_charges == BATTLE_RES_MAX - late.death_count


def test_heroism_window_opens_and_closes():

    provider = MockRaidDataProvider()

    before = provider._combat_snapshot(1, HEROISM_AT - 5.0)
    during = provider._combat_snapshot(1, HEROISM_AT + 5.0)
    after = provider._combat_snapshot(1, HEROISM_AT + 120.0)

    assert before.heroism_used is False
    assert before.heroism_remaining == 0.0

    assert during.heroism_used is True
    assert during.heroism_remaining > 0.0

    assert after.heroism_used is True
    assert after.heroism_remaining == 0.0


def test_cooldowns_report_ready_before_first_use():

    provider = MockRaidDataProvider()

    snapshot = provider._combat_snapshot(1, 0.0)

    assert snapshot.raid_cooldowns

    for state in snapshot.raid_cooldowns:

        assert state.ready is True
        assert state.remaining == 0.0
        assert state.progress == 1.0


def test_pull_clock_formats_as_minutes_and_seconds():

    provider = MockRaidDataProvider()

    assert provider._combat_snapshot(1, 0.0).pull_clock == "00:00"
    assert provider._combat_snapshot(1, 65.0).pull_clock == "01:05"
    assert provider._combat_snapshot(1, 125.0).pull_clock == "02:05"
