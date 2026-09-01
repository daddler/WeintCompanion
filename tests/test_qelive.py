"""
QE Live - die Adresse für Heiler (`core/qelive.py`).

Die Zahlen hier sind dieselben, die `modules/qelive.lua` drüben aus
`data/qelive.lua` errechnet. Wo die beiden auseinanderlaufen,
widersprechen sich Spiel und Desktop bei einer Frage, die nur eine
Antwort hat - dieselbe Auflage wie beim Parser der Sim-Gewichte, und
derselbe Grund, warum `tests/test_stat_weights.py` und
`.github/tests/statweights_test.lua` dieselbe Sim-Ausgabe prüfen.

`.github/tests/qelive_test.lua` drüben hält dieselben Werte.
"""

from core import qelive


#
# Was drüben herauskommt. Ausgerechnet mit
# `lua5.1 .github/tests/qelive_test.lua .` und hier festgehalten -
# nicht abgeleitet, sonst prüfte der Test die eigene Ableitung.
#

EXPECTED = {
    "DRUID_RESTORATION": {
        "intellect": 100, "spirit": 84, "crit": 56, "haste": 58,
        "mastery": 73,
    },
    "PALADIN_HOLY": {
        "intellect": 100, "spirit": 59, "crit": 55, "haste": 44,
        "mastery": 90,
    },
    "PRIEST_DISCIPLINE": {
        "intellect": 100, "spirit": 34, "crit": 71, "mastery": 72,
    },
    "PRIEST_HOLY": {
        "intellect": 100, "spirit": 66, "crit": 56, "mastery": 68,
    },
    "SHAMAN_RESTORATION": {
        "intellect": 100, "spirit": 36, "crit": 69, "haste": 54,
        "mastery": 57,
    },
    "MONK_MISTWEAVER": {
        "intellect": 100, "spirit": 30, "crit": 64, "haste": 24,
        "mastery": 34,
    },
}


def test_dieselben_zahlen_wie_im_addon():

    assert {entry.key for entry in qelive.SPECS} == set(EXPECTED)

    for key, want in EXPECTED.items():

        assert qelive.spec(key).weights == want, key


def test_intelligenz_ist_ueberall_der_spitzenwert():
    """
    Skaliert wird auf "größtes Gewicht = 100", und bei jedem MoP-Heiler
    ist das die Intelligenz. Stünde dort etwas anderes, wäre entweder
    die Skalierung verrutscht oder eine Zahl falsch abgeschrieben.
    """

    for entry in qelive.SPECS:

        assert entry.weights["intellect"] == 100, entry.key

        assert max(entry.weights.values()) == 100, entry.key


def test_eine_luecke_traegt_keine_zahl():
    """
    Beide Priester führen drüben Tempo mit 0. Eine 0 hiesse im Addon
    "egal", und der Umschmiede-Planer schmiedete das Tempo restlos weg
    - deshalb steht der Wert gar nicht erst in der Gewichtung, sondern
    als Lücke daneben.
    """

    for entry in qelive.SPECS:

        for gap in entry.gaps:

            assert gap not in entry.weights, (entry.key, gap)


def test_unbekannte_spec_wird_nicht_geraten():

    assert qelive.spec("WARRIOR_ARMS") is None

    assert qelive.spec("") is None

    assert qelive.spec("druid_restoration") is not None    # Schreibweise egal

    assert not qelive.is_healer("MAGE_FIRE")


def test_die_saetze_stehen_nur_fuer_eine_gefuehrte_spec():
    """
    Ohne Eintrag gibt es keinen Satz - kein Text ins Blaue, sondern
    gar keiner. Der Aufrufer zeigt dann den wowsims-Zweig.
    """

    assert qelive.guidance(None) == ""

    assert qelive.weights_note(None) == ""

    assert qelive.gap_labels(None) == []


def test_der_satz_nennt_die_luecke_beim_namen():

    note = qelive.weights_note(qelive.spec("PRIEST_HOLY"))

    assert "Tempowertung" in note

    assert "Priorisierung" in note


def test_beta_wird_gesagt_und_nicht_verschwiegen():
    """
    QE Live führt zwei seiner Modelle selbst als Beta. Wer das nicht
    weiss, hält eine grobe Auskunft für eine genaue.
    """

    beta = {entry.key for entry in qelive.SPECS if entry.beta}

    assert beta == {"PALADIN_HOLY", "SHAMAN_RESTORATION"}

    assert "Beta" in qelive.weights_note(qelive.spec("PALADIN_HOLY"))

    assert "Beta" not in qelive.weights_note(qelive.spec("PRIEST_HOLY"))


def test_die_anleitung_nennt_den_weg_aus_dem_spiel():
    """
    QE Live nimmt die Ausrüstung nur als eingefügten Text an. Wer das
    nicht weiss, sucht auf der Seite einen Knopf, den es nicht geben
    kann - der Satz muss deshalb sagen, wo der Text herkommt.
    """

    text = qelive.guidance(qelive.spec("MONK_MISTWEAVER"))

    assert "Simmen" in text

    assert "/wc qe" in text


def test_kein_qt_und_kein_netz():
    """
    Dieselbe Auflage wie bei `roster_target()` und
    `build_profile_payload()`: welcher Satz dasteht, ist genau die
    Stelle, an der etwas falsch sein kann - und ein Fenster braucht
    man dafür nicht.
    """

    import ast
    import pathlib

    tree = ast.parse(
        pathlib.Path(qelive.__file__).read_text(encoding="utf-8"),
    )

    imported = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            imported.update(alias.name.split(".")[0] for alias in node.names)

        elif isinstance(node, ast.ImportFrom) and node.module:

            imported.add(node.module.split(".")[0])

    assert "PySide6" not in imported

    assert "httpx" not in imported
