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
    TARGET_SETTINGS,
    TARGET_URL,
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


def test_a_linked_account_without_a_guild_uses_the_project_guild():

    assert roster_target("", has_account=True) == (
        TARGET_URL,
        guild_url(),
    )


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
