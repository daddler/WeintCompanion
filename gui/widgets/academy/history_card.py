"""
WeintCompanion
Verlauf über mehrere Raidabende - die Lernkurve

Der Entwurf (§6.3) sieht hier zwei Polylinien vor: die
Gesamtbewertung in Akzentfarbe durchgezogen, ein einzelner Bereich in
`state.info` gestrichelt, mit waagerechten Hilfslinien und einer
Legende mit Von→Nach-Werten.

**Bis 2.3.4 hatte diese Karte keine Datenquelle** und sagte das auch:
ein `PlayerProfile` entsteht aus genau einem Snapshot und ist nach
seiner Anzeige weg, `RaidDataService.history()` hält abgeschlossene
Pulls nur für die laufende Sitzung und ohne Sterne. Es gab keine
Stelle, die eine Bewertung über den Tag hinaus aufhob.

Seit 2.3.5 gibt es sie: `analyzer/academy/progression.py` (was ein
aufgezeichneter Pull ist und was mehrere davon aussagen) und
`core/academy_history.py` (wo sie liegen). Diese Karte zeichnet nur
noch, was von dort kommt.

Der Leerzustand bleibt und ist kein Restposten: bis zum zweiten
aufgezeichneten Pull **gibt** es keine Kurve, und eine Linie aus
einem Punkt wäre eine Behauptung. Die feste Höhe bleibt ebenfalls,
damit die Karte beim ersten Pull nicht in die Seite hineinwächst.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from analyzer.academy.progression import (
    build_trend,
    category_sentence,
    summary_text,
    weakest_category,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.academy.progression_chart import ProgressionChart
from gui.widgets.card import Card
from gui.widgets.empty_state import EmptyState
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.wrapped_label import enable_wrap


HISTORY_HEIGHT = 340


class LegendEntry(QWidget):
    """
    Ein Eintrag der Legende: farbiger Strich, Beschriftung, Werte.

    Der Strich liest seine Farbe bei jedem Zeichnen neu - er trägt
    dieselbe Akzentfarbe wie die Linie, zu der er gehört.
    """

    def __init__(self, accent: bool, parent=None):

        super().__init__(parent)

        self._accent = accent

        root = QHBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(8)

        self.dash = QLabel("—")

        self.dash.setFont(font("body"))

        root.addWidget(self.dash)

        self.text = QLabel("")

        self.text.setFont(font("small"))

        restyle(
            self.text,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(self.text)

        root.addStretch(1)

        #
        # Gebundener Slot, keine Lambda: der ThemeManager ist ein
        # Singleton und lebt so lange wie das Programm.
        #

        theme().accent_changed.connect(self._apply_color)

        self._apply_color()

    # --------------------------------------------------

    def _apply_color(self, *args):

        farbe = (
            theme().accent_base()
            if self._accent
            else tokens.STATE["info"]
        )

        restyle(
            self.dash,
            f"color:{farbe};background:transparent;",
        )

    def setText(self, text: str):

        self.text.setText(text)


class HistoryCard(Card):
    """
    Die Lernkurve eines Charakters über seine letzten Pulls.
    """

    def __init__(self, parent=None):

        super().__init__(parent=parent)

        self.setFixedHeight(HISTORY_HEIGHT)

        #
        # Die gefüllte Fassung und der Leerzustand liegen beide in der
        # Karte; umgeschaltet wird über die Sichtbarkeit, damit die
        # Karte beim ersten Punkt nicht neu aufgebaut werden muss.
        #

        self.content = QWidget()

        inhalt = QVBoxLayout(self.content)

        inhalt.setContentsMargins(0, 0, 0, 0)

        inhalt.setSpacing(tokens.SPACE[1])

        inhalt.addWidget(eyebrow_label("VERLAUF"))

        self.headline = QLabel("")

        self.headline.setFont(font("section"))

        enable_wrap(self.headline)

        restyle(
            self.headline,
            f"color:{tokens.WHITE};background:transparent;",
        )

        inhalt.addWidget(self.headline)

        self.chart = ProgressionChart()

        inhalt.addWidget(self.chart, 1)

        self.legend_overall = LegendEntry(accent=True)

        inhalt.addWidget(self.legend_overall)

        self.legend_area = LegendEntry(accent=False)

        inhalt.addWidget(self.legend_area)

        self.note = QLabel("")

        self.note.setFont(font("small"))

        enable_wrap(self.note)

        restyle(
            self.note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        inhalt.addWidget(self.note)

        self.addWidget(self.content, 1)

        self.empty = EmptyState(
            eyebrow="VERLAUF",
            title="Noch kein Verlauf über mehrere Pulls.",
            explanation=(
                "Ab dem zweiten ausgewerteten Pull steht hier, wie "
                "sich die Bewertung entwickelt - insgesamt und im "
                "schwächsten Bereich."
            ),
        )

        self.addWidget(self.empty, 1)

        self.content.setVisible(False)

    # --------------------------------------------------

    def apply(self, records, note: str = ""):
        """
        Die Karte auf eine Reihe aufgezeichneter Pulls setzen.

        `note` erklärt die Auswahl, wenn es etwas zu erklären gibt
        (etwa: gezählt wird nur die eingestellte Datenquelle).
        """

        records = tuple(records or ())

        gesamt = build_trend(records)

        if gesamt is None:

            #
            # Kein Verlauf: die Karte sagt das, statt eine Linie aus
            # einem Punkt zu zeichnen. Der Satz nennt trotzdem, was
            # schon da ist - "ein Pull aufgezeichnet" ist eine andere
            # Auskunft als "noch gar nichts".
            #

            self.empty.update_texts(
                explanation=(
                    summary_text(records, None)
                    + " Ab dem zweiten ausgewerteten Pull steht hier, "
                    "wie sich die Bewertung entwickelt."
                )
            )

            self.content.setVisible(False)

            self.empty.setVisible(True)

            return

        bereich = weakest_category(records)

        bereich_trend = build_trend(records, bereich) if bereich else None

        #
        # Deckt sich die zweite Linie mit der ersten, bleibt sie weg.
        # Das passiert, sobald nur ein einziger Bereich bewertet ist:
        # dann *ist* die Gesamtbewertung dieser Bereich, und zwei
        # deckungsgleiche Linien übereinander sehen nach einem Fehler
        # in der Zeichnung aus statt nach einer Aussage.
        #

        if bereich_trend is not None and bereich_trend.points == gesamt.points:
            bereich_trend = None

        self.headline.setText(summary_text(records, gesamt))

        self.chart.setSeries(
            gesamt.points,
            bereich_trend.points if bereich_trend else (),
            _day_label(records[0].day),
            _day_label(records[-1].day),
        )

        self.legend_overall.setText(gesamt.text)

        self.legend_area.setText(
            bereich_trend.text if bereich_trend else ""
        )

        self.legend_area.setVisible(bereich_trend is not None)

        satz = category_sentence(bereich_trend)

        self.note.setText(
            " · ".join(part for part in (satz, note) if part)
        )

        self.note.setVisible(bool(satz or note))

        self.empty.setVisible(False)

        self.content.setVisible(True)


def _day_label(day: str) -> str:
    """
    "2026-08-12" -> "12.08." - und "" bleibt "".

    Ein unlesbarer Tag wird nicht ersetzt: unter der Kurve stünde
    sonst ein Datum, das niemand gemessen hat.
    """

    teile = str(day or "").split("-")

    if len(teile) != 3:
        return ""

    return f"{teile[2]}.{teile[1]}."
