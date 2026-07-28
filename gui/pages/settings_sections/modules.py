from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from core.raid_data_service import (
    SOURCE_DESCRIPTIONS,
    SOURCE_LABELS,
    SOURCE_MOCK,
    SOURCE_WARCRAFTLOGS,
)

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.toggle_switch import ToggleSwitch

from ._common import SectionContent, toggle_row


#
# Reihenfolge der Auswahl. Die Simulation steht vorn, weil sie ohne
# jede Einrichtung funktioniert und damit der sichere Rückfallwert
# ist.
#

SOURCE_ORDER = (
    SOURCE_MOCK,
    SOURCE_WARCRAFTLOGS,
)


def _format_size(size: int) -> str:

    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"

    if size >= 1024:
        return f"{size / 1024:.0f} KB"

    return f"{size} Byte"


class ModulesSection(SectionContent):
    """
    Ein- und Ausschalten der Zusatzmodule sowie Diagnose der
    Datenquelle, aus der WeintTV und die Academy ihre Zahlen ziehen.
    """

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · MODULE",
            "Module",
            "WeintTV und die WeintAcademy nutzen dieselbe "
            "Datenquelle - hier wird sie eingerichtet.",
        )

        self.manager = manager

        #
        # WeintTV
        #

        self.weinttv_toggle = ToggleSwitch()

        self.weinttv_toggle.toggled.connect(
            self._save_weinttv
        )

        self.addRow(
            toggle_row(
                "WeintTV aktivieren",
                "Live-Dashboard mit Bossleben, Pull-Timer, "
                "Rankings und Cooldowns.",
                self.weinttv_toggle,
            )
        )

        #
        # WeintAcademy
        #

        self.academy_toggle = ToggleSwitch()

        self.academy_toggle.toggled.connect(
            self._save_academy
        )

        self.addRow(
            toggle_row(
                "WeintAcademy aktivieren",
                "Lernzentrum mit automatischer Bewertung und "
                "persönlichem Trainingsplan.",
                self.academy_toggle,
            )
        )

        #
        # Datenquelle
        #

        source_col = QVBoxLayout()

        source_col.setSpacing(6)

        source_title = QLabel("Datenquelle")

        source_title.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        source_col.addWidget(source_title)

        self.source_select = SegmentedControl([
            (SOURCE_LABELS[source], source)
            for source in SOURCE_ORDER
        ])

        self.source_select.valueChanged.connect(
            self._save_source
        )

        source_col.addWidget(self.source_select)

        self.source_value = QLabel("-")

        self.source_value.setWordWrap(True)

        self.source_value.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
        )

        source_col.addWidget(self.source_value)

        #
        # Zustand der gewählten Quelle (erkannter Bericht, Grund für
        # "keine Daten"). Kommt direkt aus dem Provider, damit hier
        # keine zweite Fehlerbehandlung entsteht.
        #

        self.source_status = QLabel("")

        self.source_status.setWordWrap(True)

        self.source_status.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        source_col.addWidget(self.source_status)

        self.addRow(source_col)

        #
        # Combat-Log
        #

        log_col = QVBoxLayout()

        log_col.setSpacing(6)

        log_title = QLabel("Combat-Log")

        log_title.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        log_col.addWidget(log_title)

        log_description = QLabel(
            "Grundlage der späteren Live-Auswertung. Damit WoW "
            "protokolliert, muss im Spiel einmal /combatlog "
            "eingegeben oder das automatische Protokollieren "
            "aktiviert werden."
        )

        log_description.setWordWrap(True)

        log_description.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        log_col.addWidget(log_description)

        self.log_value = QLabel("-")

        self.log_value.setWordWrap(True)

        self.log_value.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_SECONDARY};"
        )

        log_col.addWidget(self.log_value)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.search_button = HeroButton("Erneut suchen", primary=False)

        self.search_button.clicked.connect(
            self._search_combat_log
        )

        button_row.addWidget(self.search_button)

        log_col.addLayout(button_row)

        self.addRow(log_col, divider=False)

        self.refresh()

    # --------------------------------------------------
    # Speichern
    # --------------------------------------------------

    def _save_weinttv(self, enabled: bool):

        self.manager.config.data["weinttv_enabled"] = enabled

        self.manager.config.save()

        if enabled:
            self.manager.logger.success("WeintTV aktiviert.")

        else:
            self.manager.logger.info("WeintTV deaktiviert.")

    def _save_academy(self, enabled: bool):

        self.manager.config.data["academy_enabled"] = enabled

        self.manager.config.save()

        if enabled:
            self.manager.logger.success("WeintAcademy aktiviert.")

        else:
            self.manager.logger.info("WeintAcademy deaktiviert.")

    # --------------------------------------------------
    # Datenquelle
    # --------------------------------------------------

    def _save_source(self, source: str):

        config = self.manager.config.data

        if config.get("raid_data_source") == source:
            return

        config["raid_data_source"] = source

        self.manager.config.save()

        #
        # Die alte Quelle sauber beenden und die Historie verwerfen -
        # das erledigt der Service, damit WeintTV und Academy beide
        # sofort auf der neuen Quelle stehen.
        #

        self.manager.raid_data.reload_provider()

        self.manager.logger.info(
            f"Raid-Datenquelle: {SOURCE_LABELS.get(source, source)}."
        )

        self._update_source()

    def _update_source(self):

        source = self.manager.config.data.get(
            "raid_data_source",
            SOURCE_MOCK,
        )

        self.source_value.setText(
            SOURCE_DESCRIPTIONS.get(
                source,
                f"Eingestellt: {source}",
            )
        )

        self.source_status.setText(
            self._source_status(source)
        )

    def _source_status(self, source: str) -> str:
        """
        Zustandstext der Quelle.

        Läuft sie gerade (WeintTV oder Academy sind geöffnet), ist
        ihr eigener status_text die genaueste Auskunft. Andernfalls
        wird wenigstens die Voraussetzung geprüft, die der Nutzer von
        hier aus erfüllen kann - alles andere entsteht erst beim
        ersten Abruf.
        """

        status = self.manager.raid_data.status_text()

        if status:
            return status

        if source == SOURCE_WARCRAFTLOGS:

            from core.warcraftlogs_client import WarcraftLogsClient

            if not WarcraftLogsClient().is_linked():

                return (
                    "Kein Discord-Konto verknüpft - die Verbindung "
                    "läuft über den Bot."
                )

            return (
                "Der Zustand erscheint, sobald WeintTV oder die "
                "Academy geöffnet ist."
            )

        return ""

    # --------------------------------------------------
    # Combat-Log
    # --------------------------------------------------

    def _search_combat_log(self):

        location = self.manager.raid_data.locate_combat_log()

        if location.found:

            self.manager.logger.success(
                f"Combat-Log gefunden: {location.path}"
            )

        else:

            self.manager.logger.warning(
                f"Kein Combat-Log gefunden - {location.reason}"
            )

        self._update_combat_log()

    def _update_combat_log(self):

        location = self.manager.raid_data.locate_combat_log()

        if location.found:

            self.log_value.setText(
                f"{location.path}  ({_format_size(location.size)})"
            )

            self.log_value.setStyleSheet(
                'font-family:"JetBrains Mono";'
                f"font-size:11px;color:{Colors.SUCCESS_LIGHT};"
            )

        else:

            self.log_value.setText(location.reason)

            self.log_value.setStyleSheet(
                'font-family:"JetBrains Mono";'
                f"font-size:11px;color:{Colors.WARNING_LIGHT};"
            )

    # --------------------------------------------------

    def refresh(self):

        config = self.manager.config.data

        #
        # blockSignals, damit das Setzen des Zustands nicht die
        # Speichern-Methoden auslöst - dasselbe Muster wie in den
        # übrigen Abschnitten.
        #

        self.weinttv_toggle.blockSignals(True)

        self.weinttv_toggle.setChecked(
            config.get("weinttv_enabled", True)
        )

        self.weinttv_toggle.blockSignals(False)

        self.academy_toggle.blockSignals(True)

        self.academy_toggle.setChecked(
            config.get("academy_enabled", True)
        )

        self.academy_toggle.blockSignals(False)

        source = config.get("raid_data_source", SOURCE_MOCK)

        self.source_select.blockSignals(True)

        self.source_select.setValue(source)

        self.source_select.blockSignals(False)

        self._update_source()

        self._update_combat_log()
