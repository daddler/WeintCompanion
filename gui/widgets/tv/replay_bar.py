"""
Steuerleiste der Wiedergabe, gemeinsam genutzt von WeintTV und der
Academy.

Wie der ArchivePicker kennt dieses Widget keine eigene Logik: es liest
`RaidDataService.replay_state()` und ruft dessen Methoden auf. Weil
beide Seiten denselben Service ansprechen, zeigen sie während einer
Wiedergabe immer dieselbe Sekunde - dieselbe Begründung, aus der sie
sich schon den Live-Snapshot teilen.

Genau das ist der Sinn der `compact`-Variante in der Academy: dort
soll man die Wiedergabe bedienen können, ohne dass die Seite zur
Fernbedienung wird. Die Geschwindigkeitswahl bleibt WeintTV
vorbehalten.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from core.raid_data_service import MODE_REPLAY, REPLAY_SPEEDS

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.timer_chip import TimerChip


#
# Auflösung des Schiebereglers. Er arbeitet in ganzen Zehntelsekunden
# statt in Sekunden, damit auch ein kurzer Pull noch fein genug
# angesteuert werden kann.
#

SLIDER_STEPS_PER_SECOND = 10


class ReplayBar(QWidget):

    def __init__(self, service, compact: bool = False, parent=None):

        super().__init__(parent)

        self.service = service

        self._compact = compact

        #
        # Solange der Nutzer den Regler festhält, darf der Takt der
        # Wiedergabe ihn nicht unter der Maus wegziehen.
        #

        self._seeking = False

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(10)

        self.play_button = HeroButton("Pause")

        self.play_button.clicked.connect(
            self.service.toggle_replay
        )

        layout.addWidget(self.play_button)

        self.slider = QSlider(Qt.Horizontal)

        self.slider.setMinimum(0)

        self.slider.setMaximum(100)

        self.slider.sliderPressed.connect(self._on_slider_pressed)

        self.slider.sliderReleased.connect(self._on_slider_released)

        self.slider.valueChanged.connect(self._on_slider_moved)

        layout.addWidget(self.slider, 1)

        self.clock_chip = TimerChip("00:00 / 00:00", state="primary")

        self.clock_chip.setMinimumWidth(124)

        layout.addWidget(self.clock_chip)

        self.speed_switch = SegmentedControl([
            (f"{int(speed)}x", speed)
            for speed in REPLAY_SPEEDS
        ])

        self.speed_switch.valueChanged.connect(
            self.service.set_replay_speed
        )

        self.speed_switch.setVisible(not compact)

        layout.addWidget(self.speed_switch)

        self.stop_button = HeroButton("Beenden", primary=False)

        self.stop_button.clicked.connect(
            self.service.stop_replay
        )

        layout.addWidget(self.stop_button)

        self.status_label = QLabel("")

        self.status_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        layout.addWidget(self.status_label)

        service.replayChanged.connect(self._refresh)

        service.archiveChanged.connect(self._refresh)

        self._refresh()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _on_slider_pressed(self):

        self._seeking = True

    def _on_slider_released(self):

        self._seeking = False

        self._seek_to(self.slider.value())

    def _on_slider_moved(self, value: int):
        """
        Auch während des Ziehens springen, nicht erst beim Loslassen -
        sonst sieht man beim Suchen einer Stelle nichts.
        """

        if self._seeking:

            self._seek_to(value)

    def _seek_to(self, value: int):

        self.service.seek_replay(value / SLIDER_STEPS_PER_SECOND)

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _refresh(self):

        state = self.service.replay_state()

        replaying = (
            self.service.archive_state().mode == MODE_REPLAY
        )

        #
        # Außerhalb der Wiedergabe verschwindet die Leiste vollständig
        # statt nur ausgegraut zu werden - eine Steuerung ohne etwas
        # zu steuern ist nur Rauschen.
        #

        self.setVisible(replaying or bool(state.error))

        if not replaying:

            self.status_label.setText(state.error)

            self.status_label.setVisible(bool(state.error))

            for widget in (
                self.play_button,
                self.slider,
                self.clock_chip,
                self.speed_switch,
                self.stop_button,
            ):
                widget.setVisible(False)

            return

        for widget in (
            self.play_button,
            self.slider,
            self.clock_chip,
            self.stop_button,
        ):
            widget.setVisible(True)

        self.speed_switch.setVisible(not self._compact)

        self.play_button.setText(
            "Pause"
            if state.playing
            else "Abspielen"
        )

        self.clock_chip.setValue(
            f"{state.clock} / {state.total_clock}",
            "primary" if state.playing else "neutral",
        )

        if not self._seeking:

            self.slider.blockSignals(True)

            self.slider.setMaximum(
                max(1, int(state.duration * SLIDER_STEPS_PER_SECOND))
            )

            self.slider.setValue(
                int(state.position * SLIDER_STEPS_PER_SECOND)
            )

            self.slider.blockSignals(False)

        self.speed_switch.blockSignals(True)

        self.speed_switch.setValue(state.speed)

        self.speed_switch.blockSignals(False)

        self.status_label.setText(state.error)

        self.status_label.setVisible(bool(state.error))
