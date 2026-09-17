"""
Was im Zielrepository liegt - und was davon brauchbar ist.

Sechs Ausgaenge, weil ein "nein" hier vier verschiedene Bedeutungen
hat (siehe `core/migration/discovery.py`). Genau die werden hier
einzeln festgehalten: sie sind der Unterschied zwischen "es gibt
noch nichts" (Normalfall, nichts anzeigen), "das Release ist
kaputt" (melden, es ist ein Fehler der anderen Seite) und "GitHub
war nicht erreichbar" (keine Aussage ueber das Release).
"""

import json

import pytest

from core.migration.assets import LINUX, WINDOWS, ReleaseAsset
from core.migration.discovery import Outcome, ReleaseDiscovery
from core.migration.releases import (
    GitHubReleaseSource,
    Release,
    ReleaseSource,
    ReleaseSourceError,
    StaticReleaseSource,
    release_from_api,
)
from core.migration.target import BETA, MigrationTarget, STABLE


def target(channel=STABLE, major=5):

    return MigrationTarget(
        owner="daddler",
        repo="Companion-Forever",
        product_name="Companion-Forever",
        major=major,
        channel=channel,
    )


def asset(name):

    return ReleaseAsset(name=name, url=f"https://example.invalid/{name}")


def release(tag, *, assets=("Companion-Forever-5.0.0-x86_64.AppImage",), draft=False):

    return Release(
        tag=tag,
        draft=draft,
        assets=tuple(asset(name) for name in assets),
    )


FULL = (
    "Companion-Forever-5.0.0-x86_64.AppImage",
    "Companion-Forever-5.0.0-x86_64.AppImage.sha256",
    "Companion-Forever-Setup-5.0.0-x64.exe",
    "Companion-Forever-Setup-5.0.0-x64.exe.sha256",
)


def find(releases, channel=STABLE, profile=LINUX, machine="x86_64"):

    return ReleaseDiscovery(
        source=StaticReleaseSource(releases),
        target=target(channel),
        profile=profile,
        machine=machine,
    ).find()


# --------------------------------------------------
# Kein Release
# --------------------------------------------------


def test_nothing_published_yet():
    """
    Der Normalfall, solange Companion-Forever entwickelt wird.
    """

    result = find([])

    assert result.outcome is Outcome.NO_RELEASE

    assert not result.available


def test_only_older_generations_is_also_nothing():
    """
    Eine 4.9.0 im Zielrepository ist kein Generationswechsel.
    """

    result = find([release("v4.9.0", assets=FULL)])

    assert result.outcome is Outcome.NO_RELEASE


def test_a_draft_does_not_count():

    result = find([release("v5.0.0", assets=FULL, draft=True)])

    assert result.outcome is Outcome.NO_RELEASE


# --------------------------------------------------
# Ein Stable-Release
# --------------------------------------------------


def test_a_stable_release_is_available():

    result = find([release("v5.0.0", assets=FULL)])

    assert result.available

    assert result.version_text == "5.0.0"

    assert result.choice.asset.name.endswith(".AppImage")


def test_windows_gets_its_own_asset_from_the_same_release():

    result = find([release("v5.0.0", assets=FULL)], profile=WINDOWS)

    assert result.available

    assert result.choice.asset.name.endswith(".exe")


# --------------------------------------------------
# Mehrere Releases
# --------------------------------------------------


def test_the_newest_of_several_wins():

    result = find(
        [
            release("v5.0.0", assets=FULL),
            release("v5.1.0", assets=FULL),
            release("v5.0.1", assets=FULL),
        ]
    )

    assert result.version_text == "5.1.0"


def test_a_later_generation_is_not_taken_either():
    """
    Diese App sucht genau die naechste Generation. Ein 6.0.0 im
    selben Repository gehoert einem spaeteren Wechsel - und der wird
    von einer 5.x aus angeboten, nicht von hier.
    """

    result = find([release("v6.0.0", assets=FULL)])

    assert result.outcome is Outcome.NO_RELEASE


# --------------------------------------------------
# Vorabfassungen
# --------------------------------------------------


def test_a_prerelease_is_not_offered_on_stable():

    result = find([release("v5.0.0-beta.1", assets=FULL)])

    assert result.outcome is Outcome.ONLY_PRERELEASE

    assert not result.available

    assert result.version_text == "5.0.0-beta.1"


def test_the_stable_release_wins_over_a_newer_prerelease():

    result = find(
        [
            release("v5.1.0-beta.2", assets=FULL),
            release("v5.0.0", assets=FULL),
        ]
    )

    assert result.available

    assert result.version_text == "5.0.0"


def test_on_the_beta_channel_the_prerelease_is_offered():

    result = find([release("v5.0.0-beta.1", assets=FULL)], channel=BETA)

    assert result.available

    assert result.version_text == "5.0.0-beta.1"


# --------------------------------------------------
# Ungueltiges Release
# --------------------------------------------------


def test_a_release_without_an_asset_for_this_platform_is_invalid():

    result = find([release("v5.0.0", assets=("Source code (zip)",))])

    assert result.outcome is Outcome.INVALID_RELEASE

    assert result.version_text == "5.0.0"

    assert not result.available


def test_an_invalid_release_is_not_silently_skipped_for_an_older_one():
    """
    Waere ein kaputtes 5.1.0 einfach uebersprungen worden, saehe der
    Nutzer ein Angebot auf 5.0.0 - und niemand wuerde je bemerken,
    dass das neuere Release unvollstaendig veroeffentlicht wurde.
    """

    result = find(
        [
            release("v5.1.0", assets=("Source code (zip)",)),
            release("v5.0.0", assets=FULL),
        ]
    )

    assert result.outcome is Outcome.INVALID_RELEASE

    assert result.version_text == "5.1.0"


# --------------------------------------------------
# Netz
# --------------------------------------------------


class BrokenSource(ReleaseSource):

    def fetch(self):
        raise ReleaseSourceError("Name oder Dienst nicht bekannt")


def test_a_network_failure_is_its_own_answer():

    result = ReleaseDiscovery(
        source=BrokenSource(),
        target=target(),
        profile=LINUX,
        machine="x86_64",
    ).find()

    assert result.outcome is Outcome.NETWORK_ERROR

    assert "Companion-Forever" in result.message


def test_an_unsupported_platform_asks_nobody(monkeypatch):

    monkeypatch.setattr(
        "core.migration.discovery.current_profile",
        lambda: None,
    )

    result = ReleaseDiscovery(
        source=BrokenSource(),
        target=target(),
        machine="x86_64",
    ).find()

    assert result.outcome is Outcome.UNSUPPORTED_PLATFORM


# --------------------------------------------------
# Die GitHub-Quelle selbst
# --------------------------------------------------


class FakeResponse:

    def __init__(self, payload=None, status_code=200):

        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):

        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeClient:

    def __init__(self, response):

        self.response = response
        self.calls = 0

    def get(self, url, params=None):

        self.calls += 1

        return self.response


def test_a_404_means_nothing_published_not_an_error():
    """
    Solange Companion-Forever privat ist, antwortet GitHub jedem
    ohne Rechte mit 404 - genau wie bei einem Repository ohne
    Releases. Daraus eine Fehlermeldung zu machen hiesse, jedem
    Nutzer eine rote Zeile ueber ein Repository zu zeigen, von dem er
    nichts wissen soll.
    """

    source = GitHubReleaseSource(
        "daddler",
        "Companion-Forever",
        client=FakeClient(FakeResponse(status_code=404)),
    )

    assert source.fetch() == []


def test_a_server_error_is_reported_as_one():

    source = GitHubReleaseSource(
        "daddler",
        "Companion-Forever",
        client=FakeClient(FakeResponse(status_code=500)),
    )

    with pytest.raises(ReleaseSourceError):
        source.fetch()


def test_an_unexpected_answer_is_reported_as_one():

    source = GitHubReleaseSource(
        "daddler",
        "Companion-Forever",
        client=FakeClient(FakeResponse(payload={"message": "nope"})),
    )

    with pytest.raises(ReleaseSourceError):
        source.fetch()


def test_the_release_list_is_cached_like_the_other_update_checks():

    client = FakeClient(FakeResponse(payload=[]))

    source = GitHubReleaseSource("daddler", "Companion-Forever", client=client)

    source.fetch()
    source.fetch()

    assert client.calls == 1

    source.invalidate()

    source.fetch()

    assert client.calls == 2


def test_a_release_without_a_tag_is_not_a_release():

    assert release_from_api({"name": "ohne Tag"}) is None


def test_the_dry_run_source_reads_the_github_format(tmp_path):
    """
    Der Probelauf arbeitet gegen eine Datei im **selben** Format wie
    die echte Antwort: wer den Ernstfall proben will, speichert die
    echte Antwort weg und laesst die Migration dagegen laufen.
    """

    path = tmp_path / "releases.json"

    path.write_text(
        json.dumps(
            [
                {
                    "tag_name": "v5.0.0",
                    "assets": [
                        {
                            "name": name,
                            "browser_download_url": f"https://x.invalid/{name}",
                        }
                        for name in FULL
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = ReleaseDiscovery(
        source=StaticReleaseSource.from_file(path),
        target=target(),
        profile=LINUX,
        machine="x86_64",
    ).find()

    assert result.available

    assert result.version_text == "5.0.0"
