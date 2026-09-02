"""
Die SavedVariables des WowSimsExporter lesen.

WoW schreibt die gespeicherten Daten eines Addons in eine Datei je
Konto, benannt nach dem Addon-Ordner: `WTF/Account/<Konto>/
SavedVariables/WowSimsExporter.lua`. Darin steht die Variable `WSEDB`,
und in ihr - über AceDB, also unter `profiles` - die Liste
`savedCharacters` mit dem Export je Charakter.

WARUM DIE COMPANION DIESE DATEI SELBST LIEST.

Weil sie die Quelle ist. Der Umweg über WeintCodex (Addon kopiert den
Export in seine eigenen SavedVariables, Companion liest die) wäre eine
zweite Fassung derselben Daten, die genau dann veraltet, wenn sie
gebraucht wird - und er hülfe niemandem, denn WoW schreibt beide
Dateien zum selben Zeitpunkt, nämlich bei `/reload` oder beim
Ausloggen. Gelesen wird nur; geschrieben wird in diese Datei nie.

WAS SIE NICHT LIEST.

Den Export selbst zerlegt sie nicht - das tut `core/wowsims_export.py`
mit dem JSON-Text, den sie hier herausträgt. Diese Datei kennt nur
Lua.

„NICHTS GEFUNDEN" HAT VIER GRÜNDE, UND SIE FÜHREN ZU VIER ANTWORTEN.

Kein WoW gefunden, das Addon nicht installiert, installiert aber noch
nie exportiert, exportiert aber für einen anderen Charakter - das
sieht in einer leeren Liste alles gleich aus, und drei der vier
verlangen etwas völlig anderes vom Nutzer. `Lookup.reason` benennt
deshalb, welcher Fall vorliegt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from core.lua_table import extract_variable_body, matching_brace


#
# Der Ordnername des Addons - und damit der Dateiname, den WoW für
# seine SavedVariables vergibt.
#

ADDON_FOLDER = "WowSimsExporter"

VARIABLE = "WSEDB"


#
# Warum nichts gefunden wurde. Vier Werte, weil vier verschiedene
# Sätze daraus werden (siehe Kopf).
#

NO_WOW = "no_wow"

NO_ADDON = "no_addon"

NO_EXPORT = "no_export"

FOUND = "found"


@dataclass(frozen=True)
class SavedCharacter:
    """
    Ein Eintrag aus `savedCharacters`.

    `stamp` ist eine Unix-Zeit (das Addon schreibt `time()`), 0 heisst
    "ohne Datum" - und das ist eine eigene Auskunft, keine Null.
    """

    name: str = ""

    stamp: int = 0

    data: str = ""


@dataclass(frozen=True)
class Lookup:
    """
    Was in den Dateien stand.

    `entries` ist nach Datum sortiert, das Neueste zuerst.
    """

    reason: str = NO_WOW

    entries: tuple[SavedCharacter, ...] = ()

    files: tuple[Path, ...] = ()

    @property
    def newest(self) -> SavedCharacter | None:

        return self.entries[0] if self.entries else None


#
# --------------------------------------------------
# Lua-Kleinkram
# --------------------------------------------------
#


_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    '"': '"',
    "'": "'",
    "\n": "\n",
}


def unescape(text: str) -> str:
    """
    Ein Lua-String-Literal in seinen Inhalt.

    WoW schreibt `"` als `\\"`, den Backslash als `\\\\` und alles
    Unfreundliche als `\\<Ziffern>`. Der Export ist JSON, also besteht
    er zum guten Teil aus Anführungszeichen - ohne diese Umkehrung
    kommt kein einziger davon richtig an.
    """

    out: list[str] = []

    index = 0

    length = len(text)

    while index < length:

        char = text[index]

        if char != "\\":
            out.append(char)
            index += 1
            continue

        index += 1

        if index >= length:
            break

        nxt = text[index]

        if nxt.isdigit():

            digits = ""

            while index < length and text[index].isdigit() and len(digits) < 3:
                digits += text[index]
                index += 1

            code = int(digits)

            out.append(chr(code) if code < 0x110000 else "")

            continue

        out.append(_ESCAPES.get(nxt, nxt))

        index += 1

    return "".join(out)


def read_string(text: str, start: int) -> tuple[str, int]:
    """
    Liest ab `start` (dem öffnenden Anführungszeichen) ein
    Lua-String-Literal und gibt seinen Inhalt zurück, dazu den Index
    hinter dem schliessenden Anführungszeichen.
    """

    quote = text[start]

    index = start + 1

    body: list[str] = []

    while index < len(text):

        char = text[index]

        if char == "\\":
            body.append(text[index:index + 2])
            index += 2
            continue

        if char == quote:
            return unescape("".join(body)), index + 1

        body.append(char)

        index += 1

    return unescape("".join(body)), len(text)


_KEY = re.compile(r'\["([A-Za-z_][A-Za-z0-9_]*)"\]\s*=\s*')


def read_record(text: str) -> dict:
    """
    Die flachen Werte eines `{ ["k"] = v, … }`-Blocks.

    Verschachtelte Tabellen werden übersprungen: gebraucht werden drei
    Zeichenketten und eine Zahl, und ein vollständiger Lua-Parser wäre
    für diese vier Werte deutlich mehr Fläche, auf der etwas falsch
    sein kann.
    """

    values: dict = {}

    index = 0

    while True:

        match = _KEY.search(text, index)

        if not match:
            break

        key = match.group(1)

        index = match.end()

        if index >= len(text):
            break

        char = text[index]

        if char in ('"', "'"):

            value, index = read_string(text, index)

            values[key] = value

            continue

        if char == "{":

            index = matching_brace(text, index) + 1

            continue

        end = index

        while end < len(text) and text[end] not in ",}\n":
            end += 1

        token = text[index:end].strip()

        index = end

        if token in ("true", "false"):
            values[key] = token == "true"

        else:

            try:
                values[key] = float(token) if "." in token else int(token)

            except ValueError:
                pass

    return values


def _blocks(text: str, key: str):
    """
    Alle Tabellen, die unter `key` hängen - über die ganze Tiefe
    hinweg, weil AceDB sie je nach Profil unterschiedlich tief
    ablegt.
    """

    needle = f'["{key}"]'

    index = 0

    while True:

        found = text.find(needle, index)

        if found == -1:
            return

        brace = text.find("{", found)

        if brace == -1:
            return

        try:
            end = matching_brace(text, brace)

        except ValueError:
            return

        yield text[brace + 1:end]

        index = end


def _records(block: str):
    """
    Die Einträge einer Lua-Liste: alle `{ … }` auf oberster Ebene.
    """

    index = 0

    while True:

        brace = block.find("{", index)

        if brace == -1:
            return

        try:
            end = matching_brace(block, brace)

        except ValueError:
            return

        yield block[brace + 1:end]

        index = end + 1


def parse_saved_variables(text: str) -> list[SavedCharacter]:
    """
    Alle gespeicherten Charaktere einer Datei.

    Gesucht wird in **allen** Profilen. AceDB legt die Vorgabe unter
    `profiles.Default` ab, aber wer sich je ein eigenes Profil angelegt
    hat, hat mehrere - und dann wäre die Vorgabe ausgerechnet die
    veraltete.
    """

    body = extract_variable_body(text, VARIABLE)

    if body is None:
        return []

    entries: list[SavedCharacter] = []

    seen: set[tuple[str, int]] = set()

    for block in _blocks(body, "savedCharacters"):

        for record in _records(block):

            values = read_record(record)

            data = values.get("data")

            if not isinstance(data, str) or not data:
                continue

            stamp = values.get("timestamp")

            stamp = int(stamp) if isinstance(stamp, (int, float)) else 0

            name = values.get("name")

            name = name if isinstance(name, str) else ""

            key = (name, stamp)

            #
            # Dieselbe Ablage kann in mehreren Profilen stehen (AceDB
            # kopiert beim Anlegen eines Profils); zweimal derselbe
            # Charakter mit derselben Uhrzeit ist einmal derselbe.
            #

            if key in seen:
                continue

            seen.add(key)

            entries.append(
                SavedCharacter(name=name, stamp=stamp, data=data),
            )

    entries.sort(key=lambda entry: entry.stamp, reverse=True)

    return entries


#
# --------------------------------------------------
# Die Datei finden
# --------------------------------------------------
#


class WseReader:

    def __init__(self, wow_path):

        self.wow_path = Path(wow_path) if wow_path else None

    # --------------------------------------------------

    def files(self) -> list[Path]:
        """
        Alle SavedVariables-Dateien des Addons - eine je WoW-Konto.
        """

        if self.wow_path is None:
            return []

        account_root = self.wow_path / "WTF" / "Account"

        if not account_root.exists():
            return []

        found: list[Path] = []

        try:
            accounts = sorted(account_root.iterdir())

        except OSError:
            return []

        for account in accounts:

            if not account.is_dir():
                continue

            file = (
                account
                / "SavedVariables"
                / f"{ADDON_FOLDER}.lua"
            )

            if file.is_file():
                found.append(file)

        return found

    # --------------------------------------------------

    def installed(self) -> bool:
        """
        Ob der Addon-Ordner da ist.

        Getrennt von `files()`, weil "installiert, aber noch nie
        exportiert" ein eigener Satz ist: dort ist einmal `/reload`
        die ganze Abhilfe, während bei "nicht installiert" erst etwas
        heruntergeladen werden muss.
        """

        if self.wow_path is None:
            return False

        return (
            self.wow_path / "Interface" / "AddOns" / ADDON_FOLDER
        ).is_dir()

    # --------------------------------------------------

    def read(self) -> Lookup:
        """
        Was in den Dateien steht, das Neueste zuerst.
        """

        if self.wow_path is None:
            return Lookup(reason=NO_WOW)

        files = self.files()

        if not files:

            return Lookup(
                reason=NO_ADDON if not self.installed() else NO_EXPORT,
            )

        entries: list[SavedCharacter] = []

        for file in files:

            try:
                text = file.read_text(encoding="utf-8", errors="ignore")

            except OSError:
                continue

            try:
                entries.extend(parse_saved_variables(text))

            except ValueError:

                #
                # Unausgeglichene Klammern - die Datei wurde gerade
                # geschrieben. Beim nächsten Lesen steht sie wieder;
                # eine halbe Ausrüstung wäre die schlechtere Antwort.
                #

                continue

        entries.sort(key=lambda entry: entry.stamp, reverse=True)

        return Lookup(
            reason=FOUND if entries else NO_EXPORT,
            entries=tuple(entries),
            files=tuple(files),
        )
