"""
Woher der Changelog einer Komponente kommt.

**Was auf der Seite "Addon & Updates" stand, bevor es diese Datei
gab.** Die Addon-Karte zeigte "Keine Änderungen gefunden." und die
Companion-Karte eine Handvoll Commit-Betreffs. Beides war korrekt und
beides half niemandem: das eine, weil die Release-Notes des Tags leer
waren; das andere, weil ein Commit-Betreff für den Entwickler
geschrieben ist und nicht für den Spieler.

Beide Komponenten pflegen aber eine `CHANGELOG.md` - die Companion
bündelt ihre mit (`WeintCompanion.spec`), und beim Addon liegt sie
nach jedem Update im Addon-Ordner, weil das Release-ZIP das ganze
Verzeichnis enthält. Genau die wird hier gelesen.

Die Reihenfolge der Quellen ist die Aussage:

1. **Die CHANGELOG.md der Komponente.** Vollständig, offline lesbar,
   in derselben Sprache wie der Rest der Anwendung.
2. **Der Text des GitHub-Releases.** Nur, wenn die Datei fehlt - etwa
   bei einer Addon-Fassung, die vor dieser Regel gebaut wurde, oder
   wenn das Addon gar nicht installiert ist. Er beschreibt dann auch
   nur die *eine* neue Fassung.

Was hier bewusst **nicht** passiert: kein Netzabruf. Diese Funktionen
laufen aus dem Zeichnen der Oberfläche heraus, und eine Seite, die
zum Zeichnen ins Netz geht, ist genau der Fehler, den
`tests/test_update_visibility.py` festhält. Der Release-Text ist zu
diesem Zeitpunkt bereits im `AppState` - abgeholt hat ihn die
Update-Prüfung.
"""

from __future__ import annotations

from pathlib import Path

from core.changelog_reader import ChangelogEntry, read_entries
from core.resources import Resources
from core.version import VERSION


COMPANION = "companion"

ADDON = "addon"

LABELS = {
    COMPANION: "WeintCompanion",
    ADDON: "WeintCodex",
}


def companion_entries() -> list[ChangelogEntry]:
    """
    Die mitgelieferte CHANGELOG.md dieser Anwendung.
    """

    return read_entries(Resources.path("CHANGELOG.md"))


def addon_entries(state) -> list[ChangelogEntry]:
    """
    Die CHANGELOG.md aus dem installierten Addon-Ordner.

    Ohne installiertes Addon (oder bei einer Fassung, deren ZIP die
    Datei noch nicht enthielt) bleibt der Text des GitHub-Releases -
    besser eine Fassung als keine.
    """

    path = getattr(state, "addon_path", None)

    if path:

        entries = read_entries(Path(path) / "CHANGELOG.md")

        if entries:
            return entries

    release = (getattr(state, "github_changelog", "") or "").strip()

    if not release:
        return []

    return [
        ChangelogEntry(
            version=str(
                getattr(state, "github_version", "") or "-"
            ).lstrip("vV"),
            date="",
            body=release,
        )
    ]


def entries_for(component: str, state) -> list[ChangelogEntry]:

    if component == ADDON:
        return addon_entries(state)

    return companion_entries()


def latest_entry(component: str, state) -> ChangelogEntry | None:
    """
    Der oberste Eintrag - was ein Update mitbringt.

    Beim Addon ist das die Fassung, die auf GitHub liegt (die lokale
    Datei stammt aus der *installierten*, ist also einen Schritt
    zurück, solange nicht aktualisiert wurde). Für den Hinweis auf der
    Übersicht wird deshalb gezielt der Eintrag zur angebotenen Version
    gesucht und nur ersatzweise der neueste genommen.
    """

    entries = entries_for(component, state)

    if not entries:
        return None

    wanted = (
        getattr(state, "github_version", "")
        if component == ADDON
        else getattr(state, "companion_latest_version", "")
    )

    return find_entry(entries, wanted) or entries[0]


def find_entry(
    entries: list[ChangelogEntry],
    version: str,
) -> ChangelogEntry | None:
    """
    Der Eintrag zu einer Versionsangabe, ohne über `v`-Präfix oder
    Groß-/Kleinschreibung zu stolpern.
    """

    from core.version import parse_version

    if not version:
        return None

    wanted = parse_version(version)

    for entry in entries:

        if parse_version(entry.version) == wanted:
            return entry

    return None


def installed_version(component: str, state) -> str:

    if component == ADDON:

        return (
            state.addon_version
            if getattr(state, "addon_found", False)
            else ""
        )

    return VERSION
