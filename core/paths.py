from pathlib import Path
import os
import platform


class Paths:

    # --------------------------------------------------
    # Basisverzeichnis
    # --------------------------------------------------

    @staticmethod
    def base() -> Path:

        system = platform.system()

        #
        # Linux
        #

        if system == "Linux":

            return (
                Path.home()
                / ".local"
                / "share"
                / "WeintCompanion"
            )

        #
        # Windows
        #

        if system == "Windows":

            local = os.getenv("LOCALAPPDATA")

            if local:

                return (
                    Path(local)
                    / "WeintCompanion"
                )

        #
        # Fallback
        #

        return (
            Path.home()
            / ".weintcompanion"
        )

    # --------------------------------------------------

    @staticmethod
    def cache() -> Path:

        path = (
            Paths.base()
            / "cache"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # --------------------------------------------------

    @staticmethod
    def downloads() -> Path:

        path = (
            Paths.cache()
            / "downloads"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # --------------------------------------------------

    @staticmethod
    def backups() -> Path:

        path = (
            Paths.cache()
            / "backups"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # --------------------------------------------------

    @staticmethod
    def logs() -> Path:

        path = (
            Paths.cache()
            / "logs"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    # --------------------------------------------------

    @staticmethod
    def config() -> Path:

        path = (
            Paths.base()
            / "config"
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path