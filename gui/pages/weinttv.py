"""
WeintTV - das Live-Dashboard für Raider und Raidleitung.

Die Seite enthält bewusst KEINE Auswertungslogik. Sie bekommt vom
RaidDataService fertige `RaidSnapshot`-Objekte und schreibt deren
Werte in Widgets. Alles, was gerechnet wird, passiert im Analyzer -
dadurch kann WeintTV gegen die Simulation und gegen echte
Combat-Log-Daten identisch laufen.

Aufbau: drei Bereiche in einem eigenen QStackedWidget, umgeschaltet
über einen SegmentedControl (dasselbe Muster wie die
Unternavigation der Einstellungen, nur horizontal).

    Live      Was gerade passiert
    Analyse   Die Tiefenauswertung des Pulls
    Verlauf   Abgeschlossene Pulls

Aktualisiert wird nur, solange die Seite auch sichtbar ist:
on_enter() meldet sich beim Service an, on_leave() wieder ab. Beide
Haken ruft MainWindow.change_page() auf.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analyzer.analysis.movement import format_meters
from analyzer.models import (
    MECHANIC_SOURCE_LOCAL,
    SUPPORT_INTERRUPT,
    RaidSnapshot,
)

from core.resources import Resources

from gui.theme.colors import Colors
from gui.theme.wow_colors import class_color, role_label

from gui.widgets.card import Card
from gui.widgets.section_card import SectionCard
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.analysis_gap import analysis_gap_text
from gui.widgets.tv.archive_picker import ArchivePicker
from gui.widgets.tv.data_table import (
    DataTable,
    TableCell,
    TableColumn,
    TableRowData,
)
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.meter_bar import MeterBar
from gui.widgets.tv.meter_row_list import MeterRowData, MeterRowList
from gui.widgets.tv.metric_tile import MetricTile
from gui.widgets.tv.ranking_list import RankingList, format_per_second
from gui.widgets.tv.replay_bar import ReplayBar
from gui.widgets.tv.timer_chip import TimerChip


#
# Auswahlwert des Spielerfilters für "alle Spieler". Ein leerer String
# wäre in einer QComboBox nicht von "nichts gewählt" zu unterscheiden.
#

ALL_PLAYERS = "__all__"


def _format_amount(value: float) -> str:
    """
    Große Schadenssummen lesbar machen. Gehört hierher und nicht in
    jedes Widget - dieselbe Begründung wie bei format_per_second().
    """

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if value >= 1_000:
        return f"{value / 1_000:.0f}k"

    return f"{value:.0f}"


#
# Beschriftung der Ereignisarten aus `CombatEvent.kind`. Die Liste
# ist bewusst NICHT vollständig und darf es nicht sein: eine
# unbekannte Art wird unverändert angezeigt, statt verworfen zu
# werden - sonst müsste der Companion jedes Mal nachziehen, wenn der
# Bot eine neue Art mitschickt.
#

EVENT_KIND_LABELS = {
    "phase": "Phase",
    "cast": "Ansage",
    "add": "Add",
    "wipe": "Wipe",
    "kill": "Kill",
}


TAB_LIVE = "live"
TAB_ANALYSIS = "analysis"
TAB_HISTORY = "history"


class WeintTvPage(QWidget):

    #
    # Sprung in einen anderen Hauptbereich. Duck-getypt vom
    # MainWindow verbunden, genau wie on_enter()/on_leave().
    #

    pageRequested = Signal(int)

    #
    # "Diesen Spieler in der Academy ansehen" - die eine Hälfte der
    # Verzahnung beider Bereiche. Die andere Hälfte
    # (Academy -> Wiedergabe an dieser Sekunde) liegt in
    # gui/pages/academy.py.
    #

    playerRequested = Signal(str)

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.service = manager.raid_data

        self._attached = False

        #
        # Auf welchen Spieler die Analyse eingeschränkt ist. Ohne
        # Filter wären 25 Spieler mal sechs Tabellen unlesbar.
        #

        self._filter = ALL_PLAYERS

        self._roster_signature = ()

        root = QVBoxLayout(self)

        root.setContentsMargins(32, 28, 32, 28)

        root.setSpacing(20)

        #
        # --------------------------------------------------
        # Kopfzeile
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        title_col = QVBoxLayout()

        title_col.setSpacing(4)

        eyebrow = QLabel("WEINTTV · LIVE RAID")

        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Live-Dashboard")

        title.setObjectName("title")

        title_col.addWidget(title)

        header.addLayout(title_col)

        header.addStretch()

        #
        # Zwei Angaben, die sich nicht überschneiden dürfen: WOHER
        # die Daten kommen und OB gerade welche fließen.
        #

        self.source_chip = TimerChip("Simulation", "neutral")

        header.addWidget(self.source_chip)

        self.feed_chip = TimerChip("KEINE DATEN", "neutral")

        header.addWidget(self.feed_chip)

        root.addLayout(header)

        #
        # --------------------------------------------------
        # Live/Archiv-Umschalter
        # --------------------------------------------------
        #
        # Geteilt mit der Academy über denselben RaidDataService -
        # ein Wechsel hier wirkt auch dort, siehe
        # gui/widgets/tv/archive_picker.py.
        #

        root.addWidget(ArchivePicker(self.service))

        #
        # --------------------------------------------------
        # Wiedergabe-Steuerung
        # --------------------------------------------------
        #
        # Blendet sich selbst ein, sobald ein Pull abgespielt wird -
        # ebenfalls über denselben Service, also auch hier ohne
        # Möglichkeit, gegenüber der Academy auseinanderzulaufen.
        #

        root.addWidget(ReplayBar(self.service))

        #
        # --------------------------------------------------
        # Hinweis bei deaktiviertem Modul
        # --------------------------------------------------
        #

        self.disabled_notice = self._build_disabled_notice()

        root.addWidget(self.disabled_notice)

        #
        # --------------------------------------------------
        # Bereichsumschalter
        # --------------------------------------------------
        #

        self.tabs = SegmentedControl([
            ("Live", TAB_LIVE),
            ("Analyse", TAB_ANALYSIS),
            ("Verlauf", TAB_HISTORY),
        ])

        self.tabs.valueChanged.connect(
            self._show_tab
        )

        root.addWidget(self.tabs)

        self.stack = QStackedWidget()

        root.addWidget(self.stack, 1)

        self._tab_index = {}

        for key, builder in (
            (TAB_LIVE, self._build_live),
            (TAB_ANALYSIS, self._build_analysis),
            (TAB_HISTORY, self._build_history),
        ):

            self._tab_index[key] = self.stack.count()

            self.stack.addWidget(builder())

        self.tabs.setValue(TAB_LIVE)

        #
        # Signale
        #

        self.service.snapshotChanged.connect(
            self._on_snapshot
        )

        self.refresh()

    # --------------------------------------------------
    # Aufbau: Hinweis
    # --------------------------------------------------

    def _build_disabled_notice(self) -> Card:

        card = Card()

        title = QLabel("WeintTV ist deaktiviert")

        title.setStyleSheet(
            f"font-size:15px;font-weight:600;color:{Colors.WHITE};"
            "background:transparent;border:none;"
        )

        card.addWidget(title)

        text = QLabel(
            "Das Modul lässt sich unter Einstellungen · Module "
            "wieder einschalten."
        )

        text.setWordWrap(True)

        text.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        card.addWidget(text)

        card.setVisible(False)

        return card

    def _build_analysis_notice(self) -> Card:
        """
        Erklärt, warum die Tiefenauswertung leer ist - statt sie als
        Reihe leerer Karten stehen zu lassen.
        """

        card = Card()

        title = QLabel("Keine Tiefenauswertung für diesen Stand")

        title.setStyleSheet(
            f"font-size:15px;font-weight:600;color:{Colors.WHITE};"
            "background:transparent;border:none;"
        )

        card.addWidget(title)

        self.analysis_notice_text = QLabel("")

        self.analysis_notice_text.setWordWrap(True)

        self.analysis_notice_text.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        card.addWidget(self.analysis_notice_text)

        card.setVisible(False)

        return card

    # --------------------------------------------------
    # Aufbau: Live
    # --------------------------------------------------

    def _build_live(self) -> QWidget:

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(16)

        #
        # Boss
        #

        self.boss_card = SectionCard(
            Resources.game(),
            "Boss",
            "",
        )

        boss_head = QHBoxLayout()

        boss_head.setSpacing(12)

        self.boss_name = QLabel("Kein Kampf")

        self.boss_name.setStyleSheet(
            f"font-size:20px;font-weight:700;color:{Colors.WHITE};"
            "letter-spacing:-0.01em;background:transparent;border:none;"
        )

        boss_head.addWidget(self.boss_name)

        self.boss_instance = QLabel("")

        self.boss_instance.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        boss_head.addWidget(self.boss_instance)

        boss_head.addStretch()

        self.state_chip = TimerChip("BEREIT", "neutral")

        boss_head.addWidget(self.state_chip)

        self.pull_chip = TimerChip("00:00", "primary")

        boss_head.addWidget(self.pull_chip)

        self.boss_card.addLayout(boss_head)

        self.boss_bar = MeterBar(height=14)

        self.boss_card.addWidget(self.boss_bar)

        boss_foot = QHBoxLayout()

        self.boss_health = QLabel("100.0 %")

        self.boss_health.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:12px;font-weight:700;color:{Colors.TEXT};"
            "background:transparent;border:none;"
        )

        boss_foot.addWidget(self.boss_health)

        boss_foot.addStretch()

        self.pull_label = QLabel("")

        self.pull_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        boss_foot.addWidget(self.pull_label)

        self.boss_card.addLayout(boss_foot)

        layout.addWidget(self.boss_card)

        #
        # Kennzahlen
        #

        tiles = QGridLayout()

        tiles.setContentsMargins(0, 0, 0, 0)

        tiles.setHorizontalSpacing(14)

        tiles.setVerticalSpacing(14)

        self.tile_deaths = MetricTile("TODE", "0")
        self.tile_battle_res = MetricTile("KAMPF-REZZ", "0")
        self.tile_heroism = MetricTile("HELDENTUM", "Bereit")
        self.tile_raid = MetricTile("RAIDGRÖSSE", "0")

        for column, tile in enumerate((
            self.tile_deaths,
            self.tile_battle_res,
            self.tile_heroism,
            self.tile_raid,
        )):

            tiles.addWidget(tile, 0, column)

            tiles.setColumnStretch(column, 1)

        layout.addLayout(tiles)

        #
        # Rankings
        #

        rankings = QHBoxLayout()

        rankings.setSpacing(16)

        damage_card = SectionCard(
            Resources.game(),
            "Top Schaden",
            "Schaden pro Sekunde im laufenden Pull.",
        )

        self.damage_list = RankingList(limit=5)

        damage_card.addWidget(self.damage_list)

        rankings.addWidget(damage_card, 1)

        healing_card = SectionCard(
            Resources.backup(),
            "Top Heilung",
            "Heilung pro Sekunde im laufenden Pull.",
        )

        self.healing_list = RankingList(limit=5)

        healing_card.addWidget(self.healing_list)

        rankings.addWidget(healing_card, 1)

        layout.addLayout(rankings)

        #
        # Tanks
        #

        tank_card = SectionCard(
            Resources.companion(),
            "Tank-Übersicht",
            "Lebenspunkte und aktive Schadensminderung.",
        )

        self.tank_list = MeterRowList(
            capacity=4,
            placeholder="Keine Tanks erkannt.",
        )

        tank_card.addWidget(self.tank_list)

        layout.addWidget(tank_card)

        #
        # Kampfereignisse
        #
        # Tode, Kampf-Wiederbelebungen und Heldentum in einer
        # gemeinsamen, zeitlich sortierten Liste. Bisher war nur
        # ablesbar, DASS Heldentum lief und WIE VIELE Rezz-Ladungen
        # übrig sind - nicht wann und auf wen. Drei getrennte, meist
        # fast leere Karten dafür wären verschenkter Platz; die
        # gemeinsame Zeitachse erzählt zudem den Verlauf des Pulls.
        #

        events_card = SectionCard(
            Resources.logs(),
            "Kampfereignisse",
            (
                "Tode, Kampf-Rezz, Heldentum, Unterbrechungen und "
                "Phasen in zeitlicher Folge."
            ),
        )

        self.events_list = EntryList(
            capacity=20,
            placeholder="Noch nichts passiert.",
        )

        events_card.addWidget(self.events_list)

        layout.addWidget(events_card)

        layout.addStretch()

        return page

    # --------------------------------------------------
    # Aufbau: Analyse
    # --------------------------------------------------

    def _build_analysis(self) -> QWidget:

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(16)

        #
        # Spielerfilter
        #
        # Ohne ihn stünden hier 25 Spieler mal sechs Tabellen. Die
        # Analyse soll die Frage "was soll ICH anders machen"
        # beantworten können, und dafür muss man sich auf einen
        # Spieler beschränken dürfen.
        #

        filter_row = QHBoxLayout()

        filter_row.setSpacing(10)

        filter_label = QLabel("Spieler")

        filter_label.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        filter_row.addWidget(filter_label)

        self.player_filter = QComboBox()

        self.player_filter.setMinimumWidth(200)

        self.player_filter.currentIndexChanged.connect(
            self._on_filter_changed
        )

        filter_row.addWidget(self.player_filter)

        filter_row.addStretch()

        layout.addLayout(filter_row)

        #
        # Hinweis, wenn die Quelle keine Tiefenauswertung liefert
        #
        # `RaidSnapshot.has_analysis` ist der eine Schalter dafür.
        # Ohne ihn stand die Seite in genau diesem Fall voller leerer
        # Karten: für jede einzelne wäre "keine Angaben" formal
        # richtig, in Summe sah es aber nach einem Defekt aus statt
        # nach einer Quelle, die diese Werte (noch) nicht liefert.
        #

        self.analysis_notice = self._build_analysis_notice()

        layout.addWidget(self.analysis_notice)

        #
        # Alle Karten der Tiefenauswertung in einem gemeinsamen
        # Behälter, damit sie zusammen ein- und ausgeblendet werden
        # können. Die Karten darunter (Cooldowns, Verbrauchsgüter,
        # Mechanikfehler, Warnungen) bleiben stehen - sie kommen schon
        # aus dem Grunddatensatz jeder Quelle.
        #

        self.deep_analysis = QWidget()

        deep = QVBoxLayout(self.deep_analysis)

        deep.setContentsMargins(0, 0, 0, 0)

        deep.setSpacing(16)

        layout.addWidget(self.deep_analysis)

        #
        # Erhaltener Schaden
        #
        # Steht bewusst ganz oben: es ist die Zahl, die am ehesten
        # erklärt, warum ein Pull schiefging - und die Grundlage der
        # Überlebensbewertung in der Academy.
        #

        self.damage_taken_table = DataTable(
            columns=(
                TableColumn("Spieler", weight=3),
                TableColumn("Gesamt", weight=2, align="right", mono=True),
                TableColumn("Vermeidbar", weight=2, align="right", mono=True),
                TableColumn("Anteil", weight=2, align="right", mono=True),
                TableColumn("Treffer", weight=1, align="right", mono=True),
            ),
            capacity=25,
            placeholder="Keine Angaben zum erhaltenen Schaden.",
        )

        self.damage_taken_table.rowActivated.connect(
            self.playerRequested
        )

        damage_taken_card = SectionCard(
            Resources.game(),
            "Erhaltener Schaden",
            "Wie viel getroffen wurde - und wie viel davon vermeidbar war.",
        )

        damage_taken_card.addWidget(self.damage_taken_table)

        deep.addWidget(damage_taken_card)

        #
        # Vermeidbarer Schaden nach Fähigkeit
        #

        self.avoidable_table = DataTable(
            columns=(
                TableColumn("Fähigkeit", weight=3),
                TableColumn("Spieler", weight=2),
                TableColumn("Schaden", weight=2, align="right", mono=True),
                TableColumn("Treffer", weight=1, align="right", mono=True),
                TableColumn("Was tun", weight=3),
            ),
            capacity=20,
            placeholder=(
                "Nichts Vermeidbares erkannt - oder für diesen Boss "
                "fehlen noch Referenzdaten."
            ),
        )

        self.avoidable_table.rowActivated.connect(
            self.playerRequested
        )

        avoidable_card = SectionCard(
            Resources.logs(),
            "Vermeidbarer Schaden",
            "Aufgeschlüsselt nach Fähigkeit, mit Hinweis was zu tun war.",
        )

        avoidable_card.addWidget(self.avoidable_table)

        deep.addWidget(avoidable_card)

        #
        # Wirkungsdauern
        #

        uptimes = QHBoxLayout()

        uptimes.setSpacing(16)

        dot_card = SectionCard(
            Resources.game(),
            "DoT-Uptimes",
            "Wirkungsdauer der Schadenseffekte auf dem Ziel.",
        )

        self.dot_uptimes = MeterRowList(
            capacity=12,
            placeholder="Keine Angaben zu DoT-Uptimes.",
        )

        dot_card.addWidget(self.dot_uptimes)

        uptimes.addWidget(dot_card, 1)

        hot_card = SectionCard(
            Resources.backup(),
            "HoT-Uptimes",
            "Wirkungsdauer der Heileffekte auf dem Raid.",
        )

        self.hot_uptimes = MeterRowList(
            capacity=12,
            placeholder="Keine Angaben zu HoT-Uptimes.",
        )

        hot_card.addWidget(self.hot_uptimes)

        uptimes.addWidget(hot_card, 1)

        #
        # Eigene Buffs - für die Tanks die wichtigste Zeile der ganzen
        # Seite: die aktive Schadensminderung ist ihr Beitrag zum
        # Überleben, und sie ist weder ein DoT noch ein HoT. Ohne
        # eigene Karte wäre sie entweder unsichtbar oder stünde bei
        # den Heileffekten.
        #

        buff_card = SectionCard(
            Resources.companion(),
            "Eigene Buffs",
            "Aktive Schadensminderung und Selbstbuffs.",
        )

        self.buff_uptimes = MeterRowList(
            capacity=12,
            placeholder="Keine Angaben zu eigenen Buffs.",
        )

        buff_card.addWidget(self.buff_uptimes)

        uptimes.addWidget(buff_card, 1)

        deep.addLayout(uptimes)

        #
        # Laufwege und Aktivzeit
        #

        movement_row = QHBoxLayout()

        movement_row.setSpacing(16)

        self.movement_card = SectionCard(
            Resources.companion(),
            "Laufwege",
            "Schätzung aus Positionsdaten.",
        )

        self.movement_list = MeterRowList(
            capacity=25,
            placeholder="Keine Angaben zu Laufwegen.",
        )

        self.movement_card.addWidget(self.movement_list)

        movement_row.addWidget(self.movement_card, 1)

        activity_card = SectionCard(
            Resources.dashboard(),
            "Aktivzeit",
            "Wie durchgehend gespielt wurde - unabhängig vom Schaden.",
        )

        self.activity_list = MeterRowList(
            capacity=25,
            placeholder="Keine Angaben zur Aktivzeit.",
        )

        activity_card.addWidget(self.activity_list)

        movement_row.addWidget(activity_card, 1)

        deep.addLayout(movement_row)

        #
        # Cooldown-Nutzung
        #
        # Nicht zu verwechseln mit den beiden Fortschrittslisten
        # weiter unten: die zeigen den Live-Countdown, diese Tabelle
        # die Rückschau über den ganzen Kampf.
        #

        self.cooldown_table = DataTable(
            columns=(
                TableColumn("Fähigkeit", weight=3),
                TableColumn("Spieler", weight=2),
                TableColumn("Einsätze", weight=2, align="right", mono=True),
                TableColumn("Im Heldentum", weight=2, align="right", mono=True),
                TableColumn("Zeitpunkte", weight=3, mono=True),
            ),
            capacity=25,
            placeholder="Keine Angaben zur Cooldown-Nutzung.",
        )

        self.cooldown_table.rowActivated.connect(
            self.playerRequested
        )

        cooldown_usage_card = SectionCard(
            Resources.companion(),
            "Cooldown-Nutzung",
            "Genutzte gegen mögliche Einsätze über den ganzen Kampf.",
        )

        cooldown_usage_card.addWidget(self.cooldown_table)

        deep.addWidget(cooldown_usage_card)

        #
        # Unterbrechungen und Dispels
        #

        self.support_list = EntryList(
            capacity=12,
            placeholder="Keine Unterbrechungen oder Dispels erfasst.",
        )

        support_card = SectionCard(
            Resources.sync(),
            "Unterbrechungen & Dispels",
            "Wer wann eingegriffen hat.",
        )

        support_card.addWidget(self.support_list)

        deep.addWidget(support_card)

        cooldowns = QHBoxLayout()

        cooldowns.setSpacing(16)

        raid_card = SectionCard(
            Resources.companion(),
            "Raid-Cooldowns",
            "Balken zeigt den Fortschritt der Abklingzeit.",
        )

        self.raid_cooldowns = MeterRowList(
            capacity=8,
            placeholder="Keine Raid-Cooldowns erkannt.",
        )

        raid_card.addWidget(self.raid_cooldowns)

        cooldowns.addWidget(raid_card, 1)

        heal_card = SectionCard(
            Resources.backup(),
            "Heil-Cooldowns",
            "Balken zeigt den Fortschritt der Abklingzeit.",
        )

        self.heal_cooldowns = MeterRowList(
            capacity=8,
            placeholder="Keine Heil-Cooldowns erkannt.",
        )

        heal_card.addWidget(self.heal_cooldowns)

        cooldowns.addWidget(heal_card, 1)

        layout.addLayout(cooldowns)

        #
        # Verbrauchsgüter
        #

        consumable_card = SectionCard(
            Resources.download(),
            "Verbrauchsgüter",
            "Flask, Bufffood und Kampftrank im Raid.",
        )

        self.consumables = MeterRowList(
            capacity=5,
            placeholder="Keine Angaben zu Verbrauchsgütern.",
        )

        consumable_card.addWidget(self.consumables)

        layout.addWidget(consumable_card)

        #
        # Fehler und Warnungen
        #

        issues = QHBoxLayout()

        issues.setSpacing(16)

        mechanics_card = SectionCard(
            Resources.logs(),
            "Mechanikfehler",
            "Vermeidbare Fehler des laufenden Pulls.",
        )

        self.mechanics = EntryList(
            capacity=8,
            placeholder="Keine Mechanikfehler erkannt.",
        )

        mechanics_card.addWidget(self.mechanics)

        issues.addWidget(mechanics_card, 1)

        warnings_card = SectionCard(
            Resources.changelog(),
            "Warnungen",
            "Hinweise der Auswertung an die Raidleitung.",
        )

        self.warnings = EntryList(
            capacity=6,
            placeholder="Keine Warnungen.",
        )

        warnings_card.addWidget(self.warnings)

        issues.addWidget(warnings_card, 1)

        layout.addLayout(issues)

        layout.addStretch()

        return page

    # --------------------------------------------------
    # Aufbau: Verlauf
    # --------------------------------------------------

    def _build_history(self) -> QWidget:

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(16)

        history_card = SectionCard(
            Resources.changelog(),
            "Pull-Historie",
            "Abgeschlossene Versuche dieser Sitzung, neuester zuerst.",
        )

        self.history_list = EntryList(
            capacity=12,
            placeholder=(
                "Noch keine abgeschlossenen Pulls in dieser Sitzung."
            ),
        )

        history_card.addWidget(self.history_list)

        layout.addWidget(history_card)

        layout.addStretch()

        return page

    # --------------------------------------------------
    # Navigation innerhalb der Seite
    # --------------------------------------------------

    def show_tab(self, key):
        """
        Öffentlich, weil die Academy hierher springen können muss -
        "Zur Analyse" aus der Übersicht heraus.
        """

        self.tabs.setValue(key)

        self._show_tab(key)

    def _show_tab(self, key):

        index = self._tab_index.get(key)

        if index is None:
            return

        self.stack.setCurrentIndex(index)

    # --------------------------------------------------
    # Lebenszyklus (von MainWindow.change_page aufgerufen)
    # --------------------------------------------------

    def _module_enabled(self) -> bool:

        return bool(
            self.manager.config.data.get("weinttv_enabled", True)
        )

    def on_enter(self):

        enabled = self._module_enabled()

        self.disabled_notice.setVisible(not enabled)

        self.tabs.setVisible(enabled)

        self.stack.setVisible(enabled)

        if not enabled:

            self.on_leave()

            return

        if not self._attached:

            self.service.attach()

            self._attached = True

        #
        # Sofort den zuletzt bekannten Stand zeichnen, statt bis zum
        # ersten Poll leer zu bleiben.
        #

        self._apply_snapshot(self.service.current())

    def on_leave(self):

        if not self._attached:
            return

        self.service.detach()

        self._attached = False

    # --------------------------------------------------

    def refresh(self):

        self._apply_snapshot(self.service.current())

    # --------------------------------------------------
    # Snapshot anwenden
    # --------------------------------------------------

    def _on_snapshot(self, snapshot: RaidSnapshot):
        """
        Der Anschluss an `snapshotChanged`.

        Er zeichnet nur, solange diese Seite auch angemeldet ist. Der
        Dienst veröffentlicht nämlich weiter, während eine andere
        Seite im Vordergrund ist: bei einer laufenden Wiedergabe
        viermal je Sekunde, und die WeintAcademy hängt am selben
        Signal. Ohne diese Prüfung baute jede der beiden Seiten
        dauerhaft die jeweils andere mit auf - doppelte Arbeit für
        ein Bild, das niemand sieht.

        `on_enter()` zeichnet direkt nach dem Anmelden selbst, ein
        verpasster Snapshot geht also nicht verloren.
        """

        if not self._attached:
            return

        self._apply_snapshot(snapshot)

    def _apply_snapshot(self, snapshot: RaidSnapshot):

        self._apply_header(snapshot)

        self._apply_live(snapshot)

        self._apply_analysis(snapshot)

        self._apply_history()

    # --------------------------------------------------

    def _apply_header(self, snapshot: RaidSnapshot):

        self.source_chip.setValue(
            snapshot.source_label,
            "info" if snapshot.live else "neutral",
        )

        if not snapshot.has_data:

            self.feed_chip.setValue("KEINE DATEN", "neutral")

        elif snapshot.live:

            self.feed_chip.setValue("LIVE", "error")

        else:

            self.feed_chip.setValue("DATEN AKTIV", "primary")

    # --------------------------------------------------

    def _apply_live(self, snapshot: RaidSnapshot):

        #
        # Boss
        #

        self.boss_name.setText(snapshot.encounter_name)

        encounter = snapshot.encounter

        if encounter is not None:

            parts = [
                part
                for part in (encounter.instance, encounter.difficulty)
                if part
            ]

            self.boss_instance.setText(" · ".join(parts))

        else:

            self.boss_instance.setText("")

        percent = snapshot.boss_health_percent

        self.boss_bar.setValue(percent / 100.0)

        self.boss_bar.setColor(
            Colors.ERROR
            if percent <= 25.0
            else ""
        )

        self.boss_health.setText(f"{percent:.1f} %")

        if snapshot.in_combat:

            self.state_chip.setValue("IM KAMPF", "error")

        elif snapshot.has_data:

            self.state_chip.setValue("BEREIT", "success")

        else:

            self.state_chip.setValue("KEIN RAID", "neutral")

        self.pull_chip.setValue(snapshot.pull_clock, "primary")

        self.pull_label.setText(
            f"Pull {snapshot.pull_number}"
            if snapshot.pull_number
            else ""
        )

        #
        # Kennzahlen
        #

        self.tile_deaths.setValue(str(snapshot.death_count))

        self.tile_deaths.setValueColor(
            Colors.ERROR_LIGHT
            if snapshot.death_count
            else Colors.WHITE
        )

        last_death = snapshot.deaths[-1] if snapshot.deaths else None

        self.tile_deaths.setCaption(
            f"zuletzt: {last_death.actor_name}"
            if last_death
            else "keine Ausfälle"
        )

        self.tile_battle_res.setValue(
            f"{snapshot.battle_res_charges}/{snapshot.battle_res_max}"
            if snapshot.battle_res_max
            else "-"
        )

        self.tile_battle_res.setCaption("Ladungen verfügbar")

        if snapshot.heroism_remaining > 0:

            self.tile_heroism.setValue(
                f"{int(snapshot.heroism_remaining)}s"
            )

            self.tile_heroism.setValueColor(Colors.SUCCESS_LIGHT)

            self.tile_heroism.setCaption("läuft gerade")

        elif snapshot.heroism_used:

            self.tile_heroism.setValue("Verbraucht")

            self.tile_heroism.setValueColor(Colors.TEXT_MUTED)

            self.tile_heroism.setCaption("in diesem Pull genutzt")

        else:

            self.tile_heroism.setValue("Bereit")

            self.tile_heroism.setValueColor(Colors.WHITE)

            self.tile_heroism.setCaption("noch nicht genutzt")

        self.tile_raid.setValue(str(snapshot.raid_size))

        self.tile_raid.setCaption(
            f"{len(snapshot.top_healing)} Heiler · "
            f"{len(snapshot.tanks)} Tanks"
            if snapshot.has_data
            else "kein Raid erkannt"
        )

        #
        # Rankings
        #

        self.damage_list.setEntries(snapshot.top_damage)

        self.healing_list.setEntries(snapshot.top_healing)

        #
        # Tanks
        #

        self.tank_list.setRows(
            MeterRowData(
                title=tank.actor.name,
                detail=(
                    f"{role_label(tank.actor.role)} · "
                    f"{'Mitigation aktiv' if tank.active_mitigation else 'ungeschützt'}"
                ),
                value=f"{tank.health_percent:.0f} %",
                ratio=tank.health_percent / 100.0,
                color=(
                    Colors.ERROR
                    if tank.health_percent < 35.0
                    else class_color(tank.actor.class_name)
                ),
            )
            for tank in snapshot.tanks
        )

        self.events_list.setEntries(self._event_rows(snapshot))

    def _event_rows(self, snapshot: RaidSnapshot):
        """
        Alles, was zu einem Zeitpunkt passiert ist, auf einer
        gemeinsamen Zeitachse - neueste zuerst, damit das Jüngste ohne
        Scrollen sichtbar ist.

        Zusammengeführt wird hier und nicht in der Auswertung: der
        Snapshot hält die Ereignisarten getrennt, weil die Academy sie
        getrennt braucht (ein Dispel bewertet einen anderen Bereich
        als ein Tod). Für den Verlauf eines Pulls zählt dagegen nur
        die Reihenfolge - drei fast leere Karten nebeneinander würden
        sie nicht erzählen.
        """

        rows = []

        #
        # Was die Quelle zusätzlich erzählt (Phasenwechsel, angesagte
        # Bossfähigkeiten). Unbekannte Arten laufen ohne
        # Fallunterscheidung mit - genau dafür ist `kind` eine freie
        # Zeichenkette.
        #

        for event in snapshot.events:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=event.detail or event.ability or event.kind,
                    detail=(
                        event.clock
                        + (
                            f" · {event.actor_name}"
                            if event.actor_name
                            else ""
                        )
                    ),
                    level=event.severity,
                    trailing=EVENT_KIND_LABELS.get(event.kind, event.kind),
                ),
            ))

        for event in snapshot.interrupts + snapshot.dispels:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=(
                        f"{event.actor_name} → {event.target}"
                        if event.target
                        else event.actor_name
                    ),
                    detail=(
                        f"{int(event.at_seconds) // 60:02d}:"
                        f"{int(event.at_seconds) % 60:02d}"
                        + (f" · {event.ability}" if event.ability else "")
                    ),
                    level="success",
                    trailing=(
                        "Unterbrechung"
                        if event.kind == SUPPORT_INTERRUPT
                        else "Dispel"
                    ),
                ),
            ))

        #
        # Mechanikfehler nur, wenn sie sich an einer Sekunde
        # festmachen lassen - ein Eintrag ohne Zeitpunkt (at_seconds
        # < 0) hätte auf einer Zeitachse keinen Platz und steht
        # ohnehin in der Analyse.
        #

        for issue in snapshot.mechanics:

            if issue.at_seconds < 0:
                continue

            rows.append((
                issue.at_seconds,
                EntryData(
                    title=f"{issue.actor_name}: {issue.mechanic}",
                    detail=(
                        f"{int(issue.at_seconds) // 60:02d}:"
                        f"{int(issue.at_seconds) % 60:02d}"
                    ),
                    level=issue.severity,
                    trailing=f"{issue.count}×",
                ),
            ))

        for window in snapshot.heroism_windows:

            rows.append((
                window.start,
                EntryData(
                    title=f"{window.label} eingesetzt",
                    detail=(
                        f"{window.clock}"
                        + (f" · von {window.source}" if window.source else "")
                    ),
                    level="info",
                    trailing=f"{int(window.duration)}s",
                ),
            ))

        for event in snapshot.resurrections:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=f"Kampf-Rezz auf {event.target}",
                    detail=(
                        f"{event.clock}"
                        + (f" · von {event.caster}" if event.caster else "")
                    ),
                    level="success",
                    trailing=event.ability,
                ),
            ))

        for death in snapshot.deaths:

            clock = max(0, int(death.at_seconds))

            rows.append((
                death.at_seconds,
                EntryData(
                    title=f"{death.actor_name} gestorben",
                    detail=(
                        f"{clock // 60:02d}:{clock % 60:02d}"
                        + (f" · {death.cause}" if death.cause else "")
                    ),
                    level="error",
                ),
            ))

        rows.sort(key=lambda row: row[0], reverse=True)

        return [entry for _at, entry in rows]

    # --------------------------------------------------

    def _apply_analysis(self, snapshot: RaidSnapshot):

        self.raid_cooldowns.setRows(
            self._cooldown_rows(snapshot.raid_cooldowns)
        )

        self.heal_cooldowns.setRows(
            self._cooldown_rows(snapshot.heal_cooldowns)
        )

        self.consumables.setRows(
            MeterRowData(
                title=state.label,
                detail=(
                    "fehlt: " + ", ".join(state.missing)
                    if state.missing
                    else "vollständig"
                ),
                value=f"{state.used}/{state.total}",
                ratio=state.ratio,
                color=(
                    Colors.SUCCESS
                    if state.ratio >= 0.99
                    else Colors.WARNING
                ),
            )
            for state in snapshot.consumables
        )

        #
        # Die Herkunft steht dabei: Fehler, die der Analyzer aus dem
        # erhaltenen Schaden abgeleitet hat, sind nur so gut wie die
        # Referenzdaten des jeweiligen Bosses - das soll man sehen
        # können, statt beide Quellen ununterscheidbar zu mischen.
        #

        self.mechanics.setEntries(
            EntryData(
                title=issue.mechanic,
                detail=(
                    issue.actor_name
                    + (
                        " · aus dem Schaden abgeleitet"
                        if issue.source == MECHANIC_SOURCE_LOCAL
                        else ""
                    )
                ),
                level=issue.severity,
                trailing=f"{issue.count}×",
            )
            for issue in snapshot.mechanics
        )

        self.warnings.setEntries(
            EntryData(
                title=text,
                level="warning",
            )
            for text in snapshot.warnings
        )

        self._apply_deep_analysis(snapshot)

    # --------------------------------------------------
    # Tiefenauswertung
    # --------------------------------------------------
    #
    # Jede Karte bekommt genau die Zeilen, die zur Filterauswahl
    # passen. Fehlt der Datenquelle ein Block, entsteht eine leere
    # Liste und das jeweilige Widget zeigt seinen Platzhaltertext -
    # kein Sonderfall, keine Fallunterscheidung je Feld.
    #

    def _keep(self, name: str) -> bool:

        return self._filter in (ALL_PLAYERS, name)

    def _apply_deep_analysis(self, snapshot: RaidSnapshot):

        self._apply_analysis_availability(snapshot)

        self._sync_filter(snapshot)

        self._apply_damage_taken(snapshot)

        self._apply_uptimes(snapshot)

        self._apply_movement(snapshot)

        self._apply_cooldown_usage(snapshot)

        self.support_list.setEntries(
            EntryData(
                title=(
                    f"{event.actor_name} → {event.target}"
                    if event.target
                    else event.actor_name
                ),
                detail=(
                    ("Unterbrechung" if event.kind == "interrupt" else "Dispel")
                    + (f" · {event.ability}" if event.ability else "")
                ),
                level="success",
                trailing=(
                    f"{int(event.at_seconds) // 60:02d}:"
                    f"{int(event.at_seconds) % 60:02d}"
                ),
            )
            for event in sorted(
                (
                    event
                    for event in snapshot.interrupts + snapshot.dispels
                    if self._keep(event.actor_name)
                ),
                key=lambda event: event.at_seconds,
                reverse=True,
            )
        )

    def _apply_analysis_availability(self, snapshot: RaidSnapshot):
        """
        Die Tiefenauswertung ganz aus- oder einblenden.

        Der Grund wird benannt, weil er drei völlig verschiedene sein
        kann: es wird gar kein Raid ausgewertet, es läuft gerade kein
        Pull, oder die Quelle liefert diese Werte nicht. Ein
        einheitliches "keine Daten" ließe den Nutzer im Unklaren
        darüber, ob er etwas ändern kann.
        """

        available = snapshot.has_analysis

        self.deep_analysis.setVisible(available)

        self.analysis_notice.setVisible(not available)

        if available:
            return

        self.analysis_notice_text.setText(
            analysis_gap_text(snapshot)
        )

    def _apply_damage_taken(self, snapshot: RaidSnapshot):

        rows = [
            entry
            for entry in snapshot.damage_taken
            if self._keep(entry.actor_name)
        ]

        self.damage_taken_table.setRows(
            TableRowData(
                key=entry.actor_name,
                cells=(
                    TableCell(entry.actor_name, Colors.TEXT),
                    TableCell(_format_amount(entry.total)),
                    TableCell(
                        _format_amount(entry.avoidable),
                        (
                            Colors.ERROR
                            if entry.avoidable > 0
                            else Colors.TEXT_MUTED
                        ),
                    ),
                    TableCell(
                        f"{entry.avoidable_share * 100:.0f} %",
                        (
                            Colors.ERROR
                            if entry.avoidable_share >= 0.15
                            else Colors.SUCCESS
                        ),
                        ratio=entry.avoidable_share,
                    ),
                    TableCell(str(entry.hits)),
                ),
            )
            for entry in rows
        )

        #
        # Die Aufschlüsselung nach Fähigkeit zeigt nur Vermeidbares -
        # unvermeidbarer Schaden gehört zum Kampf und wäre hier nur
        # Rauschen.
        #

        breakdown = []

        for entry in rows:

            for ability in entry.abilities:

                if not ability.avoidable:
                    continue

                breakdown.append((entry.actor_name, ability))

        breakdown.sort(key=lambda row: row[1].amount, reverse=True)

        self.avoidable_table.setRows(
            TableRowData(
                key=name,
                cells=(
                    TableCell(ability.ability, Colors.TEXT),
                    TableCell(name),
                    TableCell(_format_amount(ability.amount), Colors.ERROR),
                    TableCell(str(ability.hits)),
                    TableCell(ability.note, Colors.TEXT_MUTED),
                ),
            )
            for name, ability in breakdown
        )

    def _apply_uptimes(self, snapshot: RaidSnapshot):

        for widget, rows in (
            (self.dot_uptimes, snapshot.dot_uptimes),
            (self.hot_uptimes, snapshot.hot_uptimes),
            (self.buff_uptimes, snapshot.buff_uptimes),
        ):

            widget.setRows(
                MeterRowData(
                    title=entry.ability,
                    detail=(
                        entry.actor_name
                        + (
                            f" · {entry.applications}× aufgelegt"
                            if entry.applications
                            else ""
                        )
                        + (
                            f" · Ziel {entry.expected_percent:.0f} %"
                            if entry.expected_percent > 0
                            else ""
                        )
                    ),
                    value=f"{entry.uptime_percent:.0f} %",
                    ratio=entry.uptime_percent / 100.0,
                    color=(
                        Colors.SUCCESS
                        if entry.uptime_percent >= entry.expected_percent
                        else Colors.WARNING
                    ),
                )
                for entry in rows
                if self._keep(entry.actor_name)
            )

    def _apply_movement(self, snapshot: RaidSnapshot):

        average = snapshot.movement_average

        #
        # Der Untertitel nennt den Raidschnitt und sagt ausdrücklich,
        # dass es eine Schätzung ist. WarcraftLogs kennt keine
        # Distanzmetrik - der Wert entsteht aus Positionsangaben
        # zwischen Ereignissen und unterschätzt echtes Ausweichen.
        #

        self.movement_card.setSubtitle(
            f"Schätzung aus Positionsdaten · Raidschnitt "
            f"{format_meters(average)}"
            if average > 0
            else "Schätzung aus Positionsdaten."
        )

        longest = max(
            (entry.meters for entry in snapshot.movement),
            default=0.0,
        )

        self.movement_list.setRows(
            MeterRowData(
                title=entry.actor_name,
                detail=(
                    f"{entry.meters_per_second:.1f} m/s"
                    + (
                        f" · {entry.avoidable_hits} vermeidbare Treffer"
                        if entry.avoidable_hits
                        else ""
                    )
                ),
                value=format_meters(entry.meters),
                ratio=(
                    entry.meters / longest
                    if longest > 0
                    else 0.0
                ),
                color=(
                    Colors.WARNING
                    if average > 0 and entry.meters > average * 1.25
                    else Colors.PRIMARY
                ),
            )
            for entry in snapshot.movement
            if self._keep(entry.actor_name)
        )

        self.activity_list.setRows(
            MeterRowData(
                title=entry.actor_name,
                detail=(
                    f"{entry.apm:.0f} Aktionen/min"
                    + (
                        #
                        # Die längste Pause steht daneben, weil sie
                        # etwas anderes erzählt als der Mittelwert:
                        # 90 % Aktivzeit können gleichmäßig verteilt
                        # sein oder aus einem einzigen 18-Sekunden-Loch
                        # bestehen - und nur das zweite ist ein Fehler,
                        # den man abstellen kann.
                        #
                        f" · längste Pause {entry.longest_gap:.0f} s"
                        if entry.longest_gap >= 3.0
                        else ""
                    )
                ),
                value=f"{entry.active_percent:.0f} %",
                ratio=entry.active_percent / 100.0,
                color=(
                    Colors.SUCCESS
                    if entry.active_percent >= 90.0
                    else Colors.WARNING
                ),
            )
            for entry in snapshot.activity
            if self._keep(entry.actor_name)
        )

    def _apply_cooldown_usage(self, snapshot: RaidSnapshot):

        rows = sorted(
            (
                usage
                for usage in snapshot.cooldown_usage
                if self._keep(usage.actor_name)
            ),
            key=lambda usage: usage.efficiency,
        )

        self.cooldown_table.setRows(
            TableRowData(
                key=usage.actor_name,
                cells=(
                    TableCell(usage.ability, Colors.TEXT),
                    TableCell(usage.actor_name),
                    TableCell(
                        f"{usage.uses}/{usage.possible}"
                        if usage.possible
                        else str(usage.uses),
                        (
                            Colors.SUCCESS
                            if usage.efficiency >= 0.85
                            else Colors.WARNING
                        ),
                        ratio=usage.efficiency,
                    ),
                    TableCell(
                        str(usage.in_burst)
                        if snapshot.heroism_windows
                        else "-",
                        (
                            Colors.SUCCESS
                            if usage.in_burst
                            else Colors.TEXT_MUTED
                        ),
                    ),
                    TableCell(
                        ", ".join(
                            f"{int(at) // 60:02d}:{int(at) % 60:02d}"
                            for at in usage.cast_times
                        )
                        or "nicht genutzt",
                        (
                            Colors.TEXT_MUTED
                            if usage.cast_times
                            else Colors.ERROR
                        ),
                    ),
                ),
            )
            for usage in rows
        )

    # --------------------------------------------------

    def _sync_filter(self, snapshot: RaidSnapshot):
        """
        Die Spielerliste des Filters mitziehen, ohne die laufende
        Auswahl zu verwerfen. Der Frühausstieg bei unveränderter
        Besetzung ist wichtig: sonst würde das Auswahlfeld im
        Sekundentakt zurückgesetzt, während man es bedient.
        """

        names = snapshot.actor_names

        if names == self._roster_signature:
            return

        self._roster_signature = names

        self.player_filter.blockSignals(True)

        self.player_filter.clear()

        self.player_filter.addItem("Alle Spieler", ALL_PLAYERS)

        for name in names:

            self.player_filter.addItem(name, name)

        index = self.player_filter.findData(self._filter)

        if index >= 0:
            self.player_filter.setCurrentIndex(index)
        else:
            self._filter = ALL_PLAYERS

        self.player_filter.blockSignals(False)

    def _on_filter_changed(self, index: int):

        value = self.player_filter.itemData(index)

        if value is None:
            return

        self._filter = value

        self._apply_deep_analysis(self.service.current())

    def _cooldown_rows(self, states):

        return [
            MeterRowData(
                title=state.name,
                detail=state.actor_name,
                value=(
                    "bereit"
                    if state.ready
                    else f"{int(state.remaining)}s"
                ),
                ratio=state.progress,
                color=(
                    Colors.SUCCESS
                    if state.ready
                    else Colors.WARNING
                ),
            )
            for state in states
        ]

    # --------------------------------------------------

    def _apply_history(self):

        self.history_list.setEntries(
            EntryData(
                title=(
                    f"Pull {summary.pull_number} · "
                    f"{summary.encounter_name}"
                ),
                detail=(
                    f"{summary.clock} · "
                    f"Boss bei {summary.boss_health_percent:.1f} % · "
                    f"{summary.death_count} Ausfälle"
                    + (
                        f" · bester Schaden: {summary.best_damage_name} "
                        f"({format_per_second(summary.best_damage_value)})"
                        if summary.best_damage_name
                        else ""
                    )
                ),
                level="success" if summary.killed else "warning",
                trailing="Kill" if summary.killed else "Wipe",
            )
            for summary in self.service.history()
        )
