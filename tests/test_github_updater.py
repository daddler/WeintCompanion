"""
Die Auswahl des Update-Assets aus der GitHub-Release-Antwort.

GitHub garantiert keine feste Reihenfolge der Assets in der API-
Antwort. Läuft die Auswahl über eine reine Teilstring-Suche
("wanted in name"), passt der Filter ".appimage" auch auf die von
der CI veröffentlichte Prüfsummendatei
"WeintCompanion-x86_64.AppImage.sha256" - steht sie zufällig vor der
echten Binärdatei in der Liste, würde sie selbst als "das Asset"
erkannt. Die Suche nach ihrer eigenen Prüfsumme
("<name>.sha256.sha256") läuft dann zwangsläufig ins Leere, und das
Update wird mit "Keine Prüfsumme verfügbar" abgebrochen - obwohl der
Release ganz normal eine Prüfsumme hat.
"""

import pytest

pytest.importorskip("httpx")

from core.github_updater import GitHubUpdater


class FakeResponse:

    def __init__(self, json_data=None, text=""):

        self._json_data = json_data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


class FakeClient:
    """
    Ersetzt httpx.Client. Liefert für die Release-URL das gegebene
    JSON, für jede andere URL (die Prüfsummen-Downloads) den Inhalt
    aus "checksum_bodies" nach URL.
    """

    def __init__(self, release_json, checksum_bodies=None):

        self.release_json = release_json
        self.checksum_bodies = checksum_bodies or {}

    def get(self, url, params=None):

        if url in self.checksum_bodies:
            return FakeResponse(text=self.checksum_bodies[url])

        return FakeResponse(json_data=self.release_json)


def _updater(release_json, checksum_bodies=None, asset_filter=".appimage"):

    updater = GitHubUpdater(
        "daddler",
        "WeintCompanion",
        asset_filter=asset_filter,
    )

    updater.client = FakeClient(release_json, checksum_bodies)

    return updater


CHECKSUM_URL = (
    "https://github.com/daddler/WeintCompanion/releases/download/"
    "v1.2.1/WeintCompanion-x86_64.AppImage.sha256"
)

BINARY_URL = (
    "https://github.com/daddler/WeintCompanion/releases/download/"
    "v1.2.1/WeintCompanion-x86_64.AppImage"
)

VALID_HASH = "a" * 64


def _release_json(assets):

    return {
        "tag_name": "v1.2.1",
        "name": "1.2.1",
        "body": "",
        "published_at": "2026-07-30T00:00:00Z",
        "assets": assets,
    }


#
# --------------------------------------------------
# _is_checksum_asset
# --------------------------------------------------
#


def test_is_checksum_asset_recognises_the_sha256_sidecar():

    assert GitHubUpdater._is_checksum_asset(
        "WeintCompanion-x86_64.AppImage.sha256"
    ) is True


def test_is_checksum_asset_does_not_flag_the_real_binary():

    assert GitHubUpdater._is_checksum_asset(
        "WeintCompanion-x86_64.AppImage"
    ) is False


#
# --------------------------------------------------
# Asset-Auswahl
# --------------------------------------------------
#


def test_the_checksum_file_is_not_picked_as_the_main_asset_even_when_listed_first():
    """
    Der eigentliche Fehlerfall: die Prüfsummendatei steht vor der
    Binärdatei in der Asset-Liste. Ohne den Ausschluss würde die
    Teilstring-Suche ".appimage in name" auf die ".sha256"-Datei
    zuerst zuschlagen.
    """

    assets = [
        {
            "name": "WeintCompanion-x86_64.AppImage.sha256",
            "browser_download_url": CHECKSUM_URL,
        },
        {
            "name": "WeintCompanion-x86_64.AppImage",
            "browser_download_url": BINARY_URL,
        },
    ]

    updater = _updater(
        _release_json(assets),
        checksum_bodies={CHECKSUM_URL: f"{VALID_HASH}  WeintCompanion-x86_64.AppImage"},
    )

    release = updater.get_latest_release()

    assert release.asset_name == "WeintCompanion-x86_64.AppImage"
    assert release.download_url == BINARY_URL
    assert release.sha256 == VALID_HASH


def test_asset_order_does_not_matter_when_the_binary_comes_first():

    assets = [
        {
            "name": "WeintCompanion-x86_64.AppImage",
            "browser_download_url": BINARY_URL,
        },
        {
            "name": "WeintCompanion-x86_64.AppImage.sha256",
            "browser_download_url": CHECKSUM_URL,
        },
    ]

    updater = _updater(
        _release_json(assets),
        checksum_bodies={CHECKSUM_URL: f"{VALID_HASH}  WeintCompanion-x86_64.AppImage"},
    )

    release = updater.get_latest_release()

    assert release.asset_name == "WeintCompanion-x86_64.AppImage"
    assert release.sha256 == VALID_HASH


def test_fallback_skips_checksum_files_when_no_filter_matches():
    """
    Ohne passenden Filter (z. B. ein unbekanntes Betriebssystem) fällt
    die Auswahl auf das erste Asset zurück. Steht dort zufällig die
    Prüfsummendatei, darf sie trotzdem nicht als Haupt-Asset enden.
    """

    assets = [
        {
            "name": "WeintCompanion-x86_64.AppImage.sha256",
            "browser_download_url": CHECKSUM_URL,
        },
        {
            "name": "WeintCompanion-Setup.exe",
            "browser_download_url": "https://example.invalid/setup.exe",
        },
    ]

    updater = _updater(_release_json(assets), asset_filter=None)
    updater._wanted_asset = lambda: None

    release = updater.get_latest_release()

    assert release.asset_name == "WeintCompanion-Setup.exe"


def test_sha256_is_none_when_no_checksum_asset_exists():

    assets = [
        {
            "name": "WeintCompanion-x86_64.AppImage",
            "browser_download_url": BINARY_URL,
        },
    ]

    updater = _updater(_release_json(assets))

    release = updater.get_latest_release()

    assert release.asset_name == "WeintCompanion-x86_64.AppImage"
    assert release.sha256 is None
