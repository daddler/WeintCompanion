from __future__ import annotations

from core.downloader import ChecksumError
from core.install_errors import permission_message, probe_writable
from core.paths import Paths
from core.workflow_result import WorkflowResult


class InstallerWorkflow:

    def __init__(self, manager):

        self.manager = manager

    # --------------------------------------------------

    def run(self) -> WorkflowResult:

        state = self.manager.state
        logger = self.manager.logger

        #
        # Download-URL vorhanden?
        #

        if not state.github_download_url:

            logger.error(
                "Keine Download-URL gefunden."
            )

            return WorkflowResult(
                success=False,
                message="Keine Download-URL gefunden.",
            )

        #
        # SCHREIBRECHT ZUERST, VOR DEM DOWNLOAD.
        #
        # Gemeldet wurde: "der Download startet normal, bricht dann aber
        # einfach wieder ab". Genau so sah es aus - fuenf Megabyte
        # geladen, ein Backup angelegt, und erst danach scheiterte die
        # Installation an einem Recht, das schon vorher feststand. Die
        # Frage kostet nichts und beantwortet sich in Millisekunden;
        # sie danach zu stellen heisst, jemanden erst warten zu lassen
        # und ihm dann zu sagen, dass es von Anfang an nicht ging.
        #
        # Zurueckhaltend: nur wenn die Probe SICHER "nein" sagt, wird
        # hier abgebrochen. Sie kann sich irren (Virenscanner,
        # Netzlaufwerk), und dann soll der echte Kopiervorgang
        # entscheiden statt einer Vermutung.
        #

        if state.addon_path and not probe_writable(state.addon_path.parent):

            reason = permission_message(
                state.addon_path.parent, folder_writable=False
            )

            logger.error(reason)

            return WorkflowResult(success=False, message=reason)

        #
        # Dateiname
        #

        filename = (
            state.github_asset_name
            or f"WeintCodex-{state.github_version}.zip"
        )

        #
        # Download-Ziel
        #

        destination = (
            Paths.downloads()
            / filename
        )

        #
        # Download
        #

        logger.info(
            "Lade WeintCodex herunter..."
        )

        #
        # Anders als beim Companion-Self-Update (eigenes Repo, eigene
        # CI) liegt das WeintCodex-Release in einem separaten Repo,
        # dessen CI keine Prüfsumme garantiert veröffentlicht. Ist
        # eine vorhanden, wird sie verifiziert; fehlt sie, wird nur
        # gewarnt statt der Download blockiert - die Lua/XML-Dateien
        # landen ohnehin nur im WoW-Addon-Sandbox-Verzeichnis, nicht
        # als ausgeführte Binary.
        #

        if not state.github_sha256:

            logger.warning(
                "Für dieses WeintCodex-Release ist keine Prüfsumme "
                "verfügbar - Integrität kann nicht verifiziert werden."
            )

        try:

            zip_file = self.manager.downloader.download(
                state.github_download_url,
                destination,
                expected_sha256=state.github_sha256 or None,
            )

        except ChecksumError as exc:

            logger.error(
                f"Prüfsummen-Verifikation fehlgeschlagen: {exc}"
            )

            return WorkflowResult(
                success=False,
                message="Prüfsummen-Verifikation fehlgeschlagen.",
            )

        except Exception as exc:

            logger.error(
                f"Download fehlgeschlagen: {exc}"
            )

            return WorkflowResult(
                success=False,
                message="Download fehlgeschlagen.",
            )

        logger.success(
            "Download abgeschlossen."
        )

        #
        # Backup
        #

        backup = None

        if state.addon_found:

            logger.info(
                "Erstelle Backup..."
            )

            try:

                #
                # Der WoW-Ordner kommt mit: das Backup sichert seit
                # 2.7.1 auch die SavedVariables des Addons, also
                # Bossnotizen, Twinks und Fortschritt. Der Addon-Ordner
                # allein waere das Backup dessen, was ohnehin bei
                # GitHub liegt (siehe core/backup.py).
                #

                backup = self.manager.backup.create_backup(
                    state.addon_path,
                    state.wow_path,
                )

                logger.success(
                    f"Backup erstellt: {backup.name}"
                )

            except Exception as exc:

                logger.error(
                    f"Backup fehlgeschlagen: {exc}"
                )

                return WorkflowResult(
                    success=False,
                    message="Backup fehlgeschlagen.",
                )

        #
        # Installation
        #

        logger.info(
            "Installiere WeintCodex..."
        )

        try:

            self.manager.installer.install(
                zip_file,
                state.addon_path,
            )

        except Exception as exc:

            logger.error(
                f"Installation fehlgeschlagen: {exc}"
            )

            #
            # Best-Effort-Rettung: der atomare Swap in Installer.install()
            # lässt bei einem Fehler bereits die alte Version an Ort
            # und Stelle - dieser Restore greift nur, falls trotzdem
            # ein inkonsistenter Zustand entstanden ist (z. B. weil
            # addon_path danach fehlt). Ein Fehlschlag hier wird nur
            # geloggt, der ursprüngliche Installationsfehler bleibt
            # das gemeldete Ergebnis.
            #

            if backup is not None and not state.addon_path.exists():

                logger.warning(
                    "Versuche Wiederherstellung aus dem Backup..."
                )

                if self.manager.backup.restore(backup, state.addon_path):

                    logger.success(
                        "Vorherige Version aus Backup wiederhergestellt."
                    )

                else:

                    logger.error(
                        "Wiederherstellung aus dem Backup ist ebenfalls "
                        "fehlgeschlagen."
                    )

            #
            # Der Satz aus der Ausnahme, nicht "Installation
            # fehlgeschlagen." - die Update-Karte zeigt genau diese
            # Meldung an, und die Ursache steht nur in der Ausnahme.
            # Siehe core/install_errors.py: bei einer Rechtefrage ist
            # sie bereits der fertige deutsche Satz.
            #

            return WorkflowResult(
                success=False,
                message=str(exc) or "Installation fehlgeschlagen.",
            )

        logger.success(
            "Installation abgeschlossen."
        )

        #
        # Gerade sind ein Archiv und ein Backup dazugekommen: neu
        # zaehlen lassen, statt bis zum naechsten traegen Takt zu
        # warten (siehe core/storage_watch.py).
        #

        watch = getattr(self.manager, "storage_watch", None)

        if watch is not None:
            watch.invalidate()

        #
        # Status komplett aktualisieren
        #

        self.manager.full_refresh()

        return WorkflowResult(
            success=True,
            message="Installation erfolgreich abgeschlossen.",
        )