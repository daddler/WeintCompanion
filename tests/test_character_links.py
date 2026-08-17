"""
Tests fuer die Charakterzuordnung (core/character_links.py).

Der reine Teil: was der Bot liefert, in Zeilen uebersetzen, und den
einen Satz bilden, der ueber der Liste steht. Kein Qt, kein httpx -
aus demselben Grund wie bei roster_target() und
build_profile_payload(): die Entscheidung, was als Luecke gilt, ist
die Stelle, an der etwas falsch sein kann.
"""

import pytest

from core.character_links import (
    ANY_CLASS,
    SOURCE_COMPANION,
    SOURCE_DISCORD,
    SOURCE_RAIDLEAD,
    LinkRow,
    Overview,
    SignupRow,
    class_label,
    format_character,
    parse_overview,
    summary_text,
)


def body(signups=(), links=(), raid_id=3):

    return {
        "status": "ok",
        "raid_id": raid_id,
        "signups": list(signups),
        "links": list(links),
    }


def signup(**overrides):

    row = {
        "discord_id": "111",
        "discord_name": "Bob",
        "class": "WARRIOR",
        "role": "TANK",
        "name": "Njiah",
        "realm": "",
        "source": SOURCE_COMPANION,
        "resolved": True,
    }

    row.update(overrides)

    return row


# =========================
# DARSTELLUNG
# =========================

def test_charakter_ohne_realm():
    assert format_character("Njiah", "") == "Njiah"


def test_charakter_mit_realm_wie_die_einladung():
    """
    Ingame wird "Name-Realm" eingeladen - genau so soll es dastehen.
    """

    assert format_character("Njiah", "OokOok") == "Njiah-OokOok"


def test_charakter_ohne_namen_ist_leer():
    assert format_character("", "OokOok") == ""


def test_klassenbeschriftung():
    assert class_label("WARRIOR") == "Krieger"
    assert class_label("priest") == "Priester"


def test_leerer_token_ist_der_platzhalter():
    assert class_label(ANY_CLASS) == "Jede Klasse"


def test_unbekannte_klasse_ist_keine_klasse():
    """
    "UNKNOWN" ist der Token einer Anmeldung ohne gesetzte Klasse - er
    braucht einen eigenen, ehrlichen Text statt der Wortmarke.
    """

    assert class_label("UNKNOWN") == "Klasse unbekannt"


def test_fremder_token_wird_durchgereicht():
    """
    Nicht durch einen geratenen ersetzen - dieselbe Regel wie bei den
    Klassennamen im Analyzer.
    """

    assert class_label("DEMONHUNTER") == "DEMONHUNTER"


# =========================
# ANTWORT LESEN
# =========================

def test_antwort_wird_in_zeilen_uebersetzt():

    overview = parse_overview(body(
        signups=[signup()],
        links=[{"discord_id": "111", "class": "WARRIOR", "name": "Njiah", "realm": "OokOok"}],
    ))

    assert overview.ok
    assert overview.has_raid
    assert len(overview.signups) == 1
    assert overview.signups[0].character == "Njiah"
    assert overview.signups[0].class_name == "Krieger"
    assert overview.links[0].character == "Njiah-OokOok"


def test_kein_dict_ist_ein_grund_kein_absturz():

    overview = parse_overview("kaputt")

    assert not overview.ok
    assert overview.reason


def test_fehlende_bloecke_ergeben_leere_listen():
    """
    Eine unvollstaendige Antwort ist kein Fehler, sondern fuehrt zu
    weniger Zeilen - wie bei jedem Bot-Payload.
    """

    overview = parse_overview({"status": "ok"})

    assert overview.ok
    assert overview.signups == ()
    assert overview.links == ()
    assert not overview.has_raid


def test_zeile_ohne_discord_id_wird_verworfen():
    """
    Sie waere weder zuzuordnen noch zu loeschen.
    """

    overview = parse_overview(body(signups=[signup(discord_id="")]))

    assert overview.signups == ()


def test_handeintrag_ohne_namen_wird_verworfen():

    overview = parse_overview(body(links=[{"discord_id": "111", "name": "  "}]))

    assert overview.links == ()


def test_fehlender_anzeigename_faellt_auf_die_id_zurueck():
    """
    Kein Anzeigename heisst, dass der Bot den Account im Server nicht
    mehr findet. Die ID benennt ihn dann noch - ein leeres Feld saehe
    aus wie ein Zeichenfehler.
    """

    overview = parse_overview(body(signups=[signup(discord_name="")]))

    assert overview.signups[0].discord_name == "111"


def test_muell_in_den_listen_wird_uebersprungen():

    overview = parse_overview(body(signups=["nope", 5, signup()], links=[None]))

    assert len(overview.signups) == 1
    assert overview.links == ()


# =========================
# OFFENE ZUORDNUNGEN
# =========================

def test_offene_zeilen_werden_erkannt():

    overview = parse_overview(body(signups=[
        signup(discord_id="1", source=SOURCE_DISCORD, resolved=False),
        signup(discord_id="2"),
    ]))

    assert [row.discord_id for row in overview.open_rows] == ["1"]
    assert overview.resolved_count == 1


def test_handeintraege_je_account():

    overview = parse_overview(body(links=[
        {"discord_id": "1", "name": "A", "class": "WARRIOR"},
        {"discord_id": "2", "name": "B"},
    ]))

    assert [row.name for row in overview.links_for("1")] == ["A"]
    assert overview.links_for("2")[0].is_placeholder


def test_403_ist_keine_stoerung():
    """
    Fehlt die Rolle, ist das eine Antwort und kein Fehler - die Seite
    erklaert dann, wofuer sie da waere.
    """

    overview = Overview(forbidden=True)

    assert not overview.ok
    assert not overview.reason


# =========================
# DER SATZ UEBER DER LISTE
# =========================

def test_ohne_raid_wird_keine_null_behauptet():
    """
    "0 offen" waere die falscheste aller Antworten, wo gar nichts
    gezaehlt wurde.
    """

    text = summary_text(Overview(raid_id=None))

    assert "0" not in text
    assert "keine Anmeldung" in text


def test_ohne_anmeldungen_sagt_es_das():

    text = summary_text(parse_overview(body(signups=[])))

    assert "niemand" in text


def test_alles_zugeordnet():

    text = summary_text(parse_overview(body(signups=[signup()])))

    assert "erreicht jeden" in text


def test_offene_zuordnungen_stehen_zuerst_im_satz():
    """
    Das ist die Frage, mit der man die Seite oeffnet.
    """

    text = summary_text(parse_overview(body(signups=[
        signup(discord_id="1", source=SOURCE_DISCORD, resolved=False),
        signup(discord_id="2"),
    ])))

    assert text.startswith("1 von 2")
    assert "erreicht sie nicht" in text


# =========================
# HERKUNFT
# =========================

@pytest.mark.parametrize("source,expected", [
    (SOURCE_RAIDLEAD, "Von Hand gesetzt"),
    (SOURCE_COMPANION, "Vom Spieler gemeldet"),
    (SOURCE_DISCORD, "Kein Charakter bekannt"),
])
def test_herkunft_wird_benannt(source, expected):

    row = SignupRow(discord_id="1", discord_name="Bob", name="X", source=source)

    assert row.source_label == expected


def test_unbekannte_herkunft_wird_durchgereicht():
    """
    Ein neuer Wert vom Bot soll sichtbar sein statt still zu
    verschwinden - dieselbe Regel wie bei CombatEvent.kind.
    """

    row = SignupRow(discord_id="1", discord_name="Bob", name="X", source="neu")

    assert row.source_label == "neu"


def test_platzhalter_erkennen():

    assert LinkRow(discord_id="1", name="A").is_placeholder
    assert not LinkRow(discord_id="1", name="A", class_token="MAGE").is_placeholder
