import shlex
import sys
from pathlib import Path

from core.runtime import Runtime

APP_NAME = "WeintCompanion"

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class Autostart:
    """
    Verwaltet den Autostart-Eintrag beim Systemstart - Windows über
    den "Run"-Registry-Schlüssel (HKCU, kein Adminrecht nötig),
    Linux über einen XDG-Autostart-.desktop-Eintrag.
    """

    # --------------------------------------------------
    # Zu startender Befehl
    # --------------------------------------------------

    @staticmethod
    def _command_parts():
        """
        Im Bundle (PyInstaller) der eigentliche Programmpfad
        (AppImage bzw. .exe), in der Entwicklung Python-Interpreter
        + app.py.
        """

        if getattr(sys, "frozen", False):
            return [str(Runtime.current_executable())]

        script = (
            Path(__file__).resolve().parent.parent
            / "app.py"
        )

        return [sys.executable, str(script)]

    # --------------------------------------------------
    # Windows
    # --------------------------------------------------

    @staticmethod
    def _set_windows(enabled: bool):

        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )

        try:

            if enabled:

                command = " ".join(
                    f'"{part}"'
                    for part in Autostart._command_parts()
                )

                winreg.SetValueEx(
                    key,
                    APP_NAME,
                    0,
                    winreg.REG_SZ,
                    command,
                )

            else:

                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass

        finally:

            winreg.CloseKey(key)

    @staticmethod
    def _is_enabled_windows() -> bool:

        import winreg

        try:

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _RUN_KEY,
                0,
                winreg.KEY_READ,
            )

        except OSError:
            return False

        try:

            winreg.QueryValueEx(key, APP_NAME)
            return True

        except FileNotFoundError:
            return False

        finally:
            winreg.CloseKey(key)

    # --------------------------------------------------
    # Linux (XDG-Autostart)
    # --------------------------------------------------

    @staticmethod
    def _desktop_file_linux() -> Path:

        import os

        xdg_config = os.environ.get("XDG_CONFIG_HOME")

        base = (
            Path(xdg_config)
            if xdg_config
            else Path.home() / ".config"
        )

        return (
            base
            / "autostart"
            / "weintcompanion.desktop"
        )

    @staticmethod
    def _set_linux(enabled: bool):

        desktop_file = Autostart._desktop_file_linux()

        if not enabled:

            desktop_file.unlink(missing_ok=True)
            return

        desktop_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = " ".join(
            shlex.quote(part)
            for part in Autostart._command_parts()
        )

        desktop_file.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={command}\n"
            "Icon=icon\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )

    @staticmethod
    def _is_enabled_linux() -> bool:

        return Autostart._desktop_file_linux().exists()

    # --------------------------------------------------
    # Öffentliche API
    # --------------------------------------------------

    @staticmethod
    def is_supported() -> bool:

        return Runtime.is_windows() or Runtime.is_linux()

    @staticmethod
    def set_enabled(enabled: bool) -> bool:
        """
        Schreibt (bzw. entfernt) den Autostart-Eintrag.
        Gibt False zurück, falls die Plattform nicht unterstützt
        wird oder der Zugriff fehlschlägt (z.B. fehlende Rechte).
        """

        try:

            if Runtime.is_windows():

                Autostart._set_windows(enabled)
                return True

            if Runtime.is_linux():

                Autostart._set_linux(enabled)
                return True

        except Exception:
            return False

        return False

    @staticmethod
    def is_enabled() -> bool:

        if Runtime.is_windows():
            return Autostart._is_enabled_windows()

        if Runtime.is_linux():
            return Autostart._is_enabled_linux()

        return False
