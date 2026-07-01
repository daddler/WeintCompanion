from pathlib import Path
import os
import platform
import stat
import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class Launcher:

    # --------------------------------------------------
    # Datei starten
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

            mode = file.stat().st_mode

            file.chmod(
                mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

            #
            # Shellskripte immer über bash starten
            #

            if file.suffix.lower() == ".sh":

                print(f"[Launcher] Starte Shellscript: {file}")

                proc = subprocess.Popen(
                    ["/bin/bash", str(file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )

            #
            # AppImage / EXE / Binärdateien
            #

            else:

                print(f"[Launcher] Starte Datei: {file}")

                proc = subprocess.Popen(
                    [str(file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )

            print(f"[Launcher] PID: {proc.pid}")

            return

        #
        # macOS
        #

        if system == "Darwin":

            subprocess.Popen(
                ["open", str(file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

            return

        raise RuntimeError(
            f"Nicht unterstütztes Betriebssystem: {system}"
        )

    # --------------------------------------------------
    # Starten und Companion schließen
    # --------------------------------------------------

    def launch_and_exit(self, file):

        self.launch(file)

        #
        # Dem gestarteten Prozess etwas Zeit geben
        #

        QTimer.singleShot(
            1000,
            QApplication.quit,
        )