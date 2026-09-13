"""
Der Archivbrowser und die Quellenansicht des Raid Centers.

Diese Datei baut Widgets - wie die anderen unter `tests/`, und aus
demselben Grund: die Fehler, um die es hier geht, sind von aussen
unsichtbar. Eine Liste, die sich beim Laden selbst leert, ein "geladen"
in der Sekunde, in der die Ansicht erscheint, und ein Klick, der beim
falschen Dienst landet, werfen alle keine Ausnahme.

**Seit 4.0 gibt es kein Fenster mehr.** Der Browser steckte bis dahin
zusätzlich in einem Dialog (`ArchiveDialog`), den WeintTV und die
Academy über "Log wählen …" öffneten - zwei Wege zur selben Liste, von
denen der eine sich über den anderen legte. Er ist entfallen; die Liste
ist die Perspektive *Quelle*. Was vom Fenster geprüft wurde (es schliesst
nur für den Pull, der **in ihm** angeklickt wurde), gilt unverändert
für das Signal `fightLoaded`, das jetzt an seiner Stelle steht.

`importorskip` und `QT_QPA_PLATFORM=offscreen` wie dort.
"""

import pytest

pytest.importorskip("PySide6")

from dataclasses import replace

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QLabel

from analyzer.providers.warcraftlogs_payload import (
    build_fight_list,
    build_report_list,
)
from core.config import Config
from core.raid_data_service import (
    ArchiveState,
    MODE_ARCHIVE,
    MODE_LIVE,
    MODE_REPLAY,
    ReplayState,
)
from gui.theme.theme_manager import init_theme


REPORTS = [
    {
        "code": "aBcDeF12",
        "title": "Mittwochsraid",
        "zone": "Belagerung von Orgrimmar",
        "start": "2026-09-02T18:30:00Z",
    },
    {
        "code": "zZz9",
        "title": "Donnerstag",
        "zone": "Belagerung von Orgrimmar",
        "start": "2026-09-03T18:35:00Z",
    },
]

FIGHTS = [
    {
        "id": 1, "encounter_id": 1620, "name": "Immerseus", "difficulty_id": 6,
        "kill": True, "boss_percentage": 0, "duration": 310,
        "start": "2026-09-02T18:41:00Z", "size": 25, "pull_number": 1,
    },
    {
        "id": 2, "encounter_id": 1623, "name": "Garrosh", "difficulty_id": 6,
        "kill": False, "boss_percentage": 42, "duration": 300,
        "start": "2026-09-02T19:47:00Z", "size": 25, "pull_number": 1,
    },
    {
        "id": 3, "encounter_id": 1623, "name": "Garrosh", "difficulty_id": 6,
        "kill": False, "boss_percentage": 4, "duration": 520,
        "start": "2026-09-02T20:03:00Z", "size": 25, "pull_number": 2,
    },
]


class FakeService(QObject):
    """
    Nur das, was der Browser wirklich anspricht.
    """

    archiveChanged = Signal()
    replayChanged = Signal()

    #
    # Die Quellenansicht traegt die Quellenzeile (`SourceStrip`), und die
    # haengt an `sourceChanged` - damit ein Wechsel in den Einstellungen
    # hier nicht als alter Stand stehen bleibt.
    #

    sourceChanged = Signal()

    def __init__(self, **state):

        super().__init__()

        self.calls = []

        self._replay = ReplayState()

        self._available = False

        self.state = ArchiveState(
            mode=MODE_ARCHIVE,
            reports=build_report_list({"reports": REPORTS}),
            fights=build_fight_list({"fights": FIGHTS}),
            selected_report="aBcDeF12",
            **state,
        )

    def archive_state(self):
        return self.state

    def replay_state(self):
        return self._replay

    def replay_available(self):
        return self._available

    def enter_archive_mode(self):
        self.calls.append("enter")

    def ensure_reports(self):
        self.calls.append("reports")

    def configured_source(self):
        return "mock"

    def active_source(self):
        return "mock"

    def set_source(self, source):
        self.calls.append(("source", source))
        return False

    def history(self):
        return ()

    def show_live(self):
        self.calls.append("live")

    def start_replay(self):
        self.calls.append("replay")

    def select_archive_report(self, code):
        self.calls.append(("report", code))
        self.state = replace(self.state, selected_report=code)
        self.archiveChanged.emit()

    def select_archive_fight(self, code, fight_id):
        self.calls.append(("fight", code, fight_id))
        self.state = replace(self.state, selected_fight=fight_id)
        self.archiveChanged.emit()


@pytest.fixture(scope="module")
def qt_app():

    app = QApplication.instance() or QApplication([])

    init_theme(Config())

    return app


def _rows(body):
    """
    Die Zeilen einer Spalte als Textlisten.
    """

    layout = body.layout()

    out = []

    for position in range(layout.count() - 1):

        widget = layout.itemAt(position).widget()

        if widget is None:
            continue

        if isinstance(widget, QLabel):
            out.append([widget.text()])
            continue

        out.append([
            child.text()
            for child in widget.findChildren(QLabel)
            if child.text()
        ])

    return out


def _flat(body):

    return [" | ".join(row) for row in _rows(body)]


def _browser(qt_app, service):
    """
    Der Browser - seit 4.0 ausschliesslich als Teil der Quellenansicht.
    """

    from gui.widgets.raid.archive_browser import ArchiveBrowser

    return ArchiveBrowser(service)


def _loaded(browser):
    """
    Ob der Browser einen geladenen Pull gemeldet hat.

    Das ist der Nachfolger von "hat sich das Fenster geschlossen": das
    Raid Center schaltet auf dieses Signal hin auf die Analyse um, und
    ein Signal zur falschen Zeit ist derselbe Fehler wie ein Fenster,
    das sich zur falschen Zeit schliesst.
    """

    seen = []

    browser.fightLoaded.connect(lambda: seen.append(True))

    return seen


# --------------------------------------------------
# Aufbau
# --------------------------------------------------


def test_reports_are_listed_under_their_evening(qt_app):

    browser = _browser(qt_app, FakeService())

    days = _flat(browser.days_body)

    assert days[0].startswith("Mittwoch, ")
    assert "Mittwochsraid" in days[1]
    assert days[2].startswith("Donnerstag, ")


def test_pulls_are_grouped_under_their_boss(qt_app):

    browser = _browser(qt_app, FakeService())

    rows = _flat(browser.fights_body)

    assert rows[0] == "Immerseus | 1 Versuch · Kill"
    assert rows[2].startswith("Garrosh | 2 Versuche · bester Versuch 4 %")


def test_a_pull_row_carries_the_time_of_day_not_a_second_date(qt_app):
    """
    Das Datum steht links am Abend; zwanzig Mal zu wiederholen wäre
    Lärm - wiederzuerkennen ist ein Pull an seiner Uhrzeit.
    """

    browser = _browser(qt_app, FakeService())

    row = _rows(browser.fights_body)[1]

    assert "Pull 1" in row
    assert any(":" in cell and len(cell) == 5 for cell in row)
    assert not any("2026" in cell for cell in row)


def test_the_best_wipe_is_marked_but_a_lonely_one_is_not(qt_app):
    """
    Bei einem einzelnen Versuch wäre "bester Versuch" eine
    Auszeichnung ohne Konkurrenz.
    """

    browser = _browser(qt_app, FakeService())

    rows = _flat(browser.fights_body)

    assert "BESTER VERSUCH" in rows[4]
    assert "BESTER VERSUCH" not in rows[3]

    single = FakeService()
    single.state = replace(
        single.state,
        fights=build_fight_list({"fights": [FIGHTS[1]]}),
    )

    lonely = _browser(qt_app, single)

    assert not any("BESTER VERSUCH" in row for row in _flat(lonely.fights_body))


def test_a_kill_is_not_also_called_the_best_try(qt_app):
    """
    Dort ist der Kill die Antwort; ein zweiter Hinweis lenkt ab.
    """

    service = FakeService()
    service.state = replace(
        service.state,
        fights=build_fight_list({"fights": [FIGHTS[1], dict(FIGHTS[2], kill=True, boss_percentage=0)]}),
    )

    browser = _browser(qt_app, service)

    assert not any("BESTER VERSUCH" in row for row in _flat(browser.fights_body))


# --------------------------------------------------
# Suche und Filter
# --------------------------------------------------


def test_the_search_narrows_both_columns(qt_app):

    browser = _browser(qt_app, FakeService())

    browser.search.setText("garrosh")

    assert all("Immerseus" not in row for row in _flat(browser.fights_body))

    browser.search.setText("zzz9")

    assert all("Mittwochsraid" not in row for row in _flat(browser.days_body))


def test_only_kills_removes_the_boss_rather_than_leaving_a_heading(qt_app):

    browser = _browser(qt_app, FakeService())

    browser.kills_only.setChecked(True)

    rows = _flat(browser.fights_body)

    assert len(rows) == 2
    assert rows[0].startswith("Immerseus")


def test_a_search_without_a_hit_says_so_instead_of_showing_nothing(qt_app):

    browser = _browser(qt_app, FakeService())

    browser.search.setText("gibtesnicht")

    assert "passt" in " ".join(_flat(browser.fights_body))


def test_the_pull_count_is_on_the_heading(qt_app):

    browser = _browser(qt_app, FakeService())

    assert browser.fights_eyebrow.text() == "PULLS · 3"

    browser.kills_only.setChecked(True)

    assert browser.fights_eyebrow.text() == "PULLS · 1"


# --------------------------------------------------
# Auswahl
# --------------------------------------------------


def test_clicking_a_report_asks_the_service_for_its_pulls(qt_app):

    service = FakeService()

    browser = _browser(qt_app, service)

    browser._day_rows["zZz9"].activate()

    assert ("report", "zZz9") in service.calls


def test_clicking_a_pull_loads_it(qt_app):

    service = FakeService()

    browser = _browser(qt_app, service)

    browser._fight_rows[3].activate()

    assert ("fight", "aBcDeF12", 3) in service.calls


def test_a_still_loading_pull_is_not_reported_as_loaded(qt_app):
    """
    Der einzelne Pull kostet den Bot Minuten. Ein "geladen" beim Klick
    liesse das Raid Center auf die Analyse umschalten, die dann
    minutenlang leer dastünde - und der Nutzer vor einem Bildschirm,
    der sich aus unerfindlichen Gründen nicht ändert.
    """

    service = FakeService()

    browser = _browser(qt_app, service)

    seen = _loaded(browser)

    browser._awaiting = 3

    service.state = replace(service.state, selected_fight=3, fight_loading=True)

    browser._refresh()

    assert seen == []
    assert browser._awaiting == 3


def test_a_finished_pull_is_reported_once(qt_app):

    service = FakeService()

    browser = _browser(qt_app, service)

    seen = _loaded(browser)

    browser._awaiting = 3

    service.state = replace(service.state, selected_fight=3)

    browser._refresh()

    browser._refresh()

    assert seen == [True]
    assert browser._awaiting is None


def test_an_error_does_not_report_a_loaded_pull_over_its_own_message(qt_app):

    service = FakeService()

    browser = _browser(qt_app, service)

    seen = _loaded(browser)

    browser._awaiting = 3

    service.state = replace(
        service.state,
        selected_fight=3,
        fight_error="Bot nicht erreichbar",
    )

    browser._refresh()

    assert seen == []
    assert browser._awaiting is None
    assert "Bot nicht erreichbar" in browser.status.text()


def test_a_pull_selected_before_the_view_was_entered_reports_nothing(qt_app):
    """
    Beim Betreten ist meist noch der Pull von vorhin gewählt und längst
    geladen. Ohne den Merker meldete der Browser ihn in der Sekunde, in
    der die Ansicht erscheint - und das Raid Center sprang sofort weg
    von der Liste, die man gerade aufgeschlagen hat.
    """

    service = FakeService(selected_fight=3)

    browser = _browser(qt_app, service)

    seen = _loaded(browser)

    browser._refresh()

    assert browser._awaiting is None
    assert seen == []


def test_entering_the_list_loads_the_reports_without_leaving_live(qt_app):
    """
    Die Liste liegt einen Klick neben *Live*. Wer nachsieht, welche
    Abende es gibt, hat damit noch nicht entschieden, den laufenden Raid
    zu verlassen - `enter_archive_mode()` hätte genau das getan (der
    Live-Poll verwirft seine Ergebnisse, sobald `browsing` gilt).
    """

    service = FakeService()

    _browser(qt_app, service)

    assert "reports" in service.calls
    assert "enter" not in service.calls


# --------------------------------------------------
# Ladezustände
# --------------------------------------------------


def test_loading_reports_says_so_instead_of_looking_empty(qt_app):

    service = FakeService()
    service.state = replace(
        service.state,
        reports=(),
        reports_loading=True,
    )

    browser = _browser(qt_app, service)

    assert "geladen" in " ".join(_flat(browser.days_body))


def test_without_a_report_the_pull_column_points_left(qt_app):

    service = FakeService()
    service.state = replace(service.state, selected_report="", fights=())

    browser = _browser(qt_app, service)

    assert "Raidabend" in " ".join(_flat(browser.fights_body))


# --------------------------------------------------
# Die Quellenansicht
# --------------------------------------------------
#
# Sie hat die Quellenzeile (`ArchivePicker`) der drei alten Seiten
# ersetzt. Zwei Dinge daran sind neu und gehören geprüft: die
# Schnellauswahl (drei Fragen, die man vor der Liste hat) und der
# Umschalter zwischen laufendem Raid und Archiv, der jetzt hier steht
# und nicht dreimal.


def _source_view(qt_app, service):

    from core.config import Config
    from gui.pages.raid.source_view import SourceView

    class _Manager:

        def __init__(self):
            self.config = Config()
            self.raid_data = service

    return SourceView(_Manager())


def test_the_status_line_names_the_loaded_pull(qt_app):

    view = _source_view(qt_app, FakeService(selected_fight=3))

    text = view.status_label.text()

    assert text.startswith("Mittwoch, ")
    assert "Pull 2 · Garrosh · 4 %" in text


def test_without_a_pull_the_status_line_points_at_the_list(qt_app):

    service = FakeService()
    service.state = replace(service.state, selected_report="")

    view = _source_view(qt_app, service)

    assert "Raidabend" in view.status_label.text()


def test_the_live_mode_says_where_the_numbers_come_from(qt_app):

    service = FakeService()
    service.state = replace(service.state, mode=MODE_LIVE)

    view = _source_view(qt_app, service)

    assert "laufenden Log" in view.status_label.text()


def test_an_error_reaches_the_status_line(qt_app):

    service = FakeService()
    service.state = replace(service.state, fights_error="Bot nicht erreichbar")

    view = _source_view(qt_app, service)

    assert "Bot nicht erreichbar" in view.status_label.text()


def test_the_quick_selection_picks_the_last_kill(qt_app):

    service = FakeService()

    view = _source_view(qt_app, service)

    view.last_kill_button.click()

    #
    # Immerseus ist der einzige Kill der Liste.
    #

    assert ("fight", "aBcDeF12", 1) in service.calls


def test_the_quick_selection_picks_the_best_attempt(qt_app):
    """
    Ein Kill schlägt jeden Wipe - `best_try()` entscheidet das, und
    dieser Knopf zeigt dieselbe Zeile, die die Liste markiert.
    """

    service = FakeService()

    view = _source_view(qt_app, service)

    view.best_try_button.click()

    assert ("fight", "aBcDeF12", 1) in service.calls


def test_the_quick_selection_picks_the_latest_report(qt_app):

    service = FakeService()

    view = _source_view(qt_app, service)

    view.last_raid_button.click()

    #
    # zZz9 ist der Donnerstag und damit der jüngere Abend.
    #

    assert ("report", "zZz9") in service.calls


def test_a_quick_button_without_a_target_is_disabled_not_hidden(qt_app):
    """
    *lock, don't hide*: ein Knopf, der je nach Lage verschwindet, lässt
    sich weder erklären noch danach fragen.
    """

    service = FakeService()
    service.state = replace(service.state, reports=(), fights=())

    view = _source_view(qt_app, service)

    view.show()

    assert view.last_kill_button.isVisible()
    assert not view.last_kill_button.isEnabled()
    assert not view.last_raid_button.isEnabled()

    view.hide()


def test_the_mode_switch_leads_back_to_the_running_raid(qt_app):

    service = FakeService()

    view = _source_view(qt_app, service)

    view.mode_switch.setValue(MODE_LIVE)

    assert "live" in service.calls


def test_the_replay_mode_keeps_the_switch_on_archive(qt_app):
    """
    `SegmentedControl.setValue()` tut bei einem unbekannten Wert
    stillschweigend nichts - ohne die Zuordnung stünde der Schalter
    während einer Wiedergabe auf seinem alten Stand.
    """

    service = FakeService()
    service.state = replace(service.state, mode=MODE_REPLAY)

    view = _source_view(qt_app, service)

    assert view.mode_switch.value() == MODE_ARCHIVE
