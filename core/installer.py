import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from core.install_errors import probe_writable, translate


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
        # DARF HIER UEBERHAUPT GESCHRIEBEN WERDEN?
        #
        # Die Frage steht vor allem anderen, weil ihre Antwort den Satz
        # bestimmt, den der Nutzer im Fehlerfall liest: ein Ordner, in
        # dem sich nichts anlegen laesst, ist eine Rechtefrage; einer,
        # in dem das geht und der sich trotzdem nicht ersetzen laesst,
        # wird von jemandem offen gehalten (WoW laeuft). Siehe
        # core/install_errors.py - von aussen sehen beide identisch aus
        # ("[WinError 5] Zugriff verweigert"), und sie verlangen
        # Entgegengesetztes.
        #
        # Gemerkt, nicht sofort geworfen: die Probe kann sich irren
        # (Virenscanner, Netzlaufwerk), und dann soll der echte
        # Kopiervorgang entscheiden statt einer Vermutung.
        #

        writable = probe_writable(addon_path.parent)

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

        try:

            if new_path.exists():
                shutil.rmtree(new_path)

            if old_path.exists():
                shutil.rmtree(old_path)

        except OSError as exc:

            raise translate(
                exc, addon_path.parent, folder_writable=writable
            ) from exc

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

            #
            # Der erste Schreibvorgang im Zielverzeichnis. Scheitert er
            # an den Rechten, ist die Installation gar nicht erst
            # angelaufen - die bestehende Fassung bleibt unberuehrt.
            #

            try:

                shutil.copytree(
                    source,
                    new_path,
                )

            except OSError as exc:

                raise translate(
                    exc, addon_path.parent, folder_writable=writable
                ) from exc

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

        except OSError as exc:

            if old_path.exists() and not addon_path.exists():
                os.rename(old_path, addon_path)

            #
            # HIER IST DER HAEUFIGE FALL. Unter Windows laesst sich ein
            # Verzeichnis nicht umbenennen, solange irgendjemand eine
            # Datei darin offen haelt - und "Zugriff verweigert" sagt
            # nicht, dass es WoW ist. Die Probe oben trennt das vom
            # fehlenden Schreibrecht.
            #

            raise translate(
                exc, addon_path, folder_writable=writable
            ) from exc

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