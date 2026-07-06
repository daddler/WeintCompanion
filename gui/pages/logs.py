from pathlib import Path
import subprocess
import sys

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.paths import Paths
from gui.widgets.log_widget import LogWidget

from core.resources import Resources
from gui.widgets.hero_banner import HeroButton
from gui.widgets.section_card import SectionCard


class LogsPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        title = QLabel("Logs")
        title.setObjectName("title")

        subtitle = QLabel(
            "Alle Aktivitäten von WeintCompanion."
        )

        subtitle.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        #
        # --------------------------------------------------
        # Toolbar
        # --------------------------------------------------
        #

        toolbar = QHBoxLayout()

        self.clear_button = HeroButton(
            "Logs leeren",
            primary=False,
        )

        self.open_button = HeroButton(
            "Logordner öffnen",
            primary=False,
        )

        toolbar.addWidget(self.clear_button)
        toolbar.addWidget(self.open_button)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        #
        # --------------------------------------------------
        # LogWidget
        # --------------------------------------------------
        #

        self.logs = LogWidget(
            self.manager.logger
        )

        card = SectionCard(
            Resources.logs(),
            "Live-Protokoll",
        )

        card.addWidget(self.logs)

        layout.addWidget(card)

        #
        # --------------------------------------------------
        # Signale
        # --------------------------------------------------
        #

        self.clear_button.clicked.connect(
            self.clear_logs
        )

        self.open_button.clicked.connect(
            self.open_log_folder
        )

    # --------------------------------------------------

    def refresh(self):

        self.logs.refresh()

    # --------------------------------------------------

    def clear_logs(self):

        self.manager.logger.clear()

        self.logs.refresh()

        self.manager.logger.info(
            "Logs wurden geleert."
        )

    # --------------------------------------------------

    def open_log_folder(self):

        folder = Paths.logs()

        if sys.platform.startswith("linux"):

            subprocess.Popen(
                ["xdg-open", str(folder)]
            )

        elif sys.platform == "win32":

            subprocess.Popen(
                ["explorer", str(folder)]
            )

        elif sys.platform == "darwin":

            subprocess.Popen(
                ["open", str(folder)]
            )