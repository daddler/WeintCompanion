from __future__ import annotations

import os
from pathlib import Path


def matching_brace(text: str, open_index: int) -> int:
    """
    Findet den Index der zu text[open_index] ("{") passenden
    schließenden Klammer, unter Berücksichtigung von Lua-String-
    Literalen (damit "{"/"}" innerhalb von Strings nicht mitgezählt
    werden).
    """

    depth = 0
    index = open_index
    length = len(text)
    quote = None

    while index < length:

        char = text[index]

        if quote:

            if char == "\\":
                index += 2
                continue

            if char == quote:
                quote = None

        elif char in ('"', "'"):

            quote = char

        elif char == "{":

            depth += 1

        elif char == "}":

            depth -= 1

            if depth == 0:
                return index

        index += 1

    raise ValueError("Unausgeglichene Klammern in Lua-Datei.")


#
# Der alte, dateiinterne Name. Die Klammersuche ist inzwischen auch
# ausserhalb dieser Datei die einzige richtige Antwort auf "wo endet
# dieser Block" (addon/wse_reader.py liest damit die SavedVariables
# eines fremden Addons), und eine zweite Fassung davon liefe an
# Lua-Strings mit Klammern darin auseinander.
#

_find_matching_brace = matching_brace


def extract_variable_body(text: str, var_name: str) -> str | None:
    """
    Gegenstück zu upsert_variable(): gibt NUR den Inhalt zwischen den
    äußeren "{"/"}" von "var_name = { ... }" zurück (ohne die
    Klammern selbst), oder None, wenn die Variable nicht gefunden
    wird.

    WICHTIG: Eine WoW-SavedVariables-Datei kann mehrere Variablen
    desselben Addons enthalten (z. B. WeintCompanionDB UND
    WeintCompanionInboxDB). Ein zeilenweiser Parser, der einfach die
    gesamte Datei ab dem ersten "["queue"]" durchsucht, ohne den
    Gültigkeitsbereich zu begrenzen, liest sonst versehentlich auch
    Einträge aus dem Queue einer GANZ ANDEREN Variable mit, sobald
    diese weiter hinten in derselben Datei steht.
    """

    needle = f"{var_name} = {{"

    start = text.find(needle)

    if start == -1:
        return None

    open_index = start + len(needle) - 1

    close_index = _find_matching_brace(text, open_index)

    return text[open_index + 1:close_index]


def upsert_variable(path: Path, var_name: str, body: str) -> None:
    """
    Ersetzt (oder ergänzt) den Block "var_name = { ... }" in einer
    WoW-SavedVariables-Datei, ohne die übrigen darin gespeicherten
    Variablen anzufassen.

    WICHTIG: WoW schreibt ALLE SavedVariables eines Addons in EINE
    gemeinsame Datei (z. B. WeintCodex.lua enthält sowohl
    WeintCodex_SavedData als auch WeintCompanionDB). Ein naives
    Überschreiben der ganzen Datei würde die jeweils anderen
    Variablen mitlöschen - deshalb wird hier nur der exakte Block der
    gewünschten Variable herausgeschnitten und ersetzt.

    body: der Inhalt zwischen den äußeren "{"/"}" (diese beiden
    Klammern werden von dieser Funktion selbst ergänzt).
    """

    text = path.read_text(encoding="utf-8") if path.exists() else ""

    needle = f"{var_name} = {{"

    start = text.find(needle)

    new_block = f"{var_name} = {{\n{body}}}"

    if start == -1:

        if text and not text.endswith("\n"):
            text += "\n"

        text += new_block + "\n"

    else:

        open_index = start + len(needle) - 1

        close_index = _find_matching_brace(text, open_index)

        text = text[:start] + new_block + text[close_index + 1:]

    #
    # Write-Temp-Then-Rename: diese Datei ist WoWs SavedVariables-
    # Datei, die ALLE Variablen des Addons enthält, nicht nur die
    # hier bearbeitete. Ein Crash mitten in einem direkten
    # path.write_text() würde die komplette Datei (samt unrelated
    # Spielstand) abschneiden/beschädigen - os.replace() ist auf dem
    # jeweiligen Dateisystem atomar, es gibt also nie einen
    # sichtbaren Zwischenzustand.
    #

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    tmp_path.write_text(text, encoding="utf-8")

    os.replace(tmp_path, path)


#
# Lua-Serialisierung (Companion -> Addon)
#
# Der Inbox-Writer hat bislang nur flache Zeichenketten geschrieben.
# Auswertung und Lektionskatalog sind aber verschachtelte Strukturen,
# und ein handgeschriebenes Trennzeichen-Format daraus wäre in
# deutschem Fließtext (Lektionstexte, "Was tun"-Hinweise) nicht
# eindeutig: genau die Zeichen, die als Trenner taugen, kommen darin
# vor. Deshalb wird echtes Lua geschrieben, das WoW ohnehin selbst
# parst - das Addon braucht dafür keinen Parser.
#


_LUA_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def quote_lua_string(value: str) -> str:
    """
    Ein Lua-String-Literal inklusive Anführungszeichen.

    Steuerzeichen werden numerisch escapet: eine SavedVariables-Datei
    muss von WoWs Lua-Parser gelesen werden, und ein rohes Steuerzeichen
    im Literal ist dort ein Syntaxfehler - der die GESAMTE Datei
    unbrauchbar machen würde, samt der Variablen anderer Features.
    """

    out = ['"']

    for char in value:

        escaped = _LUA_ESCAPES.get(char)

        if escaped is not None:
            out.append(escaped)

        elif ord(char) < 32 or ord(char) == 127:
            out.append(f"\\{ord(char):03d}")

        else:
            out.append(char)

    out.append('"')

    return "".join(out)


def _lua_number(value) -> str:

    #
    # inf/nan gibt es in Lua zwar, sie würden hier aber als "inf"
    # bzw. "nan" ausgeschrieben und wären beim Einlesen ein
    # Syntaxfehler. Rechenfehler in der Auswertung dürfen die Datei
    # nicht zerlegen - sie werden zu 0.
    #

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int):
        return str(value)

    if value != value or value in (float("inf"), float("-inf")):
        return "0"

    return repr(float(value))


def to_lua(value, indent: int = 0) -> str:
    """
    Wandelt Zahlen, Wahrheitswerte, Zeichenketten, Listen und
    Dictionaries in eine Lua-Tabellenliteral-Darstellung.

    Nicht unterstützte Typen lösen einen TypeError aus, statt still
    etwas Falsches zu schreiben - eine kaputte SavedVariables-Datei
    fällt sonst erst im Spiel auf.

    None wird zu nil; in Dictionaries werden None-Werte übersprungen,
    weil ein Lua-Tabellenfeld mit nil-Wert dasselbe ist wie ein
    fehlendes Feld.
    """

    pad = "    " * indent
    inner_pad = "    " * (indent + 1)

    if value is None:
        return "nil"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return _lua_number(value)

    if isinstance(value, str):
        return quote_lua_string(value)

    if isinstance(value, dict):

        parts = []

        for key, item in value.items():

            if item is None:
                continue

            parts.append(
                f"{inner_pad}[{quote_lua_string(str(key))}] = "
                f"{to_lua(item, indent + 1)},"
            )

        if not parts:
            return "{}"

        return "{\n" + "\n".join(parts) + f"\n{pad}}}"

    if isinstance(value, (list, tuple)):

        parts = []

        for item in value:

            #
            # In einer Lua-Sequenz würde ein nil das Feld beenden -
            # ipairs bräche dort ab und der Rest der Liste wäre im
            # Addon unsichtbar. None-Einträge werden deshalb
            # ausgelassen, nicht als nil geschrieben.
            #

            if item is None:
                continue

            parts.append(f"{inner_pad}{to_lua(item, indent + 1)},")

        if not parts:
            return "{}"

        return "{\n" + "\n".join(parts) + f"\n{pad}}}"

    raise TypeError(
        f"to_lua: nicht unterstützter Typ {type(value).__name__}"
    )
