"""
Die Sim-Gewichte: zerlegen, skalieren, weitergeben.

Geprüft wird hier, was schiefgehen kann, ohne dass es jemandem
auffällt - und das ist bei diesem Modul fast alles:

* eine Positionsliste, deren Reihenfolge sich verschoben hat, ordnet
  jede Zahl dem falschen Wert zu und sieht dabei vollständig aus,
* ein Komma, das für einen Tausender gehalten wird, macht aus 0,68
  eine Null,
* ein Profilschlüssel ohne Sim-Seite führte den Knopf auf die Seite
  einer fremden Spezialisierung,
* und ein Vorschlag, dessen Kennung sich bei gleichem Inhalt ändert,
  stünde im Spiel nach jedem Login erneut da.

Die Sim-Ausgabe unter `tests/data/` ist **unverändert** die, die
wowsims.com/mop nach *Suggest Reforges* für einen Blut-Todesritter
ausgibt. Ein nachgebautes Beispiel bestätigte nur die eigene Annahme
über jene Reihenfolge.
"""

from pathlib import Path

from core.stat_weights import (
    SPECS,
    STAT_ORDER,
    WeightSet,
    build_transfer,
    looks_like_sim,
    normalize,
    parse,
    payload,
    sim_url,
    spec,
)


SIM_OUTPUT = (
    Path(__file__).resolve().parent / "data" / "wowsims_mop_output.json"
).read_text(encoding="utf-8")


# --------------------------------------------------
# Die Sim-Ausgabe
# --------------------------------------------------


def test_sim_output_is_recognised_as_one():

    assert looks_like_sim(SIM_OUTPUT)


def test_sim_positions_are_the_documented_ones():
    """
    Die Zuordnung ist an der Klasse belegt (Todesritter: Stärke ja,
    Beweglichkeit und Intelligenz nein) und an der Grenze weiter
    unten. Läge eine Position woanders, käme hier Unsinn heraus.
    """

    result = parse(SIM_OUTPUT)

    assert result.ok

    assert result.source == "sim"

    assert result.weights["strength"] == 1

    assert "agility" not in result.weights

    assert "intellect" not in result.weights

    assert result.weights["stamina"] == 1.02

    assert result.weights["hit"] == 1.77

    assert result.weights["crit"] == 0.85

    assert result.weights["haste"] == 0.89

    assert result.weights["expertise"] == 1.5

    assert result.weights["dodge"] == 0.97

    assert result.weights["parry"] == 0.99

    assert result.weights["mastery"] == 0.98


def test_the_scaled_result_is_the_one_the_addon_computes():
    """
    Dieselbe Ausgabe muss hier und ingame dieselben Zahlen ergeben -
    sonst widersprechen sich Spiel und Desktop bei einer Frage, die
    nur eine Antwort hat. Die drei Werte stehen wortgleich im
    Testlauf des Addons (`.github/tests/statweights_test.lua`).
    """

    weights, _ = normalize(parse(SIM_OUTPUT).weights)

    assert weights["hit"] == 100

    assert weights["strength"] == 56

    assert weights["expertise"] == 85


def test_sim_class_is_reported():
    """
    Die Klasse ist die einzige Auskunft, an der auffällt, dass jemand
    die Ausgabe eines fremden Charakters eingefügt hat.
    """

    assert parse(SIM_OUTPUT).sim_class == "DEATHKNIGHT"


def test_sim_caps_are_read_but_stay_as_they_are():
    """
    Waffenkunde steht als Wertung (5100), die Trefferchance als
    Prozent (7,5). Umgerechnet wird erst für die Anzeige - und 5100
    bei 340 je Prozent sind die 15 %, die das Spec-Profil führt.
    """

    caps = {cap.stat: cap for cap in parse(SIM_OUTPUT).caps}

    assert caps["expertise"].rating == 5100

    assert round(caps["expertise"].percent, 1) == 15.0

    assert caps["hit"].pct == 7.5

    assert caps["hit"].percent == 7.5


def test_unknown_sim_fields_are_named_not_swallowed():
    """
    Angriffskraft und Rüstung gewichtet der Sim mit, WeintCodex kennt
    sie nicht. Wer nicht sieht, dass sie unter den Tisch fallen, hält
    das Ergebnis für vollständig.
    """

    ignored = parse(SIM_OUTPUT).ignored

    assert "Angriffskraft" in ignored

    assert "Rüstung" in ignored


def test_a_different_array_length_refuses_instead_of_guessing():
    """
    Der Kern dieses Lesewegs: verschiebt der Sim seine Reihenfolge,
    bekäme jeder Wert lautlos das Gewicht eines anderen. Dann wird
    nichts geraten und nichts gelesen.
    """

    shortened = SIM_OUTPUT.replace(
        '"epWeightsStats":{"apiVersion":3,'
        '"stats":[1,0,1.02,0,0,1.77,0.85,0.89,1.5,0.97,0.99,0.98,'
        '0.23,0,0,0,0,0.57,0.57,0,0,0]',
        '"epWeightsStats":{"apiVersion":3,"stats":[1,0,1.02,0,0,1.77]',
    )

    assert shortened != SIM_OUTPUT

    result = parse(shortened)

    assert not result.ok

    assert "6 Werte" in result.problem


def test_a_sim_output_is_never_handed_to_the_pair_reader():
    """
    Der Paarleser fände in den Schlüsselnamen und Zahlen einer
    Sim-Ausgabe durchaus etwas - die stille Falschauskunft, die es
    hier nicht geben darf. Ohne Gewichte gibt es deshalb einen
    Fehlertext und keine zusammengesuchte Gewichtung.
    """

    without_weights = SIM_OUTPUT.replace('"epWeightsStats"', '"epWeightsGone"')

    result = parse(without_weights)

    assert not result.ok

    assert not result.weights


# --------------------------------------------------
# Wertepaare
# --------------------------------------------------


def test_pairs_from_a_pasted_table():

    result = parse(
        "Beweglichkeit\t1.00\n"
        "CritRating\t0.55\n"
        "Haste Rating\t0.48\n"
    )

    assert result.ok

    assert result.source == "pairs"

    assert result.weights == {
        "agility": 1.0,
        "crit": 0.55,
        "haste": 0.48,
    }


def test_pairs_from_json():

    result = parse('{ "Agility": 1, "CritRating": 0.55, "Dps": 42000 }')

    assert result.weights["agility"] == 1.0

    assert result.weights["crit"] == 0.55

    assert "Dps" in result.ignored


def test_the_german_comma_is_a_decimal_point():
    """
    Ohne diese Unterscheidung wäre "Krit 0,68" der Wert 0 - der Wert
    fällt still auf null, und genau das fällt niemandem auf.
    """

    result = parse("Beweglichkeit 1,00 Krit 0,68")

    assert result.weights["agility"] == 1.0

    assert result.weights["crit"] == 0.68


def test_a_comma_next_to_a_decimal_point_separates_thousands():
    """
    Entschieden wird am ganzen Text: steht irgendwo ein Punkt
    zwischen Ziffern, schreibt diese Quelle Nachkommastellen mit
    Punkt.
    """

    result = parse("Agility 3,400.5 Crit 1,870")

    assert result.weights["agility"] == 3400.5

    assert result.weights["crit"] == 1870


def test_two_spellings_of_one_stat_are_not_added_up():

    result = parse("HitRating 0.5 SpellHitRating 0.9")

    assert result.weights["hit"] == 0.9


def test_text_without_a_single_pair_says_so():

    result = parse("Guten Morgen")

    assert not result.ok

    assert result.problem


def test_empty_input_says_so():

    assert parse("   ").problem


# --------------------------------------------------
# Skalieren
# --------------------------------------------------


def test_normalize_puts_the_largest_weight_at_100():

    weights, negatives = normalize(
        {"strength": 1.0, "crit": 0.55, "haste": 0.48},
    )

    assert weights == {"strength": 100, "crit": 55, "haste": 48}

    assert negatives == []


def test_normalize_keeps_the_ratios_regardless_of_scale():
    """
    Ein Maßstabswechsel, keine Wertung: dieselbe Gewichtung in
    anderen Zahlen muss dasselbe ergeben.
    """

    small, _ = normalize({"agility": 1.0, "crit": 0.5})

    large, _ = normalize({"agility": 3400.0, "crit": 1700.0})

    assert small == large


def test_negative_weights_become_zero_and_are_named():
    """
    Manche Skalen setzen einen Wert auf -1, um ihn zu meiden. Die
    Skala des Addons kennt kein "meiden", nur "egal".
    """

    weights, negatives = normalize({"agility": 1.0, "spirit": -1.0})

    assert "spirit" not in weights

    assert negatives == ["spirit"]


def test_nothing_usable_yields_no_weights():

    weights, _ = normalize({"agility": 0.0, "spirit": -1.0})

    assert weights == {}


# --------------------------------------------------
# Wohin der Knopf führt
# --------------------------------------------------


def test_every_spec_has_a_sim_page():

    for entry in SPECS:

        assert entry.url.startswith("https://www.wowsims.com/mop/")

        assert entry.path.count("/") == 1


def test_the_two_derivable_looking_paths_are_the_real_ones():
    """
    `HUNTER_BEASTMASTERY` hiesse abgeleitet "beastmastery" und heisst
    dort "beast_mastery", `DEATHKNIGHT` heisst "death_knight". Genau
    dafür ist die Zuordnung eine Tabelle.
    """

    assert sim_url("HUNTER_BEASTMASTERY").endswith("/hunter/beast_mastery/")

    assert sim_url("DEATHKNIGHT_BLOOD").endswith("/death_knight/blood/")


def test_the_offensive_tank_profiles_point_at_their_base_spec():
    """
    Der Sim kennt keine zwei Haltungen. Die Gewichte dieses Profils
    sind eigene, die Seite ist dieselbe.
    """

    assert sim_url("WARRIOR_PROTECTION_OFFENSIVE") == sim_url(
        "WARRIOR_PROTECTION",
    )


def test_an_unknown_spec_key_is_not_guessed():
    """
    Eine erfundene Zuordnung führte auf die Seite einer fremden Spec,
    und deren Ergebnis sähe genauso aus wie das richtige.
    """

    assert spec("PALADIN_SCHUTZHEILIG") is None

    assert sim_url("") is None


def test_all_thirtyfour_specs_are_there():
    """
    Fünf Profile sind die offensive Haltung der Tanks; sie zählen
    nicht als eigene Spezialisierung.
    """

    base = [entry for entry in SPECS if not entry.key.endswith("_OFFENSIVE")]

    assert len(base) == 34

    assert len({entry.key for entry in SPECS}) == len(SPECS)


# --------------------------------------------------
# Was ins Spiel geht
# --------------------------------------------------


def _set(**weights) -> WeightSet:

    return WeightSet(
        spec_key="DEATHKNIGHT_BLOOD",
        weights=weights or {"strength": 100, "hit": 60},
        character="Aldrin",
        created=1_756_000_000,
    )


def test_the_id_follows_the_content_not_the_clock():
    """
    Sie entscheidet im Spiel, ob ein Vorschlag neu ist. Zweimal
    dieselbe Gewichtung ist derselbe Vorschlag - sonst stünde nach
    jedem Login dieselbe Frage wieder da.
    """

    first = _set()

    later = WeightSet(
        spec_key=first.spec_key,
        weights=dict(first.weights),
        created=first.created + 9999,
    )

    assert first.id == later.id


def test_a_changed_weight_is_a_new_suggestion():

    assert _set(strength=100, hit=60).id != _set(strength=100, hit=61).id


def test_the_same_weights_for_another_spec_are_another_suggestion():

    other = WeightSet(spec_key="WARRIOR_ARMS", weights={"strength": 100})

    mine = WeightSet(spec_key="DEATHKNIGHT_BLOOD", weights={"strength": 100})

    assert other.id != mine.id


def test_the_transfer_string_is_a_wcimport_string():

    text = build_transfer(_set())

    assert text.startswith("WCIMPORT:SW:DEATHKNIGHT_BLOOD:")

    assert "strength|100" in text

    assert "hit|60" in text


def test_the_transfer_string_keeps_the_display_order():
    """
    Dieselbe Reihenfolge wie die Felder im Spiel - so steht die Zeile
    im Chat wie die Liste darunter.
    """

    text = build_transfer(
        WeightSet(spec_key="MAGE_FIRE", weights={"crit": 80, "intellect": 100}),
    )

    pairs = text.rsplit(":", 1)[1]

    assert pairs.index("intellect|100") < pairs.index("crit|80")


def test_a_character_name_cannot_take_the_string_apart():
    """
    Der Name kommt aus dem Spiel. Ein Doppelpunkt darin verschöbe
    jeden Abschnitt dahinter.
    """

    text = build_transfer(
        WeightSet(
            spec_key="MAGE_FIRE",
            weights={"intellect": 100},
            character="Bob:der|Erste,zwei",
        ),
    )

    assert text.count(":") == build_transfer(
        WeightSet(spec_key="MAGE_FIRE", weights={"intellect": 100}),
    ).count(":")


def test_the_payload_carries_the_whole_list():
    """
    Zugestellt wird immer alles: eine gelöschte Gewichtung
    verschwindet im Spiel allein dadurch, dass sie in der nächsten
    Zustellung fehlt.
    """

    data = payload([_set(), WeightSet(spec_key="MAGE_FIRE", weights={"intellect": 100})])

    assert len(data["sets"]) == 2

    assert data["sets"][0]["spec"] == "DEATHKNIGHT_BLOOD"

    assert data["sets"][0]["id"]


def test_the_payload_does_not_carry_the_caps():
    """
    Eine Grenze ist eine Aussage über das Spiel und steht im
    Spec-Profil des Addons. Sie mitzuschicken hiesse, dieselbe Frage
    an zwei Stellen zu beantworten.
    """

    blob = repr(payload([_set()]))

    assert "cap" not in blob.lower()


def test_the_display_order_matches_the_stat_table():

    assert set(STAT_ORDER) == set(normalize({key: 1.0 for key in STAT_ORDER})[0])
