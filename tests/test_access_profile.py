"""
Das Zugriffsprofil: Rollen -> Rang -> Freigaben -> Inbox.

Zwei Dinge sind hier wichtiger als der Rest, weil sie beide still
schiefgehen und erst im Spiel auffallen:

- Die Community-ID muss als Lua-ZEICHENKETTE in der Datei landen. Eine
  Discord-Snowflake ist zu groß für Luas 5.1-Zahlen; als Zahl
  geschrieben würde sie zu "1.23e+18" und im Addon nie gegen die
  Dezimaldarstellung passen - jede Nachricht gälte dort als "fremde
  Community".
- Die Freigaben müssen echte Wahrheitswerte sein. Das Addon behandelt
  alles andere absichtlich als "nicht gesetzt" und fällt auf seine
  eigene Rangtabelle zurück, womit unsere Zuordnung wirkungslos wäre.

Beides wird deshalb gegen die geschriebene Datei geprüft, nicht nur
gegen die Python-Struktur.
"""

import shutil
import subprocess

import pytest

from addon.addon_inbox import AddonInbox
from core.access_roles import (
    FEATURE_KEYS,
    TIER_FEATURES,
    TIER_ORDER,
    build_profile_payload,
    features_for,
    resolve_tier,
)
from core.lua_table import extract_variable_body, quote_lua_string


class _Logger:

    def __init__(self):
        self.errors = []

    def info(self, message):
        pass

    def error(self, message):
        self.errors.append(message)

    def success(self, message):
        pass

    def warning(self, message):
        pass


class _State:

    def __init__(self, wow_path):
        self.wow_path = wow_path


class _Config:

    def __init__(self, data=None):
        self.data = data or {}


class _Manager:

    def __init__(self, wow_path, config=None):
        self.state = _State(wow_path)
        self.logger = _Logger()
        self.config = config or _Config()


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


def _inbox_body(wow_path) -> str:

    return extract_variable_body(
        _lua_file(wow_path).read_text(encoding="utf-8"),
        "WeintCompanionInboxDB",
    ) or ""


def _build(data, role_map=None, now=1000):
    """
    Kurzform: nur die Nutzlast, Fehlgrund verworfen.
    """

    payload, _, _ = build_profile_payload(
        data, role_map=role_map, version="1.4.0", now=now
    )

    return payload


def _response(**overrides):

    data = {
        "community": {"id": "123456789012345678", "name": "Weint"},
        "identity": {"discordId": "42", "discordName": "njiah"},
        "roles": ["Raider"],
    }

    data.update(overrides)

    return data


# --------------------------------------------------
# Rollen -> Rang
# --------------------------------------------------


def test_known_roles_map_to_their_tier():

    assert resolve_tier(["Trial"])[0] == "mitglied"
    assert resolve_tier(["Offizier"])[0] == "offizier"
    assert resolve_tier(["Raidgast"])[0] == "extern"


def test_bis_einer_weint_roles_map_to_their_tier():
    """
    Die tatsaechlichen Discord-Rollennamen der Gilde: Admin,
    Gildenleitung, Klassen-Support und Member sind gildenintern und
    bekommen "offizier". Raider und Friends sind gildenextern und
    bekommen "extern" - nicht "mitglied", obwohl "raider" andernorts
    oft ein Gildenmitglied waere.
    """

    assert resolve_tier(["Admin"])[0] == "offizier"
    assert resolve_tier(["Gildenleitung"])[0] == "offizier"
    assert resolve_tier(["Klassen-Support"])[0] == "offizier"
    assert resolve_tier(["Member"])[0] == "offizier"

    assert resolve_tier(["Raider"])[0] == "extern"
    assert resolve_tier(["Friends"])[0] == "extern"


def test_the_highest_tier_wins():
    """
    Ein Offizier, der zusätzlich "Raidgast" trägt, darf nicht auf
    Gast zurückfallen.
    """

    tier, matched = resolve_tier(["Raidgast", "Offizier"])

    assert tier == "offizier"
    assert len(matched) == 2


def test_role_matching_ignores_case_and_whitespace():

    assert resolve_tier(["  tRiAl "])[0] == "mitglied"


def test_unknown_roles_yield_no_tier():
    """
    Kein stiller Rückfall auf "gast": eine im Discord umbenannte Rolle
    ist ein Konfigurationsfehler und darf nicht wie eine bewusste
    Sperre aussehen.
    """

    assert resolve_tier(["Irgendwas"])[0] is None
    assert resolve_tier([])[0] is None


def test_a_custom_map_overrides_the_default():

    tier, _ = resolve_tier(
        ["Stammraider"],
        {"Stammraider": "offizier"},
    )

    assert tier == "offizier"


def test_an_unknown_tier_in_the_map_is_ignored():

    assert resolve_tier(["X"], {"X": "grossmeister"})[0] is None


# --------------------------------------------------
# Freigaben
# --------------------------------------------------


def test_features_are_complete_and_boolean():
    """
    Vollständig, damit das Addon seine eigene Rangtabelle nie braucht -
    ein Auseinanderlaufen der beiden Tabellen könnte sonst unbemerkt
    bleiben.
    """

    for tier in TIER_ORDER:

        features = features_for(tier)

        assert set(features) == set(FEATURE_KEYS)

        for key, value in features.items():
            assert value is True or value is False, (tier, key)


def test_guest_gets_nothing_and_officer_gets_everything():

    assert not any(features_for("gast").values())
    assert all(features_for("offizier").values())


def test_calendar_view_never_without_raids_view():
    """
    Die Kalenderseite des Addons liest die Anmeldungen für die
    Einladungsvorschau - Termine ohne Roster wären dort ein Widerspruch.
    """

    for tier in TIER_ORDER:

        features = features_for(tier)

        if features["calendar.view"]:
            assert features["raids.view"], tier


def test_tiers_are_monotone():
    """
    Ein höherer Rang darf nie weniger dürfen als ein niedrigerer.
    """

    for lower, higher in zip(TIER_ORDER, TIER_ORDER[1:]):
        assert TIER_FEATURES[lower] <= TIER_FEATURES[higher], (lower, higher)


def test_extern_may_raid_but_not_touch_the_guild_bank_or_loot():
    """
    Der Kern der Sache: ein Extern-Raider braucht Roster, Termine und
    Taktiken - aber er soll keine fremde Gildenbank in unsere
    Auswertung scannen und keinen Loot in unseren Discord melden.
    """

    features = features_for("extern")

    assert features["raids.view"]
    assert features["calendar.view"]
    assert features["bossguides.tips"]

    assert not features["materials.scan"]
    assert not features["loot.report"]
    assert not features["weinttv.raid"]
    assert not features["calendar.invite"]


# --------------------------------------------------
# Nutzlast
# --------------------------------------------------


def test_payload_carries_the_community_id_as_a_string():

    payload = _build(_response())

    assert payload["community"]["id"] == "123456789012345678"
    assert isinstance(payload["community"]["id"], str)


def test_a_numeric_community_id_is_stringified():
    """
    Genau der Fall, der sonst still bricht: eine Snowflake als Zahl.
    """

    payload = _build(
        _response(community={"id": 123456789012345678, "name": "Weint"})
    )

    assert payload["community"]["id"] == "123456789012345678"


def test_payload_without_a_community_is_refused():

    assert _build(_response(community={})) is None
    assert _build(_response(community={"id": "  "})) is None
    assert _build({"roles": ["Raider"]}) is None
    assert _build("bloedsinn") is None


def test_unmatched_roles_deliver_nothing_and_name_the_reason():

    payload, matched, error = build_profile_payload(
        _response(roles=["Irgendwas"]), version="1.4.0", now=1000
    )

    assert payload is None
    assert matched == []

    # Der Grund muss im Log landen koennen - "nichts passiert" ohne
    # Erklaerung waere hier der schlechteste Ausgang.
    assert error and "Irgendwas" in error


def test_the_bot_may_send_the_tier_itself():
    """
    Vorwärtskompatibilität: schickt der Bot den Rang mit, gewinnt er -
    so lässt sich die Zuordnung später dorthin ziehen, ohne die
    Companion neu auszuliefern.
    """

    payload = _build(
        _response(roles=["Voellig Unbekannt"], tier="offizier")
    )

    assert payload["tier"] == "offizier"
    assert payload["features"]["calendar.invite"] is True


def test_a_nonsense_tier_from_the_bot_falls_back_to_the_local_map():

    payload = _build(_response(tier="grossmeister"))

    assert payload["tier"] == "extern"


def test_issued_at_is_taken_from_the_caller_and_advances():
    """
    Das Addon lehnt ein Profil mit aelterem issuedAt ab. Der Zeitpunkt
    wird deshalb hereingegeben und nicht im Modul gelesen - so ist er
    hier ueberhaupt pruefbar, und ein fester Wert (der jede
    Aktualisierung blockieren wuerde) faellt auf.
    """

    first = _build(_response(), now=1000)
    second = _build(_response(), now=2000)

    assert first["issuedAt"] == 1000
    assert second["issuedAt"] > first["issuedAt"]


def test_expires_at_defaults_to_never():

    assert _build(_response())["expiresAt"] == 0
    assert _build(_response(expiresAt="quatsch"))["expiresAt"] == 0
    assert _build(_response(expiresAt=1770000000))["expiresAt"] == 1770000000


def test_an_empty_notice_is_omitted():

    assert "notice" not in _build(_response(notice="   "))
    assert _build(_response(notice="Frag im Discord"))["notice"] == (
        "Frag im Discord"
    )


# --------------------------------------------------
# Zustellung
# --------------------------------------------------


def test_the_profile_reaches_the_inbox_on_its_own_channel(wow_path):
    """
    Eigener Kanal, sonst würde der Roster-Sync im selben Durchlauf die
    Nachricht mitlöschen (siehe addon/addon_inbox.py).
    """

    inbox = AddonInbox(_Manager(wow_path))

    payload = _build(_response())
    payload.pop("_matchedRoles", None)

    inbox.publish("roster", [{"type": "raid_import", "payload": "WCIMPORT:X"}])
    inbox.publish("access", [{
        "type": "access_profile",
        "payload": payload,
        "community": payload["community"]["id"],
    }])

    body = _inbox_body(wow_path)

    assert "access_profile" in body
    assert "raid_import" in body


def test_the_community_is_written_as_a_quoted_string(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("access", [{
        "type": "raid_import",
        "payload": "WCIMPORT:RAIDWED:x",
        "community": "123456789012345678",
    }])

    body = _inbox_body(wow_path)

    assert '["community"] = "123456789012345678"' in body


def test_a_message_without_a_community_stays_as_before(wow_path):

    inbox = AddonInbox(_Manager(wow_path))

    inbox.publish("roster", [
        {"type": "raid_import", "payload": "WCIMPORT:RAIDWED:x"},
    ])

    assert '["community"]' not in _inbox_body(wow_path)


# --------------------------------------------------
# Gegenprobe mit einem echten Lua-Interpreter
# --------------------------------------------------


LUA = shutil.which("lua5.1") or shutil.which("lua")


@pytest.mark.skipif(LUA is None, reason="kein Lua-Interpreter vorhanden")
def test_the_addon_would_read_the_profile_as_expected(wow_path):
    """
    Die eigentliche Gegenprobe: WoWs Lua liest diese Datei. Geprüft
    wird genau, was core/access.lua im Addon prüft - Zeichenkette bei
    der ID, echte Wahrheitswerte bei den Freigaben.
    """

    inbox = AddonInbox(_Manager(wow_path))

    payload = _build(
        _response(
            community={"id": 123456789012345678, "name": "Bis Einer Weint"},
            roles=["Raidgast"],
            notice='Rolle "Raider" gibt es in #raidorga',
        )
    )

    payload.pop("_matchedRoles", None)

    inbox.publish("access", [{
        "type": "access_profile",
        "payload": payload,
        "community": payload["community"]["id"],
    }])

    script = f"""
        dofile({quote_lua_string(str(_lua_file(wow_path)))})

        local msg = WeintCompanionInboxDB.queue[1]
        assert(msg.type == "access_profile", "Typ falsch")
        assert(type(msg.community) == "string", "Huellen-Community keine Zeichenkette")

        local p = msg.payload
        assert(type(p) == "table", "Nutzlast ist keine Tabelle")

        -- Der Fallstrick: als Zahl waere das "1.23e+17" und wuerde
        -- im Addon nie gegen die Bindung passen.
        assert(type(p.community.id) == "string", "community.id keine Zeichenkette")
        assert(p.community.id == "123456789012345678", "community.id falsch")

        assert(p.tier == "extern", "Rang falsch: " .. tostring(p.tier))
        assert(p.tierLabel == "Extern", "Rangname falsch")

        -- Nur echte Booleans zaehlen im Addon.
        assert(p.features["raids.view"] == true, "raids.view nicht true")
        assert(p.features["materials.scan"] == false, "materials.scan nicht false")

        assert(type(p.issuedAt) == "number", "issuedAt keine Zahl")
        assert(p.expiresAt == 0, "expiresAt falsch")
        assert(p.roles[1] == "Raidgast", "Rollen verloren")
        assert(p.notice:find("raidorga", 1, true), "Hinweis verloren")
        assert(p.companionVersion ~= nil, "Companion-Version fehlt")

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
