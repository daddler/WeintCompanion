from pathlib import Path

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
from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl

from ._common import SectionContent


LINUX_LAUNCHER_PLACEHOLDERS = {

    "custom": "z. B. faugus-launcher --start \"Battle.net\"",
    "lutris": "Lutris-Spiel-Slug, z. B. battlenet",
    "steam": "Steam App-ID, z. B. 123456789",

}


class WowClientSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · WOW-CLIENT",
            "World of Warcraft",
            "Pfad zu deiner MoP-Classic-Installation.",
        )

        self.manager = manager

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
            "Classic-Ordner auswählen",
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
            "Bottles, ...) gestartet wird."
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

        self.addRow(self.linux_card, divider=False)

    # --------------------------------------------------

    def refresh(self):

        path = self.manager.config.get_classic_path()

        if path:

            self.status_label.setText("Classic gefunden")

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.SUCCESS};"
            )

            self.path_label.setText(str(path))

        else:

            self.status_label.setText("Kein Classic-Pfad ausgewählt")

            self.status_label.setStyleSheet(
                f"font-size:14px;font-weight:700;color:{Colors.ERROR};"
            )

            self.path_label.setText(
                "Bitte wähle deinen World of Warcraft Classic-Ordner aus."
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
            and (folder / "_classic_").exists()
        ):
            folder = folder / "_classic_"

        if not (
            (folder / "Interface").exists()
            and (folder / "Interface" / "AddOns").exists()
            and (folder / "WTF").exists()
        ):

            QMessageBox.warning(
                self,
                "Ungültiger Ordner",
                "Dies ist kein gültiger MoP-Classic-Ordner.",
            )

            return

        self.manager.config.set_classic_path(folder)

        self.manager.refresh()

        self.manager.logger.success(
            f"Classic-Pfad geändert: {folder}"
        )

        self.refresh()
