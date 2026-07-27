import os
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
        # ".new"/".old"-Arbeitsordner neben dem eigentlichen
        # Zielordner, für den atomaren Swap unten. Reste eines
        # vorherigen, abgebrochenen Installationsversuchs zuerst
        # aufräumen.
        #

        new_path = addon_path.with_name(
            addon_path.name + ".new"
        )

        old_path = addon_path.with_name(
            addon_path.name + ".old"
        )

        if new_path.exists():
            shutil.rmtree(new_path)

        if old_path.exists():
            shutil.rmtree(old_path)

        #
        # ZIP entpacken und die neue Version komplett in "new_path"
        # aufbauen, OHNE die bestehende Installation anzufassen -
        # schlägt hier irgendetwas fehl (korruptes ZIP, volle
        # Platte, ...), bleibt die alte Version unangetastet.
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

            print(
                "Bereite neue Version vor..."
            )

            shutil.copytree(
                source,
                new_path,
            )

        #
        # Atomarer Swap: alte Version (falls vorhanden) beiseite
        # schieben, neue Version an ihre Stelle verschieben. Beide
        # os.rename()-Aufrufe liegen im selben Verzeichnis (also
        # garantiert im selben Dateisystem) und sind damit atomar -
        # es gibt keinen Zwischenzustand, in dem addon_path weder
        # die alte noch die neue Version enthält. Schlägt der zweite
        # rename() fehl, wird die alte Version aus old_path
        # zurückgeschoben, statt den Nutzer ohne Addon dastehen zu
        # lassen.
        #

        try:

            print(
                "Installiere neue Version..."
            )

            if addon_path.exists():
                os.rename(addon_path, old_path)

            os.rename(new_path, addon_path)

        except Exception:

            if old_path.exists() and not addon_path.exists():
                os.rename(old_path, addon_path)

            raise

        finally:

            if old_path.exists():
                shutil.rmtree(old_path, ignore_errors=True)

            if new_path.exists():
                shutil.rmtree(new_path, ignore_errors=True)

        return True