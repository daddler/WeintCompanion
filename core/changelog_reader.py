"""
CHANGELOG.md lesen - für das "Was ist neu"-Fenster, für die
Änderungsansicht und für den Update-Hinweis auf der Übersicht.

**Zwei Schreibweisen, ein Leser.** Die Companion schreibt ihre
Überschriften als `## 2.0.1`, das Addon als
`## [1.3.3.1] – 2026-08-11`. Beide Dateien landen inzwischen in
derselben Ansicht (Einstellungen und Übersicht zeigen den Changelog
beider Komponenten), also muss ein Leser beide verstehen. Ein zweiter
Parser wäre eine Datei, die irgendwann nur noch die eine Hälfte
kennt - und das Symptom wäre eine leere Änderungsliste, die von "es
gab keine Änderungen" nicht zu unterscheiden ist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.resources import Resources
from core.version import parse_version

#
# `## 2.0.1`, `## [1.3.3.1] – 2026-08-11`, `## v1.3.3.1 - 11.08.2026`.
# Die Version selbst muss mit einer Ziffer beginnen; eine Überschrift
# wie "## Unveröffentlicht" ist damit keine Version und wird
# übersprungen, statt als Fassung "Unveröffentlicht" aufzutauchen.
#

_HEADER_RE = re.compile(
    r"^##\s+\[?v?(\d[\w.]*)\]?\s*(?:[–—-]\s*(.+?))?\s*$"
)


@dataclass(frozen=True)
class ChangelogEntry:
    """Eine Fassung mit ihrem Datum und ihrem Text."""

    version: str

    date: str

    body: str


def _split_sections(text: str) -> list[tuple[str, str]]:
    """
    Zerlegt den CHANGELOG-Text in (Version, Body)-Paare, in der
    Reihenfolge der Datei (neueste zuerst, wie in CHANGELOG.md
    üblich). Alles vor der ersten "## "-Überschrift (Titel, Intro-
    Satz) wird ignoriert.
    """

    return [
        (entry.version, entry.body)
        for entry in split_entries(text)
    ]


def split_entries(text: str) -> list[ChangelogEntry]:
    """
    Dasselbe wie `_split_sections()`, nur mit dem Datum aus der
    Überschrift - die Änderungsansicht zeigt es an.
    """

    entries: list[ChangelogEntry] = []

    version = None
    date = ""
    lines: list[str] = []

    def flush():

        if version is not None:

            entries.append(
                ChangelogEntry(
                    version=version,
                    date=date,
                    body="\n".join(lines).strip(),
                )
            )

    for line in text.splitlines():

        match = _HEADER_RE.match(line)

        if match:

            flush()

            version = match.group(1)
            date = (match.group(2) or "").strip()
            lines = []

            continue

        if version is not None:
            lines.append(line)

    flush()

    return entries


def read_entries(path) -> list[ChangelogEntry]:
    """
    Eine CHANGELOG.md von der Platte, neueste Fassung zuerst.

    Eine fehlende oder unlesbare Datei ergibt eine leere Liste - die
    Ansicht sagt dann, dass sie nichts gefunden hat. Ein Fehler wäre
    hier unangebracht: der Changelog ist Beiwerk, kein Betriebsmittel.
    """

    if path is None:
        return []

    file = Path(path)

    if not file.exists():
        return []

    try:
        return split_entries(file.read_text(encoding="utf-8"))

    except (OSError, UnicodeDecodeError):
        return []


#
# Markdown-Auszeichnungen, die als reiner Text nur stören. Fett und
# kursiv tragen im Changelog die Betonung eines Satzanfangs; als
# `**...**` in einem QLabel sind sie schlicht Zeichensalat. Der Text
# wird deshalb entkleidet, nicht ausgezeichnet - ein QLabel könnte
# Markdown zwar über Rich Text darstellen, aber dann müsste jede
# Klammer und jedes `<` im Changelog maskiert werden.
#

_EMPHASIS_RE = re.compile(r"\*{1,3}(.+?)\*{1,3}")

_CODE_RE = re.compile(r"`([^`]+)`")

_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def strip_markdown(text: str) -> str:

    text = _LINK_RE.sub(r"\1", text)

    text = _EMPHASIS_RE.sub(r"\1", text)

    return _CODE_RE.sub(r"\1", text)


def format_changelog_body(body: str) -> str:
    """
    Wandelt die Markdown-Syntax aus CHANGELOG.md in lesbare Absätze
    mit "•"-Aufzählung um, ohne von Zeilenumbrüchen mitten im Satz
    abhängig zu sein.

    Drei Formen kommen vor und müssen auseinandergehalten werden:

    - `### Neu` - eine Zwischenüberschrift. Das Addon gliedert seinen
      Changelog danach; ohne eigene Behandlung landete sie **mitten im
      vorherigen Aufzählungspunkt**, weil jede Zeile ohne "- " als
      Fortsetzung galt.
    - `- ...` mit eingerückten Folgezeilen - ein Aufzählungspunkt.
    - Ein freistehender Absatz. Die Companion schreibt ihren Changelog
      überwiegend so; vorher fiel er komplett weg, und ein Eintrag
      ohne Aufzählung war damit leer.
    """

    blocks: list[str] = []

    current: list[str] = []

    kind = ""

    def flush():

        nonlocal current

        if current:

            text = strip_markdown(" ".join(current))

            blocks.append(
                f"• {text}" if kind == "bullet" else text
            )

        current = []

    for line in body.splitlines():

        stripped = line.strip()

        if not stripped:

            #
            # Eine Leerzeile trennt Absätze, nicht die Folgezeilen
            # eines Aufzählungspunktes: eingerückte Fortsetzungen
            # stehen dort ohne Leerzeile dazwischen.
            #

            if kind == "paragraph":
                flush()

            continue

        if stripped.startswith("#"):

            flush()

            kind = ""

            blocks.append(
                strip_markdown(stripped.lstrip("#").strip()).upper()
            )

            continue

        if stripped.startswith(("- ", "* ")):

            flush()

            kind = "bullet"

            current = [stripped[2:]]

            continue

        if current:

            current.append(stripped)

            continue

        kind = "paragraph"

        current = [stripped]

    flush()

    return "\n\n".join(block for block in blocks if block)


def read_changelog_sections(
    up_to_version: str,
    since_version: str | None = None,
    limit: int = 5,
) -> list[tuple[str, str]]:
    """
    Liest CHANGELOG.md und gibt die Abschnitte zwischen (exklusiv)
    "since_version" und (inklusiv) "up_to_version" zurück, neueste
    zuerst.

    Ohne "since_version" wird nur der Abschnitt von "up_to_version"
    selbst zurückgegeben (nützlich für eine reine "aktuelle Version"-
    Anzeige). "limit" begrenzt die Anzahl der Abschnitte, falls beim
    Update mehrere Versionen übersprungen wurden - verhindert eine
    endlos lange Textwand.

    Gibt eine leere Liste zurück, wenn CHANGELOG.md fehlt, nicht
    gelesen werden kann, oder "up_to_version" darin nicht vorkommt.
    """

    path = Path(Resources.path("CHANGELOG.md"))

    if not path.exists():
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    sections = _split_sections(text)

    upper = parse_version(up_to_version)
    since = parse_version(since_version) if since_version else None

    result: list[tuple[str, str]] = []
    started = False

    for version, body in sections:

        parsed = parse_version(version)

        if not started:

            if parsed != upper:
                continue

            started = True

        if since is not None and parsed <= since:
            break

        result.append((version, body))

        #
        # Ohne "since" gibt es keine natürliche untere Grenze außer
        # "limit" - in diesem Fall reicht aber schon der erste
        # Treffer (die Version selbst), mehr wurde nie angefragt.
        #

        if since is None or len(result) >= limit:
            break

    return result
