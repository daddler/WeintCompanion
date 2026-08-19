"""
WeakAuras: eine Aura eintragen, die im Spiel zur Auswahl steht.

Die Frage, die diese Seite beantwortet: **wie kommt eine WeakAura in
WeintCodex, ohne dass jemand ein Addon-Release baut?**

Bis 2.0.12 gab es dafür genau einen Weg - eine Lua-Datei unter
`data/weakauras/` im Addon anlegen, die Datei in die `.toc` eintragen,
eine Version schneiden, ein Release veröffentlichen und warten, bis
alle es installiert haben. Für eine Aura, die zum nächsten Mittwoch
gebraucht wird, ist das kein Weg.

Hier wird sie stattdessen eingetragen und über die bestehende
Addon-Brücke zugestellt (`core/weakaura_sync.py`). Im Spiel steht sie
danach in derselben Liste wie die mitgelieferten und lässt sich mit
demselben Knopf installieren.

Seit 2.2.0 gibt es dafür **zwei Reichweiten**: nur auf diesem Rechner,
oder über den Discord-Bot für die ganze Gilde. Die Freigabe ist eine
eigene Handlung und keine Voreinstellung - alles, was jemand tippt,
ungefragt an 25 Leute zu schicken, wäre die Art Überraschung, die man
einmal erlebt und danach die Funktion meidet.

Sechs Dinge daran sind nicht Geschmack:

* **"Im Spiel nach dem nächsten /reload" steht auf der Seite, nicht in
  der Dokumentation.** WoW liest seine SavedVariables zur Laufzeit
  nicht erneut; eine gerade eingetragene Aura ist im laufenden Spiel
  also nicht da. Wer das nicht weiß, sucht sie - und findet einen
  Fehler, wo keiner ist.
* **Die Liste zeigt auch die mitgelieferten Auren**, obwohl diese Seite
  sie nicht angelegt hat. Das Addon meldet, welche es kennt
  (`weakaura_catalog`); ohne diese Zeilen liesse sich "eine vorhandene
  aktualisieren" nur auf die eigenen Einträge anwenden - und der
  häufigste Fall ist gerade, dass ein mitgeliefertes Klassenpaket eine
  neue Fassung braucht.
* **Die Kennung wird beim Bearbeiten nie neu vergeben.** Sie entscheidet
  im Addon darüber, ob eine Zustellung eine neue Aura ist oder eine
  vorhandene ersetzt. Ein Tippfehler im Namen zu korrigieren darf keine
  zweite Aura erzeugen.
* **Löschen fragt nach.** Der Importstring ist das Einzige, was sich
  nicht wiederherstellen lässt: er steht nur hier und im Spiel des
  Autors.
* **Eine fremde Gildenaura lässt sich hier nicht bearbeiten.** Wer
  keine Raidleitung ist, sieht sie und bekommt sie ins Spiel, ändert
  sie aber nicht - eine Bibliothek, in der jeder alles überschreiben
  kann, ist keine. Entschieden wird das am Bot; hier wird nur nicht
  angeboten, was dort ohnehin mit 403 endete.
* **Eine vergebene Kennung wird benannt, nicht umgangen.** Der Bot
  antwortet mit 409 und nennt den bisherigen Autor; die Seite bietet
  daraufhin "unter neuer Kennung freigeben" an. Still umzubenennen
  erzeugte eine zweite Aura, die aussieht wie die erste, und niemand
  wüsste, welche im Spiel gilt.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.weakaura_client import WeakAuraClient
from core.weakaura_library import (
    CATEGORIES,
    CATEGORY_LABELS,
    SCOPE_GUILD,
    SCOPE_LOCAL,
    CatalogEntry,
    WeakAura,
    aura_from_catalog,
    clean_import_string,
    make_id,
    now,
    validate,
    warnings,
)
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.empty_state import EmptyState
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.select import Select
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.wrapped_label import enable_wrap


#
# Breite der Bearbeitungsspalte. Der Importstring ist das breiteste
# Feld der Seite und soll nicht auf 200 px zusammenschrumpfen, wenn
# das Fenster auf der Mindestbreite steht.
#

EDITOR_WIDTH = 420


def _category_items():

    return [(CATEGORY_LABELS[key], key) for key in CATEGORIES]


class _AuraRow(QWidget):
    """
    Eine Zeile der Liste: Name, Rubrik, Version - und woher sie
    stammt.

    Die ganze Zeile ist anklickbar und lädt den Eintrag in die
    Bearbeitung. Ein eigener Knopf daneben wäre ein zweites Ziel für
    dieselbe Handlung.
    """

    def __init__(
        self,
        page,
        aura: WeakAura = None,
        entry: CatalogEntry = None,
        shadowed: bool = False,
        parent=None,
    ):

        super().__init__(parent)

        self.page = page

        self.aura = aura

        self.entry = entry

        self.setCursor(Qt.PointingHandCursor)

        root = QHBoxLayout(self)

        root.setContentsMargins(0, tokens.SPACE[1], 0, tokens.SPACE[1])

        root.setSpacing(tokens.SPACE[2])

        left = QVBoxLayout()

        left.setContentsMargins(0, 0, 0, 0)

        left.setSpacing(1)

        name = QLabel(aura.name if aura else entry.name)

        name.setFont(font("body"))

        restyle(name, f"color:{tokens.WHITE};background:transparent;")

        left.addWidget(name)

        category = (aura or entry).category

        version = (aura.version if aura else entry.version) or "?"

        parts = [CATEGORY_LABELS.get(category, category), f"v{version}"]

        if aura is not None and aura.shared and aura.author:
            parts.append(aura.author)

        #
        # Der Hinweis, den es sonst nirgends gäbe: eine eigene Aura
        # unter derselben Kennung gewinnt im Spiel gegen die der
        # Gilde. Ohne diese Zeile wäre nicht zu erklären, warum die
        # freigegebene Fassung ingame anders aussieht.
        #

        if shadowed:
            parts.append("eigene Fassung gewinnt")

        meta = QLabel(" · ".join(parts))

        meta.setFont(font("small"))

        restyle(meta, f"color:{tokens.TEXT['faint']};background:transparent;")

        left.addWidget(meta)

        root.addLayout(left, 1)

        #
        # Der Chip sagt, wo die Zeile herkommt. "Im Addon" heisst: sie
        # wurde hier noch nie angefasst - ein Klick legt eine
        # Aktualisierung an, statt sie zu bearbeiten.
        #

        if aura is None:

            root.addWidget(
                Chip("IM ADDON", variant="neutral"),
                alignment=Qt.AlignVCenter,
            )

        elif aura.shared:

            root.addWidget(
                Chip("GILDE", variant="ok"),
                alignment=Qt.AlignVCenter,
            )

        else:

            root.addWidget(
                Chip("NUR HIER", variant="info"),
                alignment=Qt.AlignVCenter,
            )

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            if self.aura is not None:
                self.page.edit_aura(self.aura)
            else:
                self.page.edit_catalog_entry(self.entry)

        super().mouseReleaseEvent(event)


class _GuildRow(QWidget):
    """
    Eine Zeile der Gildenbibliothek, die hier nicht selbst angelegt
    wurde.

    Sie ist **nicht** anklickbar wie die eigenen: bearbeiten liesse
    sich nur, was einem gehört oder was die Raidleitung anfasst, und
    ein Formular, das beim Speichern 403 sagt, ist schlechter als
    keins. Was geht, steht als Knopf daneben.
    """

    def __init__(self, page, aura: WeakAura, moderator: bool, parent=None):

        super().__init__(parent)

        self.page = page

        self.aura = aura

        root = QHBoxLayout(self)

        root.setContentsMargins(0, tokens.SPACE[1], 0, tokens.SPACE[1])

        root.setSpacing(tokens.SPACE[2])

        left = QVBoxLayout()

        left.setContentsMargins(0, 0, 0, 0)

        left.setSpacing(1)

        name = QLabel(aura.name)

        name.setFont(font("body"))

        restyle(name, f"color:{tokens.WHITE};background:transparent;")

        left.addWidget(name)

        parts = [
            CATEGORY_LABELS.get(aura.category, aura.category),
            f"v{aura.version}",
        ]

        if aura.author:
            parts.append(aura.author)

        meta = QLabel(" · ".join(parts))

        meta.setFont(font("small"))

        restyle(meta, f"color:{tokens.TEXT['faint']};background:transparent;")

        left.addWidget(meta)

        root.addLayout(left, 1)

        #
        # Nur für die Raidleitung. Für alle anderen ist die Zeile
        # eine Auskunft: sie bekommen die Aura ins Spiel, ändern sie
        # aber nicht.
        #

        if moderator:

            fix = HeroButton("Rubrik ändern", primary=False)

            fix.clicked.connect(lambda: page.moderate_guild(aura))

            root.addWidget(fix, alignment=Qt.AlignVCenter)

            remove = HeroButton("Entfernen", primary=False)

            remove.clicked.connect(lambda: page.withdraw_guild(aura))

            root.addWidget(remove, alignment=Qt.AlignVCenter)

        root.addWidget(
            Chip("GILDE", variant="ok"),
            alignment=Qt.AlignVCenter,
        )


class WeakAurasPage(Page):

    #
    # Die Netzaufrufe laufen in einem eigenen Thread, zeichnen darf
    # aber nur der Hauptthread. Ein Qt-Signal ist der Weg dorthin -
    # dieselbe Überlegung wie bei `CharacterLinksPage.loaded`.
    #

    finished = Signal()

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            eyebrow="WEAKAURAS",
            title="Was soll im Spiel zur Auswahl stehen?",
            parent=parent,
        )

        self.store = manager.weakauras

        #
        # Der Eintrag, der gerade bearbeitet wird. `None` heisst: die
        # Bearbeitung ist zu. Sie steht nicht dauerhaft offen, weil
        # ein leeres Formular neben einer Liste aussieht, als fehlte
        # etwas.
        #

        self._editing: WeakAura | None = None

        #
        # Ist der Eintrag schon gespeichert? Entscheidet über den
        # Löschknopf und über die Prüfung auf doppelte Kennungen.
        #

        self._is_new = True

        self._delete_armed = False

        #
        # Wird gerade das Formular befüllt? Ohne diesen Riegel frisst
        # sich das Befüllen selbst auf: `setText()` löst `textChanged`
        # aus, das über `_on_edited()` in `_collect()` läuft - und
        # `_collect()` schreibt die Feldwerte in **denselben**
        # Eintrag, aus dem `_fill_editor()` gerade noch liest. Beim
        # Wechsel auf eine andere Aura landete so der Importstring der
        # zuvor bearbeiteten im neuen Formular: sie war halb
        # eingetragen, sah aber vollständig aus.
        #

        self._filling = False

        self._notice = ""

        self.client = WeakAuraClient()

        self.guild_sync = getattr(manager, "weakaura_guild_sync", None)

        #
        # Die Aura, deren Freigabe an einer vergebenen Kennung
        # gescheitert ist. Solange sie hier liegt, bietet die Seite
        # "Unter neuer Kennung freigeben" an.
        #

        self._conflict_aura: WeakAura | None = None

        #
        # Läuft gerade ein Netzaufruf? Ein zweiter Klick soll ihn
        # nicht verdoppeln, und ein Netzaufruf im Klick-Handler friert
        # das Fenster für seine Dauer ein - deshalb ein kurzlebiger
        # Thread, wie bei `ConnectionsPage.sync_now()` und den
        # Archiv-Abrufen.
        #

        self._thread: threading.Thread | None = None

        #
        # Der Ausgang des letzten Netzaufrufs, vom Worker gefüllt und
        # im Hauptthread gezeichnet. Widgets dürfen nur dort
        # entstehen.
        #

        self._pending: WeakAura | None = None

        self._result = None

        self.finished.connect(self._on_finished)

        #
        # Die zuletzt gezeichnete Zusammensetzung der Liste, siehe
        # `_list_signature()`.
        #

        self._list_state = None

        self.new_button = HeroButton("Neue Aura", primary=True)

        self.new_button.clicked.connect(self.start_new)

        self.header.addAction(self.new_button)

        self.summary = QLabel("")

        self.summary.setFont(font("body"))

        enable_wrap(self.summary)

        restyle(
            self.summary,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        self.addWidget(self.summary)

        columns = QHBoxLayout()

        columns.setContentsMargins(0, 0, 0, 0)

        columns.setSpacing(tokens.SPACE[4])

        #
        # Links: die Liste, in einem eigenen Scrollbereich. Der
        # Seiten-Wrapper würde Liste und Bearbeitung gemeinsam
        # scrollen - dann wandert das Formular aus dem Bild, sobald
        # die Liste lang ist.
        #

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(True)

        self.scroll.setFrameShape(QScrollArea.NoFrame)

        restyle(self.scroll, "background:transparent;")

        self.list_host = QWidget()

        self.list_layout = QVBoxLayout(self.list_host)

        self.list_layout.setContentsMargins(0, 0, tokens.SPACE[2], 0)

        self.list_layout.setSpacing(0)

        self.scroll.setWidget(self.list_host)

        columns.addWidget(self.scroll, 1)

        #
        # Rechts: die Bearbeitung.
        #

        self.editor = self._build_editor()

        self.editor.setFixedWidth(EDITOR_WIDTH)

        columns.addWidget(self.editor)

        self.addLayout(columns, 1)

        self.render()

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def refresh(self):
        """
        Nur zeichnen - keine Netzrunde, kein `full_refresh()`. Siehe
        `tests/test_update_visibility.py`.
        """

        self.render()

    def on_leave(self):
        """
        Die Rückmeldung ("… ist gespeichert") beschreibt, was gerade
        getan wurde. Wer die Seite verlässt und später zurückkommt,
        soll nicht eine Meldung von vorgestern lesen, die klingt, als
        sei eben etwas passiert.
        """

        self._notice = ""

    # --------------------------------------------------
    # Aufbau der Bearbeitung
    # --------------------------------------------------

    def _build_editor(self) -> Card:

        card = Card(accent=True)

        card.root.setSpacing(tokens.SPACE[2])

        self.editor_eyebrow = eyebrow_label("NEUE AURA")

        card.root.addWidget(self.editor_eyebrow)

        self.name_input = self._line(card, "Name", "Wie die Aura im Spiel heisst")

        self.category_input = Select()

        self.category_input.set_items(_category_items(), current=CATEGORIES[0])

        card.root.addWidget(self._label("Rubrik"))

        card.root.addWidget(self.category_input)

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        version_column = QVBoxLayout()

        version_column.setContentsMargins(0, 0, 0, 0)

        version_column.setSpacing(4)

        version_column.addWidget(self._label("Version"))

        self.version_input = QLineEdit("1.0")

        self.version_input.setFixedHeight(36)

        self.version_input.setFont(font("body"))

        version_column.addWidget(self.version_input)

        row.addLayout(version_column, 1)

        author_column = QVBoxLayout()

        author_column.setContentsMargins(0, 0, 0, 0)

        author_column.setSpacing(4)

        author_column.addWidget(self._label("Autor"))

        self.author_input = QLineEdit()

        self.author_input.setPlaceholderText("optional")

        self.author_input.setFixedHeight(36)

        self.author_input.setFont(font("body"))

        author_column.addWidget(self.author_input)

        row.addLayout(author_column, 1)

        card.root.addLayout(row)

        self.icon_input = self._line(
            card,
            "Symbol",
            "Interface\\Icons\\... (optional)",
        )

        card.root.addWidget(self._label("Beschreibung"))

        self.description_input = QPlainTextEdit()

        self.description_input.setFixedHeight(64)

        self.description_input.setFont(font("body"))

        self.description_input.setPlaceholderText(
            "Was kann die Aura? Steht im Spiel in der Zeile."
        )

        card.root.addWidget(self.description_input)

        card.root.addWidget(self._label("WeakAuras-String"))

        self.string_input = QPlainTextEdit()

        self.string_input.setMinimumHeight(96)

        self.string_input.setFont(font("mono"))

        self.string_input.setPlaceholderText(
            "!WA:2!... - im Spiel über WeakAuras exportieren und hier einfügen"
        )

        card.root.addWidget(self.string_input, 1)

        #
        # Was noch fehlt bzw. was auffällt. Zwei getrennte Zeilen:
        # ein Hinweis, der wie ein Fehler aussieht, wird entweder
        # fälschlich ernst genommen oder lehrt, Fehler zu übersehen.
        #

        self.problems = QLabel("")

        self.problems.setFont(font("small"))

        enable_wrap(self.problems)

        restyle(
            self.problems,
            f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
        )

        card.root.addWidget(self.problems)

        self.hints = QLabel("")

        self.hints.setFont(font("small"))

        enable_wrap(self.hints)

        restyle(
            self.hints,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.hints)

        #
        # Die Reichweite. Bewusst ein Schalter im Formular und nicht
        # zwei "Fertig"-Knöpfe: es ist eine Eigenschaft der Aura, die
        # sich später ändern lässt, keine zwei verschiedenen
        # Handlungen.
        #

        share_row = QHBoxLayout()

        share_row.setContentsMargins(0, tokens.SPACE[1], 0, 0)

        share_row.setSpacing(tokens.SPACE[2])

        self.share_toggle = ToggleSwitch()

        self.share_toggle.toggled.connect(self._on_share_toggled)

        share_row.addWidget(self.share_toggle, alignment=Qt.AlignVCenter)

        share_label = QLabel("Für die Gilde freigeben")

        share_label.setFont(font("body"))

        restyle(
            share_label,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        share_row.addWidget(share_label, alignment=Qt.AlignVCenter)

        share_row.addStretch(1)

        card.root.addLayout(share_row)

        self.share_hint = QLabel("")

        self.share_hint.setFont(font("small"))

        enable_wrap(self.share_hint)

        restyle(
            self.share_hint,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.share_hint)

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[1])

        self.save_button = HeroButton("Fertig", primary=True)

        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.save_button)

        self.cancel_button = HeroButton("Abbrechen", primary=False)

        self.cancel_button.clicked.connect(self.close_editor)

        buttons.addWidget(self.cancel_button)

        buttons.addStretch(1)

        self.delete_button = HeroButton("Löschen", primary=False)

        self.delete_button.clicked.connect(self.delete)

        buttons.addWidget(self.delete_button)

        card.root.addLayout(buttons)

        for widget in (
            self.name_input,
            self.version_input,
            self.author_input,
            self.icon_input,
        ):
            widget.textChanged.connect(self._on_edited)

        self.description_input.textChanged.connect(self._on_edited)

        self.string_input.textChanged.connect(self._on_edited)

        self.category_input.currentIndexChanged.connect(self._on_edited)

        return card

    def _label(self, text: str) -> QLabel:

        label = QLabel(text)

        label.setFont(font("small"))

        restyle(
            label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        return label

    def _line(self, card: Card, label: str, placeholder: str) -> QLineEdit:

        card.root.addWidget(self._label(label))

        field = QLineEdit()

        field.setPlaceholderText(placeholder)

        field.setFixedHeight(36)

        field.setFont(font("body"))

        card.root.addWidget(field)

        return field

    # --------------------------------------------------
    # Bearbeitung öffnen und schliessen
    # --------------------------------------------------

    def start_new(self):

        self._editing = WeakAura()

        self._is_new = True

        self._notice = ""

        self._conflict_aura = None

        self._fill_editor(self._editing)

        self.render()

        self.name_input.setFocus()

    def edit_aura(self, aura: WeakAura):

        #
        # Eine Kopie: wer abbricht, soll die Liste unverändert
        # vorfinden. Ohne sie schriebe jeder Tastendruck in den
        # gespeicherten Eintrag.
        #

        self._editing = WeakAura(**vars(aura))

        self._is_new = False

        self._notice = ""

        self._conflict_aura = None

        self._fill_editor(self._editing)

        self.render()

    def edit_catalog_entry(self, entry: CatalogEntry):
        """
        Eine im Spiel vorhandene Aura aktualisieren.

        Der Importstring bleibt leer - das Addon meldet ihn nicht mit,
        und wer aktualisiert, bringt ohnehin eine neue Zeichenkette
        mit. Die **Kennung** wird übernommen: an ihr erkennt das
        Addon, dass es die vorhandene Aura ersetzen soll statt eine
        zweite anzulegen.
        """

        self._editing = aura_from_catalog(entry)

        self._is_new = False

        self._notice = (
            f"„{entry.name}“ wird ersetzt. Die bisherige Fassung "
            f"bleibt im Addon-Ordner liegen, im Spiel steht ab dem "
            f"nächsten /reload diese hier."
        )

        self._fill_editor(self._editing)

        self.render()

        self.string_input.setFocus()

    def close_editor(self):

        self._editing = None

        self._notice = ""

        self._delete_armed = False

        self.render()

    def _fill_editor(self, aura: WeakAura):

        self._filling = True

        self.name_input.setText(aura.name)

        self.category_input.select_value(aura.category)

        self.version_input.setText(aura.version)

        self.author_input.setText(aura.author)

        self.icon_input.setText(aura.icon)

        self.description_input.setPlainText(aura.description)

        self.string_input.setPlainText(aura.string)

        self.share_toggle.setChecked(aura.shared)

        self._delete_armed = False

        self._filling = False

        self._update_share_hint()

    def _collect(self) -> WeakAura:
        """
        Den Formularstand in den bearbeiteten Eintrag übernehmen.

        Die Kennung wird hier **nicht** angefasst: sie steht seit dem
        Öffnen fest und wird erst beim Speichern eines neuen Eintrags
        vergeben.
        """

        aura = self._editing

        aura.name = self.name_input.text().strip()

        aura.category = self.category_input.value() or CATEGORIES[0]

        aura.version = self.version_input.text().strip()

        aura.author = self.author_input.text().strip()

        aura.icon = self.icon_input.text().strip()

        aura.description = self.description_input.toPlainText().strip()

        aura.string = clean_import_string(self.string_input.toPlainText())

        aura.scope = SCOPE_GUILD if self.share_toggle.isChecked() else SCOPE_LOCAL

        return aura

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def _on_edited(self):

        if self._editing is None or self._filling:
            return

        #
        # Ein begonnenes Löschen ist mit der nächsten Änderung vom
        # Tisch: sonst stünde der scharfgeschaltete Knopf noch da,
        # während längst weitergetippt wird.
        #

        self._delete_armed = False

        self._update_validation()

    def _update_validation(self):

        aura = self._collect()

        taken = self.store.taken_ids() if self._is_new else None

        problems = validate(aura, taken_ids=taken)

        self.problems.setText(" ".join(problems))

        self.problems.setVisible(bool(problems))

        notes = warnings(aura)

        self.hints.setText(" ".join(notes))

        self.hints.setVisible(bool(notes))

        self.save_button.setEnabled(not problems)

        self.delete_button.setVisible(not self._is_new)

        self.delete_button.setText(
            "Wirklich löschen?" if self._delete_armed else "Löschen"
        )

    def _on_share_toggled(self, _checked=False):

        if self._filling:
            return

        self._update_share_hint()

    def _update_share_hint(self):
        """
        Was der Schalter bedeutet - in Worten, nicht als Symbol.

        Freigeben schickt einen Importstring an alle. Das ist nichts,
        was man aus einem Schalterzustand erraten soll.
        """

        if not self.share_toggle.isChecked():

            self.share_hint.setText(
                "Die Aura bleibt auf diesem Rechner und geht nur in dein "
                "eigenes WeintCodex."
            )

            return

        if not self.client.own_discord_id():

            self.share_hint.setText(
                "Dafür muss unter Einstellungen → Discord ein Konto "
                "verknüpft sein - die Bibliothek läuft über den Bot."
            )

            return

        self.share_hint.setText(
            "Die Aura wird in die Bibliothek der Gilde gestellt. Alle "
            "mit verknüpfter Companion bekommen sie in ihr WeintCodex."
        )

    # --------------------------------------------------

    def save(self):

        if self._editing is None or self._busy():
            return

        aura = self._collect()

        if self._is_new:
            aura.id = make_id(aura.name, taken=self.store.taken_ids())

        if validate(aura, taken_ids=self.store.taken_ids() if self._is_new else None):
            return

        aura.updated_at = now()

        #
        # Lokal zuerst, immer. Auch eine freigegebene Aura gehört auf
        # diesen Rechner: sonst wäre sie nach einem 409 oder einem
        # nicht erreichbaren Bot komplett weg, obwohl sie gerade
        # getippt wurde.
        #

        self.store.put(aura)

        self._editing = None

        self._deliver()

        if not aura.shared:

            self._notice = (
                f"„{aura.name}“ ist gespeichert und liegt für das Addon "
                f"bereit. Im Spiel steht sie nach dem nächsten /reload."
            )

            self.render()

            return

        #
        # Und jetzt in die Bibliothek. Im Thread: eine Netzrunde im
        # Klick-Handler friert das Fenster für ihre Dauer ein.
        #

        self._run(
            aura,
            lambda: self.client.publish(aura),
            f"„{aura.name}“ wird freigegeben …",
        )

    # --------------------------------------------------
    # Die Bibliothek der Gilde
    # --------------------------------------------------

    def _busy(self) -> bool:

        return self._thread is not None and self._thread.is_alive()

    def _run(self, aura, call, notice):
        """
        Einen Netzaufruf starten und die Seite so lange sperren.

        `call` wird im Worker ausgeführt und liefert ein
        `WriteResult`; gezeichnet wird erst wieder im Hauptthread,
        über `finished`.
        """

        self._pending = aura

        self._result = None

        self._notice = notice

        self.new_button.setEnabled(False)

        self.render()

        def worker():

            try:
                self._result = call()

            except Exception as exc:

                #
                # Der Client fängt eigentlich alles ab. Bleibt
                # trotzdem etwas übrig, darf es nicht den Thread
                # sprengen und die Seite für immer gesperrt lassen.
                #

                from core.weakaura_client import WriteResult

                self._result = WriteResult(reason=f"Unerwarteter Fehler: {exc}")

            self.finished.emit()

        self._thread = threading.Thread(
            target=worker,
            daemon=True,
            name="WeakAuraLibrary",
        )

        self._thread.start()

    def _on_finished(self):

        self.new_button.setEnabled(True)

        result = self._result

        aura = self._pending

        self._result, self._pending = None, None

        if result is None:
            self.render()
            return

        if result.ok:

            #
            # Der Bot kann eine andere Kennung vergeben haben (nach
            # "unter neuer Kennung freigeben"). Dann ist der lokale
            # Eintrag unter der alten Kennung der falsche - er wird
            # umgehängt, statt beide stehen zu lassen.
            #

            if aura is not None and result.aura is not None:

                if result.aura.id != aura.id:

                    self.store.remove(aura.id)

                    aura.id = result.aura.id

                    self.store.put(aura)

            self._notice = (
                f"„{result.aura.name if result.aura else ''}“ liegt in der "
                f"Bibliothek der Gilde. Alle mit verknüpfter Companion "
                f"bekommen sie beim nächsten Abgleich."
                if result.aura
                else "Erledigt."
            )

            if self.guild_sync is not None:
                self.guild_sync.invalidate()

            self._deliver()

            self.render()

            return

        if result.conflict and aura is not None:

            #
            # Die Kennung gehört jemand anderem. Der Bot benennt von
            # sich aus nichts um - das erzeugte eine zweite Aura, die
            # aussieht wie die erste. Stattdessen wird gefragt.
            #

            self._conflict_aura = aura

            self._notice = (
                f"{result.reason} Mit „Unter neuer Kennung freigeben“ "
                f"landet deine Fassung daneben in der Bibliothek."
            )

            self.render()

            return

        #
        # Fehlgeschlagen. Lokal ist die Aura gespeichert, im Spiel ist
        # sie da - nur geteilt ist sie nicht. Genau das steht auch da,
        # statt eines "Fehler beim Speichern", das mehr behauptet.
        #

        self._notice = (
            f"Freigeben hat nicht geklappt: {result.reason} Die Aura ist "
            f"gespeichert und steht in deinem eigenen WeintCodex."
        )

        self.render()

    def publish_again(self):
        """
        Nach einem 409: unter einer neuen Kennung freigeben.

        Ausdrücklich nur auf Knopfdruck - siehe den Kopfkommentar.
        """

        aura = getattr(self, "_conflict_aura", None)

        if aura is None or self._busy():
            return

        self._conflict_aura = None

        self._run(
            aura,
            lambda: self.client.publish(aura, rename=True),
            f"„{aura.name}“ wird unter neuer Kennung freigegeben …",
        )

    def moderate_guild(self, aura: WeakAura):
        """
        Die Rubrik einer fremden Gildenaura richtigstellen.

        Reihum durch die drei Rubriken statt eines eigenen Dialogs:
        es gibt genau drei, und die häufigste Korrektur ist "die steht
        unter der falschen".
        """

        if self._busy():
            return

        order = list(CATEGORIES)

        try:
            following = order[(order.index(aura.category) + 1) % len(order)]

        except ValueError:
            following = order[0]

        self._run(
            None,
            lambda: self.client.moderate(aura.id, category=following),
            f"„{aura.name}“ wird nach "
            f"{CATEGORY_LABELS[following]} verschoben …",
        )

    def withdraw_guild(self, aura: WeakAura):
        """
        Eine fremde Gildenaura aus der Bibliothek nehmen.

        Ohne Rückfrage, anders als beim eigenen Löschen: hier geht
        nichts verloren, was nur hier läge - der Autor hat sie
        weiterhin in seiner eigenen Companion und kann sie erneut
        freigeben. Genau das steht auch in der Rückmeldung.
        """

        if self._busy():
            return

        self._run(
            None,
            lambda: self.client.withdraw(aura.id),
            f"„{aura.name}“ wird aus der Bibliothek genommen …",
        )

    def delete(self):

        if self._editing is None or self._is_new:
            return

        #
        # Zwei Schritte, wie `/wc access reset` im Addon: der
        # Importstring steht nur hier und im Spiel des Autors, ein
        # versehentlicher Klick ist also nicht rückgängig zu machen.
        #

        if not self._delete_armed:

            self._delete_armed = True

            self._update_validation()

            return

        name = self._editing.name

        aura_id = self._editing.id

        was_shared = self._editing.shared

        removed = self.store.remove(aura_id)

        self._editing = None

        self._delete_armed = False

        if removed:

            self._notice = (
                f"„{name}“ ist gelöscht. Im Spiel verschwindet die "
                f"Aura nach dem nächsten /reload."
            )

            self._deliver()

            #
            # Eine freigegebene Aura muss auch aus der Bibliothek.
            # Sonst holt der nächste Abgleich sie zurück, und sie
            # wäre nicht wegzubekommen - die Löschung sähe aus, als
            # hätte sie nicht funktioniert.
            #

            if was_shared and self.client.own_discord_id():

                self._run(
                    None,
                    lambda: self.client.withdraw(aura_id),
                    f"„{name}“ ist gelöscht und wird aus der Bibliothek "
                    f"genommen …",
                )

                return

        else:

            #
            # Eine mitgelieferte Aura lässt sich hier nicht löschen -
            # sie steckt im Addon-ZIP. Das ist keine Störung, sondern
            # die ehrliche Auskunft darüber, wem sie gehört.
            #

            self._notice = (
                "Diese Aura kommt mit dem Addon und lässt sich hier nicht "
                "entfernen - nur durch eine neuere Fassung ersetzen."
            )

        self.render()

    def _deliver(self):
        """
        Sofort zustellen, statt auf den nächsten Sync-Takt zu warten.

        Ohne das läge zwischen "Fertig" und der Datei bis zu ein
        Sync-Intervall - und wer in dieser Zeit `/reload` drückt,
        findet nichts und hält es für kaputt.
        """

        sync = getattr(self.manager, "weakaura_sync", None)

        if sync is not None:
            sync.publish_now()

    # --------------------------------------------------
    # Zeichnen
    # --------------------------------------------------

    def render(self):

        self._render_summary()

        self._render_list()

        self.editor.setVisible(self._editing is not None)

        if self._editing is not None:

            self.editor_eyebrow.setText(
                "NEUE AURA" if self._is_new else "AURA BEARBEITEN"
            )

            self._update_validation()

    def _may_moderate(self) -> bool:
        """
        Darf hier eine fremde Gildenaura angefasst werden?

        Ohne verknüpftes Konto sicher nicht. Ob die Raidlead-Rolle da
        ist, weiß allein der Bot - deshalb werden die Knöpfe gezeigt
        und ein 403 als Antwort erklärt, statt sie zu verstecken:
        dieselbe Regel wie bei der Charakterzuordnung
        (*lock, don't hide*). Ein Bereich, der je nach Rolle
        verschwindet, lässt sich weder erklären noch danach fragen.
        """

        return bool(self.client.own_discord_id())

    def _render_summary(self):

        own = self.store.auras()

        guild = self.store.guild_auras()

        known = self.store.catalog()

        if self._notice:

            self.summary.setText(self._notice)

            return

        #
        # Der Katalog kommt erst, wenn WeintCodex 2.1.0.0 einmal
        # gelaufen ist. Solange er leer ist, wird über ihn **keine
        # Zahl behauptet**: "0 im Spiel bekannt" wäre schlicht falsch,
        # sobald hier bereits etwas eingetragen und zugestellt ist -
        # dieselbe Linie wie `stars == 0` und `readiness() is None`.
        #

        reload_note = (
            "Änderungen sind im Spiel nach dem nächsten /reload da - "
            "WoW liest seine Daten nur beim Laden."
        )

        if not known:

            if not own:

                self.summary.setText(
                    "Sobald WeintCodex einmal angemeldet war, steht hier, "
                    "welche Auren es kennt. Eine neue lässt sich schon jetzt "
                    "eintragen."
                )

                return

            self.summary.setText(
                f"{len(own)} Aura(s) eingetragen"
                + (f", {len(guild)} aus der Gilde" if guild else "")
                + f". Welche das Addon kennt, steht hier, sobald "
                f"WeintCodex einmal angemeldet war. {reload_note}"
            )

            return

        shared_note = (
            f" {len(guild)} aus der Gilde."
            if guild
            else ""
        )

        self.summary.setText(
            f"{len(own)} Aura(s) über die Companion eingetragen, "
            f"{len(known)} im Spiel bekannt.{shared_note} {reload_note}"
        )

    def _list_signature(self):
        """
        Woraus die Liste besteht - ohne sie zu bauen.

        `refresh()` läuft bei jeder Zustandsmeldung des Managers, also
        etwa im Sync-Takt. Ein unbedingtes Neuaufbauen setzte dabei die
        Bildlaufposition zurück, während jemand die Liste durchsieht -
        dieselbe Falle, wegen der `ArchivePicker` seine Auswahlkästen
        erst vergleicht (siehe `gui/widgets/select.py`).
        """

        return (
            tuple(
                (aura.id, aura.name, aura.category, aura.version)
                for aura in self.store.auras()
            ),
            tuple(
                (aura.id, aura.name, aura.category, aura.version)
                for aura in self.store.guild_auras()
            ),
            tuple(
                (entry.id, entry.name, entry.category, entry.version)
                for entry in self.store.addon_entries()
            ),
            tuple(sorted(self.store.shadowed_ids())),
            self._conflict_aura.id if self._conflict_aura else "",
        )

    def _render_list(self):

        signature = self._list_signature()

        if signature == self._list_state:
            return

        self._list_state = signature

        while self.list_layout.count():

            item = self.list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        own = self.store.auras()

        shadowed = self.store.shadowed_ids()

        #
        # Nur die Zeilen anderer Leute. Eine eigene freigegebene Aura
        # steht schon oben und wäre hier ein zweites Mal dasselbe.
        #

        guild = [
            aura
            for aura in self.store.guild_auras()
            if aura.id not in self.store.own_ids()
        ]

        addon_entries = self.store.addon_entries()

        if not own and not guild and not addon_entries:

            empty = EmptyState(
                eyebrow="NOCH NICHTS EINGETRAGEN",
                title="Keine Aura hinterlegt",
                explanation=(
                    "Trage eine Aura ein, damit sie im Spiel unter WeakAuras "
                    "zur Auswahl steht. Gebraucht werden ein Name, eine "
                    "Rubrik und der Export-String aus WeakAuras."
                ),
                action="Neue Aura",
                icon="weakauras",
            )

            empty.actionTriggered.connect(self.start_new)

            self.list_layout.addWidget(empty, 1)

            return

        if self._conflict_aura is not None:

            #
            # Der eine Fall, in dem eine Handlung über der Liste
            # steht: die Freigabe ist an einer vergebenen Kennung
            # gescheitert, und die Antwort darauf ist eine
            # Entscheidung, keine Meldung.
            #

            again = HeroButton("Unter neuer Kennung freigeben", primary=True)

            again.clicked.connect(self.publish_again)

            self.list_layout.addWidget(again, alignment=Qt.AlignLeft)

        if own:

            self.list_layout.addWidget(
                self._section("VON DIESEM RECHNER")
            )

            for aura in own:
                self.list_layout.addWidget(
                    _AuraRow(self, aura=aura, shadowed=aura.id in shadowed)
                )

        if guild:

            self.list_layout.addWidget(
                self._section("AUS DER GILDE")
            )

            moderator = self._may_moderate()

            for aura in guild:
                self.list_layout.addWidget(_GuildRow(self, aura, moderator))

        if addon_entries:

            self.list_layout.addWidget(
                self._section("MIT DEM ADDON GELIEFERT")
            )

            for entry in addon_entries:
                self.list_layout.addWidget(_AuraRow(self, entry=entry))

        self.list_layout.addStretch(1)

    def _section(self, text: str) -> QWidget:

        host = QWidget()

        layout = QVBoxLayout(host)

        layout.setContentsMargins(0, tokens.SPACE[3], 0, tokens.SPACE[1])

        layout.setSpacing(0)

        layout.addWidget(eyebrow_label(text))

        return host
