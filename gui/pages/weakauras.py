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

Vier Dinge daran sind nicht Geschmack:

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
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.weakaura_library import (
    CATEGORIES,
    CATEGORY_LABELS,
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

    def __init__(self, page, aura: WeakAura = None, entry: CatalogEntry = None, parent=None):

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

        meta = QLabel(f"{CATEGORY_LABELS.get(category, category)} · v{version}")

        meta.setFont(font("small"))

        restyle(meta, f"color:{tokens.TEXT['faint']};background:transparent;")

        left.addWidget(meta)

        root.addLayout(left, 1)

        #
        # Der Chip sagt, wo die Zeile herkommt. "Im Addon" heisst: sie
        # wurde hier noch nie angefasst - ein Klick legt eine
        # Aktualisierung an, statt sie zu bearbeiten.
        #

        if aura is not None:

            root.addWidget(
                Chip("COMPANION", variant="info"),
                alignment=Qt.AlignVCenter,
            )

        else:

            root.addWidget(
                Chip("IM ADDON", variant="neutral"),
                alignment=Qt.AlignVCenter,
            )

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            if self.aura is not None:
                self.page.edit_aura(self.aura)
            else:
                self.page.edit_catalog_entry(self.entry)

        super().mouseReleaseEvent(event)


class WeakAurasPage(Page):

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

        self._delete_armed = False

        self._filling = False

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

    def save(self):

        if self._editing is None:
            return

        aura = self._collect()

        if self._is_new:
            aura.id = make_id(aura.name, taken=self.store.taken_ids())

        if validate(aura, taken_ids=self.store.taken_ids() if self._is_new else None):
            return

        aura.updated_at = now()

        self.store.put(aura)

        self._editing = None

        self._notice = (
            f"„{aura.name}“ ist gespeichert und liegt für das Addon "
            f"bereit. Im Spiel steht sie nach dem nächsten /reload."
        )

        self._deliver()

        self.render()

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

        removed = self.store.remove(self._editing.id)

        self._editing = None

        self._delete_armed = False

        if removed:

            self._notice = (
                f"„{name}“ ist gelöscht. Im Spiel verschwindet die "
                f"Aura nach dem nächsten /reload."
            )

            self._deliver()

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

    def _render_summary(self):

        own = self.store.auras()

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
                f"{len(own)} Aura(s) eingetragen. Welche das Addon kennt, "
                f"steht hier, sobald WeintCodex einmal angemeldet war. "
                f"{reload_note}"
            )

            return

        self.summary.setText(
            f"{len(own)} Aura(s) über die Companion eingetragen, "
            f"{len(known)} im Spiel bekannt. {reload_note}"
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
                (entry.id, entry.name, entry.category, entry.version)
                for entry in self.store.addon_entries()
            ),
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

        addon_entries = self.store.addon_entries()

        if not own and not addon_entries:

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

        if own:

            self.list_layout.addWidget(
                self._section("ÜBER DIE COMPANION EINGETRAGEN")
            )

            for aura in own:
                self.list_layout.addWidget(_AuraRow(self, aura=aura))

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
