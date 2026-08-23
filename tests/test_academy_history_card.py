"""
Die Verlaufskarte der Academy - was auf dem Bildschirm steht, und
woher sie ihre Punkte bekommt.

Sie baut Widgets und braucht deshalb Qt. Geprüft wird das, was ein
reiner Test nicht sehen kann: dass die Karte bis zum zweiten Pull
ihren Leerzustand zeigt statt einer Linie aus einem Punkt, dass sie
danach umschaltet, und dass die Kurve nicht bei jedem Bild neu
gezeichnet wird - sie hängt am Snapshot-Strom, der in einer
Wiedergabe viermal je Sekunde tickt.

Am Ende steht die Verdrahtung im `CompanionManager`: sie braucht Qt
(er ist ein `QObject`) und entscheidet, ob ein zweimal geöffneter
Archivpull zwei Punkte ergibt oder einen.
"""

import os

import pytest

pytest.importorskip("PySide6")

from analyzer.academy.progression import PullRecord


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


@pytest.fixture(autouse=True)
def _theme():

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())


def _record(key, sequence, **stars):

    return PullRecord(
        key=key,
        day="2026-08-12",
        sequence=sequence,
        source="warcraftlogs",
        spec="Vergeltung",
        encounter="Malkorok",
        pull_number=sequence,
        ratings=tuple(stars.items()),
    )


def _card(records):

    from gui.widgets.academy.history_card import HistoryCard

    card = HistoryCard()

    card.resize(560, 340)

    card.apply(records)

    return card


# --------------------------------------------------


def test_one_pull_is_no_curve():
    """
    Eine Linie aus einem Punkt wäre eine Behauptung. Der Leerzustand
    sagt trotzdem, was schon da ist - "ein Pull aufgezeichnet" ist
    eine andere Auskunft als "noch gar nichts".
    """

    card = _card([_record("a", 1, rotation=3)])

    assert card.empty.isVisibleTo(card)

    assert not card.content.isVisibleTo(card)

    assert "Ein Pull" in card.empty.explanation.text()


def test_the_second_pull_turns_the_card_into_a_curve():

    card = _card([
        _record("a", 1, rotation=2, mechanics=2),
        _record("b", 2, rotation=4, mechanics=3),
    ])

    assert card.content.isVisibleTo(card)

    assert not card.empty.isVisibleTo(card)

    assert "2 Pulls" in card.headline.text()

    assert card.chart._overall == (2.0, 3.5)


def test_the_weakest_area_is_the_second_line():

    card = _card([
        _record("a", 1, rotation=5, mechanics=1),
        _record("b", 2, rotation=5, mechanics=2),
    ])

    assert card.chart._area == (1.0, 2.0)

    assert "Mechaniken" in card.legend_area.text.text()


def test_a_second_line_that_covers_the_first_one_stays_away():
    """
    Ist nur ein Bereich bewertet, *ist* die Gesamtbewertung dieser
    Bereich. Zwei deckungsgleiche Linien übereinander sehen nach
    einem Fehler in der Zeichnung aus statt nach einer Aussage.
    """

    card = _card([
        _record("a", 1, rotation=4),
        _record("b", 2, rotation=3),
    ])

    assert card.chart._overall == (4.0, 3.0)

    assert card.chart._area == ()

    assert not card.legend_area.isVisibleTo(card)


def test_the_chart_does_not_redraw_for_unchanged_values():
    """
    `setSeries()` hängt an `_apply_snapshot()` und läuft damit im
    Sekundentakt, in einer Wiedergabe viermal je Sekunde. Die Kurve
    ändert sich höchstens einmal je Pull - dieselbe Regel wie beim
    ArchivePicker.
    """

    card = _card([
        _record("a", 1, rotation=2, mechanics=2),
        _record("b", 2, rotation=4, mechanics=4),
    ])

    aufrufe = []

    card.chart.update = lambda *args: aufrufe.append(1)

    card.chart.setSeries((2.0, 4.0), (), "12.08.", "12.08.")

    assert aufrufe == []

    card.chart.setSeries((2.0, 5.0), (), "12.08.", "12.08.")

    assert aufrufe == [1]


def test_the_simulation_names_itself_under_the_curve():
    """
    Die Kurve der Simulation sieht aus wie eine echte. Ohne diesen
    Satz wäre nicht zu erkennen, dass sie aus gerechneten Pulls
    besteht.
    """

    from gui.pages.academy import _source_note

    assert "Simulation" in _source_note("mock")

    assert _source_note("warcraftlogs") == ""


def test_the_curve_is_released_with_its_card():
    """
    Beide Widgets hängen am `accent_changed` des ThemeManagers, und
    der ist ein Singleton, der so lange lebt wie das Programm. Eine
    Lambda darin hielte die Karte für immer fest (siehe CLAUDE.md).
    """

    import gc
    import weakref

    card = _card([
        _record("a", 1, rotation=2),
        _record("b", 2, rotation=4),
    ])

    verweis = weakref.ref(card.chart)

    del card

    gc.collect()

    assert verweis() is None


# --------------------------------------------------
# Die Verdrahtung
# --------------------------------------------------
#
# Aufgezeichnet wird im `CompanionManager` und nicht auf der
# Academy-Seite: wer den Abend über WeintTV laufen lässt und erst
# danach in die Academy sieht, hätte sonst genau einen Punkt.
#


class _ArchiveState:

    def __init__(self, report="", fight=None, reports=(), browsing=None):
        self.selected_report = report
        self.selected_fight = fight
        self.reports = reports
        self.browsing = bool(report) if browsing is None else browsing


class _Report:

    def __init__(self, code, start):
        self.code = code
        self.start = start


class _Academy:

    def __init__(self):
        self.calls = []

    def note_snapshot(self, snapshot, **kwargs):
        self.calls.append(kwargs)
        return True


class _RaidData:

    def __init__(self, state):
        self._state = state

    def archive_state(self):
        return self._state


class _Manager:

    def __init__(self, state):
        from types import SimpleNamespace

        self.raid_data = _RaidData(state)
        self.academy = _Academy()
        self.config = SimpleNamespace(data={"raid_data_source": "warcraftlogs"})
        self.logger = SimpleNamespace(warning=lambda message: None)


def _note(state):

    from core.companion_manager import CompanionManager

    manager = _Manager(state)

    #
    # `_report_day()` gehört zur selben Verdrahtung und wird deshalb
    # mitgebunden - der Test prüft beide zusammen, weil sie zusammen
    # die Herkunft eines Punktes bestimmen.
    #

    manager._report_day = CompanionManager._report_day.__get__(manager)

    CompanionManager._note_academy_pull(manager, object())

    return manager.academy.calls[0]


def test_an_archived_pull_carries_report_and_fight_as_its_origin():
    """
    Ohne diese Herkunft wäre derselbe Pull, zweimal geöffnet, zweimal
    in der Kurve - und ihre Reihenfolge käme aus der Klickfolge statt
    aus dem Raidabend.
    """

    aufruf = _note(
        _ArchiveState(
            report="abc123",
            fight=7,
            reports=(_Report("abc123", "2026-08-12T18:00:00Z"),),
        )
    )

    assert aufruf["origin"] == "abc123#7"

    assert aufruf["sequence"] == 7

    assert aufruf["day"].startswith("2026-08-1")

    assert aufruf["source"] == "warcraftlogs"


def test_a_live_pull_carries_no_origin():

    aufruf = _note(_ArchiveState())

    assert aufruf["origin"] == ""

    assert aufruf["day"] == ""

    assert aufruf["sequence"] == 0


def test_a_left_over_archive_selection_does_not_brand_a_live_pull():
    """
    `show_live()` lässt die Archiv-Auswahl ausdrücklich stehen, damit
    ein Rücksprung ins Archiv wieder dort landet, wo man war. Ohne
    die Prüfung auf `browsing` bekäme der nächste Live-Pull die
    Kennung des zuletzt angesehenen Archivkampfes - und würde als
    dessen Doppelgänger verworfen. Der Punkt fehlte dann in der
    Kurve, ohne dass irgendetwas fehlschlägt.
    """

    aufruf = _note(
        _ArchiveState(report="abc123", fight=7, browsing=False)
    )

    assert aufruf["origin"] == ""


def test_a_report_that_is_no_longer_listed_costs_the_day_and_nothing_else():
    """
    Dann fällt die Aufzeichnung auf den heutigen Tag zurück - was für
    einen gerade gespielten Pull ohnehin stimmt. Ein geratenes Datum
    wäre der teurere Fehler.
    """

    aufruf = _note(_ArchiveState(report="weg", fight=2))

    assert aufruf["origin"] == "weg#2"

    assert aufruf["day"] == ""


def test_a_failing_record_never_takes_the_running_fight_with_it():
    """
    Der Aufruf hängt am Datenstrom von WeintTV. Eine Aufzeichnung,
    die scheitert, darf dort nichts anhalten.
    """

    from types import SimpleNamespace

    from core.companion_manager import CompanionManager

    gemeldet = []

    manager = _Manager(_ArchiveState())

    manager.raid_data = SimpleNamespace(
        archive_state=lambda: (_ for _ in ()).throw(RuntimeError("kaputt"))
    )

    manager.logger = SimpleNamespace(warning=gemeldet.append)

    CompanionManager._note_academy_pull(manager, object())

    assert gemeldet
