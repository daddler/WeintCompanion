import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.backend_config import (
    BOT_BASE_URL,
    BOT_URL_ENV,
    DEFAULT_BOT_BASE_URL,
    bot_url_override_path,
    bot_url_source,
    normalize_bot_url,
    write_bot_url_override,
)
from core.discord_account import is_usable
from core.net_errors import bot_unreachable_text

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton

from ._common import SectionContent


class _DiscordLoginBridge(QObject):
    """
    Meldet das Ergebnis des Discord-Logins thread-sicher an den
    Hauptthread zurück (der Login blockiert im Hintergrund-Thread).
    """

    finished = Signal(object, object)  # (result_dict | None, error_str | None)


class _BotProbeBridge(QObject):
    """
    Meldet das Ergebnis der Erreichbarkeitsprüfung zurück in den
    Hauptthread - derselbe Weg wie beim Login, aus demselben Grund:
    ein Netzabruf im Klick-Handler friert das Fenster ein.
    """

    finished = Signal(str, bool, str)  # (adresse, erreichbar, meldung)


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

        self.addRow(card)

        self.addRow(self._build_address_row(), divider=False)

        self.login_button.clicked.connect(self.start_login)
        self.unlink_button.clicked.connect(self.unlink)

        self.refresh()

    # --------------------------------------------------
    # Adresse des Bots
    # --------------------------------------------------
    # Warum das hier bedienbar ist und nicht nur in einer Datei:
    # der Bot liegt bei einem Anbieter, der den Rechner in den
    # Hostnamen schreibt (siehe core/backend_config.py). Zieht er um,
    # verschwindet der alte Name aus dem DNS, und ab diesem Moment
    # scheitert jeder Abruf mit "Der Name oder der Dienst ist nicht
    # bekannt" - die Anmeldung eingeschlossen. Der Ausweg gibt es
    # seit 2.0.12, aber er führte über eine von Hand angelegte Datei
    # in einem Verzeichnis, das niemand auswendig kennt. Ein Ausweg,
    # den man erst finden muss, ist im Ernstfall keiner.

    def _build_address_row(self) -> QWidget:

        self._probe = _BotProbeBridge(self)

        self._probe.finished.connect(self._on_probe_finished)

        row = QWidget()

        layout = QVBoxLayout(row)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(10)

        label = QLabel("Adresse des Bots")

        label.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        layout.addWidget(label)

        description = QLabel(
            "Nur ändern, wenn der Bot umgezogen ist - dann meldet "
            "die App, seine Adresse liesse sich nicht auflösen. Leer "
            "lassen für die eingebaute Adresse. Die Änderung greift "
            "nach einem Neustart der Companion."
        )

        description.setWordWrap(True)

        description.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(description)

        self.address_input = QLineEdit()

        self.address_input.setPlaceholderText(DEFAULT_BOT_BASE_URL)

        layout.addWidget(self.address_input)

        self.address_hint = QLabel("")

        self.address_hint.setWordWrap(True)

        self.address_hint.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(self.address_hint)

        address_buttons = QHBoxLayout()

        address_buttons.addStretch()

        self.probe_button = HeroButton(
            "Erreichbarkeit prüfen",
            primary=False,
        )

        self.address_save_button = HeroButton(
            "Adresse übernehmen",
            primary=False,
        )

        address_buttons.addWidget(self.probe_button)
        address_buttons.addWidget(self.address_save_button)

        layout.addLayout(address_buttons)

        self.probe_button.clicked.connect(self.probe_address)
        self.address_save_button.clicked.connect(self.save_address)

        self._refresh_address()

        return row

    def _refresh_address(self):
        """
        Das Feld auf den gerade gültigen Stand bringen.

        Nicht Teil von `refresh()`: jenes läuft bei jedem Betreten
        des Abschnitts und bei jeder `state_changed`, und es würde
        eine halb getippte Adresse unter den Fingern des Nutzers
        überschreiben.
        """

        quelle = bot_url_source()

        self.address_input.setText(
            "" if quelle == "default" else BOT_BASE_URL
        )

        if quelle == BOT_URL_ENV:

            #
            # Die Umgebungsvariable gewinnt über die Datei. Ohne
            # diesen Hinweis änderte man hier eine Adresse, die
            # danach folgenlos bliebe - von aussen nicht von einem
            # kaputten Knopf zu unterscheiden.
            #

            self.address_input.setEnabled(False)

            self.address_save_button.setEnabled(False)

            self.address_hint.setText(
                f"Aktuell: {BOT_BASE_URL} - vorgegeben durch die "
                f"Umgebungsvariable {BOT_URL_ENV}. Solange die "
                "gesetzt ist, hat eine Eingabe hier keine Wirkung."
            )

            return

        self.address_input.setEnabled(True)

        self.address_save_button.setEnabled(True)

        if quelle == "default":

            self.address_hint.setText(
                f"Aktuell: {BOT_BASE_URL} (eingebaute Adresse)."
            )

        else:

            self.address_hint.setText(
                f"Aktuell: {BOT_BASE_URL} - hinterlegt in "
                f"{bot_url_override_path()}."
            )

    def save_address(self):

        eingabe = self.address_input.text().strip()

        try:

            gespeichert = write_bot_url_override(eingabe)

        except (ValueError, OSError) as exc:

            self.address_hint.setText(f"Nicht gespeichert: {exc}")

            return

        self.manager.logger.info(
            "Adresse des Bots geändert: "
            f"{gespeichert or DEFAULT_BOT_BASE_URL} "
            "(gilt ab dem nächsten Start)."
        )

        self.address_input.setText(gespeichert)

        self.address_hint.setText(
            f"Gespeichert: {gespeichert or DEFAULT_BOT_BASE_URL}. "
            "Bitte die Companion neu starten - erst danach benutzen "
            "Anmeldung und Abgleich die neue Adresse."
        )

    def probe_address(self):
        """
        Antwortet der Bot unter dieser Adresse überhaupt?

        Geprüft wird, was im Feld steht - nicht, was gilt: sonst
        liesse sich eine neue Adresse erst nach dem Neustart
        beurteilen, also genau dann nicht, wenn man es wissen will.
        """

        adresse = (
            normalize_bot_url(self.address_input.text())
            or BOT_BASE_URL
        )

        self.probe_button.setEnabled(False)

        self.address_hint.setText(f"Prüfe {adresse} …")

        thread = threading.Thread(
            target=self._probe_worker,
            args=(adresse, ),
            daemon=True,
            name="BotProbeThread",
        )

        thread.start()

    def _probe_worker(self, adresse: str):

        #
        # Erst hier importiert: dieser Abschnitt wird gebaut, sobald
        # jemand die Einstellungen öffnet, und soll dafür keine
        # HTTP-Bibliothek nachziehen.
        #

        import httpx

        try:

            response = httpx.get(f"{adresse}/status", timeout=8)

        except Exception as exc:

            self._probe.finished.emit(
                adresse,
                False,
                bot_unreachable_text(exc, adresse),
            )

            return

        if response.status_code >= 500:

            self._probe.finished.emit(
                adresse,
                False,
                f"{adresse} antwortet, meldet aber einen Fehler "
                f"(HTTP {response.status_code}). Der Bot läuft "
                "gerade nicht richtig.",
            )

            return

        #
        # Alles unterhalb von 500 zählt als erreichbar - auch ein
        # 404. Die Frage an dieser Stelle ist, ob dort überhaupt
        # jemand zuhört; welche Pfade er kennt, beantworten die
        # Abrufe selbst.
        #

        self._probe.finished.emit(
            adresse,
            True,
            f"{adresse} ist erreichbar (HTTP "
            f"{response.status_code}).",
        )

    def _on_probe_finished(self, adresse, erreichbar, meldung):

        self.probe_button.setEnabled(True)

        self.address_hint.setText(meldung)

        if erreichbar:
            self.manager.logger.success(meldung)
        else:
            self.manager.logger.warning(meldung.replace("\n\n", " "))

    # --------------------------------------------------

    def refresh(self):

        account = self.manager.discord_account.load()

        #
        # Ohne diese Zeile bliebe der Button nach jedem refresh()
        # (Login-Abschluss oder "Trennen") dauerhaft deaktiviert.
        #

        self.login_button.setEnabled(True)

        #
        # `is_usable()` und nicht "steht da etwas": ohne
        # Companion-Token ist nichts abrufbar, und "Verbunden als …"
        # wäre dann eine Behauptung, der kein einziger Abruf folgt.
        #

        if is_usable(account):

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

            result = self.manager.discord_auth.login(
                self.manager.logger
            )

        except Exception as exc:

            self._bridge.finished.emit(None, str(exc))

            return

        self._bridge.finished.emit(result, None)

    def _on_login_finished(self, result, error):

        #
        # Das Ablegen gehört mit in die Fehlerbehandlung. Es stand
        # vorher ungesichert im Erfolgszweig: schlug es fehl (kein
        # Schreibrecht, ein Virenscanner, der die Datei hält, eine
        # Antwort ohne Companion-Token), flog die Ausnahme mitten aus
        # einem Qt-Slot heraus, das `refresh()` darunter lief nie, und
        # auf dem Bildschirm blieb "Browser öffnet sich …" stehen.
        # Genau der Zustand, den man von aussen als "ich verbinde
        # mich, und es kommt nichts" beschreibt.
        #

        problem = error

        if not problem:

            try:

                self.manager.discord_account.save(result)

            except Exception as exc:

                problem = str(exc)

        if problem:

            self.manager.logger.error(
                f"Discord-Login fehlgeschlagen: {problem}"
            )

        elif result.get("authorized"):

            self.manager.logger.success(
                f"Discord verbunden als {result.get('username')}."
            )

        else:

            self.manager.logger.warning(
                f"Discord verbunden als {result.get('username')}, "
                "aber ohne Berechtigung für den Raid-Roster-Export."
            )

        self.refresh()

        #
        # Nach `refresh()`, denn das setzt den Hinweistext neu. Ein
        # Fehlschlag, der nur im Protokoll steht, ist an dieser Stelle
        # von "nichts passiert" nicht zu unterscheiden.
        #

        if problem:

            self.hint_label.setText(
                f"Der letzte Versuch ist fehlgeschlagen: {problem}"
            )

    # --------------------------------------------------

    def unlink(self):

        account = self.manager.discord_account.load()

        if account and account.get("companion_token"):

            self.manager.discord_auth.unlink(
                account["companion_token"]
            )

        self.manager.discord_account.clear()

        #
        # Die WeakAuras der Gilde gehören der Gilde, nicht diesem
        # Rechner. Sie nach dem Trennen weiter ins Addon zu stellen
        # wäre dieselbe Vermischung, gegen die es `/wc access reset`
        # gibt - und sie liessen sich ohne Konto auch nicht mehr
        # aktualisieren. Die selbst eingetragenen bleiben: die hat
        # niemand anderes.
        #

        store = getattr(self.manager, "weakauras", None)

        if store is not None and store.clear_guild():

            sync = getattr(self.manager, "weakaura_sync", None)

            if sync is not None:
                sync.publish_now()

        self.manager.logger.info(
            "Discord-Verknüpfung getrennt."
        )

        self.refresh()
