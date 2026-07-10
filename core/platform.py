import os
import platform
import subprocess
from pathlib import Path

from core.runtime import Runtime


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_linux() -> bool:
    return platform.system() == "Linux"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def open_folder(path):

    if path is None:
        return False

    path = Path(path)

    if not path.exists():
        return False

    try:

        if is_windows():

            os.startfile(path)

        elif is_linux():

            #
            # xdg-open ist meist selbst ein Shellskript - ohne
            # bereinigte Umgebung erbt es das AppImage-eigene
            # LD_LIBRARY_PATH und crasht lautlos (siehe
            # Runtime.clean_subprocess_env()).
            #

            subprocess.Popen(
                ["xdg-open", str(path)],
                env=Runtime.clean_subprocess_env(),
            )

        elif is_macos():

            subprocess.Popen(
                ["open", str(path)]
            )

        return True

    except Exception as e:

        print(e)

        return False