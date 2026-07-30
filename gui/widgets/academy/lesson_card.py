"""
Karte einer Lektion des Trainingsplans.

Baut auf der bestehenden Card auf (gui/widgets/card.py), damit
Rahmen, Radius und Innenabstände identisch zu allen anderen Karten
der Anwendung sind. Die erste Lektion des Plans wird als "nächste"
hervorgehoben - dafür genügt der bereits vorhandene
Akzent-Rahmen von Card(accent=True).

Seit der automatischen Prüfung trägt die Karte zusätzlich das
Ergebnis aus dem gewählten Log: erfüllt, nicht erfüllt oder keine
Daten, jeweils mit dem gemessenen Wert gegen das Ziel. Der
Erledigt-Schalter bleibt daneben bestehen - er ist die Angabe des
Spielers, das Ergebnis die Evidenz aus dem Log. Beides ineinander zu
überführen würde entweder den selbst gesetzten Haken zerstören oder
eine Behauptung aufstellen, die aus einem Pull nicht folgt.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from analyzer.academy.models import (
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNKNOWN,
    Lesson,
    LessonResult,
)

from gui.theme.colors import Colors
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.tv.timer_chip import TimerChip


#
# Prüfergebnis auf die Zustandsfarben der TimerChip abbilden - "keine
# Daten" ist bewusst neutral und nicht rot: es ist kein Fehler des
# Spielers, wenn die Datenquelle etwas nicht liefert.
#

STATUS_STATES = {
    STATUS_PASSED: "success",
    STATUS_FAILED: "error",
    STATUS_UNKNOWN: "neutral",
}


class LessonCard(Card):

    #
    # (lesson_id, erledigt)
    #

    completedChanged = Signal(str, bool)

    #
    # Sekunde im Kampf, an der ein Befund festgemacht ist - der
    # Sprung in die Wiedergabe.
    #

    momentRequested = Signal(float)

    def __init__(
        self,
        lesson: Lesson,
        completed: bool = False,
        highlight: bool = False,
        result: LessonResult | None = None,
        parent=None,
    ):

        super().__init__(accent=highlight, parent=parent)

        self.lesson = lesson

        self.result = result

        #
        # --------------------------------------------------
        # Kopfzeile
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(10)

        title_col = QVBoxLayout()

        title_col.setSpacing(4)

        eyebrow_text = lesson.category_label.upper()

        if highlight:

            eyebrow_text = f"NÄCHSTE LEKTION · {eyebrow_text}"

        eyebrow = eyebrow_label(
            eyebrow_text,
            Colors.PRIMARY_HOVER if highlight else Colors.TEXT_MUTED,
        )

        title_col.addWidget(eyebrow)

        title = QLabel(lesson.title)

        title.setWordWrap(True)

        title.setStyleSheet(
            f"font-size:15px;font-weight:600;color:{Colors.WHITE};"
            "background:transparent;border:none;"
        )

        title_col.addWidget(title)

        header.addLayout(title_col, 1)

        #
        # Erledigt-Schalter
        #

        done_col = QVBoxLayout()

        done_col.setSpacing(4)

        done_label = QLabel("Erledigt")

        done_label.setAlignment(Qt.AlignRight)

        done_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        done_col.addWidget(done_label)

        toggle_row = QHBoxLayout()

        toggle_row.setContentsMargins(0, 0, 0, 0)

        toggle_row.addStretch()

        self.toggle = ToggleSwitch(completed)

        self.toggle.toggled.connect(
            self._on_toggled
        )

        toggle_row.addWidget(self.toggle)

        done_col.addLayout(toggle_row)

        header.addLayout(done_col)

        self.addLayout(header)

        #
        # --------------------------------------------------
        # Ergebnis der automatischen Prüfung
        # --------------------------------------------------
        #
        # Bewusst getrennt vom Erledigt-Schalter: das eine ist die
        # Evidenz aus dem Log, das andere die eigene Angabe. Sie
        # ineinander zu überführen würde entweder den selbst
        # gesetzten Haken zerstören oder eine Behauptung über das
        # Können des Spielers aufstellen, die aus einem Pull nicht
        # folgt.
        #

        if result is not None and lesson.is_measurable:

            self._add_result(result)

        #
        # --------------------------------------------------
        # Beschreibung
        # --------------------------------------------------
        #

        summary = QLabel(lesson.summary)

        summary.setWordWrap(True)

        summary.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        self.addWidget(summary)

        #
        # --------------------------------------------------
        # Schritte
        # --------------------------------------------------
        #

        if lesson.steps:

            steps = QWidget()

            steps_layout = QVBoxLayout(steps)

            steps_layout.setContentsMargins(0, 0, 0, 0)

            steps_layout.setSpacing(6)

            for number, step in enumerate(lesson.steps, start=1):

                row = QHBoxLayout()

                row.setContentsMargins(0, 0, 0, 0)

                row.setSpacing(10)

                marker = QLabel(f"{number}")

                marker.setFixedWidth(16)

                marker.setAlignment(Qt.AlignTop)

                marker.setStyleSheet(
                    'font-family:"JetBrains Mono";'
                    f"font-size:11px;color:{Colors.PRIMARY_HOVER};"
                    "background:transparent;border:none;"
                )

                row.addWidget(marker)

                text = QLabel(step)

                text.setWordWrap(True)

                text.setStyleSheet(
                    f"font-size:12px;color:{Colors.TEXT_SECONDARY};"
                    "background:transparent;border:none;"
                )

                row.addWidget(text, 1)

                steps_layout.addLayout(row)

            self.addWidget(steps)

    # --------------------------------------------------

    def _add_result(self, result: LessonResult):

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(10)

        state = STATUS_STATES.get(result.status, "neutral")

        chip = TimerChip(result.label.upper(), state)

        row.addWidget(chip)

        detail = QLabel(
            " · ".join(
                entry.detail
                for entry in result.checks
                if entry.detail
            )
        )

        detail.setWordWrap(True)

        detail.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        row.addWidget(detail, 1)

        #
        # Der Sprung in die Wiedergabe erscheint nur, wenn sich der
        # Befund tatsächlich an einer Sekunde festmachen lässt.
        #

        if result.at_seconds >= 0:

            jump = HeroButton("Im Replay ansehen", primary=False)

            jump.clicked.connect(
                lambda: self.momentRequested.emit(result.at_seconds)
            )

            row.addWidget(jump)

        self.addLayout(row)

    def _on_toggled(self, checked: bool):

        self.completedChanged.emit(
            self.lesson.lesson_id,
            checked,
        )

    def setCompleted(self, completed: bool):
        """
        Zustand ohne erneutes Auslösen des Signals setzen - genau das
        Muster, das die Settings-Abschnitte in ihrem refresh()
        verwenden.
        """

        self.toggle.blockSignals(True)

        self.toggle.setChecked(completed)

        self.toggle.blockSignals(False)
