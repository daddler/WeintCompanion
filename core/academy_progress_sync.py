"""
Academy-Fortschritt, wie ihn das Addon zurückmeldet.

Bewusst ein eigenes Modul und nicht Teil von core/sync_manager.py:
das ist reines Parsen ohne Netzwerk, und der Test-Job der CI
installiert nur pytest, keine Projektabhängigkeiten. Läge die
Funktion im SyncManager, zöge schon der Import des Testmoduls über
discord/sync_client.py `requests` herein - und der komplette
Testlauf bräche beim Einsammeln ab.

Format (siehe SendAcademyProgress in modules/companion.lua des
Addons):

    <Charakter>|<erledigt,...>|<abgewählt,...>;<Charakter2>|...

Lektions-IDs sind ASCII-Bezeichner ohne Komma, Pipe oder Semikolon -
das Format ist damit eindeutig.
"""

from __future__ import annotations


def parse_addon_progress(payload: str) -> dict[str, tuple[list[str], list[str]]]:
    """
    {Charakter: (erledigt, abgewählt)}.

    Unvollständige Blöcke werden übersprungen statt den ganzen
    Durchlauf abzubrechen: eine halb geschriebene SavedVariables-
    Datei (WoWs Lua-VM schreibt, während wir lesen) darf den
    Fortschritt der übrigen Charaktere nicht kosten.
    """

    result: dict[str, tuple[list[str], list[str]]] = {}

    for block in (payload or "").split(";"):

        parts = block.split("|")

        if len(parts) != 3:
            continue

        name = parts[0].strip()

        if not name:
            continue

        result[name] = (
            [entry for entry in parts[1].split(",") if entry],
            [entry for entry in parts[2].split(",") if entry],
        )

    return result


def apply_addon_progress(academy, payload: str) -> bool:
    """
    Übernimmt den gemeldeten Stand in den AcademyService und
    speichert, wenn sich etwas geändert hat. Gibt zurück, ob
    gespeichert wurde.

    Die Listen des Addons ERSETZEN die hiesigen. Das Addon hat beim
    Login den Desktop-Stand erhalten und seitdem nur ergänzt; es ist
    für diesen Charakter also die jüngere Quelle. Ein Zusammenführen
    statt Ersetzen hieße, dass ingame abgehakte Lektionen nie wieder
    geöffnet werden könnten - das Addon meldet leere Listen genau
    deshalb ausdrücklich mit.
    """

    if academy is None:
        return False

    changed = False

    for name, (completed, excluded) in parse_addon_progress(payload).items():

        if academy.data["completed"].get(name) != completed:

            academy.data["completed"][name] = completed
            changed = True

        if academy.data["excluded"].get(name) != excluded:

            academy.data["excluded"][name] = excluded
            changed = True

    if changed:
        academy.save()

    return changed
