"""
Was der Nutzer in die neue Generation mitnimmt.

Die schaerfste Regel dieser Datei ist eine Verneinung: **keine
Zugangsdaten**. Sie wird hier zweifach geprueft - einmal fuer den
naheliegenden Fall (ein Token steht in der Konfiguration) und einmal
fuer den, der spaeter passiert: jemand nimmt einen Schluessel in die
Positivliste auf, unter dem irgendwann ein Token landet.
"""

import json

from core.migration.payload import (
    DATA_FILES,
    SCHEMA_VERSION,
    SETTINGS,
    build_payload,
    write_payload,
)
from core.migration.target import target_for


class FakeConfig:

    def __init__(self, data):

        self.data = data


def payload(data=None, tmp_path=None):

    return build_payload(
        FakeConfig(data or {}),
        target_for(None),
        "5.0.0",
        config_dir=tmp_path,
    )


# --------------------------------------------------
# Form
# --------------------------------------------------


def test_the_payload_is_versioned(tmp_path):
    """
    Ohne `schema_version` kann V5 eine spaetere Fassung dieser Datei
    nicht von der ersten unterscheiden - und muesste raten.
    """

    data = payload(tmp_path=tmp_path)

    assert data["schema_version"] == SCHEMA_VERSION


def test_both_sides_are_named_with_product_and_version(tmp_path):

    data = payload(tmp_path=tmp_path)

    assert data["source"]["product"] == "WeintCompanion"

    assert data["source"]["version"]

    assert data["target"]["product"] == "Companion-Forever"

    assert data["target"]["version"] == "5.0.0"

    assert data["target"]["repository"] == "daddler/Companion-Forever"


# --------------------------------------------------
# Inhalt
# --------------------------------------------------


def test_the_wow_folders_travel_along(tmp_path):
    """
    Das Wichtigste ueberhaupt: wer das nicht mitnimmt, laesst jeden
    Nutzer die Ordnersuche erneut machen.
    """

    data = payload(
        {
            "wow_client": "forever",
            "wow_paths": {"forever": "/spiele/wow"},
        },
        tmp_path,
    )

    assert data["settings"]["wow_client"] == "forever"

    assert data["settings"]["wow_paths"]["forever"] == "/spiele/wow"


def test_unknown_keys_are_not_taken_along(tmp_path):
    """
    Positivliste, nicht Sperrliste: was spaeter jemand der
    Konfiguration hinzufuegt, faellt von selbst heraus, statt
    stillschweigend mitzureisen.
    """

    data = payload({"irgendwas_neues": "wert"}, tmp_path)

    assert "irgendwas_neues" not in data["settings"]


def test_the_things_that_belong_to_this_app_stay_here(tmp_path):
    """
    Merker fuer gesehene Popups, einmalige Umstellungen,
    Fensterzustand der 4er-Oberflaeche: V5 hat seine eigene
    Einfuehrung.
    """

    for key in (
        "onboarding_seen_version",
        "onboarding_tour_edition",
        "raid_data_source_migrated",
        "classic_path",
    ):

        assert key not in SETTINGS


# --------------------------------------------------
# Keine Geheimnisse
# --------------------------------------------------


def test_a_token_in_the_configuration_never_reaches_the_payload(tmp_path):

    data = payload(
        {
            "companion_token": "geheim-123",
            "discord_access_token": "geheim-456",
            "api_key": "geheim-789",
        },
        tmp_path,
    )

    text = json.dumps(data, ensure_ascii=False)

    for secret in ("geheim-123", "geheim-456", "geheim-789"):
        assert secret not in text


def test_a_secret_hidden_inside_an_allowed_key_is_stripped(tmp_path):
    """
    `access_role_map` steht auf der Positivliste. Landet dort eines
    Tages ein "token", faellt es trotzdem heraus - die Pruefung geht
    rekursiv durch die Werte.
    """

    data = payload(
        {"access_role_map": {"Raider": "mitglied", "token": "geheim-999"}},
        tmp_path,
    )

    assert data["settings"]["access_role_map"] == {"Raider": "mitglied"}

    assert "geheim-999" not in json.dumps(data)


def test_the_discord_account_file_is_marked_as_not_to_be_taken(tmp_path):
    """
    Sie enthaelt das Companion-Token. Sie steht im Payload nur, damit
    V5 weiss, dass es diese Datei kennt und **nicht** anfasst.
    """

    entry = next(
        item
        for item in payload(tmp_path=tmp_path)["data_files"]
        if item["role"] == "discord_account"
    )

    assert entry["migrate"] is False

    assert entry["note"]


def test_every_other_data_file_is_offered_for_migration():

    roles = {role: migrate for role, _, migrate in DATA_FILES}

    assert roles["characters"] is True

    assert roles["academy_progress"] is True

    assert roles["weakauras"] is True

    assert roles["discord_account"] is False


def test_the_data_files_are_pointed_at_not_copied(tmp_path):
    """
    Pfade statt Inhalte: V5 laeuft auf demselben Rechner, und die
    Bibliothek zweimal auf der Platte zu halten waere weder noetig
    noch ehrlich.
    """

    (tmp_path / "characters.json").write_text("[]", encoding="utf-8")

    entries = {
        item["role"]: item
        for item in payload(tmp_path=tmp_path)["data_files"]
    }

    assert entries["characters"]["exists"] is True

    assert entries["characters"]["path"].endswith("characters.json")

    assert entries["weakauras"]["exists"] is False


# --------------------------------------------------
# Schreiben
# --------------------------------------------------


def test_the_payload_is_written_atomically(tmp_path):

    destination = tmp_path / "handover" / "migration.json"

    written = write_payload(payload(tmp_path=tmp_path), destination)

    assert written == destination

    assert json.loads(destination.read_text(encoding="utf-8"))["schema_version"]

    #
    # Keine halbe Datei daneben: geschrieben wird erst temporaer,
    # dann ersetzt.
    #

    assert not list(tmp_path.glob("**/*.tmp"))
