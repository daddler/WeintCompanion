"""
Die Zustellung Richtung Addon.

Der wichtigste Test hier ist der letzte: was Python schreibt, muss
WoWs Lua tatsächlich einlesen können. Ein Tippfehler im Serialisierer
fällt sonst erst im Spiel auf - und dort nicht als Fehlermeldung,
sondern als komplett unlesbare SavedVariables-Datei, die auch die
Daten aller anderen Features mitnimmt.

Daneben die Eigenschaft, wegen der AddonInbox überhaupt existiert:
zwei Absender im selben Sync-Durchlauf dürfen sich nicht gegenseitig
überschreiben.
"""

import shutil
import subprocess

import pytest

from addon.addon_inbox import AddonInbox
from addon.inbox_writer import InboxWriter
from core.lua_table import extract_variable_body, quote_lua_string, to_lua
from core.version import VERSION


class _Logger:

    def info(self, message):
        pass

    def error(self, message):
        pass

    def success(self, message):
        pass

    def warning(self, message):
        pass


class _State:

    def __init__(self, wow_path):
        self.wow_path = wow_path


class _Manager:

    def __init__(self, wow_path):
        self.state = _State(wow_path)
        self.logger = _Logger()


@pytest.fixture
def wow_path(tmp_path):
    """
    Eine WoW-Installation mit bereits vorhandener SavedVariables-Datei.
    """

    saved = (
        tmp_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables"
    )

    saved.mkdir(parents=True)

    (saved / "WeintCodex.lua").write_text(
        'WeintCodex_SavedData = {\n["twinks"] = {\n},\n}\n',
        encoding="utf-8",
    )

    return tmp_path


def _inbox_body(wow_path) -> str:

    file = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )

    return extract_variable_body(
        file.read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    ) or ""


# --------------------------------------------------
# Writer
# --------------------------------------------------


def test_writer_keeps_string_payloads_as_before(wow_path):

    InboxWriter(wow_path).send_batch([
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    body = _inbox_body(wow_path)

    assert '["type"] = "raid_import"' in body
    assert '["payload"] = "WCIMPORT:RAIDWED:x"' in body


def test_writer_serialises_table_payloads(wow_path):

    InboxWriter(wow_path).send_batch([
        {"type": "weinttv_report", "payload": {"pull": 7, "kill": False}},
    ])

    body = _inbox_body(wow_path)

    assert '["pull"] = 7' in body
    assert '["kill"] = false' in body


def test_writer_leaves_other_variables_alone(wow_path):

    InboxWriter(wow_path).send_batch([
        {"type": "raid_import", "payload": "x"},
    ])

    file = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )

    # WoW schreibt alle SavedVariables eines Addons in dieselbe Datei -
    # der Spielstand daneben darf dabei nicht verloren gehen.
    assert "WeintCodex_SavedData" in file.read_text(encoding="utf-8")


# --------------------------------------------------
# Kanäle
# --------------------------------------------------


def test_channels_do_not_overwrite_each_other(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    inbox.publish("analysis", [
        {"type": "weinttv_report", "payload": {"pull": 7}},
    ])

    body = _inbox_body(wow_path)

    # Genau der Fall, für den es die Kanäle gibt: beide Absender
    # laufen nacheinander im selben Worker.
    assert "raid_import" in body
    assert "weinttv_report" in body


def test_publishing_a_channel_again_replaces_only_that_channel(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [{"type": "raid_import", "payload": "alt"}])
    inbox.publish("analysis", [{"type": "weinttv_report", "payload": {"pull": 1}}])
    inbox.publish("roster", [{"type": "raid_import", "payload": "neu"}])

    body = _inbox_body(wow_path)

    assert "neu" in body
    assert '"alt"' not in body
    assert "weinttv_report" in body


def test_clearing_a_channel_keeps_the_others(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [{"type": "raid_import", "payload": "x"}])
    inbox.publish("analysis", [{"type": "weinttv_report", "payload": {"pull": 1}}])

    inbox.clear("analysis")

    body = _inbox_body(wow_path)

    assert "raid_import" in body
    assert "weinttv_report" not in body


def test_publish_reports_failure_without_a_wow_path():

    inbox = AddonInbox(_Manager(None))

    assert inbox.publish("roster", [{"type": "x", "payload": "y"}]) is False


# --------------------------------------------------
# Gegenprobe mit einem echten Lua-Interpreter
# --------------------------------------------------


LUA = shutil.which("lua5.1") or shutil.which("lua")


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_written_file_is_valid_lua_and_round_trips(wow_path):
    """
    Die Datei wird von WoWs Lua eingelesen - also mit echtem Lua
    gegenprüfen, statt sich auf Zeichenketten-Vergleiche zu verlassen.
    """

    payload = {
        "text": 'Anführungszeichen " und Backslash \\ und Zeilen\numbruch',
        "umlaute": "Überleben, Fähigkeit, Größe",
        "zahlen": [1, -2, 3.5],
        "wahrheit": True,
        "leer": [],
        "verschachtelt": {"a": {"b": ["c"]}},
        "kein_wert": None,
    }

    InboxWriter(wow_path).send_batch([
        {"type": "weinttv_report", "payload": payload},
    ])

    file = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )

    script = f"""
        dofile({quote_lua_string(str(file))})
        local msg = WeintCompanionInboxDB.queue[1]
        assert(msg.type == "weinttv_report", "Typ falsch")
        local p = msg.payload
        assert(type(p) == "table", "Payload ist keine Tabelle")
        assert(p.text:find('"', 1, true), "Anfuehrungszeichen verloren")
        assert(p.text:find("\\\\", 1, true), "Backslash verloren")
        assert(p.text:find("\\n", 1, true), "Zeilenumbruch verloren")
        assert(p.umlaute == "Überleben, Fähigkeit, Größe", "Umlaute verloren")
        assert(#p.zahlen == 3 and p.zahlen[2] == -2, "Zahlen falsch")
        assert(p.wahrheit == true, "Wahrheitswert falsch")
        assert(#p.leer == 0, "Leere Liste falsch")
        assert(p.verschachtelt.a.b[1] == "c", "Verschachtelung falsch")
        assert(p.kein_wert == nil, "None haette entfallen muessen")
        assert(WeintCodex_SavedData ~= nil, "Fremde Variable verloren")
        print("ok")
    """

    result = subprocess.run(
        [LUA, "-e", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_control_characters_do_not_break_the_file(wow_path):
    """
    Ein Steuerzeichen aus einer Fremdquelle (Bossname, Fähigkeitstext)
    darf die Datei nicht zerlegen - dort hängen auch die Variablen
    anderer Features drin.
    """

    InboxWriter(wow_path).send_batch([
        {"type": "weinttv_report", "payload": {"boss": "Horr\x07idon\x00"}},
    ])

    file = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )

    result = subprocess.run(
        [LUA, "-e", f"dofile({quote_lua_string(str(file))}) print('ok')"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_to_lua_rejects_unsupported_types():

    # Lieber ein Fehler beim Bauen als eine unlesbare Datei im Spiel.
    with pytest.raises(TypeError):
        to_lua({"wann": object()})


# --------------------------------------------------
# Versionsmarke
# --------------------------------------------------
#
# Das Addon sendet seit WeintCodex 1.3.3.0 eine Nachricht
# "character_report" (wer ist gerade angemeldet). Eine Companion, die
# den Typ nicht kennt, würde ihn an den Bot schicken; der antwortet
# nicht mit Erfolg, die Nachricht bliebe liegen und der Nutzer bekäme
# alle fünf Sekunden einen Fehler. Das Addon liest deshalb diese
# Marke und sendet erst ab 1.7.0.
#
# Eine blosse Empfehlung zur Update-Reihenfolge hätte das nicht
# verhindert - Addon und App werden unabhängig aktualisiert.
# --------------------------------------------------


def test_die_companion_version_steht_in_der_inbox(wow_path):

    InboxWriter(wow_path).send_batch([
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    body = extract_variable_body(
        (
            wow_path
            / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
        ).read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    )

    assert f'["companionVersion"] = "{VERSION}"' in body


def test_die_marke_steht_auch_bei_leerer_warteschlange(wow_path):
    """
    Sonst erschiene sie erst, wenn zufällig etwas zuzustellen ist -
    und das Addon bliebe bis dahin stumm, obwohl die App neu genug
    ist.
    """

    InboxWriter(wow_path).send_batch([])

    body = extract_variable_body(
        (
            wow_path
            / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
        ).read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    )

    assert "companionVersion" in body


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_das_addon_liest_die_marke_als_zeichenkette(wow_path):

    InboxWriter(wow_path).send_batch([])

    file = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )

    script = f"""
        dofile({quote_lua_string(str(file))})
        local v = WeintCompanionInboxDB.companionVersion
        assert(type(v) == "string", "Version ist keine Zeichenkette")
        local major, minor = v:match("^v?(%d+)%.(%d+)")
        assert(major and minor, "Version nicht zerlegbar: " .. tostring(v))
        print("ok")
    """

    result = subprocess.run([LUA, "-e", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
