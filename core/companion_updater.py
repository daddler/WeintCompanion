from pathlib import Path

from core.github_updater import GitHubUpdater
from core.linux_updater import LinuxUpdater
from core.runtime import Runtime
from core.version import VERSION


class CompanionUpdater:

    def __init__(self, manager):

        self.manager = manager

        self.github = GitHubUpdater(
            owner="daddler",
            repo="WeintCompanion",
        )

        self.linux = LinuxUpdater()

    # --------------------------------------------------

    @staticmethod
    def normalize(version):

        if not version:
            return ""

        return (
            version
            .strip()
            .lower()
            .removeprefix("v")
        )

    # --------------------------------------------------
    # Auf Updates prüfen
    # --------------------------------------------------

    def check_for_update(self):

        state = self.manager.state

        release = self.github.get_latest_release()

        if release is None:

            state.companion_latest_version = "-"
            state.companion_download_url = ""
            state.companion_asset_name = ""
            state.companion_update_available = False

            self.manager.logger.error(
                "Companion konnte nicht auf Updates geprüft werden."
            )

            return

        state.companion_latest_version = release.version
        state.companion_download_url = release.download_url
        state.companion_asset_name = release.asset_name

        current = self.normalize(VERSION)
        latest = self.normalize(release.version)

        state.companion_update_available = (
            current != latest
        )

        if state.companion_update_available:

            self.manager.logger.info(
                f"Neue Companion-Version verfügbar ({release.version})."
            )

        else:

            self.manager.logger.success(
                "Companion ist aktuell."
            )

    # --------------------------------------------------
    # Update herunterladen
    # --------------------------------------------------

    def download_update(self):

        state = self.manager.state

        if not state.companion_update_available:

            self.manager.logger.info(
                "Companion ist bereits aktuell."
            )

            return None

        if not state.companion_download_url:

            self.manager.logger.error(
                "Keine Download-URL vorhanden."
            )

            return None

        filename = (
            state.companion_asset_name
            or f"WeintCompanion-{state.companion_latest_version}"
        )

        #
        # Zielpfad bestimmen
        #

        if Runtime.is_linux() and Runtime.is_appimage():

            current = Runtime.current_executable()

            destination = current.with_name(
                current.name + ".new"
            )

        else:

            destination = (
                Path("cache")
                / "downloads"
                / filename
            )

        self.manager.logger.info(
            "Lade Companion-Update herunter..."
        )

        try:

            file = self.manager.downloader.download(
                state.companion_download_url,
                destination,
            )

        except Exception as exc:

            self.manager.logger.error(
                f"Download fehlgeschlagen: {exc}"
            )

            return None

        self.manager.logger.success(
            "Companion-Update heruntergeladen."
        )

        return Path(file)

    # --------------------------------------------------
    # Update starten
    # --------------------------------------------------

    def install_update(self):

        file = self.download_update()

        if file is None:
            return False

        try:

            #
            # Linux (AppImage)
            #

            if Runtime.is_linux() and Runtime.is_appimage():

                current = Runtime.current_executable()

                self.manager.logger.info(
                    "Erstelle Linux-Update..."
                )

                script = self.linux.create_update_script(
                    downloaded_appimage=file,
                    current_appimage=current,
                )

                self.manager.logger.info(
                    "Starte Update-Skript..."
                )
                #
                # Polling vor dem Update beenden
                #

                self.manager.stop_auto_sync()

                self.manager.launcher.launch_and_exit(
                    script
                )

                return True

            #
            # Windows / macOS
            #

            self.manager.logger.info(
                "Starte Installer..."
            )

            #
            # Polling vor dem Update beenden
            #

            self.manager.stop_auto_sync()    
            self.manager.launcher.launch_and_exit(
                file
            )

            return True

        except Exception as exc:

            self.manager.logger.error(
                f"Update konnte nicht gestartet werden: {exc}"
            )

            return False