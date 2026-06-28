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

        for root in self.search_roots:

            if not root.exists():
                continue

            result = self._search(root)

            if result:
                return result

        return None

    # --------------------------------------------------

    def _search(self, directory):

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

                if not child.is_dir():
                    continue

                result = self._search(child)

                if result:
                    return result

        except (PermissionError, OSError):

            return None

        return None