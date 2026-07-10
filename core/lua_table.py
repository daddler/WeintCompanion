from __future__ import annotations

from pathlib import Path


def _find_matching_brace(text: str, open_index: int) -> int:
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

    path.write_text(text, encoding="utf-8")
