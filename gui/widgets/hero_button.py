from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class HeroButton(QFrame):

    installRequested = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("card")

        self.mode = "install"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        #
        # Titel
        #

        self.title = QLabel("WeintCodex")

        self.title.setAlignment(Qt.AlignCenter)

        self.title.setStyleSheet("""
            font-size:24px;
            font-weight:700;
            background:transparent;
        """)

        layout.addWidget(self.title)

        #
        # Status
        #

        self.status = QLabel("Bereit.")

        self.status.setObjectName("subtitle")
        self.status.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.status)

        #
        # Button
        #

        self.button = QPushButton()

        self.button.setObjectName("heroButton")
        self.button.setMinimumHeight(56)

        self.button.clicked.connect(
            self.installRequested.emit
        )

        layout.addWidget(self.button)

        #
        # Progressbar
        #

        self.progress = QProgressBar()

        self.progress.hide()

        layout.addWidget(self.progress)

        self.refresh()

    # --------------------------------------------------

    def refresh(self, state=None):

        #
        # Kein Status vorhanden
        #

        if state is None:

            self.button.setText(
                "⬇ WeintCodex installieren"
            )

            return

        #
        # WoW fehlt
        #

        if not state.wow_found:

            self.mode = "select"

            self.status.setText(
                "Bitte zuerst den WoW-Ordner auswählen."
            )

            self.button.setText(
                "📂 WoW-Ordner auswählen"
            )

            return

        #
        # Addon fehlt
        #

        if not state.addon_found:

            self.mode = "install"

            self.status.setText(
                "WeintCodex ist noch nicht installiert."
            )

            self.button.setText(
                "⬇ WeintCodex installieren"
            )

            return

        #
        # Update verfügbar
        #

        if state.update_available:

            self.mode = "update"

            self.status.setText(
                f"Version {state.github_version} verfügbar."
            )

            self.button.setText(
                "🔄 WeintCodex aktualisieren"
            )

            return

        #
        # Aktuell
        #

        self.mode = "current"

        self.status.setText(
            f"Version {state.addon_version} ist installiert."
        )

        self.button.setText(
            "✔ WeintCodex ist aktuell"
        )

    # --------------------------------------------------

    def set_text(self, text):

        self.button.setText(text)

    # --------------------------------------------------

    def set_status(self, text):

        self.status.setText(text)

    # --------------------------------------------------

    def set_busy(self, busy):

        self.button.setDisabled(busy)

        self.progress.setVisible(busy)

        if busy:

            #
            # Animierte Progressbar
            #

            self.progress.setRange(0, 0)

        else:

            self.progress.setRange(0, 100)
            self.progress.setValue(0)

    # --------------------------------------------------

    def set_progress(self, value):

        self.progress.setRange(0, 100)

        self.progress.setValue(value)