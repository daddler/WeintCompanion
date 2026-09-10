"""
Charakterzuordnung (Raidleitung).

Die Frage, die diese Seite beantwortet: **wer aus der Anmeldung lässt
sich ingame überhaupt einladen?**

Der Kalender-Invite in WeintCodex adressiert echte Charakternamen. Der
Bot kennt sie nur, wenn der Spieler die Companion verknüpft *und*
seine Twinkverwaltung gepflegt hat - drei Voraussetzungen, von denen
Gildenfremde die erste kaum erfüllen können. Für alle anderen schickte
er den Discord-Anzeigenamen weiter. Den gibt es ingame nicht:
`C_Calendar.EventInvite` läuft ins Leere und meldet das nicht einmal,
also fiel die Lücke frühestens am leeren Kalender auf.

Diese Seite ist die zweite von zwei Stellen, an denen sie sich
schliessen lässt - die andere ist `/weintcharakter` in Discord. Beide
schreiben dieselbe Tabelle im Bot; hier gibt es dafür die Liste vor
sich statt eines Befehls, den man auswendig können muss.

Drei Dinge daran sind nicht Geschmack:

* **Offene Zuordnungen stehen oben.** Der Bot sortiert bereits so. Das
  ist die Frage, mit der man diese Seite öffnet; die bereits geklärten
  Zeilen sind nur der Beleg, dass nichts übersehen wurde.
* **Die Seite wird nicht versteckt, sondern gesperrt.** Ohne die
  Raidlead-Rolle antwortet der Bot mit 403, und dann steht hier, wofür
  sie da wäre. Dieselbe Regel wie im Addon (`core/access.lua`:
  „lock, don't hide") - ein Bereich, der je nach Rolle verschwindet,
  lässt sich nicht erklären und nicht danach fragen.
* **Jeder Abruf läuft in einem kurzlebigen Thread**, wie die
  Archiv-Abrufe und `ConnectionsPage.sync_now()`. Eine Netzrunde im
  Klick-Handler friert das Fenster für ihre Dauer ein, und `refresh()`
  darf ohnehin nur zeichnen.

**Und seit 3.5.0: welcher Raid?** Im Discord dürfen mehrere
Anmeldungen nebeneinander laufen (ein 25er für die Twinks, später ein
10er für die Mains). Diese Seite fragte den Bot ohne Angabe, und ohne
Angabe antwortet er zum *nächsten* Raid - also zu dem, der zuletzt
dazukam. Der 25er war damit nicht mehr zu bearbeiten, obwohl er offen
stand, und nichts an der Seite sagte, welchen der beiden man gerade
vor sich hatte.

Der Bot nimmt den Raid längst als `?raid=<id>` entgegen (siehe
`docs/raid-schedule-bridge.md`); es fehlte nur die Wahl. Drei Regeln
dazu:

* **Die Kennungen kommen aus dem Termin**, den `RaidScheduleSync`
  ohnehin im Takt holt (`raid_choices()` in `core/raid_schedule.py`) -
  kein zweiter Abruf und keine zweite Aufzählung laufender Raids.
* **Ein Raid wird gewählt, nicht geraten.** Solange die Companion
  keine Kennung kennt (frisch gestartet, ältere Bot-Fassung), wird
  keine geschickt, und es bleibt beim bisherigen Verhalten.
* **Was geladen ist, steht im Kopf** - auch bei einem einzigen Raid.
  Die Frage "welchen bearbeite ich hier gerade" darf nicht davon
  abhängen, ob die Auswahl sichtbar ist.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.character_links import (
    ANY_CLASS,
    CLASS_LABELS,
    Overview,
    SignupRow,
)
from core.character_links_client import CharacterLinksClient
from core.raid_schedule import raid_choices
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.wow_colors import class_color
from gui.widgets.card import Card
from gui.widgets.empty_state import EmptyState
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.select import Select
from gui.widgets.wrapped_label import enable_wrap


#
# Reihenfolge des Klassen-Auswahlkastens. Der Platzhalter steht oben,
# weil er der häufigste Fall ist: die meisten der nachzutragenden
# Spieler haben genau einen Charakter.
#

def _class_items():

    return [(("Jede Klasse"), ANY_CLASS)] + [
        (label, token)
        for token, label in sorted(CLASS_LABELS.items(), key=lambda item: item[1])
    ]


class _SignupRow(QWidget):
    """
    Eine Zeile: wer, welche Klasse, welcher Charakter - und ein
    Eingabefeld, wenn noch keiner feststeht.
    """

    submitted = Signal(str, str, str)

    cleared = Signal(str)

    def __init__(self, row: SignupRow, parent=None):

        super().__init__(parent)

        self.row = row

        root = QHBoxLayout(self)

        root.setContentsMargins(0, tokens.SPACE[1], 0, tokens.SPACE[1])

        root.setSpacing(tokens.SPACE[2])

        #
        # Links: der Discord-Name. Er ist der einzige Anhaltspunkt,
        # wer gemeint ist, und bleibt deshalb auch dann stehen, wenn
        # rechts längst ein Charakter zugeordnet ist.
        #

        left = QVBoxLayout()

        left.setContentsMargins(0, 0, 0, 0)

        left.setSpacing(1)

        name = QLabel(row.discord_name)

        name.setFont(font("body"))

        restyle(name, f"color:{tokens.WHITE};background:transparent;")

        left.addWidget(name)

        meta = QLabel(f"{row.class_name} · {row.role}")

        meta.setFont(font("caption"))

        restyle(
            meta,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        left.addWidget(meta)

        root.addLayout(left, 3)

        #
        # Mitte: der aufgelöste Charakter, in Klassenfarbe. Fehlt er,
        # steht hier kein leeres Feld, sondern der Grund.
        #

        status = QVBoxLayout()

        status.setContentsMargins(0, 0, 0, 0)

        status.setSpacing(1)

        character = QLabel(row.character if row.resolved else "kein Charakter")

        character.setFont(font("body"))

        restyle(
            character,
            "color:%s;background:transparent;" % (
                class_color(row.class_token) if row.resolved
                else tokens.STATE["warn"]
            ),
        )

        status.addWidget(character)

        origin = QLabel(row.source_label)

        origin.setFont(font("caption"))

        restyle(
            origin,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        status.addWidget(origin)

        root.addLayout(status, 3)

        #
        # Rechts: die Bearbeitung. Für eine offene Zeile ein
        # Eingabefeld, für eine geklärte nur dann etwas zu tun, wenn
        # der Eintrag von Hand kam - eine Meldung des Spielers lässt
        # sich hier nicht löschen, sie gehört ihm.
        #

        edit = QHBoxLayout()

        edit.setContentsMargins(0, 0, 0, 0)

        edit.setSpacing(tokens.SPACE[1])

        self.input = QLineEdit()

        self.input.setPlaceholderText("Charaktername, crossrealm Name-Realm")

        self.input.setFixedHeight(36)

        self.input.setFont(font("body"))

        if row.resolved:
            self.input.setText(row.character)

        edit.addWidget(self.input, 2)

        self.classes = Select()

        self.classes.set_items(_class_items(), current=_default_class(row))

        edit.addWidget(self.classes, 1)

        save = HeroButton("Speichern", primary=not row.resolved)

        save.clicked.connect(self._emit)

        edit.addWidget(save)

        self.input.returnPressed.connect(self._emit)

        clear = HeroButton("Zurücksetzen", primary=False)

        clear.setVisible(row.source == "raidlead")

        clear.clicked.connect(lambda: self.cleared.emit(self.row.discord_id))

        edit.addWidget(clear)

        root.addLayout(edit, 5)

    def _emit(self):

        self.submitted.emit(
            self.row.discord_id,
            self.input.text().strip(),
            self.classes.value() or ANY_CLASS,
        )


def _default_class(row: SignupRow) -> str:
    """
    Womit der Auswahlkasten einer Zeile startet.

    Die Klasse der Anmeldung, wenn sie bekannt ist - das ist die
    genauere und damit bessere Zuordnung. "UNKNOWN" ist keine Klasse,
    sondern eine Anmeldung ohne gesetzte Klasse; dort bleibt nur der
    Platzhalter.
    """

    token = (row.class_token or "").upper()

    return token if token in CLASS_LABELS else ANY_CLASS


class CharacterLinksPage(Page):

    #
    # Die Abrufe laufen in einem eigenen Thread, zeichnen darf aber nur
    # der Hauptthread. Ein Qt-Signal ist der Weg dorthin: es wird an
    # den Empfänger-Threads Ereignisschleife zugestellt, und die
    # gehört dem Fenster. Dieselbe Überlegung wie bei
    # `_AutoSyncStarter` im CompanionManager.
    #

    loaded = Signal()

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            eyebrow="RAIDLEITUNG",
            title="Wer lässt sich einladen?",
            parent=parent,
        )

        self.client = CharacterLinksClient()

        self._thread: threading.Thread | None = None

        #
        # Der zuletzt geholte Stand. Gezeichnet wird ausschliesslich
        # daraus, damit `refresh()` nie ins Netz greift.
        #

        self._overview = Overview()

        self._loading = False

        self._notice = ""

        #
        # Welcher der laufenden Raids gemeint ist. `None` heißt "noch
        # keiner gewählt" und wird als *keine* Angabe geschickt - der
        # Bot antwortet dann zum nächsten Raid, wie bisher.
        #

        self._raid_id: int | None = None

        #
        # Die zuletzt gezeichnete Auswahl. `refresh()` vergleicht
        # dagegen und zeichnet nur bei einer Änderung neu: die Liste
        # trägt Eingabefelder, und ein Neubau unter den Fingern
        # verwirft, was gerade getippt wurde.
        #

        self._choice_key: tuple = ()

        self.loaded.connect(self._on_loaded)

        #
        # Die Raidwahl steht **vor** dem Neu-laden-Knopf: sie
        # bestimmt, was geladen wird.
        #

        self.raid_label = QLabel("Raid")

        self.raid_label.setFont(font("caption"))

        restyle(
            self.raid_label,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        self.header.addAction(self.raid_label)

        self.raids = Select()

        self.raids.setMinimumWidth(240)

        self.raids.currentIndexChanged.connect(self._on_raid_changed)

        self.header.addAction(self.raids)

        self._set_raid_picker_visible(False)

        self.reload = HeroButton("Neu laden", primary=False)

        self.reload.clicked.connect(self.load)

        self.header.addAction(self.reload)

        #
        # Welcher Raid hier gerade gezeigt wird. Eigene Zeile und
        # nicht Teil der Zusammenfassung: sie steht auch dann da, wenn
        # nur ein Raid läuft und der Auswahlkasten deshalb fehlt -
        # "welchen bearbeite ich" ist die erste Frage, sobald es
        # überhaupt mehrere geben kann.
        #

        self.raid_line = QLabel("")

        self.raid_line.setFont(font("caption"))

        enable_wrap(self.raid_line)

        restyle(
            self.raid_line,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.addWidget(self.raid_line)

        self.summary = QLabel("")

        self.summary.setFont(font("body"))

        enable_wrap(self.summary)

        restyle(
            self.summary,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        self.addWidget(self.summary)

        self.status = QLabel("")

        self.status.setFont(font("caption"))

        enable_wrap(self.status)

        self.addWidget(self.status)

        #
        # Der Listenbereich. Eigener Scrollbereich statt des
        # Seiten-Wrappers: 25 Zeilen mit Eingabefeldern sollen unter
        # einem stehenden Kopf laufen, nicht mit ihm zusammen.
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

        self.addWidget(self.scroll, 1)

        self.render()

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def on_enter(self):
        """
        Beim Betreten holen - die Anmeldung ändert sich zwischen zwei
        Besuchen dieser Seite ständig, und ein veralteter Stand ist
        hier schlimmer als eine kurze Wartezeit: er behauptet
        geschlossene Lücken.

        Der Termin wird dabei **fällig gestellt**, nicht abgerufen:
        `invalidate()` setzt nur den Merker zurück, geholt wird im
        Sync-Takt (also im nächsten Durchlauf, ein paar Sekunden
        später). Ein Abruf von hier aus wäre ein zweiter Leser
        desselben Endpunkts neben `RaidScheduleSync` - und ein
        gerade im Discord neu erstellter Raid soll in der Auswahl
        auftauchen, ohne dass man fünf Minuten wartet.
        """

        sync = getattr(self.manager, "raid_schedule_sync", None)

        if sync is not None:
            sync.invalidate()

        self._sync_raids()

        self.load()

    def refresh(self):

        #
        # Nur zeichnen. Kein `full_refresh()`, kein Netzabruf - siehe
        # `tests/test_update_visibility.py`, das genau das prüft.
        #
        # Und nur dann, wenn sich an der Auswahl etwas geändert hat.
        # `refresh()` hängt an `state_changed`, das im Sync-Takt kommt;
        # ein unbedingter Neubau der Liste verwürfe einen halb
        # getippten Charakternamen. Der Inhalt selbst wird ohnehin
        # nicht hier, sondern nach jedem Abruf gezeichnet.
        #

        if self._sync_raids():
            self.render()

    # --------------------------------------------------
    # Raidwahl
    # --------------------------------------------------

    def _choices(self):
        """
        Die laufenden Raids, so wie der Termin sie kennt.

        Über `getattr`, weil `refresh()` auch aus Tests und aus dem
        Aufbau der Seite heraus läuft, wo der Manager ein einfacher
        Platzhalter sein kann - dieselbe Vorsicht wie in
        `OverviewPage._schedule()`.
        """

        sync = getattr(self.manager, "raid_schedule_sync", None)

        return raid_choices(getattr(sync, "schedule", None))

    def _sync_raids(self) -> bool:
        """
        Den Auswahlkasten nachziehen. Gibt zurück, ob sich etwas
        geändert hat.

        **Die Auswahl erscheint erst ab zwei Raids.** Bei einem
        einzigen gäbe es nichts zu wählen, und ein Kasten mit genau
        einem Eintrag sieht aus wie eine Entscheidung, die man treffen
        müsste. Welcher Raid geladen ist, steht trotzdem im Kopf -
        dafür sorgt `render()`, unabhängig von diesem Kasten.
        """

        choices = self._choices()

        key = tuple(
            (choice.raid_id, choice.label)
            for choice in choices
        )

        changed = key != self._choice_key

        self._choice_key = key

        if len(choices) < 2:

            self._set_raid_picker_visible(False)

            return changed

        #
        # Ein gewählter Raid, den es nicht mehr gibt (im Discord
        # gelöscht), fällt auf "keiner gewählt" zurück statt eine
        # Kennung zu behalten, auf die der Bot mit "keine Anmeldung"
        # antwortet.
        #

        known = {choice.raid_id for choice in choices}

        if self._raid_id is not None and self._raid_id not in known:
            self._raid_id = None

        self.raids.blockSignals(True)

        self.raids.set_items(
            [(choice.label, choice.raid_id) for choice in choices],
            current=self._raid_id if self._raid_id is not None else choices[0].raid_id,
        )

        self.raids.blockSignals(False)

        self._set_raid_picker_visible(True)

        return changed

    def _set_raid_picker_visible(self, visible: bool):

        self.raid_label.setVisible(visible)

        self.raids.setVisible(visible)

    def _on_raid_changed(self, index: int):

        raid_id = self.raids.itemData(index)

        if raid_id is None or raid_id == self._raid_id:
            return

        self._raid_id = int(raid_id)

        #
        # Ein Wechsel ist eine Frage an den Bot, keine Filterung des
        # bereits geholten Standes: die Anmeldungen des anderen Raids
        # liegen hier gar nicht vor.
        #

        self.load()

    # --------------------------------------------------
    # Abruf
    # --------------------------------------------------

    def load(self):

        if self._thread is not None and self._thread.is_alive():
            return

        self._loading = True

        self._notice = ""

        self.reload.setEnabled(False)

        self.render()

        #
        # Die Kennung wird **hier** abgelesen und mitgegeben, nicht im
        # Thread: wer während des Abrufs umschaltet, bekäme sonst die
        # Antwort zum neuen Raid unter dem alten Kopf.
        #

        self._thread = threading.Thread(
            target=self._load_worker,
            args=(self._raid_id,),
            daemon=True,
            name="CharacterLinksFetch",
        )

        self._thread.start()

    def _load_worker(self, raid_id):

        overview = self.client.fetch(raid_id)

        self._overview = overview

        self._loading = False

        #
        # Zurück auf den Hauptthread: `render()` baut Widgets, und die
        # dürfen nur dort entstehen. `QMetaObject` wäre der
        # ausführliche Weg; ein Signal ist der im Haus übliche.
        #

        self.loaded.emit()

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def _submit(self, discord_id: str, character: str, class_token: str):

        if self._thread is not None and self._thread.is_alive():
            return

        self.reload.setEnabled(False)

        self._thread = threading.Thread(
            target=self._write_worker,
            args=(discord_id, character, class_token, False, self._raid_id),
            daemon=True,
            name="CharacterLinkWrite",
        )

        self._thread.start()

    def _clear(self, discord_id: str):

        if self._thread is not None and self._thread.is_alive():
            return

        self.reload.setEnabled(False)

        self._thread = threading.Thread(
            target=self._write_worker,
            args=(discord_id, "", "", True, self._raid_id),
            daemon=True,
            name="CharacterLinkWrite",
        )

        self._thread.start()

    def _write_worker(self, discord_id, character, class_token, remove, raid_id):
        """
        Schreiben und danach neu holen.

        **Der Handeintrag selbst kennt keinen Raid** - er gilt für den
        Account, nicht für eine Anmeldung (siehe
        `docs/character-links-and-admin-bridge.md`). Nur das erneute
        Holen braucht den Raid, damit die Liste danach dieselbe ist
        wie vorher und nicht die des nächsten Raids.
        """


        if remove:
            result = self.client.remove_link(discord_id)
        else:
            result = self.client.set_link(discord_id, character, class_token)

        if not result.ok:

            self._notice = result.reason

            self.loaded.emit()

            return

        #
        # Nach dem Schreiben den ganzen Stand neu holen statt die eine
        # Zeile lokal zu ändern: der Bot entscheidet, welcher Name
        # gewinnt, wenn Meldung und Handeintrag sich widersprechen.
        # Eine lokal nachgezogene Zeile könnte etwas anderes anzeigen,
        # als der Export gleich verwendet.
        #

        self._notice = (
            f"Gespeichert: {result.character}" if result.character
            else "Zuordnung entfernt."
        )

        self._overview = self.client.fetch(raid_id)

        self.loaded.emit()

    # --------------------------------------------------
    # Zeichnen
    # --------------------------------------------------

    def _on_loaded(self):

        self._loading = False

        self.reload.setEnabled(True)

        #
        # Ohne eigene Wahl gilt, was der Bot geantwortet hat. Erst
        # damit zeigt der Auswahlkasten den Raid, der wirklich vor
        # einem liegt - sonst stünde er auf dem ersten Eintrag,
        # während die Liste zu einem anderen gehört.
        #

        if self._raid_id is None and self._overview.raid_id is not None:
            self._raid_id = self._overview.raid_id

        self._sync_raids()

        self.render()

    def render(self):

        from core.character_links import summary_text

        overview = self._overview

        self._apply_raid_line()

        while self.list_layout.count():

            item = self.list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if self._loading:

            self.summary.setText("Stand wird beim Bot abgefragt …")

            self._set_status("")

            return

        if overview.forbidden:

            self.summary.setText("")

            self._set_status("")

            self.list_layout.addWidget(EmptyState(
                eyebrow="NICHT FREIGEGEBEN",
                title="Dafür fehlt die Raidlead-Rolle",
                explanation=(
                    "Diese Seite verbindet Discord-Konten mit "
                    "WoW-Charakteren, damit der Kalender-Invite im Spiel "
                    "jeden erreicht. Sie nennt dafür die Charakternamen "
                    "des ganzen Rosters und ist deshalb der Raidleitung "
                    "vorbehalten - genau wie die Aufstellung selbst."
                ),
            ))

            self.list_layout.addStretch(1)

            return

        if overview.reason:

            self.summary.setText("")

            self._set_status(overview.reason, tokens.STATE["error"])

            self.list_layout.addStretch(1)

            return

        self.summary.setText(summary_text(overview))

        self._set_status(self._notice)

        if not overview.signups:

            self.list_layout.addWidget(EmptyState(
                eyebrow="KEINE ANMELDUNG",
                title=(
                    "Zurzeit läuft keine Anmeldung"
                    if not overview.has_raid
                    else "Noch hat sich niemand gemeldet"
                ),
                explanation=(
                    "Sobald in Discord ein Raid steht und sich Leute "
                    "eintragen, steht hier für jeden, mit welchem "
                    "Charakter er eingeladen wird - und wer noch keinen "
                    "hat."
                ),
            ))

            self.list_layout.addStretch(1)

            return

        #
        # `Card` bringt sein Layout selbst mit (`card.root`, mit den
        # Innenabstaenden der eingestellten Dichte). Ein zweites
        # daraufzusetzen laesst Qt kommentarlos ins Leere laufen - die
        # Zeilen waeren nie erschienen.
        #

        card = Card()

        inner = card.root

        inner.setSpacing(0)

        last_resolved = None

        for row in overview.signups:

            #
            # Eine Überschrift je Block, nicht je Zeile: die offenen
            # zuerst, darunter die geklärten als Beleg. Der Wechsel
            # muss sichtbar sein, sonst liest sich die Liste als eine.
            #

            if row.resolved != last_resolved:

                if last_resolved is not None:
                    inner.addSpacing(tokens.SPACE[3])

                inner.addWidget(eyebrow_label(
                    "OFFEN" if not row.resolved else "ZUGEORDNET",
                    tokens.STATE["warn"] if not row.resolved
                    else tokens.TEXT["faint"],
                ))

                last_resolved = row.resolved

            widget = _SignupRow(row)

            widget.submitted.connect(self._submit)

            widget.cleared.connect(self._clear)

            inner.addWidget(widget)

        self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

    def _apply_raid_line(self):
        """
        Die Zeile "welcher Raid liegt hier".

        Benannt wird der Raid, den der **Bot** geantwortet hat, nicht
        der eigene Merker: die beiden fallen genau in dem Moment
        auseinander, in dem etwas schiefging (Raid gelöscht, ältere
        Bot-Fassung, Abruf noch unterwegs), und dann ist die Antwort
        die richtige Auskunft.

        Kennt die Companion den Termin nicht, bleibt die Zeile leer
        statt eine Kennung wie "Raid 7" anzuzeigen - eine Zahl, die im
        Discord nirgends steht, benennt nichts.
        """

        if self._loading:

            self.raid_line.setVisible(False)

            return

        raid_id = self._overview.raid_id

        label = ""

        for choice in self._choices():

            if choice.raid_id == raid_id:

                label = choice.label

                break

        self.raid_line.setText(f"Anmeldung: {label}" if label else "")

        self.raid_line.setVisible(bool(label))

    def _set_status(self, text: str, color: str | None = None):

        self.status.setText(text or "")

        self.status.setVisible(bool(text))

        restyle(
            self.status,
            "color:%s;background:transparent;" % (
                color or tokens.TEXT["secondary"]
            ),
        )
