from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton

from ._common import SectionContent


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

        self.addRow(card, divider=False)

        self.change_button.clicked.connect(self.choose_folder)

        self.refresh()

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
