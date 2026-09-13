"""
Die Karte "Dein letzter Pull" auf der Übersicht.

Bis 3.6.0 hatte sie einen Knopf, *Lektion öffnen*, und der führte in die
Academy - wo die Arbeit von vorn begann: Charakter wählen, Pull
wiederfinden, Lektion suchen. Und die Sternreihe daneben stand seit 2.0
da und wurde nie gefüllt.

Geprüft wird beides an der Karte selbst (ohne die ganze Seite), weil
beides von aussen unsichtbar ist: ein Knopf, der den Pull *nicht*
mitnimmt, führt an genau dieselbe Stelle wie vorher, und eine leere
Sternreihe sieht wie eine Bewertung von null aus.
"""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.config import Config
from core.last_pull import LastPull
from gui.navigation import RAID_VIEW_ANALYSIS, RAID_VIEW_LEARN
from gui.theme.theme_manager import init_theme


ARCHIVED = LastPull(
    known=True,
    boss="Garrosh Höllschrei",
    difficulty="25 Heroisch",
    kill=False,
    boss_percent=42.0,
    duration=391.0,
    pull_number=17,
    report_code="aBcDeF12",
    fight_id=3,
    trend=(12.0, 30.0, 58.0),
)


SESSION = LastPull(
    known=True,
    boss="Malkorok",
    kill=False,
    boss_percent=8.0,
    duration=210.0,
    pull_number=4,
    live=True,
)


@pytest.fixture(scope="module")
def qt_app():

    app = QApplication.instance() or QApplication([])

    init_theme(Config())

    return app


@pytest.fixture
def card(qt_app):

    from gui.pages.overview import LastPullCard

    built = LastPullCard()

    built.links = []

    built.raidCenterRequested.connect(built.links.append)

    return built


# --------------------------------------------------
# Der Weg zum Pull
# --------------------------------------------------


def test_the_first_button_opens_this_pull_in_the_analysis(card):

    card.apply(ARCHIVED)

    card.open_pull.click()

    assert len(card.links) == 1

    link = card.links[0]

    assert link.view == RAID_VIEW_ANALYSIS

    assert link.report_code == "aBcDeF12"

    assert link.fight_id == 3


def test_the_second_button_opens_the_same_pull_under_learning(card):

    card.apply(ARCHIVED)

    card.open_lesson.click()

    link = card.links[0]

    assert link.view == RAID_VIEW_LEARN

    assert link.has_pull


def test_a_session_pull_carries_no_half_identity(card):
    """
    Ein Pull dieser Sitzung hat keinen Bericht - er lief live mit. Eine
    halbe Kennung könnte nichts laden und würde die bestehende
    Archivauswahl trotzdem verwerfen.
    """

    card.apply(SESSION)

    card.open_pull.click()

    link = card.links[0]

    assert not link.has_pull

    assert link.report_code == ""

    assert link.fight_id is None

    #
    # Die Perspektive geht trotzdem mit: der Pull ist der geladene, und
    # den will man sehen.
    #

    assert link.view == RAID_VIEW_ANALYSIS


def test_without_a_pull_the_buttons_lead_nowhere_and_say_so(card):
    """
    *lock, don't hide*: die Knöpfe bleiben stehen, sind aber
    abgeschaltet. Ein Knopf, der je nach Lage verschwindet, lässt sich
    weder erklären noch danach fragen.
    """

    card.apply(None)

    assert not card.open_pull.isEnabled()

    assert not card.open_lesson.isEnabled()

    card.apply(ARCHIVED)

    assert card.open_pull.isEnabled()


# --------------------------------------------------
# Der Fokus
# --------------------------------------------------


def test_a_recorded_rating_fills_the_star_row(card):

    card.apply(ARCHIVED, focus=("Bewegung", 2))

    assert card.area.text() == "Bewegung"

    assert card.rating.stars.stars() == 2

    assert "Bewegung" in card.lesson_title.text()


def test_without_a_recorded_rating_nothing_is_estimated(card):
    """
    Ein "schwächster Bereich" ohne Auswertung wäre geraten, und die
    leere Sternreihe daneben sähe ohne den Satz daneben wie ein Urteil
    aus.
    """

    card.apply(ARCHIVED)

    assert card.area.text() == "—"

    assert card.rating.stars.stars() == 0

    assert "nicht bewertet" in card.lesson_title.text()

    #
    # Und der Satz nennt den nächsten Schritt, nicht den Mangel.
    #

    assert "Pull ansehen" in card.lesson_reason.text()


def test_the_empty_card_says_there_is_no_pull_at_all(card):
    """
    Der Fall "es gibt wirklich keinen": kein Pull in dieser Sitzung,
    kein Bericht beim Bot, kein Zwischenspeicher.
    """

    card.apply(None)

    assert card.boss.text() == "Noch kein Pull"

    assert card.area.text() == "—"

    assert card.timestamp.text() == ""


def test_the_trend_line_holds_the_progress_of_the_same_boss(card):

    card.apply(ARCHIVED)

    assert card.sparkline._values == list(ARCHIVED.trend)
