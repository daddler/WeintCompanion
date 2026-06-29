from pathlib import Path
import platform
import sys


class Runtime:

    @staticmethod
    def current_executable() -> Path:
        """
        Liefert den Pfad der aktuell laufenden Datei.

        Linux:
            /home/fabi/Programme/WeintCompanion-x86_64.AppImage

        Windows:
            C:\Program Files\WeintCompanion\WeintCompanion.exe
        """

        return Path(sys.argv[0]).resolve()

    @staticmethod
    def is_linux() -> bool:
        return platform.system() == "Linux"

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        return platform.system() == "Darwin"

    @staticmethod
    def is_appimage() -> bool:
        """
        Erkennt, ob die App als AppImage läuft.
        """

        exe = Runtime.current_executable()

        return exe.suffix.lower() == ".appimage"