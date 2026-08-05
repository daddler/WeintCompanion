"""
Die Spezialisierungstabelle.

Sie schließt einen Fehler, der lange nicht auffiel, weil er nichts
kaputt machte: der Lektionskatalog ist mit **deutschen**
Spezialisierungsnamen geschlüsselt, WarcraftLogs liefert **englische**.
Im Echtbetrieb traf deshalb kein einziger Katalogschlüssel zu, und der
Unterschied zu "für diese Spezialisierung ist nichts hinterlegt" war
in der Oberfläche nicht zu sehen.

Der zweite Teil wiegt für die Bewertung noch schwerer: aus der
Spezialisierung folgt die Rolle. Ohne sie konnte die App Tanks
grundsätzlich nicht erkennen - und ein als Schadensausteiler geführter
Tank wird gegen die Schadensrangliste gemessen.
"""

from analyzer.academy.lessons import SPEC_LESSONS
from analyzer.data import specs
from analyzer.models import ROLE_DPS, ROLE_HEALER, ROLE_TANK
from analyzer.providers.warcraftlogs_payload import build_actor


def test_all_thirtyfour_specialisations_are_present():
    """
    Mists of Pandaria hat vierunddreißig Spezialisierungen - elf
    Klassen zu drei, der Druide zu vier.
    """

    assert len(specs.SPECS) == 34

    assert len(specs.specs_for_class("Druid")) == 4

    for class_name in (
        "Death Knight",
        "Hunter",
        "Mage",
        "Monk",
        "Paladin",
        "Priest",
        "Rogue",
        "Shaman",
        "Warlock",
        "Warrior",
    ):
        assert len(specs.specs_for_class(class_name)) == 3, class_name


def test_the_roles_are_complete():

    assert len(specs.specs_for_role(ROLE_TANK)) == 5

    assert len(specs.specs_for_role(ROLE_HEALER)) == 6

    assert len(specs.specs_for_role(ROLE_DPS)) == 23


def test_english_names_translate_to_the_catalogue_spelling():

    assert specs.normalize_spec("Warrior", "Protection") == "Schutz"

    assert specs.normalize_spec("DeathKnight", "Blood") == "Blut"

    assert specs.normalize_spec("Monk", "Brewmaster") == "Braumeister"

    assert specs.normalize_spec("Hunter", "Beast Mastery") == "Tierherrschaft"


def test_german_names_survive_unchanged():
    """
    Die Simulation und der Katalog schreiben bereits deutsch - eine
    Übersetzung darf daraus nichts anderes machen.
    """

    for spec in specs.SPECS:

        assert specs.normalize_spec(spec.class_name, spec.name) == spec.name


def test_unknown_specialisations_are_passed_through():
    """
    Dieselbe Regel wie bei den Klassennamen: ein künftiger Patch soll
    einen Spieler nicht aus der Auswertung entfernen, nur weil die
    Tabelle ihn noch nicht kennt.
    """

    assert specs.normalize_spec("Demon Hunter", "Havoc") == "Havoc"

    assert specs.role_for_spec("Demon Hunter", "Havoc") == ""


def test_ambiguous_names_need_the_class():
    """
    "Frost" gibt es beim Todesritter und beim Magier, "Schutz" beim
    Krieger und beim Paladin. Ohne Klasse darf nur geantwortet werden,
    wo sich die Kandidaten einig sind.
    """

    assert specs.find("", "Frost") is None

    assert specs.role_for_spec("", "Frost") == ROLE_DPS

    assert specs.role_for_spec("", "Protection") == ROLE_TANK

    assert specs.role_for_spec("", "Restoration") == ROLE_HEALER


def test_the_payload_translates_and_derives_the_role():
    """
    Der eigentliche Zweck: eine Bot-Antwort in der Schreibweise von
    WarcraftLogs muss im Katalog ankommen - und ein Tank ohne
    gemeldete Rolle muss als Tank erkannt werden.
    """

    actor = build_actor({
        "name": "Bramborn",
        "class": "Warrior",
        "spec": "Protection",
        "damage_total": 400_000.0,
    })

    assert actor.spec == "Schutz"
    assert actor.role == ROLE_TANK


def test_a_role_sent_by_the_bot_still_wins():
    """
    Nur der Bot kennt die Rangliste, aus der die Rolle stammt - die
    Spezialisierung ist der Ersatzweg, nicht der Vorrang.
    """

    actor = build_actor({
        "name": "Ausnahme",
        "class": "Warrior",
        "spec": "Protection",
        "role": "dps",
    })

    assert actor.role == ROLE_DPS


def test_every_catalogue_key_exists_in_the_table():
    """
    Der Test, der die stille Fehlpaarung künftig verhindert: jeder
    Schlüssel des Lektionskatalogs muss eine Spezialisierung sein, die
    es wirklich gibt - sonst ist die Lektion für niemanden
    erreichbar.
    """

    for class_name, spec_name in SPEC_LESSONS:

        if not spec_name:
            continue

        assert specs.find(class_name, spec_name) is not None, (
            class_name,
            spec_name,
        )
