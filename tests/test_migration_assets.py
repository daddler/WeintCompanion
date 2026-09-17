"""
Die Auswahl der Installationsdatei aus einem Release.

Dieselbe Lehre wie in `test_github_updater.py`, eine Stufe schaerfer:
dort ging es darum, dass eine Pruefsummendatei nicht als Asset
durchgeht; hier zusaetzlich darum, dass eine Datei fuer eine fremde
Plattform oder eine fremde Architektur **gar nicht** genommen wird -
auch dann nicht, wenn sie die einzige im Release ist. "Irgendwas
installieren" ist beim Generationswechsel keine Rueckfallebene.
"""

import pytest

from core.migration.assets import (
    LINUX,
    WINDOWS,
    AssetError,
    ReleaseAsset,
    checksum_for,
    select_asset,
)


def asset(name):

    return ReleaseAsset(
        name=name,
        url=f"https://example.invalid/{name}",
        size=1024,
    )


FULL_RELEASE = [
    asset("Companion-Forever-5.0.0-x86_64.AppImage"),
    asset("Companion-Forever-5.0.0-x86_64.AppImage.sha256"),
    asset("Companion-Forever-Setup-5.0.0-x64.exe"),
    asset("Companion-Forever-Setup-5.0.0-x64.exe.sha256"),
    asset("Source code (zip)"),
    asset("Source code (tar.gz)"),
]


# --------------------------------------------------
# Der Normalfall
# --------------------------------------------------


def test_linux_gets_the_appimage():

    choice = select_asset(FULL_RELEASE, LINUX, "x86_64")

    assert choice.asset.name == "Companion-Forever-5.0.0-x86_64.AppImage"


def test_windows_gets_the_installer():

    choice = select_asset(FULL_RELEASE, WINDOWS, "x86_64")

    assert choice.asset.name == "Companion-Forever-Setup-5.0.0-x64.exe"


def test_the_checksum_travels_with_the_choice():

    choice = select_asset(FULL_RELEASE, LINUX, "x86_64")

    assert choice.checksum.name.endswith(".AppImage.sha256")


def test_amd64_is_the_same_architecture_as_x86_64():

    choice = select_asset(FULL_RELEASE, LINUX, "amd64")

    assert choice.asset.name.endswith("x86_64.AppImage")


# --------------------------------------------------
# Was nie gewaehlt wird
# --------------------------------------------------


def test_a_checksum_file_is_never_the_asset():
    """
    ".appimage" steckt als Teilstring auch in
    "...AppImage.sha256". GitHub garantiert keine Reihenfolge der
    Assets - stuende die Pruefsummendatei zuerst, waere sie ohne
    diese Regel "das Asset".
    """

    assets = [
        asset("Companion-Forever-5.0.0-x86_64.AppImage.sha256"),
        asset("Companion-Forever-5.0.0-x86_64.AppImage"),
    ]

    choice = select_asset(assets, LINUX, "x86_64")

    assert choice.asset.name.endswith(".AppImage")


def test_source_archives_are_not_installation_files():

    assets = [asset("Source code (zip)"), asset("Source code (tar.gz)")]

    with pytest.raises(AssetError) as error:
        select_asset(assets, LINUX, "x86_64")

    assert error.value.code == "NO_MATCH"


def test_a_foreign_architecture_is_not_taken():
    """
    Ein Release, das nur eine ARM-AppImage enthaelt, hat fuer einen
    x86-Rechner **nichts** - und nicht "das einzige, was da ist".
    """

    assets = [asset("Companion-Forever-5.0.0-aarch64.AppImage")]

    with pytest.raises(AssetError) as error:
        select_asset(assets, LINUX, "x86_64")

    assert error.value.code == "NO_MATCH"


def test_a_missing_asset_for_this_platform_is_reported():

    assets = [asset("Companion-Forever-Setup-5.0.0-x64.exe")]

    with pytest.raises(AssetError) as error:
        select_asset(assets, LINUX, "x86_64")

    assert error.value.code == "NO_MATCH"

    assert "Linux" in error.value.message


def test_two_equal_candidates_are_never_guessed_between():
    """
    Mehrdeutig heisst: keine Auswahl. Lieber kein Wechsel als der
    Wechsel auf eine geratene Datei.
    """

    assets = [
        asset("Companion-Forever-5.0.0-x86_64.AppImage"),
        asset("Companion-Forever-5.0.0-lite-x86_64.AppImage"),
    ]

    with pytest.raises(AssetError) as error:
        select_asset(assets, LINUX, "x86_64")

    assert error.value.code == "AMBIGUOUS"


def test_an_unsupported_platform_says_so(monkeypatch):
    """
    macOS: die App laeuft dort nur aus dem Quelltext, es gibt keinen
    Build - und damit auch keinen Wechsel. Ohne erkannte Plattform
    wird nichts geraten.
    """

    monkeypatch.setattr(
        "core.migration.assets.current_profile",
        lambda: None,
    )

    with pytest.raises(AssetError) as error:
        select_asset(FULL_RELEASE, None, "x86_64")

    assert error.value.code == "UNSUPPORTED_PLATFORM"


# --------------------------------------------------
# Vorzug
# --------------------------------------------------


def test_an_exe_beats_an_msi():
    """
    Die Reihenfolge in `PlatformProfile.suffixes` entscheidet - nicht
    die Reihenfolge in der Antwort von GitHub.
    """

    assets = [
        asset("Companion-Forever-5.0.0-x64.msi"),
        asset("Companion-Forever-Setup-5.0.0-x64.exe"),
    ]

    choice = select_asset(assets, WINDOWS, "x86_64")

    assert choice.asset.name.endswith(".exe")


def test_a_file_without_an_architecture_still_counts():

    assets = [asset("Companion-Forever-5.0.0.AppImage")]

    choice = select_asset(assets, LINUX, "x86_64")

    assert choice.asset.name == "Companion-Forever-5.0.0.AppImage"


def test_the_named_architecture_wins_over_the_unnamed_one():

    assets = [
        asset("Companion-Forever-5.0.0.AppImage"),
        asset("Companion-Forever-5.0.0-x86_64.AppImage"),
    ]

    choice = select_asset(assets, LINUX, "x86_64")

    assert choice.asset.name.endswith("x86_64.AppImage")


def test_a_release_without_a_checksum_file_selects_but_reports_none():
    """
    Ob ein fehlender Hash den Wechsel abbricht, entscheidet die
    Pruefung (`core/migration/integrity.py`) - nicht die Auswahl.
    """

    assets = [asset("Companion-Forever-5.0.0-x86_64.AppImage")]

    choice = select_asset(assets, LINUX, "x86_64")

    assert choice.checksum is None

    assert checksum_for(assets, choice.asset) is None
