"""
Die Discord-Verweise: Gilde, Feedback-Channel, Aufstellung.

Hintergrund: der Knopf "Aufstellung im Discord" auf der Übersicht war
verdrahtet an nichts. Er stand seit dem 2.0-Umbau in der Karte, ließ
sich anklicken und tat nichts - kein Fehler im Protokoll, keine
Meldung, nur ein Knopf, der nichts bewirkt.

Die Gilden-ID stand dabei doppelt im Programm: einmal als Teil des
Feedback-Links in Einstellungen -> Über. Sie liegt jetzt in
core/backend_config.py, damit beide Seiten dieselbe benutzen.

Die ID ist eine **Zeichenkette**, nicht eine Zahl - dieselbe Regel wie
bei `community.id` in core/access_roles.py: eine Discord-Snowflake
sprengt die Zahlengenauigkeit und käme als `1.23e+18` zurück.
"""

import pytest

from core.backend_config import (
    DISCORD_FEEDBACK_CHANNEL_ID,
    DISCORD_GUILD_ID,
    DISCORD_RAID_CHANNEL_ID,
    TARGET_SETTINGS,
    TARGET_URL,
    app_url,
    channel_url,
    feedback_url,
    guild_url,
    roster_target,
)


# --------------------------------------------------
# Die Verweise selbst
# --------------------------------------------------


def test_the_feedback_link_did_not_change():
    """
    Der Link stand vor dem Umbau wörtlich in
    gui/pages/settings_sections/about.py. Wird er aus den beiden IDs
    zusammengesetzt, muss dasselbe herauskommen - sonst führt der
    Support-Knopf ins Leere.
    """

    assert feedback_url() == (
        "https://discord.com/channels/"
        "1311060525555257364/1519466082362982410"
    )


def test_the_guild_link_defaults_to_the_project_guild():

    assert guild_url() == (
        f"https://discord.com/channels/{DISCORD_GUILD_ID}"
    )


def test_a_given_guild_wins_over_the_default():

    assert guild_url("42") == "https://discord.com/channels/42"


def test_the_ids_are_strings():
    """
    Als Zahl notiert wäre die Snowflake schon in der Quelle verloren.
    """

    assert isinstance(DISCORD_GUILD_ID, str)

    assert isinstance(DISCORD_FEEDBACK_CHANNEL_ID, str)

    assert isinstance(DISCORD_RAID_CHANNEL_ID, str)


def test_a_channel_link_carries_channel_and_message():

    assert channel_url("1", "2", "3") == (
        "https://discord.com/channels/1/2/3"
    )

    assert channel_url("1", "2") == "https://discord.com/channels/1/2"


def test_a_message_without_a_channel_stays_a_guild_link():
    """
    `/channels/<gilde>` öffnet den Standardkanal,
    `/channels/<gilde>//<nachricht>` dagegen gar nichts.
    """

    assert channel_url("1", "", "3") == "https://discord.com/channels/1"


def test_the_app_link_is_the_same_path_under_its_own_scheme():

    assert app_url("https://discord.com/channels/1/2/3") == (
        "discord://-/channels/1/2/3"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://github.com/daddler/WeintCodex",
        "https://discord.gg/einladung",
    ],
)
def test_only_a_discord_link_gets_an_app_variant(url):
    """
    Leer heißt für den Aufrufer "bleib beim Browser". Ein GitHub-Link
    unter `discord://` wäre eine Adresse, die niemand öffnen kann.
    """

    assert app_url(url) == ""


@pytest.mark.parametrize(
    "value",
    [
        1311060525555257364,
        "  1311060525555257364  ",
    ],
)
def test_a_number_or_padded_id_still_yields_a_usable_link(value):
    """
    Die ID kommt aus der Konfiguration und damit aus einer Datei, die
    ein Mensch bearbeiten kann. Eine dort als Zahl notierte Snowflake
    darf nicht als `1.31106052555525734e+18` im Link landen.
    """

    assert guild_url(value) == (
        "https://discord.com/channels/1311060525555257364"
    )


def test_an_empty_selection_falls_back_instead_of_building_a_stub():

    assert guild_url("") == guild_url()

    assert guild_url("   ") == guild_url()


# --------------------------------------------------
# Wohin der Knopf führt
# --------------------------------------------------


def test_a_known_community_wins():

    assert roster_target("999", has_account=True) == (
        TARGET_URL,
        "https://discord.com/channels/999",
    )


def test_the_profile_guild_beats_the_project_guild():
    """
    Der eigentliche Sinn der Reihenfolge: wer in einer anderen Gilde
    spielt, landet in seiner - nicht in der des Projekts.
    """

    kind, value = roster_target("999", has_account=True)

    assert kind == TARGET_URL

    assert DISCORD_GUILD_ID not in value


def test_a_linked_account_without_a_guild_uses_the_project_channel():
    """
    Nicht nur die Gilde: der Anmelde-Kanal ist der Ort, an dem die
    Aufstellung steht. `/channels/<gilde>` allein landet auf dem
    Standardkanal des Servers.
    """

    assert roster_target("", has_account=True) == (
        TARGET_URL,
        f"{guild_url()}/{DISCORD_RAID_CHANNEL_ID}",
    )


def test_the_signup_the_bot_reported_wins():
    """
    Die einzige Auskunft, die auf den Beitrag selbst zeigt - und sie
    stammt aus derselben Antwort wie der Termin daneben.
    """

    assert roster_target(
        "999",
        has_account=True,
        signup={
            "guild_id": "1",
            "channel_id": "2",
            "message_id": "3",
        },
    ) == (TARGET_URL, "https://discord.com/channels/1/2/3")


@pytest.mark.parametrize(
    "signup",
    [
        None,
        {},
        {"guild_id": "1"},
        {"message_id": "3"},
    ],
)
def test_a_signup_without_a_channel_is_no_target(signup):
    """
    Ein halber Fundort ist keiner: ohne Kanal bliebe eine Adresse
    übrig, die auf nichts zeigt. Dann gilt wieder die Reihenfolge
    darunter.
    """

    assert roster_target("999", has_account=True, signup=signup) == (
        TARGET_URL,
        guild_url("999"),
    )


def test_the_project_channel_is_not_carried_into_a_foreign_guild():
    """
    Eine fremde Gilde hat eigene Kanäle - die Kanal-ID des Projekts
    führte dort ins Nichts.
    """

    kind, value = roster_target("999", has_account=True)

    assert value == guild_url("999")

    assert DISCORD_RAID_CHANNEL_ID not in value


def test_without_an_account_the_settings_are_the_target():
    """
    Kein Browser: ein Link würde auf einen Server zeigen, zu dem die
    Anwendung nie eine Verbindung hergestellt hat.
    """

    assert roster_target("", has_account=False) == (
        TARGET_SETTINGS,
        "discord",
    )


def test_a_known_guild_works_even_without_a_linked_account():
    """
    Die gespeicherte Gilde stammt aus einem Zugriffsprofil, das nur
    mit verknüpftem Konto überhaupt abgerufen werden konnte. Wurde das
    Konto danach getrennt, ist die Gilde trotzdem die richtige
    Auskunft - und der Knopf muss nicht in die Einstellung verweisen,
    wo nichts zu tun ist.
    """

    kind, value = roster_target("999", has_account=False)

    assert kind == TARGET_URL

    assert value.endswith("/999")


@pytest.mark.parametrize("stored", [None, "", "   "])
def test_a_blank_community_is_treated_as_unknown(stored):

    assert roster_target(stored, has_account=False)[0] == TARGET_SETTINGS


# --------------------------------------------------
# Die Gilde aus dem Zugriffsprofil festhalten
# --------------------------------------------------


class _Logger:

    def info(self, *a):
        pass

    def error(self, *a):
        pass

    def success(self, *a):
        pass


class _Config:

    def __init__(self):
        self.data = {}
        self.saves = 0

    def save(self):
        self.saves += 1


class _Manager:

    def __init__(self):
        self.logger = _Logger()
        self.config = _Config()


def _sync():

    pytest.importorskip("httpx")

    from core.access_profile_sync import AccessProfileSync

    manager = _Manager()

    #
    # Die Inbox wird für _remember_community() nicht gebraucht.
    #

    return AccessProfileSync(manager, inbox=None), manager


def test_the_community_is_stored_as_a_string():

    sync, manager = _sync()

    sync._remember_community(
        {"id": 1311060525555257364, "name": "WeintCodex"}
    )

    assert manager.config.data["discord_community_id"] == (
        "1311060525555257364"
    )

    assert manager.config.data["discord_community_name"] == "WeintCodex"


def test_an_unchanged_community_is_not_written_again():
    """
    `process()` läuft in jedem Sync-Zyklus - alle fünf Sekunden.
    Jedes Mal eine Datei zu schreiben, um denselben Wert zu
    hinterlegen, wäre Schreiblast ohne Nutzen.
    """

    sync, manager = _sync()

    community = {"id": "123", "name": "Gilde"}

    sync._remember_community(community)

    assert manager.config.saves == 1

    sync._remember_community(community)

    sync._remember_community(community)

    assert manager.config.saves == 1


def test_a_changed_community_is_written():

    sync, manager = _sync()

    sync._remember_community({"id": "123", "name": "Alt"})

    sync._remember_community({"id": "123", "name": "Neu"})

    assert manager.config.saves == 2

    assert manager.config.data["discord_community_name"] == "Neu"


def test_a_missing_id_stores_nothing():
    """
    Kein Rückfall auf die Projektgilde an dieser Stelle: was hier
    landet, soll die Gilde DIESES Nutzers sein. Eine erfundene wäre
    schlechter als keine - der Knopf hat seinen eigenen Rückfall.
    """

    sync, manager = _sync()

    for community in ({}, {"id": ""}, {"id": "   "}, {"id": None}):

        sync._remember_community(community)

    assert "discord_community_id" not in manager.config.data

    assert manager.config.saves == 0


# --------------------------------------------------
# Anwendung statt Browser
# --------------------------------------------------
#
# Der Knopf soll in der Discord-Anwendung landen, nicht in einer
# zweiten, meist abgemeldeten Ansicht desselben Servers im Browser.
# Wer Discord nur im Browser nutzt, hat für `discord://` aber kein
# Programm - und ein lautlos verpuffter Aufruf wäre wieder genau der
# tote Knopf, gegen den core/browser.py geschrieben wurde.
#
# Wo die Anwendung gesucht wird, steht in tests/test_discord_app.py.
# Hier geht es nur um die Weiche: Anwendung zuerst, Browser danach -
# und der Browser bekommt die **https**-Adresse, nie das Schema.


@pytest.fixture
def linux(monkeypatch):

    from core.runtime import Runtime

    monkeypatch.setattr(Runtime, "is_windows", staticmethod(lambda: False))
    monkeypatch.setattr(Runtime, "is_macos", staticmethod(lambda: False))


def test_the_app_is_tried_first(linux, monkeypatch):

    from core import browser, discord_app

    calls = []

    monkeypatch.setattr(
        discord_app,
        "find_launcher",
        lambda url: ["/usr/bin/discord", url],
    )

    monkeypatch.setattr(
        discord_app.subprocess,
        "Popen",
        lambda argv, **kw: calls.append(argv),
    )

    monkeypatch.setattr(
        browser.webbrowser,
        "open",
        lambda url: pytest.fail(f"Browser statt Anwendung: {url}"),
    )

    assert browser.open_url(
        "https://discord.com/channels/1/2/3",
        app_url="discord://-/channels/1/2/3",
    )

    assert calls == [
        ["/usr/bin/discord", "discord://-/channels/1/2/3"]
    ]


def test_without_an_app_the_browser_takes_over(linux, monkeypatch):
    """
    Und zwar mit der Web-Adresse. Genau das war der gemeldete Fehler:
    xdg-open reichte `discord://…` an den Browser weiter und meldete
    Erfolg, worauf dort `http://discord//-/channels/…` stand.
    """

    from core import browser, discord_app

    opened = []

    monkeypatch.setattr(discord_app, "find_launcher", lambda url: [])

    monkeypatch.setattr(
        discord_app.subprocess,
        "Popen",
        lambda argv, **kw: pytest.fail(f"nichts zu starten: {argv}"),
    )

    monkeypatch.setattr(
        browser.webbrowser,
        "open",
        lambda url: opened.append(url) or True,
    )

    assert browser.open_url(
        "https://discord.com/channels/1/2/3",
        app_url="discord://-/channels/1/2/3",
    )

    assert opened == ["https://discord.com/channels/1/2/3"]


def test_a_crashing_launch_is_not_the_end_of_the_button(linux, monkeypatch):

    from core import browser, discord_app

    opened = []

    def boom(argv, **kw):
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(
        discord_app,
        "find_launcher",
        lambda url: ["/opt/discord/Discord", url],
    )

    monkeypatch.setattr(discord_app.subprocess, "Popen", boom)

    monkeypatch.setattr(
        browser.webbrowser,
        "open",
        lambda url: opened.append(url) or True,
    )

    assert browser.open_url("https://discord.com/x", app_url="discord://-/x")

    assert opened == ["https://discord.com/x"]


def test_without_an_app_link_nothing_extra_happens(linux, monkeypatch):

    from core import browser, discord_app

    monkeypatch.setattr(
        discord_app,
        "find_launcher",
        lambda url: pytest.fail("keine Anwendungssuche erwartet"),
    )

    monkeypatch.setattr(
        browser.subprocess,
        "run",
        lambda cmd, **kw: pytest.fail("kein Anwendungsaufruf erwartet"),
    )

    monkeypatch.setattr(browser.webbrowser, "open", lambda url: True)

    assert browser.open_url("https://github.com/daddler/WeintCodex")
