"""
Der Archivbrowser und die Quellenzeile.

Diese Datei baut Widgets - wie die fünf anderen unter `tests/`, und
aus demselben Grund: die Fehler, um die es hier geht, sind von aussen
unsichtbar. Eine Liste, die sich beim Laden selbst leert, ein Fenster,
das sich in der Sekunde schliesst, in der es aufgeht, und ein Klick,
der beim falschen Dienst landet, werfen alle keine Ausnahme.

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
    Der Browser selbst - seit 3.5.0 ein Widget, das sowohl in der
    Archiv-Seite steckt als auch im Fenster darum. Geprueft wird
    deshalb er und nicht der Rahmen; fuer die zwei Regeln, die wirklich
    zum Fenster gehoeren, gibt es `_dialog()` daneben.
    """

    from gui.dialogs.archive_dialog import ArchiveBrowser

    return ArchiveBrowser(service)


def _dialog(qt_app, service):

    from gui.dialogs.archive_dialog import ArchiveDialog

    return ArchiveDialog(service)


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


def test_the_window_stays_open_while_the_pull_is_still_loading(qt_app):
    """
    Der einzelne Pull kostet den Bot Minuten. Ein Fenster, das sich
    beim Klick schliesst, lässt den Nutzer vor einer Seite stehen, die
    sich aus unerfindlichen Gründen nicht ändert.
    """

    service = FakeService()

    dialog = _dialog(qt_app, service)

    service.select_archive_fight = lambda code, fight_id: None

    dialog.browser._awaiting = 3

    service.state = replace(service.state, selected_fight=3, fight_loading=True)

    dialog.browser._refresh()

    assert dialog.result() == 0
    assert dialog.browser._awaiting == 3


def test_an_error_does_not_close_the_window_over_its_own_message(qt_app):

    service = FakeService()

    browser = _browser(qt_app, service)

    browser._awaiting = 3

    service.state = replace(
        service.state,
        selected_fight=3,
        fight_error="Bot nicht erreichbar",
    )

    browser._refresh()

    assert browser._awaiting is None
    assert "Bot nicht erreichbar" in browser.status.text()


def test_a_pull_selected_before_the_window_opened_does_not_close_it(qt_app):
    """
    Beim Öffnen ist meist noch der Pull von vorhin gewählt und längst
    geladen. Ohne den Merker schlösse sich das Fenster in der Sekunde,
    in der es aufgeht.
    """

    service = FakeService(selected_fight=3)

    dialog = _dialog(qt_app, service)

    assert dialog.browser._awaiting is None
    assert dialog.result() == 0


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
# Quellenzeile
# --------------------------------------------------


def _picker(qt_app, service):

    from gui.widgets.tv.archive_picker import ArchivePicker

    return ArchivePicker(service)


def test_the_source_line_names_the_loaded_pull(qt_app):

    picker = _picker(qt_app, FakeService(selected_fight=3))

    text = picker.status_label.text()

    assert text.startswith("Mittwoch, ")
    assert "Pull 2 · Garrosh · 4 %" in text


def test_without_a_pull_the_source_line_points_at_the_browser(qt_app):

    service = FakeService()
    service.state = replace(service.state, selected_report="")

    picker = _picker(qt_app, service)

    assert "Log w" in picker.status_label.text()


def test_the_live_mode_leaves_the_source_line_to_the_page_header(qt_app):

    service = FakeService()
    service.state = replace(service.state, mode=MODE_LIVE)

    picker = _picker(qt_app, service)

    assert picker.status_label.text() == ""


def test_an_error_reaches_the_source_line(qt_app):

    service = FakeService()
    service.state = replace(service.state, fights_error="Bot nicht erreichbar")

    picker = _picker(qt_app, service)

    assert "Bot nicht erreichbar" in picker.status_label.text()


def test_the_browse_button_stays_available_in_live_mode(qt_app):
    """
    *lock, don't hide*: "einen vergangenen Pull ansehen" ist eine
    Absicht, kein Zustand.
    """

    service = FakeService()
    service.state = replace(service.state, mode=MODE_LIVE)

    picker = _picker(qt_app, service)

    assert picker.browse_button.isEnabled()


def test_the_play_button_hides_during_playback(qt_app):

    service = FakeService()
    service.state = replace(service.state, mode=MODE_REPLAY)
    service._available = True

    picker = _picker(qt_app, service)

    picker.show()

    assert not picker.play_button.isVisible()

    picker.hide()
