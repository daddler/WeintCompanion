from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.platform import is_linux
from core.wow_clients import all_clients
from core.wow_folder import check_client_folder
from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.status_dot import StatusDot

from ._common import SectionContent


LINUX_LAUNCHER_PLACEHOLDERS = {

    "custom": "Vollständiger Start-Befehl, z. B. für Bottles/Heroic",
    "lutris": "Lutris-Spiel-Slug, z. B. battlenet",
    "steam": "Steam App-ID, z. B. 123456789",
    "faugus": "Faugus Game-ID, z. B. battlenet",

}


class WowClientSection(SectionContent):
    """
    Spielversion **und** Pfad - in dieser Reihenfolge, weil die zweite
    Frage von der ersten abhängt: welcher Ordner gültig ist, steht in
    der Spielversion (`core/wow_clients.py`).

    Jede Version behält ihren eigenen Pfad (`config.wow_paths`). Ein
    Wechsel hin und zurück verliert deshalb nichts - das ist der
    ganze Grund, warum der Umschalter hier steht und nicht nur ein
    zweiter Ordnerknopf.
    """

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · WOW-CLIENT",
            "World of Warcraft",
            "Spielversion und Pfad zu deiner Installation.",
        )

        self.manager = manager

        #
        # --------------------------------------------------
        # Spielversion
        # --------------------------------------------------
        #

        version_card = QWidget()

        version_layout = QVBoxLayout(version_card)

        version_layout.setContentsMargins(0, 0, 0, 0)

        version_layout.setSpacing(10)

        version_title = QLabel("Spielversion")

        version_title.setStyleSheet(
            f"font-size:14px;font-weight:700;color:{Colors.WHITE};"
        )

        version_layout.addWidget(version_title)

        self.client_control = SegmentedControl([
            (entry.short_name, entry.id)
            for entry in all_clients()
        ])

        self.client_control.valueChanged.connect(
            self._on_client_changed
        )

        version_layout.addWidget(self.client_control)

        self.client_hint = QLabel("")

        self.client_hint.setWordWrap(True)

        self.client_hint.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        version_layout.addWidget(self.client_hint)

        self.addRow(version_card)

        #
        # --------------------------------------------------
        # Installationsordner
        # --------------------------------------------------
        #

        card = QWidget()

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(0, 0, 0, 0)

        card_layout.setSpacing(10)

        self.status_label = QLabel("-")

        self.status_label.setStyleSheet(
            f"font-size:14px;font-weight:700;color:{Colors.SUCCESS};"
        )

        card_layout.addWidget(self.status_label)

        self.path_label = QLabel("-")

        self.path_label.setWordWrap(True)

        self.path_label.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
        )

        card_layout.addWidget(self.path_label)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.change_button = HeroButton(
            "Ordner auswählen",
            primary=False,
        )

        button_row.addWidget(self.change_button)

        card_layout.addLayout(button_row)

        self.addRow(card, divider=not is_linux())

        self.change_button.clicked.connect(self.choose_folder)

        #
        # --------------------------------------------------
        # Battle.net-Start (nur unter Linux relevant - unter
        # Windows wird Battle.net.exe automatisch neben dem
        # WoW-Ordner gefunden und gestartet)
        # --------------------------------------------------
        #

        self.linux_card = None

        if is_linux():

            self._build_linux_launch_card()

        self.refresh()

    # --------------------------------------------------

    def _build_linux_launch_card(self):

        self.linux_card = QWidget()

        layout = QVBoxLayout(self.linux_card)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Battle.net-Start")

        title.setStyleSheet(
            f"font-size:14px;font-weight:700;color:{Colors.WHITE};"
        )

        layout.addWidget(title)

        description = QLabel(
            "Unter Linux gibt es kein einheitliches Battle.net - "
            "hinterlege, wie dein Launcher (Lutris, Steam, Faugus, "
            "Bottles, ...) gestartet wird. Die Faugus Game-ID findest "
            "du in ~/.local/share/faugus-launcher/games.json oder am "
            "Namen des WINEPREFIX-Ordners unter ~/Faugus/."
        )

        description.setWordWrap(True)

        description.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(description)

        self.launcher_type_control = SegmentedControl([

            ("Eigener Befehl", "custom"),
            ("Lutris", "lutris"),
            ("Steam", "steam"),
            ("Faugus", "faugus"),

        ])

        self.launcher_type_control.valueChanged.connect(
            self._on_launcher_type_changed
        )

        layout.addWidget(self.launcher_type_control)

        self.launcher_value_input = QLineEdit()

        self.launcher_value_input.editingFinished.connect(
            self._save_linux_launcher
        )

        layout.addWidget(self.launcher_value_input)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.save_launcher_button = HeroButton(
            "Speichern",
            primary=False,
        )

        self.save_launcher_button.clicked.connect(
            self._save_linux_launcher
        )

        button_row.addWidget(self.save_launcher_button)

        layout.addLayout(button_row)

        #
        # Die Bestaetigung trug bis 1.7 einen Haken als Textzeichen
        # ("\u2713"). Das ist genau die Bauart, die 2.0 abschafft: das
        # Zeichen fehlt in der beigelegten Schrift, kaeme also aus
        # irgendeiner Systemschrift, und es traegt eine Bedeutung
        # ("hat geklappt"), die zu einem StatusDot gehoert.
        #

        saved_row = QHBoxLayout()

        saved_row.setContentsMargins(0, 0, 0, 0)

        saved_row.setSpacing(8)

        saved_row.addStretch(1)

        self.saved_dot = StatusDot("ok")

        saved_row.addWidget(self.saved_dot)

        self.saved_label = QLabel("")

        self.saved_label.setStyleSheet(
            f"font-size:12px;font-weight:600;color:{Colors.SUCCESS_LIGHT};"
        )

        saved_row.addWidget(self.saved_label)

        self.saved_row_widget = QWidget()

        self.saved_row_widget.setLayout(saved_row)

        self.saved_row_widget.hide()

        layout.addWidget(self.saved_row_widget)

        self.addRow(self.linux_card, divider=False)

    # --------------------------------------------------

    def refresh(self):

        config = self.manager.config

        client = config.get_wow_client()

        #
        # blockSignals: `setValue()` löst `valueChanged` aus, und der
        # Slot schriebe die Version zurück und liesse den Manager neu
        # laden - aus einem Zeichnen würde ein Schreibvorgang (siehe
        # docs/architecture/navigation.md).
        #

        self.client_control.blockSignals(True)
        self.client_control.setValue(client.id)
        self.client_control.blockSignals(False)

        self.client_hint.setText(client.hint)

        self.client_hint.setVisible(bool(client.hint))

        path = config.get_wow_path()

        if path:

            self.status_label.setText(
                f"{client.short_name} gefunden"
            )

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.SUCCESS};"
            )

            self.path_label.setText(str(path))

        else:

            self.status_label.setText(
                f"Kein Pfad für {client.short_name} ausgewählt"
            )

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.ERROR};"
            )

            self.path_label.setText(
                f"Bitte wähle den Ordner deiner Installation von "
                f"{client.name} aus."
            )

        if self.linux_card is not None:

            launcher_type = self.manager.config.get_linux_launcher_type()

            self.launcher_type_control.blockSignals(True)
            self.launcher_type_control.setValue(launcher_type)
            self.launcher_type_control.blockSignals(False)

            self.launcher_value_input.setText(
                self.manager.config.get_linux_launcher_value()
            )

            self.launcher_value_input.setPlaceholderText(
                LINUX_LAUNCHER_PLACEHOLDERS.get(
                    launcher_type,
                    "",
                )
            )

    # --------------------------------------------------

    def _on_launcher_type_changed(self, launcher_type):

        self.launcher_value_input.setPlaceholderText(
            LINUX_LAUNCHER_PLACEHOLDERS.get(
                launcher_type,
                "",
            )
        )

    def _save_linux_launcher(self):

        self.manager.config.set_linux_launcher(
            self.launcher_type_control.value(),
            self.launcher_value_input.text(),
        )

        self.manager.logger.success(
            "Battle.net-Start-Konfiguration gespeichert."
        )

        self.saved_label.setText("Einstellungen gespeichert")

        self.saved_row_widget.show()

        QTimer.singleShot(
            3000,
            self.saved_row_widget.hide,
        )

    # --------------------------------------------------

    def _on_client_changed(self, client_id):
        """
        Der Wechsel der Spielversion.

        Er holt nichts nach: der hinterlegte Pfad der neuen Version
        (falls es ihn gibt) steht in der Konfiguration, und
        `manager.refresh()` zieht Addon-Stand und Synchronisation
        nach. Was er **nicht** tut, ist den Ordner der neuen Version
        suchen - das erledigt `CompanionManager.detect_wow()` von
        selbst, sobald keiner hinterlegt ist.
        """

        config = self.manager.config

        if client_id == config.get_wow_client_id():
            return

        config.set_wow_client(client_id)

        client = config.get_wow_client()

        self.manager.refresh()

        self.manager.logger.info(
            f"Spielversion gewechselt: {client.name}"
        )

        self.refresh()

    # --------------------------------------------------

    def choose_folder(self):

        client = self.manager.config.get_wow_client()

        folder = QFileDialog.getExistingDirectory(
            self,
            f"{client.name} auswählen",
        )

        if not folder:
            return

        check = check_client_folder(folder, client)

        if not check.ok:

            #
            # Die Begründung kommt aus der Prüfung selbst - sie kennt
            # den Unterschied zwischen "da ist gar nichts", "da liegt
            # eine andere Spielversion" und "da liegen mehrere".
            #

            QMessageBox.warning(
                self,
                "Ungültiger Ordner",
                check.reason,
            )

            return

        self.manager.config.set_wow_path(check.path)

        self.manager.refresh()

        self.manager.logger.success(
            f"Pfad für {client.short_name} geändert: {check.path}"
        )

        self.refresh()
