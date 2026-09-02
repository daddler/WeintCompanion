from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from core import storage_usage
from core.backup import backup_time_text
from core.paths import Paths
from gui.theme import tokens
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

    #
    # Der Satz, warum die Dateien da sind und dass Löschen nichts
    # kaputt macht. Er steht nur da, wenn der Ordner über der Grenze
    # liegt - wer aus der Meldung hierher kommt, soll den Grund
    # vorfinden, und wer aus eigenem Antrieb hier ist, braucht keine
    # Warnung über drei Backups.
    #

    hint = QLabel("")

    hint.setWordWrap(True)

    hint.setVisible(False)

    text_col.addWidget(hint)

    layout.addLayout(text_col, 1)

    button = HeroButton("Löschen", primary=False)

    layout.addWidget(button)

    return row, detail, hint, button


class BackupsSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · BACKUPS",
            "Backups",
            "Lokale Speicherorte für Downloads und Addon-Backups.",
        )

        self.manager = manager

        (
            download_row,
            self.download_label,
            self.download_hint,
            self.clear_downloads,
        ) = _storage_row("Downloads")

        self.addRow(download_row)

        (
            backup_row,
            self.backup_label,
            self.backup_hint,
            self.clear_backups,
        ) = _storage_row("Backups")

        self.addRow(backup_row)

        #
        # Der Rückweg. Seit 2.7.1 liegt in jedem Backup auch der
        # Spielstand des Addons - Bossnotizen, Twinks, Fortschritt.
        # Ohne diesen Knopf wäre er zwar gesichert, aber nur von Hand
        # aus einem ZIP zu holen, dessen Ort niemand kennt.
        #

        (
            restore_row,
            self.restore_label,
            self.restore_hint,
            self.restore_button,
        ) = _storage_row("Spielstand aus dem Backup")

        self.restore_button.setText("Zurückholen")

        self.addRow(restore_row, divider=False)

        self.clear_downloads.clicked.connect(
            self.clear_download_cache
        )

        self.clear_backups.clicked.connect(
            self.clear_backups_folder
        )

        self.restore_button.clicked.connect(
            self.restore_saved_variables
        )

        self.refresh()

    # --------------------------------------------------

    def _apply_folder(self, usage, label, hint, button):
        """
        Eine der beiden Zeilen aus dem Bericht zeichnen.

        Gezählt und formuliert wird in `core/storage_usage.py` - hier
        wird nur gezeichnet. Zwei Zählweisen für dieselbe Zahl wären
        genau die Doppelung, an der Meldung und Seite verschiedene
        Zahlen nennen.
        """

        label.setText(storage_usage.folder_text(usage))

        text = storage_usage.folder_hint(usage)

        hint.setText(text)

        hint.setVisible(bool(text))

        if text:

            #
            # Der aufgehellte Warnton aus der Tokentabelle, nicht der
            # Akzent: der Hinweis beschreibt einen Zustand und folgt
            # deshalb keiner Akzentwahl.
            #

            hint.setStyleSheet(
                f"font-size:12px;color:{tokens.STATE_TEXT['warn']};"
            )

        button.setEnabled(usage.count > 0)

    # --------------------------------------------------

    def refresh(self):

        report = storage_usage.scan(
            Paths.downloads(),
            Paths.backups(),
        )

        self._apply_folder(
            report.downloads,
            self.download_label,
            self.download_hint,
            self.clear_downloads,
        )

        self._apply_folder(
            report.backups,
            self.backup_label,
            self.backup_hint,
            self.clear_backups,
        )

        self._apply_restore()

    # --------------------------------------------------

    def _apply_restore(self):
        """
        Was der Rückweg gerade anbieten kann.

        Drei Fälle, drei Sätze - und keiner davon behauptet etwas, was
        nicht geprüft wurde: gar kein Backup, ein Backup aus einer
        Fassung vor 2.7.1 (die sicherten nur den Addon-Ordner), oder
        ein Backup mit Spielstand samt seinem Datum.
        """

        self._restore_source = None

        backup = self.manager.backup.newest_with_saved_variables()

        if backup is None:

            self.restore_label.setText(
                "In keinem vorhandenen Backup liegt ein Spielstand"
            )

            self.restore_hint.setText(
                "Backups vor Fassung 2.7.1 sicherten nur den "
                "Addon-Ordner. Das nächste Update legt einen an."
            )

            self.restore_hint.setStyleSheet(
                f"font-size:12px;color:{Colors.TEXT_MUTED};"
            )

            self.restore_hint.setVisible(True)

            self.restore_button.setEnabled(False)

            return

        self._restore_source = backup

        self.restore_label.setText(
            f"Gesichert am {backup_time_text(backup)}"
        )

        self.restore_hint.setText(
            "Holt Bossnotizen, Twinkliste und Fortschritt aus diesem "
            "Backup zurück. World of Warcraft muss dafür geschlossen "
            "sein - es überschreibt seine Daten beim Abmelden."
        )

        self.restore_hint.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
        )

        self.restore_hint.setVisible(True)

        self.restore_button.setEnabled(
            self.manager.state.wow_path is not None
        )

    # --------------------------------------------------

    def _note_changed(self):
        """
        Nach dem Aufräumen sofort neu zählen lassen.

        Ohne das stünde die Meldung ("hier sammelt sich etwas an")
        noch bis zu fünf Minuten weiter im Raum, obwohl der Ordner
        schon leer ist - und der Merker in `MainWindow`, der das
        nächste Volllaufen wieder melden soll, würde nie zurückgesetzt.
        """

        watch = getattr(self.manager, "storage_watch", None)

        if watch is not None:
            watch.refresh()

    # --------------------------------------------------

    def _clear_folder(self, directory, question_title, question_text, log_word):

        answer = QMessageBox.question(
            self,
            question_title,
            question_text,
        )

        if answer != QMessageBox.Yes:
            return

        count = 0

        if directory.exists():

            for file in directory.iterdir():

                if file.is_file():

                    file.unlink()

                    count += 1

        self.manager.logger.success(
            f"{count} {log_word} gelöscht."
        )

        self._note_changed()

        self.refresh()

    # --------------------------------------------------

    def clear_download_cache(self):

        self._clear_folder(
            Paths.downloads(),
            "Downloads löschen",
            "Alle heruntergeladenen Dateien wirklich löschen?",
            "Download(s)",
        )

    def clear_backups_folder(self):

        self._clear_folder(
            Paths.backups(),
            "Backups löschen",
            "Alle Backups wirklich löschen?",
            "Backup(s)",
        )

    # --------------------------------------------------

    def restore_saved_variables(self):
        """
        Den Spielstand aus dem jüngsten Backup zurückschreiben.

        Die Rückfrage nennt das Datum: "Spielstand wiederherstellen"
        allein sagt nicht, wie weit man dabei zurückgeht, und genau
        das ist die Entscheidung. Die vorhandenen Dateien werden
        beiseitegelegt statt gelöscht (siehe `core/backup.py`), damit
        auch dieser Schritt einen Rückweg hat.
        """

        backup = getattr(self, "_restore_source", None)

        wow_path = self.manager.state.wow_path

        if backup is None or wow_path is None:
            return

        answer = QMessageBox.question(
            self,
            "Spielstand zurückholen",
            "Den Spielstand von WeintCodex auf den Stand vom "
            f"{backup_time_text(backup)} zurücksetzen?\n\n"
            "Alles, was seitdem im Spiel dazugekommen ist, wird "
            "dadurch ersetzt. World of Warcraft muss geschlossen "
            "sein.\n\n"
            "Die jetzigen Dateien bleiben daneben liegen und lassen "
            "sich von Hand zurückholen.",
        )

        if answer != QMessageBox.Yes:
            return

        try:

            written = self.manager.backup.restore_saved_variables(
                backup,
                wow_path,
            )

        except Exception as exc:

            self.manager.logger.error(
                f"Spielstand konnte nicht zurückgeholt werden: {exc}"
            )

            return

        if not written:

            self.manager.logger.warning(
                "In diesem Backup liegt kein Spielstand."
            )

            return

        self.manager.logger.success(
            f"Spielstand aus dem Backup vom {backup_time_text(backup)} "
            f"zurückgeholt ({len(written)} Datei(en)). "
            "Beim nächsten Anmelden in WoW ist er wieder da."
        )

        self.refresh()
