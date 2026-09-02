import pytest

from core.lua_table import extract_variable_body, upsert_variable


def test_extract_variable_body_returns_none_when_missing():
    assert extract_variable_body("SomeOtherDB = {\n}\n", "WeintCompanionDB") is None


def test_extract_variable_body_finds_simple_block():
    text = 'WeintCompanionDB = {\n["lastId"] = 3,\n}\n'
    assert extract_variable_body(text, "WeintCompanionDB") == '\n["lastId"] = 3,\n'


def test_extract_variable_body_ignores_braces_inside_strings():
    # Ein Payload-String, der selbst "{"/"}" enthält, darf das
    # Klammer-Zählen nicht durcheinanderbringen.
    text = (
        'WeintCompanionDB = {\n'
        '["payload"] = "{\\"nested\\": {}}",\n'
        '}\n'
    )

    body = extract_variable_body(text, "WeintCompanionDB")

    assert body == '\n["payload"] = "{\\"nested\\": {}}",\n'


def test_extract_variable_body_stops_at_the_right_variable_when_multiple_exist():
    # Zwei Variablen in derselben SavedVariables-Datei - nur der
    # Block der angefragten Variable darf zurückgegeben werden.
    text = (
        'WeintCodex_SavedData = {\n["foo"] = "bar",\n}\n'
        'WeintCompanionDB = {\n["lastId"] = 7,\n}\n'
    )

    assert extract_variable_body(text, "WeintCompanionDB") == '\n["lastId"] = 7,\n'
    assert extract_variable_body(text, "WeintCodex_SavedData") == '\n["foo"] = "bar",\n'


def test_extract_variable_body_raises_on_unbalanced_braces():
    text = 'WeintCompanionDB = {\n["lastId"] = 3,\n'  # keine schließende Klammer

    with pytest.raises(ValueError):
        extract_variable_body(text, "WeintCompanionDB")


def test_upsert_variable_creates_new_block(tmp_path):
    path = tmp_path / "WeintCodex.lua"

    upsert_variable(path, "WeintCompanionDB", '["lastId"] = 1,\n')

    text = path.read_text(encoding="utf-8")
    assert extract_variable_body(text, "WeintCompanionDB") == '\n["lastId"] = 1,\n'


def test_upsert_variable_replaces_only_targeted_block(tmp_path):
    path = tmp_path / "WeintCodex.lua"
    path.write_text(
        'WeintCodex_SavedData = {\n["foo"] = "bar",\n}\n'
        'WeintCompanionDB = {\n["lastId"] = 1,\n}\n',
        encoding="utf-8",
    )

    upsert_variable(path, "WeintCompanionDB", '["lastId"] = 2,\n')

    text = path.read_text(encoding="utf-8")

    # Die andere Variable in derselben Datei bleibt unangetastet.
    assert extract_variable_body(text, "WeintCodex_SavedData") == '\n["foo"] = "bar",\n'
    assert extract_variable_body(text, "WeintCompanionDB") == '\n["lastId"] = 2,\n'


def test_upsert_variable_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "WeintCodex.lua"

    upsert_variable(path, "WeintCompanionDB", '["lastId"] = 1,\n')

    assert not (tmp_path / "WeintCodex.lua.tmp").exists()
    assert path.exists()


# --------------------------------------------------
# Ein Schreibvorgang, der WoWs eigenen nicht überholt
# --------------------------------------------------
#
# `upsert_variable()` ist ein Lesen, Ändern, Zurückschreiben auf einer
# Datei, die WoW gehört: WoW hält seine SavedVariables im
# Arbeitsspeicher und schreibt sie bei /reload und beim Abmelden
# vollständig zurück. Fällt dieser Schreibvorgang zwischen unser Lesen
# und unser Ersetzen, wäre alles weg, was in der Sitzung dazugekommen
# ist - Bossnotizen, Twinkliste, Fortschritt -, ersetzt durch den Stand
# vom letzten Anmelden. Nichts daran fiele auf: die Datei wäre gültiges
# Lua, vollständig, nur älter.


def _saved_variables(path, notiz):

    path.write_text(
        "WeintCodex_SavedData = {\n"
        f'["bossNotes"] = {{ ["Malkorok"] = "{notiz}" }},\n'
        "}\n"
        "WeintCompanionInboxDB = {\n"
        '["queue"] = {\n},\n'
        "}\n",
        encoding="utf-8",
    )


def test_upsert_variable_meldet_dass_geschrieben_wurde(tmp_path):

    file = tmp_path / "WeintCodex.lua"

    _saved_variables(file, "alt")

    assert upsert_variable(file, "WeintCompanionInboxDB", "") is True


def test_upsert_variable_ueberschreibt_keinen_fremden_schreibvorgang(
    tmp_path, monkeypatch
):
    """
    Schreibt WoW die Datei, während wir sie zusammenbauen, wird nicht
    ersetzt - und die Notiz, die in dieser Sitzung dazugekommen ist,
    bleibt stehen.
    """

    from core import lua_table

    file = tmp_path / "WeintCodex.lua"

    _saved_variables(file, "alt")

    echt = lua_table._stamp

    aufrufe = {"n": 0}

    def dazwischenfunken(path):

        aufrufe["n"] += 1

        #
        # Zwei Aufrufe je Anlauf: einmal vor dem Lesen, einmal
        # unmittelbar vor dem Ersetzen. Genau dazwischen - also vor dem
        # zweiten - meldet WoW sich zu Wort.
        #

        if aufrufe["n"] == 2:
            _saved_variables(file, "in dieser Sitzung getippt")

        return echt(path)

    monkeypatch.setattr(lua_table, "_stamp", dazwischenfunken)

    assert upsert_variable(
        file, "WeintCompanionInboxDB", '["queue"] = {},\n'
    ) is True

    #
    # Der erste Anlauf wurde verworfen, der zweite hat die neue Fassung
    # gelesen: die Notiz steht noch da, und die Zustellung ist
    # trotzdem drin.
    #

    text = file.read_text(encoding="utf-8")

    assert "in dieser Sitzung getippt" in text

    assert "WeintCompanionInboxDB" in text

    assert aufrufe["n"] >= 4


def test_upsert_variable_gibt_auf_statt_zu_ueberschreiben(
    tmp_path, monkeypatch
):
    """
    Wer den Zeitraum dreimal hintereinander trifft, schreibt gerade
    fortlaufend. Dann wird nichts geschrieben und `False` gemeldet -
    die Zustellung Richtung Addon geht im nächsten Takt erneut hinaus
    und liegt ausserdem als Live-Brücke im Addon-Ordner.
    """

    from core import lua_table

    file = tmp_path / "WeintCodex.lua"

    _saved_variables(file, "wichtig")

    zaehler = {"n": 0}

    def immer_anders(path):

        zaehler["n"] += 1

        return (zaehler["n"], zaehler["n"])

    monkeypatch.setattr(lua_table, "_stamp", immer_anders)

    assert upsert_variable(file, "WeintCompanionInboxDB", "") is False

    assert "wichtig" in file.read_text(encoding="utf-8")

    assert not (tmp_path / "WeintCodex.lua.tmp").exists()
