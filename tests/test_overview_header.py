"""
Der Kopf der Übersicht: Begrüßung und "Erneut prüfen".

Zwei Dinge werden hier geprüft, und beide sind an der Seite und nicht
an `core/greeting.py` zu prüfen, weil sie erst dort zusammenkommen:

**Die Begrüßung muss den Zustand lesen, den sie behauptet.** Der Satz
selbst entsteht in `core/greeting.py` (dort ohne Fenster geprüft);
hier geht es darum, dass die Seite ihm den richtigen Namen und den
richtigen Termin reicht - und dass sie ihn überhaupt setzt, statt bei
"Willkommen zurück." stehen zu bleiben.

**Der Prüfknopf darf den Hauptthread nicht anhalten.** Die Prüfung
geht zweimal ins Netz. Steht sie im Klick-Handler, friert das Fenster
für ihre Dauer ein - derselbe Fehler, den `ConnectionsPage.refresh()`
einmal hatte (siehe `tests/test_update_visibility.py`). Geprüft wird
deshalb, dass die Prüfung in einem anderen Thread läuft und der Knopf
danach von selbst wieder benutzbar ist.
"""

import os
import threading

import pytest

pytest.importorskip("PySide6")


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def _pump(ms: int = 200):

    from PySide6.QtCore import QDeadlineTimer, QEventLoop

    app = _app()

    deadline = QDeadlineTimer(ms)

    while not deadline.hasExpired():
        app.processEvents(QEventLoop.AllEvents, 4)


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
        self.github_version = "1.3.3.1"
        self.github_changelog = ""
        self.update_available = False
        self.companion_version = "2.0.8"
        self.companion_latest_version = "2.0.8"
        self.companion_update_available = False
        self.companion_changelog = None
        self.discord_connected = True
        self.discord_name = "daddler"
        self.wow_found = True


class _Service:

    def history(self):
        return []


class _ScheduleSync:

    def __init__(self, schedule=None):
        self.schedule = schedule


class _Manager:

    def __init__(self, config):
        self.state = _State()
        self.config = config
        self.logger = _Logger()
        self.raid_data = _Service()
        self.characters = None
        self.discord_account = None
        self.raid_schedule_sync = None
        self.checks = []

    def refresh_update_status(self):

        #
        # Wer ruft - genau das ist die Frage. Ein Eintrag mit
        # "MainThread" wäre der eingefrorene Klick-Handler.
        #

        self.checks.append(threading.current_thread().name)


@pytest.fixture
def page():

    _app()

    from core.config import Config
    from gui.theme.theme_manager import init_theme

    config = Config()

    init_theme(config)

    from gui.pages.overview import OverviewPage

    #
    # Der eigene Charakter wird ausdrücklich geleert: `Config()` liest
    # die echte Konfiguration dieses Rechners, und ein dort
    # hinterlegter Name würde die Begrüßung der Tests mitbestimmen.
    #

    config.data["academy_ingame_character"] = ""

    widget = OverviewPage(_Manager(config))

    yield widget

    widget.close()


# --------------------------------------------------
# Begrüßung
# --------------------------------------------------


def test_the_eyebrow_greets_by_daytime(page):

    from core.greeting import daypart

    page.refresh()

    assert page.header.eyebrow.text().startswith(daypart())


def test_the_ingame_character_is_the_name_we_greet(page):
    """
    Der angemeldete Charakter ist die einzige Antwort auf "wer bin
    ich", die niemand geraten hat - `academy_player_name` kann auf
    einem Kollegen stehen (siehe `analyzer/names.py`).
    """

    page.manager.config.data["academy_ingame_character"] = "Krallenwut"

    page.manager.config.data["academy_player_name"] = "Feuerbrand"

    page.refresh()

    assert page.header.eyebrow.text().endswith(", Krallenwut")


def test_without_a_known_character_the_discord_name_stands_in(page):

    page.manager.config.data["academy_ingame_character"] = ""

    page.refresh()

    assert page.header.eyebrow.text().endswith(", daddler")


def test_an_unknown_name_is_not_invented(page):

    page.manager.config.data["academy_ingame_character"] = ""

    page.manager.state.discord_name = "-"

    page.refresh()

    assert "," not in page.header.eyebrow.text()


def test_the_title_names_the_next_raid(page):

    from datetime import datetime, timedelta

    from core.raid_schedule import RaidDay, RaidSchedule

    #
    # Morgen um dieselbe Uhrzeit - der Fall, wegen dem die Begrüßung
    # überhaupt gebaut wurde: "in 1 T 3 STD" im Chip sagt nicht, dass
    # morgen Raid ist.
    #

    starts_at = (
        datetime.now().astimezone() + timedelta(days=1)
    ).replace(microsecond=0)

    day = RaidDay(key="wed", label="Mittwoch", starts_at=starts_at)

    page.manager.raid_schedule_sync = _ScheduleSync(
        RaidSchedule(known=True, title="Schlacht um Orgrimmar", days=(day,))
    )

    page.refresh()

    assert page.header.title.text().startswith("Morgen um ")

    assert page.header.title.text().endswith("Uhr ist Raid.")


def test_without_a_date_the_old_sentence_stands(page):

    page.refresh()

    assert page.header.title.text() == "Alles bereit für den nächsten Raid."


# --------------------------------------------------
# "Erneut prüfen"
# --------------------------------------------------


def test_the_check_runs_off_the_main_thread(page):

    page.check_updates()

    _pump(400)

    assert page.manager.checks, "Die Prüfung wurde gar nicht angestoßen."

    assert page.manager.checks[0] != "MainThread"

    #
    # Und der Knopf ist danach wieder benutzbar - sonst bliebe er für
    # den Rest der Sitzung gesperrt.
    #

    assert page.check_button.isEnabled()

    assert page.check_button.text() == "Erneut prüfen"


def test_two_clicks_do_not_start_two_rounds(page):

    started = threading.Event()

    release = threading.Event()

    def slow():

        started.set()

        release.wait(2)

        page.manager.checks.append("slow")

    page.manager.refresh_update_status = slow

    page.check_updates()

    started.wait(2)

    assert not page.check_button.isEnabled()

    page.check_updates()

    release.set()

    _pump(400)

    assert page.manager.checks == ["slow"]
