"""
Sucht die Installation einer Spielversion auf der Platte.

Bis 4.0 suchte diese Klasse nach einem Ordner namens `_classic_`.
Seit 4.1 bekommt sie eine Spielversion (`core/wow_clients.py`), und
davon hängt ab, *wonach* sie sucht:

* **Ordnername bekannt** (MoP Classic: `_classic_`): der Name
  entscheidet, danach die Kennzeichen. Das ist die alte, enge Suche -
  ein Ordner, der zufällig `Interface/` und `WTF/` enthält, gilt nicht
  als Treffer.
* **Ordnername unbekannt** (Forever, solange Blizzard ihn nicht
  nennt): allein die Kennzeichen entscheiden - **ausser** bei
  Ordnernamen, die erkennbar zu einer anderen Spielversion gehören
  (`FOREIGN_FLAVOR_FOLDERS`). Ohne diesen Ausschluss fände eine Suche
  nach Forever `_retail_` und gäbe es als Forever aus; der Nutzer
  installierte sein Addon in eine Installation, die er nie startet,
  und nichts daran wäre sichtbar.

Gefunden wird automatisch nur, wenn noch kein Pfad hinterlegt ist
(`CompanionManager.detect_wow()`). Die Handauswahl in den
Einstellungen geht über `core/wow_folder.py` und ist die verlässliche
Antwort - die Suche hier ist Bequemlichkeit, keine Wahrheit.
"""

from pathlib import Path

from core.wow_clients import (
    default_client,
    foreign_flavor_folders,
)
from core.wow_folder import is_installation


class WoWFinder:

    def __init__(self, client=None):

        self.client = client or default_client()

        self.foreign_folders = set(
            foreign_flavor_folders(self.client)
        )

        self.search_roots = [

            #
            # Linux
            #

            Path.home() / "Games",
            Path.home() / ".steam",
            Path.home() / ".local/share",
            Path("/mnt"),
            Path("/media"),
            Path("/run/media"),

            #
            # Windows
            #

            Path("C:/Program Files (x86)"),
            Path("C:/Program Files"),
            Path("D:/Program Files (x86)"),
            Path("D:/Program Files"),
            Path("E:/Program Files (x86)"),
            Path("E:/Program Files"),
        ]

    # --------------------------------------------------

    def find(self):

        #
        # Bekannte Blizzard-Struktur
        #

        visited = set()

        for root in self.search_roots:

            if not root.exists():
                continue

            result = self._search(root, visited)

            if result:
                return result

        return None

    # --------------------------------------------------

    def _search(self, directory, visited, depth=0):

        #
        # Schutz gegen Endlosrekursion durch Symlink-Zyklen: Ein
        # Steam-Proton-Prefix enthält unter "pfx/dosdevices/" u. a.
        # "z:" als Symlink auf "/" - da unsere Suchwurzeln (z. B.
        # "~/.steam", "~/.local/share") selbst wieder unterhalb von
        # "/" liegen, würde ein naives Verfolgen dieses Symlinks
        # zurück auf sich selbst führen und dabei denselben Pfad
        # immer wieder anhängen (siehe Crash-Report: kde-open erhielt
        # einen Pfad mit mehrfach wiederholtem
        # ".../pfx/dosdevices/z:/home/...". Die eigentliche
        # WoW-Installation liegt ohnehin unter dem echten
        # "pfx/drive_c/..."-Verzeichnis, nicht hinter den
        # Bequemlichkeits-Symlinks in "dosdevices/" - wir überspringen
        # Symlinks beim Abstieg daher komplett.
        #
        # Zusätzlich schützt ein besuchte-Pfade-Set (per realem,
        # aufgelöstem Pfad) sowie ein Tiefenlimit vor anderen, nicht
        # symlink-basierten Zyklen bzw. pathologisch tiefen
        # Verzeichnisbäumen.
        #

        if depth > 40:
            return None

        try:
            real = directory.resolve()
        except OSError:
            return None

        if real in visited:
            return None

        visited.add(real)

        #
        # Eine fremde Spielversion wird weder als Treffer genommen
        # noch betreten - darunter liegt keine andere Installation.
        #

        if directory.name in self.foreign_folders:
            return None

        try:

            if self._matches(directory):
                return directory

            #
            # Rekursiv weitersuchen
            #

            for child in directory.iterdir():

                if child.is_symlink():
                    continue

                if not child.is_dir():
                    continue

                result = self._search(child, visited, depth + 1)

                if result:
                    return result

        except (PermissionError, OSError):

            return None

        return None

    # --------------------------------------------------

    def _matches(self, directory):
        """
        Ist dieser Ordner die gesuchte Installation?
        """

        if (
            self.client.folder_known
            and directory.name not in self.client.folder_names
        ):

            return False

        return is_installation(directory, self.client)