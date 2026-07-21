from pathlib import Path
import os
import shutil
import subprocess

from core.github_updater import GitHubUpdater
from core.linux_updater import LinuxUpdater
from core.paths import Paths
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

    def check_for_update(self):

        state = self.manager.state

        self._warn_if_previous_update_incomplete()

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

        state.companion_update_available = not versions_equal(
            VERSION,
            release.version,
        )

        if state.companion_update_available:

            self.manager.logger.info(
                f"Neue Companion-Version verfügbar ({release.version})."
            )

        else:

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

        WICHTIG: systemd-run wird NUR verwendet, wenn wir auch
        wirklich in einer solchen Scope laufen UND eine
        funktionierende D-Bus-User-Session vorhanden ist. Auf
        schlankeren Setups (z. B. i3, Sway, Hyprland - häufig auf
        CachyOS) läuft die App oft gar nicht in einer Scope und/oder
        die D-Bus-Session-Umgebung ist für den Startkontext nicht
        vollständig gesetzt. In diesem Fall würde systemd-run im
        Hintergrund lautlos fehlschlagen (z. B. "Failed to create
        bus connection") - das Updater-Skript würde dann NIE
        ausgeführt, obwohl unser Python-Code keinen Fehler bemerkt
        (der Fehler passiert asynchron im schon gestarteten
        Kindprozess). Deshalb wird hier vorher aktiv geprüft, ob
        der Einsatz überhaupt nötig und sicher möglich ist - sonst
        wird direkt der normale, bewährte Fallback genutzt.
        """

        if self._running_in_systemd_scope() and self._has_dbus_session():

            systemd_run = shutil.which("systemd-run")

            if systemd_run:

                try:

                    #
                    # WICHTIG für Debugging:
                    # systemd-run kann asynchron fehlschlagen
                    # (z. B. "Failed to create bus connection"),
                    # ohne dass unser Popen()-Aufruf hier einen
                    # Fehler wirft. Deshalb wird die Ausgabe in
                    # eine Log-Datei neben der AppImage geschrieben,
                    # statt sie mit DEVNULL zu verwerfen - so lässt
                    # sich ein stiller Fehlschlag im Nachhinein
                    # nachvollziehen.
                    #

                    debug_log_path = (
                        Path(args[1]).parent
                        / "systemd-run-debug.log"
                    )

                    debug_log = open(
                        debug_log_path,
                        "w",
                        encoding="utf-8",
                    )

                    subprocess.Popen(
                        [
                            systemd_run,
                            "--user",
                            "--scope",
                            "--collect",
                            "--",
                        ]
                        + args,
                        start_new_session=True,
                        stdin=subprocess.DEVNULL,
                        stdout=debug_log,
                        stderr=debug_log,
                        #
                        # Siehe Runtime.clean_subprocess_env(): ohne
                        # das vererbt das AppImage-Bundle sein eigenes
                        # LD_LIBRARY_PATH an update.sh (und damit an
                        # jedes darin aufgerufene System-Tool wie mv/
                        # chmod/bash selbst) - klassisches "symbol
                        # lookup error", das update.sh lautlos
                        # abbrechen lässt, bevor es die AppImage
                        # ersetzen kann.
                        #
                        env=Runtime.clean_subprocess_env(),
                    )

                    return

                except Exception as exc:

                    self.manager.logger.warning(
                        f"systemd-run fehlgeschlagen, nutze Fallback: {exc}"
                    )

        #
        # Normaler Fallback (kein Desktop-Scope, kein systemd
        # oder keine D-Bus-Session - z. B. i3, Sway, Hyprland,
        # oder direkter Start über ein Terminal)
        #

        subprocess.Popen(
            args,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=Runtime.clean_subprocess_env(),
        )

    # --------------------------------------------------

    @staticmethod
    def _running_in_systemd_scope() -> bool:
        """
        Prüft, ob der aktuelle Prozess innerhalb einer
        transienten systemd-Scope läuft (typisch für Apps, die
        über GNOME/KDE per Doppelklick/Dateimanager gestartet
        wurden). Nur dann besteht überhaupt das Risiko, dass
        systemd beim Beenden die komplette Cgroup mitsamt dem
        Updater-Prozess killt.
        """

        try:

            cgroup_file = Path("/proc/self/cgroup")

            if not cgroup_file.exists():

                return False

            content = cgroup_file.read_text()

            return ".scope" in content

        except Exception:

            return False

    # --------------------------------------------------

    @staticmethod
    def _has_dbus_session() -> bool:
        """
        Prüft, ob eine funktionierende D-Bus-User-Session
        Umgebung vorhanden ist. systemd-run benötigt diese, um
        mit dem systemd --user Manager zu kommunizieren.
        """

        return bool(
            os.environ.get("DBUS_SESSION_BUS_ADDRESS")
            or os.environ.get("XDG_RUNTIME_DIR")
        )

    # --------------------------------------------------
    # Windows-Waiter starten (unabhängig vom eigenen Prozess)
    # --------------------------------------------------

    def _spawn_windows_waiter(self, script):
        """
        Startet das Wartescript unsichtbar (kein Konsolenfenster)
        und komplett unabhängig von WeintCompanion, damit es auch
        nach dem Beenden von WeintCompanion weiterläuft.

        WICHTIG: Hier NICHT zusätzlich DETACHED_PROCESS setzen.
        Laut Win32-Doku wird CREATE_NO_WINDOW ignoriert, wenn es
        zusammen mit DETACHED_PROCESS verwendet wird. Der Kind-
        prozess startet dann komplett ohne Konsole - "timeout"
        (aufgerufen aus dem Wartescript) braucht aber ein Konsolen-
        Handle, um auf STRG+C zu prüfen, und erzeugt sich in diesem
        Fall selbst ein neues, sichtbares Konsolenfenster. Genau das
        ist das eingefrorene "timeout /t 1 /nobreak"-Fenster, das
        Nutzer beim Update sehen. CREATE_NO_WINDOW allein reicht:
        der Kindprozess bekommt eine (unsichtbare) Konsole und läuft
        unabhängig von WeintCompanion weiter, da Windows-Kindprozesse
        ohnehin nicht am Elternprozess hängen.
        """

        creationflags = getattr(
            subprocess,
            "CREATE_NO_WINDOW",
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
            # macOS
            #

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