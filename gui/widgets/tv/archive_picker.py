"""
Umschalter zwischen Live-Feed und Archiv (vergangene WarcraftLogs-
Reports), gemeinsam genutzt von WeintTV und der Academy.

Das Widget kennt keine eigene Auswertungslogik - es liest
ausschließlich `RaidDataService.archive_state()` und ruft dessen
Methoden auf. Genau dieselbe Regel wie beim RaidSnapshot selbst: eine
Seite rechnet nichts, sie zeigt nur an. Weil beide Seiten hier
denselben Service ansprechen, sehen sie beim Blick ins Archiv immer
denselben Report/Pull - keine zwei Ansichten können auseinanderlaufen.

Aufbau: Live/Archiv-Umschalter, dahinter zwei Auswahlfelder (Bericht,
Pull), die nur im Archiv-Modus sichtbar sind, und eine kurze
Statuszeile für Ladezustand/Fehler.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from core.raid_data_service import ArchiveState, MODE_ARCHIVE, MODE_LIVE

from gui.theme.colors import Colors
from gui.widgets.segmented_control import SegmentedControl


class ArchivePicker(QWidget):

    def __init__(self, service, parent=None):

        super().__init__(parent)

        self.service = service

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(10)

        self.mode_switch = SegmentedControl([
            ("Live", MODE_LIVE),
            ("Archiv", MODE_ARCHIVE),
        ])

        self.mode_switch.valueChanged.connect(
            self._on_mode_changed
        )

        layout.addWidget(self.mode_switch)

        self.report_box = QComboBox()

        self.report_box.setMinimumWidth(200)

        self.report_box.currentIndexChanged.connect(
            self._on_report_changed
        )

        layout.addWidget(self.report_box)

        self.fight_box = QComboBox()

        self.fight_box.setMinimumWidth(220)

        self.fight_box.currentIndexChanged.connect(
            self._on_fight_changed
        )

        layout.addWidget(self.fight_box)

        self.status_label = QLabel("")

        self.status_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(self.status_label, 1)

        service.archiveChanged.connect(
            self._refresh
        )

        self._refresh()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _on_mode_changed(self, value: str):

        if value == MODE_LIVE:

            self.service.show_live()

        else:

            self.service.enter_archive_mode()

    def _on_report_changed(self, index: int):

        code = self.report_box.itemData(index)

        if code:

            self.service.select_archive_report(code)

    def _on_fight_changed(self, index: int):

        fight_id = self.fight_box.itemData(index)

        if fight_id is None:
            return

        state = self.service.archive_state()

        if state.selected_report:

            self.service.select_archive_fight(
                state.selected_report,
                fight_id,
            )

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _refresh(self):

        state = self.service.archive_state()

        self.mode_switch.blockSignals(True)

        self.mode_switch.setValue(state.mode)

        self.mode_switch.blockSignals(False)

        is_archive = state.mode == MODE_ARCHIVE

        self.report_box.setVisible(is_archive)

        self.fight_box.setVisible(is_archive)

        self.status_label.setVisible(is_archive)

        if not is_archive:
            return

        self._fill_reports(state)

        self._fill_fights(state)

        self._update_status(state)

    def _fill_reports(self, state: ArchiveState):

        self.report_box.blockSignals(True)

        self.report_box.clear()

        if state.reports_loading and not state.reports:

            self.report_box.addItem("Lädt Berichte ...", "")

            self.report_box.setEnabled(False)

        elif not state.reports:

            self.report_box.addItem("Keine Berichte gefunden", "")

            self.report_box.setEnabled(False)

        else:

            self.report_box.setEnabled(True)

            self.report_box.addItem("Bericht wählen ...", "")

            for report in state.reports:

                self.report_box.addItem(report.label, report.code)

            if state.selected_report:

                index = self.report_box.findData(state.selected_report)

                if index >= 0:
                    self.report_box.setCurrentIndex(index)

        self.report_box.blockSignals(False)

    def _fill_fights(self, state: ArchiveState):

        self.fight_box.blockSignals(True)

        self.fight_box.clear()

        has_report = bool(state.selected_report)

        self.fight_box.setEnabled(has_report and not state.fights_loading)

        if not has_report:

            self.fight_box.addItem("Erst einen Bericht wählen", None)

        elif state.fights_loading and not state.fights:

            self.fight_box.addItem("Lädt Pulls ...", None)

        elif not state.fights:

            self.fight_box.addItem("Keine Pulls gefunden", None)

        else:

            self.fight_box.addItem("Pull wählen ...", None)

            for fight in state.fights:

                self.fight_box.addItem(fight.label, fight.fight_id)

            if state.selected_fight is not None:

                index = self.fight_box.findData(state.selected_fight)

                if index >= 0:
                    self.fight_box.setCurrentIndex(index)

        self.fight_box.blockSignals(False)

    def _update_status(self, state: ArchiveState):

        reason = state.fight_error or state.fights_error or state.reports_error

        if reason:

            self.status_label.setText(reason)

            self.status_label.setStyleSheet(
                f"font-size:11px;color:{Colors.WARNING_LIGHT};"
            )

            return

        if state.fight_loading:
            text = "Lädt Pull ..."

        elif state.fights_loading:
            text = "Lädt Pulls ..."

        elif state.reports_loading:
            text = "Lädt Berichte ..."

        else:
            text = ""

        self.status_label.setText(text)

        self.status_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )
