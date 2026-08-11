"""
Die beiden Schnellzugriffe, die der 2.0-Umbau verloren hat.

Bis 1.7 sass auf dem Dashboard eine Reihe mit drei Knöpfen:
"Addon-Ordner öffnen", "WoW starten" und "Jetzt synchronisieren".
Das Dashboard ist in 2.0 der Übersicht gewichen - synchronisiert wird
seitdem auf der Seite "Verbindungen", die anderen beiden hat der Umbau
unterschiedlich schlecht überlebt.

**"WoW starten" startete nichts mehr.** Der Knopf ist auf die
Übersicht mitgewandert, rief dort aber `manager.launcher.launch()`
auf. `Launcher` ist der Dateistarter des Selbstupdates und verlangt
einen Pfad (`launch(self, file)`); ohne Argument wirft der Aufruf
einen `TypeError`. Darunter stand ein `except Exception`, das für den
Linux-Fall "noch kein Startbefehl hinterlegt" gedacht war - der
`TypeError` lief also genau dort hinein, und der Knopf landete auf
jedem Betriebssystem stillschweigend in den Einstellungen, statt das
Spiel zu starten. Battle.net startet der `BattleNetLauncher`, erreichbar
über `manager.start_wow()`.

**"Addon-Ordner öffnen" fiel ganz weg.** `core.platform.open_folder()`
hatte danach keinen einzigen Aufrufer mehr. Der Knopf sitzt jetzt auf
"Addon & Updates", wo die Installation selbst steht.

Beide Methoden lesen nur `self.manager` und ihre eigenen Signale -
sie werden deshalb an einem Stellvertreter geprüft, ohne die ganze
Seite zu bauen (nichts sonst in `tests/` baut ein Widget dafür).
"""

import pytest

pytest.importorskip("PySide6")


class _Logger:

    def __init__(self):
        self.warnings = []
        self.errors = []

    def info(self, *a):
        pass

    def success(self, *a):
        pass

    def warning(self, *a):
        self.warnings.append(a[0] if a else "")

    def error(self, *a):
        self.errors.append(a[0] if a else "")


class _Config:

    def __init__(self, launch_command=""):
        self._launch_command = launch_command

    def get_linux_launch_command(self):
        return self._launch_command


class _State:

    def __init__(self, addon_found=True, addon_path="/wow/Interface/AddOns"):
        self.addon_found = addon_found
        self.addon_path = addon_path
        self.wow_path = "/wow/_classic_"


class _Manager:

    def __init__(self, launch_command="", addon_found=True):
        self.config = _Config(launch_command)
        self.logger = _Logger()
        self.state = _State(addon_found=addon_found)
        self.started = 0

    def start_wow(self):
        self.started += 1


class _Signal:
    """Nimmt auf, was emittiert wurde."""

    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


class _Page:
    """
    Stellvertreter für die Seite: genau die Attribute, welche die
    beiden Methoden anfassen.
    """

    def __init__(self, manager):
        self.manager = manager
        self.openSettingsSection = _Signal()


# --------------------------------------------------
# "WoW starten"
# --------------------------------------------------


def _launch(manager, linux: bool, monkeypatch):

    from gui.pages import overview

    monkeypatch.setattr(overview, "is_linux", lambda: linux)

    page = _Page(manager)

    overview.OverviewPage._launch_wow(page)

    return page


def test_starting_wow_really_starts_wow(monkeypatch):
    """
    Der Kern der Regression: der Knopf muss den Battle.net-Starter
    erreichen. Vorher kam hier eine 0 heraus, weil der `TypeError`
    schon vor dem Start abgebogen ist.
    """

    manager = _Manager()

    page = _launch(manager, linux=False, monkeypatch=monkeypatch)

    assert manager.started == 1

    assert page.openSettingsSection.emitted == []


def test_on_linux_a_launch_command_is_all_it_takes(monkeypatch):
    """
    Mit hinterlegtem Startbefehl gilt unter Linux dasselbe.
    """

    manager = _Manager(launch_command="flatpak run net.lutris.Lutris")

    page = _launch(manager, linux=True, monkeypatch=monkeypatch)

    assert manager.started == 1

    assert page.openSettingsSection.emitted == []


def test_on_linux_without_a_command_the_settings_are_the_next_step(
    monkeypatch,
):
    """
    Der einzige Fall, in dem der Knopf NICHT starten darf - und der
    Grund, aus dem es das `except Exception` überhaupt gab. Er muss
    erhalten bleiben, aber als ausdrückliche Prüfung statt als
    verschluckter Fehler: sonst ist er von einem echten Defekt nicht
    zu unterscheiden.
    """

    manager = _Manager(launch_command="")

    page = _launch(manager, linux=True, monkeypatch=monkeypatch)

    assert manager.started == 0

    assert page.openSettingsSection.emitted == ["wow_client"]

    assert manager.logger.warnings


# --------------------------------------------------
# "Addon-Ordner öffnen"
# --------------------------------------------------


def test_the_addon_folder_can_be_opened_again(monkeypatch):

    from gui.pages import addon

    opened = []

    monkeypatch.setattr(addon, "open_folder", opened.append)

    manager = _Manager(addon_found=True)

    addon.AddonPage.open_addon_folder(_Page(manager))

    assert opened == ["/wow/Interface/AddOns"]


def test_without_an_installation_nothing_is_opened(monkeypatch):
    """
    Ohne Installation gibt es keinen Ordner - der Dateimanager darf
    dann nicht mit einem leeren Pfad aufgerufen werden.
    """

    from gui.pages import addon

    opened = []

    monkeypatch.setattr(addon, "open_folder", opened.append)

    manager = _Manager(addon_found=False)

    addon.AddonPage.open_addon_folder(_Page(manager))

    assert opened == []

    assert manager.logger.errors


# --------------------------------------------------
# Die Verdrahtung
# --------------------------------------------------


def test_both_buttons_are_actually_connected():
    """
    Die Methoden oben sind nur dann etwas wert, wenn ein Knopf sie
    auch auslöst - genau daran ist "Addon-Ordner öffnen" gescheitert:
    `open_folder()` war vorhanden und hatte null Aufrufer.
    """

    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent

    for module, handler in (
        ("gui/pages/overview.py", "_launch_wow"),
        ("gui/pages/addon.py", "open_addon_folder"),
    ):

        tree = ast.parse((root / module).read_text(encoding="utf-8"))

        connected = any(
            isinstance(node, ast.Attribute)
            and node.attr == handler
            for node in ast.walk(tree)
        )

        assert connected, f"{module}: {handler} ist an keinen Knopf gehängt"
