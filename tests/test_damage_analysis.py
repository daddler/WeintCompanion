"""
Einordnung des erhaltenen Schadens und die daraus abgeleiteten
Mechanikfehler.

Hier wird aus einer Zahl eine Wertung - entsprechend viel kann
schiefgehen. Zwei Fehler wären besonders schlimm und beide wären
unsichtbar:

1. Unbekanntes als "unvermeidbar" zu behandeln würde jeden Boss ohne
   Referenzdaten allen Spielern eine tadellose Bewertung geben.
2. Wenn Bot-Regel und abgeleiteter Fehler denselben Vorfall
   beschreiben und beide stehen bleiben, zählt die Academy ihn
   doppelt.
"""

from analyzer.analysis.damage import (
    build_damage_taken,
    classify_abilities,
    derive_mechanics,
    has_usable_classification,
    merge_mechanics,
)
from analyzer.data import avoidable
from analyzer.models import (
    MECHANIC_MOVEMENT,
    MECHANIC_SOURCE_BOT,
    MECHANIC_SOURCE_LOCAL,
    DamageTakenEntry,
    MechanicIssue,
)


#
# --------------------------------------------------
# Referenzdaten
# --------------------------------------------------
#


def test_an_unknown_ability_is_unknown_and_not_unavoidable():
    """
    Der wichtigste Einzelfall der ganzen Auswertung.

    Wäre Unbekanntes "unvermeidbar", stiege die Überlebensbewertung
    jedes Spielers auf die volle Punktzahl, sobald der Boss nicht in
    der Tabelle steht - und die Tabelle deckt anfangs nur eine
    Handvoll ab.
    """

    assert avoidable.verdict("Horridon", "Irgendwas Neues") == (
        avoidable.VERDICT_UNKNOWN
    )

    assert avoidable.verdict("Unbekannter Boss", "Double Swipe") == (
        avoidable.VERDICT_UNKNOWN
    )


def test_classification_never_raises_on_junk():

    for name, ability in (
        ("", ""),
        ("Horridon", ""),
        ("", "Double Swipe"),
        ("HORRIDON", "double swipe"),
    ):

        assert avoidable.verdict(name, ability) in (
            avoidable.VERDICT_AVOIDABLE,
            avoidable.VERDICT_UNAVOIDABLE,
            avoidable.VERDICT_UNKNOWN,
        )


def test_lookup_is_case_insensitive():

    assert avoidable.is_avoidable("horridon", "DOUBLE SWIPE") is True


def test_the_encounter_table_beats_the_global_one():

    #
    # "Melee" ist global als unvermeidbar hinterlegt.
    #

    assert avoidable.verdict("Horridon", "Melee") == (
        avoidable.VERDICT_UNAVOIDABLE
    )


def test_tanks_are_exempt_where_the_rule_says_so():
    """
    Einen Nahkampfangriff für den Tank "vermeidbar" zu nennen wäre
    unsinnig - er steht dort, weil das seine Aufgabe ist.
    """

    assert avoidable.verdict(
        "Horridon",
        "Triple Puncture",
        role="tank",
    ) == avoidable.VERDICT_UNAVOIDABLE


def test_every_rule_uses_a_real_mechanic_category():

    for name in avoidable.known_encounters():

        for rule in avoidable.rules_for(name):

            assert avoidable.mechanic_category(name, rule.ability)


#
# --------------------------------------------------
# Aufteilung
# --------------------------------------------------
#


def _rows():

    return (
        ("Double Swipe", 96000.0, 2, ""),
        ("Dire Call", 54000.0, 3, ""),
        ("Völlig Unbekannt", 20000.0, 1, ""),
    )


def test_the_three_buckets_add_up_to_the_total():

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    assert entry.total == 96000.0 + 54000.0 + 20000.0

    assert entry.avoidable == 96000.0
    assert entry.unavoidable == 54000.0
    assert entry.unclassified == 20000.0


def test_shares_stay_within_bounds():

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    assert 0.0 <= entry.avoidable_share <= 1.0
    assert 0.0 <= entry.classified_share <= 1.0


def test_abilities_are_sorted_by_damage():

    entries = classify_abilities("Horridon", _rows())

    amounts = [entry.amount for entry in entries]

    assert amounts == sorted(amounts, reverse=True)


def test_an_entirely_unclassified_row_is_not_usable_for_a_rating():
    """
    Sonst bildete die Überlebensbewertung nur die Lücken der Tabelle
    ab statt das Spiel des Spielers.
    """

    entry = build_damage_taken(
        "Dolchtanz",
        "Unbekannter Boss",
        _rows(),
    )

    assert entry.classified_share == 0.0

    assert has_usable_classification(entry) is False


def test_an_empty_entry_is_not_usable_either():

    assert has_usable_classification(None) is False

    assert has_usable_classification(DamageTakenEntry(actor_name="X")) is False


#
# --------------------------------------------------
# Ableitung und Zusammenführung
# --------------------------------------------------
#


def test_avoidable_hits_become_mechanic_issues():

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    issues = derive_mechanics((entry,), "Horridon")

    assert len(issues) == 1

    issue = issues[0]

    assert issue.actor_name == "Dolchtanz"
    assert issue.count == 2
    assert issue.source == MECHANIC_SOURCE_LOCAL
    assert issue.category

    #
    # Der Hinweis aus den Referenzdaten muss durchkommen - ohne ihn
    # weiß der Spieler nicht, was er anders machen soll.
    #

    assert "stehen bleiben" in issue.mechanic


def test_unavoidable_damage_produces_no_issue():

    entry = build_damage_taken(
        "Bramborn",
        "Horridon",
        (("Triple Puncture", 500000.0, 9, ""),),
        role="tank",
    )

    assert derive_mechanics((entry,), "Horridon") == ()


def test_the_bot_wins_when_both_describe_the_same_hit():
    """
    Der Bot schickt seine Regeln auf Deutsch, der Analyzer leitet aus
    englischen Fähigkeitsnamen ab. Ohne die Alias-Brücke stünde
    derselbe Vorfall zweimal in der Liste - und die Academy zählte ihn
    doppelt.
    """

    bot = (
        MechanicIssue(
            actor_name="Dolchtanz",
            mechanic="Doppelhieb nicht ausgewichen",
            count=2,
            category=MECHANIC_MOVEMENT,
            source=MECHANIC_SOURCE_BOT,
        ),
    )

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    derived = derive_mechanics((entry,), "Horridon")

    merged = merge_mechanics(bot, derived)

    assert len(merged) == 1

    assert merged[0].source == MECHANIC_SOURCE_BOT


def test_genuinely_different_issues_both_survive():

    bot = (
        MechanicIssue(
            actor_name="Dolchtanz",
            mechanic="Unterbrechung verpasst",
            count=1,
            source=MECHANIC_SOURCE_BOT,
        ),
    )

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    merged = merge_mechanics(bot, derive_mechanics((entry,), "Horridon"))

    assert len(merged) == 2


def test_the_same_ability_for_another_player_is_not_deduplicated():
    """
    Die Entdopplung darf nur je Spieler greifen - sonst verschwände
    der Fehler aller anderen, sobald der Bot ihn für einen gemeldet
    hat.
    """

    bot = (
        MechanicIssue(
            actor_name="Windschritt",
            mechanic="Doppelhieb nicht ausgewichen",
            count=1,
            source=MECHANIC_SOURCE_BOT,
        ),
    )

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    merged = merge_mechanics(bot, derive_mechanics((entry,), "Horridon"))

    assert len(merged) == 2


def test_bot_rows_come_first():
    """
    Handverlesene Regeln sind für die Raidleitung die verlässlicheren
    - sie gehören nach oben.
    """

    bot = (
        MechanicIssue(
            actor_name="Frostgrimm",
            mechanic="Unterbrechung verpasst",
            source=MECHANIC_SOURCE_BOT,
        ),
    )

    entry = build_damage_taken("Dolchtanz", "Horridon", _rows())

    merged = merge_mechanics(bot, derive_mechanics((entry,), "Horridon"))

    assert merged[0].source == MECHANIC_SOURCE_BOT


#
# --------------------------------------------------
# Abdeckung
# --------------------------------------------------
#


def test_every_siege_of_orgrimmar_boss_has_reference_data():
    """
    Ohne Referenzdaten bleibt der erhaltene Schaden eines Kampfes
    unklassifiziert - die Überlebensbewertung entfällt dann komplett,
    und der vermeidbare Schaden in WeintTVs Analyse bleibt leer.
    """

    from analyzer.data.encounters import (
        INSTANCE_ENCOUNTERS,
        SIEGE_OF_ORGRIMMAR,
    )

    missing = [
        name
        for name in INSTANCE_ENCOUNTERS[SIEGE_OF_ORGRIMMAR]
        if not avoidable.rules_for(name)
    ]

    assert missing == []


def test_every_boss_has_both_verdicts_represented():
    """
    Eine Tabelle mit ausschließlich vermeidbaren Fähigkeiten wäre
    verdächtig: irgendetwas an einem Boss ist immer unvermeidbar, und
    ohne diesen Anteil wirkt jeder Spieler schlechter als er ist.
    """

    for name in avoidable.known_encounters():

        verdicts = {rule.verdict for rule in avoidable.rules_for(name)}

        assert avoidable.VERDICT_AVOIDABLE in verdicts, name
        assert avoidable.VERDICT_UNAVOIDABLE in verdicts, name


def test_every_avoidable_rule_explains_what_to_do():
    """
    Ein Fehler ohne Hinweis ist ein Vorwurf ohne Lernwert - genau
    das, was die Academy vermeiden soll.
    """

    for name in avoidable.known_encounters():

        for rule in avoidable.rules_for(name):

            if rule.verdict != avoidable.VERDICT_AVOIDABLE:
                continue

            assert rule.note.strip(), (name, rule.ability)
            assert rule.label.strip(), (name, rule.ability)


def test_ability_labels_are_unambiguous():
    """
    Die Übersetzungstabelle für Bot-Texte wird aus den Labels
    abgeleitet. Zwei Fähigkeiten mit demselben deutschen Namen würden
    dort aufeinander abgebildet - und die Entdopplung träfe die
    falsche Zeile.
    """

    labels = {}

    for name in avoidable.known_encounters():

        for rule in avoidable.rules_for(name):

            if not rule.label:
                continue

            key = rule.label.strip().lower()

            assert labels.get(key, rule.ability) == rule.ability, key

            labels[key] = rule.ability


def test_the_alias_table_is_derived_from_the_labels():
    """
    Sie von Hand zu pflegen wäre bei über achtzig Regeln eine zweite
    Liste, die unweigerlich auseinanderliefe - und das Symptom wäre
    ein doppelt gezählter Fehler, den niemand als solchen erkennt.
    """

    for name in avoidable.known_encounters():

        for rule in avoidable.rules_for(name):

            if not rule.label:
                continue

            assert avoidable.alias_ability(rule.label) == rule.ability


#
# "Beute Pandarias" hat keinen einzelnen Boss und damit auch keinen
# klassischen Tankangriff - der Schaden kommt aus den Kisten und
# ihren Gegnern. Eine Fähigkeit dafür zu erfinden, nur damit die
# Tabelle gleichmäßig aussieht, wäre genau das Raten, das diese
# Referenzdaten vermeiden sollen.
#

WITHOUT_TANK_ABILITY = {"Spoils of Pandaria"}


def test_tank_abilities_are_marked_as_such_on_every_boss():
    """
    Ohne die Tank-Ausnahme würde jeder Tank für den Schaden bestraft,
    den anzunehmen seine Aufgabe ist.
    """

    for name in avoidable.known_encounters():

        if name in WITHOUT_TANK_ABILITY:
            continue

        assert any(
            rule.tank_exempt
            for rule in avoidable.rules_for(name)
        ), name
