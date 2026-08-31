"""
Simmen: das Ergebnis von wowsims in WeintCodex bringen.

Gesimmt wird auf [wowsims.com/mop]. Was dort herauskommt, sind
**Wertegewichte** - und die sind die Schnittstelle: das Addon rechnet
ohnehin mit Gewichten, an drei Stellen (Sockel, Verzauberungen,
Umschmieden). Bisher war der Weg dazwischen von Hand zu gehen, und man
musste ihn kennen: Seite der eigenen Spezialisierung heraussuchen,
Ergebnis kopieren, im Spiel die richtige Unterseite finden und dort in
ein Eingabefeld einfügen, das man erst suchen muss.

**Die Companion simmt nicht selbst, und das ist eine Entscheidung.**
Ein brauchbarer Sim wäre eine eigene Spielsimulation; einer, der nur
so aussieht, wäre schlimmer als keiner, weil seine Zahlen aussehen wie
echte. Dieselbe Linie wie im Addon (dort gibt es aus demselben Grund
keinen Sim) und wie beim Rotationshelfer, der den Tankspecs lieber
keine Prioritätenliste gibt als eine erfundene. Diese Seite übernimmt
den **Weg**, nicht die Rechnung.

Drei Schritte, in dieser Reihenfolge, und die Seite nummeriert sie:

1. Sim öffnen - auf der Seite der gewählten Spezialisierung, nicht auf
   der Startseite. Ein Knopf, der den Handgriff verlangt, den er
   abnehmen sollte, nimmt nichts ab.
2. Ergebnis einfügen - die Zeichenkette aus *Suggest Reforges*,
   dieselbe, die ReforgeLite liest. Ein Wertname plus Zahl geht
   genauso.
3. Ins Spiel bringen - **auf zwei Wegen**, und beide stehen da:

   * Die Companion stellt die Gewichtung über die Addon-Brücke zu; im
     Spiel steht sie nach dem nächsten `/reload` bereit.
   * Oder der `WCIMPORT:SW:`-String, der sich ohne Neuladen unter
     *Import* einfügen lässt.

   Der zweite Weg ist nicht nur bequemer: WoW liest seine
   SavedVariables zur Laufzeit nicht erneut, und wer gerade im Raid
   steht, lädt nicht neu.

**Was ankommt, ist ein Vorschlag und keine Einstellung.** Im Spiel
füllt er die Felder auf *Priorisierung* und wird erst auf Klick
wirksam - dieselbe Regel, die dort für einen von Hand eingefügten Text
schon gilt. Eine Gewichtung, die sich nach einem Login von selbst
geändert hat, wäre von einem Fehler nicht zu unterscheiden. Die Seite
sagt das an beiden Wegen.

Und dieselbe Zurückhaltung an zwei weiteren Stellen:

* **Die Grenzen aus dem Sim werden genannt, nicht übernommen.** 7,5 %
  Treffer und 15 % Waffenkunde gelten für jeden gleich; sie sind eine
  Aussage über das Spiel und stehen im Spec-Profil des Addons. Weicht
  der Sim ab, ist das eine Datenfrage für einen Menschen.
* **Eine Ausgabe für eine andere Klasse wird gemeldet, nicht
  abgewiesen.** Vielleicht simmt jemand für seinen Zweitcharakter -
  aber wissen soll er es.

`refresh()` zeichnet ausschliesslich und fasst das Eingabefeld **nie**
an: die Seite wird bei jeder `state_changed` neu gezeichnet, und ein
halb eingefügter Text unter den Fingern des Nutzers wegzuräumen ist
dieselbe Falle wie beim Adressfeld in Einstellungen → Discord.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.browser import open_url
from core.stat_weights import (
    SPECS,
    STAT_LABELS,
    WeightSet,
    build_transfer,
    class_label,
    normalize,
    ordered,
    parse,
    sim_url,
    spec as spec_of,
    spec_label,
)
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.select import Select
from gui.widgets.wrapped_label import enable_wrap


BASE_PAGE = "https://www.wowsims.com/mop/"


def _spec_items():
    """
    Alle Spezialisierungen, nach Klasse und Name - dieselbe Ordnung,
    in der man sie sucht.
    """

    return [
        (f"{class_label(entry.class_token)} · {entry.label}", entry.key)
        for entry in sorted(
            SPECS,
            key=lambda item: (class_label(item.class_token), item.label),
        )
    ]


class SimPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            eyebrow="CHARAKTER",
            title="Sim-Ergebnis übernehmen.",
            parent=parent,
        )

        self.store = getattr(manager, "stat_weights", None)

        self.sync = getattr(manager, "stat_weights_sync", None)

        #
        # Was zuletzt eingelesen wurde: die skalierte Gewichtung, noch
        # nicht abgelegt. Erst der Knopf darunter macht sie zu einem
        # Eintrag - was von aussen kommt, sieht man sich an, bevor es
        # gilt.
        #

        self._parsed = None

        self._weights: dict[str, int] = {}

        self._build_source_card()

        self._build_paste_card()

        self._build_delivery_card()

        self.body.addStretch(1)

        self.refresh()

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _step(self, card: Card, number: str, text: str):

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        step = QLabel(number)

        step.setFont(font("mono"))

        restyle(
            step,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        row.addWidget(step, 0, Qt.AlignTop)

        title = QLabel(text)

        title.setFont(font("card"))

        restyle(title, f"color:{tokens.WHITE};background:transparent;")

        row.addWidget(title, 1)

        card.root.addLayout(row)

    def _hint(self, card: Card, text: str, color: str = "") -> QLabel:

        label = QLabel(text)

        label.setFont(font("small"))

        enable_wrap(label)

        restyle(
            label,
            f"color:{color or tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(label)

        return label

    # --------------------------------------------------

    def _build_source_card(self):

        card = Card()

        self._step(card, "1", "Charakter simmen")

        self._hint(
            card,
            "Die Ausrüstung stellst du im Sim selbst ein — das weiß nur "
            "er. Danach auf Suggest Reforges drücken und die "
            "Zeichenkette kopieren, die dabei herauskommt.",
        )

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        character_column = QVBoxLayout()

        character_column.setContentsMargins(0, 0, 0, 0)

        character_column.setSpacing(4)

        character_column.addWidget(eyebrow_label("CHARAKTER"))

        self.character_select = Select()

        self.character_select.currentIndexChanged.connect(
            self._on_character_changed,
        )

        character_column.addWidget(self.character_select)

        row.addLayout(character_column, 1)

        spec_column = QVBoxLayout()

        spec_column.setContentsMargins(0, 0, 0, 0)

        spec_column.setSpacing(4)

        spec_column.addWidget(eyebrow_label("SPEZIALISIERUNG"))

        self.spec_select = Select()

        self.spec_select.set_items(_spec_items())

        self.spec_select.currentIndexChanged.connect(
            self._on_spec_changed,
        )

        spec_column.addWidget(self.spec_select)

        row.addLayout(spec_column, 1)

        card.root.addLayout(row)

        #
        # Warum die Spezialisierung neben dem Charakter steht und nicht
        # nur aus ihm folgt: eine zweite Spec ist der Normalfall, und
        # wer sie simmt, will sie hier auch wählen können.
        #

        self.spec_hint = self._hint(
            card,
            "Zweitspezialisierung? Hier umstellen — die Gewichtung "
            "gehört im Spiel zu genau einer.",
            tokens.TEXT["faint"],
        )

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.open_button = HeroButton("Sim öffnen")

        self.open_button.clicked.connect(self._open_sim)

        buttons.addWidget(self.open_button)

        self.url_label = QLabel("")

        self.url_label.setFont(font("small"))

        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        restyle(
            self.url_label,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        buttons.addWidget(self.url_label, 1)

        card.root.addLayout(buttons)

        self.addWidget(card)

    def _build_paste_card(self):

        card = Card()

        self._step(card, "2", "Ergebnis einfügen")

        self.input = QPlainTextEdit()

        self.input.setMinimumHeight(120)

        self.input.setFont(font("mono"))

        self.input.setPlaceholderText(
            "Die Ausgabe des Sims hier ganz hinein — dieselbe, die auch "
            "ReforgeLite liest. Ein Wertname und eine Zahl je Zeile geht "
            "genauso."
        )

        card.root.addWidget(self.input)

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.read_button = HeroButton("Einlesen")

        self.read_button.clicked.connect(self._read)

        buttons.addWidget(self.read_button)

        self.clear_button = HeroButton("Feld leeren", primary=False)

        self.clear_button.clicked.connect(self._clear_input)

        buttons.addWidget(self.clear_button)

        buttons.addStretch(1)

        card.root.addLayout(buttons)

        #
        # Drei getrennte Zeilen, und das ist Absicht: ein Befund, ein
        # Hinweis und ein Fehler raten zu Verschiedenem. Ein Hinweis,
        # der wie ein Fehler aussieht, wird entweder fälschlich ernst
        # genommen oder lehrt, Fehler zu übersehen.
        #

        self.result = QLabel("")

        self.result.setFont(font("small"))

        enable_wrap(self.result)

        restyle(
            self.result,
            f"color:{tokens.WHITE};background:transparent;",
        )

        card.root.addWidget(self.result)

        self.notes = QLabel("")

        self.notes.setFont(font("small"))

        enable_wrap(self.notes)

        restyle(
            self.notes,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.notes)

        self.problem = QLabel("")

        self.problem.setFont(font("small"))

        enable_wrap(self.problem)

        restyle(
            self.problem,
            f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
        )

        card.root.addWidget(self.problem)

        self.apply_button = HeroButton("Für diese Spezialisierung übernehmen")

        self.apply_button.clicked.connect(self._apply)

        self.apply_button.setEnabled(False)

        card.root.addWidget(self.apply_button, 0, Qt.AlignLeft)

        self.addWidget(card)

    def _build_delivery_card(self):

        card = Card()

        self._step(card, "3", "Ins Spiel bringen")

        self.stored = QLabel("")

        self.stored.setFont(font("body"))

        enable_wrap(self.stored)

        restyle(
            self.stored,
            f"color:{tokens.WHITE};background:transparent;",
        )

        card.root.addWidget(self.stored)

        self.stored_weights = QLabel("")

        self.stored_weights.setFont(font("mono"))

        enable_wrap(self.stored_weights)

        restyle(
            self.stored_weights,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.stored_weights)

        self.delivery_hint = self._hint(card, "")

        self.transfer = QLineEdit()

        self.transfer.setReadOnly(True)

        self.transfer.setFont(font("mono"))

        self.transfer.setFixedHeight(36)

        card.root.addWidget(self.transfer)

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.copy_button = HeroButton("String kopieren")

        self.copy_button.clicked.connect(self._copy_transfer)

        buttons.addWidget(self.copy_button)

        self.remove_button = HeroButton("Gewichtung entfernen", primary=False)

        self.remove_button.clicked.connect(self._remove)

        buttons.addWidget(self.remove_button)

        buttons.addStretch(1)

        card.root.addLayout(buttons)

        self.copy_state = QLabel("")

        self.copy_state.setFont(font("small"))

        enable_wrap(self.copy_state)

        restyle(
            self.copy_state,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        card.root.addWidget(self.copy_state)

        self.addWidget(card)

    # --------------------------------------------------
    # Zustand
    # --------------------------------------------------

    def on_enter(self):

        self.refresh()

    def selected_spec(self) -> str:

        return self.spec_select.value() or ""

    def selected_character(self) -> dict:

        key = self.character_select.value()

        for sheet in self._sheets():

            if _sheet_key(sheet) == key:
                return sheet

        return {}

    def _sheets(self) -> list[dict]:

        characters = getattr(self.manager, "characters", None)

        if characters is None:
            return []

        try:
            return characters.characters()

        except Exception:
            return []

    # --------------------------------------------------

    def refresh(self):
        """
        Zeichnet - und fasst das Eingabefeld nicht an.
        """

        self._fill_characters()

        self._draw_source()

        self._draw_stored()

    def _fill_characters(self):

        sheets = self._sheets()

        items = [
            (
                f"{sheet.get('name', '?')} · "
                f"{sheet.get('spec') or spec_label(sheet.get('spec_key', ''))}",
                _sheet_key(sheet),
            )
            for sheet in sheets
        ]

        if not items:

            #
            # Kein gemeldeter Charakter heisst nicht "diese Seite geht
            # nicht": die Spezialisierung lässt sich von Hand wählen,
            # und der Sim braucht ohnehin keinen Namen. Gesagt wird es
            # trotzdem, sonst sieht die leere Liste nach Fehler aus.
            #

            items = [("Noch kein Charakter gemeldet", "")]

        filled = self.character_select.set_items(items)

        self.character_select.setEnabled(bool(sheets))

        if filled and sheets:
            self._on_character_changed()

    def _draw_source(self):

        key = self.selected_spec()

        url = sim_url(key)

        if url:

            self.url_label.setText(url)

            self.open_button.setEnabled(True)

        else:

            #
            # Ein unbekannter Profilschlüssel wird nicht geraten - die
            # Seite einer fremden Spezialisierung sähe genauso aus wie
            # die richtige.
            #

            self.url_label.setText(
                f"{BASE_PAGE} — für diese Spezialisierung ist hier keine "
                f"eigene Seite hinterlegt."
            )

            self.open_button.setEnabled(True)

    def _draw_stored(self):

        key = self.selected_spec()

        entry = self.store.get(key) if self.store else None

        if entry is None:

            self.stored.setText(
                f"Für {spec_label(key)} ist noch keine Gewichtung "
                f"übernommen."
            )

            self.stored_weights.setText("")

            self.delivery_hint.setText(
                "Sobald oben etwas eingelesen und übernommen ist, steht "
                "hier beides: die Zustellung ins Spiel und der String zum "
                "Einfügen ohne Neuladen."
            )

            self.transfer.setText("")

            self.transfer.setEnabled(False)

            self.copy_button.setEnabled(False)

            self.remove_button.setEnabled(False)

            self.header.setTitle("Sim-Ergebnis übernehmen.")

            return

        self.stored.setText(
            f"{spec_label(entry.spec_key)}"
            f"{_from_character(entry)} · {_stamp(entry.created)}"
        )

        self.stored_weights.setText(_weights_text(entry.weights))

        self.delivery_hint.setText(
            "Die Companion hat sie an das Addon übergeben — im Spiel "
            "liegt sie nach dem nächsten /reload unter Charakter → "
            "Priorisierung bereit und wird dort auf deinen Klick "
            "wirksam. Ohne Neuladen: den String hier kopieren und im "
            "Spiel unter Import einfügen."
        )

        self.transfer.setText(build_transfer(entry))

        self.transfer.setEnabled(True)

        self.copy_button.setEnabled(True)

        self.remove_button.setEnabled(True)

        self.header.setTitle(
            f"Gewichtung für {spec_label(entry.spec_key)} liegt bereit."
        )

    # --------------------------------------------------
    # Handlungen
    # --------------------------------------------------

    def _on_character_changed(self):

        sheet = self.selected_character()

        key = (sheet.get("spec_key") or "").strip().upper()

        if key and spec_of(key):
            self.spec_select.select_value(key)

        self._draw_source()

        self._draw_stored()

    def _on_spec_changed(self):

        self._draw_source()

        self._draw_stored()

    def _open_sim(self):

        url = sim_url(self.selected_spec()) or BASE_PAGE

        open_url(url, getattr(self.manager, "logger", None))

    def _clear_input(self):

        self.input.setPlainText("")

        self._parsed = None

        self._weights = {}

        self.result.setText("")

        self.notes.setText("")

        self.problem.setText("")

        self.apply_button.setEnabled(False)

    def _read(self):

        text = self.input.toPlainText()

        parsed = parse(text)

        if parsed.problem:

            self.result.setText("")

            self.notes.setText("")

            self.problem.setText(parsed.problem)

            self.apply_button.setEnabled(False)

            self._weights = {}

            return

        weights, negatives = normalize(parsed.weights)

        if not weights:

            self.result.setText("")

            self.notes.setText("")

            self.problem.setText(
                "Darin steht keine brauchbare Gewichtung — alle Werte "
                "sind null oder negativ."
            )

            self.apply_button.setEnabled(False)

            self._weights = {}

            return

        self._parsed = parsed

        self._weights = weights

        self.problem.setText("")

        self.result.setText(_weights_text(weights))

        self.notes.setText(" ".join(self._note_lines(parsed, negatives)))

        self.apply_button.setEnabled(True)

    def _note_lines(self, parsed, negatives) -> list[str]:
        """
        Was neben den Gewichten noch zu sagen ist - und alles davon
        wird gesagt, nicht verschwiegen: wer es nicht sieht, hält das
        Ergebnis für vollständig.
        """

        lines: list[str] = []

        if negatives:

            lines.append(
                "Negative Gewichte gibt es hier nicht — auf 0 gesetzt: "
                + ", ".join(STAT_LABELS.get(key, key) for key in negatives)
                + "."
            )

        if parsed.ignored:

            lines.append(
                "Nicht übernommen (kennt WeintCodex nicht): "
                + ", ".join(parsed.ignored)
                + "."
            )

        if parsed.caps:

            named = " · ".join(
                f"{STAT_LABELS.get(cap.stat, cap.stat)} "
                f"{_percent(cap.percent)} %"
                for cap in parsed.caps
            )

            lines.append(
                f"Grenzen aus dem Sim: {named}. Sie werden nicht "
                f"übernommen — eine Grenze gilt für jeden gleich und "
                f"steht im Spec-Profil des Addons."
            )

        if parsed.caps_ignored:

            lines.append(
                "Nicht gelesene Grenzen: "
                + ", ".join(parsed.caps_ignored)
                + "."
            )

        expected = spec_of(self.selected_spec())

        if (
            parsed.sim_class
            and expected
            and parsed.sim_class != expected.class_token
        ):

            lines.append(
                f"Achtung: diese Ausgabe ist für "
                f"{class_label(parsed.sim_class)} gerechnet, gewählt ist "
                f"{class_label(expected.class_token)} · {expected.label}."
            )

        return lines

    def _apply(self):

        if not self._weights or self.store is None:
            return

        key = self.selected_spec()

        if not key:
            return

        sheet = self.selected_character()

        entry = self.store.put(
            WeightSet(
                spec_key=key,
                weights=dict(self._weights),
                character=str(sheet.get("name", "")),
                realm=str(sheet.get("realm", "")),
                source=(self._parsed.source if self._parsed else "sim"),
                created=int(time.time()),
            )
        )

        #
        # Sofort zustellen statt auf den Sync-Takt zu warten: wer hier
        # drückt, will gleich `/reload` tippen (dieselbe Überlegung wie
        # beim "Fertig" der WeakAuras-Seite).
        #

        if self.sync is not None:
            self.sync.publish_now()

        self._clear_input()

        self.refresh()

        logger = getattr(self.manager, "logger", None)

        if logger is not None:

            logger.success(
                f"Sim-Gewichtung für {spec_label(entry.spec_key)} "
                f"übernommen."
            )

    def _remove(self):

        if self.store is None:
            return

        if not self.store.remove(self.selected_spec()):
            return

        #
        # Auch das Löschen wird zugestellt: im Spiel verschwindet der
        # Vorschlag dadurch, dass er in der nächsten Zustellung fehlt.
        #

        if self.sync is not None:
            self.sync.publish_now()

        self.copy_state.setText("")

        self.refresh()

    def _copy_transfer(self):

        text = self.transfer.text()

        if not text:
            return

        clipboard = QGuiApplication.clipboard()

        if clipboard is None:

            #
            # Kein Zwischenspeicher (kommt auf einem X-losen System
            # vor): dann steht der String im Feld darüber und lässt
            # sich von Hand markieren. Ein Knopf, der stumm nichts
            # tut, ist der schlechtere Ausgang.
            #

            self.copy_state.setText(
                "Kopieren geht auf diesem System nicht — der String "
                "steht oben und lässt sich markieren."
            )

            return

        clipboard.setText(text)

        self.copy_state.setText(
            "Kopiert. Im Spiel unter Import einfügen — dort wirkt er "
            "sofort, ohne /reload."
        )


# --------------------------------------------------


def _sheet_key(sheet: dict) -> str:

    name = str(sheet.get("name", "")).strip()

    realm = str(sheet.get("realm", "")).strip()

    return f"{name}-{realm}" if realm else name


def _from_character(entry) -> str:

    return f" · {entry.character}" if entry.character else ""


def _stamp(created: int) -> str:

    if not created:
        return "ohne Datum"

    return time.strftime("%d.%m.%Y", time.localtime(created))


def _percent(value: float) -> str:

    return f"{value:.1f}".replace(".", ",")


def _weights_text(weights: dict[str, int]) -> str:

    return " · ".join(
        f"{STAT_LABELS.get(key, key)} {value}"
        for key, value in ordered(weights)
    )
