from __future__ import annotations

import re
from pathlib import Path

from core.resources import Resources
from core.version import parse_version

_HEADER_RE = re.compile(r"^##\s+(\S+)\s*$")


def _split_sections(text: str) -> list[tuple[str, str]]:
    """
    Zerlegt den CHANGELOG-Text in (Version, Body)-Paare, in der
    Reihenfolge der Datei (neueste zuerst, wie in CHANGELOG.md
    üblich). Alles vor der ersten "## "-Überschrift (Titel, Intro-
    Satz) wird ignoriert.
    """

    sections: list[tuple[str, str]] = []

    current_version = None
    current_lines: list[str] = []

    for line in text.splitlines():

        match = _HEADER_RE.match(line)

        if match:

            if current_version is not None:

                sections.append((
                    current_version,
                    "\n".join(current_lines).strip(),
                ))

            current_version = match.group(1)
            current_lines = []

            continue

        if current_version is not None:
            current_lines.append(line)

    if current_version is not None:

        sections.append((
            current_version,
            "\n".join(current_lines).strip(),
        ))

    return sections


def format_changelog_body(body: str) -> str:
    """
    Wandelt die Markdown-Bullet-Syntax aus CHANGELOG.md ("- ..." mit
    eingerückten Folgezeilen) in lesbare Absätze mit "•"-Aufzählung
    um, ohne von Zeilenumbrüchen mitten im Satz abhängig zu sein.
    """

    entries: list[str] = []
    current: list[str] = []

    for line in body.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("- "):

            if current:
                entries.append(" ".join(current))

            current = [stripped[2:]]

        elif current:

            current.append(stripped)

    if current:
        entries.append(" ".join(current))

    return "\n\n".join(f"• {entry}" for entry in entries)


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
