from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.navigation_item import NavigationItem

from .settings_sections.about import AboutSection
from .settings_sections.appearance import AppearanceSection
from .settings_sections.auto_update import AutoUpdateSection
from .settings_sections.backups import BackupsSection
from .settings_sections.discord import DiscordSection
from .settings_sections.general import GeneralSection
from .settings_sections.wow_client import WowClientSection


SECTIONS = [

    ("general", "Allgemein", GeneralSection),
    ("wow_client", "WoW-Client", WowClientSection),
    ("discord", "Discord", DiscordSection),
    ("auto_update", "Auto-Update", AutoUpdateSection),
    ("backups", "Backups", BackupsSection),
    ("appearance", "Erscheinungsbild", AppearanceSection),
    ("about", "Über", AboutSection),

]


class SettingsPage(QWidget):
    """
    Koordinator: linke Unternavigation (Text) + rechter Inhalt,
    siehe Design's Settings-Screen (72px Rail + 220px Nav + Inhalt).
    """

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(0)

        #
        # --------------------------------------------------
        # Unternavigation
        # --------------------------------------------------
        #

        nav_container = QWidget()

        nav_container.setFixedWidth(Metrics.SETTINGS_NAV_WIDTH)

        nav_container.setStyleSheet(f"""
        QWidget{{
            background:{Colors.BACKGROUND};
            border-right:1px solid {Colors.BORDER};
        }}
        """)

        nav_layout = QVBoxLayout(nav_container)

        nav_layout.setContentsMargins(16, 20, 16, 20)

        nav_layout.setSpacing(2)

        heading = QLabel("EINSTELLUNGEN")

        heading.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_MUTED};"
            "letter-spacing:0.15em;"
        )

        nav_layout.addWidget(heading)

        nav_layout.addSpacing(6)

        self._nav_items = {}

        self._section_index = {}

        for index, (key, label, _cls) in enumerate(SECTIONS):

            item = NavigationItem(label)

            item.clicked.connect(
                lambda i=index: self.show_index(i)
            )

            nav_layout.addWidget(item)

            self._nav_items[key] = item
            self._section_index[key] = index

        nav_layout.addStretch()

        root.addWidget(nav_container)

        #
        # --------------------------------------------------
        # Inhalt
        # --------------------------------------------------
        #

        self.stack = QStackedWidget()

        #
        # Die Unterseiten sind auf max. 640px Inhaltsbreite begrenzt
        # (siehe SectionContent) - der Rest der Fläche muss trotzdem
        # dunkel bleiben statt die weiße Qt-Standardpalette
        # durchscheinen zu lassen.
        #

        self.stack.setStyleSheet(
            f"background:{Colors.BACKGROUND};"
        )

        root.addWidget(self.stack, 1)

        self._sections = []

        for key, label, cls in SECTIONS:

            section = cls(manager)

            self.stack.addWidget(section)

            self._sections.append(section)

        self.show_index(0)

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def show_index(self, index: int):

        for i, item in enumerate(self._nav_items.values()):

            item.setActive(i == index)

        self.stack.setCurrentIndex(index)

        section = self._sections[index]

        if hasattr(section, "refresh"):

            section.refresh()

    def show_section(self, key: str):

        index = self._section_index.get(key)

        if index is not None:

            self.show_index(index)

    # --------------------------------------------------
    # Refresh (von MainWindow bei jedem Seitenwechsel aufgerufen)
    # --------------------------------------------------

    def refresh(self):

        for section in self._sections:

            if hasattr(section, "refresh"):

                section.refresh()
