"""
WeintCompanion 2.0
Meldungsstreifen

Kurze Einblendungen unten rechts **statt Dialogen**.

Ein modaler Dialog unterbricht: er nimmt die Eingabe an sich und
verlangt eine Bestätigung, bevor irgendetwas weitergeht. Für "Addon
aktualisiert" ist das die falsche Form - der Nutzer hat die Handlung
gerade selbst ausgelöst und braucht keine Rückfrage, sondern eine
Quittung. Und die Anwendung läuft neben einem Vollbildspiel: ein
Dialog, der den Fokus zieht, kann einen Pull kosten.

Zwei Standzeiten, und der Unterschied ist Absicht:

- **Erfolg und Hinweis verschwinden von selbst** (4 s). Sie tragen
  nichts, was man aufheben müsste.
- **Fehler bleiben bis zum Klick.** Eine Fehlermeldung, die von selbst
  geht, ist eine, die niemand gelesen hat - und genau die, deren Text
  man später bräuchte.

Die Rückgängig-Aktion ist der Grund, warum Erfolgsmeldungen überhaupt
eine Standzeit haben dürfen: sie macht die Meldung zum letzten
Zeitfenster für einen Widerruf, statt zu einer Vorab-Rückfrage.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.motion import TOAST_DWELL, curve, duration
from gui.theme.restyle import restyle
from gui.widgets.status_dot import StatusDot
from gui.widgets.wrapped_label import WrappedLabel


TOAST_WIDTH = 420

HOST_MARGIN = 24


class Toast(QWidget):
    """
    Eine einzelne Meldung.
    """

    dismissed = Signal(object)

    actionTriggered = Signal()

    def __init__(
        self,
        text: str,
        variant: str = "ok",
        action: str = "",
        parent=None,
    ):

        super().__init__(parent)

        self._variant = variant

        self.setFixedWidth(TOAST_WIDTH)

        self.setCursor(Qt.PointingHandCursor)

        root = QHBoxLayout(self)

        root.setContentsMargins(16, 12, 16, 12)

        root.setSpacing(10)

        self.dot = StatusDot(variant)

        root.addWidget(self.dot, alignment=Qt.AlignTop)

        column = QVBoxLayout()

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(4)

        self.label = WrappedLabel(text, TOAST_WIDTH - 90)

        self.label.setFont(font("small"))

        restyle(
            self.label,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        column.addWidget(self.label)

        self.action = QLabel(action.upper())

        self.action.setFont(font("micro"))

        self.action.setCursor(Qt.PointingHandCursor)

        self.action.setVisible(bool(action))

        restyle(
            self.action,
            f"color:{tokens.STATE_TEXT.get(variant, tokens.TEXT['secondary'])};"
            "background:transparent;",
        )

        column.addWidget(self.action)

        root.addLayout(column, 1)

        #
        # Fehler bleiben stehen, bis jemand sie wegklickt.
        #

        self._timer = QTimer(self)

        self._timer.setSingleShot(True)

        self._timer.timeout.connect(self.dismiss)

        self._effect = QGraphicsOpacityEffect(self)

        self.setGraphicsEffect(self._effect)

        self._animation = None

    # --------------------------------------------------

    def paintEvent(self, event):
        """
        Fläche `#121217` mit einer Oberkante in der Zustandsfarbe.

        Dieselbe Bauart wie bei `Card`: kein umlaufender Rahmen,
        sondern eine Kante, die als Licht gelesen wird - hier nur in
        der Farbe, die sagt, worum es geht.
        """

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()

        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor(tokens.SURFACE_EXTRA["toast"]))

        painter.drawRoundedRect(
            rect,
            tokens.RADIUS["lg"],
            tokens.RADIUS["lg"],
        )

        color = tokens.STATE.get(self._variant)

        if color is None:
            return

        painter.setPen(QColor(tokens.tint(color, 0.34)))

        inset = tokens.RADIUS["lg"] * 0.55

        painter.drawLine(
            int(rect.left() + inset),
            rect.top(),
            int(rect.right() - inset),
            rect.top(),
        )

    # --------------------------------------------------

    def show_toast(self):

        ms = duration("toast_in")

        self._effect.setOpacity(1.0 if ms <= 0 else 0.0)

        self.show()

        if ms > 0:

            start = self.pos()

            fade = QPropertyAnimation(self._effect, b"opacity", self)

            fade.setDuration(ms)

            fade.setEasingCurve(QEasingCurve(curve("toast_in")))

            fade.setStartValue(0.0)

            fade.setEndValue(1.0)

            slide = QPropertyAnimation(self, b"pos", self)

            slide.setDuration(ms)

            slide.setEasingCurve(QEasingCurve(curve("toast_in")))

            slide.setStartValue(QPoint(start.x(), start.y() + 8))

            slide.setEndValue(start)

            group = QParallelAnimationGroup(self)

            group.addAnimation(fade)

            group.addAnimation(slide)

            group.start()

            self._animation = group

        #
        # Kein Timer für Fehler: sie bleiben, bis geklickt wird.
        #

        if self._variant != "error":

            self._timer.start(TOAST_DWELL)

    def dismiss(self):

        ms = duration("toast_out")

        if ms <= 0:

            self.dismissed.emit(self)

            return

        fade = QPropertyAnimation(self._effect, b"opacity", self)

        fade.setDuration(ms)

        fade.setEasingCurve(QEasingCurve(curve("toast_out")))

        fade.setStartValue(self._effect.opacity())

        fade.setEndValue(0.0)

        fade.finished.connect(lambda: self.dismissed.emit(self))

        fade.start()

        self._animation = fade

    def mousePressEvent(self, event):

        if (
            self.action.isVisible()
            and self.action.geometry().contains(
                self.mapTo(self, event.position().toPoint())
            )
        ):

            self.actionTriggered.emit()

        self._timer.stop()

        self.dismiss()

        event.accept()


class ToastHost(QWidget):
    """
    Der Stapel unten rechts im Fenster.

    Er ist ein Kind des Fensters und **kein** eigenes Fenster: ein
    zweites Fenster erschiene in der Taskleiste, könnte den Fokus
    ziehen und läge auf manchen Compositorn falsch.
    """

    def __init__(self, parent):

        super().__init__(parent)

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self._toasts: list[Toast] = []

        parent.installEventFilter(self)

    # --------------------------------------------------

    def post(self, text: str, variant: str = "ok", action: str = ""):

        toast = Toast(text, variant, action, self.parentWidget())

        toast.dismissed.connect(self._remove)

        self._toasts.append(toast)

        self._reposition()

        toast.show_toast()

        toast.raise_()

        return toast

    def _remove(self, toast):

        if toast in self._toasts:
            self._toasts.remove(toast)

        toast.hide()

        toast.deleteLater()

        self._reposition()

    def _reposition(self):

        parent = self.parentWidget()

        if parent is None:
            return

        y = parent.height() - HOST_MARGIN

        #
        # Von unten nach oben stapeln: die neueste Meldung sitzt
        # unten, wo der Blick sie zuletzt gesehen hat.
        #

        for toast in reversed(self._toasts):

            toast.adjustSize()

            y -= toast.height()

            toast.move(
                parent.width() - TOAST_WIDTH - HOST_MARGIN,
                y,
            )

            y -= 8

    def eventFilter(self, watched, event):

        if event.type() == event.Type.Resize:
            self._reposition()

        return False
