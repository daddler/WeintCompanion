"""
Archiv.

Ein vergangener WarcraftLogs-Kampf statt des Live-Feeds: Bericht
wählen, Pull wählen, abspielen.

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

Diese Seite ist deshalb vor allem Bedienung: Auswahl oben,
Wiedergabeleiste unten. Die Daten selbst stellt WeintTV dar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from gui.pages._page import Page
from gui.theme import tokens
from gui.widgets.card import Card
from gui.widgets.empty_state import EmptyState
from gui.widgets.tv.archive_picker import ArchivePicker
from gui.widgets.tv.replay_bar import ReplayBar


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
        # Auswahl
        #

        picker_card = Card()

        self.picker = ArchivePicker(self.service)

        picker_card.addWidget(self.picker)

        self.addWidget(picker_card)

        #
        # Hinweis auf die Darstellung. Die Zahlen des gewählten Pulls
        # erscheinen in WeintTV - dort steht die ganze Anordnung, und
        # sie hier ein zweites Mal zu bauen hieße, zwei Darstellungen
        # desselben Snapshots zu pflegen.
        #

        self.empty = EmptyState(
            eyebrow="ARCHIV",
            title="Wähle einen Bericht und einen Pull.",
            explanation=(
                "Die Auswahl gilt für WeintTV und die Academy "
                "gleichermaßen - beide lesen denselben Snapshot. Mit "
                "der Wiedergabe läuft der Kampf Sekunde für Sekunde "
                "erneut ab."
            ),
            action="In WeintTV ansehen",
            icon="weinttv",
        )

        self.empty.actionTriggered.connect(self._open_tv)

        self.addWidget(self.empty, 1)

        #
        # Wiedergabeleiste
        #

        self.replay_bar = ReplayBar(self.service)

        self.addWidget(self.replay_bar)

        self.service.archiveChanged.connect(self._on_archive_changed)

        self._on_archive_changed()

    # --------------------------------------------------

    def _open_tv(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.WEINTTV)

    def _on_archive_changed(self, *args):

        state = self.service.archive_state()

        fight = getattr(state, "fight", None)

        if fight is None:

            self.header.setTitle("Einen vergangenen Kampf ansehen.")

            return

        title = getattr(fight, "name", "") or "Kampf"

        self.header.setTitle(f"{title} liegt bereit.")

    # --------------------------------------------------

    def on_enter(self):

        self.service.attach()

    def on_leave(self):

        self.service.detach()
