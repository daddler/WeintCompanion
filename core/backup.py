from datetime import datetime
from pathlib import Path
import shutil
import zipfile

from core.paths import Paths


class BackupManager:

    def __init__(self):

        self.backup_dir = Paths.backups()

    # --------------------------------------------------

    def create_backup(self, addon_path):

        addon_path = Path(addon_path)

        if not addon_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        archive = (
            self.backup_dir
            / f"WeintCodex_{timestamp}"
        )

        shutil.make_archive(
            str(archive),
            "zip",
            addon_path.parent,
            addon_path.name,
        )

        return archive.with_suffix(".zip")

    # --------------------------------------------------

    def restore(self, backup_zip, addon_path) -> bool:
        """
        Stellt "addon_path" aus einem zuvor mit create_backup()
        erstellten Zip wieder her. Wird als Best-Effort-Rettung
        genutzt, wenn eine Installation fehlschlägt - überschreibt
        einen ggf. vorhandenen Ordner an "addon_path" komplett, da
        das Backup als vertrauenswürdiger Vorzustand gilt.

        Gibt True bei Erfolg zurück, False wenn das Backup nicht
        existiert oder das Wiederherstellen selbst fehlschlägt (dann
        soll der Aufrufer den ursprünglichen Fehler weiterreichen,
        nicht diesen hier).
        """

        backup_zip = Path(backup_zip)
        addon_path = Path(addon_path)

        if not backup_zip.exists():
            return False

        try:

            if addon_path.exists():
                shutil.rmtree(addon_path)

            with zipfile.ZipFile(backup_zip, "r") as archive:
                archive.extractall(addon_path.parent)

            return True

        except Exception:

            return False