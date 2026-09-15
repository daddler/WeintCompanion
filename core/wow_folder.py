"""
Prüft, ob ein vom Nutzer gewählter Ordner tatsächlich die Installation
einer bestimmten Spielversion ist.

Bis 2.0 stand diese Prüfung nur in
`gui/pages/settings_sections/wow_client.py`. Die Einrichtung (§6.6)
braucht denselben Schritt ein zweites Mal - zwei Kopien derselben
Prüfung liefen früher oder später auseinander, sobald sich einmal nur
eine von beiden geändert hätte.

Bis 4.0 prüfte sie fest auf `_classic_`. Seit 4.1 fragt sie eine
Spielversion (`core/wow_clients.py`), und die trägt den Ordnernamen -
**oder trägt ihn ausdrücklich nicht**, solange er nicht bekannt ist.
Dieser zweite Fall ist der eigentliche Grund für den Umbau, und er
bestimmt den Aufbau unten:

1. Trägt der gewählte Ordner selbst die Kennzeichen, ist er es.
2. Sonst: die bekannten Ordnernamen der Spielversion direkt darunter.
3. Sonst: **genau ein** Unterordner mit den Kennzeichen, der nicht
   erkennbar zu einer anderen Spielversion gehört.

Schritt 3 ist der, der Forever ohne bekannten Ordnernamen trägt: wer
"World of Warcraft" wählt, landet in dem einen Unterordner, der eine
Installation ist. Sind es mehrere, wird **nicht geraten** - dann sagt
die Antwort, dass der Nutzer den Unterordner selbst wählen muss. Ein
falsch geratener Ordner wäre hier teuer: das Addon landete in einer
Installation, die nie gestartet wird, und die Frage "warum passiert
nichts" hätte keine sichtbare Ursache.

Die Antwort ist deshalb kein blosses `None`, sondern ein `FolderCheck`
mit Begründung - die Oberfläche kann sie unverändert anzeigen, ohne die
Fälle selbst zu kennen (dieselbe Bauart wie `CombatLogLocation` in
`analyzer/combatlog/locator.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.wow_clients import (
    WowClient,
    default_client,
    foreign_flavor_folders,
)


#
# Wie viele Unterordner höchstens angesehen werden, wenn der
# Ordnername unbekannt ist. Eine Battle.net-Wurzel hat eine Handvoll
# Einträge; wer versehentlich sein Benutzerverzeichnis wählt, soll
# keine Sekunde warten müssen.
#

MAX_CHILDREN_SCANNED = 200


@dataclass(frozen=True)
class FolderCheck:
    """
    Ergebnis der Prüfung.

    `path` ist None, wenn der Ordner nicht taugt; `reason` erklärt auf
    Deutsch, warum.
    """

    path: Path | None = None

    reason: str = ""

    @property
    def ok(self) -> bool:

        return self.path is not None


# --------------------------------------------------


def is_installation(folder, target: WowClient) -> bool:
    """
    Trägt dieser Ordner alle Kennzeichen einer Installation?
    """

    folder = Path(folder)

    for marker in target.markers:

        if not folder.joinpath(*marker).exists():
            return False

    return True


# --------------------------------------------------


def check_client_folder(folder, target: WowClient | None = None) -> FolderCheck:
    """
    Prüft einen vom Nutzer gewählten Ordner gegen eine Spielversion.
    """

    target = target or default_client()

    folder = Path(folder)

    if not folder.is_dir():

        return FolderCheck(
            reason="Diesen Ordner gibt es nicht.",
        )

    #
    # 1. Der gewählte Ordner selbst.
    #

    if is_installation(folder, target):
        return FolderCheck(path=folder)

    #
    # 2. Ein bekannter Ordnername direkt darunter. Die meisten Nutzer
    #    wählen im Dateidialog die Wurzel "World of Warcraft", nicht
    #    den Unterordner der Spielversion.
    #

    for name in target.folder_names:

        candidate = folder / name

        if is_installation(candidate, target):
            return FolderCheck(path=candidate)

    #
    # 3. Ordnername unbekannt (Forever) oder die Installation liegt
    #    unter einem anderen Namen: der eine passende Unterordner.
    #

    foreign = foreign_flavor_folders(target)

    found: list[Path] = []

    skipped_foreign: list[str] = []

    try:

        for index, child in enumerate(sorted(folder.iterdir())):

            if index >= MAX_CHILDREN_SCANNED:
                break

            if child.is_symlink() or not child.is_dir():
                continue

            if not is_installation(child, target):
                continue

            if child.name in foreign:

                skipped_foreign.append(child.name)
                continue

            found.append(child)

    except OSError as exc:

        return FolderCheck(
            reason=f"Ordner nicht lesbar: {exc}",
        )

    if len(found) == 1:
        return FolderCheck(path=found[0])

    if len(found) > 1:

        names = ", ".join(child.name for child in found)

        return FolderCheck(
            reason=(
                f"Hier liegen mehrere Installationen ({names}) - bitte "
                f"den Ordner von {target.short_name} direkt auswählen."
            ),
        )

    if skipped_foreign:

        names = ", ".join(skipped_foreign)

        return FolderCheck(
            reason=(
                f"Hier liegt nur {names} - das ist eine andere "
                f"Spielversion als {target.short_name}."
            ),
        )

    return FolderCheck(
        reason=(
            f"Das ist kein gültiger Ordner für {target.short_name} - "
            "darin fehlen Interface/AddOns und WTF."
        ),
    )


# --------------------------------------------------


def resolve_client_folder(folder, target: WowClient | None = None) -> Path | None:
    """
    Der tatsächliche Installationsordner, oder `None`.

    Die kurze Form von `check_client_folder()` für alle Aufrufer, die
    keine Begründung anzeigen.
    """

    return check_client_folder(folder, target).path
