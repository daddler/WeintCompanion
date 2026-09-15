from pathlib import Path


class AddonReader:

    def __init__(self, wow_path):
        """
        `wow_path` ist das Installationsverzeichnis der eingestellten
        Spielversion - bei MoP Classic `_classic_`, bei einer anderen
        was `core/wow_clients.py` dafür führt. Unterhalb davon liegt
        `Interface/AddOns/` in jeder Fassung gleich.
        """

        self.wow_path = Path(wow_path)

    # --------------------------------------------------

    @property
    def addon_path(self):

        return (
            self.wow_path
            / "Interface"
            / "AddOns"
            / "WeintCodex"
        )

    # --------------------------------------------------

    @property
    def toc_path(self):

        return (
            self.addon_path
            / "WeintCodex.toc"
        )

    # --------------------------------------------------

    def exists(self):

        return (
            self.addon_path.exists()
            and self.toc_path.exists()
        )

    # --------------------------------------------------

    def get_version(self):

        if not self.exists():
            return None

        try:

            with open(
                self.toc_path,
                "r",
                encoding="utf-8",
            ) as file:

                for line in file:

                    if line.startswith("## Version:"):

                        return (
                            line
                            .split(":", 1)[1]
                            .strip()
                        )

        except Exception:

            return None

        return None