from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QCheckBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.hero_banner import HeroButton
from gui.widgets.section_card import SectionCard
from core.paths import Paths
from core.resources import Resources


class _DiscordLoginBridge(QObject):
    """
    Meldet das Ergebnis des Discord-Logins thread-sicher an den
    Hauptthread zurück (der Login blockiert im Hintergrund-Thread,
    siehe SettingsPage._run_discord_login).
    """

    finished = Signal(object, object)  # (result_dict | None, error_str | None)


class SettingsPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        self._discord_bridge = _DiscordLoginBridge(self)
        self._discord_bridge.finished.connect(
            self._on_discord_login_finished
        )

        # --------------------------------------------------
        # Titel
        # --------------------------------------------------

        title = QLabel("Einstellungen")
        title.setObjectName("title")

        subtitle = QLabel(
            "Verwalte WeintCompanion, Synchronisation und lokale Speicherorte."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        #
        # ==================================================
        # Allgemein
        # ==================================================
        #

        general = SectionCard(
            Resources.settings(),
            "Allgemeine Einstellungen",
        )

        general_layout = QVBoxLayout()
        general_layout.setSpacing(14)

        self.update_check = QCheckBox(
            "Beim Start nach Updates suchen"
        )

        self.sync_check = QCheckBox(
            "Automatische Synchronisation aktivieren"
        )

        general_layout.addWidget(
            self.update_check
        )

        general_layout.addWidget(
            self.sync_check
        )

        interval_row = QHBoxLayout()

        interval_row.addWidget(
            QLabel("Synchronisationsintervall")
        )

        self.interval = QSpinBox()

        self.interval.setRange(2, 300)

        self.interval.setSuffix(" Sekunden")

        interval_row.addStretch()

        interval_row.addWidget(
            self.interval
        )

        general_layout.addLayout(
            interval_row
        )

        general.addLayout(
            general_layout
        )

        layout.addWidget(
            general
        )

        #
        # ==================================================
        # World of Warcraft
        # ==================================================
        #

        wow = SectionCard(
            Resources.game(),
            "World of Warcraft",
        )

        wow_layout = QVBoxLayout()
        wow_layout.setSpacing(12)

        #
        # Status
        #

        self.path_status = QLabel(
            "Classic gefunden"
        )

        self.path_status.setStyleSheet("""
        QLabel{
            color:#78D879;
            font-size:14px;
            font-weight:700;
            background:transparent;
        }
        """)

        wow_layout.addWidget(
            self.path_status
        )

        #
        # Installationspfad
        #

        self.path_label = QLabel("-")

        self.path_label.setWordWrap(True)

        self.path_label.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:13px;
            background:transparent;
        }
        """)

        wow_layout.addWidget(
            self.path_label
        )

        #
        # Button
        #

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.change_button = HeroButton(
            "Classic-Ordner auswählen",
            primary=False,
        )

        button_row.addWidget(
            self.change_button
        )

        wow_layout.addLayout(
            button_row
        )

        wow.addLayout(
            wow_layout
        )

        layout.addWidget(
            wow
        )

        #
        # ==================================================
        # Discord
        # ==================================================
        #

        discord = SectionCard(
            Resources.discord(),
            "Discord",
        )

        discord_layout = QVBoxLayout()
        discord_layout.setSpacing(12)

        self.discord_status = QLabel("Nicht verbunden")

        self.discord_status.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:14px;
            font-weight:700;
            background:transparent;
        }
        """)

        discord_layout.addWidget(
            self.discord_status
        )

        self.discord_hint = QLabel(
            "Verknüpfe deinen Discord-Account, damit Companion "
            "deinen Raid-Roster automatisch ans Addon übergeben kann."
        )

        self.discord_hint.setWordWrap(True)

        self.discord_hint.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:13px;
            background:transparent;
        }
        """)

        discord_layout.addWidget(
            self.discord_hint
        )

        discord_button_row = QHBoxLayout()

        discord_button_row.addStretch()

        self.discord_unlink_button = HeroButton(
            "Trennen",
            primary=False,
        )

        self.discord_login_button = HeroButton(
            "Mit Discord verbinden",
            primary=True,
        )

        discord_button_row.addWidget(
            self.discord_unlink_button
        )

        discord_button_row.addWidget(
            self.discord_login_button
        )

        discord_layout.addLayout(
            discord_button_row
        )

        discord.addLayout(
            discord_layout
        )

        layout.addWidget(
            discord
        )

        #
        # ==================================================
        # Speicherverwaltung
        # ==================================================
        #

        storage = SectionCard(
            Resources.backup(),
            "Speicherverwaltung",
        )

        storage_layout = QVBoxLayout()
        storage_layout.setSpacing(18)

        #
        # Downloads
        #

        download_row = QHBoxLayout()
        download_row.setSpacing(20)

        download_info = QVBoxLayout()
        download_info.setSpacing(4)

        download_title = QLabel("Downloads")

        download_title.setStyleSheet("""
        QLabel{
            color:white;
            font-size:15px;
            font-weight:700;
            background:transparent;
        }
        """)

        self.download_label = QLabel("-")

        self.download_label.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:13px;
            background:transparent;
        }
        """)

        download_info.addWidget(download_title)
        download_info.addWidget(self.download_label)

        download_row.addLayout(download_info)

        download_row.addStretch()

        self.clear_downloads = HeroButton(
            "Downloads löschen",
            primary=False,
        )

        download_row.addWidget(
            self.clear_downloads
        )

        storage_layout.addLayout(
            download_row
        )

        #
        # Trennlinie
        #

        line = QLabel()

        line.setFixedHeight(1)

        line.setStyleSheet("""
        QLabel{
            background:#343945;
        }
        """)

        storage_layout.addWidget(line)

        #
        # Backups
        #

        backup_row = QHBoxLayout()
        backup_row.setSpacing(20)

        backup_info = QVBoxLayout()
        backup_info.setSpacing(4)

        backup_title = QLabel("Backups")

        backup_title.setStyleSheet("""
        QLabel{
            color:white;
            font-size:15px;
            font-weight:700;
            background:transparent;
        }
        """)

        self.backup_label = QLabel("-")

        self.backup_label.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:13px;
            background:transparent;
        }
        """)

        backup_info.addWidget(
            backup_title
        )

        backup_info.addWidget(
            self.backup_label
        )

        backup_row.addLayout(
            backup_info
        )

        backup_row.addStretch()

        self.clear_backups = HeroButton(
            "Backups löschen",
            primary=False,
        )

        backup_row.addWidget(
            self.clear_backups
        )

        storage_layout.addLayout(
            backup_row
        )

        storage.addLayout(
            storage_layout
        )

        layout.addWidget(
            storage
        )

        #
        # ==================================================
        # Speichern
        # ==================================================
        #

        button_row = QHBoxLayout()

        self.save_button = HeroButton(
            "Einstellungen speichern",
            primary=True,
        )

        button_row.addStretch()

        button_row.addWidget(
            self.save_button
        )

        layout.addLayout(
            button_row
        )

        layout.addStretch()

        #
        # ==================================================
        # Signale
        # ==================================================
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

        self.discord_login_button.clicked.connect(
            self.start_discord_login
        )

        self.discord_unlink_button.clicked.connect(
            self.discord_unlink
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

            self.path_status.setText(
                "Classic gefunden"
            )

            self.path_status.setStyleSheet("""
            QLabel{
                color:#78D879;
                font-size:14px;
                font-weight:700;
                background:transparent;
            }
            """)

            self.path_label.setText(
                str(path)
            )

        else:

            self.path_status.setText(
                "Kein Classic-Pfad ausgewählt"
            )

            self.path_status.setStyleSheet("""
            QLabel{
                color:#F28C8C;
                font-size:14px;
                font-weight:700;
                background:transparent;
            }
            """)

            self.path_label.setText(
                "Bitte wähle deinen World of Warcraft Classic-Ordner aus."
            )

        #
        # Discord
        #

        account = self.manager.discord_account.load()

        #
        # start_discord_login() deaktiviert den Button waehrend des
        # laufenden Logins - ohne diese Zeile blieb er nach JEDEM
        # refresh() (Login-Abschluss oder "Trennen") dauerhaft
        # deaktiviert, da ihn sonst nirgendwo etwas wieder aktiviert
        # hat. Das war der Bug: nach "Trennen" liess sich "Mit Discord
        # verbinden" nicht mehr anklicken, nur ein Neustart der App half.
        #

        self.discord_login_button.setEnabled(True)

        if account:

            self.discord_status.setText(
                f"Verbunden als {account.get('username', '?')}"
            )

            self.discord_status.setStyleSheet("""
            QLabel{
                color:#78D879;
                font-size:14px;
                font-weight:700;
                background:transparent;
            }
            """)

            if account.get("authorized"):

                self.discord_hint.setText(
                    "Dein Account darf den Raid-Roster automatisch "
                    "abrufen - Companion übergibt neue Anmeldungen "
                    "automatisch ans Addon."
                )

            else:

                self.discord_hint.setText(
                    "Verbunden, aber dieser Account darf den "
                    "Raid-Roster nicht abrufen (fehlende Rolle). "
                    "Wende dich an einen Raidlead/Officer."
                )

            self.discord_login_button.setText(
                "Erneut verbinden"
            )

            self.discord_unlink_button.setEnabled(True)

        else:

            self.discord_status.setText(
                "Nicht verbunden"
            )

            self.discord_status.setStyleSheet("""
            QLabel{
                color:#F28C8C;
                font-size:14px;
                font-weight:700;
                background:transparent;
            }
            """)

            self.discord_hint.setText(
                "Verknüpfe deinen Discord-Account, damit Companion "
                "deinen Raid-Roster automatisch ans Addon übergeben kann."
            )

            self.discord_login_button.setText(
                "Mit Discord verbinden"
            )

            self.discord_unlink_button.setEnabled(False)

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
                True,
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

        download_count = 0

        if download_dir.exists():

            download_count = sum(
                1
                for file in download_dir.iterdir()
                if file.is_file()
            )

        if download_count == 0:

            self.download_label.setText(
                "Keine Downloads im Cache"
            )

        elif download_count == 1:

            self.download_label.setText(
                "1 Datei im Download-Cache"
            )

        else:

            self.download_label.setText(
                f"{download_count} Dateien im Download-Cache"
            )

        self.clear_downloads.setEnabled(
            download_count > 0
        )

        #
        # Backups
        #

        backup_dir = Paths.backups()

        backup_count = 0

        if backup_dir.exists():

            backup_count = sum(
                1
                for file in backup_dir.iterdir()
                if file.is_file()
            )

        if backup_count == 0:

            self.backup_label.setText(
                "Keine Backups vorhanden"
            )

        elif backup_count == 1:

            self.backup_label.setText(
                "1 Backup vorhanden"
            )

        else:

            self.backup_label.setText(
                f"{backup_count} Backups vorhanden"
            )

        self.clear_backups.setEnabled(
            backup_count > 0
        )

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

    # --------------------------------------------------
    # Discord-Login
    # --------------------------------------------------
    # Der Login blockiert (öffnet den Browser, wartet auf den lokalen
    # Redirect, tauscht den Code beim Bot aus) - läuft deshalb in
    # einem Hintergrund-Thread, damit die UI währenddessen nicht
    # einfriert. Das Ergebnis kommt thread-sicher per Qt-Signal
    # zurück (siehe _CompanionUpdateBridge in dashboard.py fürs
    # gleiche Muster).

    def start_discord_login(self):

        self.discord_login_button.setEnabled(False)
        self.discord_unlink_button.setEnabled(False)

        self.discord_status.setText(
            "Browser öffnet sich - bitte Discord-Login abschließen..."
        )

        thread = threading.Thread(
            target=self._discord_login_worker,
            daemon=True,
            name="DiscordLoginThread",
        )

        thread.start()

    def _discord_login_worker(self):

        try:

            result = self.manager.discord_auth.login()

        except Exception as exc:

            self._discord_bridge.finished.emit(None, str(exc))

            return

        self._discord_bridge.finished.emit(result, None)

    def _on_discord_login_finished(self, result, error):

        if error:

            self.manager.logger.error(
                f"Discord-Login fehlgeschlagen: {error}"
            )

        else:

            self.manager.discord_account.save(result)

            if result.get("authorized"):

                self.manager.logger.success(
                    f"Discord verbunden als {result.get('username')}."
                )

            else:

                self.manager.logger.warning(
                    f"Discord verbunden als {result.get('username')}, "
                    "aber ohne Berechtigung für den Raid-Roster-Export."
                )

        self.refresh()

    # --------------------------------------------------
    # Discord trennen
    # --------------------------------------------------

    def discord_unlink(self):

        account = self.manager.discord_account.load()

        if account and account.get("companion_token"):

            self.manager.discord_auth.unlink(
                account["companion_token"]
            )

        self.manager.discord_account.clear()

        self.manager.logger.info(
            "Discord-Verknüpfung getrennt."
        )

        self.refresh()