import json
from pathlib import Path


class Config:

    def __init__(self):

        self.file = Path("config.json")

        self.data = {

            "classic_path": "",

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