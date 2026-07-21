from dataclasses import dataclass
from datetime import datetime, timedelta
import platform

import httpx

from core.version import parse_version


@dataclass
class GitHubRelease:

    version: str
    name: str
    changelog: str
    download_url: str
    published_at: str
    asset_name: str


class GitHubUpdater:

    def __init__(
        self,
        owner: str,
        repo: str,
        asset_filter: str | None = None,
    ):

        self.owner = owner
        self.repo = repo
        self.asset_filter = asset_filter

        self.api_url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/releases/latest"
        )

        self.client = httpx.Client(
            follow_redirects=True,
            timeout=15,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "WeintCompanion",
            },
        )

        #
        # Cache
        #

        self._cached_release = None
        self._last_check = None

        self.cache_duration = timedelta(
            minutes=15
        )

    # --------------------------------------------------

    def _wanted_asset(self):

        #
        # Expliziter Filter
        #

        if self.asset_filter:

            return self.asset_filter.lower()

        #
        # Companion automatisch erkennen
        #

        system = platform.system()

        if system == "Windows":

            return "setup.exe"

        if system == "Linux":

            return ".appimage"

        if system == "Darwin":

            return ".dmg"

        return None

    # --------------------------------------------------

    def get_latest_release(self):

        #
        # Cache
        #

        if (
            self._cached_release is not None
            and self._last_check is not None
        ):

            if (
                datetime.now()
                - self._last_check
                < self.cache_duration
            ):

                return self._cached_release

        try:

            response = self.client.get(
                self.api_url
            )

            response.raise_for_status()

            data = response.json()

            assets = data.get(
                "assets",
                [],
            )

            asset_name = ""
            download_url = ""

            wanted = self._wanted_asset()

            #
            # Passendes Asset suchen
            #

            for asset in assets:

                name = asset.get(
                    "name",
                    "",
                ).lower()

                if wanted and wanted in name:

                    asset_name = asset.get(
                        "name",
                        "",
                    )

                    download_url = asset.get(
                        "browser_download_url",
                        "",
                    )

                    break

            #
            # Fallback:
            # Falls kein Filter passt, erstes Asset nehmen.
            #

            if not download_url and assets:

                asset = assets[0]

                asset_name = asset.get(
                    "name",
                    "",
                )

                download_url = asset.get(
                    "browser_download_url",
                    "",
                )

            release = GitHubRelease(

                version=data.get(
                    "tag_name",
                    "",
                ),

                name=data.get(
                    "name",
                    "",
                ),

                changelog=data.get(
                    "body",
                    "",
                ),

                download_url=download_url,

                published_at=data.get(
                    "published_at",
                    "",
                ),

                asset_name=asset_name,

            )

            self._cached_release = release
            self._last_check = datetime.now()

            return release

        except httpx.HTTPStatusError as e:

            if e.response.status_code == 403:

                print(
                    "GitHub API Rate Limit erreicht."
                )

            elif e.response.status_code == 404:

                print(
                    f"Kein Release für {self.repo} gefunden."
                )

            else:

                print(
                    f"GitHubUpdater: {e}"
                )

            return None

        except Exception as e:

            print(
                f"GitHubUpdater: {e}"
            )

            return None

    # --------------------------------------------------
    # Commits eines Releases ("was wurde committed")
    # --------------------------------------------------

    def get_release_commits(self, tag_name):
        """
        Liefert die Commit-Titel, die im Release "tag_name" enthalten
        sind - verglichen mit dem direkt davor veröffentlichten
        Release (GitHubs eigene Release-Notes listen bei Direkt-
        Pushes auf den Standardbranch ohne Pull-Request oft nur den
        Vergleichslink, keine einzelnen Änderungen).

        Rückgabe: Liste von Commit-Titeln, [] wenn es kein
        vorheriges Release gibt (erstes Release), None bei einem
        Fehler (z. B. Rate-Limit, kein Netzwerk).
        """

        try:

            response = self.client.get(
                f"https://api.github.com/repos/"
                f"{self.owner}/{self.repo}/releases",
                params={"per_page": 100},
            )

            response.raise_for_status()

            releases = response.json()

        except Exception as e:

            print(
                f"GitHubUpdater: {e}"
            )

            return None

        tags = [
            release.get("tag_name", "")
            for release in releases
        ]

        #
        # Tag-Vergleich per parse_version statt reinem String-
        # Vergleich: ein Tag wie "v0.8" muss dieselbe Version wie
        # "0.8.0" treffen, sonst findet z. B. der Changelog-Abruf
        # kein passendes Release, obwohl es eines gibt.
        #

        wanted = parse_version(tag_name)

        index = next(
            (
                i for i, tag in enumerate(tags)
                if parse_version(tag) == wanted
            ),
            None,
        )

        if index is None:
            return None

        if index + 1 >= len(tags):
            return []

        current_tag = tags[index]
        previous_tag = tags[index + 1]

        try:

            response = self.client.get(
                f"https://api.github.com/repos/"
                f"{self.owner}/{self.repo}/compare/"
                f"{previous_tag}...{current_tag}"
            )

            response.raise_for_status()

            data = response.json()

        except Exception as e:

            print(
                f"GitHubUpdater: {e}"
            )

            return None

        commits = []

        for commit in data.get("commits", []):

            message = (
                commit.get("commit", {})
                .get("message", "")
            )

            title = (
                message.splitlines()[0]
                if message
                else ""
            )

            if title:
                commits.append(title)

        return commits