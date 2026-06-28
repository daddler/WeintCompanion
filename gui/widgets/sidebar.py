from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from gui.widgets.navigation_item import NavigationItem


class Sidebar(QFrame):

    pageChanged = Signal(int)

    def __init__(self, manager):
        super().__init__()

        self.manager = manager
        self.setObjectName("sidebar")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        #
        # ----------------------------------------------------
        # Logo
        # ----------------------------------------------------
        #

        self.logo = QLabel()

        self.logo.setAlignment(Qt.AlignCenter)

        pix = QPixmap("assets/logo.png")

        if not pix.isNull():

            self.logo.setPixmap(
                pix.scaled(
                    110,
                    110,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        layout.addWidget(self.logo)

        #
        # Titel
        #

        title = QLabel("WEINT\nCOMPANION")
        title.setObjectName("sidebarLogo")
        title.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)

        subtitle = QLabel(
            "MoP Classic Companion"
        )

        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        layout.addWidget(subtitle)

        version = QLabel("Version 0.1.0")

        version.setObjectName("subtitle")
        version.setAlignment(Qt.AlignCenter)

        layout.addWidget(version)

        layout.addSpacing(20)

        #
        # Navigation
        #

        self.items = []

        pages = [

            ("assets/home.png", "Dashboard"),

            ("assets/package.png", "WeintCodex"),

            ("assets/sync.png", "Synchronisation"),

            ("assets/settings.png", "Einstellungen"),

            ("assets/logs.png", "Logs"),

        ]

        for index, (icon, text) in enumerate(pages):

            item = NavigationItem(icon, text)

            item.clicked.connect(
                lambda i=index: self.change_page(i)
            )

            layout.addWidget(item)

            self.items.append(item)

        layout.addStretch()

        #
        # Status
        #

        self.status = QFrame()

        self.status.setObjectName("card")

        status_layout = QVBoxLayout(self.status)

        status_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        title = QLabel("🟢 Companion bereit")
        title.setObjectName("cardTitle")

        version = QLabel("Version 0.1.0")
        version.setObjectName("subtitle")

        self.addon = QLabel(
            "📦 WeintCodex\nWird geprüft..."
        )

        self.addon.setObjectName("subtitle")

        status_layout.addWidget(title)
        status_layout.addWidget(version)

        status_layout.addSpacing(8)

        status_layout.addWidget(self.addon)

        layout.addWidget(self.status)

        #
        # Footer
        #

        footer = QLabel("© Bis einer weint")

        footer.setAlignment(Qt.AlignCenter)

        footer.setObjectName("subtitle")

        layout.addSpacing(8)

        layout.addWidget(footer)

        #
        # Dashboard aktiv
        #

        self.refresh()

        self.items[0].setActive(True)

    # ---------------------------------------------------------

    def change_page(self, index):

        for item in self.items:

            item.setActive(False)

        self.items[index].setActive(True)

        self.pageChanged.emit(index)

    def refresh(self):

        state = self.manager.state

        if state.addon_found:

            self.addon.setText(
                f"📦 WeintCodex\nVersion {state.addon_version}"
            )

        else:

            self.addon.setText(
                "📦 WeintCodex\nNicht installiert"
            )