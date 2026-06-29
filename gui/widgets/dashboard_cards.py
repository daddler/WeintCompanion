from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QWidget,
)

from gui.widgets.status_card import StatusCard


class DashboardCards(QWidget):

    folderRequested = Signal()

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QGridLayout(self)

        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(20)

        #
        # WoW
        #

        self.wow = StatusCard(
            "🎮",
            "World of Warcraft",
            "Nicht gefunden",
            "Pfad: -",
            "📂 Ordner auswählen",
        )

        self.wow.get_button().clicked.connect(
            self.folderRequested.emit
        )

        #
        # WeintCodex
        #

        self.addon = StatusCard(
            "📦",
            "WeintCodex",
            "Nicht installiert",
            "Version: -",
        )

        #
        # GitHub
        #

        self.github = StatusCard(
            "🔄",
            "Updates",
            "Nicht geprüft",
            "-",
        )

        #
        # Backups
        #

        self.backup = StatusCard(
            "💾",
            "Backups",
            "Keine Informationen",
            "-",
        )

        layout.addWidget(self.wow, 0, 0)
        layout.addWidget(self.addon, 0, 1)
        layout.addWidget(self.github, 1, 0)
        layout.addWidget(self.backup, 1, 1)

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        self.refresh_wow()
        self.refresh_addon()
        self.refresh_github()
        self.refresh_backup()

    # --------------------------------------------------

    def refresh_wow(self):

        state = self.manager.state

        if state.wow_found:

            self.wow.set_status(
                "🟢 Installation gefunden"
            )

            parts = state.wow_path.parts

            if len(parts) >= 3:
                short = "/".join(parts[-3:])
            else:
                short = str(state.wow_path)

            self.wow.set_details(short)
            self.wow.set_tooltip(str(state.wow_path))

        else:

            self.wow.set_status(
                "🔴 Nicht gefunden"
            )

            self.wow.set_details(
                "Bitte den MoP-Classic-Ordner auswählen."
            )

    # --------------------------------------------------

    def refresh_addon(self):

        state = self.manager.state

        if state.addon_found:

            self.addon.set_status(
                "🟢 Installiert"
            )

            self.addon.set_details(
                f"Version {state.addon_version}"
            )

        else:

            self.addon.set_status(
                "🔴 Nicht installiert"
            )

            self.addon.set_details(
                "Das Addon wurde nicht gefunden."
            )

    # --------------------------------------------------

    def refresh_github(self):

        state = self.manager.state

        #
        # GitHub nicht erreichbar
        #

        if (
            state.github_version == "-"
            and
            state.companion_latest_version == "-"
        ):

            self.github.set_status(
                "⚪ GitHub nicht erreichbar"
            )

            self.github.set_details("-")

            return

        #
        # Verfügbare Updates sammeln
        #

        updates = []

        if state.companion_update_available:

            updates.append(
                f"🖥 Companion → {state.companion_latest_version}"
            )

        if state.update_available:

            updates.append(
                f"📦 WeintCodex → {state.github_version}"
            )

        #
        # Updates vorhanden
        #

        if updates:

            count = len(updates)

            if count == 1:

                self.github.set_status(
                    "🟡 1 Update verfügbar"
                )

            else:

                self.github.set_status(
                    f"🟡 {count} Updates verfügbar"
                )

            self.github.set_details(
                "\n".join(updates)
            )

            return

        #
        # Alles aktuell
        #

        self.github.set_status(
            "🟢 Alles aktuell"
        )

        self.github.set_details(
            "\n".join([
                f"🖥 Companion ✓ {state.companion_version}",
                f"📦 WeintCodex ✓ {state.github_version}",
            ])
        )

    # --------------------------------------------------

    def refresh_backup(self):

        backup_dir = Path("cache/backups")

        if not backup_dir.exists():

            self.backup.set_status(
                "⚪ Keine Backups"
            )

            self.backup.set_details("-")

            return

        backups = list(backup_dir.iterdir())

        if not backups:

            self.backup.set_status(
                "⚪ Keine Backups"
            )

            self.backup.set_details("-")

            return

        newest = max(
            backups,
            key=lambda p: p.stat().st_mtime,
        )

        self.backup.set_status(
            f"🟢 {len(backups)} vorhanden"
        )

        self.backup.set_details(
            newest.name
        )