from pathlib import Path
import platform
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

            import os

            os.startfile(file)

            return

        #
        # Linux
        #

        if system == "Linux":

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
            250,
            QApplication.quit,
        )