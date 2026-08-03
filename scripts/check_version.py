"""
Prüft, ob ein Tag und die Versionsnummern im Repo zusammenpassen.

Der Grund für dieses Skript ist ein Fehler, der dieses Projekt
inzwischen dreimal getroffen hat (v1.2.0, v1.2.1, v1.2.4): ein `git
tag vX.Y.Z` auf einem lokalen Stand, der noch nicht die zugehörige
Versionserhöhung enthielt. Der Tag zeigt dann auf einen älteren
Commit, die CI baut daraus ein Release mit dem Namen vX.Y.Z - und
darin steckt eine Anwendung, die sich selbst als ältere Version
meldet.

Das Ergebnis ist besonders unangenehm, weil nichts fehlschlägt:
Build grün, Release da, Installation läuft. Erst der Updater fällt
auf. Er sieht ein neueres Release als seine eigene Version, lädt es,
installiert es - und meldet danach unverändert die alte Version.
Eine Endlosschleife, aus der sich der Nutzer nicht befreien kann.

Deshalb bricht die CI ab, BEVOR gebaut wird. Lokal vor dem Taggen:

    python scripts/check_version.py v1.2.5

Geprüft werden alle Stellen, an denen die Version wirklich steht -
core/version.py ist die maßgebliche (der Updater vergleicht
ausschließlich sie), packaging/installer.iss trägt sie für den
Windows-Installer ein zweiten Mal, und der Changelog braucht einen
Abschnitt, sonst zeigt die "Was ist neu"-Ansicht nach dem Update
nichts an.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def normalize(value: str) -> str:
    """
    "v1.2.4", "V1.2.4" und "1.2.4" sind dieselbe Version.
    """

    return (value or "").strip().lstrip("vV")


def version_py() -> str:

    text = (ROOT / "core" / "version.py").read_text(encoding="utf-8")

    match = re.search(r'VERSION\s*=\s*"([^"]+)"', text)

    return match.group(1) if match else ""


def installer_iss() -> str:

    path = ROOT / "packaging" / "installer.iss"

    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8")

    match = re.search(
        r'#define\s+MyAppVersion\s+"([^"]+)"',
        text,
    )

    return match.group(1) if match else ""


def changelog_has(version: str) -> bool:
    """
    Ein Abschnitt "## 1.2.4" im Changelog.

    Nicht bloß Kosmetik: gui/dialogs/whats_new_dialog.py liest genau
    diese Überschriften, um nach einem Update die Änderungen zu
    zeigen. Fehlt der Abschnitt, bleibt das Fenster leer.
    """

    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    return bool(
        re.search(
            rf"^##\s+v?{re.escape(version)}\s*$",
            text,
            re.MULTILINE,
        )
    )


def check(tag: str) -> list[str]:
    """
    Liefert die Liste der Beanstandungen - leer heißt "in Ordnung".
    """

    wanted = normalize(tag)

    problems = []

    if not wanted:

        return ["Kein Tag übergeben."]

    if not re.fullmatch(r"\d+\.\d+\.\d+", wanted):

        problems.append(
            f"Tag '{tag}' ist keine Version der Form vX.Y.Z."
        )

    for label, path, found in (
        ("core/version.py", "VERSION", version_py()),
        ("packaging/installer.iss", "MyAppVersion", installer_iss()),
    ):

        if not found:

            problems.append(
                f"{label}: {path} nicht gefunden."
            )

            continue

        if normalize(found) != wanted:

            problems.append(
                f"{label}: {path} steht auf {found}, "
                f"der Tag lautet aber {tag}."
            )

    if not changelog_has(wanted):

        problems.append(
            f"CHANGELOG.md: kein Abschnitt '## {wanted}'."
        )

    return problems


def main() -> int:

    tag = sys.argv[1] if len(sys.argv) > 1 else ""

    problems = check(tag)

    if not problems:

        print(f"Version {normalize(tag)} ist überall eingetragen.")

        return 0

    print(
        f"Tag und Repo passen nicht zusammen (Tag: {tag or '-'}):",
        file=sys.stderr,
    )

    for problem in problems:

        print(f"  - {problem}", file=sys.stderr)

    print(
        "\nWahrscheinlichste Ursache: getaggt wurde ein Stand ohne "
        "die Versionserhöhung. Prüfen mit\n"
        "    git log --oneline -1 " + (tag or "<tag>") + "\n"
        "und den Tag auf den richtigen Commit setzen, statt das "
        "Release so zu veröffentlichen - ein Build mit falscher "
        "Versionsnummer bringt jeden Updater in eine Endlosschleife.",
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":

    raise SystemExit(main())
