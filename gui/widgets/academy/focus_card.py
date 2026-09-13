"""
„Deine größten Baustellen" - die Antwort auf die eine Frage, die die
Lernansicht beantworten soll.

**Warum es diese Karte gibt.** Bis 3.6.0 war die Academy ein
Lernzentrum: drei Reiter (Übersicht, Trainingsplan, Katalog), sechs
Bewertungskacheln, sechs Kennzahlen, eine Kurve, eine Lektionsliste.
Alles davon richtig, und keins davon beantwortete die Frage, mit der
jemand hinsieht - *was soll ich als Nächstes verbessern?* Die Antwort
lag verteilt: der schwächste Bereich in einer hervorgehobenen Kachel,
seine Begründung im Kleintext darin, die passende Lektion eine
Reiterseite weiter, der Moment dazu in einem Knopf auf deren Karte.

Diese Karte führt die vier Teile zu **einer Zeile je Baustelle**
zusammen: Bereich, Sterne, Begründung, Lektion - und daneben die zwei
Wege, die man von dort aus gehen will (die Lektion, oder der Moment im
Kampf).

Drei Regeln, die nicht Geschmack sind:

- **Was nicht bewertet ist, ist keine Baustelle.** Gelesen wird
  `profile.weakest`, das über `rated` läuft und damit null Sterne
  überspringt - `stars == 0` heißt "keine Daten", nicht "schlecht".
  Eine unbewertete Kategorie oben als größte Baustelle zu zeigen wäre
  genau die Verwechslung, gegen die der Analyzer geschrieben ist.
- **Die Zeilen werden nicht neu gebaut.** Diese Karte hängt am
  Snapshot und läuft damit im Sekundentakt, in einer Wiedergabe
  viermal je Sekunde. Die drei Zeilen entstehen einmal und werden
  beschriftet - dieselbe Regel wie bei `MeterRowList`, `EntryList` und
  dem Archivbrowser.
- **Ein Knopf, der nichts trifft, steht nicht da.** Den Sprung in die
  Wiedergabe gibt es nur, wenn die Bewertung einen Moment nennt
  (`at_seconds >= 0`; -1 heißt "kein Moment" und nie "Sekunde 0"), und
  die Lektion nur, wenn der Plan für diesen Bereich eine offene hat.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.academy.star_rating import Rating
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.wrapped_label import enable_wrap


#
# Wie viele Baustellen. Drei sind der Ausschnitt, in dem "als
# Nächstes" noch eine Reihenfolge ist; bei sechs ist es wieder die
# vollständige Bewertung, und die steht ohnehin darunter.
#

FOCUS_ROWS = 3


#
# Breite der Bereichsspalte. "Mechaniken" ist der längste der sechs
# Namen; darunter bricht er um, und ein Bereichsname über zwei Zeilen
# liest sich wie zwei Bereiche.
#

AREA_COLUMN_W = 116


def _clock(seconds: float) -> str:

    total = max(0, int(seconds))

    return f"{total // 60:02d}:{total % 60:02d}"


class FocusRow(QFrame):
    """
    Eine Baustelle: Bereich, Sterne, Begründung, Lektion, zwei Wege.
    """

    #
    # Die Signale tragen genau, was das Ziel braucht - keine
    # Rückverweise auf die Zeile. Ein Callback-Abschluss, der das
    # Fenster festhält, baut einen Kreis, den der Sammler nicht sieht
    # (siehe docs/architecture/qt-pitfalls.md).
    #

    lessonRequested = Signal(str)

    momentRequested = Signal(float)

    analysisRequested = Signal(str)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName("focusRow")

        self.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self,
            f"""
            QFrame#focusRow{{
                background:{tokens.SURFACE["card"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        #
        # **Die Höhe hängt an der Breite.** Die Begründung darin ist
        # umbrechender Text ("4 von 6 möglichen Einsätzen · 0 von 1
        # grossen Cooldowns im Heldentum · …"), und `enable_wrap()`
        # meldet das am Label an - aber nur am Label. Ohne dieselbe
        # Ankündigung an der Zeile fragt das Layout der Karte nie
        # `heightForWidth()` und verteilt die Höhe nach einer
        # `sizeHint()`, die eine Textzeile annimmt. Sichtbar war das
        # als Knopfreihe, die unten aus ihrer eigenen Zeile lief.
        #

        policy = self.sizePolicy()

        policy.setHeightForWidth(True)

        policy.setVerticalPolicy(QSizePolicy.Minimum)

        self.setSizePolicy(policy)

        self._lesson_id = ""

        self._category = ""

        self._seconds = -1.0

        root = QHBoxLayout(self)

        root.setContentsMargins(14, 12, 14, 12)

        root.setSpacing(tokens.SPACE[2])

        # --------------------------------------------------
        # Links: Bereich und Sterne
        # --------------------------------------------------

        head = QVBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(4)

        #
        # Feste Breite, damit die drei Zeilen eine Spalte bilden: ohne
        # sie richtete sich jede nach der Länge ihres eigenen
        # Bereichsnamens, und die Sterne stünden im Zickzack.
        #

        self.area = QLabel("")

        self.area.setFixedWidth(AREA_COLUMN_W)

        self.area.setFont(font("card"))

        restyle(
            self.area,
            f"color:{tokens.WHITE};background:transparent;",
        )

        head.addWidget(self.area)

        self.rating = Rating(0)

        head.addWidget(self.rating)

        head.addStretch(1)

        root.addLayout(head)

        # --------------------------------------------------
        # Mitte: warum, und welche Lektion
        # --------------------------------------------------

        column = QVBoxLayout()

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(4)

        self.detail = enable_wrap(QLabel(""))

        self.detail.setFont(font("small"))

        restyle(
            self.detail,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        column.addWidget(self.detail)

        self.lesson = enable_wrap(QLabel(""))

        self.lesson.setFont(font("small"))

        restyle(
            self.lesson,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        column.addWidget(self.lesson)

        # --------------------------------------------------
        # Die Wege, unter dem Text
        # --------------------------------------------------
        #
        # Nebeneinander und nicht übereinander: drei gestapelte Knöpfe
        # sind 128 px hoch, und drei solche Zeilen schöben Bewertung,
        # Kennzahlen und Plan komplett unter den Rand. Nebeneinander
        # kostet eine Zeile für alle drei.
        #

        actions = QHBoxLayout()

        actions.setContentsMargins(0, 0, 0, 0)

        actions.setSpacing(tokens.SPACE[1])

        self.lesson_button = HeroButton("Lektion starten")

        self.lesson_button.clicked.connect(self._request_lesson)

        actions.addWidget(self.lesson_button)

        self.moment_button = HeroButton("Moment ansehen", primary=False)

        self.moment_button.clicked.connect(self._request_moment)

        actions.addWidget(self.moment_button)

        self.detail_button = HeroButton("Zahlen dazu", primary=False)

        self.detail_button.clicked.connect(self._request_analysis)

        actions.addWidget(self.detail_button)

        actions.addStretch(1)

        column.addLayout(actions)

        column.addStretch(1)

        root.addLayout(column, 1)

    # --------------------------------------------------

    def hasHeightForWidth(self) -> bool:

        return True

    def heightForWidth(self, width: int) -> int:
        """
        Die Höhe, die diese Zeile bei dieser Breite wirklich braucht.

        Über das eigene Layout gefragt und nicht geschätzt: es kennt
        die umbrechenden Labels darin und rechnet dieselbe Antwort, die
        beim Zeichnen gilt. `super()` wäre hier die Ein-Zeilen-Annahme.
        """

        return max(
            self.layout().heightForWidth(width),
            self.layout().minimumSize().height(),
        )

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def _request_lesson(self):

        if self._lesson_id:
            self.lessonRequested.emit(self._lesson_id)

    def _request_moment(self):

        if self._seconds >= 0:
            self.momentRequested.emit(float(self._seconds))

    def _request_analysis(self):

        self.analysisRequested.emit(self._category)

    # --------------------------------------------------
    # Beschriften
    # --------------------------------------------------

    def apply(self, rating, item):
        """
        `rating` ist ein `SkillRating`, `item` der offene `PlanItem`
        dieses Bereichs oder `None`.
        """

        self._category = rating.category

        self._seconds = float(getattr(rating, "at_seconds", -1.0))

        self.area.setText(rating.label)

        self.rating.setStars(rating.stars)

        #
        # Die Begründung, sonst der Kennzahlensatz, sonst der
        # allgemeine Hinweis zum Bereich. Leer bliebe die Zeile als
        # Sterne ohne Aussage stehen - und eine Bewertung ohne Grund
        # ist ein Urteil ohne Beleg.
        #

        self.detail.setText(
            rating.detail
            or rating.metric_text
            or rating.hint
        )

        lesson = getattr(item, "lesson", None)

        self._lesson_id = getattr(lesson, "lesson_id", "") if lesson else ""

        self.lesson.setText(
            f"Lektion: {lesson.title}"
            if lesson is not None
            else "Für diesen Bereich ist derzeit keine Lektion offen."
        )

        self.lesson_button.setVisible(bool(self._lesson_id))

        self.moment_button.setVisible(self._seconds >= 0)

        self.moment_button.setText(
            f"Moment {_clock(self._seconds)}"
            if self._seconds >= 0
            else "Moment ansehen"
        )

        #
        # Neuer Text, neue Höhe. Ohne diesen Anstoss behielte die Zeile
        # die Höhe des vorigen Befundes - beim Wechsel des Charakters
        # ist das regelmässig eine Zeile zu wenig.
        #

        self.updateGeometry()


class FocusCard(Card):
    """
    Die Karte um die Baustellen - samt Leerzustand.
    """

    lessonRequested = Signal(str)

    momentRequested = Signal(float)

    analysisRequested = Signal(str)

    def __init__(self, parent=None):

        super().__init__(accent=True, parent=parent)

        self.addWidget(
            eyebrow_label("DEINE GRÖSSTEN BAUSTELLEN")
        )

        self.placeholder = enable_wrap(QLabel(""))

        self.placeholder.setFont(font("small"))

        restyle(
            self.placeholder,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.addWidget(self.placeholder)

        self.rows: list[FocusRow] = []

        for _ in range(FOCUS_ROWS):

            row = FocusRow()

            row.lessonRequested.connect(self.lessonRequested)

            row.momentRequested.connect(self.momentRequested)

            row.analysisRequested.connect(self.analysisRequested)

            row.setVisible(False)

            self.addWidget(row)

            self.rows.append(row)

    # --------------------------------------------------

    def apply(self, profile, plan, placeholder: str = ""):
        """
        Die schwächsten bewerteten Bereiche, schwächster zuerst.

        `placeholder` ist der Satz für den Fall, dass keine Baustelle
        übrig bleibt - er kommt von aussen (`analysis_gap.py`), damit
        diese Karte und die Leerzustandskarte darüber nicht zwei
        verschiedene Erklärungen für dieselbe Lage geben. Dass "nichts
        ausgewertet" und "nichts Auffälliges" zwei verschiedene Sätze
        brauchen, entscheidet ebenfalls dort `focus_placeholder()`.
        """

        #
        # **Nur wirklich schwache Bereiche.** `profile.weakest` gibt
        # alle bewerteten aufsteigend zurück; blind die ersten drei zu
        # nehmen führte unter der Überschrift "deine grössten
        # Baustellen" Bereiche mit fünf Sternen auf - das Gegenteil
        # dessen, was dort steht. `is_weak` zieht die Grenze bei drei
        # Sternen und setzt `has_data` voraus, also auch hier: null
        # Sterne heissen "keine Daten", nicht "schlecht".
        #

        weakest = tuple(
            rating
            for rating in getattr(profile, "weakest", ())
            if getattr(rating, "is_weak", False)
        )[:FOCUS_ROWS]

        for index, row in enumerate(self.rows):

            if index >= len(weakest):

                row.setVisible(False)

                continue

            rating = weakest[index]

            row.apply(rating, _open_item_for(plan, rating.category))

            row.setVisible(True)

        self.placeholder.setText("" if weakest else placeholder)

        self.placeholder.setVisible(not weakest and bool(placeholder))


def _open_item_for(plan, category: str):
    """
    Die nächste offene Lektion dieses Bereichs.

    Offen und nicht bloss "die erste": eine Lektion, die abgehakt ist
    oder die der Log als erfüllt zeigt, als nächsten Schritt
    anzubieten wäre eine Empfehlung gegen den eigenen Verlauf.
    """

    for item in getattr(plan, "items", ()):

        if item.lesson.category != category:
            continue

        if item.done:
            continue

        return item

    return None
