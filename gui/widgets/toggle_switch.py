from __future__ import annotations

from PySide6.QtCore import (
    Qt,
    QSize,
    QRectF,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)

from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
)

from PySide6.QtWidgets import QAbstractButton

from gui.theme import tokens
from gui.theme.motion import curve, duration
from gui.theme.theme_manager import theme


class ToggleSwitch(QAbstractButton):
    """
    Umschaltknopf, 36 x 20 px, Knauf 16 px.

    Aus: angehobene Flaeche mit Rahmen, Knauf in `text.muted`.
    Ein: Verlauf in der Akzentfarbe, Knauf weiss.

    Der Verlauf trug bis 1.7 das Violett-Indigo der alten Marke. Seit
    2.0 gilt "Bernstein traegt die Bedeutung, Violett nur das Licht":
    ein Schalter sagt an/aus, ist also bedeutungstragend, und faerbt
    sich deshalb im Akzent. Gelesen wird die Farbe im paintEvent -
    ein im Konstruktor gemerkter Wert ueberlebte den Akzentwechsel
    nicht.
    """

    WIDTH = 36
    HEIGHT = 20
    THUMB_MARGIN = 2

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)

        self.setCheckable(True)

        self.setCursor(Qt.PointingHandCursor)

        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._thumb_position = (
            1.0 if checked else 0.0
        )

        self._animation = QPropertyAnimation(
            self,
            b"thumbPosition",
        )

        #
        # Dauer und Kurve kommen aus den Bewegungstoken - insbesondere
        # liefert duration() bei "Bewegung reduzieren" 0 ms, und der
        # Knauf springt statt zu gleiten. Eine hier fest eingetragene
        # Zahl haette diese Einstellung stumm umgangen.
        #

        self._animation.setDuration(duration("toggle"))
        self._animation.setEasingCurve(
            QEasingCurve(curve("toggle"))
        )

        theme().accent_changed.connect(lambda _n: self.update())

        theme().motion_changed.connect(
            lambda _r: self._animation.setDuration(duration("toggle"))
        )

        #
        # super().setChecked() statt self.setChecked(): _thumb_position
        # ist oben bereits passend zu "checked" gesetzt, unser eigener
        # setChecked()-Override (siehe unten) wäre hier nur redundant.
        #

        super().setChecked(checked)

        self.toggled.connect(
            self._animate_to_state
        )

    # --------------------------------------------------
    # Sichtbaren Zustand synchron zu isChecked() halten
    # --------------------------------------------------
    # QAbstractButton.setChecked() ist in Qt nicht virtual - ein
    # interaktiver Klick ändert den Zustand direkt in C++ und feuert
    # dabei ganz normal das toggled-Signal (oben verbunden mit
    # _animate_to_state). Ruft dagegen unser eigener Code setChecked()
    # explizit auf - typischerweise aus refresh() mit blockSignals(True),
    # um die zugehörige _save_*()-Methode nicht erneut auszulösen -,
    # würde ohne diesen Override die Thumb-Position stumm auf dem alten
    # Wert hängen bleiben: der Schalter zeigt dann z.B. nach einem
    # Neustart "aus" an, obwohl isChecked() bereits korrekt True ist.

    def setChecked(self, checked: bool):

        super().setChecked(checked)

        self._animate_to_state(checked)

    # --------------------------------------------------
    # Property fürs Thumb
    # --------------------------------------------------

    def getThumbPosition(self):
        return self._thumb_position

    def setThumbPosition(self, value):
        self._thumb_position = value
        self.update()

    thumbPosition = Property(
        float,
        getThumbPosition,
        setThumbPosition,
    )

    def _animate_to_state(self, checked: bool):

        target = 1.0 if checked else 0.0

        #
        # Steht das Thumb schon am Ziel, gibt es nichts zu animieren.
        # Ohne diese Prüfung war das trotzdem nicht folgenlos: der
        # Lektionskatalog der Academy ruft setChecked() beim Zeichnen
        # jedes Snapshots für JEDE Zeile auf, auch wenn sich nichts
        # geändert hat. Bei laufender Wiedergabe (vier Bilder je
        # Sekunde) liefen so dauerhaft dutzende Animationen, die jede
        # für sich ein Neuzeichnen anstießen - Rechenzeit für eine
        # Bewegung, die niemand sieht, weil Start- und Endwert
        # identisch sind.
        #

        if (
            self._animation.state() != QPropertyAnimation.Running
            and self._thumb_position == target
        ):
            return

        self._animation.stop()

        self._animation.setStartValue(
            self._thumb_position
        )

        self._animation.setEndValue(target)

        self._animation.start()

    # --------------------------------------------------

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(
            0,
            0,
            self.WIDTH,
            self.HEIGHT,
        )

        radius = self.HEIGHT / 2

        if not self.isEnabled():

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(tokens.SURFACE["raised"]))
            painter.drawRoundedRect(rect, radius, radius)

        elif self._thumb_position > 0.001:

            gradient = QLinearGradient(
                rect.left(),
                0,
                rect.right(),
                0,
            )

            gradient.setColorAt(0, QColor(theme().accent_light()))
            gradient.setColorAt(1, QColor(theme().accent_base()))

            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, radius, radius)

        else:

            painter.setPen(
                QColor(tokens.BORDER["strong"])
            )

            painter.setBrush(
                QColor(tokens.SURFACE["raised"])
            )

            painter.drawRoundedRect(
                rect.adjusted(0.5, 0.5, -0.5, -0.5),
                radius,
                radius,
            )

        #
        # Thumb
        #

        diameter = self.HEIGHT - self.THUMB_MARGIN * 2

        travel = self.WIDTH - diameter - self.THUMB_MARGIN * 2

        x = self.THUMB_MARGIN + travel * self._thumb_position

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QColor(tokens.WHITE)
            if self.isEnabled() and self._thumb_position > 0.001
            else QColor(tokens.TEXT["muted"])
        )

        painter.drawEllipse(
            QRectF(
                x,
                self.THUMB_MARGIN,
                diameter,
                diameter,
            )
        )

        painter.end()
