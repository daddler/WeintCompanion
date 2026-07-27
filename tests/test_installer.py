import os
import zipfile

import pytest

from core.installer import Installer


def _make_zip(tmp_path, marker_name):
    zip_path = tmp_path / "WeintCodex.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("WeintCodex/WeintCodex.toc", "## Interface: 50400\n")
        archive.writestr(f"WeintCodex/{marker_name}", "content")

    return zip_path


def _existing_addon(tmp_path):
    addon_path = tmp_path / "WoW" / "Interface" / "AddOns" / "WeintCodex"
    addon_path.mkdir(parents=True)
    (addon_path / "old_version.txt").write_text("old", encoding="utf-8")
    return addon_path


def test_install_replaces_existing_addon(tmp_path):
    addon_path = _existing_addon(tmp_path)
    zip_path = _make_zip(tmp_path, "new_version.txt")

    Installer().install(zip_path, addon_path)

    assert (addon_path / "new_version.txt").exists()
    assert not (addon_path / "old_version.txt").exists()

    # Keine Arbeitsordner bleiben nach einer erfolgreichen Installation zurück.
    assert not addon_path.with_name(addon_path.name + ".new").exists()
    assert not addon_path.with_name(addon_path.name + ".old").exists()


def test_install_into_fresh_addons_folder(tmp_path):
    addon_path = tmp_path / "WoW" / "Interface" / "AddOns" / "WeintCodex"
    zip_path = _make_zip(tmp_path, "new_version.txt")

    Installer().install(zip_path, addon_path)

    assert (addon_path / "new_version.txt").exists()


def test_install_leaves_old_version_intact_if_swap_fails(tmp_path, monkeypatch):
    """
    Simuliert einen Absturz genau zwischen den beiden os.rename()-
    Aufrufen des atomaren Swaps (core/installer.py::Installer.install).
    Vorher lag hier ein rmtree()-dann-copytree()-Ablauf, bei dem
    exakt dieses Szenario den Nutzer komplett ohne installiertes
    Addon zurückließ - das darf nicht mehr passieren.
    """

    addon_path = _existing_addon(tmp_path)
    zip_path = _make_zip(tmp_path, "new_version.txt")

    new_path = addon_path.with_name(addon_path.name + ".new")

    real_rename = os.rename

    def flaky_rename(src, dst):
        if str(src) == str(new_path):
            raise OSError("simulierter Absturz mitten im Swap")
        real_rename(src, dst)

    monkeypatch.setattr("core.installer.os.rename", flaky_rename)

    with pytest.raises(OSError):
        Installer().install(zip_path, addon_path)

    # Egal was passiert: addon_path enthält entweder komplett die
    # alte oder komplett die neue Version, nie einen Mischzustand
    # oder gar nichts.
    assert addon_path.exists()
    assert (addon_path / "old_version.txt").exists()
    assert not (addon_path / "new_version.txt").exists()
