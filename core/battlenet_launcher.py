import os
import platform
import shlex
import subprocess
from pathlib import Path

from core.runtime import Runtime


#
# Fallback-Suchpfade, falls Battle.net nicht als Geschwisterordner
# des WoW-Pfads liegt (z. B. portable Installation) - dieselben
# Laufwerke/Ordner wie in addon/finder.py (WoWFinder.search_roots).
#

WINDOWS_SEARCH_ROOTS = [
    Path("C:/Program Files (x86)"),
    Path("C:/Program Files"),
    Path("D:/Program Files (x86)"),
    Path("D:/Program Files"),
    Path("E:/Program Files (x86)"),
    Path("E:/Program Files"),
]


class BattleNetLauncher:

    def __init__(self, config):

        self.config = config

    # --------------------------------------------------
    # Windows: Battle.net.exe suchen
    # --------------------------------------------------

    def find_windows_executable(self, wow_path):

        candidates = []

        if wow_path is not None:

            #
            # wow_path zeigt auf ".../World of Warcraft/_classic_" -
            # Battle.net liegt als Geschwisterordner von
            # "World of Warcraft", nicht darunter.
            #

            wow_root = Path(wow_path).parent
            program_root = wow_root.parent

            candidates.append(
                program_root / "Battle.net" / "Battle.net.exe"
            )

        for root in WINDOWS_SEARCH_ROOTS:

            candidates.append(
                root / "Battle.net" / "Battle.net.exe"
            )

        for candidate in candidates:

            if candidate.exists():
                return candidate

        return None

    # --------------------------------------------------
    # Start
    # --------------------------------------------------

    def launch(self, wow_path):

        system = platform.system()

        if system == "Windows":

            self._launch_windows(wow_path)
            return

        if system == "Linux":

            self._launch_linux()
            return

        raise RuntimeError(
            f"Battle.net-Start wird unter {system} nicht unterstützt."
        )

    def _launch_windows(self, wow_path):

        exe = self.find_windows_executable(wow_path)

        if exe is None:

            raise FileNotFoundError(
                "Battle.net.exe wurde nicht gefunden."
            )

        os.startfile(exe)

    def _launch_linux(self):

        command = self.config.get_linux_launch_command()

        if not command:

            raise RuntimeError(
                "Kein Start-Befehl hinterlegt (Einstellungen -> "
                "WoW-Client)."
            )

        try:

            args = shlex.split(command)

        except ValueError as exc:

            raise RuntimeError(
                f"Start-Befehl ist ungültig: {exc}"
            ) from exc

        subprocess.Popen(
            args,
            env=Runtime.clean_subprocess_env(),
            start_new_session=True,
        )
