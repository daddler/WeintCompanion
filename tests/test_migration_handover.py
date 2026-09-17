"""
Die Uebergabe: bereitstellen und starten.

Die wichtigste Zusicherung steht im vorletzten Test: **die
bestehende Installation wird nicht angefasst.** Der
Generationswechsel legt eine zweite Anwendung daneben; er ersetzt
nichts, benennt nichts um und loescht nichts. Das ist der
Rueckfallweg - schlaegt irgendetwas fehl, startet der Nutzer weiter
seine 4.x.
"""

import os
import stat

import pytest

from core.migration.assets import LINUX, WINDOWS
from core.migration.handover import Handover, HandoverError


CONTENT = b"#!/bin/sh\necho Companion-Forever\n"


@pytest.fixture
def downloaded(tmp_path):

    path = tmp_path / "downloads" / "Companion-Forever-5.0.0-x86_64.AppImage"

    path.parent.mkdir(parents=True)

    path.write_bytes(CONTENT)

    return path


@pytest.fixture
def root(tmp_path, monkeypatch):
    """
    Wohin installiert wird - im Test neben eine vorgetaeuschte
    bestehende AppImage.
    """

    folder = tmp_path / "anwendungen"

    folder.mkdir()

    (folder / "WeintCompanion-x86_64.AppImage").write_bytes(b"die alte Fassung")

    monkeypatch.setattr(
        "core.migration.handover.install_root",
        lambda: folder,
    )

    return folder


@pytest.fixture
def launched(monkeypatch):

    calls = []

    monkeypatch.setattr(
        "core.migration.handover.spawn_detached",
        lambda args, **kwargs: calls.append(list(args)),
    )

    return calls


# --------------------------------------------------
# Linux
# --------------------------------------------------


def test_the_appimage_is_placed_and_started(downloaded, root, launched):

    result = Handover(LINUX).run(downloaded)

    target = root / downloaded.name

    assert target.exists()

    assert target.read_bytes() == CONTENT

    assert result.installed_path == target

    assert result.launched

    assert launched == [[str(target)]]


def test_the_new_application_is_executable(downloaded, root, launched):
    """
    Eine AppImage ohne Ausfuehrbit startet nicht - und der Nutzer
    saehe nur, dass "nichts passiert".
    """

    Handover(LINUX).run(downloaded)

    mode = (root / downloaded.name).stat().st_mode

    assert mode & stat.S_IXUSR


def test_the_existing_installation_is_left_alone(downloaded, root, launched):

    old = root / "WeintCompanion-x86_64.AppImage"

    before = old.read_bytes()

    Handover(LINUX).run(downloaded)

    assert old.exists()

    assert old.read_bytes() == before


def test_no_half_file_is_left_under_the_final_name(downloaded, root, launched):

    Handover(LINUX).run(downloaded)

    assert not list(root.glob("*.part"))


def test_a_dry_run_places_the_file_but_starts_nothing(downloaded, root, launched):

    result = Handover(LINUX, dry_run=True).run(downloaded)

    assert (root / downloaded.name).exists()

    assert not result.launched

    assert launched == []


def test_an_empty_download_is_never_handed_over(tmp_path, root, launched):

    empty = tmp_path / "leer.AppImage"

    empty.write_bytes(b"")

    with pytest.raises(HandoverError) as error:
        Handover(LINUX).run(empty)

    assert error.value.code == "EMPTY_DOWNLOAD"

    assert launched == []


def test_a_missing_download_is_never_handed_over(tmp_path, root):

    with pytest.raises(HandoverError) as error:
        Handover(LINUX).run(tmp_path / "gibtsnicht.AppImage")

    assert error.value.code == "EMPTY_DOWNLOAD"


# --------------------------------------------------
# Windows
# --------------------------------------------------


def test_the_installer_is_called_with_the_silent_switches(downloaded, monkeypatch):
    """
    Ohne diese drei Schalter oeffnet sich der volle Installations-
    assistent - startet der im Hintergrund oder wird uebersehen,
    sieht der Wechsel aus wie "es passiert nichts". Der Installer
    startet die neue Anwendung danach selbst (Release-Vertrag).
    """

    seen = {}

    class Completed:
        returncode = 0

    def fake_run(command, **kwargs):

        seen["command"] = command
        seen["kwargs"] = kwargs

        return Completed()

    monkeypatch.setattr("core.migration.handover.subprocess.run", fake_run)

    result = Handover(WINDOWS).run(downloaded)

    assert seen["command"][0] == str(downloaded)

    assert "/VERYSILENT" in seen["command"]

    assert "/SUPPRESSMSGBOXES" in seen["command"]

    assert "/NORESTART" in seen["command"]

    assert seen["kwargs"]["timeout"] > 0

    assert result.launched


def test_a_failed_installer_is_a_failed_migration(downloaded, monkeypatch):

    class Completed:
        returncode = 2

    monkeypatch.setattr(
        "core.migration.handover.subprocess.run",
        lambda command, **kwargs: Completed(),
    )

    with pytest.raises(HandoverError) as error:
        Handover(WINDOWS).run(downloaded)

    assert error.value.code == "INSTALL_FAILED"

    assert "unveraendert" in error.value.message


def test_a_windows_dry_run_runs_no_installer(downloaded, monkeypatch):

    def fail(*args, **kwargs):
        raise AssertionError("Der Installer wurde trotzdem ausgefuehrt.")

    monkeypatch.setattr("core.migration.handover.subprocess.run", fail)

    result = Handover(WINDOWS, dry_run=True).run(downloaded)

    assert not result.launched


def test_an_unknown_platform_hands_nothing_over(downloaded):

    with pytest.raises(HandoverError) as error:
        Handover(None).run(downloaded)

    assert error.value.code == "UNSUPPORTED_PLATFORM"
