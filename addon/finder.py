from pathlib import Path


class WoWFinder:

    def __init__(self):

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

        try:

            #
            # _classic_ gefunden?
            #

            if directory.name == "_classic_":

                interface = directory / "Interface"
                addons = interface / "AddOns"
                wtf = directory / "WTF"

                if (
                    interface.exists()
                    and addons.exists()
                    and wtf.exists()
                ):

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