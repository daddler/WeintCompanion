"""
Die Zustellung, die ein /reload überlebt.

Der Weg über WeintCompanionInboxDB kann eine laufende Spielsitzung
nicht erreichen: WoW schreibt seine SavedVariables bei /reload aus
dem Arbeitsspeicher zurück und liest sie erst danach wieder ein -
alles, was wir in der Zwischenzeit hineingeschrieben haben, ist
vorher schon gelöscht. Die Live-Brücke ist eine Lua-Datei im
Addon-Ordner, die WoW nur liest.

Geprüft wird hier vor allem das, was im Spiel als "die Daten sind
weg" auffiele und sonst nirgends:

* die Datei muss echtes Lua sein (sie liegt im Addon-Ordner - ein
  Syntaxfehler dort ist ein Ladefehler des Addons),
* `writtenAt` darf nur wandern, wenn sich die Nachrichten wirklich
  geändert haben, sonst arbeitet das Addon bei jedem /reload dieselbe
  Zustellung erneut ein,
* und nach einem Addon-Update, das den leeren Auslieferungsstand
  darüber entpackt, muss sie von selbst zurückkommen.
"""

import shutil
import subprocess

import pytest

from addon.addon_inbox import AddonInbox
from addon.live_bridge import BRIDGE_DIR, BRIDGE_NAME, LiveBridgeWriter
from core.lua_table import quote_lua_string
from core.version import VERSION

LUA = shutil.which("lua5.1") or shutil.which("lua")


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
    Eine WoW-Installation mit installiertem Addon und vorhandener
    SavedVariables-Datei.
    """

    addon = tmp_path / "Interface" / "AddOns" / "WeintCodex"
    (addon / BRIDGE_DIR).mkdir(parents=True)
    (addon / "WeintCodex.toc").write_text(
        "## Version: 2.3.0.0\n", encoding="utf-8"
    )
    (addon / BRIDGE_DIR / BRIDGE_NAME).write_text(
        "WeintCodex_CompanionLive = WeintCodex_CompanionLive or "
        "{ writtenAt = 0, companionVersion = \"\", queue = {} }\n",
        encoding="utf-8",
    )

    saved = tmp_path / "WTF" / "Account" / "TESTACC" / "SavedVariables"
    saved.mkdir(parents=True)
    (saved / "WeintCodex.lua").write_text(
        'WeintCodex_SavedData = {\n["twinks"] = {\n},\n}\n',
        encoding="utf-8",
    )

    return tmp_path


def _bridge(wow_path):

    return (
        wow_path
        / "Interface" / "AddOns" / "WeintCodex" / BRIDGE_DIR / BRIDGE_NAME
    )


# --------------------------------------------------
# Ablageort
# --------------------------------------------------


def test_kein_addon_installiert_ist_kein_fehler(tmp_path):

    writer = LiveBridgeWriter(tmp_path)

    assert writer.path() is None
    assert writer.write([{"type": "raid_import", "payload": "x"}]) is False


def test_ohne_wow_pfad_passiert_nichts():

    assert LiveBridgeWriter(None).path() is None


def test_die_datei_liegt_da_wo_die_toc_sie_laedt(wow_path):
    """
    WeintCodex.toc lädt "data/companion_live.lua". Landet sie
    woanders, wird sie nie ausgeführt - und das sieht im Spiel exakt
    aus wie "die Companion stellt nichts zu".
    """

    path = LiveBridgeWriter(wow_path).path()

    assert path.parent.name == BRIDGE_DIR
    assert path.name == BRIDGE_NAME


# --------------------------------------------------
# Inhalt
# --------------------------------------------------


def test_die_zustellung_landet_in_der_datei(wow_path):

    LiveBridgeWriter(wow_path).write([
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    content = _bridge(wow_path).read_text(encoding="utf-8")

    assert '["type"] = "raid_import"' in content
    assert '["payload"] = "WCIMPORT:RAIDWED:x"' in content
    assert f'["companionVersion"] = "{VERSION}"' in content


def test_unveraenderte_nachrichten_lassen_den_stempel_stehen(wow_path):
    """
    Das Addon erkennt an `writtenAt`, ob es etwas Neues gibt. Wanderte
    der Stempel bei jedem Sync-Zyklus, würde jeder /reload denselben
    Import erneut einarbeiten und im Chat melden.
    """

    writer = LiveBridgeWriter(wow_path)
    messages = [{"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"}]

    writer.write(messages)
    first = _bridge(wow_path).read_text(encoding="utf-8")

    writer.write(messages)
    second = _bridge(wow_path).read_text(encoding="utf-8")

    assert first == second


def test_geaenderte_nachrichten_setzen_einen_neuen_stempel(wow_path):

    writer = LiveBridgeWriter(wow_path)

    writer.write([{"type": "raid_import", "payload": "alt"}])
    first = _bridge(wow_path).read_text(encoding="utf-8")

    writer.write([{"type": "raid_import", "payload": "neu"}])
    second = _bridge(wow_path).read_text(encoding="utf-8")

    assert first != second
    assert "neu" in second
    assert '"alt"' not in second


def test_kein_zwischenstand_bleibt_liegen(wow_path):

    LiveBridgeWriter(wow_path).write([
        {"type": "raid_import", "payload": "x"},
    ])

    leftovers = list(_bridge(wow_path).parent.glob("*.tmp"))

    assert leftovers == []


# --------------------------------------------------
# Zusammenspiel mit der Inbox
# --------------------------------------------------


def test_beide_wege_bekommen_dieselbe_warteschlange(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    saved = (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    ).read_text(encoding="utf-8")

    live = _bridge(wow_path).read_text(encoding="utf-8")

    assert "WCIMPORT:RAIDWED:x" in saved
    assert "WCIMPORT:RAIDWED:x" in live


def test_ein_addon_update_nimmt_die_zustellung_nicht_dauerhaft_weg(wow_path):
    """
    Der Installer entpackt den leeren Auslieferungsstand über unsere
    Datei. Die Absender schicken einen unveränderten Roster nicht noch
    einmal - ohne reassert() wäre die Zustellung damit verschwunden,
    bis sich beim Bot inhaltlich etwas ändert.
    """

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    _bridge(wow_path).write_text(
        "WeintCodex_CompanionLive = WeintCodex_CompanionLive or "
        "{ writtenAt = 0, companionVersion = \"\", queue = {} }\n",
        encoding="utf-8",
    )

    inbox.reassert()

    assert "WCIMPORT:RAIDWED:x" in _bridge(wow_path).read_text(encoding="utf-8")


def test_ohne_belegten_kanal_wird_nichts_ueberschrieben(wow_path):
    """
    Beim Start der App sind die Kanäle leer. Würde reassert() daraus
    eine leere Zustellung schreiben, nähme sie dem Addon den gültigen
    Stand des vorherigen App-Starts weg, bevor die Absender ihren
    ersten Zyklus hinter sich haben.
    """

    LiveBridgeWriter(wow_path).write([
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    AddonInbox(_Manager(wow_path)).reassert()

    assert "WCIMPORT:RAIDWED:x" in _bridge(wow_path).read_text(encoding="utf-8")


# --------------------------------------------------
# Gegenprobe mit einem echten Lua-Interpreter
# --------------------------------------------------


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_die_datei_ist_gueltiges_lua_und_traegt_die_nachrichten(wow_path):
    """
    Sie liegt im Addon-Ordner und wird von WoW als Programmcode
    ausgeführt. Ein Tippfehler im Serialisierer ist dort kein
    unlesbarer Datensatz, sondern ein Ladefehler.
    """

    LiveBridgeWriter(wow_path).write([
        {"type": "raid_import", "payload": 'Name|TANK|WARRIOR|Ook"Ook|\\|discord|'},
        {"type": "weinttv_report", "payload": {"pull": 7, "kill": False}},
    ])

    script = f"""
        dofile({quote_lua_string(str(_bridge(wow_path)))})
        local live = WeintCodex_CompanionLive
        assert(type(live) == "table", "Tabelle fehlt")
        assert(type(live.writtenAt) == "number", "Stempel ist keine Zahl")
        assert(live.writtenAt > 0, "Stempel ist leer")
        assert(type(live.companionVersion) == "string", "Version fehlt")
        assert(#live.queue == 2, "Warteschlange unvollstaendig")
        assert(live.queue[1].type == "raid_import", "Typ falsch")
        assert(live.queue[1].payload:find('"', 1, true), "Zeichen verloren")
        assert(live.queue[2].payload.pull == 7, "Tabelle falsch")
        assert(live.queue[2].payload.kill == false, "Wahrheitswert falsch")
        print("ok")
    """

    result = subprocess.run([LUA, "-e", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_der_auslieferungsstand_wird_von_der_zustellung_ersetzt(wow_path):
    """
    Der Stub im Repo setzt die Tabelle mit "or", damit er nichts
    überschreibt. Unsere Zustellung muss ohne dieses "or" schreiben -
    sonst gewönne beim Laden die zuerst gesetzte Tabelle.
    """

    LiveBridgeWriter(wow_path).write([
        {"type": "raid_import", "payload": "neu"},
    ])

    script = f"""
        WeintCodex_CompanionLive = {{ writtenAt = 0, queue = {{}} }}
        dofile({quote_lua_string(str(_bridge(wow_path)))})
        assert(#WeintCodex_CompanionLive.queue == 1, "Stub hat gewonnen")
        print("ok")
    """

    result = subprocess.run([LUA, "-e", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
