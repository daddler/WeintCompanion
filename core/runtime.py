from pathlib import Path
import os
import platform
import sys


class Runtime:

    @staticmethod
    def current_executable() -> Path:
        """
        Liefert den Pfad der aktuell gestarteten Anwendung.

        Linux (AppImage):
            APPIMAGE
            -> /home/fabi/Downloads/WeintCompanion-x86_64.AppImage

        Windows:
            sys.argv[0]
            -> C:\\Program Files\\WeintCompanion\\WeintCompanion.exe
        """

        #
        # AppImage liefert den echten Dateipfad
        #

        appimage = os.environ.get("APPIMAGE")

        if appimage:

            return Path(appimage).resolve()

        #
        # Fallback für Windows, macOS und Entwicklung
        #

        return Path(sys.argv[0]).resolve()

    # --------------------------------------------------

    @staticmethod
    def is_linux() -> bool:

        return platform.system() == "Linux"

    # --------------------------------------------------

    @staticmethod
    def is_windows() -> bool:

        return platform.system() == "Windows"

    # --------------------------------------------------

    @staticmethod
    def is_macos() -> bool:

        return platform.system() == "Darwin"

    # --------------------------------------------------

    @staticmethod
    def is_appimage() -> bool:
        """
        Erkennt, ob WeintCompanion als AppImage läuft.
        """

        return "APPIMAGE" in os.environ