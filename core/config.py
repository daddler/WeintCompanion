import json
from pathlib import Path

from core.paths import Paths


class Config:

    def __init__(self):

        self.file = (
            Paths.config()
            / "config.json"
        )

        self.data = {

            "classic_path": "",

            #
            # Allgemeine Einstellungen
            #

            "check_updates": True,

            "auto_sync": True,

            "sync_interval": 5,

            "roster_sync_enabled": True,

        }

        self.load()

    # --------------------------------------------------

    def load(self):

        if not self.file.exists():

            self.save()

            return

        try:

            with open(
                self.file,
                "r",
                encoding="utf-8",
            ) as f:

                self.data.update(
                    json.load(f)
                )
                #
                # Fehlende Einstellungen ergänzen
                #

                changed = False

                defaults = {

                    "check_updates": True,
                    "auto_sync": True,
                    "sync_interval": 5,
                    "roster_sync_enabled": True,

                }

                for key, value in defaults.items():

                    if key not in self.data:

                        self.data[key] = value
                        changed = True

                if changed:

                    self.save()

        except Exception:

            self.save()

    # --------------------------------------------------

    def save(self):

        with open(
            self.file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                self.data,
                f,
                indent=4,
                ensure_ascii=False,
            )

    # --------------------------------------------------
    # Classic-Pfad
    # --------------------------------------------------

    def get_classic_path(self):

        path = self.data.get(
            "classic_path",
            "",
        )

        if not path:
            return None

        path = Path(path)

        if path.exists():
            return path

        return None

    # --------------------------------------------------

    def set_classic_path(self, path):

        self.data["classic_path"] = str(path)

        self.save()