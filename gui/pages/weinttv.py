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
    Analyse   Cooldowns, Verbrauchsgüter, Fehler, Warnungen
    Verlauf   Abgeschlossene Pulls

Aktualisiert wird nur, solange die Seite auch sichtbar ist:
on_enter() meldet sich beim Service an, on_leave() wieder ab. Beide
Haken ruft MainWindow.change_page() auf.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analyzer.models import RaidSnapshot

from core.resources import Resources

from gui.theme.colors import Colors
from gui.theme.wow_colors import class_color, role_label

from gui.widgets.card import Card
from gui.widgets.section_card import SectionCard
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.archive_picker import ArchivePicker
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.meter_bar import MeterBar
from gui.widgets.tv.meter_row_list import MeterRowData, MeterRowList
from gui.widgets.tv.metric_tile import MetricTile
from gui.widgets.tv.ranking_list import RankingList, format_per_second
from gui.widgets.tv.timer_chip import TimerChip


TAB_LIVE = "live"
TAB_ANALYSIS = "analysis"
TAB_HISTORY = "history"


class WeintTvPage(QWidget):

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.service = manager.raid_data

        self._attached = False

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
            self._apply_snapshot
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

        self.mechanics.setEntries(
            EntryData(
                title=issue.mechanic,
                detail=issue.actor_name,
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
