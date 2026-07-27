from __future__ import annotations

from core.downloader import ChecksumError
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

                backup = self.manager.backup.create_backup(
                    state.addon_path
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

            return WorkflowResult(
                success=False,
                message="Installation fehlgeschlagen.",
            )

        logger.success(
            "Installation abgeschlossen."
        )

        #
        # Status komplett aktualisieren
        #

        self.manager.full_refresh()

        return WorkflowResult(
            success=True,
            message="Installation erfolgreich abgeschlossen.",
        )