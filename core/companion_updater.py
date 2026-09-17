from pathlib import Path
import os

from core.downloader import ChecksumError
from core.github_updater import GitHubUpdater
from core.linux_updater import LinuxUpdater
from core.paths import Paths
from core.process_spawn import spawn_detached, spawn_windows_hidden
from core.windows_updater import WindowsUpdater
from core.runtime import Runtime
from core.version import VERSION, versions_equal


class CompanionUpdater:

    def __init__(self, manager):

        self.manager = manager

        self.github = GitHubUpdater(
            owner="daddler",
            repo="WeintCompanion",
        )

        self.linux = LinuxUpdater()
        self.windows = WindowsUpdater()

        self._changelog_commits = None

    # --------------------------------------------------
    # Auf Updates prüfen
    # --------------------------------------------------

    def check_for_update(self, quiet: bool = False):
        """
        `quiet`: dieselbe Prüfung ohne die Zeilen, die nur den Vollzug
        melden - für die Hintergrundwache, die alle fünfzehn Minuten
        fragt. Siehe `CompanionManager.check_github()`.
        """

        state = self.manager.state

        self._warn_if_previous_update_incomplete()

        release = self.github.get_latest_release()

        if release is None:

            state.companion_latest_version = "-"
            state.companion_download_url = ""
            state.companion_asset_name = ""
            state.companion_sha256 = ""
            state.companion_update_available = False

            if quiet:

                self.manager.logger.info(
                    "Companion konnte nicht auf Updates geprüft werden."
                )

            else:

                self.manager.logger.error(
                    "Companion konnte nicht auf Updates geprüft werden."
                )

            return

        state.companion_latest_version = release.version
        state.companion_download_url = release.download_url
        state.companion_asset_name = release.asset_name
        state.companion_sha256 = release.sha256 or ""

        state.companion_update_available = not versions_equal(
            VERSION,
            release.version,
        )

        if state.companion_update_available:

            self.manager.logger.info(
                f"Neue Companion-Version verfügbar ({release.version})."
            )

        elif not quiet:

            self.manager.logger.success(
                "Companion ist aktuell."
            )

        state.companion_changelog = self._get_changelog()

    # --------------------------------------------------
    # Changelog der installierten Version
    # --------------------------------------------------

    def _get_changelog(self):
        """
        Ergebnis wird für die Laufzeit des Prozesses zwischen-
        gespeichert - VERSION ändert sich erst nach einem Neustart.
        Ein Fehlschlag (None) wird NICHT zwischengespeichert, damit
        ein erneuter Update-Check (z. B. "Nach Updates suchen") nach
        einem vorübergehenden Netzwerkproblem erneut versuchen kann.
        """

        if self._changelog_commits is None:

            self._changelog_commits = (
                self.github.get_release_commits(VERSION)
            )

        return self._changelog_commits

    # --------------------------------------------------
    # Vorheriges Update prüfen
    # --------------------------------------------------

    def _warn_if_previous_update_incomplete(self):
        """
        Erkennt ein Update, das zuletzt nicht zu Ende lief (z. B. weil
        der Updater-Prozess durch eine systemd-Scope mit abgeschossen
        wurde, siehe _spawn_detached). In diesem Fall liegt neben der
        AppImage noch eine ".new"-Datei, die nie umbenannt wurde. Ohne
        diese Prüfung bemerkt der Nutzer das nur daran, dass "einfach
        nichts passiert" ist - hier wird es wenigstens sichtbar geloggt.
        """

        if not (Runtime.is_linux() and Runtime.is_appimage()):
            return

        current = Runtime.current_executable()

        leftover = current.with_name(
            current.name + ".new"
        )

        if leftover.exists():

            self.manager.logger.warning(
                "Das letzte Companion-Update wurde nicht abgeschlossen "
                f"({leftover.name} liegt noch neben der AppImage). "
                "Bitte Update erneut starten."
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

        #
        # Der Companion-Self-Updater ersetzt eine ausführbare Binary
        # und startet sie danach automatisch neu - ein Update ohne
        # verifizierbare Prüfsumme wird deshalb bewusst NICHT
        # heruntergeladen, statt es "trotzdem" zu versuchen. Die CI
        # (build.yml) veröffentlicht seit Einführung dieser Prüfung
        # zu jedem Release ein "<asset>.sha256" - fehlt sie, ist das
        # Release entweder älter als diese Änderung oder wurde
        # manipuliert.
        #

        if not state.companion_sha256:

            self.manager.logger.error(
                "Keine Prüfsumme für das Companion-Update verfügbar - "
                "Update wird aus Sicherheitsgründen abgebrochen."
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
                Paths.downloads()
                / filename
            )

        self.manager.logger.info(
            "Lade Companion-Update herunter..."
        )

        try:

            file = self.manager.downloader.download(
                state.companion_download_url,
                destination,
                expected_sha256=state.companion_sha256,
            )

        except ChecksumError as exc:

            self.manager.logger.error(
                f"Prüfsummen-Verifikation fehlgeschlagen: {exc}"
            )

            return None

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

        Der Ablauf samt seiner drei Lehren (systemd-Scope, D-Bus,
        bereinigte Umgebung) steht seit 4.1 in
        `core/process_spawn.py` - der Generationswechsel
        (`core/migration/handover.py`) startet die neue Anwendung
        auf demselben Weg, und zwei Kopien dieser Lehren wären zwei
        Stellen, an denen sie beim nächsten Mal nur an einer
        nachgezogen werden.
        """

        spawn_detached(
            args,
            logger=self.manager.logger,
        )

    # --------------------------------------------------
    # Windows-Waiter starten (unabhängig vom eigenen Prozess)
    # --------------------------------------------------

    def _spawn_windows_waiter(self, script):
        """
        Startet das Wartescript unsichtbar und unabhängig von
        WeintCompanion - Begründung der Creation-Flags siehe
        `core/process_spawn.spawn_windows_hidden()`.
        """

        spawn_windows_hidden(
            [
                "cmd",
                "/c",
                str(script),
            ]
        )

    # --------------------------------------------------
    # Update starten
    # --------------------------------------------------

    def install_update(self):
        """
        Läuft in einem Hintergrund-Thread (siehe
        DashboardPage._companion_update_worker) - deshalb dürfen hier
        KEINE Qt-Objekte angefasst werden, die dem Hauptthread gehören
        (QTimer, QApplication). stop_auto_sync() (intern QTimer.stop())
        muss der Aufrufer vorher im Hauptthread erledigen; ebenso darf
        QApplication.quit() erst zurück im Hauptthread passieren -
        sonst kann die App bei einem Cross-Thread-Zugriff auf das
        timer-gebundene Qt-Objekt hängen bleiben ("reagiert nicht"),
        statt sauber zu beenden.
        """

        file = self.download_update()

        if file is None:
            return False

        #
        # Ein leerer/fehlender Download darf niemals als "Update" an
        # den Updater weitergereicht werden (z. B. bei einem Verbindungs-
        # abbruch mitten im Stream, der keine Exception auslöst).
        #

        if not file.exists() or file.stat().st_size == 0:

            self.manager.logger.error(
                "Heruntergeladene Update-Datei ist leer oder fehlt."
            )

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

                self._spawn_detached(
                    [
                        str(script),
                        str(current),
                        str(file),
                        str(os.getpid()),
                    ]
                )

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

                self._spawn_windows_waiter(script)

                return True

            #
            # macOS - für 1.0 NICHT offiziell unterstützt: es gibt
            # weder ein Build-Skript noch einen CI-Job für ein
            # .dmg-Release, dieser Zweig ist ungetestet und läuft nur
            # noch mit, falls ihn jemand manuell aus dem Quellcode
            # startet. Vor einer echten macOS-Unterstützung braucht
            # es mindestens einen eigenen Build-/CI-Prozess (siehe
            # scripts/build_linux.sh bzw. build_windows.ps1 als
            # Vorbild) sowie einen Test auf echter Hardware.
            #

            self.manager.logger.warning(
                "macOS wird von WeintCompanion aktuell nicht offiziell "
                "unterstützt - der Installer-Start ist ungetestet."
            )

            self.manager.logger.info(
                "Starte Installer..."
            )

            #
            # launch() statt launch_and_exit(): Der Aufruf läuft im
            # Hintergrund-Thread, QApplication.quit() muss aber im
            # Hauptthread passieren (siehe Docstring oben) - das
            # übernimmt der Aufrufer nach Rückkehr dieser Funktion.
            #

            self.manager.launcher.launch(
                file
            )

            return True

        except Exception as exc:

            self.manager.logger.error(
                f"Update konnte nicht gestartet werden: {exc}"
            )

            return False