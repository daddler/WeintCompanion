"""
WeintAcademy - das Lernzentrum.

Die Academy wertet dieselben Snapshots aus wie WeintTV. Sie holt
sich Profil und Trainingsplan fertig vom AcademyService, der
seinerseits die Auswertung im Analyzer aufruft. In dieser Datei
steht deshalb ausschließlich Darstellung.

Drei Bereiche, umgeschaltet über denselben SegmentedControl wie in
WeintTV, damit sich beide neuen Module gleich bedienen:

    Übersicht      Bewertung, nächste Lektion, Fortschritt
    Trainingsplan  Die Lektionen der Reihe nach, abhakbar
    Katalog        Alle verfügbaren Lektionen nach Bereich

Ein Detail zur Aktualisierung: die Sternebewertungen dürfen im
Sekundentakt mitlaufen, die Lektionskarten nicht - sie werden nur
neu gebaut, wenn sich der Plan tatsächlich ändert. Sonst entstünde
bei jedem Snapshot eine komplett neue Kartenliste, was sichtbar
flackern und jede Interaktion unterbrechen würde.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analyzer.academy.lessons import lessons_in_category
from analyzer.academy.models import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    MAX_STARS,
    PlayerProfile,
    TrainingPlan,
)
from analyzer.models import RaidSnapshot

from core.resources import Resources

from gui.theme.colors import Colors
from gui.theme.wow_colors import class_color, class_label, role_label

from gui.widgets.academy.lesson_card import LessonCard
from gui.widgets.academy.star_rating import StarRating
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.section_card import SectionCard
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.archive_picker import ArchivePicker
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.meter_bar import MeterBar


TAB_OVERVIEW = "overview"
TAB_PLAN = "plan"
TAB_CATALOG = "catalog"


class AcademyPage(QWidget):

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        self.service = manager.raid_data

        self.academy = manager.academy

        self._attached = False

        #
        # Merker, damit nur bei echten Änderungen neu gebaut wird.
        #

        self._plan_signature = None

        self._roster_signature = None

        self._profile = PlayerProfile()

        self._plan = TrainingPlan()

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

        eyebrow = QLabel("WEINTACADEMY · TRAINING")

        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Lernzentrum")

        title.setObjectName("title")

        title_col.addWidget(title)

        header.addLayout(title_col)

        header.addStretch()

        character_label = QLabel("Charakter")

        character_label.setStyleSheet(
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
        )

        header.addWidget(character_label)

        self.character_box = QComboBox()

        self.character_box.setMinimumWidth(180)

        self.character_box.currentTextChanged.connect(
            self._on_character_changed
        )

        header.addWidget(self.character_box)

        root.addLayout(header)

        #
        # --------------------------------------------------
        # Live/Archiv-Umschalter
        # --------------------------------------------------
        #
        # Geteilt mit WeintTV über denselben RaidDataService - ein
        # Wechsel hier wirkt auch dort, siehe
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
            ("Übersicht", TAB_OVERVIEW),
            ("Trainingsplan", TAB_PLAN),
            ("Katalog", TAB_CATALOG),
        ])

        self.tabs.valueChanged.connect(
            self._show_tab
        )

        root.addWidget(self.tabs)

        self.stack = QStackedWidget()

        root.addWidget(self.stack, 1)

        self._tab_index = {}

        for key, builder in (
            (TAB_OVERVIEW, self._build_overview),
            (TAB_PLAN, self._build_plan),
            (TAB_CATALOG, self._build_catalog),
        ):

            self._tab_index[key] = self.stack.count()

            self.stack.addWidget(builder())

        self.tabs.setValue(TAB_OVERVIEW)

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

        title = QLabel("WeintAcademy ist deaktiviert")

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
    # Aufbau: Übersicht
    # --------------------------------------------------

    def _build_overview(self) -> QWidget:

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(16)

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

        rating_card = SectionCard(
            Resources.dashboard(),
            "Bewertung",
            "Aus dem zuletzt ausgewerteten Kampf abgeleitet.",
        )

        self.rating_widgets = {}

        for category in CATEGORY_ORDER:

            row = QHBoxLayout()

            row.setSpacing(14)

            label = QLabel(CATEGORY_LABELS[category])

            label.setFixedWidth(110)

            label.setStyleSheet(
                f"font-size:13px;font-weight:600;color:{Colors.TEXT};"
                "background:transparent;border:none;"
            )

            row.addWidget(label)

            stars = StarRating(0, MAX_STARS)

            row.addWidget(stars)

            detail = QLabel("")

            detail.setWordWrap(True)

            detail.setStyleSheet(
                f"font-size:12px;color:{Colors.TEXT_MUTED};"
                "background:transparent;border:none;"
            )

            row.addWidget(detail, 1)

            rating_card.addLayout(row)

            self.rating_widgets[category] = (stars, detail)

        layout.addWidget(rating_card)

        #
        # Nächste Lektion
        #

        self.next_card = Card(accent=True)

        next_eyebrow = eyebrow_label(
            "NÄCHSTE LEKTION",
            Colors.PRIMARY_HOVER,
        )

        self.next_card.addWidget(next_eyebrow)

        self.next_title = QLabel("-")

        self.next_title.setWordWrap(True)

        self.next_title.setStyleSheet(
            f"font-size:17px;font-weight:700;color:{Colors.WHITE};"
            "background:transparent;border:none;"
        )

        self.next_card.addWidget(self.next_title)

        self.next_summary = QLabel("")

        self.next_summary.setWordWrap(True)

        self.next_summary.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};"
            "background:transparent;border:none;"
        )

        self.next_card.addWidget(self.next_summary)

        open_row = QHBoxLayout()

        open_row.addStretch()

        self.open_plan_button = HeroButton("Zum Trainingsplan")

        self.open_plan_button.clicked.connect(
            lambda: self.tabs.setValue(TAB_PLAN)
        )

        open_row.addWidget(self.open_plan_button)

        self.next_card.addLayout(open_row)

        layout.addWidget(self.next_card)

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

        layout.addStretch()

        return page

    # --------------------------------------------------
    # Aufbau: Trainingsplan
    # --------------------------------------------------

    def _build_plan(self) -> QWidget:

        page = QWidget()

        self.plan_layout = QVBoxLayout(page)

        self.plan_layout.setContentsMargins(0, 0, 0, 0)

        self.plan_layout.setSpacing(14)

        self.plan_placeholder = QLabel(
            "Sobald ein Kampf ausgewertet wurde, entsteht hier "
            "automatisch ein Trainingsplan."
        )

        self.plan_placeholder.setWordWrap(True)

        self.plan_placeholder.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_MUTED};"
        )

        self.plan_layout.addWidget(self.plan_placeholder)

        self.plan_layout.addStretch()

        self._lesson_cards: list[LessonCard] = []

        return page

    # --------------------------------------------------
    # Aufbau: Katalog
    # --------------------------------------------------

    def _build_catalog(self) -> QWidget:

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(16)

        self.catalog_lists = {}

        for category in CATEGORY_ORDER:

            card = SectionCard(
                Resources.changelog(),
                CATEGORY_LABELS[category],
                "Lektionen dieses Bereichs.",
            )

            entries = EntryList(
                capacity=10,
                placeholder="Keine Lektionen hinterlegt.",
            )

            card.addWidget(entries)

            layout.addWidget(card)

            self.catalog_lists[category] = entries

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
    # Lebenszyklus
    # --------------------------------------------------

    def _module_enabled(self) -> bool:

        return bool(
            self.manager.config.data.get("academy_enabled", True)
        )

    def on_enter(self):

        enabled = self._module_enabled()

        self.disabled_notice.setVisible(not enabled)

        self.tabs.setVisible(enabled)

        self.stack.setVisible(enabled)

        self.character_box.setVisible(enabled)

        if not enabled:

            self.on_leave()

            return

        if not self._attached:

            self.service.attach()

            self._attached = True

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

        self._sync_roster(snapshot)

        self._profile = self.academy.build_profile(snapshot)

        self._plan = self.academy.build_plan(self._profile)

        self._apply_overview()

        self._apply_plan()

        self._apply_catalog()

    # --------------------------------------------------

    def _sync_roster(self, snapshot: RaidSnapshot):
        """
        Die Auswahlliste nur dann neu füllen, wenn sich der Raid
        tatsächlich geändert hat - sonst würde sie im Sekundentakt
        zurückspringen, während der Nutzer sie gerade bedient.
        """

        names = self.academy.roster(snapshot)

        if names == self._roster_signature:
            return

        self._roster_signature = names

        selected = self.academy.resolve_player_name(snapshot)

        self.character_box.blockSignals(True)

        self.character_box.clear()

        self.character_box.addItems(names)

        if selected in names:

            self.character_box.setCurrentText(selected)

        self.character_box.blockSignals(False)

    def _on_character_changed(self, name: str):

        if not name:
            return

        self.academy.set_player_name(name)

        self._apply_snapshot(self.service.current())

    # --------------------------------------------------

    def _apply_overview(self):

        profile = self._profile

        self.profile_name.setText(profile.name)

        self.profile_name.setStyleSheet(
            f"font-size:22px;font-weight:700;"
            f"color:{class_color(profile.class_name)};"
            "letter-spacing:-0.01em;background:transparent;border:none;"
        )

        if profile.actor is not None:

            self.profile_title.setText(
                f"{profile.spec} {class_label(profile.class_name)} · "
                f"{role_label(profile.actor.role)}"
            )

        else:

            self.profile_title.setText(profile.title)

        if profile.sample_size:

            self.profile_meta.setText(
                f"{profile.encounter_name} · Pull {profile.sample_size} · "
                f"Ø {profile.average_stars:.1f}/{MAX_STARS}"
            )

        else:

            self.profile_meta.setText("")

        self.profile_note.setText(profile.note)

        self.profile_note.setVisible(bool(profile.note))

        #
        # Bewertungen
        #

        for category, (stars, detail) in self.rating_widgets.items():

            rating = profile.rating(category)

            if rating is None:

                stars.setStars(0)

                detail.setText("Noch keine Auswertung.")

                continue

            stars.setStars(rating.stars)

            detail.setText(rating.detail)

        #
        # Nächste Lektion
        #

        lesson = self._plan.next_lesson

        if lesson is None:

            self.next_title.setText("Alle Lektionen erledigt")

            self.next_summary.setText(
                "Der aktuelle Lernpfad ist abgeschlossen - neue "
                "Lektionen entstehen mit der nächsten Auswertung."
            )

            self.open_plan_button.setEnabled(False)

        else:

            self.next_title.setText(lesson.title)

            self.next_summary.setText(
                f"{lesson.category_label} · {lesson.summary}"
            )

            self.open_plan_button.setEnabled(True)

        #
        # Fortschritt
        #

        done, total = self.academy.progress_for(profile)

        self.progress_bar.setValue(
            done / total
            if total
            else 0.0
        )

        self.progress_label.setText(
            f"{done} von {total} Lektionen erledigt"
        )

        self.reset_button.setEnabled(done > 0)

    # --------------------------------------------------

    def _apply_plan(self):

        signature = tuple(
            (lesson.lesson_id, self._plan.is_completed(lesson.lesson_id))
            for lesson in self._plan.lessons
        )

        if signature == self._plan_signature:
            return

        self._plan_signature = signature

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

        lessons = self._plan.lessons

        self.plan_placeholder.setVisible(not lessons)

        for index, lesson in enumerate(lessons):

            completed = self._plan.is_completed(lesson.lesson_id)

            card = LessonCard(
                lesson,
                completed=completed,
                highlight=(index == 0 and not completed),
            )

            card.completedChanged.connect(
                self._on_lesson_toggled
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

        self._apply_snapshot(self.service.current())

    def _reset_progress(self):

        self.academy.reset(self._profile.name)

        self._apply_snapshot(self.service.current())

    # --------------------------------------------------

    def _apply_catalog(self):

        for category, entries in self.catalog_lists.items():

            entries.setEntries(
                EntryData(
                    title=lesson.title,
                    detail=lesson.summary,
                    level=(
                        "success"
                        if self._plan.is_completed(lesson.lesson_id)
                        else "info"
                    ),
                    trailing=(
                        "erledigt"
                        if self._plan.is_completed(lesson.lesson_id)
                        else ""
                    ),
                )
                for lesson in lessons_in_category(
                    self._profile.actor,
                    category,
                )
            )
