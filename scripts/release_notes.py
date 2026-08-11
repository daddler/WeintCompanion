"""
Den Changelog-Abschnitt eines Tags als Release-Text ausgeben.

    python scripts/release_notes.py v2.0.2 > notes.md

**Warum das gebraucht wird.** Der Release-Text war bis 2.0.1
`generate_release_notes: true`, also die von GitHub erzeugte
Commit-Liste. Für den Entwickler ist das brauchbar, für den Nutzer
nicht: in der App stand unter "Addon & Updates" eine Reihe von
Commit-Betreffen, und beim Addon - dessen Releases von Hand mit leerem
Notes-Feld angelegt wurden - stand "Keine Änderungen gefunden.".

Beide Repositorys pflegen aber ohnehin eine `CHANGELOG.md` (die CI
bricht sogar ab, wenn der Abschnitt zum Tag fehlt, siehe
`scripts/check_version.py`). Der Release-Text ist deshalb genau dieser
Abschnitt - eine Quelle, drei Orte: GitHub, das "Was ist neu"-Fenster
und die Änderungsansicht in der App.

Bewusst ohne Import aus `core/`: das Skript läuft in der CI vor jeder
Installation von Abhängigkeiten, und ein `from core...` würde es an
den Importpfad der Anwendung binden.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

HEADER_RE = re.compile(
    r"^##\s+\[?v?(\d[\w.]*)\]?\s*(?:[–—-]\s*(.+?))?\s*$"
)


def normalize(value: str) -> tuple[int, ...]:

    digits = re.findall(r"\d+", (value or "").strip().lstrip("vV"))

    numbers = [int(part) for part in digits] or [0]

    while len(numbers) < 4:
        numbers.append(0)

    return tuple(numbers[:4])


def section_for(text: str, version: str) -> str:
    """
    Der Text unter der Überschrift dieser Fassung.

    Leer, wenn es sie nicht gibt - der Aufrufer entscheidet dann, ob
    das ein Fehler ist.
    """

    wanted = normalize(version)

    collecting = False

    lines: list[str] = []

    for line in text.splitlines():

        match = HEADER_RE.match(line)

        if match:

            if collecting:
                break

            collecting = normalize(match.group(1)) == wanted

            continue

        if collecting:
            lines.append(line)

    return "\n".join(lines).strip()


def main() -> int:

    tag = sys.argv[1] if len(sys.argv) > 1 else ""

    path = ROOT / "CHANGELOG.md"

    if not path.exists():

        print(
            f"CHANGELOG.md nicht gefunden ({path}).",
            file=sys.stderr,
        )

        return 1

    body = section_for(path.read_text(encoding="utf-8"), tag)

    if not body:

        print(
            f"Kein Changelog-Abschnitt für {tag or '-'} gefunden.",
            file=sys.stderr,
        )

        return 1

    print(body)

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
