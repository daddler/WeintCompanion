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

from dataclasses import dataclass
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


@dataclass(frozen=True)
class UpdateNote:
    """
    Der Text, der über dem Update-Knopf steht.

    `version` ist die Fassung, die er beschreibt, `installed` sagt, ob
    das die gerade laufende ist. Ohne dieses zweite Feld kann die
    Oberfläche den Text nicht beschriften - und ein unbeschrifteter
    Auszug unter "Update verfügbar" wird als Inhalt des Updates
    gelesen, egal welche Fassung er in Wahrheit beschreibt.
    """

    version: str

    body: str

    installed: bool


def installed_entry(component: str, state) -> ChangelogEntry | None:
    """
    Der Eintrag zu der Fassung, die gerade läuft.

    Bewusst über `find_entry` und nicht über "der oberste Eintrag":
    beim Addon *kann* die oberste Fassung eine andere sein. Fehlt die
    CHANGELOG.md im Addon-Ordner, steht in `addon_entries()` nur der
    Release-Text der **neuen** Fassung - und der beschreibt die
    installierte gerade nicht. Dann ist die ehrliche Antwort `None`.
    """

    version = installed_version(component, state)

    if not version:
        return None

    entries = entries_for(component, state)

    if not entries:
        return None

    return find_entry(entries, version)


def update_note(component: str, state) -> UpdateNote | None:
    """
    Was neben einem wartenden Update zu lesen ist: **die Notizen der
    Fassung, die man hat.**

    Bis 2.4.0 stand hier der Auszug zur *angebotenen* Fassung, also zu
    etwas, das auf diesem Rechner noch gar nicht liegt. Beschriftet
    war er nicht, und beides zusammen ergab einen vorausschauenden
    Text an einer Stelle, an der jeder eine Beschreibung dessen
    erwartet, was er sieht. Was das Update mitbringt, steht vollständig
    hinter "Alle Änderungen ansehen" - eine Zeile weiter, einen Klick
    entfernt, und dort ist es auch als solches beschriftet.

    `None` heißt "zu dieser Fassung liegt nichts vor". Das ist eine
    eigene Auskunft und darf nicht durch den Text einer anderen
    Fassung ersetzt werden - dieselbe Linie wie `stars == 0`.
    """

    entry = installed_entry(component, state)

    if entry is None:
        return None

    return UpdateNote(
        version=entry.version,
        body=entry.body,
        installed=True,
    )
