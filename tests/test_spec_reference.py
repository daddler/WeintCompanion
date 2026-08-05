"""
Die Anreicherung entscheidet, was in WeintTV und der Academy als
Befund und was als Datenlücke erscheint. Beides zu verwechseln ist der
teuerste Fehler, den diese Datei machen kann: eine erfundene Null
beschuldigt einen Spieler, eine unterschlagene Null versteckt einen
echten Fehler.

Geprüft wird deshalb vor allem die Grenze zwischen beidem - und die
Regeln, die verhindern, dass aus einer Umbenennung zwei Zeilen werden.
"""

from analyzer.analysis.spec_reference import (
    apply_spec_reference,
    cooldown_hint,
    reference_hint,
)
from analyzer.models import (
    CD_DEFENSIVE,
    CD_PERSONAL,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    ActivityEntry,
    Actor,
    CooldownUsage,
    MetricEntry,
    RaidSnapshot,
    UptimeEntry,
)


ROGUE = Actor("Silbermond", "Rogue", "Meucheln", ROLE_DPS)

DRUID = Actor("Elvenne", "Druid", "Wiederherstellung", ROLE_HEALER)

WARRIOR = Actor("Bramborn", "Warrior", "Schutz", ROLE_TANK)


def _snapshot(**kwargs) -> RaidSnapshot:
    """
    Ein Snapshot mit Tiefenauswertung - ohne die tut die Anreicherung
    nichts, und das ist Absicht (siehe letzter Test).
    """

    actors = kwargs.pop("actors", (ROGUE, DRUID, WARRIOR))

    return RaidSnapshot(
        source_label="Bot",
        raid_size=25,
        pull_seconds=200.0,
        top_damage=tuple(
            MetricEntry(actor=actor, value=1000.0, total=200000.0, share=0.3)
            for actor in actors
        ),
        activity=(
            ActivityEntry(actor_name=actors[0].name, active_percent=95.0),
        ),
        **kwargs,
    )


#
# --------------------------------------------------
# Sprache und Einsortierung
# --------------------------------------------------
#


def test_a_german_report_is_recognised_and_gets_its_target_value():

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Tödliches Gift",
                uptime_percent=92.0,
            ),
        ),
    ))

    entry = snapshot.uptimes_of("Silbermond", UPTIME_DOT)[0]

    assert entry.ability == "Tödliches Gift"
    assert entry.expected_percent > 0.0


def test_an_english_report_is_shown_in_german():
    """
    In welcher Sprache ein Bericht ankommt, hängt allein daran, wer
    ihn hochgeladen hat. In einer Karte darf deshalb nicht
    "Rupture" neben "Tödliches Gift" stehen.
    """

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Rupture",
                uptime_percent=88.0,
            ),
        ),
    ))

    assert snapshot.uptimes_of("Silbermond", UPTIME_DOT)[0].ability == "Blutung"


def test_the_spell_id_wins_over_a_name_nobody_knows():
    """
    Die ID ist die einzige Angabe ohne Sprache. Eine Quelle, die einen
    unbekannten Anzeigenamen schickt, bleibt damit auswertbar.
    """

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Ability 1943",
                uptime_percent=77.0,
                spell_id=1943,
            ),
        ),
    ))

    entry = snapshot.uptimes_of("Silbermond", UPTIME_DOT)[0]

    assert entry.ability == "Blutung"
    assert entry.uptime_percent == 77.0


def test_a_hot_filed_under_dots_lands_in_the_hot_list():
    """
    Die Einsortierung entscheidet, für wen ein Effekt überhaupt
    gelesen wird: HoTs wertet die Academy nur bei Heilern aus. Legt
    die Quelle einen HoT ins falsche Fach, bliebe die HoT-Karte leer,
    obwohl die Zahl da ist.
    """

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Elvenne",
                ability="Verjüngung",
                uptime_percent=84.0,
            ),
        ),
    ))

    assert snapshot.uptimes_of("Elvenne", UPTIME_DOT) == ()

    assert snapshot.uptimes_of("Elvenne", UPTIME_HOT)[0].ability == "Verjüngung"


def test_an_unknown_ability_survives_unchanged():
    """
    Was die Tabelle nicht kennt, darf nicht verschwinden - ein
    künftiger Patch soll keine Zeile verschlucken.
    """

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Zauber von morgen",
                uptime_percent=50.0,
            ),
        ),
    ))

    assert any(
        entry.ability == "Zauber von morgen"
        for entry in snapshot.uptimes_of("Silbermond", UPTIME_DOT)
    )


#
# --------------------------------------------------
# Befund gegen Datenlücke
# --------------------------------------------------
#


def test_missing_abilities_are_filled_with_zero_when_the_source_delivers():

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Blutung",
                uptime_percent=93.0,
            ),
        ),
    ))

    rows = {
        entry.ability: entry.uptime_percent
        for entry in snapshot.uptimes_of("Silbermond", UPTIME_DOT)
    }

    assert rows["Blutung"] == 93.0

    #
    # Tödliches Gift gehört zu Meucheln und wurde nicht gemeldet.
    # Weil die Quelle DoTs nachweislich liefert, ist das eine Null.
    #

    assert rows["Tödliches Gift"] == 0.0


def test_nothing_is_claimed_for_a_kind_the_source_never_delivers():
    """
    Der wichtigste Test dieser Datei. Liefert die Quelle gar keine
    HoTs, darf für einen Heiler keine Reihe von Nullen entstehen -
    das wäre eine Behauptung über etwas, das niemand gemessen hat.
    """

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Blutung",
                uptime_percent=93.0,
            ),
        ),
    ))

    assert snapshot.uptimes_of("Elvenne", UPTIME_HOT) == ()

    assert snapshot.uptimes_of("Bramborn", UPTIME_BUFF) == ()


def test_talent_dependent_abilities_are_never_filled_in():
    """
    "Erdleben - nie aufgelegt" bei jemandem ohne die passende Wahl
    wäre ein Vorwurf für nichts.
    """

    snapshot = apply_spec_reference(_snapshot(
        hot_uptimes=(
            UptimeEntry(
                actor_name="Elvenne",
                ability="Verjüngung",
                uptime_percent=80.0,
                kind=UPTIME_HOT,
            ),
        ),
    ))

    abilities = {
        entry.ability
        for entry in snapshot.uptimes_of("Elvenne", UPTIME_HOT)
    }

    assert "Blühendes Leben" in abilities

    assert "Nachwachsen" not in abilities


def test_applying_twice_changes_nothing():
    """
    Die Anreicherung läuft an mehreren Stellen (Live, Archiv,
    Wiedergabe, Simulation). Liefe sie zweimal über denselben
    Snapshot und verdoppelte dabei Zeilen, wäre jede dieser Stellen
    eine Fehlerquelle.
    """

    once = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Rupture",
                uptime_percent=93.0,
            ),
        ),
        cooldown_usage=(
            CooldownUsage(
                actor_name="Silbermond",
                ability="Vendetta",
                cast_times=(20.0, 140.0),
                cooldown=120.0,
                category=CD_PERSONAL,
            ),
        ),
    ))

    twice = apply_spec_reference(once)

    assert twice.dot_uptimes == once.dot_uptimes

    assert twice.cooldown_usage == once.cooldown_usage


#
# --------------------------------------------------
# Cooldowns
# --------------------------------------------------
#


def test_unused_cooldowns_of_the_spec_appear_with_their_cooldown():

    snapshot = apply_spec_reference(_snapshot(
        cooldown_usage=(
            CooldownUsage(
                actor_name="Silbermond",
                ability="Vendetta",
                cast_times=(20.0,),
                cooldown=120.0,
                possible=2,
                category=CD_PERSONAL,
            ),
        ),
    ))

    rows = {
        usage.ability: usage
        for usage in snapshot.cooldowns_of("Silbermond")
    }

    blades = rows["Schattenklingen"]

    assert blades.uses == 0
    assert blades.cooldown == 180.0

    #
    # Auf Abklingzeit gehörende Cooldowns bekommen eine Obergrenze -
    # daraus entsteht die Quote "genutzt von möglich".
    #

    assert blades.possible == 2


def test_situational_cooldowns_carry_no_upper_bound():
    """
    Ein ungenutzter Mantel der Schatten ist kein verschenkter Einsatz,
    sondern ein Kampf, in dem er nicht gebraucht wurde. Eine
    Obergrenze würde daraus eine schlechte Quote machen - und träfe
    Tanks und Heiler am härtesten, die die meisten davon haben.
    """

    snapshot = apply_spec_reference(_snapshot(
        cooldown_usage=(
            CooldownUsage(
                actor_name="Silbermond",
                ability="Vendetta",
                cast_times=(20.0,),
                cooldown=120.0,
                possible=2,
                category=CD_PERSONAL,
            ),
        ),
    ))

    cloak = next(
        usage
        for usage in snapshot.cooldowns_of("Silbermond")
        if usage.ability == "Mantel der Schatten"
    )

    assert cloak.category == CD_DEFENSIVE
    assert cloak.possible == 0


def test_no_cooldown_row_is_invented_when_the_source_is_silent():

    snapshot = apply_spec_reference(_snapshot(
        dot_uptimes=(
            UptimeEntry(
                actor_name="Silbermond",
                ability="Blutung",
                uptime_percent=93.0,
            ),
        ),
    ))

    assert snapshot.cooldown_usage == ()


def test_the_live_cooldown_lists_use_the_same_names():

    from analyzer.models import CooldownState

    snapshot = apply_spec_reference(_snapshot(
        raid_cooldowns=(
            CooldownState(name="Rallying Cry", actor_name="Bramborn"),
        ),
    ))

    assert snapshot.raid_cooldowns[0].name == "Sammelschrei"


#
# --------------------------------------------------
# Hinweistexte
# --------------------------------------------------
#


def test_the_hint_names_what_the_spec_would_show():

    assert "Blutung" in reference_hint(ROGUE, UPTIME_DOT)

    assert "Vendetta" in cooldown_hint(ROGUE)

    #
    # Ohne bekannte Spezialisierung gibt es keinen Hinweis. Ein
    # erfundener Satz wäre schlechter als keiner.
    #

    assert reference_hint(None, UPTIME_DOT) == ""

    assert reference_hint(
        Actor("Fremd", "Unbekannt", "Unbekannt", ROLE_DPS),
        UPTIME_DOT,
    ) == ""


#
# --------------------------------------------------
# Grenze nach unten
# --------------------------------------------------
#


def test_a_snapshot_without_deep_analysis_stays_untouched():
    """
    Eine Quelle, die nur Summen liefert, bekommt keine Referenzzeilen
    angehängt: `has_analysis` wäre danach true, WeintTV würde seinen
    Erklärtext ausblenden und stattdessen lauter Nullen zeigen.
    """

    plain = RaidSnapshot(
        source_label="Bot",
        raid_size=25,
        pull_seconds=200.0,
        top_damage=(
            MetricEntry(actor=ROGUE, value=1000.0, total=200000.0, share=1.0),
        ),
    )

    assert apply_spec_reference(plain) is plain

    assert plain.has_analysis is False
