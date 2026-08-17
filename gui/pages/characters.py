"""
Meine Charaktere.

**Die Seite hatte bis 2.0.0 keine Datenquelle**, und der Leerzustand
war deshalb die richtige Anzeige und kein Platzhalter: Was lokal über
Charaktere bekannt war, war erstaunlich wenig. Die Twinkliste des
Addons (`"character"`, Name | Klasse | Realm) wird von `SyncManager`
an den Bot weitergereicht und **nicht gespeichert** - sie existiert
für die Dauer eines Sync-Zyklus. Gegenstandsstufe, Ausrüstung oder
Spezialisierung kamen an keiner Stelle vor.

Seit WeintCodex 1.3.3.1 meldet das Addon `"character_sheet"`: den
Ausrüstungsstand des gerade angemeldeten Charakters. `CharacterStore`
sammelt diese Meldungen über mehrere Anmeldungen zu einer Liste
(`core/character_store.py`), und diese Seite zeichnet sie.

Zwei Dinge, die die Seite über ihre Daten sagt und nicht verschweigt:

* **Wer nie eingeloggt war, steht nicht hier.** Die Liste ist die
  Summe der Anmeldungen, keine Kontoübersicht - das Addon kann nur
  melden, was es gesehen hat. Die Fußzeile sagt das, sonst läse sich
  eine unvollständige Liste als vollständige.
* **Der Leerzustand bleibt**, für den Fall, dass noch nichts geliefert
  wurde. Er nennt jetzt aber den nächsten Schritt ("einmal im Spiel
  anmelden") statt "wird nicht übertragen".

Seit 2.0.9 trägt jede Karte links ein **Klassenbild**
(`gui/widgets/class_avatar.py`), an derselben Stelle und in derselben
Rolle wie das Porträt im Kopf der Charakterrubrik von WeintCodex. Das
3D-Modell des Spiels gibt es auf dem Desktop nicht - was hier vorliegt,
ist die Klasse, und die ist genau das, was ein Porträt auf einen Blick
beantwortet.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.character_sheet_sync import readiness
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.wow_colors import class_color, class_label
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.class_avatar import ClassAvatar
from gui.widgets.empty_state import EmptyState
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.wrapped_label import enable_wrap


#
# Wie viele Karten nebeneinander passen. Bei 960 px Fensterbreite
# (dem Mindestmaß) bleiben nach Navigation und Rändern rund 700 px -
# drei Karten wären dort 230 px breit und der Name bräche um.
#

COLUMNS = 3


#
# Das Klassenbild links des Namens - dieselbe Anordnung wie im Kopf
# der Charakterrubrik von WeintCodex, wo links das Porträt und rechts
# daneben Spezialisierung, Titel und Unterzeile stehen. 56 px, weil
# drei Karten nebeneinander bei 960 px Fensterbreite rund 230 px breit
# sind; die 86 px des Spiels würden dort den Namen umbrechen.
#

AVATAR = 56


def _ago(stamp: int) -> str:
    """
    "vor 3 Tagen" statt eines Datums.

    Die Frage vor dieser Zeile ist nicht "wann war das", sondern "ist
    das noch aktuell" - und darauf antwortet ein Abstand direkter als
    ein Kalendertag.
    """

    if not stamp:
        return "Zeitpunkt unbekannt"

    seconds = max(0, int(time.time()) - int(stamp))

    if seconds < 3600:
        return "gerade eben"

    hours = seconds // 3600

    if hours < 24:
        return f"vor {hours} Std."

    days = hours // 24

    if days == 1:
        return "gestern"

    if days < 30:
        return f"vor {days} Tagen"

    return f"vor {days // 30} Mon."


class CharacterCard(Card):
    """
    Eine Karte je Charakter: Name in Klassenfarbe, Spezialisierung,
    Stufe, Gegenstandsstufe und wann er zuletzt gemeldet hat.
    """

    def __init__(self, sheet: dict, parent=None):

        super().__init__(parent=parent)

        color = class_color(sheet.get("class", ""))

        self.setEdgeColor(tokens.tint(color, 0.34))

        #
        # Kopf: Klassenbild, daneben Name und Beschreibung.
        #

        head = QHBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(tokens.SPACE[2])

        self.avatar = ClassAvatar(sheet.get("class", ""), AVATAR)

        head.addWidget(self.avatar, alignment=Qt.AlignTop)

        titles = QVBoxLayout()

        titles.setContentsMargins(0, 0, 0, 0)

        titles.setSpacing(2)

        #
        # Name
        #

        self.name = QLabel(sheet.get("name", ""))

        self.name.setFont(font("h2"))

        restyle(self.name, f"color:{color};background:transparent;")

        titles.addWidget(self.name)

        #
        # Klasse, Spezialisierung, Realm
        #

        parts = []

        spec = sheet.get("spec", "")

        if spec:
            parts.append(spec)

        parts.append(class_label(sheet.get("class", "")) or "Unbekannte Klasse")

        realm = sheet.get("realm", "")

        if realm:
            parts.append(realm)

        self.subtitle = QLabel(" · ".join(part for part in parts if part))

        self.subtitle.setFont(font("small"))

        enable_wrap(self.subtitle)

        restyle(
            self.subtitle,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        titles.addWidget(self.subtitle)

        titles.addStretch(1)

        head.addLayout(titles, 1)

        self.addLayout(head)

        self.addSpacing(tokens.SPACE[1])

        #
        # Die beiden Zahlen, wegen derer man die Seite öffnet.
        #

        numbers = QHBoxLayout()

        numbers.setContentsMargins(0, 0, 0, 0)

        numbers.setSpacing(tokens.SPACE[4])

        numbers.addLayout(
            _stat(
                "STUFE",
                str(sheet.get("level") or "-"),
            )
        )

        item_level = sheet.get("item_level_equipped") or 0.0

        numbers.addLayout(
            _stat(
                "GEGENSTANDSSTUFE",
                f"{item_level:.0f}" if item_level > 0 else "-",
            )
        )

        numbers.addStretch(1)

        self.addLayout(numbers)

        self.addStretch(1)

        #
        # Fuß: Vorbereitungsstand als Chip. `None` heißt "nichts
        # geprüft" und ist etwas anderes als 0 % - deshalb ein eigener,
        # neutraler Chip statt einer roten Null.
        #

        foot = QHBoxLayout()

        foot.setContentsMargins(0, 0, 0, 0)

        foot.setSpacing(tokens.SPACE[1])

        ratio = readiness(sheet)

        if ratio is None:

            foot.addWidget(Chip("KEINE PRÜFUNG", "neutral"))

        else:

            foot.addWidget(
                Chip(
                    f"{ratio * 100:.0f} % AUSGERÜSTET",
                    "ok" if ratio >= 0.999 else "warn",
                )
            )

        foot.addStretch(1)

        self.seen = QLabel(_ago(sheet.get("updated", 0)))

        self.seen.setFont(font("small"))

        restyle(
            self.seen,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        foot.addWidget(self.seen, alignment=Qt.AlignVCenter)

        self.addLayout(foot)


def _stat(label: str, value: str) -> QVBoxLayout:

    column = QVBoxLayout()

    column.setContentsMargins(0, 0, 0, 0)

    column.setSpacing(2)

    column.addWidget(eyebrow_label(label))

    number = QLabel(value)

    number.setFont(font("h2"))

    restyle(number, f"color:{tokens.WHITE};background:transparent;")

    column.addWidget(number)

    return column


class CharactersPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "CHARAKTER",
            "Deine Charaktere sammeln sich hier.",
            parent,
        )

        #
        # Der Leerzustand und das Raster liegen beide dauerhaft in der
        # Seite; `refresh()` blendet um. Beides bei jedem Aufruf neu zu
        # bauen wäre teurer und ließe die Seite beim Wechsel flackern.
        #

        self.empty = EmptyState(
            eyebrow="NOCH KEINE DATEN",
            title="Das Addon hat noch keinen Charakter gemeldet.",
            explanation=(
                "WeintCodex übergibt beim Anmelden im Spiel, welcher "
                "Charakter gespielt wird, samt Gegenstandsstufe, "
                "Verzauberungen und Sockeln. Melde dich einmal im "
                "Spiel an - danach steht der Charakter hier, auch wenn "
                "du ihn längere Zeit nicht spielst."
            ),
            action="Addon prüfen",
            icon="charaktere",
        )

        self.empty.actionTriggered.connect(self._open_addon)

        self.addWidget(self.empty, 1)

        self.grid_host = QWidget()

        self.grid = QGridLayout(self.grid_host)

        self.grid.setContentsMargins(0, 0, 0, 0)

        self.grid.setSpacing(tokens.SPACE[3])

        self.grid.setAlignment(Qt.AlignTop)

        self.addWidget(self.grid_host, 1)

        self.grid_host.hide()

        #
        # Die Liste ist die Summe der Anmeldungen, keine
        # Kontoübersicht. Ohne diesen Satz läse sich eine
        # unvollständige Liste als vollständige.
        #

        self.note = QLabel()

        self.note.setFont(font("small"))

        enable_wrap(self.note)

        restyle(
            self.note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.addWidget(self.note)

        self.note.hide()

        self._signature = None

    # --------------------------------------------------

    def _open_addon(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ADDON)

    # --------------------------------------------------

    def _sheets(self) -> list[dict]:

        store = getattr(self.manager, "characters", None)

        if store is None:
            return []

        return store.characters()

    def refresh(self):

        sheets = self._sheets()

        #
        # `refresh()` läuft bei jedem Seitenwechsel und bei jedem
        # `state_changed`. Ohne diesen Vergleich würde das Raster
        # jedes Mal abgerissen und neu gebaut, obwohl sich nichts
        # geändert hat - dieselbe Regel wie beim ArchivePicker, dessen
        # Auswahlfelder deshalb im Sekundentakt zuklappten.
        #

        signature = tuple(
            (
                sheet.get("name"),
                sheet.get("realm"),
                sheet.get("updated"),
                sheet.get("item_level_equipped"),
            )
            for sheet in sheets
        )

        if signature == self._signature:
            self._apply_title(sheets)
            return

        self._signature = signature

        self._fill(sheets)

        self._apply_title(sheets)

    # --------------------------------------------------

    def _apply_title(self, sheets: list[dict]):

        #
        # Der angemeldete Charakter steht im Titel - er ist die
        # Auskunft, die vor der Liste kommt. Fehlt er (noch), sagt der
        # Titel wieder das Allgemeine.
        #

        name = (
            self.manager.config.data.get("academy_ingame_character", "")
            or ""
        )

        if name:

            self.header.setTitle(f"Im Spiel angemeldet: {name}.")

            return

        if sheets:

            self.header.setTitle(
                f"{len(sheets)} Charakter{'e' if len(sheets) != 1 else ''} "
                f"gemeldet."
            )

            return

        self.header.setTitle("Deine Charaktere sammeln sich hier.")

    def _fill(self, sheets: list[dict]):

        while self.grid.count():

            item = self.grid.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if not sheets:

            self.grid_host.hide()

            self.note.hide()

            self.empty.show()

            return

        self.empty.hide()

        for index, sheet in enumerate(sheets):

            self.grid.addWidget(
                CharacterCard(sheet),
                index // COLUMNS,
                index % COLUMNS,
            )

        #
        # Eine angefangene letzte Zeile soll ihre Karten nicht über die
        # ganze Breite ziehen.
        #

        for column in range(COLUMNS):
            self.grid.setColumnStretch(column, 1)

        #
        # Der freie Platz gehört unter die Karten, nicht in sie hinein.
        # Ohne diese Zeile zieht das Raster die letzte Zeile über die
        # ganze Resthöhe, und eine Karte mit vier Zeilen Inhalt ist
        # 600 px hoch.
        #

        self.grid.setRowStretch(self.grid.rowCount(), 1)

        self.grid_host.show()

        self.note.setText(
            "Ein Charakter erscheint hier, sobald du dich mit ihm im "
            "Spiel angemeldet hast - die Liste ist die Summe deiner "
            "Anmeldungen, nicht die deines Accounts."
        )

        self.note.show()
