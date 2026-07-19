from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from gui.theme.colors import Colors

from ._common import SectionContent


class AppearanceSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · ERSCHEINUNGSBILD",
            "Erscheinungsbild",
            "WeintCompanion nutzt aktuell ausschließlich ein dunkles "
            "Farbschema - ein Hell-Modus ist nicht geplant.",
        )

        self.manager = manager

        swatch_row = QWidget()

        layout = QHBoxLayout(swatch_row)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(8)

        for color in (
            Colors.BACKGROUND,
            Colors.SURFACE,
            Colors.PRIMARY,
            Colors.PRIMARY_2,
        ):

            swatch = QLabel()

            swatch.setFixedSize(40, 40)

            swatch.setStyleSheet(f"""
            QLabel{{
                background:{color};
                border:1px solid {Colors.BORDER_LIGHT};
                border-radius:8px;
            }}
            """)

            layout.addWidget(swatch)

        layout.addStretch()

        self.addRow(swatch_row, divider=False)

    def refresh(self):
        pass
