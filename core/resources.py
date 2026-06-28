from __future__ import annotations

import sys
from pathlib import Path


class Resources:

    @staticmethod
    def root() -> Path:
        """
        Gibt den Projektordner zurück.

        Entwicklung:
            Projektordner/

        PyInstaller:
            _MEIPASS/
        """

        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)

        return Path(__file__).resolve().parent.parent

    # --------------------------------------------------

    @staticmethod
    def path(relative: str) -> str:

        return str(
            Resources.root() / relative
        )

    # --------------------------------------------------
    # Assets
    # --------------------------------------------------

    @staticmethod
    def logo():

        return Resources.path(
            "assets/logo.png"
        )

    @staticmethod
    def banner():

        return Resources.path(
            "assets/companion_banner.png"
        )

    @staticmethod
    def icon():

        return Resources.path(
            "assets/icon.png"
        )

    @staticmethod
    def home():

        return Resources.path(
            "assets/home.png"
        )

    @staticmethod
    def package():

        return Resources.path(
            "assets/package.png"
        )

    @staticmethod
    def sync():

        return Resources.path(
            "assets/sync.png"
        )

    @staticmethod
    def settings():

        return Resources.path(
            "assets/settings.png"
        )

    @staticmethod
    def logs():

        return Resources.path(
            "assets/logs.png"
        )