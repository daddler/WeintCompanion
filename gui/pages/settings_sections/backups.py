from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from core.paths import Paths
from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton

from ._common import SectionContent


def _storage_row(title_text: str):

    row = QWidget()

    layout = QHBoxLayout(row)

    layout.setContentsMargins(0, 0, 0, 0)

    layout.setSpacing(20)

    text_col = QVBoxLayout()

    text_col.setSpacing(4)

    title = QLabel(title_text)

    title.setStyleSheet(
        f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
    )

    text_col.addWidget(title)

    detail = QLabel("-")

    detail.setStyleSheet(
        f"font-size:13px;color:{Colors.TEXT_MUTED};"
    )

    text_col.addWidget(detail)

    layout.addLayout(text_col, 1)

    button = HeroButton("Löschen", primary=False)

    layout.addWidget(button)

    return row, detail, button


class BackupsSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · BACKUPS",
            "Backups",
            "Lokale Speicherorte für Downloads und Addon-Backups.",
        )

        self.manager = manager

        download_row, self.download_label, self.clear_downloads = _storage_row(
            "Downloads"
        )

        self.addRow(download_row)

        backup_row, self.backup_label, self.clear_backups = _storage_row(
            "Backups"
        )

        self.addRow(backup_row, divider=False)

        self.clear_downloads.clicked.connect(
            self.clear_download_cache
        )

        self.clear_backups.clicked.connect(
            self.clear_backups_folder
        )

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        download_dir = Paths.downloads()

        download_count = 0

        if download_dir.exists():

            download_count = sum(
                1
                for file in download_dir.iterdir()
                if file.is_file()
            )

        if download_count == 0:

            self.download_label.setText("Keine Downloads im Cache")

        elif download_count == 1:

            self.download_label.setText("1 Datei im Download-Cache")

        else:

            self.download_label.setText(
                f"{download_count} Dateien im Download-Cache"
            )

        self.clear_downloads.setEnabled(download_count > 0)

        backup_dir = Paths.backups()

        backup_count = 0

        if backup_dir.exists():

            backup_count = sum(
                1
                for file in backup_dir.iterdir()
                if file.is_file()
            )

        if backup_count == 0:

            self.backup_label.setText("Keine Backups vorhanden")

        elif backup_count == 1:

            self.backup_label.setText("1 Backup vorhanden")

        else:

            self.backup_label.setText(
                f"{backup_count} Backups vorhanden"
            )

        self.clear_backups.setEnabled(backup_count > 0)

    # --------------------------------------------------

    def clear_download_cache(self):

        answer = QMessageBox.question(
            self,
            "Downloads löschen",
            "Alle heruntergeladenen Dateien wirklich löschen?",
        )

        if answer != QMessageBox.Yes:
            return

        download_dir = Paths.downloads()

        count = 0

        if download_dir.exists():

            for file in download_dir.iterdir():

                if file.is_file():

                    file.unlink()

                    count += 1

        self.manager.logger.success(
            f"{count} Download(s) gelöscht."
        )

        self.refresh()

    def clear_backups_folder(self):

        answer = QMessageBox.question(
            self,
            "Backups löschen",
            "Alle Backups wirklich löschen?",
        )

        if answer != QMessageBox.Yes:
            return

        backup_dir = Paths.backups()

        count = 0

        if backup_dir.exists():

            for file in backup_dir.iterdir():

                if file.is_file():

                    file.unlink()

                    count += 1

        self.manager.logger.success(
            f"{count} Backup(s) gelöscht."
        )

        self.refresh()
