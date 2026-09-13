"""
Der Kopfblock des Raid Centers: **welchen Pull habe ich vor mir?**

Die eine Auskunft, die beim Wechsel der Perspektive stehen bleibt - und
damit das Stück Oberfläche, an dem der ganze Umbau auf 4.0 hängt. Wer
von *Analyse* auf *Lernen* wechselt, soll nicht das Gefühl haben, auf
eine andere Seite gewechselt zu sein: derselbe Boss, derselbe Pull,
dasselbe Datum stehen weiter oben, es wechselt nur der Blick darunter.

Bis 3.6.0 gab es diese Auskunft dreimal und jedes Mal anders: WeintTV
hatte den Bossnamen in seinem Kopfblock, die Academy den Satz aus
`encounter_meta()`, das Archiv den aus `selection_text()`. Drei
Formulierungen desselben Sachverhalts, die beim Umschalten kurz
auseinanderliefen - und keine davon nannte Datum und Uhrzeit, obwohl
genau die die Frage "war das der Wipe von gestern?" beantworten.

**Was hier steht, wird nicht hier entschieden.** Die Felder kommen aus
`core/raid_context.context_from()`, die Sätze aus denselben reinen
Funktionen daneben. Dieses Widget liest und malt; es hält keinen
Zustand über den Kampf und trifft keine Entscheidung darüber, was
"Wipe" heisst.

Drei Dinge daran sind nicht Geschmack:

- **Der Charakterwähler gehört zum Kontext**, nicht in die
  Lernansicht. Er stand bis 3.6.0 im Kopf der Academy, also an genau
  einer der drei Seiten - obwohl die Analyse daneben denselben
  Charakter meint, wenn sie "nur ich" zeigt. Weil er jetzt zum Kontext
  gehört, ist er auch beim Wechsel der Perspektive noch da, und ein
  Wechsel wirkt sofort auf Bewertung und Analyse.
- **Die Datenquelle steht als Chip hier und als Zeile in *Quelle*.**
  Der Chip liest `active_source()` - dieselbe Auskunft wie die Zeile
  dort, aus derselben Funktion. Der 2019er Fehler war ein zweiter Chip
  *aus einer anderen Quelle* (dem Label des Snapshots): der widersprach
  der Einstellung kurz nach jedem Wechsel. Eine Beispielquelle wird in
  Warnfarbe benannt, weil "diese Zahlen gehören niemandem" die Auskunft
  ist, ohne die alles darunter falsch gelesen wird.
- **"Zum laufenden Raid" ist ein Knopf und kein Schalter.** Solange
  etwas anderes als der Live-Feed gezeigt wird, ist der Weg zurück die
  häufigste nächste Absicht - und er lag bis 3.6.0 in einem
  Zweifachschalter auf drei Seiten, den man erst finden musste.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from analyzer.models import RaidSnapshot

from core.raid_context import (
    boss_line,
    context_from,
    empty_hint,
    empty_line,
    facts_line,
    instance_line,
    mode_label,
    outcome_label,
    when_line,
)
from core.raid_data_service import (
    MODE_LIVE,
    MODE_REPLAY,
    SOURCE_LABELS,
    is_demo_source,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.wrapped_label import enable_wrap


class SourceChip(Chip):
    """
    Ein Chip, den man anklicken kann.

    Er führt in die Quellenansicht - dorthin, wo sich die Quelle auch
    wechseln lässt. Ein Chip, der eine Einstellung benennt, ohne einen
    Weg zu ihr zu zeigen, ist der Zustand, aus dem die Beschwerde
    "warum kommt mein Raid da nicht vor" entstand.
    """

    clicked = Signal()

    def __init__(self, parent=None):

        super().__init__("", "neutral", parent=parent)

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):

        self.clicked.emit()

        event.accept()


class RaidContextHeader(Card):
    """
    Boss, Pull, Ausgang, Zeitpunkt, Charakter - und die zwei Knöpfe,
    die von hier aus gebraucht werden.
    """

    #
    # In die Quellenansicht wechseln (Klick auf den Quellenchip).
    #

    sourceRequested = Signal()

    #
    # Der Charakter hat sich geändert - das Raid Center zeichnet
    # Bewertung und Analyse neu.
    #

    characterChanged = Signal(str)

    def __init__(self, manager, parent=None):

        super().__init__(parent=parent)

        self.manager = manager

        self.service = manager.raid_data

        self.academy = manager.academy

        self._roster_signature = None

        grid = QGridLayout()

        grid.setContentsMargins(0, 0, 0, 0)

        grid.setHorizontalSpacing(tokens.SPACE[4])

        grid.setVerticalSpacing(tokens.SPACE[2])

        self.identity = self._build_identity()

        grid.addWidget(self.identity, 0, 0)

        self.controls = self._build_controls()

        grid.addWidget(self.controls, 0, 1)

        grid.setColumnStretch(0, 1)

        self.grid = grid

        self._stacked = False

        self.addLayout(grid)

        #
        # Signale. Alle vier, weil der Kontext aus allen vier Quellen
        # entsteht: der Snapshot sagt, was läuft, die Archivauswahl
        # welcher Pull, die Wiedergabe ob gerade abgespielt wird, und
        # die Quelle woher die Zahlen kommen.
        #

        self.service.snapshotChanged.connect(self._on_snapshot)

        self.service.archiveChanged.connect(self.refresh)

        self.service.replayChanged.connect(self.refresh)

        self.service.sourceChanged.connect(self.refresh)

        self.refresh()

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build_identity(self) -> QWidget:

        wrap = QWidget()

        column = QVBoxLayout(wrap)

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(4)

        self.instance = eyebrow_label("")

        column.addWidget(self.instance)

        title_row = QHBoxLayout()

        title_row.setContentsMargins(0, 0, 0, 0)

        title_row.setSpacing(tokens.SPACE[1])

        self.boss = QLabel("")

        self.boss.setFont(font("title"))

        restyle(
            self.boss,
            f"color:{tokens.WHITE};background:transparent;",
        )

        title_row.addWidget(self.boss)

        self.outcome = Chip("", "neutral")

        title_row.addWidget(self.outcome)

        self.mode = Chip("", "info", dot=True)

        title_row.addWidget(self.mode)

        title_row.addStretch(1)

        column.addLayout(title_row)

        facts_row = QHBoxLayout()

        facts_row.setContentsMargins(0, 0, 0, 0)

        facts_row.setSpacing(tokens.SPACE[2])

        self.facts = QLabel("")

        self.facts.setFont(font("mono"))

        restyle(
            self.facts,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        facts_row.addWidget(self.facts)

        self.when = enable_wrap(QLabel(""))

        self.when.setFont(font("small"))

        restyle(
            self.when,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        facts_row.addWidget(self.when, 1)

        column.addLayout(facts_row)

        return wrap

    def _build_controls(self) -> QWidget:

        wrap = QWidget()

        column = QVBoxLayout(wrap)

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(4)

        # --------------------------------------------------
        # Quelle und Charakter
        # --------------------------------------------------

        top = QHBoxLayout()

        top.setContentsMargins(0, 0, 0, 0)

        top.setSpacing(tokens.SPACE[2])

        top.addStretch(1)

        self.source_chip = SourceChip()

        self.source_chip.clicked.connect(self.sourceRequested)

        top.addWidget(self.source_chip)

        character_label = QLabel("Charakter")

        character_label.setFont(font("small"))

        restyle(
            character_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        top.addWidget(character_label)

        self.character_box = QComboBox()

        self.character_box.setMinimumWidth(170)

        self.character_box.currentTextChanged.connect(
            self._on_character_changed
        )

        top.addWidget(self.character_box)

        #
        # "Dem Spiel folgen" muss sichtbar sein: sonst wäre die
        # Automatik ein zweiter, unsichtbarer Akteur an der Auswahlbox -
        # also genau die Beschwerde, die sie behebt.
        #

        self.follow_game = ToggleSwitch(
            self.manager.config.data.get("academy_follow_game", True)
        )

        self.follow_game.toggled.connect(self._on_follow_game_toggled)

        top.addWidget(self.follow_game)

        follow_label = QLabel("Dem Spiel folgen")

        follow_label.setFont(font("small"))

        restyle(
            follow_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        top.addWidget(follow_label)

        column.addLayout(top)

        #
        # Welchen Charakter das Spiel zuletzt gemeldet hat. Ohne diese
        # Zeile ist nicht zu erkennen, warum die Auswahl steht, wo sie
        # steht - und ob die Verbindung zum Addon überhaupt lebt.
        #

        self.ingame_hint = enable_wrap(QLabel(""))

        self.ingame_hint.setFont(font("small"))

        self.ingame_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        restyle(
            self.ingame_hint,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        column.addWidget(self.ingame_hint)

        # --------------------------------------------------
        # Die beiden Knöpfe
        # --------------------------------------------------

        actions = QHBoxLayout()

        actions.setContentsMargins(0, 0, 0, 0)

        actions.setSpacing(tokens.SPACE[1])

        actions.addStretch(1)

        self.live_button = HeroButton("Zum laufenden Raid", primary=False)

        self.live_button.clicked.connect(self.service.show_live)

        actions.addWidget(self.live_button)

        self.play_button = HeroButton("▶  Wiedergabe")

        self.play_button.clicked.connect(self.service.start_replay)

        actions.addWidget(self.play_button)

        column.addLayout(actions)

        return wrap

    # --------------------------------------------------
    # Haltepunkte
    # --------------------------------------------------

    def on_layout_changed(self, state):
        """
        Unter 980 px stehen Kennung und Bedienelemente untereinander.

        Nebeneinander bräuchten sie zusammen rund 900 px, und die
        Knöpfe wären die Hälfte, die abgeschnitten wird - genau das,
        was §14 ausschliesst. Umgehängt und nicht neu gebaut: ein
        Neubau je Fenstergrösse verlöre den Stand der Auswahlbox und
        liesse den Kopf bei jedem Ziehen am Rand flackern.
        """

        stacked = bool(getattr(state, "single_column", False))

        if stacked == self._stacked:
            return

        self._stacked = stacked

        self.grid.removeWidget(self.controls)

        if stacked:

            self.grid.addWidget(self.controls, 1, 0)

        else:

            self.grid.addWidget(self.controls, 0, 1)

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _on_character_changed(self, name: str):

        if not name:
            return

        #
        # Eine Wahl von Hand: sie gilt für den Charakter, auf dem sie
        # getroffen wurde, und stellt sofort ins Addon zu.
        #

        self.academy.note_manual_choice(name)

        self._sync_ingame_hint()

        self.characterChanged.emit(name)

    def show_player(self, name: str):
        """
        Von aussen einen Charakter wählen - der Sprung aus der Analyse
        ("diesen Spieler ansehen").

        Der Sprung ist eine **ausdrückliche** Wahl, anders als der
        Anzeigefilter der Analyse, der die Identität bewusst nicht
        anfasst.
        """

        if not name:
            return

        self.academy.note_manual_choice(name)

        index = self.character_box.findText(name)

        if index >= 0:

            self.character_box.blockSignals(True)

            self.character_box.setCurrentIndex(index)

            self.character_box.blockSignals(False)

        self._sync_ingame_hint()

    def _on_follow_game_toggled(self, checked: bool):

        self.manager.config.data["academy_follow_game"] = bool(checked)

        self.manager.config.save()

        if not checked:

            self._sync_ingame_hint()

            return

        #
        # Wieder eingeschaltet: die zuletzt gemeldete Anmeldung sofort
        # anwenden, statt bis zum nächsten Login zu warten.
        # note_ingame_character() räumt dabei die Handauswahl weg.
        #

        self.manager.config.data["academy_player_source"] = ""

        self.manager.config.data["academy_manual_for"] = ""

        self.manager.config.save()

        self.academy.note_ingame_character(
            self.academy.ingame_character(),
            self.manager.config.data.get("academy_ingame_realm", ""),
        )

        self._sync_ingame_hint()

        self._roster_signature = None

        self.characterChanged.emit(self.academy.player_name())

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _on_snapshot(self, snapshot):

        self.refresh(snapshot)

    def refresh(self, snapshot=None):
        """
        Den Kopf aus dem Kontext beschriften.

        `snapshot` ist optional und nur eine Abkürzung für den Fall,
        dass er gerade ohnehin vorliegt: `context_from()` liest ihn
        sonst selbst vom Dienst. Zwei verschiedene Snapshots in einem
        Bild gibt es damit nicht.
        """

        context = context_from(
            self.service,
            self.academy.player_name(),
        )

        self._apply_identity(context)

        self._apply_source(context)

        self._apply_actions(context)

        #
        # Der Snapshot für die Auswahlliste. `RaidSnapshot.empty()` als
        # Rückfall und kein `None`: `academy.roster()` liest Felder
        # daraus, und ein `None` wäre dort eine Ausnahme in einem
        # Qt-Slot - also ein Fehler ohne Rückverfolgung.
        #

        self._sync_roster(
            snapshot
            if snapshot is not None
            else (self.service.current() or RaidSnapshot.empty())
        )

    def _apply_identity(self, context):

        self.instance.setText(instance_line(context))

        boss = boss_line(context)

        #
        # Ohne Kampf steht hier, **welche** der drei Lagen vorliegt und
        # was der nächste Schritt ist - nicht "keine Daten". Ein
        # gemeinsamer Satz für "lädt gerade", "niemand kämpft" und
        # "nichts gewählt" wäre der Zustand, aus dem man nicht
        # weiterkommt.
        #

        self.boss.setText(boss or empty_line(context))

        restyle(
            self.boss,
            "color:%s;background:transparent;" % (
                tokens.WHITE if boss else tokens.TEXT["muted"]
            ),
        )

        outcome = outcome_label(context)

        self.outcome.setText(outcome.upper())

        self.outcome.setVariant(_outcome_variant(context.outcome))

        self.outcome.setVisible(bool(outcome))

        self.mode.setText(mode_label(context))

        #
        # Nur der laufende Log pulst. Eine Wiedergabe oder das Archiv
        # bewegen sich auch, aber das Zeichen "live" behauptete dort
        # etwas, das nicht stimmt.
        #

        self.mode.setVariant(
            "live"
            if context.live
            else (
                "accent"
                if context.browsing
                else ("info" if context.known else "neutral")
            )
        )

        self.mode.setDotVisible(context.live)

        facts = facts_line(context)

        self.facts.setText(facts)

        self.facts.setVisible(bool(facts))

        #
        # Wo kein Zeitpunkt gemeldet ist, steht der nächste Schritt -
        # der Platz bleibt so nie leer, ohne dass eine Uhrzeit erfunden
        # wird. Ein fehlgeschlagener Abruf nennt dort seinen Grund, und
        # zwar in Warnfarbe: er ist keine Auskunft über den Kampf,
        # sondern eine über die Verbindung.
        #

        self.when.setText(when_line(context) or empty_hint(context))

        restyle(
            self.when,
            "color:%s;background:transparent;" % (
                tokens.STATE_TEXT["warn"]
                if context.error and not when_line(context)
                else tokens.TEXT["muted"]
            ),
        )

    def _apply_source(self, context):

        demo = is_demo_source(context.source)

        self.source_chip.setText(
            (
                SOURCE_LABELS.get(context.source, context.source)
                or "KEINE QUELLE"
            ).upper()
        )

        self.source_chip.setVariant("warn" if demo else "neutral")

        self.source_chip.setToolTip(
            "Beispieldaten - diese Zahlen gehören niemandem. "
            "Klicken, um die Datenquelle zu wechseln."
            if demo
            else "Datenquelle. Klicken, um sie zu wechseln."
        )

    def _apply_actions(self, context):

        #
        # "Zum laufenden Raid" nur, wenn man gerade nicht dort ist.
        # Anders als bei einem Schalter ist das kein Verstecken eines
        # Zustands: der Zustand steht als Chip daneben.
        #

        self.live_button.setVisible(context.mode != MODE_LIVE)

        replay = self.service.replay_state()

        self.play_button.setVisible(
            context.mode != MODE_REPLAY
            and self.service.replay_available()
        )

        #
        # `starting`, nicht `loading`: die Zeitleiste wird schon beim
        # Wählen eines Pulls im Hintergrund geholt. Am ausgegrauten
        # Knopf abzulesen, dass irgendwo etwas lädt, wäre in dem
        # Moment nur irreführend - gedrückt werden darf er trotzdem,
        # der Dienst merkt sich den Start dann vor.
        #

        self.play_button.setEnabled(not replay.starting)

        self.play_button.setText(
            "Wird geladen …"
            if replay.starting
            else "▶  Wiedergabe"
        )

    def _sync_roster(self, snapshot):
        """
        Die Auswahlliste nur dann neu füllen, wenn sich der Raid
        tatsächlich geändert hat - sonst würde sie im Sekundentakt
        zurückspringen, während der Nutzer sie gerade bedient.
        """

        names = self.academy.roster(snapshot)

        if names == self._roster_signature:

            self._sync_ingame_hint()

            return

        self._roster_signature = names

        self._sync_ingame_hint()

        #
        # reconcile_selection() entscheidet UND schreibt fest. Vorher
        # stand hier ein blosses "wenn der gespeicherte Name noch
        # vorkommt, setz ihn" - fehlte er, blieb die Box sichtbar auf
        # dem ersten Namen stehen, während die Config den alten
        # behielt. Die Nutzlast ins Addon entsteht aus der Config,
        # also zeigte die App X und im Spiel stand Y. Nichts schlug
        # dabei fehl, deshalb ist es so lange unentdeckt geblieben.
        #

        selected = self.academy.reconcile_selection(names)

        self.character_box.blockSignals(True)

        self.character_box.clear()

        self.character_box.addItems(names)

        if selected in names:
            self.character_box.setCurrentText(selected)

        self.character_box.blockSignals(False)

        self.character_box.setToolTip(selected or "")

    def _sync_ingame_hint(self):
        """
        Nennt den zuletzt vom Spiel gemeldeten Charakter - und sagt,
        wenn eine Auswahl von Hand ihn gerade überstimmt.
        """

        ingame = self.academy.ingame_character()

        if not ingame:

            #
            # Kurz gehalten: die Zeile steht im Kopfblock, und der ist
            # eng. Der lange Satz (welche Addon-Fassung es dafür
            # braucht) steht im Tooltip - dort sucht ihn, wer wissen
            # will, woran es liegt.
            #

            text = "Ingame noch nicht gemeldet"

        else:

            realm = self.manager.config.data.get("academy_ingame_realm", "")

            text = "Ingame angemeldet: " + ingame + (f"-{realm}" if realm else "")

            manual = (
                self.manager.config.data.get("academy_player_source") == "manual"
                and self.manager.config.data.get("academy_follow_game", True)
            )

            if manual:
                text += "  ·  eigene Auswahl hat Vorrang"

        if self.ingame_hint.text() != text:
            self.ingame_hint.setText(text)

        self.ingame_hint.setToolTip(
            "Das Addon meldet beim Login, welcher Charakter angemeldet "
            "ist - dafür braucht es WeintCodex 1.3.3.0 oder neuer."
            if not ingame
            else text
        )


def _outcome_variant(outcome: str) -> str:
    """
    Die Farbe des Ausgangschips.

    Ein Wipe ist **warn** und nicht **error**: er ist der Normalfall
    beim Lernen eines Bosses, und eine rote Fehlermarke daneben wäre
    ein Urteil über einen Raidabend, der genau so aussehen soll.
    """

    from core.raid_context import OUTCOME_KILL, OUTCOME_OPEN, OUTCOME_WIPE

    if outcome == OUTCOME_KILL:
        return "ok"

    if outcome == OUTCOME_WIPE:
        return "warn"

    if outcome == OUTCOME_OPEN:
        return "live"

    return "neutral"
