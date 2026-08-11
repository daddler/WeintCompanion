"""
WeintCompanion 2.0
Segmentierter Umschalter

Bis 1.7 war das eine Reihe einzelner Knöpfe mit je eigenem Rahmen und
8 px Abstand dazwischen - optisch drei Knöpfe, die zufällig
nebeneinander standen. Seit 2.0 ist es **ein** Element: eine
eingelassene Rinne (`surface.card`), 4 px Innenrand, und darin
Segmente von 30 px. Das aktive Segment hebt sich als Fläche heraus
(`surface.raised` plus 1-px-Akzentrahmen), statt sich einzufärben.

Der Unterschied ist nicht nur Geschmack: drei gleich aussehende Knöpfe
laden zum Drücken ein, ein Umschalter zeigt einen Zustand. Genau
darum geht es hier - LIVE / ARCHIV / VERGLEICH ist keine Handlung,
sondern eine Ansichtswahl.

**Eine Falle, die einmal echten Schaden angerichtet hat**:
`setValue()` mit einem unbekannten Wert tut wortlos nichts. Der
Archivmodus kennt drei Werte, die Wiedergabe ist ein vierter - wird
`MODE_REPLAY` nicht auf eine der angezeigten Ansichten abgebildet,
bleibt der Schalter auf seinem alten Stand stehen, während die
Anwendung längst woanders ist. Das Verhalten bleibt (eine Ausnahme in
einem Qt-Slot ist schlimmer), ist aber hier ausdrücklich vermerkt.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme


SEGMENT_HEIGHT = 30

TRACK_PADDING = 4


class SegmentedControl(QWidget):
    """
    Reihe exklusiver Segmente in einer gemeinsamen Rinne.
    """

    valueChanged = Signal(object)

    def __init__(self, options: list[tuple[str, object]], parent=None):
        """
        options: Liste aus (Label, Wert)-Paaren.
        """

        super().__init__(parent)

        self.setObjectName("segmentedControl")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self._values = []

        self._buttons = []

        self.setFixedHeight(SEGMENT_HEIGHT + 2 * TRACK_PADDING)

        #
        # Der Umschalter ist so breit wie seine Segmente und nicht so
        # breit wie der Platz, den ein Layout ihm anbietet. Bis 1.7
        # sorgte dafür ein `addStretch()` **innerhalb** des Elements -
        # das ging, solange die Segmente einzelne Knöpfe ohne
        # gemeinsame Fläche waren. Jetzt gibt es eine Rinne, und ein
        # Dehnbereich darin würde sie über die halbe Seite ziehen.
        #

        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            TRACK_PADDING,
            TRACK_PADDING,
            TRACK_PADDING,
            TRACK_PADDING,
        )

        layout.setSpacing(2)

        self.group = QButtonGroup(self)

        self.group.setExclusive(True)

        for label, value in options:

            button = QPushButton(label)

            button.setCheckable(True)

            button.setCursor(Qt.PointingHandCursor)

            button.setFixedHeight(SEGMENT_HEIGHT)

            button.setFont(font("mono"))

            #
            # Gebundene Methode statt einer Lambda mit `b=button`:
            # jene hält `self` fest, und weil der Knopf ein Kind von
            # `self` ist, entsteht ein Kreis
            # (self -> Knopf -> Verbindung -> Lambda -> self), den die
            # Speicherbereinigung nicht auflösen kann - die Lambda
            # liegt in der C++-Verbindung und ist für Python nicht
            # sichtbar. Das Steuerelement würde damit nie freigegeben.
            # Welcher Knopf gemeint ist, sagt sender().
            #

            button.toggled.connect(self._on_button_toggled)

            self.group.addButton(button)

            layout.addWidget(button)

            self._values.append(value)

            self._buttons.append(button)

        self._apply_track()

        for button in self._buttons:
            self._apply_segment(button, button.isChecked())

        #
        # Gebundene Methode statt Lambda: eine Lambda hält eine harte
        # Referenz auf `self`, und der ThemeManager ist ein Singleton -
        # das Steuerelement würde damit nie mehr freigegeben.
        #

        theme().accent_changed.connect(self._on_accent)

    # --------------------------------------------------

    def _apply_track(self):

        restyle(
            self,
            f"""
            QWidget#segmentedControl{{
                background:{tokens.SURFACE["card"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

    def _apply_segment(self, button, active: bool):

        if active:

            accent = theme().accent_base()

            sheet = f"""
            QPushButton{{
                padding:0px 14px;
                background:{tokens.SURFACE["raised"]};
                border:1px solid {tokens.tint(accent, 0.40)};
                color:{theme().accent_light()};
                border-radius:{tokens.RADIUS["sm"]}px;
                font-weight:{tokens.WEIGHT["bold"]};
            }}
            """

        else:

            sheet = f"""
            QPushButton{{
                padding:0px 14px;
                background:transparent;
                border:1px solid transparent;
                color:{tokens.TEXT["muted"]};
                border-radius:{tokens.RADIUS["sm"]}px;
                font-weight:{tokens.WEIGHT["normal"]};
            }}
            QPushButton:hover{{
                color:{tokens.TEXT["primary"]};
            }}
            """

        #
        # restyle() statt setStyleSheet(): der Umschalter im Archiv
        # hängt an `replayChanged` und wird damit bei laufender
        # Wiedergabe vier Mal je Sekunde angefasst.
        #

        restyle(button, sheet)

    def _on_accent(self, _name: str = ""):

        for button in self._buttons:
            self._apply_segment(button, button.isChecked())

    # --------------------------------------------------

    def _on_button_toggled(self, checked: bool):
        """
        Der Slot am `toggled` jedes Segmentknopfes.

        Welcher Knopf es war, sagt `sender()` - siehe den Kommentar an
        der Verbindung. Ein unbekannter Absender wird stillschweigend
        ignoriert: der Slot hängt an nichts anderem, und eine Ausnahme
        in einem Qt-Slot ist schwer zu verfolgen.
        """

        button = self.sender()

        if button not in self._buttons:
            return

        self._on_toggled(button, checked)

    def _on_toggled(self, button, checked):

        self._apply_segment(button, checked)

        if checked:

            index = self._buttons.index(button)

            self.valueChanged.emit(self._values[index])

    # --------------------------------------------------

    def setValue(self, value):
        """
        Achtung: ein unbekannter Wert bleibt wirkungslos - siehe den
        Modulkommentar.
        """

        for button, candidate in zip(self._buttons, self._values):

            if candidate == value:

                button.setChecked(True)

                return

    def value(self):

        for button, candidate in zip(self._buttons, self._values):

            if button.isChecked():

                return candidate

        return None
