"""
LERNEN - was soll ich als Nächstes verbessern?

Die dritte der vier Perspektiven des Raid Centers. Sie bewertet genau
den Pull, den der Kopfblock darüber nennt, und zwar für genau den
Charakter, der dort gewählt ist - beides kommt von aussen, diese
Ansicht wählt nichts selbst aus.

**Was sich mit 4.0 geändert hat**, und es ist mehr als eine
Umbenennung: die Academy war ein *Lernzentrum* mit drei Reitern
(Übersicht, Trainingsplan, Katalog). Wer wissen wollte, woran er
arbeiten soll, musste dafür die richtige Reiterseite finden - die
Antwort lag verteilt über eine hervorgehobene Bewertungskachel, ihren
Kleintext, eine Lektionskarte eine Seite weiter und einen Knopf darauf.
Die erste Frage der Seite lautete faktisch "welche Academy-Seite
möchte ich öffnen?".

Jetzt ist es **eine Spalte** mit einer Reihenfolge, die der Frage
folgt:

    1. Deine größten Baustellen   (FocusCard - Bereich, Sterne,
                                   Begründung, Lektion, der Moment im
                                   Kampf)
    2. Die vollständige Bewertung (sechs Bereiche - der Beleg)
    3. Die Zahlen dahinter        (sechs Kennzahlen)
    4. Der Trainingsplan          (die Lektionen der Reihe nach)
    5. Fortschritt und Lernkurve
    6. Der Katalog                (Konfiguration, deshalb zuletzt)

Die **Bewertungslogik ist unverändert**: Profil und Trainingsplan holt
diese Ansicht wie bisher fertig vom `AcademyService`, der seinerseits
den Analyzer aufruft. In dieser Datei steht ausschließlich Darstellung.

Ein Detail zur Aktualisierung, das bleibt: die Sternebewertungen dürfen
im Sekundentakt mitlaufen, die Lektionskarten nicht - sie werden nur neu
gebaut, wenn sich der Plan tatsächlich ändert. Sonst entstünde bei jedem
Snapshot eine komplett neue Kartenliste, was sichtbar flackern und jede
Interaktion unterbrechen würde.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import Signal

from analyzer.academy.lessons import lessons_in_category
from analyzer.academy.models import (
    CATEGORY_HINTS,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    STATUS_PASSED,
    STATUS_UNKNOWN,
    PlayerProfile,
    TrainingPlan,
)
from analyzer.models import RaidSnapshot

from core.academy_dummy_sync import (
    practice_for_lessons,
    practice_payload,
)
from core.raid_data_service import SOURCE_MOCK
from core.resources import Resources

from gui.navigation import RAID_VIEW_ANALYSIS, RAID_VIEW_SOURCE
from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.theme.wow_colors import class_color, class_label, role_label

from gui.widgets.academy.catalog_list import CatalogList, CatalogRowData
from gui.widgets.academy.focus_card import FocusCard
from gui.widgets.academy.history_card import HistoryCard
from gui.widgets.academy.lesson_card import LessonCard
from gui.widgets.academy.rating_grid import RatingGrid
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.section_card import SectionCard
from gui.widgets.tv.analysis_gap import (
    ACTION_ARCHIVE,
    academy_empty_action,
    academy_empty_text,
    focus_placeholder,
    rating_gap_text,
)
from gui.widgets.tv.encounter_meta import average_text
from gui.widgets.tv.meter_bar import MeterBar
from gui.widgets.tv.metric_tile import MetricTile


class LearnView(QWidget):
    """
    Das Coaching zu diesem Pull. Eine Ansicht, kein Ort.
    """

    #
    # Auf eine andere Perspektive desselben Pulls wechseln - der
    # Kontext bleibt dabei stehen, das Raid Center schaltet nur den
    # Stapel um.
    #

    viewRequested = Signal(str)

    #
    # Eine Sekunde im Kampf ansehen. Das Raid Center startet die
    # Wiedergabe, springt dorthin und zeigt die Live-Ansicht - diese
    # Datei weiss von der Wiedergabe nichts (siehe
    # docs/systems/archive-and-replay.md: die Academy hat nie eigenen
    # Wiedergabecode gehabt, und das bleibt so).
    #

    momentRequested = Signal(float)

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        self.academy = manager.academy

        #
        # Merker, damit nur bei echten Änderungen neu gebaut wird.
        #

        self._plan_signature = None

        #
        # Die Kurve wird nur neu gezeichnet, wenn ein Pull dazugekommen
        # ist - siehe `_apply_history()`.
        #

        self._history_signature = None

        self._profile = PlayerProfile()

        self._plan = TrainingPlan()

        self.catalog_cards = {}

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(16)

        self._build(root)

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build(self, layout: QVBoxLayout):

        #
        # --------------------------------------------------
        # Leerzustand
        # --------------------------------------------------
        #
        # Ohne ausgewerteten Kampf stand hier ein Name "-", sechs
        # Kacheln "noch keine Daten", drei Kennzahlen "-" und "0 von 0
        # Lektionen" - ein Formular ohne Inhalt, das keine der beiden
        # Fragen beantwortet, die man davor hat: was fehlt, und was
        # kann ich tun. Diese Karte beantwortet beide, und der Knopf
        # daneben führt genau dorthin. Sie verschwindet, sobald ein
        # Kampf da ist.
        #

        self.empty_card = Card(accent=True)

        self.empty_card.addWidget(
            eyebrow_label("NOCH KEINE AUSWERTUNG", Colors.PRIMARY_HOVER)
        )

        self.empty_text = QLabel("")

        self.empty_text.setWordWrap(True)

        self.empty_text.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        self.empty_card.addWidget(self.empty_text)

        empty_row = QHBoxLayout()

        empty_row.addStretch()

        self.empty_button = HeroButton("Pull auswählen …")

        #
        # Der Knopf führt in die Quellenansicht und nicht mehr in
        # ein Fenster darüber: die Liste der Raidabende ist seit 4.0
        # eine der vier Perspektiven und kein Dialog.
        #

        self.empty_button.clicked.connect(
            lambda: self.viewRequested.emit(RAID_VIEW_SOURCE)
        )

        empty_row.addWidget(self.empty_button)

        self.empty_card.addLayout(empty_row)

        self.empty_card.setVisible(False)

        layout.addWidget(self.empty_card)

        #
        # --------------------------------------------------
        # Die größten Baustellen
        # --------------------------------------------------
        #
        # Das Erste auf der Seite, weil es die Frage ist, mit der man
        # hinsieht. Alles darunter ist Beleg dafür: die vollständige
        # Bewertung, die Zahlen, der Plan, die Kurve.
        #

        self.focus_card = FocusCard()

        self.focus_card.lessonRequested.connect(self.show_lesson)

        self.focus_card.momentRequested.connect(self.momentRequested)

        self.focus_card.analysisRequested.connect(
            lambda _category: self.viewRequested.emit(RAID_VIEW_ANALYSIS)
        )

        layout.addWidget(self.focus_card)

        #
        # Charakterkarte
        #

        profile_card = Card()

        name_row = QHBoxLayout()

        name_row.setSpacing(12)

        self.profile_name = QLabel("-")

        self.profile_name.setStyleSheet(
            f"font-size:22px;font-weight:700;color:{Colors.WHITE};"
            "letter-spacing:-0.01em;background:transparent;border:none;"
        )

        name_row.addWidget(self.profile_name)

        self.profile_title = QLabel("")

        self.profile_title.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        name_row.addWidget(self.profile_title)

        name_row.addStretch()

        self.profile_meta = QLabel("")

        self.profile_meta.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        name_row.addWidget(self.profile_meta)

        profile_card.addLayout(name_row)

        self.profile_note = QLabel("")

        self.profile_note.setWordWrap(True)

        self.profile_note.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        self.profile_note.setVisible(False)

        profile_card.addWidget(self.profile_note)

        layout.addWidget(profile_card)

        #
        # Bewertung
        #

        #
        # Sechs Bewertungskacheln statt sechs Zeilen (§6.3): jede
        # Kachel steht für sich, und genau eine - der schwächste
        # Bereich - hebt sich ab. RatingGrid kapselt sowohl die
        # Kachelform als auch die Haltepunkt-Spaltenzahl (6 -> 3 -> 2),
        # siehe on_layout_changed() weiter unten.
        #

        self.rating_grid = RatingGrid(
            CATEGORY_ORDER,
            CATEGORY_LABELS,
            CATEGORY_HINTS,
        )

        layout.addWidget(self.rating_grid)

        #
        # Erklärt, warum mehrere Bereiche unbewertet bleiben, wenn die
        # Quelle keine Tiefenauswertung liefert. Ohne diesen Satz
        # stünden dort sechs "noch keine Daten"-Kacheln, und der
        # naheliegende Schluss wäre "die Academy ist kaputt" statt
        # "diese Quelle kann das noch nicht".
        #

        self.rating_notice = QLabel("")

        self.rating_notice.setWordWrap(True)

        self.rating_notice.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        self.rating_notice.setVisible(False)

        layout.addWidget(self.rating_notice)

        #
        # Kennzahlen der Tiefenauswertung
        #
        # Die Zahlen, auf denen die Bewertungen beruhen - sichtbar
        # neben den Sternen, damit eine Bewertung nicht als Urteil
        # ohne Beleg dasteht.
        #
        # Sechs statt drei, und die drei neuen sind nicht Zierat: sie
        # stehen für Zahlen, die im Snapshot längst lagen und auf
        # dieser Seite nirgends auftauchten, obwohl die Bewertung
        # daneben aus ihnen entsteht. Wer bei "Mechaniken 2 Sterne"
        # wissen will, woran das liegt, findet die verpasste
        # Unterbrechung sonst nur im Fliesstext der Kachel.
        #
        # Ein Raster und keine Zeile: sechs Kacheln nebeneinander sind
        # bei 960 px Fensterbreite je 140 px breit, und "3 von 5
        # genutzt" bricht darin um.
        #

        self.tile_grid = QGridLayout()

        self.tile_grid.setSpacing(14)

        self.tile_avoidable = MetricTile("VERMEIDBAR", "-")
        self.tile_activity = MetricTile("AKTIVZEIT", "-")
        self.tile_cooldowns = MetricTile("COOLDOWNS", "-")
        self.tile_interrupts = MetricTile("UNTERBRECHUNGEN", "-")
        self.tile_deaths = MetricTile("TODE", "-")
        self.tile_supplies = MetricTile("VORBEREITUNG", "-")

        self._tiles = (
            self.tile_avoidable,
            self.tile_activity,
            self.tile_cooldowns,
            self.tile_interrupts,
            self.tile_deaths,
            self.tile_supplies,
        )

        self._layout_tiles(3)

        layout.addLayout(self.tile_grid)

        #
        # --------------------------------------------------
        # Der Trainingsplan
        # --------------------------------------------------
        #
        # Bis 3.6.0 ein eigener Reiter. Er steht jetzt in derselben
        # Spalte, weil er die Fortsetzung der Baustellen darüber ist und
        # keine zweite Ansicht: "woran arbeiten" und "in welcher
        # Reihenfolge" sind eine Frage.
        #

        plan_wrap = QWidget()

        self.plan_layout = QVBoxLayout(plan_wrap)

        self.plan_layout.setContentsMargins(0, 0, 0, 0)

        self.plan_layout.setSpacing(14)

        self.plan_layout.addWidget(
            eyebrow_label("DEIN TRAININGSPLAN")
        )

        self.plan_placeholder = QLabel(
            "Sobald ein Kampf ausgewertet wurde, entsteht hier "
            "automatisch ein Trainingsplan."
        )

        self.plan_placeholder.setWordWrap(True)

        self.plan_placeholder.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        self.plan_layout.addWidget(self.plan_placeholder)

        #
        # Warum der Plan so sortiert ist. Er steht nur da, wenn die
        # Lernkurve die Reihenfolge bestimmt hat: die Sterne auf der
        # Übersicht gehören zum angezeigten Kampf, und eine
        # Reihenfolge, die ihnen widerspricht, sähe ohne diesen Satz
        # nach einem Fehler aus.
        #

        self.plan_note = QLabel("")

        self.plan_note.setWordWrap(True)

        self.plan_note.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        self.plan_note.setVisible(False)

        self.plan_layout.addWidget(self.plan_note)

        #
        # Die Übungsserie am Trainingsdummy. Sie entsteht aus den
        # Sitzungen, die das Addon meldet, wurde gespeichert - und
        # bis 2.8.0 nirgends gezeigt: wer zwei Tage hintereinander
        # geübt hatte, sah davon nichts, und am dritten erschien
        # wortlos ein Haken. Genau der Kreis, für den es den
        # Rotationshelfer gibt, war an seiner sichtbarsten Stelle
        # unsichtbar.
        #

        self.practice_note = QLabel("")

        self.practice_note.setWordWrap(True)

        self.practice_note.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        self.practice_note.setVisible(False)

        self.plan_layout.addWidget(self.practice_note)

        self.plan_layout.addStretch()

        self._lesson_cards: list[LessonCard] = []

        layout.addWidget(plan_wrap)

        #
        # Fortschritt
        #

        progress_card = SectionCard(
            Resources.backup(),
            "Fortschritt",
            "Erledigte Lektionen dieses Charakters.",
        )

        self.progress_bar = MeterBar(height=8)

        progress_card.addWidget(self.progress_bar)

        progress_row = QHBoxLayout()

        self.progress_label = QLabel("0 von 0 Lektionen")

        self.progress_label.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        progress_row.addWidget(self.progress_label)

        progress_row.addStretch()

        self.reset_button = HeroButton("Lernpfad zurücksetzen", primary=False)

        self.reset_button.clicked.connect(
            self._reset_progress
        )

        progress_row.addWidget(self.reset_button)

        progress_card.addLayout(progress_row)

        layout.addWidget(progress_card)

        #
        # Verlauf über mehrere Pulls (§6.3) - die Lernkurve. Sie
        # kommt nicht aus dem gerade gezeigten Snapshot, sondern aus
        # den aufgezeichneten Pulls dieses Charakters (siehe
        # core/academy_history.py); gezeichnet wird sie in
        # `_apply_history()`.
        #

        self.history_card = HistoryCard()

        layout.addWidget(self.history_card)


    # --------------------------------------------------
    # Aufbau: Trainingsplan
    # --------------------------------------------------

        #
        # --------------------------------------------------
        # Der Katalog
        # --------------------------------------------------
        #
        # Zuletzt und mit Absicht: er ist **Konfiguration** und keine
        # Auskunft über diesen Pull. Als eigener Reiter stand er
        # gleichrangig neben der Bewertung, obwohl man ihn einmal
        # einstellt und danach nie wieder aufsucht.
        #

        self.catalog_lists = {}

        layout.addWidget(eyebrow_label("LEKTIONSKATALOG"))

        hint = QLabel(
            "Alle Lektionen sind standardmäßig aktiv. Wer eine "
            "abwählt, nimmt sie aus dem Trainingsplan - neu "
            "hinzukommende Lektionen bleiben davon unberührt und "
            "erscheinen automatisch."
        )

        hint.setWordWrap(True)

        hint.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
            "background:transparent;border:none;"
        )

        layout.addWidget(hint)

        for category in CATEGORY_ORDER:

            card = SectionCard(
                Resources.changelog(),
                CATEGORY_LABELS[category],
                "Lektionen dieses Bereichs.",
            )

            entries = CatalogList(
                capacity=40,
                placeholder="Keine Lektionen hinterlegt.",
            )

            entries.activeChanged.connect(
                self._on_catalog_toggled
            )

            card.addWidget(entries)

            layout.addWidget(card)

            self.catalog_lists[category] = entries

            self.catalog_cards[category] = card

        reset_row = QHBoxLayout()

        reset_row.addStretch()

        self.reset_selection_button = HeroButton(
            "Alle Lektionen wieder aufnehmen",
            primary=False,
        )

        self.reset_selection_button.clicked.connect(
            self._reset_selection
        )

        reset_row.addWidget(self.reset_selection_button)

        layout.addLayout(reset_row)

        layout.addStretch()

    # --------------------------------------------------
    # Von aussen
    # --------------------------------------------------

    def show_lesson(self, lesson_id: str):
        """
        Die Lektionskarte zu `lesson_id` in den Blick holen.

        Kein Seitenwechsel und kein Dialog: die Karte steht auf
        derselben Spalte, ein Stück weiter unten. `ensureWidgetVisible`
        auf dem Scrollbereich des Raid Centers erledigt das - gefunden
        wird er über den Elternbaum, damit diese Ansicht ihren Rahmen
        nicht kennen muss.
        """

        for card in self._lesson_cards:

            if card.lesson.lesson_id != lesson_id:
                continue

            area = _scroll_area_of(self)

            if area is not None:
                area.ensureWidgetVisible(card, 0, 24)

            return

    def on_layout_changed(self, state):
        """
        Die Spaltenzahl des Bewertungsrasters (§6.3): sechs bei voller
        Breite, drei sobald die rechte Nebenspalte zur Schublade wird
        (< 1280 px), zwei sobald die Ansicht einspaltig wird (< 980 px).
        Beide Schwellen bestehen bereits als Haltepunkt-Flags - eine
        dritte, eigene Schwelle nur für dieses Raster wäre eine zweite
        Wahrheit über dieselbe Fensterbreite.
        """

        if state.single_column:
            self.rating_grid.set_columns(2)

        elif state.drawer:
            self.rating_grid.set_columns(3)

        else:
            self.rating_grid.set_columns(6)

        #
        # Die Kennzahlen folgen derselben Fensterbreite, nur eine
        # Stufe gröber: sie tragen Zahlen und keine Sternereihen und
        # vertragen deshalb mehr nebeneinander.
        #

        self._layout_tiles(2 if state.single_column else 3)

    def _layout_tiles(self, columns: int):
        """
        Die Kennzahlkacheln neu anordnen.

        Die Kacheln werden dabei **umgehängt und nicht neu gebaut** -
        WoW gibt Frames nie frei, Qt zwar schon, aber ein Neubau je
        Fenstergrösse verlöre die Werte darin und liesse die Seite bei
        jedem Ziehen am Rand flackern.
        """

        if getattr(self, "_tile_columns", None) == columns:
            return

        self._tile_columns = columns

        for tile in self._tiles:
            self.tile_grid.removeWidget(tile)

        for position, tile in enumerate(self._tiles):

            self.tile_grid.addWidget(
                tile,
                position // columns,
                position % columns,
            )

        for column in range(max(columns, self.tile_grid.columnCount())):

            self.tile_grid.setColumnStretch(column, 1 if column < columns else 0)

    # --------------------------------------------------
    # Snapshot anwenden
    # --------------------------------------------------

    def apply(self, snapshot: RaidSnapshot):
        """
        Bewertung und Plan aus **genau diesem** Stand.

        Der Snapshot kommt vom Raid Center und wird nicht daneben noch
        einmal geholt: `service.current()` ist während einer Wiedergabe
        nachweislich ein anderer Stand als der gerade gezeigte, und dann
        beschrieben die Sterne eine andere Sekunde als die Kennzahlen
        darunter.
        """

        self._profile = self.academy.build_profile(snapshot)

        #
        # Der Snapshot geht mit, damit der Plan seine Lektionen gegen
        # genau den gerade gezeigten Kampf prüfen kann. Im
        # Wiedergabe-Modus ist das der Stand der laufenden Sekunde -
        # daraus entsteht die Verzahnung mit der Analyse, ohne dass
        # diese Ansicht etwas von einer Wiedergabe wissen müsste.
        #

        #
        # Mit dem gewählten Charakter, nicht mit `profile.name`: das
        # ist wörtlich "-", sobald der Spieler im Pull fehlt, und der
        # Fortschritt würde unter diesem Unnamen gesucht - der Plan
        # zeigte dann alle Lektionen wieder als offen.
        #
        self._plan = self.academy.build_plan(
            self._profile,
            snapshot,
            character=self.academy.player_name(),
        )

        self._apply_profile(snapshot)

        self._apply_history()

        self._apply_plan()

        self._apply_catalog()

    def on_archive_changed(self):
        """
        Nur der Leerzustand wird nachgezogen - alles andere hängt am
        Snapshot und wäre hier eine zweite Quelle für dieselbe
        Anzeige.

        Gerufen wird das vom Raid Center: während ein Pull geholt wird,
        ändert sich kein Snapshot, und ohne diesen Weg stünde die
        Leerzustandskarte die ganze Wartezeit über mit "kein
        ausgewerteter Kampf" neben der Wartekarte.
        """

        self._apply_empty_state(self.service.current())

    def invalidate(self):
        """
        Plan und Kurve beim nächsten Zeichnen neu aufbauen.

        Nötig, wenn sich von aussen etwas geändert hat, was die
        Signaturen nicht sehen - ein Charakterwechsel im Kopfblock
        wechselt den ganzen Lernstand, ohne dass eine einzelne Lektion
        anders aussieht.
        """

        self._plan_signature = None

        self._history_signature = None

    def _apply_rating_notice(self, snapshot: RaidSnapshot):
        """
        Benennt den Grund, wenn Bereiche unbewertet bleiben.

        Null Sterne heißen in der Academy "keine Daten", nicht
        "schlecht" - das steht auch je Zeile dran. Woran es liegt,
        beantwortet die Zeile aber nicht, und genau das ist die Frage,
        die sich beim Blick auf fünf unbewertete Bereiche stellt.

        Der Text kommt aus derselben Quelle wie der Hinweis in
        WeintTV, damit beide Seiten denselben Sachverhalt nicht
        unterschiedlich erklären.
        """

        reason = rating_gap_text(snapshot)

        self.rating_notice.setText(reason)

        self.rating_notice.setVisible(bool(reason))

    def _apply_metric_tiles(self, snapshot: RaidSnapshot):
        """
        Die Zahlen hinter den Bewertungen.

        Sie stehen bewusst neben den Sternen: eine Bewertung ohne den
        Wert, auf dem sie beruht, ist ein Urteil ohne Beleg.
        """

        name = self._profile.name

        taken = snapshot.damage_taken_of(name)

        self.tile_avoidable.setValue(
            f"{taken.avoidable_share * 100:.0f} %"
            if taken is not None and taken.total > 0
            else "-"
        )

        self.tile_avoidable.setCaption(
            f"{taken.avoidable_hits} Treffer"
            if taken is not None and taken.avoidable_hits
            else "erhaltener Schaden"
        )

        activity = snapshot.activity_of(name)

        self.tile_activity.setValue(
            f"{activity.active_percent:.0f} %"
            if activity is not None
            else "-"
        )

        self.tile_activity.setCaption(
            f"{activity.apm:.0f} Aktionen/min"
            if activity is not None
            else "keine Angaben"
        )

        cooldowns = [
            usage
            for usage in snapshot.cooldowns_of(name)
            if usage.possible > 0
        ]

        used = sum(usage.uses for usage in cooldowns)

        possible = sum(usage.possible for usage in cooldowns)

        self.tile_cooldowns.setValue(
            f"{used}/{possible}"
            if possible
            else "-"
        )

        self.tile_cooldowns.setCaption(
            f"{sum(usage.in_burst for usage in cooldowns)} im Heldentum"
            if cooldowns and snapshot.heroism_windows
            else "genutzt von möglich"
        )

        self._apply_support_tiles(snapshot, name)

    def _apply_support_tiles(self, snapshot: RaidSnapshot, name: str):
        """
        Die drei Kennzahlen, die bis 2.8.0 nirgends standen, obwohl sie
        im Snapshot lagen und die Bewertung daneben aus ihnen entsteht.

        **Ein Strich heisst hier immer "nicht geliefert" und nie
        "null".** Das ist der Unterschied, an dem sonst eine Datenlücke
        wie ein Befund aussieht: "0 Unterbrechungen" ist ein Vorwurf,
        "-" ist eine Auskunft über die Quelle. Deshalb wird für jede
        Kachel zuerst gefragt, ob die Quelle diese Art Ereignis
        überhaupt geliefert hat, und erst dann gezählt.
        """

        #
        # Unterbrechungen und Entzauberungen teilen sich eine Kachel:
        # beides ist Hilfsarbeit für den Raid, beides zählt in
        # dieselbe Bewertung, und zwei Kacheln nebeneinander mit
        # jeweils einstelligen Zahlen wären zwei halbe Auskünfte.
        #

        interrupts = [
            event
            for event in snapshot.interrupts
            if event.actor_name == name
        ]

        dispels = [
            event
            for event in snapshot.dispels
            if event.actor_name == name
        ]

        knows_support = bool(snapshot.interrupts or snapshot.dispels)

        self.tile_interrupts.setValue(
            str(len(interrupts)) if knows_support else "-"
        )

        #
        # Die Entzauberungen stehen als zweite Zahl in der Unterzeile
        # und nicht in einer eigenen Kachel: es ist dieselbe Sorte
        # Arbeit für den Raid, sie zählt in dieselbe Bewertung, und
        # zwei Kacheln mit je einer einstelligen Zahl wären zwei halbe
        # Auskünfte.
        #

        self.tile_interrupts.setCaption(
            f"{len(dispels)} entzaubert"
            if knows_support
            else "keine Angaben"
        )

        #
        # Tode: der Snapshot führt sie immer, auch als leere Liste -
        # "0" ist hier also eine echte Aussage und keine Lücke.
        # Ausserhalb eines Kampfes gilt sie allerdings nicht, dort
        # steht noch gar nichts fest.
        #

        deaths = [
            death
            for death in snapshot.deaths
            if death.actor_name == name
        ]

        rezzed = [
            event
            for event in snapshot.resurrections
            if event.target == name
        ]

        self.tile_deaths.setValue(
            str(len(deaths)) if snapshot.has_data else "-"
        )

        if not snapshot.has_data:
            caption = "keine Angaben"

        elif not deaths:
            caption = "überlebt"

        elif rezzed:
            caption = f"{len(rezzed)}× wiederbelebt"

        else:
            caption = deaths[-1].cause or "gestorben"

        self.tile_deaths.setCaption(caption)

        #
        # Vorbereitung: Fläschchen und Bufffood. Die fehlende Liste ist
        # der Punkt - sie beantwortet als einzige Zahl dieser Seite
        # eine Frage, die man VOR dem Pull hätte beantworten können.
        #

        supplies = snapshot.consumables

        if not supplies:

            self.tile_supplies.setValue("-")

            self.tile_supplies.setCaption("keine Angaben")

            return

        missing = [
            entry.label
            for entry in supplies
            if name in entry.missing
        ]

        self.tile_supplies.setValue(
            "vollständig" if not missing else f"{len(missing)} fehlt"
            if len(missing) == 1
            else f"{len(missing)} fehlen"
        )

        self.tile_supplies.setCaption(
            ", ".join(missing)
            if missing
            else ", ".join(entry.label for entry in supplies)
        )

    def _apply_profile(self, snapshot: RaidSnapshot):
        """
        Der Snapshot wird **gereicht und nicht neu geholt**.

        `_apply_snapshot()` baut Profil und Plan aus genau diesem
        Stand; `self.service.current()` daneben zu fragen ist eine
        zweite Quelle für dieselbe Auskunft, und in einer Wiedergabe
        sind die beiden nachweislich verschieden - die Sterne
        beschrieben dann die abgespielte Sekunde und die Kennzahlen
        darunter den zuletzt veröffentlichten Stand. Dieselbe Regel,
        aus der es überhaupt nur einen Snapshot gibt.
        """

        profile = self._profile

        self._apply_empty_state(snapshot)

        self.profile_name.setText(profile.name)

        restyle(
            self.profile_name,
            f"font-size:22px;font-weight:700;"
            f"color:{class_color(profile.class_name)};"
            "letter-spacing:-0.01em;background:transparent;border:none;",
        )

        if profile.actor is not None:

            self.profile_title.setText(
                f"{profile.spec} {class_label(profile.class_name)} · "
                f"{role_label(profile.actor.role)}"
            )

        else:

            self.profile_title.setText(profile.title)

        #
        # Nur die Durchschnittsnote. Boss, Schwierigkeit, Pull und
        # Ausgang standen hier bis 3.6.0 mit (`encounter_meta`) - seit
        # 4.0 trägt sie der Kontextblock des Raid Centers, der beim
        # Perspektivwechsel stehen bleibt. Ein zweites Mal hier wäre
        # genau die Doppelung, die dieser Umbau beseitigt; die Note
        # dagegen steht nirgends sonst.
        #

        self.profile_meta.setText(average_text(profile))

        self.profile_note.setText(profile.note)

        self.profile_note.setVisible(bool(profile.note))

        #
        # Bewertungen - das Raster übernimmt Sterne, Detailtext und
        # die Hervorhebung des schwächsten Bereichs in einem Aufruf.
        #

        self.rating_grid.apply(profile)

        self._apply_rating_notice(snapshot)

        self._apply_metric_tiles(snapshot)

        #
        # Die größten Baustellen - die Karte oben.
        #
        # Sie ersetzt die frühere Karte "Nächste Lektion". Der
        # Unterschied ist nicht die Form: die alte Karte nannte **eine**
        # Lektion und liess offen, aus welchem Befund sie folgt; diese
        # nennt die zwei bis drei schwächsten Bereiche mit ihrer
        # Begründung, der Lektion dazu und dem Moment im Kampf. Das ist
        # die Antwort auf "was soll ich verbessern" statt auf "was ist
        # die nächste Lektion".
        #
        # Der Platzhaltersatz kommt aus `analysis_gap.py`, damit diese
        # Karte und die Leerzustandskarte darüber dieselbe Lage nicht
        # verschieden erklären. `focus_placeholder()` zieht dabei zwei
        # Linien: ohne Kampfdaten ist NICHTS erledigt (es ist nur
        # nichts berechnet), und "bewertet, aber nichts Schwaches" ist
        # ein Lob und kein Mangel.
        #

        self.focus_card.apply(
            profile,
            self._plan,
            placeholder=focus_placeholder(
                snapshot.has_data,
                bool(profile.rated),
            ),
        )

        #
        # Fortschritt
        #

        done, total = self.academy.progress_for(profile)

        self.progress_bar.setValue(
            done / total
            if total
            else 0.0
        )

        #
        # "0 von 0 Lektionen erledigt" ist eine Zahl, die nichts sagt,
        # und von einem Fehler nicht zu unterscheiden. Ohne Lektionen
        # steht deshalb da, dass es noch keine gibt.
        #

        self.progress_label.setText(
            f"{done} von {total} Lektionen erledigt"
            if total
            else "Noch keine Lektionen für diesen Charakter"
        )

        self.reset_button.setEnabled(done > 0)

    def _apply_empty_state(self, snapshot: RaidSnapshot):
        """
        Die Karte über der Seite: was fehlt, und was dagegen hilft.

        Formuliert wird beides in `gui/widgets/tv/analysis_gap.py` -
        derselben Stelle, an der auch WeintTV seine Lücken erklärt,
        damit die beiden Seiten denselben Sachverhalt nicht
        verschieden benennen.

        Der Knopf steht nur da, wo er etwas ausrichtet. Läuft ein Raid
        und bloss gerade kein Pull, ist Warten das Richtige, und ein
        Knopf daneben legte eine Handlung nahe, die niemand braucht.
        """

        text = academy_empty_text(
            snapshot,
            loading=self.service.archive_state().fight_loading,
        )

        self.empty_card.setVisible(bool(text))

        if not text:
            return

        self.empty_text.setText(text)

        self.empty_button.setVisible(
            academy_empty_action(snapshot) == ACTION_ARCHIVE
        )

    def _apply_history(self):
        """
        Die Lernkurve zeichnen - die aufgezeichneten Pulls dieses
        Charakters, nicht der gerade gezeigte Kampf.

        **Erst vergleichen, dann zeichnen.** Diese Methode hängt an
        `_apply_snapshot()` und läuft damit im Sekundentakt, in einer
        Wiedergabe viermal je Sekunde - die Kurve ändert sich dagegen
        höchstens einmal je Pull. Dieselbe Regel wie beim
        Archivbrowser und der WeakAura-Liste.

        Gefiltert wird nach **Datenquelle und Spezialisierung**: die
        Simulation ist keine Lernkurve, und eine Rotationsbewertung
        als Frost sagt nichts über die Rotation als Feuer. Beide
        Filter greifen nur, wenn die Frage beantwortbar ist (siehe
        `progression.select()`).
        """

        source = self.manager.config.data.get("raid_data_source", "")

        #
        # Dieselbe Auswahl, aus der auch der Trainingsplan seine
        # Reihenfolge nimmt - liefen die beiden auseinander, zeigte
        # die Karte eine andere Entwicklung, als der Plan daneben
        # behauptet.
        #

        records = self.academy.curve_for(self._profile)

        signature = tuple(record.key for record in records)

        if signature == self._history_signature:
            return

        self._history_signature = signature

        self.history_card.apply(records, _source_note(source))

    def _practice_text(self) -> str:
        """
        Der Satz zur Übungsserie am Trainingsdummy - leer, wenn für
        diese Spezialisierung noch nichts geübt wurde.

        Formuliert wird er in core/academy_dummy_sync.py, dort wird
        auch entschieden, was eine Serie fortsetzt. Ein eigener Satz
        hier liefe irgendwann anders aus als der, den das Addon
        zugestellt bekommt.
        """

        state = practice_for_lessons(
            practice_payload(self.academy, self.academy.player_name()),
            [item.lesson_id for item in self._plan.items],
        )

        return (state or {}).get("text", "")

    def _apply_plan(self):

        #
        # Während einer laufenden Wiedergabe wird der Plan nicht neu
        # gebaut. Bei achtfacher Geschwindigkeit kämen viermal pro
        # Sekunde neue Snapshots - die Karten würden flackern und
        # jeder Klick ginge im Neuaufbau verloren. Die Bewertungen
        # oben laufen weiter mit; sobald pausiert oder gestoppt wird,
        # zieht der Plan nach.
        #

        if self.service.replay_state().playing:
            return

        signature = (
            tuple(
                (
                    item.lesson_id,
                    item.completed,
                    item.status,
                )
                for item in self._plan.items
            ),

            #
            # Die Begründung gehört in die Signatur: sie ändert sich,
            # sobald ein Pull dazukommt, während die Lektionen
            # dieselben bleiben können - ohne sie bliebe der Satz auf
            # dem Stand von vorgestern stehen.
            #

            self._plan.note,

            #
            # Die Übungsserie gehört mit hinein: sie ändert sich durch
            # eine gemeldete Sitzung, ohne dass sich am Plan etwas
            # bewegt - ohne sie bliebe "Tag 2 von 3" stehen, nachdem
            # längst Tag 3 gemeldet wurde.
            #

            self._practice_text(),
        )

        if signature == self._plan_signature:
            return

        self._plan_signature = signature

        self.plan_note.setText(self._plan.note)

        self.plan_note.setVisible(bool(self._plan.note))

        praxis = self._practice_text()

        self.practice_note.setText(praxis)

        self.practice_note.setVisible(bool(praxis))

        #
        # Alte Karten entfernen. deleteLater() statt sofortigem
        # Löschen, weil der Aufruf aus einem Signal der gerade
        # angeklickten Karte kommen kann.
        #

        for card in self._lesson_cards:

            self.plan_layout.removeWidget(card)

            card.setParent(None)

            card.deleteLater()

        self._lesson_cards = []

        items = self._plan.items

        self.plan_placeholder.setVisible(not items)

        for index, item in enumerate(items):

            card = LessonCard(
                item.lesson,
                completed=item.completed,
                highlight=(index == 0 and not item.done),
                result=item.result,
            )

            card.completedChanged.connect(
                self._on_lesson_toggled
            )

            card.momentRequested.connect(
                self.momentRequested
            )

            #
            # Vor dem abschließenden Stretch einfügen, damit die
            # Karten oben bleiben.
            #

            self.plan_layout.insertWidget(
                self.plan_layout.count() - 1,
                card,
            )

            self._lesson_cards.append(card)

    def _on_lesson_toggled(self, lesson_id: str, completed: bool):

        self.academy.set_completed(
            self._profile.name,
            lesson_id,
            completed,
        )

        self.apply(self.service.current())

    def _reset_progress(self):

        self.academy.reset(self._profile.name)

        self._plan_signature = None

        self.apply(self.service.current())

    def _reset_selection(self):

        self.academy.reset_selection(self._profile.name)

        self._plan_signature = None

        self.apply(self.service.current())

    def _apply_catalog(self):

        excluded = self.academy.excluded_for(self._profile.name)

        for category, entries in self.catalog_lists.items():

            lessons = lessons_in_category(
                self._profile.actor,
                category,
                self._profile.encounter_name,
            )

            rows = []

            for lesson in lessons:

                item = self._plan.item(lesson.lesson_id)

                completed = self._plan.is_completed(lesson.lesson_id)

                rows.append(
                    CatalogRowData(
                        lesson_id=lesson.lesson_id,
                        title=lesson.title,
                        detail=(
                            lesson.summary
                            + (
                                " · im Log erfüllt"
                                if item is not None
                                and item.status == STATUS_PASSED
                                else ""
                            )
                            + (" · abgehakt" if completed else "")
                        ),
                        active=lesson.lesson_id not in excluded,
                        completed=completed,
                        status=(
                            item.status
                            if item is not None
                            else STATUS_UNKNOWN
                        ),
                    )
                )

            entries.setRows(rows)

            #
            # Die Kopfzeile nennt, wie viele Lektionen eines Bereichs
            # aktiv sind - sonst wäre eine Abwahl nach dem Wechsel des
            # Bereichs nicht mehr auffindbar.
            #

            card = self.catalog_cards.get(category)

            if card is not None:

                active = sum(1 for row in rows if row.active)

                card.setSubtitle(
                    f"{active} von {len(rows)} Lektionen aktiv."
                )

    def _on_catalog_toggled(self, lesson_id: str, active: bool):

        self.academy.set_enabled(
            self._profile.name,
            lesson_id,
            active,
        )

        #
        # Die Auswahl verändert den Trainingsplan - die Signatur
        # zurücksetzen, damit er wirklich neu gebaut wird.
        #

        self._plan_signature = None

        self.apply(self.service.current())


# --------------------------------------------------
# Hilfen
# --------------------------------------------------


def _scroll_area_of(widget):
    """
    Der Scrollbereich, in dem dieses Widget liegt - oder `None`.

    Über den Elternbaum und nicht über eine Rückreferenz: die Ansicht
    soll ihren Rahmen nicht kennen müssen, und ein gespeicherter Zeiger
    auf den Rahmen wäre ein Kreis, den der Sammler nicht auflöst.
    """

    from PySide6.QtWidgets import QScrollArea

    parent = widget.parentWidget()

    while parent is not None:

        if isinstance(parent, QScrollArea):
            return parent

        parent = parent.parentWidget()

    return None


def _source_note(source: str) -> str:
    """
    Der Zusatz unter der Kurve, wenn die Datenquelle ihn braucht.

    Bei der Simulation ist er nicht Zierde: die Kurve sieht dort aus
    wie eine echte, und ohne diesen Satz wäre nicht zu erkennen, dass
    sie aus gerechneten Pulls besteht. Bei einer echten Quelle steht
    dort nichts - eine Selbstverständlichkeit auszusprechen macht die
    Zeile nur länger.
    """

    if source == SOURCE_MOCK:
        return "Aus der Simulation - echte Pulls zählen getrennt."

    return ""
