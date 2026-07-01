from pathlib import Path
import shutil
import stat


class LinuxUpdater:

    def prepare(
        self,
        downloaded_appimage: Path,
        current_appimage: Path,
    ) -> Path:

        updater_source = (
            Path(__file__).resolve().parent.parent
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

        #
        # Alte Version entfernen
        #

        if updater_target.exists():
            updater_target.unlink()

        #
        # Neuen Updater kopieren
        #

        shutil.copy2(
            updater_source,
            updater_target,
        )

        #
        # Ausführbar machen
        #

        mode = updater_target.stat().st_mode

        updater_target.chmod(
            mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

        return updater_target