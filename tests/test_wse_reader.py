"""
Die SavedVariables des WowSimsExporter lesen.

Eine fremde Datei, die wir nicht in der Hand haben: geschrieben von
WoW, gefüllt über AceDB, und der eigentliche Inhalt ist ein
JSON-Text, der als **Lua-String** darin steht - also mit jedem
Anführungszeichen maskiert. Wer da eine Maskierung verliert, bekommt
kein Fehlerbild, sondern JSON, das sich nicht mehr lesen lässt.

Die Testdatei unter `tests/data/` ist in genau der Form gebaut, in der
WoW schreibt: Tabulatoren, `["Schlüssel"] = Wert`, maskierte
Anführungszeichen und ein Schrägstrich, der aus der JSON-Bibliothek
des Addons als `\\/` kommt.
"""

from pathlib import Path

from addon.wse_reader import (
    FOUND,
    NO_ADDON,
    NO_EXPORT,
    NO_WOW,
    WseReader,
    parse_saved_variables,
    read_record,
    unescape,
)


SAVED = (
    Path(__file__).resolve().parent
    / "data"
    / "wowsims_exporter_savedvariables.lua"
).read_text(encoding="utf-8")


def install(root: Path, *, addon=True, saved=SAVED, account="ACC#1"):
    """
    Eine WoW-Installation, so weit sie für diese Frage nötig ist.
    """

    if addon:
        (root / "Interface" / "AddOns" / "WowSimsExporter").mkdir(
            parents=True, exist_ok=True,
        )

    folder = root / "WTF" / "Account" / account / "SavedVariables"

    folder.mkdir(parents=True, exist_ok=True)

    if saved is not None:
        (folder / "WowSimsExporter.lua").write_text(saved, encoding="utf-8")

    return root


# --------------------------------------------------
# Lua-Kleinkram
# --------------------------------------------------


def test_maskierung_wird_zurueckgenommen():

    assert unescape(r'a\"b') == 'a"b'

    assert unescape(r"a\\b") == "a\\b"

    assert unescape(r"a\nb") == "a\nb"

    assert unescape(r"a\65b") == "aAb"


def test_verschachtelte_tabellen_werden_uebersprungen():
    """
    Gebraucht werden drei flache Werte. Ein vollständiger Lua-Parser
    wäre für sie deutlich mehr Fläche, auf der etwas falsch sein kann -
    aber eine Tabelle dazwischen darf den Leser nicht aus dem Tritt
    bringen.
    """

    record = read_record(
        '["name"] = "Njiah", ["extra"] = { ["a"] = 1, }, '
        '["timestamp"] = 17, ["flag"] = true,'
    )

    assert record["name"] == "Njiah"

    assert record["timestamp"] == 17

    assert record["flag"] is True

    assert "a" not in record


def test_klammern_in_einem_string_zaehlen_nicht_mit():
    """
    Der Export ist JSON und besteht zum guten Teil aus geschweiften
    Klammern. Zählte der Leser sie mit, endete jeder Eintrag an der
    falschen Stelle.
    """

    record = read_record(
        r'["data"] = "{\"gear\":{\"items\":[{\"id\":1}]}}", '
        r'["timestamp"] = 5,'
    )

    assert record["data"] == '{"gear":{"items":[{"id":1}]}}'

    assert record["timestamp"] == 5


# --------------------------------------------------
# Die Datei
# --------------------------------------------------


def test_eintraege_kommen_neueste_zuerst():

    entries = parse_saved_variables(SAVED)

    assert [entry.name for entry in entries] == [
        "Njiah-Ook Ook",
        "Cynsaria-Ook Ook",
    ]

    assert entries[0].stamp > entries[1].stamp


def test_der_export_kommt_als_lesbares_json_heraus():

    import json

    payload = json.loads(parse_saved_variables(SAVED)[0].data)

    assert payload["class"] == "deathknight"

    assert len(payload["gear"]["items"]) == 16


def test_eine_fremde_variable_wird_nicht_mitgelesen():
    """
    WoW schreibt alle SavedVariables eines Addons in eine Datei -
    dieselbe Vorsicht wie in `core/lua_table.extract_variable_body()`.
    """

    entries = parse_saved_variables(
        'WSEFREMD = {\n\t["savedCharacters"] = {\n\t\t{\n'
        '\t\t\t["data"] = "x",\n\t\t\t["timestamp"] = 9,\n\t\t},\n'
        "\t},\n}\n"
    )

    assert entries == []


def test_derselbe_eintrag_in_zwei_profilen_zaehlt_einmal():
    """
    AceDB kopiert beim Anlegen eines Profils. Zweimal derselbe
    Charakter mit derselben Uhrzeit ist einmal derselbe - sonst stünde
    er doppelt in der Liste und man suchte den Unterschied.
    """

    doubled = SAVED.replace(
        '\t\t["Default"] = {',
        '\t\t["Zweit"] = {\n\t\t\t["savedCharacters"] = {\n\t\t\t\t{\n'
        '\t\t\t\t\t["timestamp"] = 1787000000,\n'
        '\t\t\t\t\t["name"] = "Njiah-Ook Ook",\n'
        '\t\t\t\t\t["data"] = "{}",\n\t\t\t\t},\n\t\t\t},\n\t\t},\n'
        '\t\t["Default"] = {',
        1,
    )

    entries = parse_saved_variables(doubled)

    assert [entry.name for entry in entries].count("Njiah-Ook Ook") == 1


def test_ein_eintrag_ohne_daten_wird_uebergangen():

    entries = parse_saved_variables(
        'WSEDB = {\n\t["profiles"] = {\n\t\t["Default"] = {\n'
        '\t\t\t["savedCharacters"] = {\n\t\t\t\t{\n'
        '\t\t\t\t\t["timestamp"] = 3,\n\t\t\t\t},\n\t\t\t},\n'
        "\t\t},\n\t},\n}\n"
    )

    assert entries == []


# --------------------------------------------------
# Warum nichts da ist
# --------------------------------------------------


def test_ohne_wow_pfad_ist_der_grund_das_fehlende_wow():

    assert WseReader(None).read().reason == NO_WOW


def test_addon_fehlt(tmp_path):

    install(tmp_path, addon=False, saved=None)

    assert WseReader(tmp_path).read().reason == NO_ADDON


def test_addon_da_aber_nie_exportiert(tmp_path):
    """
    Der Unterschied zu "nicht installiert" ist der ganze Punkt: hier
    ist einmal Neuladen die Abhilfe, dort muss erst etwas
    heruntergeladen werden.
    """

    install(tmp_path, saved=None)

    assert WseReader(tmp_path).read().reason == NO_EXPORT


def test_gefunden(tmp_path):

    install(tmp_path)

    lookup = WseReader(tmp_path).read()

    assert lookup.reason == FOUND

    assert lookup.newest.name == "Njiah-Ook Ook"


def test_zwei_konten_werden_zusammengelegt(tmp_path):
    """
    Wer zwei WoW-Konten spielt, hat zwei Dateien - und die neuere
    Meldung ist die richtige, egal aus welcher sie kommt.
    """

    install(tmp_path, account="ERSTES")

    install(
        tmp_path,
        account="ZWEITES",
        saved=SAVED.replace("1787000000", "1799000000", 1)
              .replace("Njiah", "Zweitkonto"),
    )

    lookup = WseReader(tmp_path).read()

    assert lookup.newest.name.startswith("Zweitkonto")

    assert len(lookup.files) == 2


def test_eine_halb_geschriebene_datei_nimmt_die_seite_nicht_mit(tmp_path):
    """
    WoW schreibt die Datei beim Ausloggen neu. Wird sie genau dabei
    gelesen, fehlt die schliessende Klammer - dann ist die Antwort
    "nichts gefunden" und kein Absturz. Beim nächsten Lesen steht sie
    wieder.
    """

    install(tmp_path, saved=SAVED[: len(SAVED) // 2])

    assert WseReader(tmp_path).read().reason == NO_EXPORT
