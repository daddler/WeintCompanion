"""
WeintCompanion 2.0
Aufstellungsstreifen

Die Zusagen als Plätze: je Rolle eine Reihe kleiner Kästchen,
gefüllte in Klassenfarbe, offene als dunkle Lücke. Genau so stand die
Aufstellung im Entwurf der Übersicht - und sie beantwortet die Frage,
wegen der man sonst ins Discord sieht: nicht *wie viele* zugesagt
haben, sondern **was noch fehlt**.

Drei Entscheidungen, die dabei zählen:

- **Gemalt statt gebaut.** Fünfundzwanzig Kästchen als
  fünfundzwanzig Widgets wären fünfundzwanzig Layoutobjekte, die bei
  jeder Änderung der Anmeldung neu entstehen. Ein `paintEvent` malt
  sie in einem Zug, und die Farbe wird dabei **im Malen** aus dem
  Theme gelesen, nicht im Konstruktor - sonst behielte der Streifen
  seine Akzentfarbe über einen Themenwechsel hinweg (siehe die Notiz
  zu den drei Themensignalen in CLAUDE.md).
- **Der Streifen schrumpft, er bricht nicht um.** Wird das Fenster
  schmal, werden die Kästchen schmaler statt in eine zweite Zeile zu
  rutschen: die Reihe ist ein Balken, kein Text.
- **Eine leere Klasse ist kein Fehler.** Meldet der Bot nur Zahlen je
  Rolle und keine Klassen, sind die gefüllten Plätze in Akzentfarbe -
  die Aufstellung stimmt, nur das Bild ist ärmer. Eine geratene
  Klasse wäre in der Farbe von einer gemeldeten nicht zu
  unterscheiden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.theme_manager import theme
from gui.theme.wow_colors import class_color


#
# Maße des Entwurfs. `SLOT_WIDTH` ist die Obergrenze - schmaler wird
# der Streifen von selbst, breiter nie, sonst wüchsen die Kästchen bei
# einem Zehnerraid zu Balken.
#

SLOT_WIDTH = 9.0

SLOT_HEIGHT = 26.0

SLOT_GAP = 4.0

GROUP_GAP = 20.0

LABEL_HEIGHT = 13.0

LABEL_GAP = 6.0

MIN_SLOT_WIDTH = 3.0

#
# Der Abstand zwischen zwei Reihen hat eine Untergrenze, die Kästchen
# nicht: unterschritten würde er von den Rubriken darüber, und
# "HEILERSCHADEN" ist schlimmer als ein paar Pixel schmalere Plätze.
#

MIN_GROUP_GAP = 8.0


@dataclass
class SlotGroup:
    """
    Eine Rolle: Beschriftung, gefüllte Plätze, offene Plätze.

    `filled` trägt je Platz einen Klassennamen (englisch, wie in
    `wow_colors`) oder "" für "Klasse nicht gemeldet".
    """

    label: str = ""

    filled: list[str] = field(default_factory=list)

    open_slots: int = 0


class RosterStrip(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self._groups: list[SlotGroup] = []

        self.setFixedHeight(int(LABEL_HEIGHT + LABEL_GAP + SLOT_HEIGHT))

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        #
        # Gebundener Slot, keine Lambda: der ThemeManager ist ein
        # Singleton und hielte den Streifen sonst für immer fest.
        #

        theme().accent_changed.connect(self.update)

    # --------------------------------------------------

    def setGroups(self, groups):
        """
        Die Reihen setzen. Gleicher Inhalt heißt kein Neuzeichnen -
        die Übersicht ruft `refresh()` bei jedem Seitenwechsel und bei
        jeder abgeschlossenen Prüfung auf.
        """

        groups = list(groups or [])

        if groups == self._groups:
            return

        self._groups = groups

        self.update()

    def groups(self) -> list[SlotGroup]:

        return list(self._groups)

    def is_empty(self) -> bool:

        return not any(
            len(group.filled) + group.open_slots
            for group in self._groups
        )

    # --------------------------------------------------

    def _layout(self, metrics: QFontMetricsF):
        """
        Kästchenbreite, Abstände und die Breite je Reihe.

        Eine Reihe ist nie schmaler als ihre eigene Rubrik: zwei Tanks
        sind 22 px, "TANKS" ist mehr als das Doppelte davon, und ohne
        diese Untergrenze schob sich die Beschriftung der nächsten
        Reihe in die vorige ("TANKSHEILER").

        Wird es eng, schrumpfen die Kästchen - die Rubriken nicht, sie
        wären sonst als erstes unlesbar. Deshalb lässt sich die
        Stauchung nicht als einfaches Verhältnis ausrechnen, und
        deshalb wird sie in wenigen Stufen gesucht statt gelöst: die
        Rechnung ist ein Dutzend Multiplikationen, die Formel dafür
        wäre eine Fallunterscheidung je Reihe.
        """

        counts = [
            len(group.filled) + group.open_slots
            for group in self._groups
        ]

        labels = [
            metrics.horizontalAdvance(group.label) if group.label else 0.0
            for group in self._groups
        ]

        available = max(1.0, float(self.width()))

        def measure(factor: float):

            slot = max(MIN_SLOT_WIDTH, SLOT_WIDTH * factor)

            gap = SLOT_GAP * factor

            group_gap = max(MIN_GROUP_GAP, GROUP_GAP * factor)

            widths = [
                max(
                    count * (slot + gap) - gap if count else 0.0,
                    label,
                )
                for count, label in zip(counts, labels)
            ]

            total = sum(widths) + group_gap * max(0, len(widths) - 1)

            return slot, gap, group_gap, widths, total

        steps = 12

        result = measure(1.0)

        for step in range(steps + 1):

            result = measure(1.0 - step / steps)

            if result[4] <= available:
                break

        return result[:4]

    # --------------------------------------------------

    def paintEvent(self, event):

        if not self._groups:
            return

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        label_font = font("micro")

        metrics = QFontMetricsF(label_font)

        slot_width, slot_gap, group_gap, widths = self._layout(metrics)

        top = LABEL_HEIGHT + LABEL_GAP

        accent = QColor(theme().accent_base())

        empty = QColor(tokens.SURFACE["raised"])

        x = 0.0

        for group, width in zip(self._groups, widths):

            count = len(group.filled) + group.open_slots

            if count <= 0:
                continue

            #
            # Die Rubrik sitzt über ihrer eigenen Reihe. Sie bekommt
            # dort so viel Platz, wie sie braucht - die Reihe ist
            # notfalls dafür breiter (siehe `_layout`).
            #

            if group.label:

                painter.setFont(label_font)

                painter.setPen(QColor(tokens.TEXT["faint"]))

                painter.drawText(
                    QRectF(x, 0.0, width, LABEL_HEIGHT),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    group.label,
                )

            painter.setPen(Qt.NoPen)

            for index in range(count):

                rect = QRectF(
                    x + index * (slot_width + slot_gap),
                    top,
                    slot_width,
                    SLOT_HEIGHT,
                )

                if index < len(group.filled):

                    name = group.filled[index]

                    painter.setBrush(
                        QColor(class_color(name)) if name else accent
                    )

                else:

                    painter.setBrush(empty)

                painter.drawRoundedRect(rect, 2.0, 2.0)

            x += width + group_gap
