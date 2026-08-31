"""
Was das Exporter-Addon meldet - und was die Seite daraus macht.

Drei Fragen werden hier geprüft, und alle drei scheitern lautlos, wenn
sie falsch beantwortet werden:

* **Welche Spezialisierung ist das?** Das Addon schreibt `marksman`
  und `disc`, unsere Profile heissen `HUNTER_MARKSMANSHIP` und
  `PRIEST_DISCIPLINE`. Eine Ableitung, die bei zwei von 34
  danebengreift, führt genau dort ins Leere - und ein toter Knopf ist
  von einer nicht simmbaren Spec nicht zu unterscheiden.
* **Darf diese Ausrüstung an diese Seite?** Die Zweitspec derselben
  Klasse ja, ein anderer Charakter nein.
* **Warum steht nichts da?** Vier Gründe, vier Antworten - drei davon
  verlangen etwas völlig anderes vom Nutzer.
"""

import json
from pathlib import Path

from addon.wse_reader import (
    FOUND,
    NO_ADDON,
    NO_EXPORT,
    NO_WOW,
    parse_saved_variables,
)
from core.stat_weights import SPECS, spec as spec_of
from core.wowsims_export import (
    ADDON_URL,
    MIN_LEVEL,
    SPEC_KEYS,
    age_text,
    fits_spec,
    gap_text,
    parse_export,
)


SAVED = (
    Path(__file__).resolve().parent
    / "data"
    / "wowsims_exporter_savedvariables.lua"
).read_text(encoding="utf-8")


def newest():

    return parse_export(parse_saved_variables(SAVED)[0].data)


# --------------------------------------------------
# Die Zuordnung
# --------------------------------------------------


def test_alle_vierunddreissig_specs_sind_hinterlegt():

    assert len(SPEC_KEYS) == 34


def test_jeder_schluessel_hat_eine_sim_seite():
    """
    Sonst führte die Zuordnung auf einen Profilschlüssel, den
    `sim_url()` nicht kennt - und der Knopf ins Leere.
    """

    for key in SPEC_KEYS.values():
        assert spec_of(key) is not None, key


def test_die_zwei_fallen():
    """
    Die beiden Schreibweisen, wegen derer diese Tabelle keine
    Ableitung ist.
    """

    assert SPEC_KEYS[("hunter", "marksman")] == "HUNTER_MARKSMANSHIP"

    assert SPEC_KEYS[("priest", "disc")] == "PRIEST_DISCIPLINE"


def test_die_offensiven_tankprofile_kommen_nicht_vor():
    """
    Welche Haltung ein Tank spielt, kann das Addon nicht melden, und
    der Sim kennt den Unterschied auch nicht. Sie hier zu raten hiesse,
    eine eigene Gewichtung unter falscher Flagge zu füllen.
    """

    assert not [key for key in SPEC_KEYS.values() if key.endswith("OFFENSIVE")]


def test_die_klassenkuerzel_stimmen_mit_den_sim_seiten_ueberein():

    tokens = {entry.key: entry.class_token for entry in SPECS}

    for (char_class, _), key in SPEC_KEYS.items():
        assert tokens[key] == char_class.upper()


# --------------------------------------------------
# Lesen
# --------------------------------------------------


def test_ein_echter_export_wird_vollstaendig_gelesen():

    export = newest()

    assert export.full_name == "Njiah-OokOok"

    assert export.spec_key == "DEATHKNIGHT_BLOOD"

    assert export.level == 90

    assert export.talents == "231111"

    assert export.professions == ("Engineering", "Blacksmithing")

    assert export.usable

    assert export.problems == ()


def test_leere_plaetze_zaehlen_nicht_als_ausruestung():
    """
    16 Einträge, aber die Zweitwaffenhand eines Zweihandkriegers ist
    leer. Die Liste muss ihre Länge behalten (der Sim vergibt die
    Plätze der Reihe nach), gezählt wird sie nicht mit.
    """

    export = newest()

    assert len(export.items) == 16

    assert export.item_count == 15


def test_kein_export_ist_kein_kaputter_export():
    """
    `None` heisst "das war nichts, was dieses Addon geschrieben hat" -
    ein Unterschied, der zu einer ganz anderen Auskunft führt als
    "unvollständig".
    """

    assert parse_export("") is None

    assert parse_export("kein json") is None

    assert parse_export("[1,2,3]") is None

    assert parse_export('{"class":"mage"}') is None


def test_maengel_werden_benannt_statt_verworfen():

    export = parse_export(json.dumps({
        "class": "mage",
        "spec": "",
        "level": 34,
        "gear": {"items": [None, None]},
    }))

    assert export is not None

    assert not export.usable

    assert export.spec_key == ""

    assert any("Spezialisierung" in text for text in export.problems)

    assert any(str(MIN_LEVEL) in text for text in export.problems)

    assert any("Ausrüstungsteil" in text for text in export.problems)


def test_eine_unbekannte_spec_wird_gemeldet_und_nicht_geraten():

    export = parse_export(json.dumps({
        "class": "mage",
        "spec": "chronomant",
        "level": 90,
        "gear": {"items": [{"id": 5}]},
    }))

    assert export.spec_key == ""

    assert any("chronomant" in text.lower() for text in export.problems)

    assert export.usable


# --------------------------------------------------
# Passt das zusammen?
# --------------------------------------------------


def test_die_zweitspec_derselben_klasse_darf():

    assert fits_spec(newest(), "DEATHKNIGHT_FROST")


def test_die_offensive_haltung_darf_auch():
    """
    Ein eigenes Profil im Addon, aber dieselbe Klasse und dieselbe
    Rüstung.
    """

    assert fits_spec(newest(), "DEATHKNIGHT_BLOOD_OFFENSIVE")


def test_eine_fremde_klasse_darf_nicht():

    assert not fits_spec(newest(), "MAGE_FIRE")


def test_ohne_export_und_ohne_spec_darf_nichts():

    assert not fits_spec(None, "DEATHKNIGHT_BLOOD")

    assert not fits_spec(newest(), "GIBTESNICHT")


# --------------------------------------------------
# Wie alt und warum nichts
# --------------------------------------------------


def test_das_alter_wird_grob_genannt():
    """
    Das Alter ist die eigentliche Auskunft: WoW schreibt nur beim
    Neuladen und beim Ausloggen, eine Meldung von gestern beschreibt
    die Ausrüstung von gestern.
    """

    assert age_text(0) == "ohne Datum"

    assert age_text(1000, 1060) == "gerade eben"

    assert age_text(1000, 1000 + 600) == "vor 10 Minuten"

    assert age_text(1000, 1000 + 3600) == "vor einer Stunde"

    assert age_text(1000, 1000 + 4 * 3600) == "vor 4 Stunden"

    assert age_text(1000, 1000 + 86400) == "gestern"

    assert age_text(1000, 1000 + 5 * 86400) == "vor 5 Tagen"


def test_eine_verstellte_uhr_ergibt_kein_negatives_alter():
    """
    "Vor -3 Minuten" wäre die schlechtere Auskunft als das blosse
    Datum.
    """

    assert "vor" not in age_text(5000, 1000)


def test_jeder_grund_bekommt_seinen_eigenen_satz():

    reasons = [
        gap_text(NO_WOW, None),
        gap_text(NO_ADDON, None),
        gap_text(NO_EXPORT, None),
        gap_text(FOUND, None),
    ]

    assert len(set(reasons)) == 4

    assert "World of Warcraft" in reasons[0]

    assert "nicht installiert" in reasons[1]

    #
    # "Es fehlt" ohne Adresse ist eine Sackgasse, und der Desktop ist
    # die Seite, auf der man etwas herunterlädt.
    #

    assert ADDON_URL in reasons[1]

    assert "noch nichts gemeldet" in reasons[2]


def test_eine_leere_meldung_nennt_ihren_eigenen_mangel():

    export = parse_export(json.dumps({
        "class": "mage",
        "spec": "fire",
        "level": 90,
        "gear": {"items": []},
    }))

    text = gap_text(FOUND, export)

    assert "Ausrüstungsteil" in text
