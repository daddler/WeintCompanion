from pathlib import Path
import shutil
import stat
import sys


class LinuxUpdater:

    def prepare(
        self,
        downloaded_appimage: Path,
        current_appimage: Path,
    ) -> Path:

        #
        # Im PyInstaller-Build liegen Ressourcen unter _MEIPASS
        #

        if getattr(sys, "frozen", False):

            base = Path(sys._MEIPASS)

        else:

            base = Path(__file__).resolve().parent.parent

        updater_source = (
            base
            / "packaging"
            / "linux"
            / "updater.sh"
        )

        if not updater_source.exists():

            raise FileNotFoundError(
                f"Updater nicht gefunden: {updater_source}"
            )

        updater_target = (
            current_appimage.parent
            / "update.sh"
        )

        if updater_target.exists():

            updater_target.unlink()

        shutil.copy2(
            updater_source,
            updater_target,
        )

        mode = updater_target.stat().st_mode

        updater_target.chmod(
            mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

        return updater_target