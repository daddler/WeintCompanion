from datetime import datetime
from pathlib import Path
import shutil

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