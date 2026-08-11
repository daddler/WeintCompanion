"""
Der Startbildschirm.

Bis 2.0 war das Artwork hier nur Textur: bei 28 % Deckkraft, unter
einer Vignette und einem violetten Schleier, daneben ein selbst
gebautes "W", der Titel und ein Fadenbalken. Das Bild war praktisch
nicht zu erkennen, und alles, was es zeigt, stand als Text noch einmal
darüber.

Jetzt trägt das Bild den Bildschirm. `assets/splash.png` ist ein
fertig gestaltetes Stück - Titel, Wappen, die fünf Bereiche des
Ökosystems und unten ein **gemalter** Ladebalken in einem goldenen
Rahmen. Nichts davon wird noch einmal als Widget nachgebaut; der
einzige Zusatz ist der *echte* Balken, und der liegt genau auf dem
gemalten.

Deshalb sind `BAR_*` Anteile der Bildfläche und keine Pixel: das
Fenster skaliert mit der Bildschirmgröße, das Bild mit dem Fenster,
und die Rinne muss in jeder Größe dieselbe Stelle treffen. Die Rinne
wird dabei bewusst **deckend** gezeichnet - der gemalte Balken ist
gefüllt, ein echter Fortschritt von 0 % würde sonst als 100 %
durchscheinen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from core.resources import Resources
from core.version import VERSION
from gui.theme import tokens


class SplashScreen(QWidget):
    """
    Ephemerer Startbildschirm (~1.5 s, während Python/PySide6
    hochfährt).
    """

    #
    # Breite des Fensters; die Höhe folgt dem Seitenverhältnis des
    # Artworks (16:9) und dem Streifen darunter.
    #

    WIDTH = 900

    ASPECT = 9 / 16

    RADIUS = 14

    #
    # Lage der gemalten Rinne, als Anteil der **Bildfläche** (nicht des
    # Fensters). Gemessen am Artwork; wer das Bild austauscht,
    # korrigiert hier und sonst nirgends.
    #

    BAR_LEFT = 0.291
    BAR_RIGHT = 0.709
    BAR_TOP = 0.926
    BAR_BOTTOM = 0.977

    #
    # Das Artwork trägt unter der Rinne noch ein gemaltes
    # "WIRD GELADEN …". Dieser Anteil wird unten abgeschnitten, damit
    # der Schriftzug nicht doppelt dasteht - einmal gemalt und
    # unveränderlich, einmal echt.
    #

    CROP_BOTTOM = 0.023

    #
    # Der Streifen unter dem Bild, in dem der echte Text steht. Als
    # feste Höhe und nicht als Anteil: Text wird nicht mitskaliert,
    # und ein Anteil von zwei Prozent ergab einen fünf Pixel hohen
    # Streifen, in dem die Zeile abgeschnitten war.
    #

    STATUS_HEIGHT = 34

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SplashScreen
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        self._artwork = QPixmap(Resources.banner())

        self._progress = 0.0

        self._status = "Wird gestartet …"

        self.setFixedSize(self._preferred_size())

        self._centre_on_screen()

    # --------------------------------------------------

    def _preferred_size(self) -> QSize:
        """
        Die Vorgabegröße, aber nie breiter als gut die Hälfte des
        Bildschirms - auf einem 1366 × 768-Notebook füllte ein starres
        900 px breites Fenster sonst zwei Drittel der Breite.
        """

        width = self.WIDTH

        screen = self.screen()

        if screen is not None:

            available = screen.availableGeometry()

            limit = int(available.width() * 0.55)

            if limit > 320 and width > limit:
                width = limit

        return QSize(
            width,
            self._artwork_height(width) + self.STATUS_HEIGHT,
        )

    def _artwork_height(self, width: int) -> int:
        """
        Die *sichtbare* Höhe des Bildes - die volle Höhe abzüglich des
        abgeschnittenen Fußes.
        """

        return round(width * self.ASPECT * (1.0 - self.CROP_BOTTOM))

    def _full_artwork_height(self, width: int) -> float:
        """
        Die Höhe, auf die das Bild skaliert wird, bevor unten
        abgeschnitten wird. Die `BAR_*`-Anteile beziehen sich auf
        diese Höhe, nicht auf die sichtbare.
        """

        return width * self.ASPECT

    def _centre_on_screen(self):

        screen = self.screen()

        if screen is None:
            return

        geometry = screen.availableGeometry()

        self.move(
            geometry.center().x() - self.width() // 2,
            geometry.center().y() - self.height() // 2,
        )

    # --------------------------------------------------
    # Fortschritt
    # --------------------------------------------------

    def setProgress(self, value: float):
        """
        `value` von 0.0 bis 1.0. Wird geklemmt, damit ein Schritt zu
        viel den Balken nicht über den Rahmen hinaus zeichnet.
        """

        value = max(0.0, min(1.0, float(value)))

        if abs(value - self._progress) < 0.001:
            return

        self._progress = value

        self.update()

    def setStatusText(self, text: str):

        if text == self._status:
            return

        self._status = text

        self.update()

    def setStage(self, value: float, text: str):
        """
        Beides in einem Aufruf - so kann ein Schritt nicht seinen Text
        setzen und seinen Fortschritt vergessen.
        """

        self.setProgress(value)

        self.setStatusText(text)

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect())

        #
        # Abgerundete Ecken: das Fenster ist rahmenlos und
        # durchscheinend, ohne Beschneidung stünden die Bildecken
        # eckig im Nichts.
        #

        clip = QPainterPath()

        clip.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        painter.setClipPath(clip)

        painter.fillRect(
            rect,
            QColor(tokens.SURFACE_EXTRA["splash"]),
        )

        artwork = QRectF(
            0,
            0,
            rect.width(),
            self._artwork_height(self.width()),
        )

        status = QRectF(
            0,
            artwork.bottom(),
            rect.width(),
            rect.height() - artwork.height(),
        )

        self._paint_artwork(painter, artwork)

        self._paint_bar(painter, artwork)

        self._paint_status(painter, status)

        #
        # Ein feiner Rand, damit der Bildschirm auf einem hellen
        # Hintergrund nicht ausfranst.
        #

        painter.setClipping(False)

        painter.setBrush(Qt.NoBrush)

        painter.setPen(
            QColor(tokens.SPLASH_ART["frame"])
        )

        painter.drawRoundedRect(
            rect.adjusted(0.5, 0.5, -0.5, -0.5),
            self.RADIUS,
            self.RADIUS,
        )

        painter.end()

    def _paint_artwork(self, painter: QPainter, rect: QRectF):

        if self._artwork.isNull():
            return

        #
        # Auf die *volle* Höhe skalieren und oben ausrichten - der
        # abgeschnittene Fuß fällt damit unter `rect` und wird von der
        # Beschneidung entfernt.
        #

        full_height = int(self._full_artwork_height(self.width()))

        #
        # `KeepAspectRatioByExpanding` und nicht `IgnoreAspectRatio`:
        # das Artwork ist 16:9 und träfe die Fläche genau, aber der
        # Rückfall auf `hero_banner.png` hat ein anderes Verhältnis -
        # gestaucht statt beschnitten wäre dort sofort zu sehen.
        #

        scaled = self._artwork.scaled(
            int(rect.width()),
            full_height,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        painter.save()

        painter.setClipRect(rect)

        painter.drawPixmap(
            int((rect.width() - scaled.width()) / 2),
            int((full_height - scaled.height()) / 2),
            scaled,
        )

        painter.restore()

    def _bar_rect(self, rect: QRectF) -> QRectF:
        """
        Die Rinne liegt im Bild, deshalb zählt die volle Bildhöhe -
        `rect` ist bereits um den Fuß gekürzt.
        """

        height = self._full_artwork_height(self.width())

        return QRectF(
            rect.width() * self.BAR_LEFT,
            height * self.BAR_TOP,
            rect.width() * (self.BAR_RIGHT - self.BAR_LEFT),
            height * (self.BAR_BOTTOM - self.BAR_TOP),
        )

    def _paint_bar(self, painter: QPainter, rect: QRectF):

        bar = self._bar_rect(rect)

        if bar.width() <= 0 or bar.height() <= 0:
            return

        radius = bar.height() / 2

        #
        # Erst die deckende Rinne - sie verdeckt den gemalten Balken.
        #

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QColor(tokens.SPLASH_ART["trough"])
        )

        painter.drawRoundedRect(bar, radius, radius)

        #
        # Dann die Füllung. Der Verlauf spannt sich über die *ganze*
        # Rinne und wird mitgeschnitten, statt über die Füllbreite zu
        # laufen: sonst wanderte die helle Kante mit dem Fortschritt
        # mit, und der Balken sähe bei 10 % genauso aus wie bei 90 %.
        #

        if self._progress > 0:

            fill = QRectF(bar)

            fill.setWidth(bar.width() * self._progress)

            gradient = QLinearGradient(
                bar.left(), 0, bar.right(), 0
            )

            gradient.setColorAt(
                0, QColor(tokens.SPLASH_ART["fillFrom"])
            )

            gradient.setColorAt(
                1, QColor(tokens.SPLASH_ART["fillTo"])
            )

            painter.save()

            clip = QPainterPath()

            clip.addRoundedRect(bar, radius, radius)

            painter.setClipPath(clip)

            painter.setBrush(gradient)

            painter.drawRect(fill)

            #
            # Ein Glanz auf der oberen Hälfte, wie im Artwork.
            #

            glow = QColor(tokens.SPLASH_ART["glow"])

            glow.setAlpha(70)

            painter.setBrush(glow)

            painter.drawRect(
                QRectF(
                    fill.left(),
                    fill.top(),
                    fill.width(),
                    fill.height() / 2,
                )
            )

            painter.restore()

        #
        # Zuletzt der Rahmen, damit er über Rinne und Füllung liegt.
        #

        painter.setBrush(Qt.NoBrush)

        pen = painter.pen()

        pen.setColor(QColor(tokens.SPLASH_ART["frame"]))

        pen.setWidthF(max(1.0, bar.height() * 0.12))

        painter.setPen(pen)

        painter.drawRoundedRect(bar, radius, radius)

    def _paint_status(self, painter: QPainter, band: QRectF):

        if band.height() <= 0:
            return

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QColor(tokens.SURFACE_EXTRA["splash"])
        )

        painter.drawRect(band)

        font = painter.font()

        font.setFamily("JetBrains Mono")

        size = max(9, int(band.height() * 0.52))

        font.setPixelSize(size)

        #
        # `AbsoluteSpacing` in Pixeln - dieselbe Schreibweise wie in
        # gui/theme/fonts.py. Die Aufzählung hängt an der Klasse, nicht
        # an der Instanz.
        #

        font.setLetterSpacing(QFont.AbsoluteSpacing, size * 0.1)

        painter.setFont(font)

        painter.setPen(
            QColor(tokens.TEXT["secondary"])
        )

        painter.drawText(
            band,
            Qt.AlignCenter,
            f"{self._status}   ·   v{VERSION}",
        )
