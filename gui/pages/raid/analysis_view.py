"""
ANALYSE - die Tiefenauswertung des Pulls, den man vor sich hat.

Die zweite der vier Perspektiven des Raid Centers: erhaltener Schaden
und wie viel davon vermeidbar war, Wirkzeiten (DoTs/HoTs/Selbstbuffs),
Aktivzeit, Cooldown-Nutzung mit Zeitstrahl, Unterbrechungen, Dispels,
Mechanikfehler und Warnungen.

Wie die Live-Ansicht rechnet diese Datei **nichts**: sie schreibt
Werte aus dem `RaidSnapshot` in Widgets. Die Rechnungen dahinter liegen
in `analyzer/analysis/` (Rangliste, Schadensbuckets, Cooldown-Mathematik)
und werden von der Academy-Bewertung ebenso gelesen - deshalb können
Analyse und Bewertung gar nicht auseinanderlaufen.

**Der Spielerfilter bleibt ein Anzeigefilter.** Er sagt nicht, wer
"ich" bin: die Raidansicht ist dazu da, sich auch andere anzusehen, und
ein Blick auf den Kollegen darf die Ingame-Identität nicht umstellen
(siehe `analyzer/names.py`). Was sich mit 4.0 geändert hat, ist der Weg
in die andere Richtung: ein **Klick auf eine Zeile** meldet den Spieler
als ausdrückliche Wahl an das Raid Center (`playerRequested`), das
daraufhin den Kontextcharakter setzt und auf *Lernen* umschaltet - der
Pull bleibt derselbe. Vorher führte derselbe Klick in einen anderen
Hauptbereich, wo Charakter und Pull erneut zu wählen waren.

Ebenfalls nicht mehr hier: Reiterumschalter, Quellenzeile,
Archiv-Wähler, Wiedergabeleiste, Wartekarte. Sie stehen einmal im Raid
Center darüber.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from analyzer.analysis import cooldowns as cd_math
from analyzer.analysis.spec_reference import cooldown_hint, reference_hint
from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    MECHANIC_SOURCE_LOCAL,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    RaidSnapshot,
)

from core.resources import Resources

from gui.theme.colors import Colors
from gui.widgets.card import Card
from gui.widgets.section_card import SectionCard
from gui.widgets.tv.analysis_gap import (
    BLOCK_COOLDOWN_USAGE,
    BLOCK_HEAL_COOLDOWNS,
    BLOCK_RAID_COOLDOWNS,
    analysis_gap_text,
    block_gap_text,
)
from gui.widgets.tv.cooldown_timeline import (
    CooldownTimeline,
    TimelineRow,
    clock as timeline_clock,
)
from gui.widgets.tv.data_table import (
    DataTable,
    TableCell,
    TableColumn,
    TableRowData,
)
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.meter_row_list import MeterRowData, MeterRowList


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


class AnalysisView(QWidget):
    """
    Die Tiefenauswertung. Eine Ansicht, kein Ort.
    """

    #
    # "Diesen Spieler ansehen" - das Raid Center macht daraus den
    # Kontextcharakter und den Wechsel auf *Lernen*.
    #

    playerRequested = Signal(str)

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        #
        # Auf welchen Spieler die Analyse eingeschränkt ist. Ohne
        # Filter wären 25 Spieler mal sechs Tabellen unlesbar.
        #

        self._filter = ALL_PLAYERS

        self._roster_signature = ()

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(14)

        self._build(root)

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

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
    def _build(self, layout: QVBoxLayout):

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

        #
        # Dieser Filter ist reine Anzeige - er sagt NICHT, wer "ich"
        # bin. Das ist Absicht: die Raid-Ansicht ist dazu da, sich
        # andere anzusehen, und ein Blick auf den Kollegen darf nicht
        # die Ingame-Identität umstellen. Weil man das dem Auswahlfeld
        # nicht ansieht, steht der tatsächlich gewählte
        # Academy-Charakter daneben; die Abweichung wird damit dort
        # sichtbar, wo sie entsteht.
        #
        self.identity_hint = QLabel("")

        self.identity_hint.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_FAINT};"
            "background:transparent;border:none;"
        )

        filter_row.addWidget(self.identity_hint)

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
        # Aktivzeit
        #
        # Daneben stand bis 3.6.0 eine Karte "Laufwege" mit einer
        # Meterzahl je Spieler. Sie ist ersatzlos weg, und das ist
        # keine Aufräumaktion: WarcraftLogs kennt keine
        # Distanzmetrik. Die Zahl entstand daraus, dass der Bot die
        # Abstände zwischen den Positionsangaben aufeinanderfolgender
        # Ereignisse als Gerade aufsummiert - wer zwischen zwei
        # Ereignissen einen Bogen läuft, wird unterschätzt, und wer
        # gar keine Ereignisse erzeugt, taucht überhaupt nicht auf.
        # Eine Zahl, die sich nicht belegen lässt, ist in einer
        # Auswertung schlechter als keine: sie sieht aus wie eine
        # Messung. Was der Log über Bewegung wirklich hergibt, steht
        # in der Karte "Vermeidbarer Schaden" - ein Treffer, den man
        # hätte vermeiden können, ist ein Ereignis und keine
        # Schätzung.
        #

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

        deep.addWidget(activity_card)

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
                TableColumn("Art", weight=2),
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
            "Wann ein Cooldown kam, wie lange er danach unten war - "
            "und wo er bereit war und nicht kam.",
        )

        #
        # Der Zeitstrahl steht **über** der Tabelle, weil er die
        # Frage beantwortet, die man zuerst hat: wann war die Lücke.
        # Die Tabelle bleibt darunter für die Zahlen dahinter.
        #
        # Er zeigt einen Spieler, nicht fünfundzwanzig: bei 25
        # Spielern mit je sechs Cooldowns wären es 150 Zeilen, und
        # der Strahl lebt davon, dass man die Zeilen untereinander
        # vergleichen kann. Welcher Spieler das ist, entscheidet der
        # Filter über der Seite (sonst: der eigene Charakter).
        #

        self.cooldown_timeline = CooldownTimeline()

        cooldown_usage_card.addWidget(self.cooldown_timeline)

        self.cooldown_legend = QLabel("")

        self.cooldown_legend.setWordWrap(True)

        self.cooldown_legend.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        cooldown_usage_card.addWidget(self.cooldown_legend)

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

    # --------------------------------------------------
    # Snapshot anwenden
    # --------------------------------------------------

    def apply(self, snapshot: RaidSnapshot):
        """
        Der eine Eingang. Das Raid Center reicht denselben Snapshot an
        alle Ansichten - eine Ansicht, die sich ihren Stand daneben
        selbst holt, zeigte in einer Wiedergabe nachweislich eine
        andere Sekunde als die daneben.
        """

        #
        # Erst der Platzhalter, dann die Zeilen: bleibt die Liste
        # leer, soll dort stehen, ob die Quelle nichts geliefert hat
        # oder der Raid nichts gezündet hat. Ohne die Unterscheidung
        # liest sich eine Datenlücke wie ein Befund über den Raid.
        #

        self.raid_cooldowns.setPlaceholder(
            block_gap_text(snapshot, BLOCK_RAID_COOLDOWNS)
            or "Keine Raid-Cooldowns erkannt."
        )

        self.raid_cooldowns.setRows(
            self._cooldown_rows(snapshot.raid_cooldowns)
        )

        self.heal_cooldowns.setPlaceholder(
            block_gap_text(snapshot, BLOCK_HEAL_COOLDOWNS)
            or "Keine Heil-Cooldowns erkannt."
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

        self._apply_activity(snapshot)

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

    def _focused_actor(self, snapshot: RaidSnapshot):
        """
        Der Spieler, auf den der Filter gerade zeigt - oder None,
        solange der ganze Raid gemeint ist.

        Nur für ihn lässt sich sagen, was zu erwarten wäre: eine
        Aufzählung über 25 Spezialisierungen wäre kein Hinweis mehr,
        sondern eine Wand.
        """

        if self._filter == ALL_PLAYERS:
            return None

        return snapshot.actor_of(self._filter)

    def _uptime_placeholder(
        self,
        snapshot: RaidSnapshot,
        kind: str,
        label: str,
    ) -> str:

        hint = reference_hint(self._focused_actor(snapshot), kind)

        if not hint:
            return f"Keine Angaben zu {label}-Uptimes."

        return (
            f"Keine Angaben zu {label}-Uptimes. Erwartet für diese "
            f"Spezialisierung: {hint}."
        )

    def _apply_uptimes(self, snapshot: RaidSnapshot):

        for widget, rows, kind, label in (
            (self.dot_uptimes, snapshot.dot_uptimes, UPTIME_DOT, "DoT"),
            (self.hot_uptimes, snapshot.hot_uptimes, UPTIME_HOT, "HoT"),
            (self.buff_uptimes, snapshot.buff_uptimes, UPTIME_BUFF, "Buff"),
        ):

            #
            # Der Platzhalter nennt die Fähigkeiten der gewählten
            # Spezialisierung, statt nur "keine Angaben" zu sagen.
            # "Meine Blutung fehlt" und "über meine Blutung ist nichts
            # bekannt" sahen vorher gleich aus - und das war der
            # eigentliche Mangel dieser Karten.
            #

            widget.setPlaceholder(
                self._uptime_placeholder(snapshot, kind, label)
            )

            widget.setRows(
                MeterRowData(
                    title=entry.ability,
                    detail=(
                        entry.actor_name
                        + (
                            f" · {entry.applications}× aufgelegt"
                            if entry.applications
                            #
                            # Eine Null ist hier keine Lücke, sondern
                            # ein Befund: die Quelle liefert diese Art
                            # von Wirkungsdauern, für diese Fähigkeit
                            # aber keine (siehe
                            # analyzer/analysis/spec_reference.py).
                            #
                            else " · nie aufgelegt"
                            if entry.uptime_percent <= 0
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

    def _apply_activity(self, snapshot: RaidSnapshot):
        """
        Aktivzeit - die eine der beiden früheren Karten, die auf
        Ereignissen beruht und nicht auf geschätzten Metern (siehe
        den Aufbau der Karte weiter oben).
        """

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

    #
    # Wie eine Cooldown-Kategorie in der Tabelle heisst. Aus dem
    # Modell und nicht aus der Zeile: "personal" ist der Schlüssel,
    # "auf Abklingzeit" die Aussage.
    #

    CATEGORY_TEXT = {
        CD_PERSONAL: "auf Abklingzeit",
        CD_DEFENSIVE: "defensiv",
        CD_RAID: "Raid",
        CD_HEAL: "Heilung",
    }

    def _apply_cooldown_usage(self, snapshot: RaidSnapshot):

        hint = cooldown_hint(self._focused_actor(snapshot))

        #
        # Zwei verschiedene Auskünfte, und die Reihenfolge ist keine
        # Geschmacksfrage: liefert die Quelle den Block gar nicht, ist
        # das die Ursache und muss zuerst stehen. Der Spec-Hinweis
        # ("erwartet für diese Spezialisierung") beantwortet die
        # andere Frage - was hier stünde, wenn Daten da wären - und
        # hängt sich deshalb hinten an.
        #

        gap = block_gap_text(snapshot, BLOCK_COOLDOWN_USAGE)

        placeholder = (
            (gap or "Keine Angaben zur Cooldown-Nutzung.")
            + (
                f" Erwartet für diese Spezialisierung: {hint}."
                if hint
                else ""
            )
        )

        self.cooldown_table.setPlaceholder(placeholder)

        rows = sorted(
            (
                usage
                for usage in snapshot.cooldown_usage
                if self._keep(usage.actor_name)
            ),
            #
            # Zuerst, was auf Abklingzeit gehört und am wenigsten kam
            # - dort liegt der Handlungsbedarf. Defensives danach: es
            # ist eine Auskunft, kein Befund.
            #
            key=lambda usage: (
                not cd_math.counts_towards_usage(usage.category),
                usage.efficiency if usage.possible else 1.0,
            ),
        )

        self._apply_cooldown_timeline(snapshot, placeholder)

        self.cooldown_table.setRows(
            TableRowData(
                key=usage.actor_name,
                cells=(
                    TableCell(usage.ability, Colors.TEXT),
                    TableCell(usage.actor_name),
                    TableCell(
                        self.CATEGORY_TEXT.get(usage.category, "-"),
                        Colors.TEXT_MUTED,
                    ),
                    #
                    # Eine Quote gibt es nur, wo es eine Obergrenze
                    # gibt. Bei einem Defensivcooldown steht die
                    # Anzahl allein da - "3" und nicht "3 von 6", und
                    # schon gar nicht gelb eingefärbt: er gehört
                    # aufgehoben, nicht abgearbeitet.
                    #
                    TableCell(
                        f"{usage.uses}/{usage.possible}"
                        if usage.possible
                        else str(usage.uses),
                        (
                            (
                                Colors.SUCCESS
                                if usage.efficiency >= 0.85
                                else Colors.WARNING
                            )
                            if usage.possible
                            else Colors.TEXT_MUTED
                        ),
                        ratio=usage.efficiency if usage.possible else 0.0,
                    ),
                    #
                    # Die Ausrichtung aufs Heldentum ist nur bei
                    # grossen Cooldowns eine Frage. Bei einem
                    # Ein-Minuten-Cooldown heisst "nicht im Fenster"
                    # gar nichts, und eine graue Null dort las sich
                    # wie ein Versäumnis.
                    #
                    TableCell(
                        self._burst_text(usage, snapshot),
                        (
                            Colors.SUCCESS
                            if usage.in_burst
                            else Colors.TEXT_MUTED
                        ),
                    ),
                    TableCell(
                        ", ".join(
                            timeline_clock(at)
                            for at in usage.cast_times
                        )
                        or "nicht genutzt",
                        (
                            Colors.TEXT_MUTED
                            if usage.cast_times or not usage.possible
                            else Colors.ERROR
                        ),
                    ),
                ),
            )
            for usage in rows
        )

    def _timeline_player(self, snapshot: RaidSnapshot) -> str:
        """
        Wessen Cooldowns der Zeitstrahl zeigt.

        Der Filter entscheidet; ohne Filter der eigene Charakter, den
        die Academy ohnehin schon kennt (dieselbe Quelle wie der
        Hinweis "Ingame „Nur ich" zeigt: …" über der Seite - eine
        zweite Auflösung desselben Namens liefe irgendwann anders
        aus). Leerer String heisst "niemand", nicht "alle": ein Strahl
        über fünfundzwanzig Spieler wären 150 Zeilen.
        """

        actor = self._focused_actor(snapshot)

        if actor is not None:
            return actor.name

        academy = getattr(self.manager, "academy", None)

        name = academy.player_name() if academy is not None else ""

        return name if snapshot.actor_of(name) is not None else ""

    def _burst_text(self, usage, snapshot: RaidSnapshot) -> str:

        if not snapshot.heroism_windows:
            return "-"

        if not cd_math.is_major(usage.cooldown):
            return "-"

        return str(usage.in_burst)

    def _apply_cooldown_timeline(
        self,
        snapshot: RaidSnapshot,
        placeholder: str,
    ):
        """
        Den Zeitstrahl für **einen** Spieler füllen.

        Für welchen, entscheidet derselbe Filter, der auch die
        Tabellen einschränkt; ohne Filter der eigene Charakter. Ein
        Strahl über fünfundzwanzig Spieler wären 150 Zeilen, und
        untereinander vergleichen kann man dann nichts mehr.
        """

        name = self._timeline_player(snapshot)

        duration = snapshot.pull_seconds

        rows = [
            usage
            for usage in snapshot.cooldown_usage
            if usage.actor_name == name
        ]

        #
        # Drei verschiedene Gründe für einen leeren Strahl, drei
        # verschiedene Sätze - dieselbe Regel wie in
        # `analysis_gap.py`: eine Datenlücke darf nicht wie ein Befund
        # aussehen, und "hier ist niemand ausgewählt" ist ein dritter
        # Fall.
        #

        if not name:

            self.cooldown_timeline.setPlaceholder(
                "Der Zeitstrahl zeigt einen Spieler. Wähle oben einen "
                "aus - oder verknüpfe deinen Charakter, dann steht "
                "hier deiner."
            )

        elif not snapshot.cooldown_usage:

            self.cooldown_timeline.setPlaceholder(placeholder)

        else:

            self.cooldown_timeline.setPlaceholder(
                f"Für {name} liegen in diesem Kampf keine "
                "Einsatzzeitpunkte vor."
            )

        if not rows or duration <= 0:

            self.cooldown_timeline.setTimeline((), 0.0, ())

            self.cooldown_legend.setVisible(False)

            return

        self.cooldown_timeline.setTimeline(
            [
                TimelineRow(
                    label=usage.ability,
                    casts=usage.cast_times,
                    cooldown=usage.cooldown,
                    gaps=tuple(
                        (gap.start, gap.until)
                        for gap in cd_math.ready_gaps(
                            usage.cast_times,
                            usage.cooldown,
                            duration,
                        )
                    ),
                    value=(
                        f"{usage.uses}/{usage.possible}"
                        if usage.possible
                        else f"{usage.uses}×"
                    ),
                    judged=cd_math.counts_towards_usage(usage.category),
                    tone=(
                        ""
                        if cd_math.counts_towards_usage(usage.category)
                        else "info"
                    ),
                )
                for usage in sorted(
                    rows,
                    key=lambda usage: (
                        not cd_math.counts_towards_usage(usage.category),
                        -usage.cooldown,
                    ),
                )
            ],
            duration,
            [
                (window.start, window.end)
                for window in snapshot.heroism_windows
            ],
        )

        self.cooldown_legend.setVisible(True)

        self.cooldown_legend.setText(
            f"Zeitstrahl: {name} · Balken = Einsatz und die Zeit, die "
            "der Cooldown danach unten war · gelb = bereit und nicht "
            "genutzt · blau hinterlegt = Heldentum · blaue Balken "
            "sind defensive oder Raid-Cooldowns und werden nicht auf "
            "eine Quote gerechnet."
        )

    # --------------------------------------------------

    def _sync_filter(self, snapshot: RaidSnapshot):
        """
        Die Spielerliste des Filters mitziehen, ohne die laufende
        Auswahl zu verwerfen. Der Frühausstieg bei unveränderter
        Besetzung ist wichtig: sonst würde das Auswahlfeld im
        Sekundentakt zurückgesetzt, während man es bedient.
        """

        self._sync_identity_hint()

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

    def _sync_identity_hint(self):
        """
        Nennt den Charakter, den das Addon als "ich" behandelt.

        `setText()` vergleicht selbst nicht, aber der Text ändert sich
        nur bei einem Charakterwechsel - anders als bei
        `setStyleSheet()` ist hier nichts pro Bild zu sparen.
        """

        academy = getattr(self.manager, "academy", None)

        name = academy.player_name() if academy is not None else ""

        text = (
            f"Ingame „Nur ich“ zeigt: {name}"
            if name
            else ""
        )

        if self.identity_hint.text() != text:
            self.identity_hint.setText(text)

    def _on_filter_changed(self, index: int):

        value = self.player_filter.itemData(index)

        if value is None:
            return

        #
        # Nur die Anzeige. Die Academy-Auswahl bleibt unberührt -
        # begründet oben beim Anlegen von identity_hint. Der
        # ausdrückliche Weg ist der Sprung "in der Academy ansehen"
        # (playerRequested).
        #
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
