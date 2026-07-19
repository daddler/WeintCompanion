from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.widgets.toggle_switch import ToggleSwitch

from ._common import SectionContent, toggle_row


def _version_row(label_text: str, value_text: str):

    row = QWidget()

    layout = QHBoxLayout(row)

    layout.setContentsMargins(0, 0, 0, 0)

    label = QLabel(label_text)

    label.setStyleSheet(f"font-size:13px;color:{Colors.TEXT_SECONDARY};")

    layout.addWidget(label)

    layout.addStretch()

    value = QLabel(value_text)

    value.setStyleSheet(
        'font-family:"JetBrains Mono";'
        f"font-size:13px;color:{Colors.TEXT};"
    )

    layout.addWidget(value)

    return row, value


class AutoUpdateSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · AUTO-UPDATE",
            "Auto-Update",
            "Wie WeintCompanion nach neuen Versionen sucht.",
        )

        self.manager = manager

        self.check_updates_toggle = ToggleSwitch()

        self.check_updates_toggle.toggled.connect(
            self._save_check_updates
        )

        self.addRow(
            toggle_row(
                "Beim Start nach Updates suchen",
                "Prüft GitHub beim Start auf neue Addon-/Companion-Versionen.",
                self.check_updates_toggle,
            )
        )

        info_col = QVBoxLayout()

        info_col.setSpacing(10)

        addon_row, self.addon_value = _version_row(
            "WeintCodex", "-",
        )

        info_col.addWidget(addon_row)

        companion_row, self.companion_value = _version_row(
            "WeintCompanion", "-",
        )

        info_col.addWidget(companion_row)

        self.addRow(info_col, divider=False)

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        config = self.manager.config

        self.check_updates_toggle.blockSignals(True)
        self.check_updates_toggle.setChecked(
            config.data.get("check_updates", True)
        )
        self.check_updates_toggle.blockSignals(False)

        state = self.manager.state

        if state.update_available:

            self.addon_value.setText(
                f"{state.addon_version} → {state.github_version}"
            )

        else:

            self.addon_value.setText(state.addon_version)

        if state.companion_update_available:

            self.companion_value.setText(
                f"{state.companion_version} → "
                f"{state.companion_latest_version}"
            )

        else:

            self.companion_value.setText(state.companion_version)

    # --------------------------------------------------

    def _save_check_updates(self, checked: bool):

        self.manager.config.data["check_updates"] = checked

        self.manager.config.save()
