from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.status_card import StatusCard
from core.platform import open_folder


class AddonPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        # --------------------------------------------------
        # Titel
        # --------------------------------------------------

        title = QLabel("Addonverwaltung")
        title.setObjectName("title")
        layout.addWidget(title)

        # --------------------------------------------------
        # Installierte Version
        # --------------------------------------------------

        self.installed_card = StatusCard(
            icon="📦",
            title="Installierte Version",
            status="-",
            details="-",
        )

        layout.addWidget(self.installed_card)

        # --------------------------------------------------
        # GitHub
        # --------------------------------------------------

        self.github_card = StatusCard(
            icon="🌐",
            title="GitHub Release",
            status="-",
            details="-",
        )

        layout.addWidget(self.github_card)

        # --------------------------------------------------
        # Installationsordner
        # --------------------------------------------------

        self.path_card = StatusCard(
            icon="📂",
            title="Installationsordner",
            status="-",
            details="-",
            button_text="Ordner öffnen",
        )

        layout.addWidget(self.path_card)

        # --------------------------------------------------
        # Aktionen
        # --------------------------------------------------

        self.check_button = QPushButton("🔄 Erneut prüfen")
        self.update_button = QPushButton("⬇ Addon installieren")

        layout.addWidget(self.check_button)
        layout.addWidget(self.update_button)

        # --------------------------------------------------
        # Changelog
        # --------------------------------------------------

        changelog_title = QLabel("Changelog")
        changelog_title.setObjectName("cardTitle")
        layout.addWidget(changelog_title)

        self.changelog = QTextEdit()
        self.changelog.setReadOnly(True)

        layout.addWidget(self.changelog)

        #
        # Installationsprotokoll
        #

        log_title = QLabel("Installationsprotokoll")
        log_title.setObjectName("cardTitle")

        layout.addWidget(log_title)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addWidget(self.log)

        layout.addStretch()

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

            self.installed_card.set_details(
                f"Version {state.addon_version}"
            )

            self.path_card.set_status(
                "🟢 Gefunden"
            )

            self.path_card.set_details(
                str(state.addon_path)
            )

        else:

            self.installed_card.set_status(
                "🔴 Nicht installiert"
            )

            self.installed_card.set_details("-")

            self.path_card.set_status(
                "🔴 Nicht gefunden"
            )

            self.path_card.set_details("-")

        #
        # GitHub
        #

        if state.github_version != "-":

            if state.update_available:

                self.github_card.set_status(
                    "🟡 Update verfügbar"
                )

            else:

                self.github_card.set_status(
                    "🟢 Aktuell"
                )

            self.github_card.set_details(
                f"Version {state.github_version}"
            )

            self.changelog.setPlainText(
                state.github_changelog
            )

        else:

            self.github_card.set_status(
                "⚪ Nicht geprüft"
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