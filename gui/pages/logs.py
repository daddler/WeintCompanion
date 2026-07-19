import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.paths import Paths
from core.runtime import Runtime
from gui.theme.colors import Colors
from gui.widgets.filter_chip_bar import FilterChipBar
from gui.widgets.hero_banner import HeroButton
from gui.widgets.log_widget import LogWidget


class LogsPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        self._started_at = datetime.now()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        #
        # --------------------------------------------------
        # Kopfzeile
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        eyebrow = QLabel("LOGS · SESSION")
        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Live-Protokoll")
        title.setObjectName("title")

        title_col.addWidget(title)

        header.addLayout(title_col)

        header.addStretch()

        self.search = QLineEdit()

        self.search.setPlaceholderText("Filter…")

        self.search.setFixedWidth(200)

        header.addWidget(self.search)

        self.clear_button = HeroButton(
            "Logs leeren",
            primary=False,
        )

        header.addWidget(self.clear_button)

        self.open_button = HeroButton(
            "Logordner öffnen",
            primary=False,
        )

        header.addWidget(self.open_button)

        layout.addLayout(header)

        #
        # --------------------------------------------------
        # Filter-Chips
        # --------------------------------------------------
        #

        self.chips = FilterChipBar()

        layout.addWidget(self.chips)

        #
        # --------------------------------------------------
        # Log-Stream
        # --------------------------------------------------
        #

        self.logs = LogWidget(self.manager.logger)

        layout.addWidget(self.logs, 1)

        #
        # --------------------------------------------------
        # Footer
        # --------------------------------------------------
        #

        footer = QHBoxLayout()

        self.footer_left = QLabel("")

        self.footer_left.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        footer.addWidget(self.footer_left)

        footer.addStretch()

        self.footer_right = QLabel("")

        self.footer_right.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        footer.addWidget(self.footer_right)

        layout.addLayout(footer)

        #
        # Signale
        #

        self.search.textChanged.connect(
            self.logs.set_text_filter
        )

        self.chips.filterChanged.connect(
            self.logs.set_level_filter
        )

        self.clear_button.clicked.connect(
            self.clear_logs
        )

        self.open_button.clicked.connect(
            self.open_log_folder
        )

        self._timer = QTimer(self)

        self._timer.timeout.connect(self._update_footer)

        self._timer.start(1000)

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        self.logs.refresh()

        counts = {"success": 0, "info": 0, "warning": 0, "error": 0}

        for entry in self.manager.logger.entries():

            if entry.level in counts:
                counts[entry.level] += 1

        self.chips.setCounts(counts)

        self._update_footer()

    def _update_footer(self):

        elapsed = datetime.now() - self._started_at

        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)

        minutes = remainder // 60

        self.footer_left.setText(
            f"● Streaming    Session: {hours}h {minutes}m    "
            f"Datei: {self.manager.logger.log_file}"
        )

        self.footer_right.setText(
            f"{self.logs.list.count()} Zeilen"
        )

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

            #
            # xdg-open ist meist selbst ein Shellskript - ohne
            # bereinigte Umgebung erbt es das AppImage-eigene
            # LD_LIBRARY_PATH und crasht lautlos (siehe
            # Runtime.clean_subprocess_env()).
            #

            subprocess.Popen(
                ["xdg-open", str(folder)],
                env=Runtime.clean_subprocess_env(),
            )

        elif sys.platform == "win32":

            subprocess.Popen(
                ["explorer", str(folder)]
            )

        elif sys.platform == "darwin":

            subprocess.Popen(
                ["open", str(folder)]
            )
