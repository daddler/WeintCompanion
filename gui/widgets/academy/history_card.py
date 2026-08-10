"""
WeintCompanion 2.0
Verlauf über mehrere Raidabende

Der Entwurf (§6.3) sieht hier zwei Polylinien über sechs Raidabende
vor: die Gesamtbewertung in Akzentfarbe durchgezogen, der ausgewählte
Bereich in `state.info` gestrichelt, mit drei waagerechten Hilfslinien
und einer Legende mit Von→Nach-Werten.

**Diese Karte hat im Programm keine Datenquelle.** `PlayerProfile` wird
aus genau einem Snapshot berechnet und lebt nur für den Moment der
Anzeige; `RaidDataService.history()` hält abgeschlossene Pulls nur für
die laufende Sitzung im Speicher (`PullSummary`, kein Sternewert, keine
Bereichsaufteilung) und verliert sie beim Neustart der App. Es gibt
keine Stelle, die eine Bewertung über den Tag hinaus speichert - weder
`AcademyService` (der verwaltet nur erledigte Lektionen) noch sonst
irgendwo in `core/`, `analyzer/` oder `addon/`.

Diese Karte zeigt deshalb ihren Leerzustand, statt sechs erfundene
Abende zu zeichnen - dieselbe Regel wie bei der Übersicht-Seite und
„Meine Charaktere": eine Kurve ohne echte Messwerte wäre eine
Behauptung, keine Auskunft. Die Höhe von 340 px bleibt fest, damit die
Karte an ihrem vorgesehenen Platz steht, sobald eine Datenquelle für
mehrere Abende entsteht - dann ändert sich nur ihr Inhalt.
"""

from __future__ import annotations

from gui.widgets.card import Card
from gui.widgets.empty_state import EmptyState


HISTORY_HEIGHT = 340


class HistoryCard(Card):

    def __init__(self, parent=None):

        super().__init__(parent=parent)

        self.setFixedHeight(HISTORY_HEIGHT)

        self.empty = EmptyState(
            eyebrow="VERLAUF",
            title="Noch kein Verlauf über mehrere Abende.",
            explanation=(
                "Eine Bewertung lebt bisher nur für den gerade "
                "angezeigten Kampf - sie wird nirgends über den Tag "
                "hinaus gespeichert. Sobald das der Fall ist, erscheint "
                "hier die Entwicklung über die letzten Raidabende."
            ),
        )

        self.addWidget(self.empty, 1)
