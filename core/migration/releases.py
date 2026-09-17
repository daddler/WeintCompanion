"""
Woher die Liste der Releases kommt.

Bewusst eine eigene Schicht und nicht eine Erweiterung von
`core/github_updater.py`: der bestehende Updater fragt
`releases/latest` und beantwortet damit "gibt es etwas Neueres als
mich". Fuer den Generationswechsel ist genau das die falsche Frage.
`releases/latest` liefert **immer nur eine** Veroeffentlichung, und
welche das ist, entscheidet GitHub nach seinen eigenen Regeln - eine
5.0.0, die neben einer 5.1.0-beta.2 liegt, kann dort fehlen, und eine
4.x im Zielrepository wuerde faelschlich als "die naechste
Generation" durchgehen.

Deshalb wird hier die **Liste** geholt und in
`core/migration/discovery.py` ausgewaehlt. Der bestehende Updater
bleibt unangetastet; er macht seine Arbeit richtig.

WARUM EINE SCHNITTSTELLE UND NICHT NUR GITHUB
---------------------------------------------

`ReleaseSource` ist ein schmaler Vertrag mit einer Methode. Daran
haengen drei Dinge, die sonst nicht gingen: der Probelauf
(`StaticReleaseSource` aus einer Datei, ohne Netz), die Tests, und
die Moeglichkeit, die Verteilung spaeter umzustellen, ohne die
Migration neu zu schreiben. Die GitHub-Actions-Pipeline von
Companion-Forever ist an keiner Stelle vorausgesetzt - nur, dass am
Ende ein Release mit Assets dasteht.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

from core.migration.assets import ReleaseAsset
from core.version import ReleaseVersion, parse_release


class ReleaseSourceError(Exception):
    """
    Die Liste konnte nicht geholt werden (Netz, Rate-Limit, Antwort
    unlesbar). Ausdruecklich etwas anderes als "es gibt kein
    Release": das eine ist ein Problem auf dem Weg, das andere eine
    Auskunft.
    """


@dataclass(frozen=True)
class Release:

    tag: str
    name: str = ""
    body: str = ""
    published_at: str = ""
    draft: bool = False
    prerelease: bool = False
    assets: tuple[ReleaseAsset, ...] = ()

    @property
    def version(self) -> ReleaseVersion | None:
        return parse_release(self.tag)


def _assets_from(raw) -> tuple[ReleaseAsset, ...]:

    assets = []

    for item in raw or []:

        if not isinstance(item, dict):
            continue

        assets.append(
            ReleaseAsset(
                name=str(item.get("name") or ""),
                url=str(item.get("browser_download_url") or item.get("url") or ""),
                size=int(item.get("size") or 0),
                content_type=str(item.get("content_type") or ""),
            )
        )

    return tuple(assets)


def release_from_api(data) -> Release | None:
    """
    Eine Release-Antwort von GitHub in unsere Form.

    `None` bei allem, was keinen Tag traegt - eine Veroeffentlichung
    ohne Tag ist fuer uns nicht ansprechbar.
    """

    if not isinstance(data, dict):
        return None

    tag = str(data.get("tag_name") or "").strip()

    if not tag:
        return None

    return Release(
        tag=tag,
        name=str(data.get("name") or ""),
        body=str(data.get("body") or ""),
        published_at=str(data.get("published_at") or ""),
        draft=bool(data.get("draft")),
        prerelease=bool(data.get("prerelease")),
        assets=_assets_from(data.get("assets")),
    )


class ReleaseSource:
    """
    Der Vertrag: eine Methode, die Releases liefert - neueste zuerst
    oder unsortiert, das entscheidet die Auswahl.
    """

    def fetch(self) -> list[Release]:
        raise NotImplementedError

    def invalidate(self) -> None:
        pass


class StaticReleaseSource(ReleaseSource):
    """
    Releases aus einer Liste oder einer JSON-Datei - fuer den
    Probelauf und die Tests.

    Das Dateiformat ist absichtlich dasselbe wie die GitHub-Antwort:
    wer den Ernstfall proben will, speichert die echte Antwort weg
    und laesst die Migration dagegen laufen.
    """

    def __init__(self, releases):

        self._releases = list(releases or [])

    @classmethod
    def from_file(cls, path) -> "StaticReleaseSource":

        path = Path(path)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReleaseSourceError(
                f"Release-Datei {path.name} nicht lesbar: {exc}"
            ) from exc

        if isinstance(data, dict):
            data = [data]

        releases = [
            release
            for release in (release_from_api(item) for item in data)
            if release is not None
        ]

        return cls(releases)

    def fetch(self) -> list[Release]:
        return list(self._releases)


class GitHubReleaseSource(ReleaseSource):
    """
    Die Releases eines Repositories, mit demselben
    Zwischenspeicher-Takt wie die uebrigen Update-Pruefungen
    (15 Minuten, siehe `core/github_updater.py`).

    EIN 404 IST KEIN FEHLER. Solange Companion-Forever nicht
    oeffentlich ist, antwortet GitHub auf jede Anfrage ohne Rechte
    mit 404 - genau wie bei einem Repository ohne jedes Release.
    Beides heisst fuer uns dasselbe: **noch nichts da**. Daraus eine
    Fehlermeldung zu machen hiesse, jedem Nutzer eine rote Zeile
    ueber ein Repository zu zeigen, von dem er nichts wissen soll.
    """

    def __init__(self, owner: str, repo: str, per_page: int = 30, client=None):

        self.owner = owner
        self.repo = repo
        self.per_page = per_page

        self.api_url = (
            f"https://api.github.com/repos/{owner}/{repo}/releases"
        )

        self._client = client

        self._cached: list[Release] | None = None
        self._last_check: datetime | None = None

        self.cache_duration = timedelta(minutes=15)

    # --------------------------------------------------

    @property
    def client(self):

        if self._client is None:

            import httpx

            self._client = httpx.Client(
                follow_redirects=True,
                timeout=15,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "WeintCompanion",
                },
            )

        return self._client

    # --------------------------------------------------

    def invalidate(self) -> None:

        self._cached = None
        self._last_check = None

    # --------------------------------------------------

    def fetch(self) -> list[Release]:

        if (
            self._cached is not None
            and self._last_check is not None
            and datetime.now() - self._last_check < self.cache_duration
        ):
            return list(self._cached)

        try:

            response = self.client.get(
                self.api_url,
                params={"per_page": self.per_page},
            )

            if getattr(response, "status_code", 200) == 404:

                #
                # Siehe Klassenkommentar: "gibt es nicht (fuer mich)"
                # ist eine leere Liste, kein Fehler.
                #

                self._cached = []
                self._last_check = datetime.now()

                return []

            response.raise_for_status()

            data = response.json()

        except ReleaseSourceError:

            raise

        except Exception as exc:

            raise ReleaseSourceError(str(exc)) from exc

        if not isinstance(data, list):

            raise ReleaseSourceError(
                "Unerwartete Antwort der Release-Schnittstelle."
            )

        releases = [
            release
            for release in (release_from_api(item) for item in data)
            if release is not None
        ]

        self._cached = releases
        self._last_check = datetime.now()

        return list(releases)
