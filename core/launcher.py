from pathlib import Path
import os
import platform
import stat
import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class Launcher:

    # --------------------------------------------------

    def launch(self, file):

        file = Path(file)

        if not file.exists():

            raise FileNotFoundError(file)

        system = platform.system()

        #
        # Windows
        #

        if system == "Windows":

            os.startfile(file)

            return

        #
        # Linux
        #

        if system == "Linux":

            #
            # Datei ausführbar machen
            #

            current_mode = file.stat().st_mode

            file.chmod(
                current_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

            subprocess.Popen(
                [str(file)],
                start_new_session=True,
            )

            return

        #
        # macOS
        #

        if system == "Darwin":

            subprocess.Popen(
                ["open", str(file)],
                start_new_session=True,
            )

            return

        raise RuntimeError(
            f"Nicht unterstütztes Betriebssystem: {system}"
        )

    # --------------------------------------------------

    def launch_and_exit(self, file):

        #
        # Installer starten
        #

        self.launch(file)

        #
        # Companion kurz danach schließen
        #

        QTimer.singleShot(
            1000,
            QApplication.quit,
        )