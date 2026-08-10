"""
WeintCompanion 2.0
Die eigene Titelleiste

Das Fenster ist seit 2.0 rahmenlos (`Qt.FramelessWindowHint`), also
muss die Anwendung selbst liefern, was sonst der Fenstermanager
beisteuert: Ziehen, Maximieren per Doppelklick und drei Fensterknöpfe.

Warum überhaupt: die Systemtitelleiste ist auf jeder Plattform anders
hoch, anders gefärbt und trägt auf keiner davon die Marke. Sie sitzt
außerdem genau dort, wo der Entwurf sein Titelleistenlicht und die
Markenplakette haben will - der einzige Ort, an dem das
Violett-Indigo als reines Flächenlicht auftritt.

**Der Preis ist die Fensterverwaltung**, und zwei Details davon sind
leicht zu übersehen:

- Ein Doppelklick maximiert, aber ein Zug an der *maximierten* Leiste
  muss das Fenster zuerst wiederherstellen und dann unter dem Zeiger
  weiterziehen - sonst hängt ein bildschirmbreites Fenster starr am
  Mauszeiger.
- Der Zug darf nicht auf den Fensterknöpfen beginnen. Deshalb prüft
  `mousePressEvent` die getroffene Stelle und nicht nur die Taste.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from core.version import VERSION

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme


class WindowButton(QLabel):
    """
    Einer der drei Fensterknöpfe (28 x 24 px).

    Als QLabel statt QPushButton, damit die globale Knopfregel des
    Stylesheets (Akzentverlauf, 40 px Höhe) hier nicht greift - ein
    bernsteinfarbener Schließen-Knopf wäre grotesk.
    """

    clicked = Signal()

    def __init__(self, glyph: str, danger: bool = False, parent=None):

        super().__init__(glyph, parent)

        self.setObjectName("windowButton")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setFixedSize(28, 24)

        self.setAlignment(Qt.AlignCenter)

        self.setCursor(Qt.ArrowCursor)

        self._danger = danger

        self.setFont(font("mono"))

        self._apply(False)

    def _apply(self, hover: bool):

        if hover:

            background = (
                tokens.tint(tokens.STATE["error"], 0.90)
                if self._danger
                else tokens.SURFACE["raised"]
            )

            color = tokens.WHITE

        else:

            background = "transparent"

            color = tokens.TEXT["muted"]

        restyle(
            self,
            f"""
            QLabel#windowButton{{
                background:{background};
                color:{color};
                border:none;
                border-radius:{tokens.RADIUS["sm"]}px;
            }}
            """,
        )

    def enterEvent(self, event):
        super().enterEvent(event)
        self._apply(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._apply(False)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        event.accept()


class TitleBar(QFrame):
    """
    Markenplakette, Produktname, Version - und rechts die drei Knöpfe.
    """

    def __init__(self, window, parent=None):

        super().__init__(parent)

        self._window = window

        self.setObjectName("titleBar")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setFixedHeight(theme().metric("title_bar", 40))

        #
        # Woher der Zug begann. None heißt "es wird nicht gezogen".
        #

        self._drag_offset: QPoint | None = None

        root = QHBoxLayout(self)

        root.setContentsMargins(10, 0, 8, 0)

        root.setSpacing(10)

        #
        # Markenplakette. Hier - und nur hier plus dem Kontofuß der
        # Navigationsspalte - tritt der Violett-Indigo-Verlauf auf.
        #

        self.brand = QLabel("W")

        self.brand.setFixedSize(22, 22)

        self.brand.setAlignment(Qt.AlignCenter)

        self.brand.setFont(font("mono"))

        root.addWidget(self.brand)

        self.name = QLabel("WeintCompanion")

        self.name.setFont(font("card"))

        root.addWidget(self.name)

        self.version = QLabel(VERSION)

        self.version.setFont(font("mono"))

        root.addWidget(self.version)

        root.addStretch(1)

        self.minimise = WindowButton("–")

        self.minimise.clicked.connect(self._window.showMinimized)

        root.addWidget(self.minimise)

        self.maximise = WindowButton("□")

        self.maximise.clicked.connect(self.toggle_maximised)

        root.addWidget(self.maximise)

        self.close_button = WindowButton("✕", danger=True)

        self.close_button.clicked.connect(self._window.close)

        root.addWidget(self.close_button)

        self._apply()

        theme().accent_changed.connect(lambda _n: self._apply())

    # --------------------------------------------------

    def _apply(self):

        restyle(
            self.brand,
            f"""
            QLabel{{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 {theme().accent_light()},
                    stop:1 {theme().accent_base()}
                );
                color:{theme().accent_on_base()};
                border-radius:7px;
            }}
            """,
        )

        restyle(
            self.name,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        restyle(
            self.version,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

    # --------------------------------------------------

    def paintEvent(self, event):
        """
        Senkrechter Verlauf plus 1-px-Unterkante (§4).

        Gemalt und nicht per Stylesheet gesetzt, weil die Unterkante
        eine einzelne Linie ist - ein `border-bottom` im Stylesheet
        würde zusammen mit dem Verlauf neu berechnet und liegt bei
        ungeraden Gerätefaktoren einen halben Pixel daneben.
        """

        painter = QPainter(self)

        gradient = QLinearGradient(0, 0, 0, self.height())

        gradient.setColorAt(0.0, QColor("#0C0C10"))
        gradient.setColorAt(1.0, QColor(tokens.SURFACE["sunken"]))

        painter.fillRect(self.rect(), gradient)

        painter.setPen(QColor(tokens.SURFACE["raised"]))

        painter.drawLine(
            0,
            self.height() - 1,
            self.width(),
            self.height() - 1,
        )

    # --------------------------------------------------
    # Ziehen und Maximieren
    # --------------------------------------------------

    def toggle_maximised(self):

        if self._window.isMaximized():

            self._window.showNormal()

            self.maximise.setText("□")

            return

        self._window.showMaximized()

        self.maximise.setText("❐")

    def _is_drag_area(self, position) -> bool:
        """
        Ob an dieser Stelle gezogen werden darf.

        Die Knöpfe sind ausgenommen - ein Zug, der auf "Schließen"
        beginnt, wäre sonst ein verschobenes Fenster statt eines
        Klicks.
        """

        child = self.childAt(position.toPoint())

        return not isinstance(child, WindowButton)

    def mousePressEvent(self, event):

        if (
            event.button() != Qt.LeftButton
            or not self._is_drag_area(event.position())
        ):

            super().mousePressEvent(event)

            return

        self._drag_offset = (
            event.globalPosition().toPoint()
            - self._window.frameGeometry().topLeft()
        )

        event.accept()

    def mouseMoveEvent(self, event):

        if self._drag_offset is None:
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        global_position = event.globalPosition().toPoint()

        #
        # Ein maximiertes Fenster wird beim Ziehen zuerst
        # wiederhergestellt. Ohne das hinge ein bildschirmbreites
        # Fenster starr am Zeiger; mit naivem Wiederherstellen spränge
        # seine linke obere Ecke unter den Zeiger, auch wenn der
        # rechts außen angesetzt hat. Deshalb wird der Griffpunkt
        # anteilig auf die neue, kleinere Breite umgerechnet.
        #

        if self._window.isMaximized():

            ratio = (
                event.position().x() / max(1, self.width())
            )

            self._window.showNormal()

            self.maximise.setText("□")

            width = self._window.width()

            self._drag_offset = QPoint(
                int(width * ratio),
                self._drag_offset.y(),
            )

        self._window.move(global_position - self._drag_offset)

        event.accept()

    def mouseReleaseEvent(self, event):

        self._drag_offset = None

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):

        if (
            event.button() == Qt.LeftButton
            and self._is_drag_area(event.position())
        ):

            self.toggle_maximised()

            event.accept()

            return

        super().mouseDoubleClickEvent(event)
