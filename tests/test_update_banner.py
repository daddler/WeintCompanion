"""
Der Update-Hinweis auf der Übersicht.

Ein wartendes Update war bis 2.0.1 an drei Stellen zu **sehen**
(Systemzeile, Abzeichen, Meldungsstreifen) und an keiner davon
auszulösen: jeder Weg endete auf "Addon & Updates". Diese Karte ist
die vierte Stelle und die erste, an der man etwas tun kann.

Zwei Eigenschaften trägt sie, die leicht wieder verlorengehen und
beide sichtbar falsch aussähen:

- **Sie erscheint nur bei Handlungsbedarf.** Eine Dauerkarte "alles
  aktuell" wäre der Fehler, den die Übersicht dem Dashboard gerade
  ausgetrieben hat.
- **Sie zeigt, was kommt, nicht nur dass etwas kommt.** Der Auszug
  stammt aus derselben Quelle wie die vollständige Änderungsansicht.
"""

import os

import pytest

pytest.importorskip("PySide6")


ADDON_CHANGELOG = """
# Changelog

## [1.4.0.0] – 2026-09-01

### Neu
- Ein neuer Bericht für die Companion
- Und noch etwas

## [1.3.3.1] – 2026-08-11

### Behoben
- Etwas Altes
"""


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Logger:

    def __init__(self):
        self.lines = []

    def info(self, text=""):
        self.lines.append(("info", text))

    def warning(self, text=""):
        self.lines.append(("warning", text))

    def error(self, text=""):
        self.lines.append(("error", text))

    def success(self, text=""):
        self.lines.append(("success", text))

    def entries(self):
        return []


class _State:

    def __init__(self):
        self.addon_found = True
        self.addon_path = None
        self.addon_version = "1.3.3.1"
        self.github_version = "v1.4.0.0"
        self.github_changelog = ""
        self.update_available = False
        self.companion_version = "2.0.1"
        self.companion_latest_version = "2.0.1"
        self.companion_update_available = False
        self.companion_changelog = None
        self.discord_connected = True
        self.discord_name = "Tester"
        self.wow_found = True


class _Service:

    def history(self):
        return []


class _Manager:

    def __init__(self, config):
        self.state = _State()
        self.config = config
        self.logger = _Logger()
        self.raid_data = _Service()
        self.characters = None
        self.discord_account = None
        self.raid_schedule_sync = None
        self.installs = 0
        self.companion_updates = 0

    #
    # Was der Läufer anfasst - mehr braucht die Karte nicht.
    #

    def install_or_update(self):
        self.installs += 1

    def stop_auto_sync(self):
        pass

    def start_auto_sync(self):
        pass


@pytest.fixture
def page(tmp_path):

    _app()

    from core.config import Config
    from gui.theme.theme_manager import init_theme

    config = Config()

    init_theme(config)

    (tmp_path / "CHANGELOG.md").write_text(
        ADDON_CHANGELOG, encoding="utf-8",
    )

    from gui.pages.overview import OverviewPage

    manager = _Manager(config)

    manager.state.addon_path = tmp_path

    widget = OverviewPage(manager)

    yield widget

    widget.close()


# --------------------------------------------------


def test_no_update_no_card(page):

    page.refresh()

    assert not page.updates.isVisibleTo(page)


def test_an_addon_update_shows_the_card_with_its_notes(page):

    page.manager.state.update_available = True

    page.refresh()

    assert page.updates.isVisibleTo(page)

    assert page.updates.chip.text() == "1 UPDATE"

    row = page.updates.rows["addon"]

    assert row.isVisibleTo(page.updates)

    assert "WeintCodex" in row.title.text()

    assert "1.4.0.0" in row.title.text()

    #
    # Der Auszug stammt aus der CHANGELOG.md des Addon-Ordners - und
    # zwar aus der angebotenen Fassung, nicht aus der installierten.
    #

    assert "Ein neuer Bericht" in row.excerpt.text()

    assert "Etwas Altes" not in row.excerpt.text()

    #
    # Die Companion-Zeile bleibt weg, solange dort nichts ansteht.
    #

    assert not page.updates.rows["companion"].isVisibleTo(page.updates)


def test_both_channels_count_up(page):

    page.manager.state.update_available = True

    page.manager.state.companion_update_available = True

    page.manager.state.companion_latest_version = "2.1.0"

    page.refresh()

    assert page.updates.chip.text() == "2 UPDATES"

    assert page.updates.rows["addon"].isVisibleTo(page.updates)

    assert page.updates.rows["companion"].isVisibleTo(page.updates)


def test_the_card_disappears_again(page):

    page.manager.state.update_available = True

    page.refresh()

    assert page.updates.isVisibleTo(page)

    page.manager.state.update_available = False

    page.refresh()

    assert not page.updates.isVisibleTo(page)


def test_the_button_really_installs(page):

    from gui.controllers.update_runner import UpdateRunner

    page.manager.state.update_available = True

    page.refresh()

    page.set_update_runner(UpdateRunner(page.manager))

    page.updates.rows["addon"].install.click()

    assert page.manager.installs == 1


def test_without_a_runner_the_button_is_quiet_rather_than_broken(page):
    """
    Die Seite kann vor dem MainWindow entstehen (und tut es in Tests).
    Ein Klick darf dann nichts tun - und vor allem keine Ausnahme in
    einem Qt-Slot auslösen, wo sie schwer zu verfolgen wäre.
    """

    page.manager.state.update_available = True

    page.refresh()

    page.updates.rows["addon"].install.click()

    assert page.manager.installs == 0


def test_a_failed_install_says_so_and_frees_the_button(page):

    from gui.controllers.update_runner import UpdateRunner

    def explode():
        raise RuntimeError("Prüfsumme stimmt nicht")

    page.manager.install_or_update = explode

    page.manager.state.update_available = True

    page.refresh()

    page.set_update_runner(UpdateRunner(page.manager))

    row = page.updates.rows["addon"]

    row.install.click()

    assert row.install.isEnabled()

    assert "Prüfsumme stimmt nicht" in row.excerpt.text()


def test_a_missing_changelog_says_so_instead_of_nothing(page):
    """
    Eine leere Fläche unter "Update verfügbar" liest sich wie ein
    Ladefehler.
    """

    page.manager.state.addon_path = None

    page.manager.state.update_available = True

    page.refresh()

    assert page.updates.rows["addon"].excerpt.text().strip()
