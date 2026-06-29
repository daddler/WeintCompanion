from pathlib import Path
import shutil
import stat
import subprocess
import time


def run(
    downloaded: Path,
    current: Path,
):

    #
    # Warten bis Companion beendet wurde
    #

    time.sleep(2)

    #
    # Neue Datei kopieren
    #

    shutil.copy2(
        downloaded,
        current,
    )

    #
    # Execute-Bit setzen
    #

    mode = current.stat().st_mode

    current.chmod(
        mode
        | stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
    )

    #
    # Neue Version starten
    #

    subprocess.Popen(
        [str(current)],
        start_new_session=True,
    )

    #
    # Download löschen
    #

    downloaded.unlink(
        missing_ok=True,
    )