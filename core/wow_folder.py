"""
Prüft, ob ein vom Nutzer gewählter Ordner tatsächlich eine
MoP-Classic-Installation ist.

Bis 2.0 stand diese Prüfung nur in
`gui/pages/settings_sections/wow_client.py`. Die Einrichtung (§6.6)
braucht denselben Schritt ein zweites Mal - zwei Kopien derselben
Prüfung liefen früher oder später auseinander, sobald sich einmal nur
eine von beiden geändert hätte.
"""

from __future__ import annotations

from pathlib import Path


def resolve_classic_folder(folder: str | Path) -> Path | None:
    """
    Gibt den tatsächlichen Classic-Ordner zurück, oder `None`, wenn
    `folder` keine gültige MoP-Classic-Installation ist.

    Ein Battle.net-typischer "World of Warcraft"-Wurzelordner wird
    automatisch auf seinen `_classic_`-Unterordner aufgelöst - die
    meisten Nutzer wählen im Dateidialog die Wurzel, nicht den
    Classic-Unterordner selbst.
    """

    folder = Path(folder)

    if folder.name == "World of Warcraft" and (folder / "_classic_").exists():
        folder = folder / "_classic_"

    if (
        (folder / "Interface").exists()
        and (folder / "Interface" / "AddOns").exists()
        and (folder / "WTF").exists()
    ):
        return folder

    return None
