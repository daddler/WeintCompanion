from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from core.paths import Paths


class SettingsPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        title = QLabel("Einstellungen")
        title.setObjectName("title")

        subtitle = QLabel(
            "Verwalte allgemeine Einstellungen sowie Speicher und Installationspfade."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        #
        # --------------------------------------------------
        # Allgemein
        # --------------------------------------------------
        #

        general = QGroupBox("Allgemein")
        general_layout = QVBoxLayout(general)

        self.update_check = QCheckBox(
            "Beim Start nach Updates suchen"
        )

        self.sync_check = QCheckBox(
            "Automatisch synchronisieren"
        )

        general_layout.addWidget(self.update_check)
        general_layout.addWidget(self.sync_check)

        interval_layout = QHBoxLayout()

        interval_layout.addWidget(
            QLabel("Synchronisationsintervall:")
        )

        self.interval = QSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setSuffix(" Minuten")

        interval_layout.addWidget(self.interval)
        interval_layout.addStretch()

        general_layout.addLayout(interval_layout)

        layout.addWidget(general)

        #
        # --------------------------------------------------
        # World of Warcraft
        # --------------------------------------------------
        #

        wow = QGroupBox("World of Warcraft")

        wow_layout = QVBoxLayout(wow)

        self.path_label = QLabel("-")

        wow_layout.addWidget(self.path_label)

        self.change_button = QPushButton(
            "📂 Classic-Ordner auswählen"
        )

        wow_layout.addWidget(self.change_button)

        layout.addWidget(wow)

        #
        # --------------------------------------------------
        # Speicherverwaltung
        # --------------------------------------------------
        #

        storage = QGroupBox("Speicherverwaltung")

        storage_layout = QVBoxLayout(storage)

        #
        # Downloads
        #

        self.download_label = QLabel("-")

        storage_layout.addWidget(
            QLabel("Downloads")
        )

        storage_layout.addWidget(
            self.download_label
        )

        self.clear_downloads = QPushButton(
            "🗑 Downloads löschen"
        )

        storage_layout.addWidget(
            self.clear_downloads
        )

        #
        # Backups
        #

        self.backup_label = QLabel("-")

        storage_layout.addSpacing(10)

        storage_layout.addWidget(
            QLabel("Backups")
        )

        storage_layout.addWidget(
            self.backup_label
        )

        self.clear_backups = QPushButton(
            "🗑 Backups löschen"
        )

        storage_layout.addWidget(
            self.clear_backups
        )

        layout.addWidget(storage)

        #
        # --------------------------------------------------
        # Speichern
        # --------------------------------------------------
        #

        self.save_button = QPushButton(
            "💾 Einstellungen speichern"
        )

        layout.addWidget(self.save_button)

        layout.addStretch()

        #
        # --------------------------------------------------
        # Signale
        # --------------------------------------------------
        #

        self.change_button.clicked.connect(
            self.choose_folder
        )

        self.clear_downloads.clicked.connect(
            self.clear_download_cache
        )

        self.clear_backups.clicked.connect(
            self.clear_backups_folder
        )

        self.save_button.clicked.connect(
            self.save_settings
        )

        self.refresh()

    # --------------------------------------------------
    # Oberfläche aktualisieren
    # --------------------------------------------------

    def refresh(self):

        config = self.manager.config

        #
        # Classic-Pfad
        #

        path = config.get_classic_path()

        if path:
            self.path_label.setText(str(path))
        else:
            self.path_label.setText(
                "Kein Classic-Pfad ausgewählt."
            )

        #
        # Einstellungen
        #

        self.update_check.setChecked(
            config.data.get(
                "check_updates",
                True,
            )
        )

        self.sync_check.setChecked(
            config.data.get(
                "auto_sync",
                False,
            )
        )

        self.interval.setValue(
            config.data.get(
                "sync_interval",
                5,
            )
        )

        #
        # Downloads
        #

        download_dir = Paths.downloads()

        if download_dir.exists():

            files = [
                f for f in download_dir.iterdir()
                if f.is_file()
            ]

            self.download_label.setText(
                f"{len(files)} Datei(en)"
            )

            self.clear_downloads.setEnabled(
                len(files) > 0
            )

        else:

            self.download_label.setText(
                "0 Dateien"
            )

            self.clear_downloads.setEnabled(False)

        #
        # Backups
        #

        backup_dir = Paths.backups()

        if backup_dir.exists():

            files = [
                f for f in backup_dir.iterdir()
                if f.is_file()
            ]

            self.backup_label.setText(
                f"{len(files)} Sicherung(en)"
            )

            self.clear_backups.setEnabled(
                len(files) > 0
            )

        else:

            self.backup_label.setText(
                "0 Sicherungen"
            )

            self.clear_backups.setEnabled(False)

    # --------------------------------------------------
    # WoW-Ordner auswählen
    # --------------------------------------------------

    def choose_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "MoP Classic auswählen",
        )

        if not folder:
            return

        folder = Path(folder)

        if (
            folder.name == "World of Warcraft"
            and
            (folder / "_classic_").exists()
        ):
            folder = folder / "_classic_"

        if not (
            (folder / "Interface").exists()
            and
            (folder / "Interface" / "AddOns").exists()
            and
            (folder / "WTF").exists()
        ):

            QMessageBox.warning(
                self,
                "Ungültiger Ordner",
                "Dies ist kein gültiger MoP-Classic-Ordner."
            )

            return

        self.manager.config.set_classic_path(folder)

        self.manager.refresh()

        self.manager.logger.success(
            f"Classic-Pfad geändert: {folder}"
        )

        self.refresh()

    # --------------------------------------------------
    # Einstellungen speichern
    # --------------------------------------------------

    def save_settings(self):

        config = self.manager.config

        config.data["check_updates"] = (
            self.update_check.isChecked()
        )

        config.data["auto_sync"] = (
            self.sync_check.isChecked()
        )

        config.data["sync_interval"] = (
            self.interval.value()
        )

        config.save()

        self.manager.logger.success(
            "Einstellungen gespeichert."
        )

    # --------------------------------------------------
    # Download-Cache löschen
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

    # --------------------------------------------------
    # Backups löschen
    # --------------------------------------------------

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