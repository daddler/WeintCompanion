"""
Die gemeinsame WeakAura-Bibliothek auf der Companion-Seite.

`tests/test_weakaura_library.py` prüft, was eingetragen werden darf,
`tests/test_weakaura_sync.py` den Weg ins Addon. Hier geht es um die
dritte Quelle: was der Bot liefert, wie es sich mit den eigenen Auren
mischt, und was passiert, wenn er nicht antwortet.

Drei Eigenschaften, von denen keine einen Fehler erzeugt, wenn sie
bricht:

* **Ein nicht erreichbarer Bot löscht nichts.** Sonst verschwänden bei
  jeder Netzstörung alle Gildenauren aus dem Spiel.
* **Eine leere Antwort räumt sehr wohl.** So verschwindet eine
  gelöschte oder gesperrte Aura - der Unterschied zu oben ist der
  ganze Punkt.
* **Bei gleicher Kennung gewinnt die eigene Fassung.** Wer seine
  eigene getippt hat, verliert sie nicht dadurch, dass jemand anderes
  unter derselben Kennung etwas freigibt.
"""

from __future__ import annotations

import types

import pytest

from core.weakaura_client import LibraryResult, aura_from_bot
from core.weakaura_guild_sync import WeakAuraGuildSync
from core.weakaura_library import SCOPE_GUILD, SCOPE_LOCAL, WeakAura
from core.weakaura_store import WeakAuraStore


EXPORT = "!WA:2!" + "aBcD3" * 20

GUILD_EXPORT = "!WA:2!" + "zZ9zZ" * 20


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


class _Client:
    """
    Ein Bot, der antwortet, was der Test möchte.
    """

    def __init__(self, result=None, discord_id="111"):

        self.result = result or LibraryResult(ok=True)

        self.discord_id = discord_id

        self.fetches = 0

    def own_discord_id(self):
        return self.discord_id

    def fetch(self):
        self.fetches += 1
        return self.result


@pytest.fixture
def store(tmp_path):

    return WeakAuraStore(
        types.SimpleNamespace(logger=_Logger()),
        path=tmp_path / "weakauras.json",
    )


def _guild_aura(aura_id="chef-1", **overrides):

    values = dict(
        id=aura_id,
        name="Chefaura",
        category="raid",
        string=GUILD_EXPORT,
        author="Chef",
        author_id="999",
        scope=SCOPE_GUILD,
        foreign=True,
    )

    values.update(overrides)

    return WeakAura(**values)


def _sync(store, client, deliveries=None):

    #
    # `deliveries if ... is not None` und nicht `deliveries or []`:
    # eine leere Liste ist falsy, und die Kurzform legte dem Test eine
    # zweite, unbeobachtete Liste unter.
    #

    recorded = deliveries if deliveries is not None else []

    manager = types.SimpleNamespace(
        logger=_Logger(),
        weakaura_sync=types.SimpleNamespace(
            publish_now=lambda: recorded.append(True)
        ),
    )

    return WeakAuraGuildSync(manager, store, client=client)


# --------------------------------------------------
# Was der Bot liefert
# --------------------------------------------------


def test_a_bot_row_becomes_a_guild_aura():

    aura = aura_from_bot(
        {
            "id": "chef-1",
            "name": "Chefaura",
            "category": "raid",
            "version": "1.2",
            "string": GUILD_EXPORT,
            "author": "Chef",
            "author_id": "999",
        },
        own_id="111",
    )

    assert aura.scope == SCOPE_GUILD

    assert aura.shared is True

    #
    # Fremd: hier bearbeiten liesse sich nur, was einem gehört - ein
    # Formular, das beim Speichern 403 sagt, ist schlechter als
    # keins.
    #

    assert aura.foreign is True


def test_my_own_published_aura_does_not_come_back_as_foreign():

    aura = aura_from_bot(
        {"id": "x", "name": "Meine", "string": EXPORT, "author_id": "111"},
        own_id="111",
    )

    assert aura.foreign is False


def test_a_row_without_a_string_is_dropped():
    """
    Ohne Importstring wäre die Zeile im Spiel eine Schaltfläche, die
    nichts tut.
    """

    assert aura_from_bot({"id": "x", "name": "Leer"}) is None

    assert aura_from_bot({"string": EXPORT}) is None

    assert aura_from_bot("kaputt") is None


# --------------------------------------------------
# Der Abgleich
# --------------------------------------------------


def test_a_successful_fetch_fills_the_library_and_delivers(store):

    deliveries = []

    sync = _sync(
        store,
        _Client(LibraryResult(ok=True, auras=(_guild_aura(),))),
        deliveries,
    )

    assert sync.process() is True

    assert [aura.id for aura in store.guild_auras()] == ["chef-1"]

    #
    # Sofort weiterreichen: zwischen "der Bot hat eine neue Aura" und
    # dem Addon läge sonst bis zu ein Sync-Intervall plus ein
    # /reload.
    #

    assert deliveries == [True]


def test_an_unreachable_bot_leaves_the_library_alone(store):
    """
    Der wichtigste Test dieser Datei: sonst verschwänden bei jeder
    Netzstörung alle Gildenauren aus dem Spiel, ohne dass irgendwo
    etwas kaputt wäre.
    """

    store.set_guild_auras([_guild_aura()])

    sync = _sync(store, _Client(LibraryResult(reason="Bot nicht erreichbar")))

    assert sync.process() is False

    assert [aura.id for aura in store.guild_auras()] == ["chef-1"]

    assert sync.reason == "Bot nicht erreichbar"


def test_an_empty_answer_does_clear_the_library(store):
    """
    Der Unterschied zum Test darüber ist der ganze Punkt: so
    verschwindet eine gelöschte oder gesperrte Aura.
    """

    store.set_guild_auras([_guild_aura()])

    sync = _sync(store, _Client(LibraryResult(ok=True, auras=())))

    assert sync.process() is True

    assert store.guild_auras() == []


def test_without_a_linked_account_nothing_happens(store):
    """
    Der Normalzustand für jeden, der die Companion ohne Discord
    benutzt - und ausdrücklich kein Räumen.
    """

    store.set_guild_auras([_guild_aura()])

    client = _Client(discord_id="")

    sync = _sync(store, client)

    assert sync.process() is False

    assert client.fetches == 0

    assert len(store.guild_auras()) == 1


def test_the_fetch_is_lazy_but_can_be_forced(store):
    """
    Die Bibliothek ändert sich ein paarmal im Monat; sie alle fünf
    Sekunden zu erfragen wäre eine Anfrage je Sync-Takt - auf einem
    Bot mit 0,15 vCPU.
    """

    client = _Client(LibraryResult(ok=True, auras=(_guild_aura(),)))

    sync = _sync(store, client)

    sync.process()

    sync.process()

    assert client.fetches == 1

    sync.invalidate()

    sync.process()

    assert client.fetches == 2


def test_an_unchanged_library_is_not_delivered_again(store):

    deliveries = []

    client = _Client(LibraryResult(ok=True, auras=(_guild_aura(),)))

    sync = _sync(store, client, deliveries)

    sync.process()

    sync.invalidate()

    sync.process()

    assert deliveries == [True]


# --------------------------------------------------
# Die Mischung
# --------------------------------------------------


def test_the_own_version_wins_over_the_guilds(store):
    """
    Von speziell nach allgemein, dieselbe Ordnung, mit der das Addon
    eine zugestellte Aura über eine mitgelieferte legt.
    """

    store.put(
        WeakAura(
            id="chef-1",
            name="Meine Fassung",
            category="raid",
            string=EXPORT,
        )
    )

    store.set_guild_auras([_guild_aura()])

    delivered = {aura.id: aura for aura in store.delivery()}

    assert delivered["chef-1"].string == EXPORT

    assert delivered["chef-1"].scope == SCOPE_LOCAL

    #
    # Und die Seite sagt es an der Zeile - sonst wäre nicht zu
    # erklären, warum die freigegebene Fassung ingame anders
    # aussieht.
    #

    assert store.shadowed_ids() == {"chef-1"}


def test_both_kinds_reach_the_addon_payload(store):

    store.put(WeakAura(id="mine", name="Meine", category="raid", string=EXPORT))

    store.set_guild_auras([_guild_aura()])

    auras = {entry["id"]: entry for entry in store.payload()["auras"]}

    assert set(auras) == {"mine", "chef-1"}

    #
    # Das Addon zeichnet daraus "Gilde · Chef" statt
    # "Companion · …". Ein fehlendes Feld heisst dort "vom eigenen
    # Schreibtisch" - so verhält sich auch eine ältere Companion.
    #

    assert auras["chef-1"]["scope"] == "guild"

    assert "scope" not in auras["mine"]


def test_a_guild_aura_survives_a_restart(store, tmp_path):
    """
    Ohne Zwischenspeicher wären beim Start alle Gildenauren weg, bis
    der erste Sync-Takt durch ist - und die Zustellung ans Addon, die
    genau dann läuft, hätte sie schon gelöscht.
    """

    store.set_guild_auras([_guild_aura()])

    reopened = WeakAuraStore(
        types.SimpleNamespace(logger=_Logger()),
        path=tmp_path / "weakauras.json",
    )

    restored = reopened.guild_auras()

    assert [aura.id for aura in restored] == ["chef-1"]

    assert restored[0].scope == SCOPE_GUILD

    assert restored[0].foreign is True

    assert restored[0].string == GUILD_EXPORT


def test_a_shipped_aura_replaced_by_the_guild_is_listed_only_once(store):
    """
    Wie bei einer eigenen Fassung: sonst stünde dieselbe Aura zweimal
    da und es wäre nicht zu erkennen, welche im Spiel gewinnt.
    """

    store.apply_catalog("DRUID|Druide|class|2.0.6|addon")

    assert [entry.id for entry in store.addon_entries()] == ["DRUID"]

    store.set_guild_auras([_guild_aura(aura_id="DRUID")])

    assert store.addon_entries() == []


def test_disconnecting_discord_drops_the_guild_but_keeps_ones_own(store):
    """
    Die WeakAuras der Gilde gehören der Gilde. Die selbst
    eingetragenen bleiben - die hat niemand anderes.
    """

    store.put(WeakAura(id="mine", name="Meine", category="raid", string=EXPORT))

    store.set_guild_auras([_guild_aura()])

    assert store.clear_guild() is True

    assert store.guild_auras() == []

    assert [aura.id for aura in store.auras()] == ["mine"]

    #
    # Und ein zweites Trennen schreibt die Datei nicht erneut.
    #

    assert store.clear_guild() is False


def test_someone_without_own_auras_still_gets_the_guilds(tmp_path):
    """
    Der Regelfall für die meisten: nie selbst eine Aura eingetragen,
    aber die der Gilde sollen ankommen.

    `WeakAuraSync.process()` liest deshalb `delivery()` und nicht
    `auras()` - mit der eigenen Liste wäre die Bibliothek für sie
    dauerhaft unsichtbar, obwohl sie voll ist.
    """

    from addon.addon_inbox import AddonInbox
    from core.lua_table import extract_variable_body
    from core.weakaura_sync import WeakAuraSync

    saved = tmp_path / "WTF" / "Account" / "TESTACC" / "SavedVariables"

    saved.mkdir(parents=True)

    (saved / "WeintCodex.lua").write_text(
        'WeintCodex_SavedData = {\n["twinks"] = {\n},\n}\n',
        encoding="utf-8",
    )

    manager = types.SimpleNamespace(
        logger=_Logger(),
        state=types.SimpleNamespace(wow_path=tmp_path),
    )

    store = WeakAuraStore(manager, path=tmp_path / "weakauras.json")

    store.set_guild_auras([_guild_aura()])

    assert store.auras() == []

    WeakAuraSync(manager, AddonInbox(manager), store).process()

    body = extract_variable_body(
        (saved / "WeintCodex.lua").read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    ) or ""

    assert GUILD_EXPORT in body

    assert '["scope"] = "guild"' in body
