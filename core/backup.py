from datetime import datetime
from pathlib import Path
import shutil


class BackupManager:

    def __init__(self):

        self.backup_dir = Path("cache/backups")

        self.backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

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