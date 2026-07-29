"""
Findet die Combat-Log-Datei einer WoW-Installation.

WoW schreibt das Kampfprotokoll nach `<Installation>/Logs/`. Je nach
Client und Einstellung heißt die Datei entweder schlicht
`WoWCombatLog.txt` oder trägt einen Zeitstempel im Namen
(`WoWCombatLog-010224_193000.txt`), wenn pro Sitzung eine neue Datei
angelegt wird.

Deshalb wird nicht auf einen festen Namen geprüft, sondern die
zuletzt geschriebene passende Datei gewählt: das ist immer die des
laufenden Raids.

`wow_path` ist dabei das `_classic_`-Verzeichnis, also genau das,
was `addon.finder.WoWFinder.find()` liefert und in
`AppState.wow_path` landet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


#
# Basisname aller Combat-Log-Dateien.
#

LOG_PREFIX = "WoWCombatLog"

LOG_SUFFIX = ".txt"

LOG_DIRECTORY = "Logs"


@dataclass(frozen=True)
class CombatLogLocation:
    """
    Ergebnis der Suche.

    `path` ist None, wenn nichts gefunden wurde; `reason` erklärt in
    dem Fall auf Deutsch, warum - die Oberfläche kann das direkt
    anzeigen, ohne die Fälle selbst zu kennen.
    """

    path: Path | None = None

    reason: str = ""

    size: int = 0

    @property
    def found(self) -> bool:

        return self.path is not None


# --------------------------------------------------


def logs_directory(wow_path) -> Path | None:
    """
    Das Logs-Verzeichnis einer Installation, oder None wenn der
    übergebene Pfad leer ist bzw. kein Logs-Ordner existiert.
    """

    if not wow_path:
        return None

    directory = Path(wow_path) / LOG_DIRECTORY

    if not directory.is_dir():
        return None

    return directory


# --------------------------------------------------


def find_combat_log(wow_path) -> CombatLogLocation:
    """
    Sucht die aktuellste Combat-Log-Datei einer Installation.
    """

    if not wow_path:

        return CombatLogLocation(
            reason="Keine WoW-Installation erkannt.",
        )

    directory = logs_directory(wow_path)

    if directory is None:

        return CombatLogLocation(
            reason=(
                "Kein Logs-Ordner gefunden - im Spiel muss das "
                "Kampfprotokoll mindestens einmal aktiviert worden "
                "sein (/combatlog)."
            ),
        )

    candidates: list[Path] = []

    try:

        for entry in directory.iterdir():

            if not entry.is_file():
                continue

            name = entry.name

            if not name.startswith(LOG_PREFIX):
                continue

            if not name.lower().endswith(LOG_SUFFIX):
                continue

            candidates.append(entry)

    except OSError as exc:

        return CombatLogLocation(
            reason=f"Logs-Ordner nicht lesbar: {exc}",
        )

    if not candidates:

        return CombatLogLocation(
            reason=(
                "Keine Combat-Log-Datei gefunden - im Spiel "
                "/combatlog eingeben oder das automatische "
                "Protokollieren aktivieren."
            ),
        )

    #
    # Die zuletzt geschriebene Datei ist die des laufenden Raids.
    # stat() kann zwischen iterdir() und hier fehlschlagen (Datei
    # gelöscht) - solche Kandidaten fallen einfach hinten runter.
    #

    def modified_at(path: Path) -> float:

        try:
            return path.stat().st_mtime

        except OSError:
            return 0.0

    newest = max(candidates, key=modified_at)

    try:
        size = newest.stat().st_size

    except OSError:
        size = 0

    return CombatLogLocation(
        path=newest,
        size=size,
    )
