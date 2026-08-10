"""
WeintCompanion 2.0
Das Bewertungsraster

Sechs Kacheln, eine je Bereich (Rotation, Movement, Cooldowns,
Mechaniken, Überleben, Leistung), in einem `QGridLayout` mit fester
Spaltenzahl (§6.3): sechs Spalten bei voller Breite, drei unter
1280 px, zwei unter 980 px.

**Genau eine Kachel ist hervorgehoben** - der schwächste bewertete
Bereich (`PlayerProfile.weakest`). Sie bekommt eine eigene Fläche
(`#1A1418`), eine Oberkante in `state.error` bei 28 % und einen
`StatusDot(error)` vor der Rubrik. Das ist die visuelle Antwort auf
die Frage, die die Academy stellt: "woran arbeite ich als Nächstes".
Zwei hervorgehobene Kacheln wären keine Antwort mehr, sondern eine
Liste.

Kein Bereich mit Daten heißt keine Hervorhebung - die hervorgehobene
Kachel zeigt einen *Befund*, und ohne bewertete Bereiche gibt es
keinen. `PlayerProfile.weakest` ist bereits leer, wenn keiner der
sechs Bereiche Daten trägt (`rated`, nicht `ratings`), das Raster muss
das also nicht gesondert prüfen.

Jede Kachel benutzt `Rating` aus `star_rating.py` und nicht `StarRating`
direkt: die beiden Hälften des Nullzustands (blasse Sterne + neutraler
Chip) dürfen nicht getrennt gesetzt werden können.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.academy.star_rating import Rating
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.status_dot import StatusDot
from gui.widgets.wrapped_label import enable_wrap


#
# Spaltenzahl je Haltepunkt (§6.3).
#

COLUMNS_WIDE = 6

COLUMNS_MEDIUM = 3

COLUMNS_NARROW = 2


class RatingTile(Card):
    """
    Eine einzelne Bewertungskachel.
    """

    def __init__(self, label: str, hint: str, parent=None):

        super().__init__(parent=parent)

        self._hint = hint

        self._highlighted = False

        header = QVBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(2)

        self.dot = StatusDot("empty")

        self.dot.setVisible(False)

        row = QGridLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setHorizontalSpacing(6)

        row.addWidget(self.dot, 0, 0)

        self.eyebrow = eyebrow_label(label.upper())

        row.addWidget(self.eyebrow, 0, 1)

        self.addLayout(row)

        self.rating = Rating(0)

        self.addWidget(self.rating)

        self.detail = enable_wrap(QLabel(""))

        self.detail.setFont(font("small"))

        self.addWidget(self.detail)

        self._apply_palette()

    # --------------------------------------------------

    def set_rating(self, stars: int, detail: str):

        self.rating.setStars(stars)

        self.detail.setText(detail or f"{self._hint} - noch keine Daten.")

        restyle(
            self.detail,
            f"color:{tokens.TEXT['secondary'] if stars else tokens.TEXT['muted']};"
            "background:transparent;",
        )

    def set_highlighted(self, highlighted: bool):

        if highlighted == self._highlighted:
            return

        self._highlighted = highlighted

        self.dot.setVisible(highlighted)

        if highlighted:
            self.dot.setState("error")

        self._apply_palette()

    def _apply_palette(self):

        if self._highlighted:

            self.setSurface(*tokens.CARD_GRADIENT_WEAKEST)

            self.setEdgeColor(tokens.tint(tokens.STATE["error"], 0.28))

            restyle(
                self.eyebrow,
                f"color:{tokens.STATE_TEXT['error']};background:transparent;",
            )

        else:

            self.setSurface(None)

            self.setEdgeColor(None)

            restyle(
                self.eyebrow,
                f"color:{tokens.TEXT['muted']};background:transparent;",
            )


class RatingGrid(QWidget):
    """
    Die sechs Kacheln, mit den Haltepunkten aus §6.3 selbst
    gesteuert (siehe `set_columns`, vom `Page.on_layout_changed`
    aufgerufen).
    """

    def __init__(self, categories, labels, hints, parent=None):

        super().__init__(parent)

        self._grid = QGridLayout(self)

        self._grid.setContentsMargins(0, 0, 0, 0)

        self._grid.setHorizontalSpacing(tokens.SPACE[4])

        self._grid.setVerticalSpacing(tokens.SPACE[4])

        self.tiles: dict[str, RatingTile] = {}

        self._categories = list(categories)

        for category in self._categories:

            tile = RatingTile(labels[category], hints.get(category, ""))

            self.tiles[category] = tile

        self._columns = 0

        self.set_columns(COLUMNS_WIDE)

    # --------------------------------------------------

    def set_columns(self, columns: int):

        columns = max(1, columns)

        if columns == self._columns:
            return

        self._columns = columns

        for tile in self.tiles.values():
            self._grid.removeWidget(tile)

        for index, category in enumerate(self._categories):

            row, col = divmod(index, columns)

            self._grid.addWidget(self.tiles[category], row, col)

        for col in range(columns):
            self._grid.setColumnStretch(col, 1)

    # --------------------------------------------------

    def apply(self, profile):

        weakest = profile.weakest

        weakest_category = weakest[0].category if weakest else None

        for category, tile in self.tiles.items():

            rating = profile.rating(category)

            if rating is None:

                tile.set_rating(0, "")

            else:

                tile.set_rating(rating.stars, rating.detail)

            tile.set_highlighted(category == weakest_category)
