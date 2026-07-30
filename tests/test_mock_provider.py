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


def test_deaths_accumulate_over_the_pull():

    provider = MockRaidDataProvider()

    early = provider._combat_snapshot(1, 10.0)
    late = provider._combat_snapshot(1, 170.0)

    assert early.death_count == 0
    assert late.death_count > 0


def test_battle_res_charges_are_consumed_by_resurrections_not_by_deaths():
    """
    Ein Tod allein kostet keine Ladung - erst die tatsächlich
    gewirkte Wiederbelebung tut das. Die frühere Fassung rechnete
    Ladungen gegen Todesfälle und zeigte dadurch zu wenige
    verbleibende Ladungen an, sobald jemand liegen blieb.
    """

    provider = MockRaidDataProvider()

    early = provider._combat_snapshot(1, 10.0)
    late = provider._combat_snapshot(1, 170.0)

    assert early.battle_res_charges == BATTLE_RES_MAX
    assert early.resurrections == ()

    #
    # Am Ende des Pulls sind zwei Spieler gestorben, aber nur einer
    # wurde hochgeholt.
    #

    assert late.death_count == 2
    assert len(late.resurrections) == 1

    assert late.battle_res_charges == BATTLE_RES_MAX - 1


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


#
# --------------------------------------------------
# Tiefenauswertung
# --------------------------------------------------
#


def test_deep_analysis_fields_are_filled_during_combat():
    """
    Die Simulation ist der einzige Weg, WeintTVs Analyse und die
    Academy außerhalb der Raidzeit zu begutachten. Bliebe auch nur
    eines der neuen Felder leer, wäre die entsprechende Karte in der
    Oberfläche dauerhaft unsichtbar - ohne dass irgendein Test
    fehlschlägt.
    """

    snapshot = MockRaidDataProvider()._combat_snapshot(1, 150.0)

    assert snapshot.has_analysis is True

    assert snapshot.activity
    assert snapshot.dot_uptimes
    assert snapshot.hot_uptimes
    assert snapshot.movement
    assert snapshot.damage_taken
    assert snapshot.cooldown_usage
    assert snapshot.heroism_windows
    assert snapshot.resurrections
    assert snapshot.interrupts
    assert snapshot.dispels


def test_avoidable_hits_are_consistent_across_every_view():
    """
    Der wichtigste Test dieser Datei.

    Ein vermeidbarer Treffer taucht an drei Stellen auf: im erhaltenen
    Schaden, als abgeleiteter Mechanikfehler und als Zähler in der
    Laufweg-Zeile. Wären diese Sichten uneinig, wäre die Simulation
    kein gültiger Beweis für den Vertrag mehr - und schlimmer: WeintTV
    und die Academy würden demselben Spieler unterschiedlich viele
    Fehler zuschreiben.
    """

    snapshot = MockRaidDataProvider()._combat_snapshot(1, PULL_SECONDS)

    hits_by_name = {
        entry.actor_name: entry.avoidable_hits
        for entry in snapshot.damage_taken
        if entry.avoidable_hits > 0
    }

    assert hits_by_name, "Die Simulation plant vermeidbare Treffer ein."

    movement_by_name = {
        entry.actor_name: entry.avoidable_hits
        for entry in snapshot.movement
    }

    for name, hits in hits_by_name.items():

        assert movement_by_name.get(name) == hits, (
            f"Laufweg-Zeile von {name} nennt eine andere Trefferzahl "
            f"als der erhaltene Schaden."
        )

        assert any(
            issue.actor_name == name
            for issue in snapshot.mechanics
        ), f"Zu den Treffern von {name} fehlt ein Mechanikfehler."


def test_damage_taken_buckets_never_exceed_the_total():

    snapshot = MockRaidDataProvider()._combat_snapshot(1, PULL_SECONDS)

    for entry in snapshot.damage_taken:

        assert entry.avoidable + entry.unavoidable <= entry.total + 0.01
        assert entry.unclassified >= 0.0
        assert 0.0 <= entry.avoidable_share <= 1.0


def test_tanks_take_mostly_unavoidable_damage():
    """
    Genau der Grund, warum die Academy rollenrelativ bewerten muss:
    ein Tank hat die höchste absolute Schadenssumme des Raids und
    macht trotzdem alles richtig.
    """

    snapshot = MockRaidDataProvider()._combat_snapshot(1, PULL_SECONDS)

    tank_names = {tank.actor.name for tank in snapshot.tanks}

    assert tank_names

    for entry in snapshot.damage_taken:

        if entry.actor_name not in tank_names:
            continue

        assert entry.avoidable_share < 0.05


def test_cooldown_usage_counts_casts_inside_the_heroism_window():
    """
    "Genutzt" ist die halbe Antwort - die eigentliche Frage ist, ob
    zum richtigen Zeitpunkt. Ohne diesen Zähler könnte die Academy
    Cooldowns nicht sinnvoll bewerten.
    """

    snapshot = MockRaidDataProvider()._combat_snapshot(1, PULL_SECONDS)

    window = snapshot.heroism_windows[0]

    aligned = [
        usage
        for usage in snapshot.cooldown_usage
        if usage.in_burst > 0
    ]

    assert aligned, "Die Simulation plant Einsätze im Fenster ein."

    for usage in aligned:

        inside = [
            at
            for at in usage.cast_times
            if window.contains(at)
        ]

        assert usage.in_burst == len(inside)

    #
    # Und es gibt bewusst auch Spieler, die daneben liegen - sonst
    # hätte die Bewertung nichts zu unterscheiden.
    #

    assert any(
        usage.cast_times and usage.in_burst == 0
        for usage in snapshot.cooldown_usage
    )


def test_deep_analysis_grows_with_the_pull():
    """
    Nach zehn Sekunden darf nicht schon der ganze Laufweg gelaufen
    sein - sonst sähe die Wiedergabe eines Pulls von der ersten
    Sekunde an fertig aus.
    """

    provider = MockRaidDataProvider()

    early = provider._combat_snapshot(1, 20.0)
    late = provider._combat_snapshot(1, PULL_SECONDS)

    assert early.movement_average < late.movement_average
    assert early.damage_taken_total < late.damage_taken_total


def test_post_pull_snapshot_keeps_the_deep_analysis():
    """
    Die frühere Fassung kopierte jedes Feld einzeln; ein neu
    hinzugefügtes Feld verschwand dabei stillschweigend. Nach dem
    Pull wäre die gesamte Analyse leer gewesen, ohne dass etwas
    fehlschlägt.
    """

    provider = MockRaidDataProvider()

    after = provider._after_snapshot(1)

    assert after.in_combat is False
    assert after.has_analysis is True

    assert after.damage_taken
    assert after.cooldown_usage
    assert after.movement
    assert after.resurrections
