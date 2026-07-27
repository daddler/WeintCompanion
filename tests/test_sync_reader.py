from addon.sync_reader import SyncReader


def _saved_variables_file(wow_path):
    file = (
        wow_path
        / "WTF"
        / "Account"
        / "TESTACCOUNT"
        / "SavedVariables"
        / "WeintCodex.lua"
    )

    file.parent.mkdir(parents=True, exist_ok=True)

    return file


def _valid_queue_lua(second_message_id="2"):
    return (
        'WeintCodex_SavedData = {\n'
        '["unrelated"] = "keep me",\n'
        '}\n'
        'WeintCompanionDB = {\n'
        '["version"] = 1,\n'
        '["lastId"] = 2,\n'
        '["queue"] = {\n'
        '{\n'
        '["id"] = 1,\n'
        '["created"] = 1000,\n'
        '["version"] = 1,\n'
        '["type"] = "loot",\n'
        '["payload"] = "hello",\n'
        '},\n'
        '{\n'
        f'["id"] = {second_message_id},\n'
        '["created"] = 1001,\n'
        '["version"] = 1,\n'
        '["type"] = "loot",\n'
        '["payload"] = "world",\n'
        '},\n'
        '},\n'
        '}\n'
    )


def test_get_messages_parses_valid_queue(tmp_path):
    file = _saved_variables_file(tmp_path)
    file.write_text(_valid_queue_lua(), encoding="utf-8")

    reader = SyncReader(tmp_path)
    messages = reader.get_messages()

    assert [m["id"] for m in messages] == [1, 2]
    assert messages[0]["payload"] == "hello"
    assert messages[1]["payload"] == "world"


def test_get_messages_skips_malformed_message_without_crashing(tmp_path):
    file = _saved_variables_file(tmp_path)
    # Zweite Nachricht hat eine kaputte id (z. B. durch einen Lese-
    # Zugriff mitten in einem Schreibvorgang) - darf nicht die
    # gesamte Verarbeitung zum Absturz bringen.
    file.write_text(_valid_queue_lua(second_message_id="not-a-number"), encoding="utf-8")

    reader = SyncReader(tmp_path)
    messages = reader.get_messages()

    assert [m["id"] for m in messages] == [1]


def test_read_recovers_from_unbalanced_braces(tmp_path):
    file = _saved_variables_file(tmp_path)
    # Datei bricht mitten in WeintCompanionDB ab (fehlende schließende
    # Klammer) - simuliert einen Lesezugriff während WoW gerade schreibt.
    file.write_text(
        'WeintCompanionDB = {\n["queue"] = {\n{\n["id"] = 1,\n',
        encoding="utf-8",
    )

    reader = SyncReader(tmp_path)

    assert reader.read() == ""
    assert reader.get_messages() == []


def test_remove_message_preserves_other_variable_and_is_atomic(tmp_path):
    file = _saved_variables_file(tmp_path)
    file.write_text(_valid_queue_lua(), encoding="utf-8")

    reader = SyncReader(tmp_path)
    result = reader.remove_message(1)

    assert result is True

    remaining = reader.get_messages()
    assert [m["id"] for m in remaining] == [2]

    # WeintCodex_SavedData (die andere Variable in derselben Datei)
    # muss unangetastet bleiben.
    assert '"keep me"' in file.read_text(encoding="utf-8")

    assert not file.with_suffix(file.suffix + ".tmp").exists()
