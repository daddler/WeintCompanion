from PySide6.QtWidgets import QLabel, QVBoxLayout

from core.autostart import Autostart

from gui.theme.colors import Colors
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.toggle_switch import ToggleSwitch

from ._common import SectionContent, toggle_row


class GeneralSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · ALLGEMEIN",
            "Allgemein",
            "Grundlegendes Verhalten des Companions.",
        )

        self.manager = manager

        #
        # Automatische Synchronisation (echt, config.auto_sync)
        #

        self.auto_sync_toggle = ToggleSwitch()

        self.auto_sync_toggle.toggled.connect(
            self._save_auto_sync
        )

        self.addRow(
            toggle_row(
                "Automatische Synchronisation aktivieren",
                "Companion läuft still im Hintergrund und syncht weiter.",
                self.auto_sync_toggle,
            )
        )

        #
        # Sync-Intervall (echt, config.sync_interval)
        #

        interval_col = QVBoxLayout()

        interval_col.setSpacing(10)

        interval_label = QLabel("Sync-Intervall")

        interval_label.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        interval_col.addWidget(interval_label)

        interval_desc = QLabel(
            "Wie oft der Companion automatisch synchronisiert."
        )

        interval_desc.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        interval_col.addWidget(interval_desc)

        self.interval_control = SegmentedControl([
            ("1s", 1),
            ("5s", 5),
            ("15s", 15),
            ("30s", 30),
        ])

        self.interval_control.valueChanged.connect(
            self._save_interval
        )

        interval_col.addWidget(self.interval_control)

        self.addRow(interval_col)

        #
        # Beim Systemstart öffnen (echt, Windows-Registry bzw.
        # XDG-Autostart unter Linux)
        #

        self.autostart_toggle = ToggleSwitch()

        self.autostart_toggle.toggled.connect(
            self._save_autostart
        )

        self.addRow(
            toggle_row(
                "Beim Systemstart öffnen",
                "Startet WeintCompanion automatisch, sobald du dich anmeldest.",
                self.autostart_toggle,
            )
        )

        #
        # In Tray minimieren (echt, config.minimize_to_tray)
        #

        self.tray_toggle = ToggleSwitch()

        self.tray_toggle.toggled.connect(
            self._save_minimize_to_tray
        )

        self.addRow(
            toggle_row(
                "In Tray minimieren",
                "Companion bleibt beim Schließen/Minimieren im "
                "System-Tray aktiv, statt sich zu beenden.",
                self.tray_toggle,
            )
        )

        #
        # Telemetrie senden (kein Backend - deaktiviert)
        #

        self.addRow(
            toggle_row(
                "Telemetrie senden",
                "Geplant - es werden aktuell keine Nutzungsdaten erfasst.",
                self._disabled_toggle(),
                enabled=False,
            ),
            divider=False,
        )

        self.refresh()

    def _disabled_toggle(self):

        toggle = ToggleSwitch(checked=False)

        toggle.setEnabled(False)

        return toggle

    # --------------------------------------------------

    def refresh(self):

        config = self.manager.config

        self.auto_sync_toggle.blockSignals(True)
        self.auto_sync_toggle.setChecked(
            config.data.get("auto_sync", True)
        )
        self.auto_sync_toggle.blockSignals(False)

        self.interval_control.setValue(
            config.data.get("sync_interval", 5)
        )

        #
        # Autostart: tatsächlicher Registry-/Autostart-Zustand ist
        # die Wahrheit (nicht nur der zuletzt gespeicherte Wunsch) -
        # so bleibt der Schalter korrekt, auch wenn der Eintrag von
        # außerhalb entfernt wurde.
        #

        self.autostart_toggle.blockSignals(True)
        self.autostart_toggle.setChecked(
            Autostart.is_enabled()
        )
        self.autostart_toggle.blockSignals(False)

        self.tray_toggle.blockSignals(True)
        self.tray_toggle.setChecked(
            config.data.get("minimize_to_tray", False)
        )
        self.tray_toggle.blockSignals(False)

    # --------------------------------------------------

    def _save_auto_sync(self, checked: bool):

        self.manager.config.data["auto_sync"] = checked

        self.manager.config.save()

        if checked:

            self.manager.start_auto_sync()

        else:

            self.manager.stop_auto_sync()

    def _save_interval(self, value: int):

        self.manager.config.data["sync_interval"] = value

        self.manager.config.save()

        if self.manager.config.data.get("auto_sync", True):

            self.manager.stop_auto_sync()
            self.manager.start_auto_sync()

    def _save_autostart(self, checked: bool):

        success = Autostart.set_enabled(checked)

        if not success:

            self.manager.logger.error(
                "Autostart konnte nicht geändert werden."
            )

            self.autostart_toggle.blockSignals(True)
            self.autostart_toggle.setChecked(not checked)
            self.autostart_toggle.blockSignals(False)

            return

        self.manager.config.data["start_on_boot"] = checked

        self.manager.config.save()

    def _save_minimize_to_tray(self, checked: bool):

        self.manager.config.data["minimize_to_tray"] = checked

        self.manager.config.save()

        self.manager.tray_settings_changed.emit(checked)
