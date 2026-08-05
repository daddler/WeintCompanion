"""
Die Spec-Referenztabelle ist eine Datentabelle, und Datentabellen
altern still: eine Spezialisierung, die nie nachgetragen wurde, sieht
in der Oberfläche exakt so aus wie eine, über die die Datenquelle
nichts liefert. Genau diese Verwechslung war der Anlass für die
Tabelle - sie darf hier nicht wieder entstehen.

Geprüft werden deshalb Vollständigkeit und die Böden, unter die keine
Spezialisierung fallen darf, nicht einzelne Zahlenwerte.
"""

import pytest

from analyzer.data import class_abilities, player_abilities, specs
from analyzer.models import (
    CD_PERSONAL,
    ROLE_HEALER,
    ROLE_TANK,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    Actor,
)


def _entry(spec):

    return class_abilities.for_spec(spec.class_name, spec.name)


#
# --------------------------------------------------
# Vollständigkeit
# --------------------------------------------------
#


def test_every_spec_of_the_expansion_is_covered():

    missing = [
        (spec.class_name, spec.name)
        for spec in specs.SPECS
        if _entry(spec) is None
    ]

    assert missing == []

    assert len(class_abilities.SPEC_ABILITIES) == len(specs.SPECS)


def test_every_spec_brings_cooldowns_that_are_not_optional():
    """
    Optional heißt talentabhängig und wird nie ergänzt. Eine Spec, die
    ausschließlich optionale Einträge hätte, bekäme deshalb nie eine
    einzige Referenzzeile - und wäre von "nicht gepflegt" nicht zu
    unterscheiden.
    """

    for spec in specs.SPECS:

        entry = _entry(spec)

        assert entry.cooldowns, spec

        assert any(
            not cooldown.optional
            for cooldown in entry.cooldowns
        ), spec


def test_tanks_carry_their_active_mitigation():
    """
    Die aktive Schadensminderung ist die eigentliche
    Leistungskennzahl eines Tanks (siehe `_uptime_parts` im
    Evaluator). Fehlt sie, wird ein Tank wieder allein an seiner
    Aktivzeit gemessen.
    """

    for spec in specs.specs_for_role(ROLE_TANK):

        buffs = _entry(spec).auras_of(UPTIME_BUFF)

        assert any(not aura.optional for aura in buffs), spec


def test_healers_carry_at_least_one_hot():

    for spec in specs.specs_for_role(ROLE_HEALER):

        hots = _entry(spec).auras_of(UPTIME_HOT)

        assert any(not aura.optional for aura in hots), spec


def test_damage_specs_have_either_a_dot_or_a_self_buff():
    """
    Nicht jede Schadensspezialisierung hat einen DoT (Arkan hat
    keinen), aber keine hat *nichts* - sonst bliebe die
    Rotationsbewertung bei der Aktivzeit allein stehen.
    """

    for spec in specs.SPECS:

        if spec.role in (ROLE_TANK, ROLE_HEALER):
            continue

        entry = _entry(spec)

        rows = (
            entry.auras_of(UPTIME_DOT)
            + entry.auras_of(UPTIME_BUFF)
            + tuple(
                cooldown
                for cooldown in entry.cooldowns
                if cooldown.category == CD_PERSONAL and not cooldown.optional
            )
        )

        assert rows, spec


#
# --------------------------------------------------
# Innere Widerspruchsfreiheit
# --------------------------------------------------
#


def test_every_ability_has_both_names_and_at_least_one_spell_id():

    for entry in class_abilities.SPEC_ABILITIES:

        for ability in (*entry.auras, *entry.cooldowns):

            assert ability.english.strip(), (entry.spec, ability)

            assert ability.german.strip(), (entry.spec, ability)

            assert ability.spell_ids, (entry.spec, ability)

            assert all(
                isinstance(spell_id, int) and spell_id > 0
                for spell_id in ability.spell_ids
            ), (entry.spec, ability)


def test_a_spell_id_never_names_two_abilities_within_one_spec():
    """
    Zwei Einträge mit derselben ID wären beim Nachschlagen ein
    Münzwurf - und der Verlierer wäre dauerhaft unsichtbar.
    """

    for entry in class_abilities.SPEC_ABILITIES:

        seen: dict[int, str] = {}

        for ability in (*entry.auras, *entry.cooldowns):

            for spell_id in ability.spell_ids:

                previous = seen.setdefault(spell_id, ability.english)

                assert previous == ability.english, (entry.spec, spell_id)


def test_each_ability_is_found_by_id_and_by_both_names():

    for entry in class_abilities.SPEC_ABILITIES:

        for kind, abilities in (
            (class_abilities.KIND_AURA, entry.auras),
            (class_abilities.KIND_COOLDOWN, entry.cooldowns),
        ):

            for ability in abilities:

                assert class_abilities.match(
                    entry, spell_id=ability.spell_ids[0], prefer=kind,
                ) is ability

                assert class_abilities.match(
                    entry, ability.english, prefer=kind,
                ) is ability

                assert class_abilities.match(
                    entry, ability.german, prefer=kind,
                ) is ability

                #
                # Schreibweise ist egal: Groß-/Kleinschreibung,
                # Doppelpunkte und Leerzeichen schreibt nicht jede
                # Quelle gleich.
                #

                assert class_abilities.match(
                    entry,
                    ability.english.upper().replace(":", ""),
                    prefer=kind,
                ) is ability


def test_expected_uptimes_stay_within_a_hundred_percent():

    for entry in class_abilities.SPEC_ABILITIES:

        for aura in entry.auras:

            assert 0.0 <= aura.expected_percent <= 100.0, (entry.spec, aura)


#
# --------------------------------------------------
# Anschluss an die übrigen Tabellen
# --------------------------------------------------
#


def test_translations_reach_the_lesson_matching():
    """
    Der Lektionskatalog nennt Fähigkeiten englisch, ein deutscher
    Bericht liefert sie deutsch. Ohne diesen Anschluss wäre jedes
    Kriterium, das eine Fähigkeit nennt, in einem deutschen Log
    dauerhaft "keine Daten" - lautlos.
    """

    for english, german in class_abilities.translations().items():

        for name in german:

            assert player_abilities.matches(english, name), (english, name)


def test_the_spec_follows_from_class_and_role_when_it_is_missing():
    """
    Der Live-Endpunkt schickt für Heiler regelmäßig keine
    Spezialisierung. Wo Klasse und Rolle zusammen eindeutig sind, ist
    das kein Grund, den halben Raid ohne Referenz zu lassen.
    """

    healing_druid = Actor(
        name="Elvenne",
        class_name="Druid",
        spec="",
        role=ROLE_HEALER,
    )

    found = class_abilities.for_actor(healing_druid)

    assert found is not None
    assert found.spec == "Wiederherstellung"

    #
    # Beim Priester ist es das nicht - Disziplin und Heilig heilen
    # beide. Lieber keine Aussage als eine falsche.
    #

    healing_priest = Actor(
        name="Miraia",
        class_name="Priest",
        spec="",
        role=ROLE_HEALER,
    )

    assert class_abilities.for_actor(healing_priest) is None


def test_display_name_is_language_independent():

    assert class_abilities.display_name("Shield Block") == "Schildblock"

    assert class_abilities.display_name(spell_id=132404) == "Schildblock"

    #
    # Unbekanntes bleibt, wie es gemeldet wurde - eine Fähigkeit, die
    # diese Tabelle noch nicht kennt, darf nicht verschwinden.
    #

    assert class_abilities.display_name("Zauber XY") == "Zauber XY"


# =========================
# DIE GEMELDETEN DOTS
# =========================
#
# Die Rückmeldung, die diese Runde ausgelöst hat, war eine Liste von
# achtzehn DoTs mit dem Satz "sind noch immer nicht aufgeführt". Der
# Bot schickt sie inzwischen mitsamt Spell-ID; hier steht die andere
# Hälfte der Kette: dass diese Tabelle sie auch erkennt, richtig
# einsortiert und auf einen deutschen Namen bringt.
#
# Die IDs sind dieselben, die der Bot in services/warcraftlogs_auras.py
# führt. Laufen die beiden auseinander, fällt das hier auf - und nicht
# erst als fehlende Zeile in der Oberfläche, wo eine nicht erkannte
# Aura genauso aussieht wie eine, die der Spieler nie benutzt hat.

REPORTED_DOTS = {
    8050: "Flammenschock",
    348: "Feuerbrand",
    1079: "Blutung",                 # Rip
    1943: "Blutung",                 # Rupture
    1822: "Krallenhieb",
    55095: "Frostfieber",
    55078: "Blutseuche",
    8921: "Mondfeuer",
    93402: "Sonnenfeuer",
    44457: "Lebende Bombe",
    114923: "Nethersturm",
    118253: "Schlangengift",
    3674: "Schwarzer Pfeil",
    980: "Agonie",
    172: "Verderbnis",
    30108: "Instabiles Gebrechen",
    589: "Schattenwort: Schmerz",
    34914: "Vampirberührung",
    31803: "Tadel",
}


@pytest.mark.parametrize("spell_id", sorted(REPORTED_DOTS))
def test_every_reported_dot_is_known_by_spell_id(spell_id):
    """
    Die Spell-ID ist der einzige Weg ohne Sprache - und seit der Bot
    sie mitschickt der Weg, über den die Erkennung tatsächlich läuft.
    """

    assert class_abilities.aura_kind(spell_id=spell_id) == UPTIME_DOT


@pytest.mark.parametrize("spell_id,german", sorted(REPORTED_DOTS.items()))
def test_every_reported_dot_resolves_to_its_german_name(spell_id, german):

    assert class_abilities.display_name(spell_id=spell_id) == german


@pytest.mark.parametrize("spell_id", sorted(REPORTED_DOTS))
def test_every_reported_dot_belongs_to_at_least_one_spec(spell_id):
    """
    In der Tabelle zu stehen genügt nicht: die Aura muss einer
    Spezialisierung zugeordnet sein, sonst findet `match()` sie für
    keinen Spieler und `reference_hint()` nennt sie nie.
    """

    owners = [
        (spec.class_name, spec.spec)
        for spec in class_abilities.SPEC_ABILITIES
        for aura in spec.auras
        if spell_id in aura.spell_ids
    ]

    assert owners, f"Spell-ID {spell_id} gehört zu keiner Spezialisierung"


def test_no_spell_id_is_shared_by_two_different_abilities():
    """
    Zwei Fähigkeiten unter einer ID sind ein stiller Fehler: die zweite
    bekommt Namen und Abklingzeit der ersten. Genau daran hingen zwei
    echte Fälle - Göttliche Gunst lief als Zornige Vergeltung, und der
    Gedankenschinder wurde gegen die dreifache Abklingzeit des
    Schattengeists gemessen und damit dauerhaft als "kaum genutzt"
    bewertet.
    """

    owners: dict[int, str] = {}
    clashes = []

    for spec in class_abilities.SPEC_ABILITIES:

        for row in list(spec.auras) + list(spec.cooldowns):

            for spell_id in row.spell_ids:

                if spell_id in owners and owners[spell_id] != row.english:
                    clashes.append((spell_id, owners[spell_id], row.english))

                owners.setdefault(spell_id, row.english)

    assert clashes == []
