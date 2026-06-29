from __future__ import annotations

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

        try:

            zip_file = self.manager.downloader.download(
                state.github_download_url,
                destination,
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