"""
Archiv.

Ein vergangener WarcraftLogs-Kampf statt des Live-Feeds: Abend wählen,
Pull wählen, ansehen oder abspielen.

**Zur Namensgebung**, weil sie hier eine echte Verwechslungsgefahr
auflöst: "Verlauf" heißt in WeintTV die Liste der in *dieser Sitzung*
abgeschlossenen Pulls (`PullSummary`, `history()`). Der davon völlig
unabhängige Begriff "ein vergangener Bericht" heißt überall - im Code
wie in der Oberfläche - **Archiv**. Beides "Verlauf" zu nennen hätte
zwei verschiedene Dinge unter einem Wort zusammengeworfen.

Der Zustand liegt bewusst nicht auf dieser Seite, sondern global auf
`RaidDataService` (`ArchiveState`, `ReplayState`). Das ist dieselbe
Überlegung, die auch für den Live-Feed gilt: WeintTV und die Academy
lesen **einen** Snapshot, und wer auf der einen Seite ins Archiv
wechselt, findet die andere ebenfalls dort vor. Zwei getrennte
Archivzustände wären zwei Wahrheiten über denselben Kampf.

**Seit 3.5.0 steht der Archivbrowser auf dieser Seite.** Vorher
bestand sie aus einem Wähler und dem Satz "die Zahlen erscheinen in
WeintTV" - ein Bereich in der Navigationsspalte, der selbst nichts
zeigte, während das, was man dort sucht (die Abende und ihre Pulls),
hinter einem Knopf in einem Fenster lag. Gemeldet wurde das als "man
weiss nicht, wo man was findet", und für diese Seite war das wörtlich
richtig: es gab hier nichts zu finden.

Drei Dinge dazu, die nicht Geschmack sind:

* **Es bleibt eine Liste.** Die Seite bettet `ArchiveBrowser` ein -
  dasselbe Widget, das `ArchiveDialog` für WeintTV und die Academy in
  ein Fenster legt. Ein Nachbau würde ab der ersten Änderung anders
  gruppieren als das Original.
* **Kein zweiter Weg zur selben Liste.** Der Knopf "Log wählen …" des
  `ArchivePicker` entfällt hier (`browse=False`); er legte sonst ein
  Fenster über genau die Liste, die schon dasteht.
* **Die Zahlen bleiben in WeintTV.** Diese Seite wählt aus, sie stellt
  nicht dar - eine zweite Darstellung desselben Snapshots wäre zwei
  Anordnungen zu pflegen. Der Weg dorthin steht deshalb als Knopf da,
  sobald ein Pull geladen ist.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from core import archive_index as index

from gui.dialogs.archive_dialog import ArchiveBrowser
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.hero_banner import HeroButton
from gui.widgets.tv.archive_picker import ArchivePicker
from gui.widgets.tv.loading_card import LoadingCard
from gui.widgets.tv.replay_bar import ReplayBar
from gui.widgets.tv.source_strip import SourceStrip
from gui.widgets.wrapped_label import enable_wrap


class ArchivePage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "ARCHIV",
            "Einen vergangenen Kampf ansehen.",
            parent,
        )

        self.service = manager.raid_data

        #
        # Woher die Berichte kommen - und der Weg in den Wegweiser.
        # Dieselbe Zeile wie in WeintTV und der Academy: das Archiv
        # hängt an derselben Quelle, und wer hier keine Berichte sieht,
        # findet den Grund genau dort.
        #

        self.addWidget(SourceStrip(self.service))

        #
        # Live/Archiv und die Wiedergabe. Ohne "Log wählen …" - die
        # Liste steht darunter.
        #

        self.picker = ArchivePicker(self.service, browse=False)

        self.addWidget(self.picker)

        #
        # Die Wartekarte - dieselbe wie in WeintTV und der Academy.
        # Hier ist sie am wichtigsten: hier wird der Pull angeklickt,
        # und hier stand bisher nur "Pull wird geladen …" in elf
        # Punkt neben dem Knopf.
        #

        self.addWidget(LoadingCard(self.service))

        #
        # Die Auswahl selbst.
        #

        self.browser = ArchiveBrowser(self.service, embedded=True)

        self.addWidget(self.browser, 1)

        #
        # Was mit dem geladenen Pull zu tun ist. Die Zeile erscheint
        # erst, wenn wirklich einer geladen ist: zwei Knöpfe, die ins
        # Leere führen, sind schlimmer als keine.
        #

        self.actions = self._build_actions()

        self.addWidget(self.actions)

        self.replay_bar = ReplayBar(self.service)

        self.addWidget(self.replay_bar)

        self.service.archiveChanged.connect(self._on_archive_changed)

        self._on_archive_changed()

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build_actions(self) -> QWidget:

        wrap = QWidget()

        layout = QHBoxLayout(wrap)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(tokens.SPACE[2])

        self.loaded_label = enable_wrap(QLabel(""))

        self.loaded_label.setFont(font("small"))

        restyle(
            self.loaded_label,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        layout.addWidget(self.loaded_label, 1)

        tv_button = HeroButton("In WeintTV ansehen")

        tv_button.clicked.connect(self._open_tv)

        layout.addWidget(tv_button)

        academy_button = HeroButton("In der Academy auswerten", primary=False)

        academy_button.clicked.connect(self._open_academy)

        layout.addWidget(academy_button)

        wrap.setVisible(False)

        return wrap

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _open_tv(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.WEINTTV)

    def _open_academy(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ACADEMY)

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _on_archive_changed(self, *args):
        """
        Titel und Handlungszeile nachziehen.

        Benannt wird, was **geladen** ist, nicht was angeklickt wurde -
        `selection_text()` in `core/archive_index.py` zieht diese Linie
        für alle Anzeigen gemeinsam. Bis 3.5.0 las diese Seite an
        derselben Stelle ein Feld `state.fight`, das es an
        `ArchiveState` nie gab: der Titel stand deshalb dauerhaft auf
        "Einen vergangenen Kampf ansehen.", auch mit geladenem Pull.
        """

        state = self.service.archive_state()

        text = index.selection_text(state)

        loaded = bool(text) and state.selected_fight is not None

        self.header.setTitle(
            text if loaded else "Einen vergangenen Kampf ansehen."
        )

        #
        # Der Satz wiederholt nicht, was oben im Titel steht - er sagt
        # das, was man von hier aus nicht sieht: dass dieser Pull auf
        # beiden anderen Seiten bereitliegt. Genau diese geteilte
        # Auswahl war der Teil, den niemand kannte.
        #

        self.loaded_label.setText(
            "Dieser Pull liegt in WeintTV und der Academy bereit."
            if loaded
            else ""
        )

        self.actions.setVisible(loaded)

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def on_enter(self):

        self.service.attach()

    def on_leave(self):

        self.service.detach()
