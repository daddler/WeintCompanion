"""
QUELLE - welchen Kampf willst du ansehen?

Die vierte der vier Perspektiven des Raid Centers. Sie beantwortet die
eine Frage, für die es bis 3.6.0 **drei** Orte gab: den Bereich
"Archiv" in der Navigation, den Knopf "Log wählen …" samt Fenster
darüber (auf WeintTV und in der Academy), und den Reiter "Verlauf" in
WeintTV mit den Pulls dieses Abends. Drei Orte für "welcher Kampf",
und keiner davon nannte die beiden anderen.

Hier stehen sie zusammen, in der Reihenfolge der Frage:

    1. Woher überhaupt      die Datenquelle (`SourceStrip`)
    2. Wann                 laufender Raid oder Archiv, und die drei
                            Abkürzungen (letzter Raid, letzter Kill,
                            bester Versuch)
    3. Die Liste            Raidabende links, Pulls je Boss rechts
    4. Diese Sitzung        die Pulls, die live mitgelaufen sind

**Der Archivbrowser ist derselbe wie zuvor** (`ArchiveBrowser`), nur
ohne Fenster darum: das Fenster ist mit 4.0 entfallen, weil es eine
Auswahl über genau die Ansicht legte, auf der man sie trifft. Ein
Nachbau der Liste wäre ab der ersten Änderung eine zweite Gruppierung.

**Der Zustand liegt nicht hier.** `RaidDataService` hält Modus,
Archivauswahl und Wiedergabe (`ArchiveState`, `ReplayState`); diese
Ansicht liest sie und ruft die Methoden des Dienstes. Zwei
Archivzustände wären zwei Wahrheiten über denselben Kampf - dieselbe
Überlegung, aus der WeintTV und die Academy sich schon immer *einen*
Snapshot geteilt haben.

**Zur Namensgebung**, weil sie hier eine echte Verwechslungsgefahr
auflöst: "Verlauf" hiess in WeintTV die Liste der in *dieser Sitzung*
abgeschlossenen Pulls (`PullSummary`, `history()`), und "Archiv" der
davon unabhängige Begriff "ein vergangener Bericht". Zwei Dinge, ein
Wort, zwei Reiter in zwei Bereichen. Auf dieser Ansicht stehen beide
untereinander und heissen, was sie sind: *Raidabende* und *Diese
Sitzung*.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core import archive_index as index
from core.raid_data_service import MODE_ARCHIVE, MODE_LIVE

from gui.widgets.raid.archive_browser import ArchiveBrowser
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.bar_table import format_per_second
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.source_strip import SourceStrip
from gui.widgets.wrapped_label import enable_wrap


#
# Wie viele Pulls dieser Sitzung die Liste unten trägt. Sechs, nicht
# zwölf: darunter steht nichts mehr, und die Liste der Raidabende
# darüber ist der Ort für alles, was länger zurückliegt.
#

SESSION_ROWS = 3


#
# Mindesthöhe der Liste. Ohne sie teilt Qt die Höhe nach den
# Wunschgrößen auf, und bei 720 px Fensterhöhe blieben der Liste rund
# 60 px - also genau dem Teil, wegen dem man diese Ansicht aufsucht.
# Alles andere auf dieser Ansicht ist knapp gehalten, damit sich das
# bei 1280 x 720 ohne Rollen ausgeht.
#

BROWSER_MIN_H = 180


class SourceView(QWidget):
    """
    Die Auswahl. Eine Ansicht, kein Ort - und kein Fenster.
    """

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(14)

        #
        # --------------------------------------------------
        # 1. Woher überhaupt
        # --------------------------------------------------
        #
        # Die Quellenzeile steht **hier** und nicht auf allen vier
        # Ansichten. Bis 3.6.0 stand sie dreimal da, weil es drei
        # Seiten waren; seit 4.0 nennt der Kopfblock die laufende
        # Quelle als Chip (mit Warnfarbe, wenn es eine Beispielquelle
        # ist) und führt mit einem Klick hierher - dorthin, wo man sie
        # auch wechseln kann. Eine Auskunft an vier Stellen ist vier
        # Stellen, an denen sie veralten kann.
        #

        root.addWidget(SourceStrip(self.service))

        #
        # --------------------------------------------------
        # 2. Wann - und die drei Abkürzungen
        # --------------------------------------------------
        #
        # Eine Zeile und nicht zwei. Bei 720 px Fensterhöhe ist jede
        # eingesparte Zeile Chrom eine Zeile Liste, und die Liste ist
        # das, wegen dem man diese Ansicht aufsucht. Inhaltlich gehören
        # sie ohnehin zusammen: erst *wann*, dann die drei Fragen, die
        # man dazu fast immer hat.
        #
        # Die Schnellauswahl wird in `core/archive_index.py`
        # entschieden - hier stehen nur die Knöpfe, und sie sind
        # abgeschaltet, solange sie nichts treffen würden.
        #

        picker_row = QHBoxLayout()

        picker_row.setContentsMargins(0, 0, 0, 0)

        picker_row.setSpacing(tokens.SPACE[2])

        self.mode_switch = SegmentedControl([
            ("Laufender Raid", MODE_LIVE),
            ("Archiv", MODE_ARCHIVE),
        ])

        self.mode_switch.valueChanged.connect(self._on_mode_changed)

        picker_row.addWidget(self.mode_switch)

        self.last_raid_button = HeroButton("Letzter Raid", primary=False)

        self.last_raid_button.clicked.connect(self._pick_last_raid)

        picker_row.addWidget(self.last_raid_button)

        self.last_kill_button = HeroButton("Letzter Kill", primary=False)

        self.last_kill_button.clicked.connect(self._pick_last_kill)

        picker_row.addWidget(self.last_kill_button)

        self.best_try_button = HeroButton("Bester Versuch", primary=False)

        self.best_try_button.clicked.connect(self._pick_best_try)

        picker_row.addWidget(self.best_try_button)

        self.status_label = enable_wrap(QLabel(""))

        self.status_label.setFont(font("small"))

        restyle(
            self.status_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        picker_row.addWidget(self.status_label, 1)

        root.addLayout(picker_row)

        #
        # --------------------------------------------------
        # 3. Die Liste
        # --------------------------------------------------
        #
        # Dasselbe Widget, das bis 3.6.0 auch im Fenster steckte -
        # ohne eigenen Kopf und ohne Schliessknopf, weil es hier ein
        # Ort ist und kein Vorhang.
        #

        self.browser = ArchiveBrowser(self.service)

        self.browser.setMinimumHeight(BROWSER_MIN_H)

        root.addWidget(self.browser, 1)

        #
        # --------------------------------------------------
        # 4. Diese Sitzung
        # --------------------------------------------------
        #
        # Was mitgelaufen ist, während die App offen war. Es kostet den
        # Bot nichts und ist deshalb sofort da - anders als ein
        # archivierter Pull, dessen Abruf Minuten dauert.
        #

        #
        # Eine Rubrik statt einer `SectionCard`: deren Symbol, Titel und
        # Untertitel kosten rund 50 px, die hier der Liste darüber
        # fehlen würden. Was die drei gesagt hätten, sagt das eine Wort
        # ebenso.
        #

        root.addWidget(
            eyebrow_label("DIESE SITZUNG · LIVE MITGELAUFEN")
        )

        self.session_list = EntryList(
            capacity=SESSION_ROWS,
            placeholder=(
                "Noch keine abgeschlossenen Pulls, seit die App läuft."
            ),
        )

        root.addWidget(self.session_list)

        #
        # Dass ein gewählter Pull geladen **ist**, merkt das Raid Center
        # selbst am Kontext (`same_pull()`) und schaltet dann auf die
        # Analyse um. Absichtlich dort und nicht hier: der Pull kann
        # auch über die Schnellauswahl oder einen Tiefenverweis aus der
        # Übersicht kommen, und drei Meldewege für dasselbe Ereignis
        # wären drei Stellen, an denen das Umschalten ausbleibt.
        #

        self.service.archiveChanged.connect(self._refresh)

        self.service.replayChanged.connect(self._refresh)

        self._refresh()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _on_mode_changed(self, value: str):

        if value == MODE_LIVE:

            self.service.show_live()

            return

        self.service.enter_archive_mode()

    def _pick_last_raid(self):
        """
        Den jüngsten Bericht wählen. Seine Pulls lädt der Dienst
        daraufhin selbst nach - ein zweiter Klick wäre eine Wartezeit,
        die nichts entscheidet.
        """

        state = self._archive()

        report = index.latest_report(state.reports)

        if report is None:
            return

        self.service.enter_archive_mode()

        self.service.select_archive_report(report.code)

    def _pick_last_kill(self):

        self._select(index.last_kill(self._archive().fights))

    def _pick_best_try(self):

        self._select(index.best_attempt(self._archive().fights))

    def _select(self, fight):

        state = self._archive()

        if fight is None or not state.selected_report:
            return

        self.service.select_archive_fight(
            state.selected_report,
            fight.fight_id,
        )

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _archive(self):

        return self.service.archive_state()

    def apply_session(self):
        """
        Die Pulls dieser Sitzung nachziehen.

        Getrennt von `_refresh()` und vom Raid Center gerufen: sie
        ändern sich mit dem Snapshot (ein Pull endet), nicht mit der
        Archivauswahl.
        """

        self.session_list.setEntries(
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

    def _refresh(self):

        state = self._archive()

        #
        # Die Wiedergabe ist ein dritter Modus des Dienstes, aber kein
        # dritter Knopf: man spielt immer einen Pull ab, den man vorher
        # gewählt hat. Ohne diese Zuordnung bliebe der Schalter auf
        # seinem alten Stand stehen - `SegmentedControl.setValue()` tut
        # bei einem unbekannten Wert stillschweigend nichts.
        #

        self.mode_switch.blockSignals(True)

        self.mode_switch.setValue(
            MODE_LIVE
            if state.mode == MODE_LIVE
            else MODE_ARCHIVE
        )

        self.mode_switch.blockSignals(False)

        self._update_quick(state)

        self._update_status(state)

    def _update_quick(self, state):
        """
        Ein Knopf, der nichts trifft, wird abgeschaltet und nicht
        versteckt - *lock, don't hide*, dieselbe Regel wie bei der
        Charakterzuordnung: ein Knopf, der je nach Lage verschwindet,
        lässt sich weder erklären noch danach fragen.
        """

        self.last_raid_button.setEnabled(
            index.latest_report(state.reports) is not None
        )

        self.last_kill_button.setEnabled(
            index.last_kill(state.fights) is not None
        )

        self.best_try_button.setEnabled(
            index.best_attempt(state.fights) is not None
        )

    def _update_status(self, state):

        reason = (
            state.fight_error
            or state.fights_error
            or state.reports_error
        )

        if reason and state.mode != MODE_LIVE:

            self.status_label.setText(reason)

            restyle(
                self.status_label,
                f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
            )

            return

        restyle(
            self.status_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        if state.fight_loading:

            #
            # Nur der Kurzstand. Wie lange es noch dauert und was
            # danach passiert, steht in der Wartekarte des Raid Centers
            # - hier stünde es ein zweites Mal.
            #

            self.status_label.setText(index.loading_text(state))

            return

        if state.mode == MODE_LIVE:

            self.status_label.setText(
                "Die Zahlen kommen aus dem laufenden Log eures Raids."
            )

            return

        #
        # Benannt wird, was **geladen** ist, und nicht, was angeklickt
        # wurde: nach einem fehlgeschlagenen Abruf stand in den alten
        # Ausklapplisten weiter der Pull, den man gar nicht vor sich
        # hatte. `selection_text()` zieht diese Linie für alle
        # Anzeigen gemeinsam.
        #

        self.status_label.setText(
            index.selection_text(state)
            or "Noch kein Pull gewählt - wähle links einen Raidabend."
        )

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def on_enter(self):

        self._refresh()

        self.apply_session()

    def apply(self, snapshot):
        """
        Der gemeinsame Eingang aller Ansichten.

        Diese hier zeigt keinen Snapshot - sie wählt ihn aus. Was sich
        mit ihm ändert, ist einzig die Liste der Pulls dieser Sitzung:
        ein Pull endet, und dann steht er darin.
        """

        self.apply_session()
