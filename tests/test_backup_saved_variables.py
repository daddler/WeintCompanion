"""
Was ein Backup vor einer Aktualisierung eigentlich sichern muss.

Bis 2.7.1 sicherte es den **Addon-Ordner** - also Dateien, die
jederzeit wieder von GitHub kommen - und nicht die `SavedVariables`,
in denen alles steht, was der Spieler selbst eingetragen hat:
Bossnotizen, Twinkliste, Encounter-Fortschritt, Academy. Genau
andersherum, denn nur eines von beidem ist unwiederbringlich.

Geprüft wird:

- dass beide Teile im Archiv liegen, sauber getrennt,
- dass `restore()` **nur** den Addon-Teil auspackt (sonst entstünde
  ein `WTF`-Ordner mitten in `Interface/AddOns`),
- dass der Spielstand nur auf ausdrückliches Verlangen zurückgeht und
  dabei die vorhandene Datei beiseitelegt,
- und dass ein Backup aus einer älteren Fassung (nur Addon-Ordner)
  weiterhin funktioniert.
"""

import zipfile

import pytest

from core import backup as backup_module
from core.backup import (
    ASIDE_SUFFIX,
    BackupManager,
    backup_time_text,
    saved_variable_files,
    saved_variable_members,
)


@pytest.fixture
def wow(tmp_path):
    """
    Ein WoW-Ordner mit Addon und zwei Konten.
    """

    root = tmp_path / "World of Warcraft" / "_classic_"

    addon = root / "Interface" / "AddOns" / "WeintCodex"

    (addon / "modules").mkdir(parents=True)

    (addon / "WeintCodex.toc").write_text("## Version: 2.9.1.0\n")

    (addon / "modules" / "bossguides.lua").write_text("-- code\n")

    for account in ("KONTO1", "KONTO2"):

        saved = root / "WTF" / "Account" / account / "SavedVariables"

        saved.mkdir(parents=True)

        (saved / "WeintCodex.lua").write_text(
            f'WeintCodex_SavedData = {{ ["bossNotes"] = {{ ["Malkorok"] '
            f'= "{account}: Notiz" }} }}\n'
        )

    return root


@pytest.fixture
def manager(tmp_path, monkeypatch):

    store = tmp_path / "backups"

    store.mkdir()

    monkeypatch.setattr(
        backup_module.Paths,
        "backups",
        staticmethod(lambda: store),
    )

    return BackupManager()


def _addon(wow):
    return wow / "Interface" / "AddOns" / "WeintCodex"


# --------------------------------------------------
# Was gesichert wird
# --------------------------------------------------


def test_der_spielstand_liegt_mit_im_archiv(manager, wow):

    archive = manager.create_backup(_addon(wow), wow)

    names = zipfile.ZipFile(archive).namelist()

    assert "WeintCodex/WeintCodex.toc" in names

    assert (
        "WTF/Account/KONTO1/SavedVariables/WeintCodex.lua" in names
    )


def test_alle_konten_kommen_mit(manager, wow):
    """
    `SyncReader.get_file()` nimmt das erste Konto - dort geht es
    darum, wohin geschrieben wird. Hier geht es darum, was verloren
    gehen könnte, und wer zwei Konten hat, hat auf beiden Notizen.
    """

    assert len(saved_variable_files(wow)) == 2

    archive = manager.create_backup(_addon(wow), wow)

    assert len(saved_variable_members(archive)) == 2


def test_ohne_wow_pfad_entsteht_das_bisherige_archiv(manager, wow):

    archive = manager.create_backup(_addon(wow))

    assert saved_variable_members(archive) == []

    assert "WeintCodex/WeintCodex.toc" in zipfile.ZipFile(archive).namelist()


# --------------------------------------------------
# Was zurückgeholt wird - und was nicht
# --------------------------------------------------


def test_restore_holt_nur_den_addon_ordner(manager, wow):
    """
    Ein `extractall()` über das ganze Archiv legte einen `WTF`-Ordner
    mitten in `Interface/AddOns` an.
    """

    archive = manager.create_backup(_addon(wow), wow)

    addon = _addon(wow)

    (addon / "WeintCodex.toc").write_text("## Version: kaputt\n")

    assert manager.restore(archive, addon) is True

    assert "2.9.1.0" in (addon / "WeintCodex.toc").read_text()

    assert not (addon.parent / "WTF").exists()


def test_restore_ruehrt_den_spielstand_nicht_an(manager, wow):
    """
    Er war beim Update nie weg. Ihn bei einem Fehlschlag der
    Installation stillschweigend zurückzuschieben, würde daraus einen
    Datenverlust machen.
    """

    archive = manager.create_backup(_addon(wow), wow)

    live = (
        wow / "WTF" / "Account" / "KONTO1" / "SavedVariables"
        / "WeintCodex.lua"
    )

    live.write_text("WeintCodex_SavedData = { }\n")

    manager.restore(archive, _addon(wow))

    assert live.read_text() == "WeintCodex_SavedData = { }\n"


def test_der_spielstand_geht_nur_auf_verlangen_zurueck(manager, wow):

    archive = manager.create_backup(_addon(wow), wow)

    live = (
        wow / "WTF" / "Account" / "KONTO1" / "SavedVariables"
        / "WeintCodex.lua"
    )

    live.write_text("-- inzwischen kaputt\n")

    written = manager.restore_saved_variables(archive, wow)

    assert len(written) == 2

    assert "KONTO1: Notiz" in live.read_text()


def test_die_vorhandene_datei_wird_beiseitegelegt(manager, wow):
    """
    Eine Wiederherstellung ohne Rückweg ist eine Einbahnstrasse - wer
    sie versehentlich auslöst, hätte sonst gar nichts mehr.
    """

    archive = manager.create_backup(_addon(wow), wow)

    live = (
        wow / "WTF" / "Account" / "KONTO1" / "SavedVariables"
        / "WeintCodex.lua"
    )

    live.write_text("-- der Stand von jetzt\n")

    manager.restore_saved_variables(archive, wow)

    aside = live.with_name(live.name + ASIDE_SUFFIX)

    assert aside.read_text() == "-- der Stand von jetzt\n"


# --------------------------------------------------
# Was die Oberfläche fragt
# --------------------------------------------------


def test_ein_altes_backup_traegt_keinen_spielstand(manager, wow):
    """
    Backups aus einer Fassung vor 2.7.1 sicherten nur den
    Addon-Ordner. Die Seite muss das sagen können, statt einen Knopf
    anzubieten, der nichts findet.
    """

    manager.create_backup(_addon(wow))

    assert manager.newest_with_saved_variables() is None


def test_das_juengste_backup_mit_spielstand_gewinnt(manager, wow, monkeypatch):

    alt = manager.create_backup(_addon(wow), wow)

    #
    # Zwei Backups in derselben Sekunde tragen denselben Namen; der
    # Zeitstempel kommt aus der Uhr, also wird er hier vorgegeben.
    #

    neu = manager.backup_dir / "WeintCodex_2099-01-01_00-00-00.zip"

    neu.write_bytes(alt.read_bytes())

    assert manager.newest_with_saved_variables() == neu

    assert manager.backups()[0] == neu


def test_der_zeitpunkt_kommt_aus_dem_dateinamen():

    text = backup_time_text("/x/WeintCodex_2026-09-02_14-03-11.zip")

    assert "2. September 2026" in text

    assert "14:03" in text


def test_ein_fremder_name_wird_nicht_erfunden():
    """
    Eine erfundene Uhrzeit wäre schlechter als gar keine.
    """

    assert backup_time_text("/x/irgendwas.zip") == "irgendwas"


def test_ein_eintrag_der_aus_dem_ordner_fuehrt_wird_uebergangen(
    manager, wow, tmp_path
):
    """
    Die Archive stammen aus dieser Datei, aber sie liegen im
    Zwischenspeicher des Nutzers und lassen sich austauschen.
    """

    boese = manager.backup_dir / "WeintCodex_2030-01-01_00-00-00.zip"

    with zipfile.ZipFile(boese, "w") as archive:

        archive.writestr("WTF/../../entkommen.lua", "-- nope\n")

        archive.writestr(
            "WTF/Account/KONTO1/SavedVariables/WeintCodex.lua",
            "-- brav\n",
        )

    written = manager.restore_saved_variables(boese, wow)

    assert len(written) == 1

    assert not (tmp_path / "entkommen.lua").exists()
