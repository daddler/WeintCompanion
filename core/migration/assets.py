"""
Welche Datei eines Releases zu diesem Rechner gehoert.

"Nimm das erste Asset" ist die Fassung dieses Problems, die immer
funktioniert, bis sie es einmal nicht tut - und dann installiert sie
einen Windows-Installer unter Linux oder eine ARM-AppImage auf einem
x86-Rechner. Deshalb steht die Auswahl hier, an einer Stelle, als
Tabelle: jede Zielplattform ein Eintrag, und alles, was sie von einer
anderen unterscheidet, ein Feld darin (dieselbe Bauart wie
`core/wow_clients.py`).

LINUX UND WINDOWS SIND GLEICHRANGIG
-----------------------------------

Nicht "Windows, und Linux irgendwie auch": beide stehen als Eintrag
in derselben Tabelle, beide durchlaufen dieselbe Auswahl, und der
einzige Unterschied zwischen ihnen sind die Dateiendungen, die sie
akzeptieren.

WAS AUSDRUECKLICH KEIN KANDIDAT IST
-----------------------------------

Pruefsummen (`.sha256`), Signaturen (`.sig`, `.asc`), Quelltext-
Archive. Sie liegen im selben Release und tragen denselben Namen wie
das Asset, zu dem sie gehoeren - eine Teilstringsuche nach
".appimage" findet die Pruefsumme genauso zuverlaessig wie die
AppImage selbst. Genau dieser Fehler hat den Companion-Updater
einmal mit "keine Pruefsumme verfuegbar" blockiert (siehe
`core/github_updater.py`), und er wird hier nicht wiederholt.

MEHRDEUTIG HEISST: KEINE AUSWAHL
--------------------------------

Liegen zwei gleich gut passende Installationsdateien im selben
Release, waehlt diese Datei **nicht**. Sie meldet `AMBIGUOUS`, das
Release gilt als unvollstaendig, und der Nutzer sieht kein Angebot -
lieber kein Wechsel als der Wechsel auf eine geratene Datei.
"""

from __future__ import annotations

from dataclasses import dataclass
import platform

from core.runtime import Runtime


#
# Endungen, die nie eine Installationsdatei sind.
#

_NEVER = (
    ".sha256",
    ".sha512",
    ".md5",
    ".sig",
    ".asc",
    ".pem",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
)

#
# Quelltextarchive. GitHub haengt sie an jedes Release, und ein
# "Source code (zip)" ist fuer eine Migration so brauchbar wie gar
# nichts.
#

_SOURCE_MARKERS = (
    "source code",
    "source-code",
)


@dataclass(frozen=True)
class PlatformProfile:
    """
    Eine Zielplattform.

    `suffixes` ist nach Vorzug geordnet: steht in einem Release
    sowohl ein `.exe` als auch ein `.msi`, gewinnt das `.exe`, weil
    es vorn steht - und nicht, weil es zufaellig frueher in der
    Antwort von GitHub stand.
    """

    key: str
    label: str
    suffixes: tuple[str, ...]
    package_label: str


WINDOWS = PlatformProfile(
    key="windows",
    label="Windows",
    suffixes=(".exe", ".msi"),
    package_label="Installer",
)

LINUX = PlatformProfile(
    key="linux",
    label="Linux",
    suffixes=(".appimage",),
    package_label="AppImage",
)

PROFILES = (WINDOWS, LINUX)


#
# Architekturen. Die Schluessel sind das, was `platform.machine()`
# liefert; die Werte das, was in Dateinamen steht.
#

_ARCH_ALIASES = {
    "x86_64": ("x86_64", "amd64", "x64", "win64"),
    "amd64": ("x86_64", "amd64", "x64", "win64"),
    "aarch64": ("aarch64", "arm64"),
    "arm64": ("aarch64", "arm64"),
    "i386": ("i386", "i686", "x86", "win32"),
    "i686": ("i386", "i686", "x86", "win32"),
}

_ALL_ARCH_TOKENS = tuple(
    sorted({token for tokens in _ARCH_ALIASES.values() for token in tokens})
)


@dataclass(frozen=True)
class ReleaseAsset:
    """
    Eine Datei an einem Release - unabhaengig davon, woher die
    Release-Liste kam (GitHub, Datei, Test).
    """

    name: str
    url: str
    size: int = 0
    content_type: str = ""


@dataclass(frozen=True)
class AssetChoice:

    asset: ReleaseAsset
    profile: PlatformProfile
    checksum: ReleaseAsset | None = None
    reason: str = ""


class AssetError(Exception):
    """
    Kein brauchbares Asset - mit Grund.

    `code` ist maschinenlesbar (`NO_MATCH`, `AMBIGUOUS`,
    `UNSUPPORTED_PLATFORM`), damit die Oberflaeche entscheiden kann,
    ob sie ueberhaupt etwas sagt.
    """

    def __init__(self, code: str, message: str):

        super().__init__(message)

        self.code = code
        self.message = message


def current_arch() -> str:

    return (platform.machine() or "").strip().lower()


def arch_tokens(machine: str | None = None) -> tuple[str, ...]:

    machine = (machine or current_arch()).lower()

    return _ARCH_ALIASES.get(machine, (machine,) if machine else ())


def current_profile() -> PlatformProfile | None:
    """
    Die Plattform, auf der diese App gerade laeuft - oder `None`.

    `None` ist kein Fehler, sondern macOS: die App laeuft dort
    ungetestet aus dem Quelltext (siehe `CompanionUpdater`), und ein
    Generationswechsel ohne Build, den jemand je ausgefuehrt hat,
    wird nicht angeboten.
    """

    if Runtime.is_windows():
        return WINDOWS

    if Runtime.is_linux():
        return LINUX

    return None


def _is_excluded(name: str) -> bool:

    lowered = name.lower()

    if any(lowered.endswith(suffix) for suffix in _NEVER):
        return True

    return any(marker in lowered for marker in _SOURCE_MARKERS)


def _arch_rank(name: str, wanted: tuple[str, ...]) -> int | None:
    """
    0 = traegt genau unsere Architektur im Namen,
    1 = nennt gar keine (eine Datei fuer alle),
    `None` = nennt eine fremde.

    Die Unterscheidung zwischen "keine genannt" und "fremde genannt"
    ist der ganze Punkt: ein Release, das nur
    "...-aarch64.AppImage" enthaelt, hat fuer einen x86-Rechner
    **nichts**, und das ist etwas anderes als ein Release mit einer
    architekturlosen Datei.
    """

    lowered = name.lower()

    found = [token for token in _ALL_ARCH_TOKENS if token in lowered]

    if not found:
        return 1

    if any(token in wanted for token in found):
        return 0

    return None


def select_asset(
    assets,
    profile: PlatformProfile | None = None,
    machine: str | None = None,
) -> AssetChoice:
    """
    Waehlt die Installationsdatei fuer diese Plattform.

    Wirft `AssetError`, wenn nichts passt oder zwei Dateien gleich
    gut passen - beides ist ein Befund ueber das Release, keine
    Ausnahme im Ablauf.
    """

    profile = profile or current_profile()

    if profile is None:

        raise AssetError(
            "UNSUPPORTED_PLATFORM",
            "Fuer diese Plattform wird kein Generationswechsel angeboten.",
        )

    wanted_arch = arch_tokens(machine)

    scored = []

    for asset in assets:

        name = asset.name or ""

        if not name or not asset.url or _is_excluded(name):
            continue

        lowered = name.lower()

        suffix_rank = next(
            (
                index
                for index, suffix in enumerate(profile.suffixes)
                if lowered.endswith(suffix)
            ),
            None,
        )

        if suffix_rank is None:
            continue

        rank = _arch_rank(name, wanted_arch)

        if rank is None:
            continue

        scored.append(((suffix_rank, rank), asset))

    if not scored:

        raise AssetError(
            "NO_MATCH",
            f"Das Release enthaelt keine {profile.package_label}-Datei "
            f"fuer {profile.label}.",
        )

    scored.sort(key=lambda item: (item[0], item[1].name.lower()))

    best_score = scored[0][0]

    tied = [asset for score, asset in scored if score == best_score]

    if len(tied) > 1:

        raise AssetError(
            "AMBIGUOUS",
            "Das Release enthaelt mehrere gleichwertige "
            f"{profile.package_label}-Dateien "
            f"({', '.join(asset.name for asset in tied)}) - "
            "es wird keine geraten.",
        )

    chosen = tied[0]

    return AssetChoice(
        asset=chosen,
        profile=profile,
        checksum=checksum_for(assets, chosen),
    )


def checksum_for(assets, asset: ReleaseAsset) -> ReleaseAsset | None:
    """
    Die zu `asset` gehoerende "<name>.sha256"-Datei, falls es sie
    gibt. Ob ein fehlender Hash den Wechsel abbricht, entscheidet
    nicht diese Datei - siehe `core/migration/integrity.py`.
    """

    wanted = f"{(asset.name or '').lower()}.sha256"

    return next(
        (
            candidate
            for candidate in assets
            if (candidate.name or "").lower() == wanted
        ),
        None,
    )
