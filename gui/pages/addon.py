from PySide6.QtWidgets import (
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGridLayout,
)
from gui.widgets.hero_banner import HeroButton
from gui.widgets.status_card import StatusCard
from core.platform import open_folder
from gui.widgets.section_card import SectionCard

from core.resources import Resources

class AddonPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        # --------------------------------------------------
        # Titel
        # --------------------------------------------------

        title = QLabel("📦 Software")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Installiere, aktualisiere und verwalte Weintcompanion und WeintCodex."
        )

        subtitle.setStyleSheet("""
        QLabel{
            color:#AEB4C2;
            font-size:14px;
            background:transparent;
        }
        """)

        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # --------------------------------------------------
        # Statuskarten
        # --------------------------------------------------

        self.installed_card = StatusCard(
            icon=Resources.software(),
            title="WeintCodex",
            status="-",
            details="-",
        )

        self.companion_card = StatusCard(
            icon=Resources.companion(),
            title="WeintCompanion",
            status="-",
            details="-",
        )

        self.github_card = StatusCard(
            icon=Resources.github(),
            title="GitHub",
            status="-",
            details="-",
        )

        self.path_card = StatusCard(
            icon=Resources.folder(),
            title="Addon-Ordner",
            status="-",
            details="-",
            button_text="Ordner öffnen",
        )

        self.path_card.set_value("")

        cards = QGridLayout()

        cards.setHorizontalSpacing(18)
        cards.setVerticalSpacing(18)

        cards.addWidget(self.installed_card, 0, 0)
        cards.addWidget(self.companion_card, 0, 1)
        cards.addWidget(self.github_card, 0, 2)
        cards.addWidget(self.path_card, 0, 3)

        for column in range(4):
            cards.setColumnStretch(column, 1)

        layout.addLayout(cards)

        # --------------------------------------------------
        # Aktionen
        # --------------------------------------------------

        self.check_button = HeroButton(
            "Erneut prüfen",
            primary=False,
        )

        self.update_button = HeroButton(
            "Addon installieren",
            primary=True,
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(14)

        button_row.addWidget(self.check_button)
        button_row.addWidget(self.update_button)
        button_row.addStretch()

        layout.addLayout(button_row)

        # --------------------------------------------------
        # Changelog
        # --------------------------------------------------

        self.changelog = QTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setMinimumHeight(130)

        self.changelog.setStyleSheet("""
        QTextEdit{
            background:transparent;
            border:none;
            color:#D7DBE3;
            padding:0px;
            font-size:13px;
        }
        """)

        changelog_card = SectionCard(
            Resources.changelog(),
            "Changelog",
        )

        changelog_card.addWidget(
            self.changelog
        )

        # --------------------------------------------------
        # Installationsprotokoll
        # --------------------------------------------------

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(130)

        self.log.setStyleSheet("""
        QTextEdit{
            background:transparent;
            border:none;
            color:#D7DBE3;
            padding:0px;
            font-size:13px;
        }
        """)

        log_card = SectionCard(
            Resources.logs(),
            "Installationsprotokoll",
        )

        log_card.addWidget(
            self.log
        )

        # --------------------------------------------------
        # Changelog + Log nebeneinander
        # --------------------------------------------------

        logs = QGridLayout()

        logs.setHorizontalSpacing(18)
        logs.setVerticalSpacing(0)

        logs.addWidget(
            changelog_card,
            0,
            0,
        )

        logs.addWidget(
            log_card,
            0,
            1,
        )

        logs.setColumnStretch(0, 1)
        logs.setColumnStretch(1, 1)

        layout.addLayout(logs)

        # --------------------------------------------------
        # Signale
        # --------------------------------------------------

        self.check_button.clicked.connect(
            self.check_updates
        )

        self.update_button.clicked.connect(
            self.install_or_update
        )

        self.path_card.get_button().clicked.connect(
            self.open_addon_folder
        )

        self.refresh()

    # --------------------------------------------------
    # Oberfläche aktualisieren
    # --------------------------------------------------

    def refresh(self):

        state = self.manager.state

        #
        # Installierte Version
        #

        if state.addon_found:

            self.installed_card.set_status(
                "🟢 Installiert"
            )

            self.installed_card.set_value(
                state.addon_version
            )

            self.installed_card.set_details(
                "Version installiert"
            )

            self.path_card.set_status(
                "🟢 Gefunden"
            )

            self.path_card.set_details(
                str(state.addon_path)
            )

        else:

            self.installed_card.set_state("error")
            self.installed_card.set_status(
                "🔴 Nicht installiert"
            )

            self.installed_card.set_value("-")

            self.installed_card.set_details(
                "Nicht installiert"
            )

            self.path_card.set_state("error")
            self.path_card.set_status(
                "🔴 Nicht gefunden"
            )

            self.path_card.set_details("-")

        #
        # WeintCompanion
        #

        if state.companion_update_available:

            self.companion_card.set_state("warning")

            self.companion_card.set_status(
                "🟡 Update verfügbar"
            )

        else:

            self.companion_card.set_state("normal")

            self.companion_card.set_status(
                "🟢 Installiert"
            )

        self.companion_card.set_value(
            state.companion_version
        )

        self.companion_card.set_details(
            "Version installiert"
        )

        #
        # GitHub
        #

        if state.github_version != "-":

            if state.update_available:

                self.github_card.set_state("warning")

                self.github_card.set_status(
                    "🟡 Update verfügbar"
                )

            else:

                self.github_card.set_state("normal")

                self.github_card.set_status(
                    "🟢 Aktuell"
                )

            self.github_card.set_value(
                state.github_version
            )

            self.github_card.set_details(
                "Neueste GitHub-Version"
            )

            self.changelog.setPlainText(
                state.github_changelog
            )

        else:

            self.github_card.set_state("error")

            self.github_card.set_status(
                "🔴 GitHub nicht erreichbar"
            )
            self.github_card.set_value(
                state.github_version
            )

            self.github_card.set_details(
                "Neueste GitHub-Version"
            )

            self.github_card.set_details("-")

            self.changelog.clear()

        #
        # Installieren / Aktualisieren
        #

        if not state.addon_found:

            self.update_button.setText(
                "⬇ Addon installieren"
            )

            self.update_button.setEnabled(True)

        elif state.update_available:

            self.update_button.setText(
                "⬇ Addon aktualisieren"
            )

            self.update_button.setEnabled(True)

        else:

            self.update_button.setText(
                "✓ Addon aktuell"
            )

            self.update_button.setEnabled(False)

    # --------------------------------------------------
    # Log
    # --------------------------------------------------

    def add_log(self, text):

        self.log.append(text)

    # --------------------------------------------------
    # GitHub erneut prüfen
    # --------------------------------------------------

    def check_updates(self):

        self.add_log("Prüfe GitHub auf neue Versionen...")

        self.manager.refresh()

        self.refresh()

        self.add_log("GitHub erfolgreich geprüft.")

    # --------------------------------------------------
    # Installation / Update
    # --------------------------------------------------

    def install_or_update(self):

        try:

            state = self.manager.state

            if state.addon_found:

                self.add_log(
                    "Starte Addon-Aktualisierung..."
                )

            else:

                self.add_log(
                    "Starte Addon-Installation..."
                )

            self.manager.install_or_update()

            self.refresh()

            if state.addon_found:

                self.add_log(
                    "Addon erfolgreich aktualisiert."
                )

            else:

                self.add_log(
                    "Addon erfolgreich installiert."
                )

        except Exception as e:

            self.add_log(
                f"Fehler: {e}"
            )

            print(e)

    # --------------------------------------------------
    # Ordner öffnen
    # --------------------------------------------------

    def open_addon_folder(self):

        state = self.manager.state

        if not state.addon_found:
            return

        open_folder(state.addon_path)