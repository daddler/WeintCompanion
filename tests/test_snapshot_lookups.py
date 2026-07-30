"""
Die neuen Felder und Nachschlagemethoden des RaidSnapshot.

Zwei Zusicherungen sichert diese Datei ab:

1. **Rückwärtskompatibilität.** Zehn neue Felder sind dazugekommen.
   Wäre auch nur eines ohne Standardwert, könnte kein bestehender
   Aufrufer mehr einen Snapshot bauen - und eine Datenquelle, die den
   Block nicht liefert, würde die ganze Oberfläche lahmlegen.
2. **Keine erfundenen Werte.** Fehlt eine Angabe, muss das Ergebnis
   None oder ein leeres Tupel sein, nie eine Null, die wie eine
   gemessene Zahl aussieht.
"""

from analyzer.models import (
    UPTIME_DOT,
    UPTIME_HOT,
    AbilityDamage,
    ActivityEntry,
    Actor,
    CooldownUsage,
    DamageTakenEntry,
    DeathEntry,
    HeroismWindow,
    MetricEntry,
    MovementEntry,
    PullSummary,
    RaidSnapshot,
    ResurrectionEvent,
    SupportEvent,
    UptimeEntry,
)


def test_an_empty_snapshot_still_constructs_without_arguments():

    snapshot = RaidSnapshot()

    assert snapshot.has_data is False
    assert snapshot.has_analysis is False


def test_every_new_field_defaults_to_empty():

    snapshot = RaidSnapshot()

    for field in (
        snapshot.activity,
        snapshot.dot_uptimes,
        snapshot.hot_uptimes,
        snapshot.movement,
        snapshot.damage_taken,
        snapshot.cooldown_usage,
        snapshot.heroism_windows,
        snapshot.resurrections,
        snapshot.interrupts,
        snapshot.dispels,
    ):
        assert field == ()


def test_lookups_return_nothing_instead_of_raising():

    snapshot = RaidSnapshot()

    assert snapshot.activity_of("X") is None
    assert snapshot.movement_of("X") is None
    assert snapshot.damage_taken_of("X") is None
    assert snapshot.heroism_window_at(42.0) is None

    assert snapshot.cooldowns_of("X") == ()
    assert snapshot.uptimes_of("X") == ()
    assert snapshot.interrupts_of("X") == ()
    assert snapshot.dispels_of("X") == ()
    assert snapshot.deaths_of("X") == ()


def test_raid_averages_are_zero_on_an_empty_snapshot():

    snapshot = RaidSnapshot()

    assert snapshot.movement_average == 0.0
    assert snapshot.damage_taken_total == 0.0
    assert snapshot.avoidable_total == 0.0
    assert snapshot.actor_names == ()


def test_movement_average_matches_its_rows():
    """
    Eine Eigenschaft und kein Feld - genau damit dieser Widerspruch
    gar nicht entstehen kann.
    """

    snapshot = RaidSnapshot(
        movement=(
            MovementEntry(actor_name="A", meters=100.0),
            MovementEntry(actor_name="B", meters=300.0),
        ),
    )

    assert snapshot.movement_average == 200.0


def test_uptimes_are_separated_by_kind():

    snapshot = RaidSnapshot(
        dot_uptimes=(
            UptimeEntry(actor_name="A", ability="Moonfire", kind=UPTIME_DOT),
        ),
        hot_uptimes=(
            UptimeEntry(actor_name="A", ability="Lifebloom", kind=UPTIME_HOT),
        ),
    )

    assert snapshot.uptimes_of("A", UPTIME_DOT)[0].ability == "Moonfire"
    assert snapshot.uptimes_of("A", UPTIME_HOT)[0].ability == "Lifebloom"


#
# --------------------------------------------------
# Eigenschaften der neuen Strukturen
# --------------------------------------------------
#


def test_unclassified_damage_never_goes_negative():
    """
    Bei widersprüchlichen Angaben der Datenquelle dürfte sonst ein
    negativer Rest entstehen - und die Oberfläche zeigte "-40k nicht
    eingeordnet".
    """

    entry = DamageTakenEntry(
        actor_name="A",
        total=100.0,
        avoidable=80.0,
        unavoidable=80.0,
    )

    assert entry.unclassified == 0.0


def test_shares_of_an_empty_damage_entry_are_zero():

    entry = DamageTakenEntry(actor_name="A")

    assert entry.avoidable_share == 0.0
    assert entry.classified_share == 0.0


def test_cooldown_usage_derives_its_numbers_from_the_cast_times():

    usage = CooldownUsage(
        actor_name="A",
        ability="Combustion",
        cast_times=(22.0, 99.0, 145.0),
        cooldown=45.0,
        possible=4,
        in_burst=1,
    )

    assert usage.uses == 3
    assert usage.wasted == 1
    assert usage.efficiency == 0.75
    assert usage.first_cast == 22.0
    assert round(usage.burst_share, 4) == round(1 / 3, 4)


def test_a_cooldown_without_possible_uses_reports_no_efficiency():
    """
    Ohne bekannte Abklingzeit gibt es keine Obergrenze - eine Quote
    daraus wäre erfunden.
    """

    usage = CooldownUsage(actor_name="A", ability="X", cast_times=(1.0,))

    assert usage.possible == 0
    assert usage.efficiency == 0.0
    assert usage.wasted == 0


def test_heroism_window_knows_its_span():

    window = HeroismWindow(start=96.0, end=136.0, source="Kaldrun")

    assert window.duration == 40.0
    assert window.contains(100.0) is True
    assert window.contains(95.9) is False
    assert window.contains(136.0) is True
    assert window.clock == "01:36 - 02:16"


def test_resurrection_formats_its_moment():

    event = ResurrectionEvent(target="A", caster="B", at_seconds=78.0)

    assert event.clock == "01:18"


def test_ability_damage_knows_whether_it_was_avoidable():

    assert AbilityDamage(ability="X", verdict="avoidable").avoidable is True
    assert AbilityDamage(ability="X", verdict="unknown").avoidable is False


#
# --------------------------------------------------
# has_analysis
# --------------------------------------------------
#


def test_has_analysis_reacts_to_any_deep_field():
    """
    Der eine Schalter, mit dem die Oberfläche eine ganze Karte auf
    "keine Daten" stellt.
    """

    assert RaidSnapshot(
        activity=(ActivityEntry(actor_name="A"),),
    ).has_analysis is True

    assert RaidSnapshot(
        damage_taken=(DamageTakenEntry(actor_name="A"),),
    ).has_analysis is True

    #
    # Reine Ereignislisten zählen bewusst nicht: ein Rezz allein ist
    # noch keine Tiefenauswertung.
    #

    assert RaidSnapshot(
        resurrections=(ResurrectionEvent(target="A"),),
    ).has_analysis is False


#
# --------------------------------------------------
# Pull-Zusammenfassung
# --------------------------------------------------
#


def test_pull_summary_carries_the_new_numbers():
    """
    Damit der Verlauf-Tab Entwicklung über mehrere Pulls zeigen kann
    und nicht nur Kill oder Wipe.
    """

    actor = Actor(name="A", class_name="Mage")

    snapshot = RaidSnapshot(
        pull_number=3,
        raid_size=2,
        top_damage=(MetricEntry(actor=actor, value=100.0, total=1000.0),),
        deaths=(DeathEntry(actor_name="A", at_seconds=10.0),),
        movement=(MovementEntry(actor_name="A", meters=400.0),),
        damage_taken=(
            DamageTakenEntry(actor_name="A", total=100.0, avoidable=25.0),
        ),
    )

    summary = PullSummary.from_snapshot(snapshot)

    assert summary.pull_number == 3
    assert summary.avoidable_damage == 25.0
    assert summary.movement_average == 400.0


def test_support_events_are_filtered_by_actor():

    snapshot = RaidSnapshot(
        interrupts=(
            SupportEvent(actor_name="A", at_seconds=10.0),
            SupportEvent(actor_name="B", at_seconds=20.0),
        ),
    )

    assert len(snapshot.interrupts_of("A")) == 1
    assert snapshot.interrupts_of("C") == ()
