"""
Gibt es die naechste Generation - und ist sie brauchbar?

Diese Datei beantwortet genau eine Frage und beantwortet sie
vollstaendig: **sechs** Ausgaenge, nicht "ja/nein". Das ist kein
Selbstzweck. Ein "nein" hat hier vier voellig verschiedene
Bedeutungen, und jede verlangt etwas anderes von der Oberflaeche:

- `NO_RELEASE` - noch nichts veroeffentlicht. Der Normalfall,
  solange Companion-Forever entwickelt wird. Es wird nichts gezeigt,
  nichts protokolliert, nichts wiederholt.
- `ONLY_PRERELEASE` - es gibt etwas, aber nur eine Vorabfassung.
  Auf dem Kanal "stable" wird sie **nicht** angeboten. Der Zustand
  ist trotzdem eigen, weil er einem Entwickler sagt: der Kanal
  stimmt nicht, nicht das Release.
- `INVALID_RELEASE` - es gibt eine fertige Fassung, aber sie haelt
  den Release-Vertrag nicht ein (kein Asset fuer diese Plattform,
  mehrere gleichwertige, keine Pruefsumme). Das ist ein Fehler des
  Releases und muss sichtbar sein - sonst sucht man ihn in der App.
- `NETWORK_ERROR` - GitHub war nicht erreichbar. Keine Aussage ueber
  das Release, nur ueber den Weg dorthin.
- `UNSUPPORTED_PLATFORM` - diese App laeuft irgendwo, wofuer es
  keinen Build gibt (macOS aus dem Quelltext).
- `AVAILABLE` - alles steht.

WAS HIER NICHT ENTSCHIEDEN WIRD
-------------------------------

Ob der Wechsel angeboten werden **darf** (Schalter, bereits
migriert, verschoben) - das ist `MigrationService`. Diese Datei
kennt keinen Zustand und keine Konfiguration; sie bekommt eine
Quelle und ein Ziel und sagt, was dort liegt. Genau deshalb ist sie
ohne Netz und ohne Qt testbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.migration.assets import (
    AssetChoice,
    AssetError,
    PlatformProfile,
    current_profile,
    select_asset,
)
from core.migration.releases import Release, ReleaseSource, ReleaseSourceError
from core.migration.target import MigrationTarget
from core.version import ReleaseVersion, sort_key


class Outcome(str, Enum):

    NO_RELEASE = "no_release"
    ONLY_PRERELEASE = "only_prerelease"
    INVALID_RELEASE = "invalid_release"
    NETWORK_ERROR = "network_error"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    AVAILABLE = "available"


@dataclass(frozen=True)
class DiscoveryResult:

    outcome: Outcome
    version: ReleaseVersion | None = None
    release: Release | None = None
    choice: AssetChoice | None = None
    message: str = ""

    @property
    def available(self) -> bool:
        return self.outcome is Outcome.AVAILABLE

    @property
    def version_text(self) -> str:
        return str(self.version) if self.version else ""


def _candidates(releases, target: MigrationTarget):
    """
    Alles, was zur Zielgeneration gehoert und kein Entwurf ist -
    neueste zuerst.

    Ein Entwurf (`draft`) ist auf GitHub nur fuer den Autor sichtbar
    und noch nicht veroeffentlicht. Das `prerelease`-Kennzeichen
    dagegen wird hier **nicht** ausgewertet: massgeblich ist der Tag
    (`5.0.0-beta.1`), nicht das Haekchen daneben. Beides kann
    auseinanderlaufen, und der Tag ist das, was der Nutzer spaeter
    als Fassung sieht.
    """

    matching = []

    for release in releases:

        if release.draft:
            continue

        version = release.version

        if version is None or version.major != target.major:
            continue

        matching.append((release, version))

    matching.sort(key=lambda item: sort_key(item[1]), reverse=True)

    return matching


class ReleaseDiscovery:

    def __init__(
        self,
        source: ReleaseSource,
        target: MigrationTarget,
        profile: PlatformProfile | None = None,
        machine: str | None = None,
    ):

        self.source = source
        self.target = target
        self.profile = profile
        self.machine = machine

    # --------------------------------------------------

    def find(self) -> DiscoveryResult:

        profile = self.profile or current_profile()

        if profile is None:

            return DiscoveryResult(
                Outcome.UNSUPPORTED_PLATFORM,
                message=(
                    "Fuer diese Plattform gibt es keinen "
                    f"{self.target.product_name}-Build."
                ),
            )

        try:

            releases = self.source.fetch()

        except ReleaseSourceError as exc:

            return DiscoveryResult(
                Outcome.NETWORK_ERROR,
                message=(
                    f"{self.target.slug} konnte nicht abgefragt werden: {exc}"
                ),
            )

        candidates = _candidates(releases, self.target)

        if not candidates:

            return DiscoveryResult(
                Outcome.NO_RELEASE,
                message=(
                    f"Noch keine Fassung {self.target.major}.x in "
                    f"{self.target.slug}."
                ),
            )

        allowed = [
            (release, version)
            for release, version in candidates
            if self.target.allows_prerelease(version)
        ]

        if not allowed:

            newest = candidates[0][1]

            return DiscoveryResult(
                Outcome.ONLY_PRERELEASE,
                version=newest,
                release=candidates[0][0],
                message=(
                    f"{self.target.product_name} {newest} ist eine "
                    "Vorabfassung und wird auf dem Kanal "
                    f"\"{self.target.channel}\" nicht angeboten."
                ),
            )

        release, version = allowed[0]

        try:

            choice = select_asset(
                release.assets,
                profile=profile,
                machine=self.machine,
            )

        except AssetError as exc:

            return DiscoveryResult(
                Outcome.INVALID_RELEASE,
                version=version,
                release=release,
                message=(
                    f"{self.target.product_name} {version}: {exc.message}"
                ),
            )

        return DiscoveryResult(
            Outcome.AVAILABLE,
            version=version,
            release=release,
            choice=choice,
            message=(
                f"{self.target.product_name} {version} steht bereit "
                f"({choice.asset.name})."
            ),
        )
