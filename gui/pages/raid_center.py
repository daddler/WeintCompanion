"""
Das Raid Center - ein Bereich, vier Perspektiven.

**Warum es diese Seite gibt.** Bis 3.6.0 hatte die Gruppe RAID vier
Einträge: Übersicht, WeintTV, Academy, Archiv. Die letzten drei teilten
sich unsichtbar eine Datenquelle, einen Snapshot und eine
Archivauswahl - und der Nutzer musste selbst wissen, welchen er wann
öffnet. Um von einem analysierten Pull zur passenden Lektion zu kommen,
ging der Weg über die Seitenleiste, und dort begann die Arbeit von
vorn: Charakter wählen, Pull wiederfinden, Lektion suchen. Gemeldet
wurde das als *"viele wissen nicht, wo man was findet"* - und für diese
drei Seiten war das wörtlich richtig.

Seit 4.0 ist ein **Raid/Pull der Gegenstand** und Live, Analyse, Lernen
und Quelle sind vier Blicke darauf:

    Live      Was gerade passiert.
    Analyse   Die Tiefenauswertung dieses Pulls.
    Lernen    Was du als Nächstes verbessern solltest.
    Quelle    Welchen vergangenen Kampf willst du ansehen?

Was diese Seite dafür tut, ist genau vier Dinge - und alles andere
bewusst nicht:

1. **Den Kopfblock halten.** `RaidContextHeader` nennt Boss, Pull,
   Ausgang, Prozent, Dauer, Datum, Uhrzeit, Charakter und Quelle. Er
   steht ausserhalb des Stapels und wechselt deshalb beim
   Perspektivwechsel nicht - das ist die Bedingung dafür, dass sich ein
   Wechsel nicht wie ein Seitenwechsel anfühlt.
2. **Einen Snapshot verteilen.** `snapshotChanged` kommt hier an und
   geht an den Kopf und an die *sichtbare* Ansicht. Eine Ansicht, die
   sich ihren Stand selbst holt, zeigt in einer Wiedergabe nachweislich
   eine andere Sekunde als die daneben.
3. **Die Tiefenverweise auflösen.** `open(RaidLink)` ist der eine
   Eingang von aussen: welcher Pull, welche Perspektive, welcher
   Charakter, welche Sekunde. Die Übersicht, die Analyse und die
   Lernansicht benutzen ihn alle drei.
4. **Die Ansichten auf Abruf bauen.** Dieselbe Überlegung wie bei
   `MainWindow._ensure_page()`: Live und Lernen legen ihre Listen- und
   Tabellenzeilen im Voraus an, damit das spätere Zeichnen im
   Sekundentakt flackerfrei bleibt. Das ist richtig - es gehört nur
   nicht in den Moment, in dem jemand zum ersten Mal auf *Raid Center*
   klickt.

**Was hier NICHT liegt**, und das ist die wichtigste Zeile dieser
Datei: kein Archivzustand, kein Wiedergabezustand, keine Fightauswahl.
Das alles bleibt auf `RaidDataService` (`ArchiveState`, `ReplayState`).
Diese Seite liest und ruft; sie hält über den Kampf selbst nichts. Ein
zweiter Archiv- oder Wiedergabezustand daneben wären zwei Wahrheiten
über denselben Pull - genau der Fehler, den die Architektur seit 2.8.0
vermeidet.

`refresh()` darf nur zeichnen, niemals holen (siehe
`docs/architecture/navigation.md`).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.raid_context import context_from, same_pull

from gui.dialogs.guide_dialog import GuideDialog
from gui.navigation import (
    RAID_VIEW_ANALYSIS,
    RAID_VIEW_HINTS,
    RAID_VIEW_LABELS,
    RAID_VIEW_LEARN,
    RAID_VIEW_LIVE,
    RAID_VIEW_SOURCE,
    RAID_VIEWS,
    RaidLink,
)
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.raid.context_header import RaidContextHeader
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.tv.loading_card import LoadingCard
from gui.widgets.tv.replay_bar import ReplayBar
from gui.widgets.wrapped_label import enable_wrap


#
# Welche Module eine Ansicht braucht. Die beiden Schalter aus
# *Einstellungen · Module* bleiben bestehen - sie betreffen jetzt aber
# eine Perspektive und keinen ganzen Navigationspunkt, und deshalb
# steht die Zuordnung hier und nicht in den Ansichten: eine
# abgeschaltete Academy soll das Raid Center nicht mitnehmen.
#

VIEW_MODULES = {
    RAID_VIEW_LIVE: ("weinttv_enabled", "WeintTV"),
    RAID_VIEW_ANALYSIS: ("weinttv_enabled", "WeintTV"),
    RAID_VIEW_LEARN: ("academy_enabled", "WeintAcademy"),
}


class RaidCenterPage(QWidget):

    #
    # Sprung in einen anderen Hauptbereich - duck-getypt vom
    # MainWindow verbunden, wie on_enter()/on_leave().
    #

    pageRequested = Signal(int)

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        self._attached = False

        self._view = RAID_VIEW_LIVE

        self._views: dict[str, QWidget] = {}

        #
        # Was im Stapel liegt: der Scrollbereich um eine Ansicht, nicht
        # die Ansicht selbst. Gemerkt und nicht über `parentWidget()`
        # erfragt - ein QScrollArea schiebt ein eigenes Ansichtsfenster
        # dazwischen, der Elternteil einer gescrollten Ansicht ist also
        # nie der Scrollbereich.
        #

        self._containers: dict[str, QWidget] = {}

        self._holders: dict[str, QWidget] = {}

        self._layout_state = None

        #
        # Vorgemerkter Sprung in die Wiedergabe. Er kann erst
        # ausgeführt werden, wenn die Zeitleiste geladen ist - bis
        # dahin wartet er hier.
        #

        self._pending_seek = None

        #
        # Der Pull, den die Seite beim letzten Zeichnen vor sich hatte.
        # Er entscheidet, ob ein `archiveChanged` einen *neuen* Pull
        # meldet (dann wird auf die Analyse umgeschaltet) oder nur den
        # Fortschritt desselben - siehe `_on_archive_changed()`.
        #

        self._pull = None

        root = QVBoxLayout(self)

        root.setContentsMargins(
            tokens.SPACE[5],
            tokens.SPACE[4],
            tokens.SPACE[5],
            tokens.SPACE[4],
        )

        root.setSpacing(12)

        # --------------------------------------------------
        # Der Kopfblock
        # --------------------------------------------------

        self.header = RaidContextHeader(manager)

        self.header.sourceRequested.connect(
            lambda: self.show_view(RAID_VIEW_SOURCE)
        )

        self.header.characterChanged.connect(self._on_character_changed)

        root.addWidget(self.header)

        # --------------------------------------------------
        # Die Umschaltleiste
        # --------------------------------------------------

        root.addLayout(self._build_switch())

        # --------------------------------------------------
        # Wiedergabe und Warten
        # --------------------------------------------------
        #
        # Beide über dem Stapel und nicht in einer Ansicht: die
        # Wiedergabe gilt für alle vier (man will beim Zusehen steuern
        # können, ohne die Perspektive zu wechseln), und während ein
        # Pull geholt wird, sind alle vier leer. Beide Widgets
        # entscheiden ihre Sichtbarkeit selbst.
        #

        root.addWidget(ReplayBar(self.service))

        root.addWidget(LoadingCard(self.service))

        # --------------------------------------------------
        # Hinweis bei abgeschaltetem Modul
        # --------------------------------------------------

        self.disabled_notice = self._build_disabled_notice()

        root.addWidget(self.disabled_notice)

        # --------------------------------------------------
        # Die vier Ansichten
        # --------------------------------------------------

        self.stack = QStackedWidget()

        root.addWidget(self.stack, 1)

        for key, _label, _hint in RAID_VIEWS:

            holder = QWidget()

            self._holders[key] = holder

            self.stack.addWidget(holder)

        self._switch.setValue(RAID_VIEW_LIVE)

        self.show_view(RAID_VIEW_LIVE)

        # --------------------------------------------------
        # Signale
        # --------------------------------------------------

        self.service.snapshotChanged.connect(self._on_snapshot)

        self.service.archiveChanged.connect(self._on_archive_changed)

        self.service.replayChanged.connect(self._on_replay_changed)

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build_switch(self) -> QHBoxLayout:
        """
        Die vier Perspektiven, ein Erklärsatz, und die zwei Werkzeuge,
        die nirgends sonst hingehören.

        Der Satz steht **neben** der Leiste und nicht darunter: drei
        der vier Ansichten leben von senkrechtem Platz, und eine eigene
        Zeile für achtzehn Pixel Text wäre dort eine Ranglistenzeile
        weniger. Bei schmalem Fenster bricht er um, statt abgeschnitten
        zu werden.
        """

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        self._switch = SegmentedControl([
            (RAID_VIEW_LABELS[key], key)
            for key, _label, _hint in RAID_VIEWS
        ])

        self._switch.valueChanged.connect(self.show_view)

        row.addWidget(self._switch)

        self.hint = enable_wrap(QLabel(""))

        self.hint.setFont(font("small"))

        restyle(
            self.hint,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        row.addWidget(self.hint, 1)

        #
        # Der Wegweiser. Er steht hier, weil er die Frage "wo finde ich
        # was" beantwortet und die deshalb aus jeder Perspektive
        # erreichbar sein muss.
        #

        self.guide_button = QPushButton("Was ist das hier?")

        self.guide_button.setObjectName("secondary")

        self.guide_button.setCursor(Qt.PointingHandCursor)

        self.guide_button.clicked.connect(self._open_guide)

        row.addWidget(self.guide_button)

        #
        # Das Overlay (§6.6): ein sehr kleines, immer sichtbares
        # Fenster mit denselben Werten neben dem Spiel. Der Knopf sitzt
        # hier und nicht in den Einstellungen, weil er genau in dem
        # Moment gebraucht wird, in dem das Raid Center ohnehin offen
        # ist.
        #

        self.overlay_button = QPushButton("Overlay")

        self.overlay_button.setObjectName("secondary")

        self.overlay_button.setCursor(Qt.PointingHandCursor)

        self.overlay_button.clicked.connect(self._toggle_overlay)

        row.addWidget(self.overlay_button)

        self._overlay_window = None

        return row

    def _build_disabled_notice(self) -> Card:

        card = Card()

        self.disabled_title = QLabel("")

        self.disabled_title.setFont(font("card"))

        restyle(
            self.disabled_title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        card.addWidget(self.disabled_title)

        text = enable_wrap(QLabel(
            "Das Modul lässt sich unter Einstellungen · Module wieder "
            "einschalten. Die übrigen Ansichten dieses Bereichs "
            "bleiben davon unberührt."
        ))

        text.setFont(font("small"))

        restyle(
            text,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        card.addWidget(text)

        card.setVisible(False)

        return card

    # --------------------------------------------------
    # Ansichten auf Abruf
    # --------------------------------------------------

    def _ensure_view(self, key: str):
        """
        Die Ansicht zu `key` - gebaut, falls sie noch ein Platzhalter
        ist.

        Dieselbe Überlegung wie bei `MainWindow._ensure_page()`, nur
        eine Ebene tiefer: alle vier im Voraus zu bauen kostete rund
        zwei Sekunden in dem Moment, in dem jemand das Raid Center zum
        ersten Mal öffnet - für drei Ansichten, die er in diesem Moment
        nicht sieht.
        """

        view = self._views.get(key)

        if view is not None:
            return view

        holder = self._holders.get(key)

        if holder is None:
            return None

        view = _create_view(key, self.manager)

        if view is None:
            return None

        self._views[key] = view

        self._wire(key, view)

        #
        # Jede Ansicht rollt für sich. Ein Scrollbereich um die *Seite*
        # würde den Kopfblock beim ersten Rollen mitnehmen - und damit
        # genau das aufgeben, worum es hier geht.
        #
        # Auch die Quellenansicht, obwohl ihre Liste in zwei eigenen
        # Spalten rollt: sie ist so bemessen, dass sie bei 1280 x 720
        # ohne den äusseren Balken auskommt, und er ist nur das Netz für
        # die Mindestgrösse (960 x 640). Ein Rad in einem Rad wäre er
        # erst, wenn er regelmässig erschiene - abgeschnittene Knöpfe
        # wären er in jedem Fall.
        #

        container = _wrap(view)

        self._containers[key] = container

        index = self.stack.indexOf(holder)

        self.stack.insertWidget(index, container)

        self.stack.removeWidget(holder)

        holder.deleteLater()

        self._holders.pop(key, None)

        if self._layout_state is not None and hasattr(view, "on_layout_changed"):
            view.on_layout_changed(self._layout_state)

        return view

    def _wire(self, key: str, view):
        """
        Die Tiefenverweise einer Ansicht anschliessen - duck-getypt,
        genau wie `MainWindow._ensure_page()` es mit den Seiten macht.
        Eine neue Ansicht, die springen können soll, braucht nur das
        Signal und keine Änderung hier.
        """

        if hasattr(view, "playerRequested"):

            view.playerRequested.connect(self.show_player)

        if hasattr(view, "viewRequested"):

            view.viewRequested.connect(self.show_view)

        if hasattr(view, "momentRequested"):

            view.momentRequested.connect(self.show_moment)

    # --------------------------------------------------
    # Perspektive wechseln
    # --------------------------------------------------

    def show_view(self, key: str):
        """
        Die Perspektive wechseln - **ohne** den Kontext anzutasten.

        Das ist die eine Bewegung, um die es in diesem Bereich geht:
        derselbe Pull, anderer Blick. Weder Archivauswahl noch
        Wiedergabe noch Charakter werden hier berührt.
        """

        key = str(key)

        if key not in RAID_VIEW_LABELS:
            return

        view = self._ensure_view(key)

        if view is None:
            return

        self._view = key

        self._switch.blockSignals(True)

        self._switch.setValue(key)

        self._switch.blockSignals(False)

        self.stack.setCurrentWidget(self._containers[key])

        self.hint.setText(RAID_VIEW_HINTS.get(key, ""))

        self.overlay_button.setVisible(key == RAID_VIEW_LIVE)

        self._apply_module(key)

        if hasattr(view, "on_enter"):
            view.on_enter()

        #
        # Sofort zeichnen. Ohne diesen Aufruf zeigte die neue
        # Perspektive bis zum nächsten Poll den Stand von vorher - und
        # bei einem archivierten Pull käme gar kein Poll mehr.
        #

        self._draw(self.service.current())

    def show_player(self, name: str):
        """
        Einen Charakter zum Kontextcharakter machen und die Lernansicht
        zeigen - der Weg *Analyse → Lernen*.

        Die Reihenfolge ist entscheidend: erst der Charakter, dann die
        Ansicht. `show_view()` zeichnet aus dem aktuellen Snapshot neu -
        andersherum stünde für einen Moment der falsche Charakter da.
        """

        if not name:
            return

        self.header.show_player(name)

        self._invalidate_learn()

        self.show_view(RAID_VIEW_LEARN)

    def show_moment(self, seconds: float):
        """
        Eine Sekunde des Pulls ansehen - der Weg *Lernen → Wiedergabe*.

        Läuft noch keine Wiedergabe, wird sie zuerst gestartet. Der
        Sprung selbst passiert dann erst, wenn die Zeitleiste geladen
        ist - deshalb der zweite Aufruf über `replayChanged` statt
        sofort.
        """

        from core.raid_data_service import MODE_REPLAY

        if self.service.archive_state().mode != MODE_REPLAY:

            self._pending_seek = float(seconds)

            self.service.start_replay()

        else:

            self.service.seek_replay(float(seconds))

            self.service.set_replay_playing(False)

        #
        # Angesehen wird der Moment in der Live-Ansicht: sie ist die,
        # die den Kampf *zeigt*. Die Wiedergabeleiste bleibt oben
        # stehen, also lässt sich von dort aus weiterspulen, ohne die
        # Perspektive erneut zu wechseln.
        #

        self.show_view(RAID_VIEW_LIVE)

    def open(self, link: RaidLink):
        """
        Ein Tiefenverweis - der eine Eingang von aussen.

        Die Reihenfolge ist die Aussage: erst der Pull, dann der
        Charakter, dann die Perspektive, dann der Sprung in die
        Sekunde. Andersherum zeigte die Ansicht kurz den alten Pull mit
        dem neuen Charakter.

        Was der Verweis leer lässt, bleibt unberührt - ein
        `RaidLink(view=…)` heisst "derselbe Kampf, anderer Blick".
        """

        if link is None:
            return

        if link.has_pull:

            state = self.service.archive_state()

            #
            # Nur laden, wenn nicht schon geladen: ein archivierter
            # Pull kostet den Bot Minuten, und ein erneuter Abruf
            # desselben wäre reine Wartezeit. Die Wiedergabe zählt
            # dabei als geladen - sie spielt genau diesen Pull.
            #

            already = (
                state.selected_report == link.report_code
                and state.selected_fight == link.fight_id
            )

            if not already:

                self.service.enter_archive_mode()

                self.service.select_archive_fight(
                    link.report_code,
                    int(link.fight_id),
                )

        if link.player:

            self.header.show_player(link.player)

            self._invalidate_learn()

        if link.seconds is not None:

            self.show_moment(float(link.seconds))

            return

        self.show_view(link.view or RAID_VIEW_ANALYSIS)

    # --------------------------------------------------
    # Module
    # --------------------------------------------------

    def _apply_module(self, key: str):
        """
        Ein abgeschaltetes Modul betrifft **eine** Perspektive.

        Bis 3.6.0 leerte derselbe Schalter einen ganzen
        Navigationspunkt. Jetzt bleibt der Bereich nutzbar: wer die
        Academy abgeschaltet hat, sieht Live, Analyse und Quelle
        unverändert - und auf *Lernen* den Satz, wo sie wieder
        anzuschalten ist.
        """

        setting, label = VIEW_MODULES.get(key, ("", ""))

        enabled = (
            True
            if not setting
            else bool(self.manager.config.data.get(setting, True))
        )

        self.disabled_title.setText(
            f"{label} ist deaktiviert" if label else ""
        )

        self.disabled_notice.setVisible(not enabled)

        self.stack.setVisible(enabled)

    def _enabled_for(self, key: str) -> bool:

        setting, _label = VIEW_MODULES.get(key, ("", ""))

        if not setting:
            return True

        return bool(self.manager.config.data.get(setting, True))

    # --------------------------------------------------
    # Lebenszyklus (von MainWindow.change_page aufgerufen)
    # --------------------------------------------------

    def on_enter(self):

        if not self._attached:

            self.service.attach()

            self._attached = True

        self.show_view(self._view)

    def on_leave(self):

        if not self._attached:
            return

        self.service.detach()

        self._attached = False

    def on_layout_changed(self, state):

        self._layout_state = state

        self.header.on_layout_changed(state)

        for view in self._views.values():

            if hasattr(view, "on_layout_changed"):
                view.on_layout_changed(state)

    def refresh(self):
        """
        Nur zeichnen. Kein Abruf, kein Netz - siehe
        `docs/architecture/navigation.md`.
        """

        self.header.refresh()

        self._draw(self.service.current())

    # --------------------------------------------------
    # Overlay
    # --------------------------------------------------
    #
    # Bewusst nicht an on_leave() gekoppelt: der ganze Zweck des
    # Overlays ist, weiter sichtbar zu bleiben, während man diesen
    # Bereich verlässt - es hat seine eigene Anmeldung beim Dienst
    # (showEvent/hideEvent, siehe gui/overlay/overlay_window.py).

    def _toggle_overlay(self):

        if self._overlay_window is None:

            from gui.overlay.overlay_window import OverlayWindow

            self._overlay_window = OverlayWindow(self.manager)

        if self._overlay_window.isVisible():

            self._overlay_window.hide()

        else:

            self._overlay_window.show()

            self._overlay_window.raise_()

    def _open_guide(self):
        """
        Der Wegweiser wird je Aufruf neu gebaut und mit `exec()`
        angeschlossen - er ist eine Auskunft, kein Aufenthaltsort.
        """

        GuideDialog(self).exec()

    # --------------------------------------------------
    # Snapshot verteilen
    # --------------------------------------------------

    def _on_snapshot(self, snapshot):
        """
        Der Anschluss an `snapshotChanged`.

        Er zeichnet nur, solange diese Seite angemeldet ist. Der Dienst
        veröffentlicht nämlich weiter, während eine andere Seite im
        Vordergrund ist: bei einer laufenden Wiedergabe viermal je
        Sekunde. `on_enter()` zeichnet direkt nach dem Anmelden selbst,
        ein verpasster Snapshot geht also nicht verloren.
        """

        if not self._attached:
            return

        self._draw(snapshot)

    def _draw(self, snapshot):
        """
        Ein Snapshot, eine sichtbare Ansicht.

        Die **sichtbare** und nicht alle vier: die Lernansicht baut je
        Bild ein vollständiges Profil und einen Trainingsplan, die
        Analyse sechs Tabellen. Das für drei Ansichten zu tun, die
        niemand ansieht, war schon zwischen WeintTV und der Academy die
        Doppelarbeit, gegen die dort `_attached` stand.
        """

        view = self._views.get(self._view)

        if view is None or not hasattr(view, "apply"):
            return

        if not self._enabled_for(self._view):
            return

        view.apply(snapshot)

    def _on_character_changed(self, _name: str):

        self._invalidate_learn()

        self._draw(self.service.current())

    def _invalidate_learn(self):

        learn = self._views.get(RAID_VIEW_LEARN)

        if learn is not None and hasattr(learn, "invalidate"):
            learn.invalidate()

    # --------------------------------------------------
    # Archiv und Wiedergabe
    # --------------------------------------------------

    def _on_archive_changed(self):
        """
        Ein neuer Pull ist geladen - dann wird er auch gezeigt.

        Das ist der Schritt, der bis 3.6.0 fehlte: das Archiv wählte
        aus und schrieb daneben "die Zahlen erscheinen in WeintTV", was
        richtig war und trotzdem einen Seitenwechsel von Hand verlangte.
        Umgeschaltet wird nur **aus der Quellenansicht heraus**: wer in
        der Analyse sitzt und dort einen Pull nachlädt, will dort
        bleiben.

        Verglichen wird der Pull und nicht der Kontext: während einer
        Wiedergabe ändern sich Bossanteil, Dauer und Ausgang viermal je
        Sekunde, der Pull dabei nie (siehe `same_pull()`).
        """

        context = context_from(self.service)

        previous = self._pull

        self._pull = context

        for key, view in self._views.items():

            if hasattr(view, "on_archive_changed"):
                view.on_archive_changed()

        if not context.archived or context.loading:
            return

        if previous is not None and same_pull(previous, context):
            return

        if self._view == RAID_VIEW_SOURCE:
            self.show_view(RAID_VIEW_ANALYSIS)

    def _on_replay_changed(self):
        """
        Einen vorgemerkten Sprung nachholen, sobald die Zeitleiste da
        ist.
        """

        if self._pending_seek is None:
            return

        state = self.service.replay_state()

        if state.loading or state.duration <= 0:
            return

        seconds = self._pending_seek

        self._pending_seek = None

        self.service.seek_replay(seconds)

        self.service.set_replay_playing(False)


# --------------------------------------------------
# Hilfen
# --------------------------------------------------


def _create_view(key: str, manager):
    """
    Die Ansichtsklassen werden erst hier importiert.

    Dieselbe Überlegung wie bei `build_page_specs()`: die Ansichten
    lesen `RAID_VIEW_*` aus `gui/navigation.py`, ein Import auf
    Modulebene wäre also ein Zirkelbezug über diese Datei.
    """

    if key == RAID_VIEW_LIVE:

        from gui.pages.raid.live_view import LiveView

        return LiveView(manager)

    if key == RAID_VIEW_ANALYSIS:

        from gui.pages.raid.analysis_view import AnalysisView

        return AnalysisView(manager)

    if key == RAID_VIEW_LEARN:

        from gui.pages.raid.learn_view import LearnView

        return LearnView(manager)

    if key == RAID_VIEW_SOURCE:

        from gui.pages.raid.source_view import SourceView

        return SourceView(manager)

    return None


def _wrap(widget: QWidget) -> QScrollArea:
    """
    Der Scrollbereich um eine Ansicht.

    Derselbe Aufbau wie `MainWindow.wrap_page()`, nur eine Ebene
    tiefer: dort rollt die Seite, hier die Ansicht unter einem
    stehenden Kopfblock.
    """

    scroll = QScrollArea()

    scroll.setWidget(widget)

    scroll.setWidgetResizable(True)

    scroll.setFrameShape(QScrollArea.NoFrame)

    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    scroll.setStyleSheet(
        "QScrollArea{background:transparent;border:none;}"
        "QScrollArea > QWidget > QWidget{background:transparent;}"
    )

    return scroll
