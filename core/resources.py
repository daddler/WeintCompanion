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
        """
        Das Ökosystem-Artwork - Startbildschirm und Einstellungen →
        Über zeigen dasselbe Bild.

        Fällt auf das alte `hero_banner.png` zurück, solange
        `splash.png` nicht vorliegt: ein fehlendes Bild ergäbe sonst
        eine leere `QPixmap`, und der Startbildschirm bestünde aus
        einem schwarzen Rechteck mit einem Ladebalken darin. Der
        Rückfall ist damit kein Notnagel, sondern die Zusicherung,
        dass der Start nie an einer Datei hängt.
        """

        artwork = Resources.root() / "assets" / "splash.png"

        if artwork.exists():
            return str(artwork)

        return Resources.path(
            "assets/hero_banner.png"
        )

    @staticmethod
    def icon():

        return Resources.path(
            "assets/icon.png"
        )

    @staticmethod
    def home():

        return Resources.path(
            "resources/icons/dashboard.svg"
        )

    @staticmethod
    def package():

        return Resources.path(
            "resources/icons/software.svg"
        )

    @staticmethod
    def sync():

        return Resources.path(
            "resources/icons/sync.svg"
        )

    @staticmethod
    def settings():

        return Resources.path(
            "resources/icons/settings.svg"
        )

    @staticmethod
    def logs():

        return Resources.path(
            "resources/icons/logs.svg"
        )

    # --------------------------------------------------
    # SVG Icons
    # --------------------------------------------------

    @staticmethod
    def dashboard():

        return Resources.path(
            "resources/icons/dashboard.svg"
        )

    @staticmethod
    def software():

        return Resources.path(
            "resources/icons/software.svg"
        )

    @staticmethod
    def game():

        return Resources.path(
            "resources/icons/game.svg"
        )

    @staticmethod
    def github():

        return Resources.path(
            "resources/icons/github.svg"
        )

    @staticmethod
    def backup():

        return Resources.path(
            "resources/icons/backup.svg"
        )

    @staticmethod
    def download():

        return Resources.path(
            "resources/icons/download.svg"
        )

    @staticmethod
    def folder():

        return Resources.path(
            "resources/icons/folder.svg"
        )

    @staticmethod
    def discord():

        return Resources.path(
            "resources/icons/discord.svg"
        )

    @staticmethod
    def discord_mark():
        """
        Das tatsächliche Discord-Logo (Clyde-Mark) - anders als
        Resources.discord() (generisches Chat-Icon), für Stellen, an
        denen die Marke selbst erkennbar sein soll (z. B. der
        Verbindungsstatus-Button).
        """

        return Resources.path(
            "resources/icons/discord_mark.svg"
        )

    @staticmethod
    def changelog():

        return Resources.path(
            "resources/icons/changelog.svg"
        )

    @staticmethod
    def trash():

        return Resources.path(
            "resources/icons/papierkorb.svg"
        )
    
    @staticmethod
    def settings():

        return Resources.path(
            "resources/icons/settings.svg"
        )
    
    @staticmethod
    def sync():

        return Resources.path(
            "resources/icons/sync.svg"
        )
    
    @staticmethod
    def logs():

        return Resources.path(
            "resources/icons/logs.svg"
        )

    @staticmethod
    def companion():
        return Resources.path(
            "resources/icons/companion.svg"
        )

    @staticmethod
    def weinttv():
        return Resources.path(
            "resources/icons/weinttv.svg"
        )

    @staticmethod
    def academy():
        return Resources.path(
            "resources/icons/academy.svg"
        )

    @staticmethod
    def wow():
        return Resources.game()

    @staticmethod
    def addon():
        return Resources.software()