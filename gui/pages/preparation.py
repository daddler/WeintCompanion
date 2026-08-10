"""
Vorbereitung.

Wie `characters.py` eine Seite **ohne Datenquelle im Programm** - und
aus demselben Grund trotzdem vorhanden.

Der Entwurf sieht hier ein Raster aus Charakterkarten vor: je Karte
ein Fortschrittsring und die Mängel darunter (fehlende Verzauberungen,
leere Sockel, offene BiS-Plätze). Keiner dieser drei Werte kommt in
`core/`, `addon/` oder `analyzer/` vor - weder das Addon noch der Bot
liefern Ausrüstungsdaten. Der Ring hätte also nichts zu zeigen, was er
nicht erfände.

Ein Ring bei 0 % wäre die falsche Antwort: er behauptet eine Messung
("nichts vorbereitet"), wo es gar keine gab. Genau diese Unterscheidung
zwischen *einem Befund* und *einer Datenlücke* zieht sich durch das
ganze Projekt - im Analyzer trennt sie `stars == 0` von einer schlechten
Bewertung, hier trennt sie den Leerzustand von einem roten Ring.
"""

from __future__ import annotations

from gui.pages._page import Page
from gui.widgets.empty_state import EmptyState


class PreparationPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "VORBEREITUNG",
            "Vor dem Raid steht die Ausrüstung.",
            parent,
        )

        self.empty = EmptyState(
            eyebrow="NOCH KEINE DATEN",
            title="Ausrüstungsdaten werden noch nicht übertragen.",
            explanation=(
                "Verzauberungen, Sockel und offene BiS-Plätze müssten "
                "aus dem Spiel kommen. Weder das Addon noch der Bot "
                "senden sie bisher - deshalb steht hier nichts statt "
                "einer Null, die eine Messung behaupten würde, die es "
                "nicht gab."
            ),
            action="Addon prüfen",
            icon="vorbereitung",
        )

        self.empty.actionTriggered.connect(self._open_addon)

        self.addWidget(self.empty, 1)

    # --------------------------------------------------

    def _open_addon(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ADDON)
