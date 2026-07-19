from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from gui.theme.colors import Colors


ACTIVE_STYLE = f"""
QPushButton{{
    padding:8px 14px;
    background:rgba(168,85,247,38);
    border:1px solid {Colors.PRIMARY};
    color:{Colors.PRIMARY_HOVER};
    border-radius:6px;
    font-size:12px;
    font-weight:700;
    font-family:"JetBrains Mono";
}}
"""

INACTIVE_STYLE = f"""
QPushButton{{
    padding:8px 14px;
    background:{Colors.SURFACE_LIGHT};
    border:1px solid {Colors.BORDER_LIGHT};
    color:{Colors.TEXT_SECONDARY};
    border-radius:6px;
    font-size:12px;
    font-weight:500;
    font-family:"JetBrains Mono";
}}
QPushButton:hover{{
    color:{Colors.TEXT};
}}
"""


class SegmentedControl(QWidget):
    """
    Reihe exklusiver Buttons (wie die Sync-Intervall-Auswahl
    1s/5s/15s/30s/Manuell im Design).
    """

    valueChanged = Signal(object)

    def __init__(self, options: list[tuple[str, object]], parent=None):
        """
        options: Liste aus (Label, Wert)-Paaren.
        """

        super().__init__(parent)

        self._values = []
        self._buttons = []

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        for label, value in options:

            button = QPushButton(label)

            button.setCheckable(True)

            button.setCursor(Qt.PointingHandCursor)

            button.setStyleSheet(INACTIVE_STYLE)

            button.toggled.connect(
                lambda checked, b=button: self._on_toggled(b, checked)
            )

            self.group.addButton(button)

            layout.addWidget(button)

            self._values.append(value)
            self._buttons.append(button)

        layout.addStretch()

    # --------------------------------------------------

    def _on_toggled(self, button, checked):

        button.setStyleSheet(
            ACTIVE_STYLE if checked else INACTIVE_STYLE
        )

        if checked:

            index = self._buttons.index(button)

            self.valueChanged.emit(
                self._values[index]
            )

    # --------------------------------------------------

    def setValue(self, value):

        for button, candidate in zip(self._buttons, self._values):

            if candidate == value:

                button.setChecked(True)

                return

    def value(self):

        for button, candidate in zip(self._buttons, self._values):

            if button.isChecked():

                return candidate

        return None
