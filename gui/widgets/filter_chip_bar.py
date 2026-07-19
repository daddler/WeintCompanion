from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from gui.theme.colors import Colors


ACTIVE_STYLE = f"""
QPushButton{{
    padding:6px 12px;
    background:rgba(168,85,247,38);
    border:1px solid {Colors.PRIMARY};
    color:{Colors.PRIMARY_HOVER};
    border-radius:999px;
    font-size:12px;
    font-weight:700;
}}
"""

INACTIVE_STYLE = f"""
QPushButton{{
    padding:6px 12px;
    background:{Colors.SURFACE_LIGHT};
    border:1px solid {Colors.BORDER_LIGHT};
    color:{Colors.TEXT_SECONDARY};
    border-radius:999px;
    font-size:12px;
}}
QPushButton:hover{{
    color:{Colors.TEXT};
}}
"""


LEVEL_LABELS = [
    (None, "Alle"),
    ("success", "Success"),
    ("info", "Info"),
    ("warning", "Warn"),
    ("error", "Error"),
]


class FilterChipBar(QWidget):
    """
    Exklusive Filter-Chips mit Live-Zählern (Alle/Success/Info/Warn/Error),
    wie im Logs-Screen des Designs.
    """

    filterChanged = Signal(object)

    def __init__(self):

        super().__init__()

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self._buttons = {}

        for level, label in LEVEL_LABELS:

            button = QPushButton(f"{label} · 0")

            button.setCheckable(True)

            button.setCursor(Qt.PointingHandCursor)

            button.setStyleSheet(INACTIVE_STYLE)

            button.toggled.connect(
                lambda checked, level=level, button=button:
                self._on_toggled(level, button, checked)
            )

            self.group.addButton(button)

            layout.addWidget(button)

            self._buttons[level] = (button, label)

        layout.addStretch()

        self._buttons[None][0].setChecked(True)

    # --------------------------------------------------

    def _on_toggled(self, level, button, checked):

        button.setStyleSheet(
            ACTIVE_STYLE if checked else INACTIVE_STYLE
        )

        if checked:
            self.filterChanged.emit(level)

    # --------------------------------------------------

    def setCounts(self, counts: dict):
        """
        counts: {"success": n, "info": n, "warning": n, "error": n}
        """

        total = sum(counts.values())

        for level, (button, label) in self._buttons.items():

            count = total if level is None else counts.get(level, 0)

            button.setText(f"{label} · {count}")
