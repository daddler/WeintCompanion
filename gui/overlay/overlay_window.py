"""
WeintCompanion 2.0
Overlay

Ein sehr kleines, immer sichtbares Fenster (§6.6, §7 Bausteine):
380 x 220, `WindowStaysOnTopHint`, Fläche `surface.sunken`, 1-px-Rahmen
`border.base`.

**Nur fünf Werte, keine Ranglisten** (§6.6): LIVE-Chip + Bossname,
Pull-Uhr groß (`type.mono` 40/700), Boss-Prozent (20/700, in
`state.error`-Text), ein Lebensbalken 8 px, und am Fuß `DEIN RANG` mit
Rang in Akzenthell plus dem eigenen Wert. Der Sinn dieses Fensters ist,
neben dem Spiel zu stehen, ohne den Blick zu binden - jeder sechste
Wert wäre schon zu viel.

Wie WeintTV und die Academy meldet sich das Overlay nur an, solange es
sichtbar ist (`showEvent`/`hideEvent` statt eines Lebenszeit-Attach),
und liest denselben `RaidSnapshot` wie alle anderen Ansichten - ein
Overlay, das eine eigene Zahl ausrechnet, könnte von WeintTV
abweichen.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label


WINDOW_SIZE = (380, 220)


class _HealthBar(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setFixedHeight(8)

        self._value = 1.0

    def setValue(self, value: float):

        value = max(0.0, min(1.0, float(value)))

        if value == self._value:
            return

        self._value = value

        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect())

        radius = rect.height() / 2.0

        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor(tokens.SURFACE["card"]))

        painter.drawRoundedRect(rect, radius, radius)

        if self._value <= 0:
            return

        painter.save()

        painter.setClipRect(
            QRectF(rect.left(), rect.top(), rect.width() * self._value, rect.height())
        )

        painter.setBrush(QColor(tokens.STATE["error"]))

        painter.drawRoundedRect(rect, radius, radius)

        painter.restore()


class OverlayWindow(QWidget):

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        self._attached = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setFixedSize(*WINDOW_SIZE)

        #
        # Eckige statt gerundete Ecken - bewusst, nicht aus Versehen.
        # Ein rahmenloses Top-Level-Fenster mit Eckenradius braucht
        # `WA_TranslucentBackground`, sonst bleiben die vier
        # Eckdreiecke außerhalb der Rundung auf manchen Compositorn als
        # schwarze Artefakte stehen. Das Hauptfenster (siehe
        # gui/main_window.py) löst dieselbe Lage genauso: echter
        # 1-px-Rahmen, keine Rundung.
        #

        self.setStyleSheet(
            f"""
            QWidget#overlayRoot{{
                background:{tokens.SURFACE["sunken"]};
                border:1px solid {tokens.BORDER["base"]};
            }}
            """
        )

        self.setObjectName("overlayRoot")

        root = QVBoxLayout(self)

        root.setContentsMargins(18, 16, 18, 16)

        root.setSpacing(tokens.SPACE[2])

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(8)

        self.live_chip = Chip("LIVE", "live", dot=True)

        header.addWidget(self.live_chip)

        self.boss_name = QLabel("Kein Kampf")

        self.boss_name.setFont(font("card"))

        restyle(self.boss_name, f"color:{tokens.WHITE};background:transparent;")

        header.addWidget(self.boss_name, 1)

        root.addLayout(header)

        root.addSpacing(tokens.SPACE[1])

        self.clock = QLabel("00:00")

        self.clock.setFont(font("monoBig"))

        restyle(self.clock, f"color:{tokens.WHITE};background:transparent;")

        root.addWidget(self.clock)

        self.percent = QLabel("—")

        percent_font = font("section")

        percent_font.setPixelSize(20)

        self.percent.setFont(percent_font)

        restyle(
            self.percent,
            f"color:{tokens.STATE_TEXT['error']};background:transparent;",
        )

        root.addWidget(self.percent)

        self.bar = _HealthBar()

        root.addWidget(self.bar)

        root.addStretch(1)

        footer = QHBoxLayout()

        footer.setContentsMargins(0, 0, 0, 0)

        footer.setSpacing(8)

        footer.addWidget(eyebrow_label("DEIN RANG"))

        self.rank_label = QLabel("—")

        self.rank_label.setFont(font("mono"))

        footer.addWidget(self.rank_label)

        footer.addStretch(1)

        self.value_label = QLabel("")

        self.value_label.setFont(font("mono"))

        restyle(
            self.value_label,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        footer.addWidget(self.value_label)

        root.addLayout(footer)

        self.service.snapshotChanged.connect(self._on_snapshot)

        #
        # Die Verbindung wird **hier** hergestellt und nicht in
        # `_apply_rank_color()`. Stünde sie dort, würde jeder
        # Akzentwechsel den Handler ausführen, der sich dabei ein
        # weiteres Mal verbindet - die Zahl der Verbindungen verdoppelt
        # sich dann bei jedem Wechsel (nachgemessen: 1, 2, 4, 8, 16).
        # Sichtbar wäre das erst spät und als reine Trägheit, nie als
        # Fehler.
        #

        theme().accent_changed.connect(self._on_accent_changed)

        self._apply_rank_color()

    # --------------------------------------------------

    def _on_accent_changed(self, _name: str):

        self._apply_rank_color()

    def _apply_rank_color(self):

        restyle(
            self.rank_label,
            f"color:{theme().accent_light()};background:transparent;",
        )

    # --------------------------------------------------

    def showEvent(self, event):

        super().showEvent(event)

        if not self._attached:

            self.service.attach()

            self._attached = True

            self._apply(self.service.current())

    def hideEvent(self, event):

        super().hideEvent(event)

        if self._attached:

            self.service.detach()

            self._attached = False

    def closeEvent(self, event):

        self.hideEvent(event)

        super().closeEvent(event)

    # --------------------------------------------------

    def _on_snapshot(self, snapshot):

        if not self.isVisible():
            return

        self._apply(snapshot)

    def _apply(self, snapshot):

        self.live_chip.setVisible(bool(snapshot.live) and snapshot.has_data)

        encounter = snapshot.encounter

        self.boss_name.setText(
            (encounter.name if encounter else "") or "Kein Kampf"
        )

        seconds = int(snapshot.pull_seconds or 0)

        self.clock.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

        if snapshot.has_data:

            percent = float(snapshot.boss_health_percent)

            self.percent.setText(f"{percent:.1f} %")

            self.bar.setValue(percent / 100.0)

        else:

            self.percent.setText("—")

            self.bar.setValue(0.0)

        self._apply_rank(snapshot)

    def _apply_rank(self, snapshot):

        from gui.widgets.bar_table import format_per_second

        me = self.manager.academy.player_name()

        for entries in (snapshot.top_damage, snapshot.top_healing):

            for index, entry in enumerate(entries):

                if entry.actor.name == me:

                    self.rank_label.setText(f"{index + 1} / {len(entries)}")

                    self.value_label.setText(format_per_second(entry.value))

                    return

        self.rank_label.setText("—")

        self.value_label.setText("")
