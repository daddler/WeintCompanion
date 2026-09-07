"""
Was die Academy sagt, wenn sie nichts zu sagen hat - und was sie sagt,
wenn sie etwas hat.

Beides waren bis 2.8.0 Lücken: ohne ausgewerteten Kampf stand da ein
Formular voller Striche und in der Karte der nächsten Lektion der Satz
"Alle Lektionen erledigt"; mit Kampf blieben Schwierigkeit, Ausgang,
Unterbrechungen, Tode und Verbrauchsgüter unsichtbar, obwohl sie im
Snapshot lagen.

Geprüft wird hier die Qt-freie Hälfte davon (die Sätze), plus die
Kennzahlen an einem echten Snapshot der Simulation.
"""

import pytest

from analyzer.models import RaidSnapshot
from analyzer.providers.mock import MockRaidDataProvider

from gui.widgets.tv.analysis_gap import (
    ACTION_ARCHIVE,
    ACTION_NONE,
    academy_empty_action,
    academy_empty_text,
    next_lesson_placeholder,
)
from gui.widgets.tv.encounter_meta import encounter_meta, outcome_text


@pytest.fixture(scope="module")
def pull():

    return MockRaidDataProvider()._combat_snapshot(3, 200.0)


@pytest.fixture(scope="module")
def nothing():

    return RaidSnapshot.empty("Simulation")


# --------------------------------------------------
# Leerzustand
# --------------------------------------------------


def test_without_a_pull_the_page_says_what_is_missing(nothing):

    text = academy_empty_text(nothing)

    assert text
    assert "Archiv" in text


def test_with_a_pull_the_hint_disappears(pull):

    assert academy_empty_text(pull) == ""


def test_without_a_raid_the_archive_is_the_way_out(nothing):

    assert academy_empty_action(nothing) == ACTION_ARCHIVE


def test_between_pulls_waiting_is_the_right_action_so_no_button(pull):
    """
    Läuft ein Raid und bloss gerade kein Pull, legte ein Knopf eine
    Handlung nahe, die niemand braucht.
    """

    between = MockRaidDataProvider()._prepare_snapshot(4)

    assert academy_empty_action(between) == ACTION_NONE


def test_an_empty_plan_without_data_is_not_called_finished():
    """
    "Alle Lektionen erledigt" ohne Kampfdaten ist keine Ungenauigkeit,
    sondern eine falsche Aussage über den Lernstand - ausgerechnet auf
    der Karte, die den nächsten Schritt nennen soll.
    """

    assert next_lesson_placeholder(False) == "Noch kein Trainingsplan"
    assert next_lesson_placeholder(True) == "Alle Lektionen erledigt"


# --------------------------------------------------
# Kopfzeile des Profils
# --------------------------------------------------


def test_the_header_names_difficulty_and_outcome(pull):
    """
    Derselbe Boss heroisch und normal sind zwei verschiedene
    Ansprüche, und ein Wipe bei 80 % erklärt eine schwache
    Cooldown-Wertung von selbst.
    """

    from analyzer.academy.evaluator import build_profile

    profile = build_profile(pull, pull.top_damage[3].name)

    meta = encounter_meta(pull, profile)

    assert "Horridon" in meta
    assert pull.encounter.difficulty in meta
    assert "Pull " in meta


def test_a_running_fight_has_an_open_outcome(pull):
    """
    Den laufenden Bossanteil als Wipe auszugeben wäre eine
    Behauptung über einen Kampf, der noch läuft - in einer Wiedergabe
    sogar viermal je Sekunde eine andere.
    """

    assert outcome_text(pull) == "läuft"


def test_a_finished_fight_says_kill_or_the_share(pull):

    from dataclasses import replace

    assert outcome_text(replace(pull, in_combat=False, boss_health_percent=0.0)) == "Kill"

    assert (
        outcome_text(replace(pull, in_combat=False, boss_health_percent=42.0))
        == "Wipe bei 42 %"
    )


def test_without_data_the_header_stays_empty(nothing):

    from analyzer.academy.evaluator import build_profile

    assert encounter_meta(nothing, build_profile(nothing, "Njiah")) == ""


def test_an_unrated_profile_gets_no_average_because_zero_means_no_data(pull):
    """
    `average_stars` ist 0,0, sobald kein Bereich Daten trägt. "Ø 0,0/5"
    wäre dort die schlechteste Note statt "keine Daten" - genau die
    Verwechslung, gegen die `stars == 0` geschrieben ist.
    """

    class _Unrated:
        sample_size = 3
        encounter_name = "Horridon"
        average_stars = 0.0
        rated = ()

    assert "Ø" not in encounter_meta(pull, _Unrated())


# --------------------------------------------------
# Die Kennzahlen an der echten Seite
# --------------------------------------------------
#
# Ab hier werden Widgets gebaut - wie in den anderen fünf Dateien, die
# das tun, und aus demselben Grund: eine Kachel, die dauerhaft "-"
# zeigt, obwohl die Zahl im Snapshot liegt, wirft keine Ausnahme.
#

pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def page(pull):

    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication

    from core.academy_service import AcademyService
    from core.config import Config
    from core.raid_data_service import ArchiveState, MODE_LIVE, ReplayState
    from gui.theme.theme_manager import init_theme

    QApplication.instance() or QApplication([])

    config = Config()

    init_theme(config)

    class _Service(QObject):

        snapshotChanged = Signal(object)
        archiveChanged = Signal()
        replayChanged = Signal()

        def current(self):
            return pull

        def archive_state(self):
            return ArchiveState(mode=MODE_LIVE)

        def replay_state(self):
            return ReplayState()

        def replay_available(self):
            return False

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    class _Logger:

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    class _Manager:

        def __init__(self):
            self.config = config
            self.raid_data = _Service()
            self.logger = _Logger()
            self.academy = AcademyService(self)

    from gui.pages.academy import AcademyPage

    built = AcademyPage(_Manager())

    built._attached = True

    return built


def _tiles(page, pull, name):

    page.character_box.setCurrentText(name)

    page._apply_snapshot(pull)

    return {
        tile.label.text(): (tile.value.text(), tile.caption.text())
        for tile in page._tiles
    }


def test_the_six_metrics_carry_real_numbers(page, pull):

    tiles = _tiles(page, pull, pull.top_damage[3].name)

    assert tiles["AKTIVZEIT"][0].endswith("%")
    assert "/" in tiles["COOLDOWNS"][0]
    assert tiles["UNTERBRECHUNGEN"][0].isdigit()
    assert tiles["TODE"][0] == "0"
    assert tiles["VORBEREITUNG"][0] == "vollständig"


def test_a_missing_flask_is_named_rather_than_counted_away(page, pull):
    """
    Die fehlende Liste ist der Punkt: sie beantwortet als einzige Zahl
    dieser Seite eine Frage, die man VOR dem Pull hätte beantworten
    können.
    """

    tiles = _tiles(page, pull, "Bestienrufer")

    assert tiles["VORBEREITUNG"][0] == "2 fehlen"
    assert "Flask" in tiles["VORBEREITUNG"][1]


def test_a_death_names_its_cause_or_the_battle_res(page, pull):

    assert _tiles(page, pull, "Bestienrufer")["TODE"] == ("1", "Arkane Entladung")

    assert _tiles(page, pull, "Krallenwut")["TODE"] == ("1", "1× wiederbelebt")


def test_without_a_pull_every_metric_says_no_data_not_zero(page, nothing):
    """
    Ein Strich heisst "nicht geliefert", eine Null wäre ein Vorwurf.
    """

    page._apply_snapshot(nothing)

    for tile in page._tiles:
        assert tile.value.text() == "-", tile.label.text()


def test_without_a_pull_the_empty_card_and_its_button_are_there(page, nothing):

    page._apply_snapshot(nothing)

    assert page.empty_card.isVisibleTo(page)
    assert page.empty_button.isVisibleTo(page)


def test_with_a_pull_the_empty_card_is_gone(page, pull):

    _tiles(page, pull, pull.top_damage[3].name)

    assert not page.empty_card.isVisibleTo(page)


def test_no_lessons_is_said_in_words_not_as_zero_of_zero(page, pull):

    page.progress_label.setText("")

    _tiles(page, pull, pull.top_damage[3].name)

    assert "von" in page.progress_label.text()
