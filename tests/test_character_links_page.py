"""
Die Raidwahl auf der Seite "Charakterzuordnung".

Gemeldet wurde: "Zur Zeit haben wir einen 25er Raid offen, spaeter
wurde noch ein seperater 10er Raid geoeffnet. Ich kann jetzt nur den
10er Raid per Charakterzuordnung bearbeiten."

Drei Dinge werden deshalb hier festgehalten, alle drei am Fenster und
nicht am Client:

* bei zwei laufenden Raids erscheint die Auswahl,
* bei einem einzigen erscheint sie nicht (es gaebe nichts zu waehlen),
* und ein Wechsel fragt wirklich den anderen Raid ab.
"""

import os

import pytest

pytest.importorskip("PySide6")

from core.character_links import Overview
from core.raid_schedule import parse_schedule


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Logger:

    def info(self, *a):
        pass

    def error(self, *a):
        pass

    def success(self, *a):
        pass

    def warning(self, *a):
        pass


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


class _Sync:

    def __init__(self, schedule):

        self.schedule = schedule

        self.invalidated = 0

    def invalidate(self):

        self.invalidated += 1


class _Manager:

    def __init__(self, schedule):

        self.logger = _Logger()

        self.config = _Config()

        self.raid_schedule_sync = _Sync(schedule)


def _schedule(*raids):
    """
    Ein Termin mit `raids` gleichzeitig laufenden Anmeldungen, der
    erste als Hauptteil und der Rest als `others` - genau die Form,
    in der der Bot antwortet.
    """

    first, *rest = raids

    return parse_schedule({
        "status": "ok",
        "days": [],
        **first,
        "others": [{**entry, "days": []} for entry in rest],
    })


ZEHNER = {"raid_id": 8, "title": "10er Mains", "raid_size": 10}

FUENFUNDZWANZIGER = {"raid_id": 7, "title": "25er Twinks", "raid_size": 25}


@pytest.fixture
def page(monkeypatch):

    from gui.theme.theme_manager import init_theme

    _app()

    init_theme(_Config())

    #
    # Kein Netz im Test: der Abruf laeuft ohnehin in einem Thread, und
    # was hier geprueft wird, ist die Frage - nicht die Antwort.
    #

    fragen = []

    def fetch(self, raid_id=None):

        fragen.append(raid_id)

        return Overview(raid_id=raid_id or 8)

    import core.character_links_client as client_module

    monkeypatch.setattr(
        client_module.CharacterLinksClient, "fetch", fetch
    )

    from gui.pages.character_links import CharacterLinksPage

    widget = CharacterLinksPage(
        _Manager(_schedule(ZEHNER, FUENFUNDZWANZIGER))
    )

    widget.fragen = fragen

    return widget


def test_zwei_laufende_raids_ergeben_eine_auswahl(page):

    page._sync_raids()

    assert page.raids.isVisibleTo(page)

    beschriftungen = [
        page.raids.itemText(index)
        for index in range(page.raids.count())
    ]

    assert any("10er Mains" in text for text in beschriftungen)

    assert any("25er Twinks" in text for text in beschriftungen)


def test_ein_einziger_raid_zeigt_keine_auswahl(monkeypatch, page):

    page.manager.raid_schedule_sync.schedule = _schedule(ZEHNER)

    page._sync_raids()

    assert not page.raids.isVisibleTo(page)


def test_der_wechsel_fragt_den_anderen_raid_ab(page):

    page._sync_raids()

    page.fragen.clear()

    index = next(
        i for i in range(page.raids.count())
        if page.raids.itemData(i) == 7
    )

    page.raids.setCurrentIndex(index)

    if page._thread is not None:
        page._thread.join(timeout=5)

    assert page._raid_id == 7

    assert page.fragen == [7]


def test_ohne_eigene_wahl_gilt_die_antwort_des_bots(page):
    """
    Der Auswahlkasten darf nicht auf dem ersten Eintrag stehen, waehrend
    die Liste zu einem anderen Raid gehoert.
    """

    page._overview = Overview(raid_id=7)

    page._on_loaded()

    assert page._raid_id == 7
