from pathlib import Path
import shutil
import tempfile
import zipfile


class Installer:

    # --------------------------------------------------

    def install(self, zip_file, addon_path):

        zip_file = Path(zip_file)
        addon_path = Path(addon_path)

        #
        # Sicherheitsprüfungen
        #

        if not zip_file.exists():
            raise FileNotFoundError(zip_file)

        if addon_path.name != "WeintCodex":
            raise RuntimeError(
                "Ungültiger Zielordner."
            )

        addon_parent = addon_path.parent.as_posix()

        if "Interface/AddOns" not in addon_parent:
            raise RuntimeError(
                "Addon liegt nicht im Interface/AddOns-Ordner."
            )

        #
        # ZIP entpacken
        #

        with tempfile.TemporaryDirectory() as temp:

            temp = Path(temp)

            with zipfile.ZipFile(zip_file, "r") as archive:
                archive.extractall(temp)

            #
            # WeintCodex suchen
            #

            source = None

            for folder in temp.rglob("WeintCodex"):

                if folder.is_dir():

                    toc = folder / "WeintCodex.toc"

                    if toc.exists():

                        source = folder
                        break

            if source is None:

                raise RuntimeError(
                    "WeintCodex.toc wurde im ZIP nicht gefunden."
                )

            #
            # Ziel sichern
            #

            if addon_path.exists():

                print(
                    "Entferne alte Version..."
                )

                shutil.rmtree(addon_path)

            #
            # Neue Version kopieren
            #

            print(
                "Installiere neue Version..."
            )

            shutil.copytree(
                source,
                addon_path,
                dirs_exist_ok=True,
            )

        return True