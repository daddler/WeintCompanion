from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx


@dataclass
class GitHubRelease:

    version: str
    name: str
    changelog: str
    download_url: str
    published_at: str
    asset_name: str


class GitHubUpdater:

    API_URL = (
        "https://api.github.com/repos/"
        "daddler/WeintCodex/releases/latest"
    )

    def __init__(self):

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

    def get_latest_release(self):

        #
        # Cache verwenden
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

        #
        # GitHub abfragen
        #

        try:

            response = self.client.get(
                self.API_URL
            )

            response.raise_for_status()

            data = response.json()

            asset_name = ""
            download_url = ""

            for asset in data.get(
                "assets",
                [],
            ):

                name = asset.get(
                    "name",
                    "",
                )

                if (
                    name.lower().startswith(
                        "weintcodex"
                    )
                    and
                    name.lower().endswith(
                        ".zip"
                    )
                ):

                    asset_name = name

                    download_url = asset.get(
                        "browser_download_url",
                        "",
                    )

                    break

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

            #
            # Cache aktualisieren
            #

            self._cached_release = release
            self._last_check = datetime.now()

            return release

        #
        # GitHub Rate Limit
        #

        except httpx.HTTPStatusError as e:

            if e.response.status_code == 403:

                print(
                    "GitHub API Rate Limit erreicht."
                )

            else:

                print(
                    f"GitHubUpdater: {e}"
                )

            return None

        #
        # Netzwerkfehler
        #

        except Exception as e:

            print(
                f"GitHubUpdater: {e}"
            )

            return None