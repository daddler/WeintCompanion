from pathlib import Path
import os
import shutil
import subprocess

from PySide6.QtWidgets import QApplication

from core.github_updater import GitHubUpdater
from core.linux_updater import LinuxUpdater
from core.windows_updater import WindowsUpdater
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
        self.windows = WindowsUpdater()

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
        # Linux-AppImage:
        # Download direkt neben die aktuelle AppImage
        #

        if Runtime.is_linux() and Runtime.is_appimage():

            current = Runtime.current_executable()

            destination = current.with_name(
                current.name + ".new"
            )

        #
        # Windows / Entwicklung
        #

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
    # Prozess von der eigenen systemd-Scope loslösen
    # --------------------------------------------------

    def _spawn_detached(self, args):
        """
        Startet das Updater-Skript so, dass es das Beenden von
        WeintCompanion überlebt.

        Hintergrund:
        Auf modernen Linux-Desktops (GNOME/KDE unter Fedora,
        openSUSE, CachyOS, ...) wird eine per Doppelklick oder
        aus dem Dateimanager gestartete AppImage häufig in einer
        eigenen transienten systemd-Scope ausgeführt
        ("app-...AppImage@....service").
        Beendet sich der Hauptprozess (hier über QApplication.quit()),
        beendet systemd standardmäßig (KillMode=control-group) die
        GESAMTE Cgroup - inklusive aller Kindprozesse. Das betrifft
        auch das Updater-Skript, selbst wenn es über
        start_new_session=True in eine eigene Sitzung gestartet wurde,
        denn eine neue Session ändert nichts an der Cgroup-Zugehörigkeit.

        Ergebnis: Der Updater wird zusammen mit WeintCompanion
        abgeschossen, bevor er die neue Version installieren kann -
        der Update-Button "funktioniert" scheinbar nicht.

        Lösung: Ist "systemd-run" verfügbar, wird der Updater in
        eine eigene, unabhängige transiente Scope ausgelagert
        (--user --scope), die das Beenden von WeintCompanion übersteht.
        """

        systemd_run = shutil.which("systemd-run")

        if systemd_run:

            try:

                subprocess.Popen(
                    [
                        systemd_run,
                        "--user",
                        "--scope",
                        "--collect",
                        "--quiet",
                        "--",
                    ]
                    + args,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                return

            except Exception as exc:

                self.manager.logger.warning(
                    f"systemd-run fehlgeschlagen, nutze Fallback: {exc}"
                )

        #
        # Fallback ohne systemd (z. B. andere Init-Systeme)
        #

        subprocess.Popen(
            args,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # --------------------------------------------------
    # Windows-Waiter starten (unabhängig vom eigenen Prozess)
    # --------------------------------------------------

    def _spawn_windows_waiter(self, script):
        """
        Startet das Wartescript unsichtbar (kein Konsolenfenster)
        und komplett unabhängig von WeintCompanion, damit es auch
        nach dem Beenden von WeintCompanion weiterläuft.
        """

        creationflags = 0

        creationflags |= getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        )

        creationflags |= getattr(
            subprocess,
            "DETACHED_PROCESS",
            0,
        )

        subprocess.Popen(
            [
                "cmd",
                "/c",
                str(script),
            ],
            creationflags=creationflags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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
                    "Bereite Linux-Update vor..."
                )

                script = self.linux.prepare(
                    downloaded_appimage=file,
                    current_appimage=current,
                )

                self.manager.stop_auto_sync()

                self._spawn_detached(
                    [
                        str(script),
                        str(current),
                        str(file),
                        str(os.getpid()),
                    ]
                )

                QApplication.quit()

                return True

            #
            # Windows
            #

            if Runtime.is_windows():

                self.manager.logger.info(
                    "Bereite Windows-Update vor..."
                )

                script = self.windows.prepare(
                    installer=file,
                    pid=os.getpid(),
                )

                self.manager.stop_auto_sync()

                self._spawn_windows_waiter(script)

                QApplication.quit()

                return True

            #
            # macOS
            #

            self.manager.logger.info(
                "Starte Installer..."
            )

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