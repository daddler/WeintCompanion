import re

from dataclasses import dataclass, field


VERSION = "4.1.0"


def parse_version(value):
    """
    Zerlegt eine Versionsangabe in ein Zahlen-Tupel, fehlende Teile
    werden mit 0 aufgefüllt - "0.8" und "0.8.0" ergeben so denselben
    Wert (0, 8, 0). Ohne das würden GitHub-Tags wie "v0.8" (statt
    "v0.8.0") beim reinen String-Vergleich als andere Version gelten
    und fälschlich ein "Update verfügbar" bzw. "Changelog nicht
    gefunden" auslösen.
    """

    value = (
        (value or "")
        .strip()
        .lower()
        .removeprefix("v")
    )

    numbers = []

    for part in value.split("."):

        digits = ""

        for char in part:

            if char.isdigit():
                digits += char
            else:
                break

        numbers.append(
            int(digits) if digits else 0
        )

    while len(numbers) < 3:
        numbers.append(0)

    return tuple(numbers)


def versions_equal(a, b):

    return parse_version(a) == parse_version(b)


# --------------------------------------------------
# Semantische Fassungen (Generationswechsel)
# --------------------------------------------------
#
# `parse_version()` oben beantwortet genau eine Frage: "ist das
# dieselbe Fassung wie meine". Dafuer reicht ein Zahlentupel, und
# alles, was keine Ziffer ist, darf wegfallen - "v1.2.0-beta.1" und
# "1.2.0" gelten dort bewusst als gleich, weil der Updater eine
# Vorabfassung nie zu Gesicht bekommt (die GitHub-Abfrage holt nur
# `releases/latest`, und das ist nie ein Pre-Release).
#
# Beim Wechsel auf eine neue Generation stimmt beides nicht mehr:
# eine Vorabfassung MUSS von der fertigen unterscheidbar sein (sonst
# wandert die halbe Nutzerschaft auf "5.0.0-beta.1"), und "neuer als"
# muss wirklich vergleichen und nicht nur "gleich/ungleich" sagen.
# Deshalb steht hier eine zweite, strengere Lesart daneben statt
# einer Erweiterung der ersten: die alte Funktion haengt an jedem
# bestehenden Update-Pfad, und eine geschaerfte Fassung davon waere
# eine stille Verhaltensaenderung an genau der Stelle, die niemand
# nachprueft.
#

_SEMVER = re.compile(
    r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.\-]+))?(?:\+([0-9A-Za-z.\-]+))?$"
)


@dataclass(frozen=True)
class ReleaseVersion:
    """
    Eine Fassung, wie sie an einem Release-Tag steht.

    `prerelease` traegt das, was hinter dem Bindestrich steht
    ("beta.1", "rc.2", "nightly") - leer heisst: fertige Fassung.
    Der Baumetadaten-Teil hinter "+" wird gelesen, aber nie
    verglichen (so schreibt es SemVer vor).
    """

    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    #
    # Die Schreibweise, aus der diese Fassung gelesen wurde ("v5.0.0"
    # oder "5.0.0"). Sie zaehlt beim Vergleichen ausdruecklich NICHT
    # mit: "v5.0.0" und "5.0.0" sind dieselbe Fassung, und ein
    # fuehrendes v ist eine Angewohnheit des Taggenden, keine
    # Eigenschaft der Fassung.
    #

    raw: str = field(default="", compare=False)

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def __str__(self) -> str:

        text = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            text += f"-{self.prerelease}"

        return text


def parse_release(value) -> ReleaseVersion | None:
    """
    Zerlegt einen Release-Tag. `None` heisst: das ist keine Fassung.

    Bewusst streng - im Gegensatz zu `parse_version()`, das aus jeder
    Zeichenkette ein Tupel macht. Bei der Suche nach der naechsten
    Generation lesen wir *fremde* Tags (aus einem Repository, das
    jemand anders taggt); aus "latest", "nightly" oder einem
    versehentlichen "release-5" darf dort keine Fassung "0.0.0"
    werden, die dann auch noch mitverglichen wird.
    """

    text = (value or "").strip()

    match = _SEMVER.match(text)

    if match is None:
        return None

    return ReleaseVersion(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3) or 0),
        prerelease=match.group(4) or "",
        build=match.group(5) or "",
        raw=text,
    )


def _prerelease_key(prerelease: str):
    """
    Vorabfassungen nach SemVer-Regeln vergleichbar machen: Zahlen
    zaehlen als Zahlen ("beta.9" < "beta.10"), alles andere als Text,
    und Zahlen stehen vor Text.
    """

    parts = []

    for part in prerelease.split("."):

        if part.isdigit():
            parts.append((0, int(part), ""))
        else:
            parts.append((1, 0, part))

    return parts


def sort_key(version: ReleaseVersion):
    """
    Ordnungsschluessel fuer `sorted()`/`max()`.

    Eine fertige Fassung steht ueber jeder Vorabfassung derselben
    Nummer (5.0.0 > 5.0.0-rc.1) - deshalb die 1 bzw. 0 an vierter
    Stelle.
    """

    return (
        version.major,
        version.minor,
        version.patch,
        0 if version.is_prerelease else 1,
        _prerelease_key(version.prerelease) if version.is_prerelease else [],
    )


def is_newer(candidate, current) -> bool:
    """
    Ist `candidate` (Tag oder ReleaseVersion) neuer als `current`?

    Unlesbare Angaben sind nie neuer - lieber nichts anbieten als
    etwas Erfundenes.
    """

    left = candidate if isinstance(candidate, ReleaseVersion) else parse_release(candidate)
    right = current if isinstance(current, ReleaseVersion) else parse_release(current)

    if left is None or right is None:
        return False

    return sort_key(left) > sort_key(right)


def major_of(value) -> int | None:
    """
    Die Generation einer Fassung, oder `None` bei etwas Unlesbarem.
    """

    version = value if isinstance(value, ReleaseVersion) else parse_release(value)

    return None if version is None else version.major
