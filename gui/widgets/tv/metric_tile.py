"""
Kompakte Live-Kachel: Beschriftung, großer Wert, kleine Fußzeile.

Abgrenzung zur bestehenden StatusCard (gui/widgets/status_card.py):
die ist 150px hoch, klickbar und für vier Kennzahlen auf dem
Dashboard gedacht. WeintTV zeigt acht bis zehn Werte gleichzeitig
und aktualisiert sie im Sekundentakt - dafür braucht es eine
deutlich flachere Kachel ohne Klickverhalten.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.eyebrow import eyebrow_label


class MetricTile(QFrame):

    def __init__(
        self,
        label: str,
        value: str = "-",
        caption: str = "",
        parent=None,
    ):

        super().__init__(parent)

        self.setObjectName("metricTile")

        #
        # Ohne WA_StyledBackground bliebe die Kachel durch die
        # globale Regel "QWidget{background:transparent}" ungefüllt -
        # siehe den Kommentar in gui/pages/settings_sections/_common.py.
        #

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(f"""
        QFrame#metricTile{{
            background:{Colors.CARD};
            border:1px solid {Colors.BORDER};
            border-radius:{Metrics.RADIUS_MEDIUM}px;
        }}
        """)

        root = QVBoxLayout(self)

        root.setContentsMargins(16, 12, 16, 12)

        root.setSpacing(2)

        #
        # Beschriftung
        #

        self.label = eyebrow_label(label)

        root.addWidget(self.label)

        #
        # Wert
        #

        self.value = QLabel(value)

        self._value_color = Colors.WHITE

        self._apply_value_style()

        root.addWidget(self.value)

        #
        # Fußzeile
        #

        self.caption = QLabel(caption)

        self.caption.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        self.caption.setVisible(bool(caption))

        root.addWidget(self.caption)

    # --------------------------------------------------

    def _apply_value_style(self):

        self.value.setStyleSheet(
            f"font-size:{Metrics.CARD_VALUE_SIZE}px;"
            f"font-weight:700;color:{self._value_color};"
            "letter-spacing:-0.02em;background:transparent;border:none;"
        )

    # --------------------------------------------------
    # API
    # --------------------------------------------------

    def setValue(self, value: str):

        if self.value.text() == value:
            return

        self.value.setText(value)

    def setValueColor(self, color: str):

        if color == self._value_color:
            return

        self._value_color = color

        self._apply_value_style()

    def setCaption(self, caption: str):

        if self.caption.text() == caption:

            self.caption.setVisible(bool(caption))

            return

        self.caption.setText(caption)

        self.caption.setVisible(bool(caption))

    def setLabel(self, label: str):

        self.label.setText(label)
