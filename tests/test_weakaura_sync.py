"""
Kommt die Bibliothek so im Addon an, wie das Addon sie liest?

`tests/test_weakaura_library.py` prüft, was eingetragen werden darf.
Hier geht es um den Weg dorthin: die Zustellung über die Addon-Inbox
und - mit einem echten Lua-Interpreter - dass WoWs Lua die
geschriebene Datei so liest, wie `modules/weakauras.lua` es erwartet.

Der Vertrag steht in `docs/weakaura-bridge.md`.
"""

from __future__ import annotations

import shutil
import subprocess
import types

import pytest

from addon.addon_inbox import AddonInbox
from core.lua_table import extract_variable_body, quote_lua_string
from core.weakaura_library import WeakAura
from core.weakaura_store import WeakAuraStore
from core.weakaura_sync import WeakAuraSync


EXPORT = "!WA:2!" + "aBcD3" * 20


class _Logger:

    def __init__(self):
        self.lines = []

    def info(self, message):
        self.lines.append(("info", message))

    def warning(self, message):
        self.lines.append(("warning", message))

    def error(self, message):
        self.lines.append(("error", message))

    def success(self, message):
        self.lines.append(("success", message))


@pytest.fixture
def wow_path(tmp_path):

    saved = tmp_path / "WTF" / "Account" / "TESTACC" / "SavedVariables"

    saved.mkdir(parents=True)

    (saved / "WeintCodex.lua").write_text(
        'WeintCodex_SavedData = {\n["twinks"] = {\n},\n}\n',
        encoding="utf-8",
    )

    return tmp_path


def _lua_file(wow_path):

    return (
        wow_path
        / "WTF" / "Account" / "TESTACC" / "SavedVariables" / "WeintCodex.lua"
    )


@pytest.fixture
def rig(tmp_path, wow_path):
    """
    Ablage, Inbox und Zustellung, wie sie im CompanionManager
    zusammenhängen.
    """

    manager = types.SimpleNamespace(
        logger=_Logger(),
        state=types.SimpleNamespace(wow_path=wow_path),
    )

    store = WeakAuraStore(manager, path=tmp_path / "weakauras.json")

    sync = WeakAuraSync(manager, AddonInbox(manager), store)

    return types.SimpleNamespace(
        manager=manager,
        store=store,
        sync=sync,
        wow_path=wow_path,
    )


def _inbox(wow_path) -> str:

    return extract_variable_body(
        _lua_file(wow_path).read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    ) or ""


def _aura(**overrides) -> WeakAura:

    values = dict(
        id="companion-test",
        name="Test",
        category="raid",
        description="Zeigt etwas.",
        version="1.0",
        string=EXPORT,
        updated_at=1000,
    )

    values.update(overrides)

    return WeakAura(**values)


# --------------------------------------------------


def test_nothing_is_written_for_someone_who_never_used_the_page(rig):
    """
    Eine leere Bibliothek darf keinen Kanal belegen - sonst schriebe
    die Anwendung bei jedem Nutzer in WoWs SavedVariables, ohne dass
    es etwas zu sagen gäbe.
    """

    rig.sync.process()

    assert _inbox(rig.wow_path) == ""


def test_the_library_reaches_the_inbox(rig):

    rig.store.put(_aura())

    rig.sync.process()

    body = _inbox(rig.wow_path)

    assert "weakaura_library" in body

    assert EXPORT in body

    assert any(level == "success" for level, _ in rig.manager.logger.lines)


def test_an_unchanged_library_is_not_written_twice(rig):
    """
    Aura-Strings sind lang, und jedes Schreiben fasst WoWs komplette
    SavedVariables-Datei an - samt der Variablen anderer Bereiche.
    """

    rig.store.put(_aura())

    rig.sync.process()

    stamp = _lua_file(rig.wow_path).stat().st_mtime_ns

    rig.sync.process()

    assert _lua_file(rig.wow_path).stat().st_mtime_ns == stamp


def test_deleting_the_last_aura_is_delivered_rather_than_skipped(rig):
    """
    Wer seine letzte Aura löscht, will sie im Spiel loswerden. Würde
    eine leere Bibliothek grundsätzlich übersprungen, bliebe genau
    die eine Aura für immer stehen, die ausdrücklich weg sollte.
    """

    rig.store.put(_aura())

    rig.sync.process()

    rig.store.remove("companion-test")

    rig.sync.process()

    body = _inbox(rig.wow_path)

    assert "weakaura_library" in body

    assert EXPORT not in body


def test_a_missing_savedvariables_file_is_retried_later(tmp_path):
    """
    `publish()` gibt False zurück, wenn WoW nie gestartet wurde. Der
    Merker darf dann NICHT gesetzt werden - sonst gälte die
    Zustellung als erledigt und käme nie nach.
    """

    manager = types.SimpleNamespace(
        logger=_Logger(),
        state=types.SimpleNamespace(wow_path=None),
    )

    store = WeakAuraStore(manager, path=tmp_path / "weakauras.json")

    store.put(_aura())

    sync = WeakAuraSync(manager, AddonInbox(manager), store)

    sync.process()

    assert sync._fingerprint is None


# --------------------------------------------------
# Gegenprobe mit einem echten Lua-Interpreter
# --------------------------------------------------


LUA = shutil.which("lua5.1") or shutil.which("lua")


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_the_addon_would_read_the_library_as_expected(rig):
    """
    Die eigentliche Gegenprobe: WoWs Lua liest diese Datei. Geprüft
    wird genau das, was `INBOX_HANDLERS.weakaura_library` und
    `modules/weakauras.lua` von ihr erwarten - und dass ein
    Aura-Name mit Anführungszeichen und Backslash die Datei nicht
    zerlegt.
    """

    rig.store.put(
        _aura(
            id="companion-eigene",
            name='Sperlings"schlag',
            description="Mit \\ Backslash.",
            author="Fabian",
            icon="Interface\\Icons\\spell_holy_sealofmight",
        )
    )

    rig.store.put(
        _aura(
            id="DRUID",
            name="Druide",
            category="class",
            version="2.0.7",
            string="!WA:2!" + "zZ9" * 30,
        )
    )

    rig.sync.process()

    script = f"""
        dofile({quote_lua_string(str(_lua_file(rig.wow_path)))})

        local msg = WeintCompanionInboxDB.queue[1]
        assert(msg.type == "weakaura_library", "Typ falsch")

        local p = msg.payload
        assert(type(p) == "table", "Nutzlast ist keine Tabelle")
        assert(type(p.auras) == "table", "auras ist keine Tabelle")
        assert(#p.auras == 2, "Anzahl falsch: " .. tostring(#p.auras))

        local byId = {{}}
        for _, aura in ipairs(p.auras) do byId[aura.id] = aura end

        local own = byId["companion-eigene"]
        assert(own ~= nil, "Eigene Aura fehlt")
        assert(own.name == 'Sperlings"schlag', "Anfuehrungszeichen verloren")
        assert(own.description:find("\\\\", 1, true), "Backslash verloren")
        assert(own.category == "raid", "Rubrik falsch")
        assert(own.author == "Fabian", "Autor verloren")
        assert(own.icon:find("Icons", 1, true), "Symbolpfad verloren")
        assert(own.string:sub(1, 6) == "!WA:2!", "Importstring beschaedigt")

        -- Die Kennung einer mitgelieferten Aura: an ihr erkennt
        -- modules/weakauras.lua, dass ersetzt und nicht ergaenzt wird.
        local shipped = byId["DRUID"]
        assert(shipped ~= nil, "Ersatz fuer die mitgelieferte Aura fehlt")
        assert(shipped.version == "2.0.7", "Version falsch")

        assert(type(p.version) == "number", "Formatversion fehlt")
        assert(type(p.updatedAt) == "number", "Zeitstempel fehlt")

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
