"""
WeintCompanion 2.0
Der Kopfblock von WeintTV

**96 px für alles, was über den Ranglisten steht** (§6.2). Das ist keine
Sparsamkeit, sondern die Voraussetzung für das einzige harte Kriterium
dieser Ansicht.

Die Rechnung des Entwurfs: 900 px Fensterhöhe − 40 (Titelleiste) − 38
(Ränder) = 822 verfügbar. Davon nimmt dieser Kopf 96, für die
Ranglisten bleiben 660 - und 25 × (24 + 2) = 650 passen hinein.

Bis 1.7 stand hier eine Boss-Karte mit Symbol, Titel und Untertitel
(rund 150 px) und darunter vier Kennzahlkacheln (rund 100 px), dazu
Abstände: zusammen über 300 px, bevor die erste Ranglistenzeile beginnt.
Deshalb passten dort nur fünf Plätze.

Die Kennzahlen sind nicht verschwunden, sie sind **in den Kopf
gerückt**: Tode, Kampf-Rezz und Heldentum stehen als Chips neben dem
Bossnamen. Eine Zahl, die man im Vorbeisehen braucht, verlangt keine
eigene Kachel mit Rubrik und Fußzeile.

Rechts, hinter einer 1-px-Senkrechten, die Pull-Uhr in `type.monoBig` -
der einzige Wert dieser Ansicht, der groß sein muss, weil man ihn aus
zwei Metern Entfernung auf dem zweiten Bildschirm ablesen können soll.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label


HEADER_HEIGHT = 96

BOSS_BAR_HEIGHT = 16

CLOCK_WIDTH = 148


class BossBar(QWidget):
    """
    Der Bosslebensbalken, 16 px.

    Mit einer 2 px breiten weißen Marke an der Kante der Füllung: sie
    macht den Fortschritt auch dann ablesbar, wenn sich der Balken nur
    langsam bewegt, und markiert bei Bedarf den besten Versuch.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setFixedHeight(BOSS_BAR_HEIGHT)

        self._value = 1.0

        self._best: float | None = None

    def setValue(self, value: float):

        value = max(0.0, min(1.0, float(value)))

        if value == self._value:
            return

        self._value = value

        self.update()

    def setBest(self, value: float | None):

        if value == self._best:
            return

        self._best = value

        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect())

        radius = rect.height() / 2.0

        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor(tokens.SURFACE["card"]))

        painter.drawRoundedRect(rect, radius, radius)

        if self._value <= 0.0:
            return

        width = rect.width() * self._value

        painter.save()

        painter.setClipRect(
            QRectF(rect.left(), rect.top(), width, rect.height())
        )

        gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)

        gradient.setColorAt(0.0, QColor(tokens.STATE["error"]))
        gradient.setColorAt(1.0, QColor(tokens.STATE_TEXT["error"]))

        painter.setBrush(gradient)

        painter.drawRoundedRect(rect, radius, radius)

        painter.restore()

        #
        # Die Marke an der Kante.
        #

        painter.setBrush(QColor(tokens.WHITE))

        painter.drawRect(
            QRectF(
                max(rect.left(), width - 2.0),
                rect.top(),
                2.0,
                rect.height(),
            )
        )


class LiveHeader(QFrame):
    """
    Der ganze Kopfblock.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setFixedHeight(HEADER_HEIGHT)

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[4])

        #
        # Links: Boss, Zustand, Balken
        #

        left = QVBoxLayout()

        left.setContentsMargins(0, 0, 0, 0)

        left.setSpacing(6)

        title_row = QHBoxLayout()

        title_row.setContentsMargins(0, 0, 0, 0)

        title_row.setSpacing(tokens.SPACE[1])

        self.live_chip = Chip("LIVE", "live", dot=True)

        title_row.addWidget(self.live_chip)

        self.boss_name = QLabel("Kein Kampf")

        self.boss_name.setFont(font("section"))

        restyle(
            self.boss_name,
            f"color:{tokens.WHITE};background:transparent;",
        )

        title_row.addWidget(self.boss_name)

        self.context = eyebrow_label("")

        title_row.addWidget(self.context)

        title_row.addStretch(1)

        #
        # Die Kennzahlen, die bis 1.7 vier eigene Kacheln brauchten.
        #

        self.chip_deaths = Chip("0 TODE", "neutral")

        title_row.addWidget(self.chip_deaths)

        self.chip_battle_res = Chip("REZZ 0/0", "neutral")

        title_row.addWidget(self.chip_battle_res)

        self.chip_heroism = Chip("HELDENTUM", "neutral")

        title_row.addWidget(self.chip_heroism)

        self.pull_chip = Chip("PULL 1", "accent")

        title_row.addWidget(self.pull_chip)

        left.addLayout(title_row)

        self.bar = BossBar()

        left.addWidget(self.bar)

        foot = QHBoxLayout()

        foot.setContentsMargins(0, 0, 0, 0)

        foot.setSpacing(tokens.SPACE[2])

        self.percent = QLabel("—")

        self.percent.setFont(font("mono"))

        restyle(
            self.percent,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        foot.addWidget(self.percent)

        self.best = QLabel("")

        self.best.setFont(font("small"))

        restyle(
            self.best,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        foot.addWidget(self.best)

        foot.addStretch(1)

        left.addLayout(foot)

        root.addLayout(left, 1)

        #
        # Rechts: die Pull-Uhr, abgesetzt durch eine 1-px-Senkrechte.
        #

        divider = QFrame()

        divider.setFixedWidth(1)

        divider.setStyleSheet(
            f"background:{tokens.SURFACE['raised']};border:none;"
        )

        root.addWidget(divider)

        clock = QVBoxLayout()

        clock.setContentsMargins(0, 0, 0, 0)

        clock.setSpacing(0)

        clock.addWidget(eyebrow_label("PULL-UHR"))

        self.clock = QLabel("00:00")

        self.clock.setFont(font("monoBig"))

        self.clock.setFixedWidth(CLOCK_WIDTH)

        restyle(
            self.clock,
            f"color:{tokens.WHITE};background:transparent;",
        )

        clock.addWidget(self.clock)

        self.clock_note = QLabel("")

        self.clock_note.setFont(font("small"))

        restyle(
            self.clock_note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        clock.addWidget(self.clock_note)

        clock.addStretch(1)

        root.addLayout(clock)

    # --------------------------------------------------

    def apply(self, snapshot):
        """
        Den Kopf aus einem Snapshot beschriften.
        """

        has_data = snapshot.has_data

        #
        # Der LIVE-Chip ist die einzige Pulsquelle dieser Ansicht.
        # Sichtbar nur, wenn die Quelle wirklich live ist - eine
        # Wiedergabe oder das Archiv pulsen nicht, sonst behauptete
        # das Zeichen etwas, das nicht stimmt.
        #

        self.live_chip.setVisible(bool(snapshot.live) and has_data)

        #
        # Boss, Instanz und Schwierigkeit stehen in `encounter` und
        # nicht flach am Snapshot - ohne laufenden Kampf ist es None.
        #

        encounter = snapshot.encounter

        self.boss_name.setText(
            (encounter.name if encounter else "") or "Kein Kampf"
        )

        parts = []

        if encounter:

            parts = [
                encounter.instance,
                encounter.difficulty,
                f"{encounter.raid_size}" if encounter.raid_size else "",
            ]

        self.context.setText(
            " · ".join(part for part in parts if part).upper()
        )

        if not has_data:

            self.bar.setValue(0.0)

            self.percent.setText("—")

        else:

            percent = float(snapshot.boss_health_percent)

            self.bar.setValue(percent / 100.0)

            self.percent.setText(f"{percent:.1f} %")

        deaths = len(snapshot.deaths or ())

        self.chip_deaths.setText(f"{deaths} TODE")

        self.chip_deaths.setVariant("error" if deaths else "neutral")

        self.chip_battle_res.setText(
            f"REZZ {snapshot.battle_res_charges}/{snapshot.battle_res_max}"
        )

        #
        # Heldentum: "läuft" solange Restzeit anliegt, danach
        # "genutzt" - und vorher schlicht "bereit". Drei Zustände, drei
        # Farben, aber nie rot: ein nicht genutztes Heldentum ist kein
        # Fehler.
        #

        if snapshot.heroism_remaining > 0:

            self.chip_heroism.setText(
                f"HELDENTUM {int(snapshot.heroism_remaining)}s"
            )

            self.chip_heroism.setVariant("ok")

        elif snapshot.heroism_used:

            self.chip_heroism.setText("HELDENTUM GENUTZT")

            self.chip_heroism.setVariant("neutral")

        else:

            self.chip_heroism.setText("HELDENTUM BEREIT")

            self.chip_heroism.setVariant("info")

        self.pull_chip.setText(
            f"PULL {snapshot.pull_number}"
            if snapshot.pull_number
            else "PULL —"
        )

        seconds = int(snapshot.pull_seconds or 0)

        self.clock.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

    def set_best_attempt(self, percent: float | None):
        """
        Der beste Versuch dieser Sitzung, als Fußnote unter dem
        Prozentwert.
        """

        self.best.setText(
            f"Bester Versuch {percent:.1f} %"
            if percent is not None
            else ""
        )
