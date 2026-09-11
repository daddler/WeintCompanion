"""
Die Cooldown-Rechnung - vier gemeldete Fehler, vier Prüfungen.

Alle vier hatten dieselbe Ursache: die Frage "wie gut wurden die
Cooldowns genutzt" wurde an mehreren Stellen unabhängig beantwortet.
Seit 3.6.0 rechnet sie `analyzer/analysis/cooldowns.py` einmal, und
diese Datei hält die Rechnung fest.
"""

from analyzer.analysis import cooldowns as cd
from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    CooldownUsage,
    HeroismWindow,
)


# --------------------------------------------------
# Mögliche Einsätze
# --------------------------------------------------


def test_a_perfect_run_does_not_produce_a_phantom_missed_use():
    """
    Der gemeldete Fall. Sechs Minuten Kampf, ein
    Drei-Minuten-Cooldown: möglich sind zwei Einsätze (0:00 und
    3:00). Die alte Rechnung (`dauer // cd + 1`) kam auf drei, und
    wer alles richtig machte, las "2 von 3" und "1 verschenkt".
    """

    assert cd.possible_uses(360.0, 180.0) == 2


def test_the_window_just_after_a_multiple_does_not_count():
    """
    Ein Einsatz, der rechnerisch fünf Sekunden vor Schluss noch
    bereit geworden wäre, ist keine verpasste Nutzung.
    """

    assert cd.possible_uses(365.0, 180.0) == 2

    #
    # Mit genug Restzeit dagegen schon.
    #

    assert cd.possible_uses(400.0, 180.0) == 3


def test_a_fight_shorter_than_the_cooldown_allows_exactly_one_use():

    assert cd.possible_uses(90.0, 180.0) == 1

    assert cd.possible_uses(5.0, 180.0) == 1


def test_without_a_known_cooldown_there_is_no_upper_bound():
    """
    0 heisst "unbekannt" und nie "keine möglichen Einsätze" - aus
    einer Datenlücke darf keine Quote von 0 % entstehen.
    """

    assert cd.possible_uses(300.0, 0.0) == 0

    assert cd.possible_uses(0.0, 180.0) == 0


# --------------------------------------------------
# Einordnung
# --------------------------------------------------


def test_a_defensive_cooldown_is_recognised_in_both_languages():
    """
    Der zweite gemeldete Fehler: die alte Namensliste im Payload war
    englisch und kannte keinen einzigen Defensivcooldown. Jeder nicht
    gedrückte Schildwall galt damit als verschenkter Einsatz - und
    zwar am härtesten für Tanks.
    """

    assert cd.category_of("Shield Wall") == CD_DEFENSIVE

    assert cd.category_of("Schildwall") == CD_DEFENSIVE

    assert cd.category_of("", 871) == CD_DEFENSIVE


def test_raid_and_heal_cooldowns_keep_their_drawer():

    assert cd.category_of("Sammelschrei") == CD_RAID

    assert cd.category_of("Rallying Cry") == CD_RAID

    #
    # Seelenruhe steht bei mehreren Spezialisierungen und einmal als
    # Raid-, einmal als Heilcooldown. Spec-unabhängig entscheidet der
    # erste Treffer - für die Frage, um die es hier geht, sind beide
    # dasselbe: keine Nutzungsquote.
    #

    assert not cd.counts_towards_usage(cd.category_of("Seelenruhe"))

    assert cd.category_of("Tranquility") in (CD_RAID, CD_HEAL)


def test_the_source_wins_when_it_says_something():

    assert cd.category_of("Schildwall", 0, CD_RAID) == CD_RAID

    #
    # Unsinn aus der Quelle gewinnt nicht.
    #

    assert cd.category_of("Schildwall", 0, "quatsch") == CD_DEFENSIVE


def test_an_unknown_ability_is_assumed_to_go_on_cooldown():

    assert cd.category_of("Erfundene Fähigkeit") == CD_PERSONAL


def test_only_on_cooldown_abilities_enter_the_quota():

    assert cd.counts_towards_usage(CD_PERSONAL)

    assert not cd.counts_towards_usage(CD_DEFENSIVE)

    assert not cd.counts_towards_usage(CD_RAID)

    assert not cd.counts_towards_usage(CD_HEAL)


# --------------------------------------------------
# Ausrichtung auf das Burstfenster
# --------------------------------------------------


def _usage(cast_times, cooldown, name="Berserkerwut"):

    return CooldownUsage(
        actor_name="Njiah",
        ability=name,
        cast_times=tuple(cast_times),
        cooldown=cooldown,
        possible=3,
    )


def test_a_short_cooldown_used_often_is_not_punished_for_the_window():
    """
    Der dritte gemeldete Fehler. Ein Ein-Minuten-Cooldown, sechsmal
    korrekt gedrückt, davon einer im Heldentum: der alte Anteil
    (1 von 6) ergab einen Stern für perfektes Spiel. Kurze Cooldowns
    gehören auf Abklingzeit und zählen hier gar nicht mit.
    """

    windows = (HeroismWindow(start=120.0, end=160.0),)

    hits, chances = cd.burst_alignment(
        _usage((0.0, 60.0, 122.0, 180.0, 240.0, 300.0), 60.0),
        windows,
    )

    assert (hits, chances) == (0, 0)


def test_a_major_cooldown_ready_during_the_window_is_an_opportunity():

    windows = (HeroismWindow(start=120.0, end=160.0),)

    hits, chances = cd.burst_alignment(
        _usage((130.0,), 180.0),
        windows,
    )

    assert (hits, chances) == (1, 1)

    #
    # Und eine verpasste Gelegenheit ist eine, in der er bereit war:
    # ein Einsatz weit vor dem Fenster, der bis zum Fensterende
    # wieder oben ist.
    #

    hits, chances = cd.burst_alignment(
        _usage((0.0, 300.0), 180.0),
        (HeroismWindow(start=200.0, end=240.0),),
    )

    assert (hits, chances) == (0, 1)


def test_a_major_cooldown_still_on_cooldown_is_no_missed_opportunity():
    """
    Wer seinen Drei-Minuten-Cooldown beim Pull drückt, hat ihn im
    Fenster bei 2:00 zwangsläufig unten - das ist der Preis eines
    ebenfalls richtigen Einsatzes und kein Fehler.
    """

    windows = (HeroismWindow(start=100.0, end=140.0),)

    hits, chances = cd.burst_alignment(
        _usage((0.0,), 180.0),
        windows,
    )

    assert (hits, chances) == (0, 0)


def test_without_a_window_nothing_is_counted():

    hits, chances = cd.burst_alignment(_usage((10.0,), 180.0), ())

    assert (hits, chances) == (0, 0)


# --------------------------------------------------
# Lücken
# --------------------------------------------------


def test_the_gap_says_when_the_cooldown_was_ready_and_unused():

    gaps = cd.ready_gaps((0.0, 200.0), 60.0, 400.0)

    #
    # Nach 0:00 ist er ab 1:00 bereit und kommt erst bei 3:20 wieder;
    # danach ab 4:20, also erst nach dem Kampfende.
    #

    assert [(round(gap.start), round(gap.until)) for gap in gaps] == [
        (60, 200),
        (260, 390),
    ]


def test_without_a_known_cooldown_there_is_no_gap():
    """
    Eine geschätzte Abklingzeit wäre eine erfundene Aussage über
    verschenkte Zeit.
    """

    assert cd.ready_gaps((10.0,), 0.0, 400.0) == ()


def test_short_gaps_are_noise_and_stay_out():
    """
    Fünf Sekunden zwischen "wieder bereit" und dem nächsten Einsatz
    sind keine verschenkte Zeit - niemand drückt auf die Sekunde.
    """

    gaps = cd.ready_gaps((0.0, 65.0), 60.0, 200.0)

    assert [round(gap.start) for gap in gaps] == [125]

    #
    # Und in einem Kampf, der gleich danach endet, bleibt gar nichts
    # übrig.
    #

    assert cd.ready_gaps((0.0, 65.0), 60.0, 80.0) == ()
