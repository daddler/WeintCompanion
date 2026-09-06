"""
Ein Update, das scheitert, muss das auch sagen.

Gemeldet wurde: „Update lässt sich nicht installieren, bei *Jetzt
aktualisieren* startet der Download normal, bricht dann aber einfach
wieder ab." Im Protokoll standen zwei Zeilen direkt untereinander:

    ERROR   Installation fehlgeschlagen: [WinError 5] Zugriff verweigert
    SUCCESS Addon erfolgreich aktualisiert.

Zwei Fehler in einem Bild, und beide werden hier festgehalten:

1. `install_or_update()` **wirft nicht**, es gibt einen
   `WorkflowResult` zurück. Der Läufer warf ihn weg und meldete Erfolg,
   sobald keine Ausnahme flog. Die Update-Karte zeigte weiter dieselbe
   Fassung, und der nächste Klick führte in dieselbe Runde.
2. `[WinError 5] Zugriff verweigert` nennt keinen nächsten Schritt -
   und zwei völlig verschiedene Ursachen erzeugen ihn.
"""

from __future__ import annotations

import ast
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest

from core.install_errors import (
    InstallPermissionError,
    in_protected_location,
    is_permission_error,
    permission_message,
    probe_writable,
    translate,
)
from core.installer import Installer
from core.installer_workflow import InstallerWorkflow
from core.workflow_result import WorkflowResult


# ==========================================================
# Die Übersetzung
# ==========================================================


def test_a_windows_access_error_is_recognised():
    """
    Erkannt wird über `errno` und den Text, nicht über die Klasse:
    `shutil` und `zipfile` verpacken denselben Fehler verschieden.
    """

    assert is_permission_error(PermissionError(13, "Permission denied"))

    assert is_permission_error(
        OSError(13, "Zugriff verweigert", "C:\\Program Files")
    )

    #
    # Windows meldet den Fehler als Text; die deutsche Fassung ist
    # genau die aus dem Bericht.
    #

    assert is_permission_error(
        RuntimeError("[WinError 5] Zugriff verweigert: 'C:\\\\...'")
    )

    #
    # Und die Ursachenkette zählt mit - eine Ausnahme, die eine andere
    # ausgelöst hat, kommt bei uns verpackt an.
    #

    wrapped = RuntimeError("Kopieren fehlgeschlagen")
    wrapped.__cause__ = PermissionError(13, "Permission denied")

    assert is_permission_error(wrapped)


def test_an_unrelated_error_is_left_alone():
    """
    Ein erfundener Rat zu einem Fehler, den wir nicht verstanden
    haben, ist schlechter als die rohe Meldung.
    """

    assert not is_permission_error(OSError(28, "No space left on device"))

    original = FileNotFoundError("WeintCodex.toc")

    assert translate(
        original, "C:\\WoW", folder_writable=True
    ) is original


def test_the_two_causes_get_two_different_sentences():
    """
    Der Unterschied entscheidet, was zu tun ist: einmal WoW beenden,
    einmal als Administrator starten. Ein gemeinsamer Satz wäre für
    einen der beiden Fälle falsch.
    """

    path = "C:\\Program Files (x86)\\World of Warcraft\\_classic_"

    #
    # Schreiben geht, Ersetzen nicht: jemand hält den Ordner offen.
    #

    in_use = permission_message(path, folder_writable=True)

    assert "Warcraft" in in_use
    assert "Administrator" not in in_use

    #
    # Schreiben geht gar nicht: die Rechte.
    #

    denied = permission_message(path, folder_writable=False)

    assert "Administrator" in denied
    assert "Program Files" in denied


def test_a_folder_outside_program_files_gets_the_general_advice():

    denied = permission_message("D:\\Spiele\\WoW", folder_writable=False)

    assert "Administrator" in denied
    assert "Program Files" not in denied


def test_protected_location_is_case_insensitive_and_slash_agnostic():

    assert in_protected_location("C:/Program Files (x86)/World of Warcraft")
    assert in_protected_location("c:\\PROGRAM FILES\\wow")

    assert not in_protected_location("D:\\Games\\World of Warcraft")


def test_translate_produces_the_ready_made_sentence():

    raw = PermissionError(13, "Zugriff verweigert")

    better = translate(
        raw, "C:\\Program Files\\WoW", folder_writable=False
    )

    assert isinstance(better, InstallPermissionError)

    #
    # Sie erbt von PermissionError, damit bestehende
    # `except OSError`-Zweige sie weiterhin fangen.
    #

    assert isinstance(better, OSError)

    assert "Administrator" in str(better)


# ==========================================================
# Die Probe
# ==========================================================


def test_probe_says_yes_for_an_ordinary_folder(tmp_path):

    assert probe_writable(tmp_path) is True

    #
    # Und sie räumt hinter sich auf.
    #

    assert list(tmp_path.iterdir()) == []


def test_probe_walks_up_to_the_nearest_existing_folder(tmp_path):
    """
    Bei einer Neuinstallation gibt es `Interface/AddOns` womöglich noch
    gar nicht - und angelegt werden müsste er dann ebenfalls dort, wo
    die Rechte fehlen.
    """

    assert probe_writable(tmp_path / "Interface" / "AddOns") is True


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="Ein schreibgeschützter Ordner ist unter Windows und als root "
           "keine Aussage über Rechte.",
)
def test_probe_says_no_for_a_read_only_folder(tmp_path):

    folder = tmp_path / "AddOns"

    folder.mkdir()

    folder.chmod(stat.S_IRUSR | stat.S_IXUSR)

    try:
        assert probe_writable(folder) is False

    finally:
        folder.chmod(stat.S_IRWXU)


# ==========================================================
# Der Installer
# ==========================================================


def _make_zip(tmp_path):

    zip_path = tmp_path / "WeintCodex.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("WeintCodex/WeintCodex.toc", "## Interface: 50504\n")
        archive.writestr("WeintCodex/new.txt", "content")

    return zip_path


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="Ein schreibgeschützter Ordner ist unter Windows und als root "
           "keine Aussage über Rechte.",
)
def test_installer_names_the_cause_instead_of_passing_winerror_through(tmp_path):

    addons = tmp_path / "WoW" / "Interface" / "AddOns"

    addons.mkdir(parents=True)

    addon_path = addons / "WeintCodex"

    zip_path = _make_zip(tmp_path)

    addons.chmod(stat.S_IRUSR | stat.S_IXUSR)

    try:

        with pytest.raises(InstallPermissionError) as caught:
            Installer().install(zip_path, addon_path)

        assert "Administrator" in str(caught.value)

    finally:
        addons.chmod(stat.S_IRWXU)


# ==========================================================
# Der Ablauf
# ==========================================================


class _Logger:

    def __init__(self):
        self.lines: list[tuple[str, str]] = []

    def info(self, text):
        self.lines.append(("info", text))

    def success(self, text):
        self.lines.append(("success", text))

    def warning(self, text):
        self.lines.append(("warn", text))

    def error(self, text):
        self.lines.append(("error", text))

    def levels(self):
        return [level for level, _ in self.lines]


class _State:

    def __init__(self, addon_path):
        self.addon_path = Path(addon_path)
        self.wow_path = self.addon_path.parents[2]
        self.addon_found = True
        self.github_download_url = "https://example.invalid/WeintCodex.zip"
        self.github_asset_name = "WeintCodex.zip"
        self.github_version = "3.0.0.0"
        self.github_sha256 = ""


class _Downloader:

    def __init__(self):
        self.calls = 0

    def download(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Es darf gar nicht erst geladen werden.")


class _Manager:

    def __init__(self, addon_path):
        self.state = _State(addon_path)
        self.logger = _Logger()
        self.downloader = _Downloader()


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="Ein schreibgeschützter Ordner ist unter Windows und als root "
           "keine Aussage über Rechte.",
)
def test_workflow_refuses_before_downloading_five_megabytes(tmp_path):
    """
    „Der Download startet normal, bricht dann aber einfach wieder ab" -
    genau so sah es aus. Das Recht stand vorher fest.
    """

    addons = tmp_path / "WoW" / "Interface" / "AddOns"

    addons.mkdir(parents=True)

    manager = _Manager(addons / "WeintCodex")

    addons.chmod(stat.S_IRUSR | stat.S_IXUSR)

    try:
        result = InstallerWorkflow(manager).run()

    finally:
        addons.chmod(stat.S_IRWXU)

    assert result.success is False

    assert "Administrator" in result.message

    assert manager.downloader.calls == 0

    #
    # Und keine Erfolgszeile im Protokoll.
    #

    assert "success" not in manager.logger.levels()


def test_installer_translates_a_denied_copy(tmp_path, monkeypatch):
    """
    Dieselbe Prüfung ohne Rechtespiel im Dateisystem - damit sie auch
    unter Windows und als root läuft, wo ein schreibgeschützter Ordner
    keine Aussage über Rechte ist.
    """

    import core.installer as installer_module

    addons = tmp_path / "WoW" / "Interface" / "AddOns"

    addons.mkdir(parents=True)

    zip_path = _make_zip(tmp_path)

    monkeypatch.setattr(
        installer_module, "probe_writable", lambda _path: False
    )

    def _denied(*args, **kwargs):
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(installer_module.shutil, "copytree", _denied)

    with pytest.raises(InstallPermissionError) as caught:
        Installer().install(zip_path, addons / "WeintCodex")

    assert "Administrator" in str(caught.value)


def test_installer_blames_an_open_folder_when_writing_works(tmp_path, monkeypatch):
    """
    Der zweite Fall: anlegen geht, den bestehenden Ordner ersetzen
    nicht. Unter Windows ist das WoW, das noch läuft - und der Rat
    „als Administrator starten" wäre dort schlicht falsch.
    """

    import core.installer as installer_module

    addon_path = tmp_path / "WoW" / "Interface" / "AddOns" / "WeintCodex"

    addon_path.mkdir(parents=True)

    (addon_path / "old.txt").write_text("alt", encoding="utf-8")

    zip_path = _make_zip(tmp_path)

    real_rename = installer_module.os.rename

    def _denied(src, dst):

        if Path(src) == addon_path:
            raise PermissionError(13, "Zugriff verweigert")

        return real_rename(src, dst)

    monkeypatch.setattr(installer_module.os, "rename", _denied)

    with pytest.raises(InstallPermissionError) as caught:
        Installer().install(zip_path, addon_path)

    message = str(caught.value)

    assert "Warcraft" in message
    assert "Administrator" not in message

    #
    # Und die alte Fassung steht noch.
    #

    assert (addon_path / "old.txt").exists()


def test_workflow_refuses_when_the_probe_says_no(tmp_path, monkeypatch):

    import core.installer_workflow as workflow_module

    addons = tmp_path / "WoW" / "Interface" / "AddOns"

    addons.mkdir(parents=True)

    manager = _Manager(addons / "WeintCodex")

    monkeypatch.setattr(
        workflow_module, "probe_writable", lambda _path: False
    )

    result = InstallerWorkflow(manager).run()

    assert result.success is False

    assert "Administrator" in result.message

    assert manager.downloader.calls == 0

    assert "success" not in manager.logger.levels()


# ==========================================================
# Der Läufer
# ==========================================================


class _RunnerManager:

    def __init__(self, result):
        self._result = result
        self.logger = _Logger()
        self.state = type("S", (), {"addon_found": True})()

    def install_or_update(self):
        return self._result


def _runner(result):

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    QApplication.instance() or QApplication([])

    from gui.controllers.update_runner import UpdateRunner

    manager = _RunnerManager(result)

    runner = UpdateRunner(manager)

    seen: list[tuple] = []

    runner.finished.connect(
        lambda component, success, message: seen.append(
            (component, success, message)
        )
    )

    runner.install_addon()

    return manager, seen


def test_a_failed_install_is_never_reported_as_success():
    """
    Der gemeldete Fall: ERROR und unmittelbar darunter SUCCESS.
    """

    manager, seen = _runner(
        WorkflowResult(success=False, message="Kein Schreibrecht auf …")
    )

    assert seen and seen[0][1] is False

    assert seen[0][2] == "Kein Schreibrecht auf …"

    assert "success" not in manager.logger.levels()

    #
    # Und der Läufer ist danach wieder frei - sonst wäre der zweite
    # Versuch ein toter Knopf.
    #

    assert manager is not None


def test_a_successful_install_still_says_so():

    manager, seen = _runner(
        WorkflowResult(success=True, message="Installation erfolgreich.")
    )

    assert seen and seen[0][1] is True

    assert "success" in manager.logger.levels()


def test_a_caller_without_a_result_is_treated_as_success():
    """
    Ein Aufrufer, der `None` zurückgibt (ältere Attrappen, Tests), darf
    keinen Absturz erzeugen - das wäre der zweite Fehler nach dem
    ersten.
    """

    _, seen = _runner(None)

    assert seen and seen[0][1] is True


# ==========================================================
# Und niemand darf das Ergebnis wieder wegwerfen
# ==========================================================


def test_nobody_ignores_the_result_of_install_or_update():
    """
    Der Fehler stand an **zwei** Stellen (Läufer und Einrichtung), und
    genau deshalb steht diese Prüfung hier: eine Regel, die an einer
    von zwei Stellen gilt, ist keine Regel.

    Geprüft wird strukturell - ein Aufruf von `install_or_update()`
    muss zugewiesen, zurückgegeben oder in einem Ausdruck verwendet
    werden, nie als blosse Anweisung dastehen.
    """

    root = Path(__file__).resolve().parent.parent

    offenders: list[str] = []

    for path in list((root / "gui").rglob("*.py")) + list(
        (root / "core").rglob("*.py")
    ):

        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):

            if not isinstance(node, ast.Expr):
                continue

            call = node.value

            if not isinstance(call, ast.Call):
                continue

            func = call.func

            if (
                isinstance(func, ast.Attribute)
                and func.attr == "install_or_update"
            ):
                offenders.append(f"{path.name}:{node.lineno}")

    assert not offenders, offenders
