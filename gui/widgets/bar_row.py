"""
WeintCompanion 2.0
Die Balkenzeile

Der Baustein, an dem die Dichte von WeintTV hängt: **25 Zeilen ohne
Scrollen bei 1440 x 900**.

Bis 1.7 war eine Ranglistenzeile aus fünf Widgets zusammengesetzt -
Platz, Name, Spezialisierung, Wert und darunter ein eigener 4-px-Balken,
dazu 5 px Innenabstand und 12 px zwischen den Zeilen. Das ergibt rund
40 px je Zeile; 25 davon sind 1.000 px und passen in kein Fenster, das
900 px hoch ist. Sichtbar war das als Rangliste, die nach fünf
Einträgen aufhörte.

2.0 dreht das um: **der Balken ist nicht mehr unter der Zeile, er ist
die Zeile.** Die Klassenfarbe füllt den Zeilenhintergrund bei 22 %
Deckkraft, der Text steht darauf. Damit trägt dieselbe Fläche die
Information "wie viel" und "wer" - und die Zeile kommt mit 24 px aus.
Die Rechnung des Entwurfs geht auf: 25 x (24 + 2) = 650 px.

Ebenso bewusst: **der Text wird gemalt, nicht als QLabel gesetzt.** Ein
Zeilenwidget statt fünf bedeutet bei 25 Zeilen 25 Widgets statt 125,
und im `paintEvent` gibt es kein Stylesheet, das Qt neu berechnen
könnte. Bei laufender Wiedergabe (vier Bilder je Sekunde) ist das der
Unterschied zwischen flüssig und hakelig - dieselbe Überlegung, aus der
`gui/theme/restyle.py` entstanden ist.

Zwei Zustände, die der Entwurf ausdrücklich nennt:

- **Die eigene Zeile** wird hervorgehoben: Füllung 26 % statt 22 %,
  dazu eine 1-px-Innenkontur in Akzentfarbe und die Rangnummer in
  `accent.light`. Sie ist die eine Zeile, die der Nutzer sucht.
- **Ein toter Spieler** steht bei Deckkraft 0.55, und seine
  Spezialisierung weicht dem Todeszeitpunkt (`tot mm:ss`). Ihn ganz
  auszublenden wäre falsch - sein Schaden zählt, und *dass* er tot ist,
  ist die wichtigere Information.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.motion import curve, duration
from gui.theme.theme_manager import theme


#
# Deckkraft der Klassenfarbe im Zeilenhintergrund (§5).
#

FILL_ALPHA = 0.22

FILL_ALPHA_SELF = 0.26

SELF_OUTLINE_ALPHA = 0.45

DEAD_OPACITY = 0.55

#
# Spaltenbreiten. Der Rang ist einstellig bis 9 und zweistellig bis 25 -
# 16 px reichen für beides in `type.mono`.
#

RANK_WIDTH = 16

PADDING = 8


class BarRow(QWidget):
    """
    Eine Zeile einer Rangliste.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setFixedHeight(theme().metric("row", 24))

        self._rank = 0
        self._name = ""
        self._spec = ""
        self._value = ""
        self._color = tokens.TEXT["secondary"]
        self._is_self = False
        self._dead_at: int | None = None

        #
        # Der gezeichnete Anteil und der Zielanteil. Der Balken läuft
        # auf sein Ziel zu (motion.bar), der beschriftete Wert wird
        # sofort gesetzt - eine mitlaufende Zahl neben einem
        # mitlaufenden Balken liest sich als Flackern.
        #

        self._fraction = 0.0

        self._target = 0.0

        self._animation = None

        #
        # `self.update` als gebundener Slot und NICHT
        # `lambda _n: self.update()`: eine Lambda hält eine harte
        # Referenz auf `self`, und der ThemeManager ist ein Singleton,
        # der ewig lebt - das Widget würde damit nie mehr freigegeben.
        # Wird sein C++-Objekt trotzdem zerstört, weil ein Elternteil
        # abgebaut wird, feuert die Lambda in ein gelöschtes Objekt und
        # Qt meldet "Internal C++ object already deleted". Einen
        # gebundenen Slot trennt Qt beim Zerstören des Empfängers
        # selbst.
        #

        theme().accent_changed.connect(self.update)

        theme().density_changed.connect(self._on_density)

    # --------------------------------------------------

    def _on_density(self, _name: str):

        self.setFixedHeight(theme().metric("row", 24))

        self.update()

    # --------------------------------------------------

    def set_row(
        self,
        rank: int,
        name: str,
        spec: str,
        value: str,
        fraction: float,
        color: str,
        is_self: bool = False,
        dead_at: int | None = None,
        animate: bool = True,
    ):
        """
        Die Zeile beschriften.

        `fraction` ist der Anteil am besten Wert der Liste (0.0 - 1.0),
        `dead_at` der Todeszeitpunkt in Sekunden oder None.
        """

        self._rank = rank
        self._name = name
        self._spec = spec
        self._value = value
        self._color = color or tokens.TEXT["secondary"]
        self._is_self = is_self
        self._dead_at = dead_at

        self._set_fraction(
            max(0.0, min(1.0, float(fraction))),
            animate,
        )

        self.update()

    def _set_fraction(self, target: float, animate: bool):

        if target == self._target:
            return

        self._target = target

        ms = duration("bar") if animate else 0

        if ms <= 0:

            self._fraction = target

            return

        from PySide6.QtCore import QEasingCurve, QVariantAnimation

        #
        # **Eine** Animation je Zeile, wiederverwendet - nicht je
        # Aktualisierung eine neue. Ein `QVariantAnimation(self)`
        # gehört seinem Elternobjekt: die alte, gestoppte Animation
        # bliebe an der Zeile hängen, samt ihrer Verbindung auf
        # `_on_step`. Nachgemessen sammelten sich so nach 200
        # Aktualisierungen 199 Objekte an einer einzigen Zeile.
        # Sichtbar wäre das nie als Fehler - eine gestoppte Animation
        # meldet nichts mehr - sondern nur als Speicher, der während
        # einer Wiedergabe (4 Bilder je Sekunde, 25 Zeilen je Tabelle)
        # unbegrenzt wächst.
        #

        if self._animation is None:

            self._animation = QVariantAnimation(self)

            self._animation.valueChanged.connect(self._on_step)

        animation = self._animation

        animation.stop()

        animation.setDuration(ms)

        animation.setEasingCurve(QEasingCurve(curve("bar")))

        animation.setStartValue(float(self._fraction))

        animation.setEndValue(float(target))

        animation.start()

    def _on_step(self, value):

        self._fraction = float(value)

        self.update()

    # --------------------------------------------------

    @staticmethod
    def format_clock(seconds: int) -> str:

        seconds = max(0, int(seconds))

        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setRenderHint(QPainter.TextAntialiasing, True)

        if self._dead_at is not None:
            painter.setOpacity(DEAD_OPACITY)

        rect = QRectF(self.rect())

        radius = tokens.RADIUS["sm"]

        #
        # Rinne
        #

        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor(tokens.SURFACE["base"]))

        painter.drawRoundedRect(rect, radius, radius)

        #
        # Füllung in Klassenfarbe. Sie wird an der Rinne beschnitten,
        # damit ihre rechte Kante gerade bleibt statt gerundet - sonst
        # sähe ein Anteil von 30 % aus wie eine Pille, die zufällig
        # dort endet.
        #

        if self._fraction > 0.0:

            painter.save()

            painter.setClipRect(
                QRectF(
                    rect.left(),
                    rect.top(),
                    rect.width() * self._fraction,
                    rect.height(),
                )
            )

            painter.setBrush(self._fill_color())

            painter.drawRoundedRect(rect, radius, radius)

            painter.restore()

        #
        # Die eigene Zeile bekommt eine Innenkontur in Akzentfarbe.
        #

        if self._is_self:

            pen = QPen(
                QColor(
                    self._with_alpha(
                        theme().accent_base(),
                        SELF_OUTLINE_ALPHA,
                    )
                ),
                1,
            )

            painter.setPen(pen)

            painter.setBrush(Qt.NoBrush)

            painter.drawRoundedRect(
                rect.adjusted(0.5, 0.5, -0.5, -0.5),
                radius,
                radius,
            )

        #
        # Text
        #

        self._paint_text(painter, rect)

        painter.end()

    def _fill_color(self) -> QColor:

        return QColor(
            self._with_alpha(
                self._color,
                FILL_ALPHA_SELF if self._is_self else FILL_ALPHA,
            )
        )

    @staticmethod
    def _with_alpha(value: str, alpha: float) -> QColor:

        color = QColor(value)

        color.setAlphaF(alpha)

        return color

    def _paint_text(self, painter: QPainter, rect: QRectF):

        mono = font("mono")

        small = font("small")

        #
        # Rang
        #

        painter.setFont(mono)

        painter.setPen(
            QColor(
                theme().accent_light()
                if self._is_self
                else tokens.TEXT["muted"]
            )
        )

        painter.drawText(
            QRectF(rect.left() + PADDING, rect.top(), RANK_WIDTH, rect.height()),
            Qt.AlignRight | Qt.AlignVCenter,
            str(self._rank) if self._rank else "",
        )

        #
        # Wert, rechtsbündig. Er wird zuerst vermessen, damit der Name
        # weiß, wie viel Platz ihm bleibt - ein langer Name darf den
        # Wert nicht überschreiben.
        #

        value_width = QFontMetrics(mono).horizontalAdvance(self._value) + 4

        painter.setPen(QColor(tokens.WHITE))

        painter.drawText(
            QRectF(
                rect.right() - PADDING - value_width,
                rect.top(),
                value_width,
                rect.height(),
            ),
            Qt.AlignRight | Qt.AlignVCenter,
            self._value,
        )

        #
        # Name in Klassenfarbe, dahinter die Spezialisierung - oder,
        # wenn der Spieler gefallen ist, der Zeitpunkt.
        #

        left = rect.left() + PADDING + RANK_WIDTH + 10

        available = rect.right() - PADDING - value_width - left - 8

        if available <= 0:
            return

        name_font = font("small")

        name_font.setWeight(name_font.Weight.DemiBold)

        painter.setFont(name_font)

        metrics = QFontMetrics(name_font)

        name = metrics.elidedText(
            self._name,
            Qt.ElideRight,
            int(available),
        )

        name_width = metrics.horizontalAdvance(name)

        painter.setPen(QColor(self._color))

        painter.drawText(
            QRectF(left, rect.top(), name_width, rect.height()),
            Qt.AlignLeft | Qt.AlignVCenter,
            name,
        )

        trailing = (
            f"tot {self.format_clock(self._dead_at)}"
            if self._dead_at is not None
            else self._spec
        )

        if not trailing:
            return

        painter.setFont(small)

        painter.setPen(
            QColor(
                tokens.STATE_TEXT["error"]
                if self._dead_at is not None
                else tokens.TEXT["muted"]
            )
        )

        spec_left = left + name_width + 8

        spec_width = rect.right() - PADDING - value_width - spec_left - 8

        if spec_width <= 0:
            return

        painter.drawText(
            QRectF(spec_left, rect.top(), spec_width, rect.height()),
            Qt.AlignLeft | Qt.AlignVCenter,
            QFontMetrics(small).elidedText(
                trailing,
                Qt.ElideRight,
                int(spec_width),
            ),
        )
