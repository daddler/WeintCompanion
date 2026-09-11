"""
Der Archivbrowser: einen vergangenen Pull finden, nicht ihn erraten.

**Warum es ihn gibt.** Bis 2.8.0 war das Archiv zwei Ausklapplisten in
einer Zeile. Die erste trug zwanzig gleich aussehende Berichte
("Belagerung von Orgrimmar", zwanzigmal), die zweite an einem
Raidabend leicht sechzig Pulls in der Form "Pull 14 · Garrosh · 42 % ·
06:31" - in der Reihenfolge des Berichts und sonst ohne jede Ordnung.
Wer den einen Versuch wiederfinden wollte, über den in der Gilde
gesprochen wurde, hat gescrollt und geraten; wer den Kill von letzter
Woche sehen wollte, musste wissen, an welchem Tag er war. Gemeldet
wurde das als "es ist ziemlich kompliziert, archivierte Logs zu
finden", und das ist die richtige Beschreibung: die Daten waren alle
da, gefunden hat man damit trotzdem nichts.

Also ein eigenes Fenster mit zwei Spalten - links die Abende, rechts
die Pulls nach Boss gebündelt - plus ein Suchfeld und ein Schalter für
"nur Kills". Ein Dialog und keine Seite: einen Pull wählt man, wenn
man einen ansehen will, und ist danach wieder woanders; dieselbe
Überlegung wie bei der Änderungsansicht.

**Entschieden wird hier nichts.** Welche Zeilen dastehen, wie sie
gruppiert und beschriftet sind, beantwortet `core/archive_index.py` -
Qt-frei und geprüft. Geladen wird ausschliesslich über den
`RaidDataService`, mit genau denselben drei Aufrufen, die die alte
Zeile auch benutzt hat. Dieses Fenster ist damit eine zweite Ansicht
auf denselben Zustand und keine zweite Auswahl daneben: was hier
gewählt wird, sehen WeintTV und die Academy sofort, aus demselben
Grund, aus dem sie sich schon einen Snapshot teilen.

Zwei Dinge, die nicht Geschmack sind:

- **Die Listen werden erst verglichen, dann neu gebaut.** `refresh()`
  hängt an `archiveChanged`, und das kommt während eines Ladevorgangs
  mehrfach - ein unbedingtes Neubauen setzte die Bildlaufposition
  zurück, während jemand darin liest, und verlöre die Auswahl unter
  den Fingern. Dieselbe Falle wie beim `ArchivePicker` und der
  WeakAura-Liste.
- **Ein Klick auf einen Pull übernimmt ihn sofort**, das Fenster
  bleibt aber offen, bis der Abruf durch ist. Der einzelne Pull kostet
  den Bot Minuten, und ein Fenster, das sich beim Klick schliesst,
  lässt den Nutzer vor einer Seite stehen, die sich aus unerfindlichen
  Gründen nicht ändert. Der Fortschritt steht deshalb hier, wo geklickt
  wurde, und das Fenster geht von selbst zu, sobald der Pull da ist.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import archive_index as index

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.wrapped_label import enable_wrap


#
# Breite der linken Spalte. Sie trägt Wochentag und Datum in einer
# Zeile ("Donnerstag, 03.09.2026") - darunter bricht die um, und ein
# Datum über zwei Zeilen liest sich wie zwei Berichte.
#

DAY_COLUMN_W = 260


class _Row(QFrame):
    """
    Eine anklickbare Zeile - Grundform für Bericht und Pull.

    `mousePressEvent` statt eines `QPushButton`: die Zeile trägt zwei
    Textzeilen und mehrere Chips, und ein Knopf mit eigenem Layout
    darin bringt seine Rahmen- und Fokusdarstellung mit, die hier
    nirgends hingehört.

    **Der Klick geht als Signal hinaus und nie als angehefteter
    Rückruf.** Ein `row.mousePressEvent = lambda …` (oder ein im Feld
    gemerkter Lambda, der das Fenster über seinen Abschluss festhält)
    legt einen Kreis Fenster → Zeile → Lambda → Fenster an, den der
    Sammler zwar sieht, aber in beliebiger Reihenfolge auflöst: räumt
    er das Fenster vor seinen Kindern ab, ist das C++-Objekt weg,
    während Qt noch darauf zugreift. Das endet mit SIGSEGV und **ohne
    Python-Rückverfolgung** - dieselbe Klasse Fehler wie das an
    `hideEvent` weitergereichte `QCloseEvent` im Overlay-Fenster und
    dieselbe Abhilfe wie im `SegmentedControl`: ein Signal auf eine
    **gebundene Methode**, die PySide6 nur schwach hält.

    Die Kennung der Zeile liegt deshalb als Wert an ihr, nicht im
    Abschluss eines Rückrufs.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setCursor(Qt.PointingHandCursor)

        self._selected = False

        self.setLayout(QVBoxLayout())

        self.layout().setContentsMargins(12, 9, 12, 9)

        self.layout().setSpacing(2)

        #
        # Eine gewählte Zeile ist in der Akzentfarbe getönt, und die
        # kann sich ändern, während dieses Fenster offen steht. Als
        # **gebundene Methode**, nie als Lambda: `theme()` lebt so
        # lange wie der Prozess, und ein Lambda hielte die Zeile für
        # immer fest (siehe tests/test_theme_connections.py).
        #

        theme().accent_changed.connect(self._on_accent)

        self._apply_style()

    def _on_accent(self, _name: str):

        self._apply_style()

    def mousePressEvent(self, event):

        self.activate()

    def activate(self):
        """
        Denselben Weg gehen wie ein Klick - für die Tests und für
        einen späteren Tastaturzugang.
        """

        raise NotImplementedError

    def set_selected(self, selected: bool):

        if selected == self._selected:
            return

        self._selected = selected

        self._apply_style()

    def _apply_style(self):

        #
        # Die Akzentfarbe wird beim Zeichnen gelesen und nicht im
        # Konstruktor festgehalten: eine im Konstruktor gemerkte Farbe
        # überlebt einen Akzentwechsel, und das Widget behält
        # stillschweigend die alte.
        #

        if self._selected:

            background = tokens.tint(tokens.accent()["base"], tokens.TINT_SURFACE)

            border = tokens.tint(tokens.accent()["base"], tokens.TINT_BORDER)

        else:

            background = "transparent"

            border = "transparent"

        restyle(
            self,
            f"""
            QFrame{{
                background:{background};
                border:1px solid {border};
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )


class _ReportRow(_Row):
    """
    Ein Bericht in der linken Spalte.
    """

    clicked = Signal(str)

    def __init__(self, code: str, parent=None):

        super().__init__(parent)

        self.code = code

    def activate(self):

        self.clicked.emit(self.code)


class _FightRow(_Row):
    """
    Ein Pull in der rechten Spalte.
    """

    clicked = Signal(str, int)

    def __init__(self, code: str, fight_id: int, parent=None):

        super().__init__(parent)

        self.code = code

        self.fight_id = fight_id

    def activate(self):

        self.clicked.emit(self.code, self.fight_id)


class ArchiveBrowser(QWidget):
    """
    Zwei Spalten, ein Suchfeld, ein Schalter.

    **Seit 3.5.0 ein Widget und kein Fenster mehr.** Der Browser
    steckte bis dahin fest in einem Dialog, und die Seite *Archiv*
    bestand damit aus einem Wähler und dem Satz "die Zahlen stehen in
    WeintTV" - ein Bereich in der Navigationsspalte, der selbst nichts
    zeigte. Wer "Archiv" anklickte, wollte aber genau das sehen, was
    hier drinsteht: die Abende und ihre Pulls.

    Es bleibt **eine** Ansicht: die Seite bettet dieses Widget ein
    (`embedded=True`, ohne eigenen Kopf und ohne Schliessen-Knopf),
    und `ArchiveDialog` weiter unten legt dasselbe Widget in ein
    modales Fenster - für WeintTV und die Academy, wo man einen Pull
    wählen will, ohne den Bereich zu verlassen. Zwei Nachbauten
    derselben Liste würden ab der ersten Änderung verschieden
    gruppieren.
    """

    #
    # Der hier angeklickte Pull ist angekommen. Das Fenster schliesst
    # sich daraufhin; die Seite bleibt stehen, wo sie ist - dort gibt
    # es nichts zu schliessen.
    #

    fightLoaded = Signal()

    def __init__(self, service, parent=None, embedded: bool = False):

        super().__init__(parent)

        self.service = service

        self._embedded = bool(embedded)

        #
        # Womit die beiden Spalten zuletzt gefüllt wurden - siehe der
        # Kopfkommentar: ohne dieses Gedächtnis springt die
        # Bildlaufposition bei jedem `archiveChanged` zurück.
        #

        self._days_signature = None

        self._fights_signature = None

        self._needle = ""

        self._kills_only = False

        self._day_rows: dict[str, _Row] = {}

        self._fight_rows: dict[int, _Row] = {}

        #
        # Auf welchen Pull dieses Fenster wartet. Ohne diesen Merker
        # schlösse es sich in der Sekunde, in der es aufgeht: beim
        # Öffnen ist meist noch der Pull von vorhin gewählt und längst
        # geladen, und "fertig geladen" allein ist damit kein Anlass,
        # irgendetwas zuzumachen. Zugehen soll es nur für den Pull,
        # den man gerade hier angeklickt hat.
        #

        self._awaiting: int | None = None

        root = QVBoxLayout(self)

        #
        # Eingebettet trägt die Seite die Ränder (§6.2), im Fenster
        # dieses Widget selbst.
        #

        if self._embedded:
            root.setContentsMargins(0, 0, 0, 0)
        else:
            root.setContentsMargins(28, 24, 28, 20)

        root.setSpacing(14)

        #
        # Eingebettet trägt die Seite ihren eigenen Kopf (Rubrik und
        # Titel). Ein zweiter darunter wäre dieselbe Überschrift
        # zweimal.
        #

        if not self._embedded:
            self._build_head(root)

        self._build_filters(root)

        self._build_columns(root)

        self._build_footer(root)

        service.archiveChanged.connect(self._refresh)

        #
        # Der Einstieg. `enter_archive_mode()` lädt die Berichtsliste
        # nach, falls sie noch fehlt - genau das, was das Öffnen dieses
        # Fensters bedeutet.
        #

        service.enter_archive_mode()

        self._refresh()

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build_head(self, root: QVBoxLayout):

        head = QVBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(2)

        head.addWidget(eyebrow_label("ARCHIV · VERGANGENE KÄMPFE"))

        title = QLabel("Welchen Pull willst du ansehen?")

        title.setFont(font("title"))

        restyle(title, f"color:{tokens.WHITE};background:transparent;")

        head.addWidget(title)

        root.addLayout(head)

    def _build_filters(self, root: QVBoxLayout):

        row = QHBoxLayout()

        row.setSpacing(12)

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            "Suchen nach Boss, Tag, Uhrzeit oder Berichtscode …"
        )

        self.search.setClearButtonEnabled(True)

        self.search.textChanged.connect(self._on_search)

        restyle(
            self.search,
            f"""
            QLineEdit{{
                background:{tokens.SURFACE["raised"]};
                border:1px solid {tokens.BORDER["base"]};
                border-radius:{tokens.RADIUS["md"]}px;
                padding:8px 12px;
                color:{tokens.TEXT["primary"]};
            }}
            """,
        )

        row.addWidget(self.search, 1)

        self.kills_only = ToggleSwitch(False)

        self.kills_only.toggled.connect(self._on_kills_only)

        row.addWidget(self.kills_only)

        kills_label = QLabel("Nur Kills")

        restyle(
            kills_label,
            f"font-size:12px;color:{tokens.TEXT['secondary']};"
            "background:transparent;",
        )

        row.addWidget(kills_label)

        root.addLayout(row)

    def _build_columns(self, root: QVBoxLayout):

        columns = QHBoxLayout()

        columns.setSpacing(16)

        #
        # Links: die Abende.
        #

        left = QVBoxLayout()

        left.setSpacing(6)

        left.addWidget(eyebrow_label("RAIDABENDE"))

        self.days_body, days_scroll = self._scroll_column()

        left.addWidget(days_scroll, 1)

        left_wrap = QWidget()

        left_wrap.setLayout(left)

        left_wrap.setFixedWidth(DAY_COLUMN_W)

        columns.addWidget(left_wrap)

        #
        # Rechts: die Pulls des gewählten Abends.
        #

        right = QVBoxLayout()

        right.setSpacing(6)

        self.fights_eyebrow = eyebrow_label("PULLS")

        right.addWidget(self.fights_eyebrow)

        self.fights_body, fights_scroll = self._scroll_column()

        right.addWidget(fights_scroll, 1)

        right_wrap = QWidget()

        right_wrap.setLayout(right)

        columns.addWidget(right_wrap, 1)

        root.addLayout(columns, 1)

    def _scroll_column(self):

        body = QWidget()

        layout = QVBoxLayout(body)

        layout.setContentsMargins(0, 0, 8, 0)

        layout.setSpacing(4)

        layout.addStretch()

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        restyle(scroll, "QScrollArea{background:transparent;border:none;}")

        scroll.setWidget(body)

        return body, scroll

    def _build_footer(self, root: QVBoxLayout):

        footer = QHBoxLayout()

        footer.setSpacing(12)

        self.status = enable_wrap(QLabel(""))

        restyle(
            self.status,
            f"font-size:12px;color:{tokens.TEXT['muted']};"
            "background:transparent;",
        )

        footer.addWidget(self.status, 1)

        if not self._embedded:

            close_button = HeroButton("Schliessen", primary=False)

            close_button.clicked.connect(self._close_requested)

            footer.addWidget(close_button)

        root.addLayout(footer)

    def _close_requested(self):
        """
        Den Rahmen schliessen lassen, ohne ihn zu kennen.

        `self.reject()` gäbe es hier nicht mehr - dieses Widget ist
        kein Dialog. Der Umweg über das Elternteil hält den Browser
        frei von der Frage, worin er gerade steckt.
        """

        window = self.window()

        if window is not None:
            window.close()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _on_search(self, text: str):

        self._needle = text

        #
        # Der Suchtext ändert beide Spalten, also müssen beide Merker
        # fallen - sonst filtert die Liste sichtbar nichts.
        #

        self._days_signature = None

        self._fights_signature = None

        self._refresh()

    def _on_kills_only(self, checked: bool):

        self._kills_only = bool(checked)

        self._fights_signature = None

        self._refresh()

    def _on_report(self, code: str):

        self.service.select_archive_report(code)

    def _on_fight(self, code: str, fight_id: int):

        self._awaiting = fight_id

        self.service.select_archive_fight(code, fight_id)

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _refresh(self):

        state = self.service.archive_state()

        self._fill_days(state)

        self._fill_fights(state)

        self._update_status(state)

        #
        # Ist der hier angeklickte Pull angekommen, ist dieses Fenster
        # fertig. Nicht schon beim Klick: der Abruf kostet den Bot
        # Minuten, und wer davor steht, soll sehen, dass etwas
        # passiert. Und ein Fehler schliesst gar nicht - sonst
        # verschwände die Meldung in dem Moment, in dem man sie lesen
        # soll.
        #

        if self._awaiting is None:
            return

        if state.fight_error:

            self._awaiting = None

            return

        if state.selected_fight == self._awaiting and not state.fight_loading:

            self._awaiting = None

            self.fightLoaded.emit()

    def _fill_days(self, state):

        days = index.group_reports_by_day(state.reports, self._needle)

        signature = (
            state.reports_loading,
            state.selected_report,
            tuple(
                (day.label, tuple(report.code for report in day.reports))
                for day in days
            ),
        )

        if signature == self._days_signature:
            return

        self._days_signature = signature

        self._clear(self.days_body)

        self._day_rows = {}

        if state.reports_loading and not state.reports:

            self._note(self.days_body, "Berichte werden geladen …")

            return

        if not days:

            self._note(
                self.days_body,
                "Keine Berichte gefunden."
                if not state.reports
                else "Kein Bericht passt zur Suche.",
            )

            return

        for day in days:

            self._add_day_heading(day.label)

            for report in day.reports:

                self._add_report_row(report, state.selected_report)

    def _add_day_heading(self, text: str):

        label = QLabel(text)

        label.setFont(font("small"))

        restyle(
            label,
            f"color:{tokens.TEXT['secondary']};font-weight:600;"
            "background:transparent;padding:8px 2px 2px 2px;",
        )

        self._insert(self.days_body, label)

    def _add_report_row(self, report, selected_code: str):

        row = _ReportRow(report.code)

        row.clicked.connect(self._on_report)

        title = QLabel(index.report_title(report))

        restyle(
            title,
            f"font-size:13px;color:{tokens.TEXT['primary']};"
            "background:transparent;border:none;",
        )

        row.layout().addWidget(title)

        subtitle = index.report_subtitle(report)

        if subtitle:

            detail = QLabel(subtitle)

            restyle(
                detail,
                f"font-size:11px;color:{tokens.TEXT['muted']};"
                "background:transparent;border:none;",
            )

            row.layout().addWidget(detail)

        row.set_selected(report.code == selected_code)

        self._day_rows[report.code] = row

        self._insert(self.days_body, row)

    def _fill_fights(self, state):

        groups = index.group_fights(
            state.fights,
            self._needle,
            self._kills_only,
        )

        signature = (
            state.selected_report,
            state.fights_loading,
            state.selected_fight,
            self._kills_only,
            tuple(
                (group.encounter_id, tuple(f.fight_id for f in group.fights))
                for group in groups
            ),
        )

        if signature == self._fights_signature:
            return

        self._fights_signature = signature

        self._clear(self.fights_body)

        self._fight_rows = {}

        count = index.fight_count(groups)

        self.fights_eyebrow.setText(
            f"PULLS · {count}" if count else "PULLS"
        )

        if not state.selected_report:

            self._note(self.fights_body, "Wähle links einen Raidabend.")

            return

        if state.fights_loading and not state.fights:

            self._note(self.fights_body, "Pulls werden geladen …")

            return

        if not groups:

            self._note(
                self.fights_body,
                "In diesem Bericht steht kein Pull, der zu Suche und "
                "Filter passt."
                if state.fights
                else "Dieser Bericht enthält keine Bosskämpfe.",
            )

            return

        for group in groups:

            self._add_boss_heading(group)

            #
            # Der beste Versuch wird nur markiert, wenn es mehr als
            # einen gibt: bei einem einzelnen Pull wäre "bester
            # Versuch" eine Auszeichnung ohne Konkurrenz.
            #

            best = (
                index.best_try(group.fights)
                if len(group.fights) > 1
                else None
            )

            for fight in group.fights:

                self._add_fight_row(
                    state.selected_report,
                    fight,
                    state.selected_fight,
                    best_try=(best is not None and fight.fight_id == best.fight_id),
                )

    def _add_boss_heading(self, group):

        wrap = QWidget()

        layout = QHBoxLayout(wrap)

        layout.setContentsMargins(2, 10, 2, 2)

        layout.setSpacing(8)

        name = QLabel(group.name)

        restyle(
            name,
            f"font-size:13px;font-weight:600;color:{tokens.TEXT['primary']};"
            "background:transparent;",
        )

        layout.addWidget(name)

        summary = QLabel(group.summary)

        restyle(
            summary,
            f"font-size:11px;color:{tokens.TEXT['muted']};"
            "background:transparent;",
        )

        layout.addWidget(summary)

        layout.addStretch()

        self._insert(self.fights_body, wrap)

    def _add_fight_row(self, code, fight, selected_fight, best_try: bool):

        row = _FightRow(code, fight.fight_id)

        row.clicked.connect(self._on_fight)

        line = QHBoxLayout()

        line.setContentsMargins(0, 0, 0, 0)

        line.setSpacing(10)

        pull = QLabel(
            f"Pull {fight.pull_number}" if fight.pull_number else "Pull"
        )

        pull.setFixedWidth(64)

        restyle(
            pull,
            f'font-family:"{tokens.FAMILY_MONO}";font-size:12px;'
            f"color:{tokens.TEXT['secondary']};background:transparent;"
            "border:none;",
        )

        line.addWidget(pull)

        #
        # Uhrzeit statt Datum: das Datum steht links am Abend und
        # zwanzig Mal zu wiederholen wäre Lärm. Fehlt sie, bleibt die
        # Stelle leer statt "00:00" zu behaupten.
        #

        clock = QLabel(fight.time_label)

        clock.setFixedWidth(48)

        restyle(
            clock,
            f'font-family:"{tokens.FAMILY_MONO}";font-size:12px;'
            f"color:{tokens.TEXT['muted']};background:transparent;"
            "border:none;",
        )

        line.addWidget(clock)

        outcome = Chip(
            "KILL" if fight.kill else f"{fight.boss_percentage:.0f} %",
            variant="ok" if fight.kill else "neutral",
        )

        line.addWidget(outcome)

        duration = QLabel(fight.clock)

        restyle(
            duration,
            f'font-family:"{tokens.FAMILY_MONO}";font-size:12px;'
            f"color:{tokens.TEXT['muted']};background:transparent;"
            "border:none;",
        )

        line.addWidget(duration)

        if fight.difficulty_label:

            difficulty = QLabel(fight.difficulty_label)

            restyle(
                difficulty,
                f"font-size:11px;color:{tokens.TEXT['muted']};"
                "background:transparent;border:none;",
            )

            line.addWidget(difficulty)

        line.addStretch()

        #
        # Neben einem Kill wird er nicht ausgezeichnet: dort ist der
        # Kill die Antwort, und ein zweiter Hinweis daneben lenkt nur
        # ab.
        #

        if best_try and not fight.kill:

            line.addWidget(Chip("BESTER VERSUCH", variant="info"))

        row.layout().addLayout(line)

        row.set_selected(fight.fight_id == selected_fight)

        self._fight_rows[fight.fight_id] = row

        self._insert(self.fights_body, row)

    def _update_status(self, state):

        reason = state.fight_error or state.fights_error or state.reports_error

        if reason:

            self.status.setText(reason)

            restyle(
                self.status,
                f"font-size:12px;color:{tokens.STATE_TEXT['error']};"
                "background:transparent;",
            )

            return

        if state.fight_loading:

            #
            # Mit dem Zusatz, weil dieser Schritt wirklich lange
            # dauern kann: der Bot liest dafür die vollständigen
            # Ereignisströme des Kampfes. Ohne den Hinweis sieht ein
            # ehrliches Warten aus wie ein hängender Klick.
            #

            text = (
                index.loading_text(state)
                + " Das Fenster schliesst sich von selbst, sobald er "
                "da ist - auf der Seite darunter läuft ein "
                "Fortschritt mit."
            )

        elif state.fights_loading:
            text = "Pulls werden geladen …"

        elif state.reports_loading:
            text = "Berichte werden geladen …"

        else:
            text = "Ein Klick auf einen Pull lädt ihn in WeintTV und die Academy."

        self.status.setText(text)

        restyle(
            self.status,
            f"font-size:12px;color:{tokens.TEXT['muted']};"
            "background:transparent;",
        )

    # --------------------------------------------------
    # Hilfsmittel
    # --------------------------------------------------

    def _insert(self, body: QWidget, widget: QWidget):
        """
        Vor dem abschliessenden Stretch einfügen, damit die Zeilen
        oben bleiben.
        """

        body.layout().insertWidget(body.layout().count() - 1, widget)

    def _clear(self, body: QWidget):

        layout = body.layout()

        for position in reversed(range(layout.count() - 1)):

            item = layout.takeAt(position)

            widget = item.widget()

            if widget is not None:

                widget.setParent(None)

                widget.deleteLater()

    def _note(self, body: QWidget, text: str):

        label = enable_wrap(QLabel(text))

        restyle(
            label,
            f"font-size:12px;color:{tokens.TEXT['muted']};"
            "background:transparent;padding:8px 2px;",
        )

        self._insert(body, label)


class ArchiveDialog(QDialog):
    """
    Der Browser als modales Fenster.

    Nur noch der Rahmen: Titel, Größe, Hintergrund - und die eine
    Regel, die ein Fenster hat und eine Seite nicht, nämlich sich zu
    schliessen, sobald der angeklickte Pull geladen ist. Der Inhalt
    kommt unverändert von `ArchiveBrowser`.
    """

    def __init__(self, service, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Log auswählen")

        self.setModal(True)

        self.resize(940, 660)

        self.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self,
            f"""
            QDialog{{
                background:{tokens.SURFACE["base"]};
                border:1px solid {tokens.BORDER["base"]};
                border-radius:{tokens.RADIUS["lg"]}px;
            }}
            """,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        self.browser = ArchiveBrowser(service, self)

        self.browser.fightLoaded.connect(self.accept)

        root.addWidget(self.browser)
