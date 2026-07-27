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
