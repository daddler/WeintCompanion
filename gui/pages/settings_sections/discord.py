import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton

from ._common import SectionContent


class _DiscordLoginBridge(QObject):
    """
    Meldet das Ergebnis des Discord-Logins thread-sicher an den
    Hauptthread zurück (der Login blockiert im Hintergrund-Thread).
    """

    finished = Signal(object, object)  # (result_dict | None, error_str | None)


class DiscordSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · DISCORD",
            "Discord",
            "Verknüpfe deinen Discord-Account für den Raid-Roster-Export.",
        )

        self.manager = manager

        self._bridge = _DiscordLoginBridge(self)

        self._bridge.finished.connect(
            self._on_login_finished
        )

        card = QWidget()

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(0, 0, 0, 0)

        card_layout.setSpacing(10)

        self.status_label = QLabel("Nicht verbunden")

        self.status_label.setStyleSheet(
            f"font-size:14px;font-weight:700;color:{Colors.ERROR};"
        )

        card_layout.addWidget(self.status_label)

        self.hint_label = QLabel("")

        self.hint_label.setWordWrap(True)

        self.hint_label.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
        )

        card_layout.addWidget(self.hint_label)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.unlink_button = HeroButton(
            "Trennen",
            primary=False,
        )

        self.login_button = HeroButton(
            "Mit Discord verbinden",
            primary=True,
        )

        button_row.addWidget(self.unlink_button)
        button_row.addWidget(self.login_button)

        card_layout.addLayout(button_row)

        self.addRow(card, divider=False)

        self.login_button.clicked.connect(self.start_login)
        self.unlink_button.clicked.connect(self.unlink)

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        account = self.manager.discord_account.load()

        #
        # Ohne diese Zeile bliebe der Button nach jedem refresh()
        # (Login-Abschluss oder "Trennen") dauerhaft deaktiviert.
        #

        self.login_button.setEnabled(True)

        if account:

            self.status_label.setText(
                f"Verbunden als {account.get('username', '?')}"
            )

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.SUCCESS};"
            )

            if account.get("authorized"):

                self.hint_label.setText(
                    "Dein Account darf den Raid-Roster automatisch "
                    "abrufen - Companion übergibt neue Anmeldungen "
                    "automatisch ans Addon."
                )

            else:

                self.hint_label.setText(
                    "Verbunden, aber dieser Account darf den "
                    "Raid-Roster nicht abrufen (fehlende Rolle). "
                    "Wende dich an einen Raidlead/Officer."
                )

            self.login_button.setText("Erneut verbinden")

            self.unlink_button.setEnabled(True)

        else:

            self.status_label.setText("Nicht verbunden")

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.ERROR};"
            )

            self.hint_label.setText(
                "Verknüpfe deinen Discord-Account, damit Companion "
                "deinen Raid-Roster automatisch ans Addon übergeben kann."
            )

            self.login_button.setText("Mit Discord verbinden")

            self.unlink_button.setEnabled(False)

    # --------------------------------------------------
    # Discord-Login
    # --------------------------------------------------
    # Der Login blockiert (öffnet den Browser, wartet auf den lokalen
    # Redirect, tauscht den Code beim Bot aus) - läuft deshalb in
    # einem Hintergrund-Thread, damit die UI währenddessen nicht
    # einfriert.

    def start_login(self):

        self.login_button.setEnabled(False)
        self.unlink_button.setEnabled(False)

        self.status_label.setText(
            "Browser öffnet sich - bitte Discord-Login abschließen..."
        )

        thread = threading.Thread(
            target=self._login_worker,
            daemon=True,
            name="DiscordLoginThread",
        )

        thread.start()

    def _login_worker(self):

        try:

            result = self.manager.discord_auth.login()

        except Exception as exc:

            self._bridge.finished.emit(None, str(exc))

            return

        self._bridge.finished.emit(result, None)

    def _on_login_finished(self, result, error):

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

    def unlink(self):

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
