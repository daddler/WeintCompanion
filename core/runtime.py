from pathlib import Path
import contextlib
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

    # --------------------------------------------------
    # Saubere Umgebung für externe Prozesse
    # --------------------------------------------------
    # PyInstaller (und damit auch die AppImage/EXE-Bundles) setzt
    # LD_LIBRARY_PATH auf die mitgelieferten Bibliotheken, damit die
    # gebündelte Qt/Python-Runtime funktioniert. Vererbt sich dieser
    # Wert an einen EXTERNEN, nicht im Bundle enthaltenen Prozess
    # (System-Browser über webbrowser.open(), das Updater-Skript
    # samt bash/mv/chmod/pgrep, ...), versucht dieser plötzlich gegen
    # inkompatible Bundle-Bibliotheken zu linken. Symptom: ein
    # "symbol lookup error" direkt in /bin/sh oder einem anderen
    # System-Tool, oft schon bevor der eigentliche Befehl überhaupt
    # ausgeführt wird - der Kindprozess stirbt sofort, lautlos für
    # den aufrufenden Python-Code (kein Fehler, einfach kein Effekt).
    #
    # PyInstaller hinterlegt den ursprünglichen Wert (falls vorhanden)
    # genau für diesen Fall in LD_LIBRARY_PATH_ORIG.

    @staticmethod
    def clean_subprocess_env() -> dict:
        """
        Kopie von os.environ, bereinigt um das gebündelte
        LD_LIBRARY_PATH - zum Übergeben an subprocess.Popen(env=...)
        beim Start externer Programme.
        """

        env = os.environ.copy()

        original = env.pop("LD_LIBRARY_PATH_ORIG", None)

        if original is not None:
            env["LD_LIBRARY_PATH"] = original
        else:
            env.pop("LD_LIBRARY_PATH", None)

        return env

    @staticmethod
    @contextlib.contextmanager
    def clean_environ():
        """
        Entfernt das gebündelte LD_LIBRARY_PATH vorübergehend aus
        os.environ selbst (Prozess-global) - für Aufrufe wie
        webbrowser.open(), die keine Möglichkeit bieten, eine eigene
        Umgebung an den intern gestarteten Subprozess zu übergeben.
        Bereits geladene Bibliotheken sind davon nicht betroffen, der
        Dynamic Linker liest den Wert nur beim Start neuer Prozesse.
        """

        key = "LD_LIBRARY_PATH"

        had_key = key in os.environ
        original = os.environ.get(key)
        backup = os.environ.get(f"{key}_ORIG")

        if backup is not None:
            os.environ[key] = backup
        else:
            os.environ.pop(key, None)

        try:

            yield

        finally:

            if had_key:
                os.environ[key] = original
            else:
                os.environ.pop(key, None)