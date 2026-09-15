"""
Die Spielversionstabelle (`core/wow_clients.py`) und was daran hängt:
die Suche auf der Platte (`addon/finder.py`) und die Konfiguration
(`core/config.py`).

Diese Datei prüft vor allem **den Wechsel**, denn der ist der Zweck der
ganzen Vorbereitung: dass eine zweite Spielversion nur ein Eintrag ist,
dass der Pfad der einen beim Wechsel zur anderen nicht verlorengeht -
und dass der Wechsel auf eine Version mit unbekanntem Ordnernamen nicht
im Ordner einer anderen landet.
"""

import json

from addon.finder import WoWFinder
from core.config import Config
from core.paths import Paths
from core.wow_clients import (
    CLIENTS,
    DEFAULT_CLIENT_ID,
    FOREVER,
    MOP_CLASSIC,
    client,
    default_client,
    foreign_flavor_folders,
    released_clients,
)


def _make_installation(base, name):

    folder = base / name

    (folder / "Interface" / "AddOns").mkdir(parents=True)

    (folder / "WTF").mkdir(parents=True)

    return folder


# --------------------------------------------------
# Die Tabelle
# --------------------------------------------------


def test_every_client_has_a_unique_id():

    ids = [entry.id for entry in CLIENTS]

    assert len(ids) == len(set(ids))


def test_an_unknown_id_falls_back_instead_of_raising():
    """
    Der Wert kommt aus der config.json und damit aus einer Datei, die
    ein Nutzer von Hand ändern kann - ein Tippfehler darf den Start
    nicht verhindern.
    """

    assert client("gibt-es-nicht") is default_client()

    assert client(None) is default_client()

    assert default_client().id == DEFAULT_CLIENT_ID


def test_forever_carries_no_folder_name_yet():
    """
    Das ist kein Versehen, sondern der Zustand, den diese Vorbereitung
    tragen muss - siehe den Kommentar in core/wow_clients.py.
    """

    assert not FOREVER.folder_known

    assert FOREVER.max_level is None

    assert MOP_CLASSIC.folder_known


def test_only_released_clients_are_offered_in_the_setup():

    assert MOP_CLASSIC in released_clients()

    assert FOREVER not in released_clients()


def test_a_clients_own_folder_name_is_not_foreign_to_itself():

    assert "_classic_" not in foreign_flavor_folders(MOP_CLASSIC)

    assert "_classic_" in foreign_flavor_folders(FOREVER)


# --------------------------------------------------
# Suche auf der Platte
# --------------------------------------------------


def test_the_finder_looks_for_the_clients_own_folder(tmp_path):

    root = tmp_path / "World of Warcraft"

    classic = _make_installation(root, "_classic_")

    _make_installation(root, "_retail_")

    finder = WoWFinder(MOP_CLASSIC)

    finder.search_roots = [tmp_path]

    assert finder.find() == classic


def test_the_finder_ignores_other_flavours_when_the_name_is_unknown(tmp_path):
    """
    Ohne den Ausschluss fände eine Suche nach Forever `_retail_` und
    gäbe es als Forever aus.
    """

    root = tmp_path / "World of Warcraft"

    _make_installation(root, "_retail_")

    _make_installation(root, "_classic_era_")

    finder = WoWFinder(FOREVER)

    finder.search_roots = [tmp_path]

    assert finder.find() is None


def test_the_finder_accepts_an_unknown_name_by_its_markers(tmp_path):

    root = tmp_path / "World of Warcraft"

    forever = _make_installation(root, "_forever_")

    finder = WoWFinder(FOREVER)

    finder.search_roots = [tmp_path]

    assert finder.find() == forever


def test_the_finder_does_not_accept_a_stray_folder_for_mop(tmp_path):
    """
    Bei bekanntem Ordnernamen bleibt die Suche eng: ein Ordner, der
    zufällig Interface/ und WTF/ enthält, ist kein Treffer.
    """

    _make_installation(tmp_path, "irgendein-ordner")

    finder = WoWFinder(MOP_CLASSIC)

    finder.search_roots = [tmp_path]

    assert finder.find() is None


# --------------------------------------------------
# Konfiguration
# --------------------------------------------------


def test_the_old_classic_path_is_taken_over(tmp_path, monkeypatch):
    """
    Bis 4.0 gab es genau einen Pfad. Eine bestehende Installation darf
    ihn beim Update nicht verlieren.
    """

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    installation = _make_installation(tmp_path, "_classic_")

    (tmp_path / "config.json").write_text(
        json.dumps({"classic_path": str(installation)}),
        encoding="utf-8",
    )

    config = Config()

    assert config.data["wow_paths"][MOP_CLASSIC.id] == str(installation)

    assert config.get_wow_client().id == MOP_CLASSIC.id

    assert config.get_wow_path() == installation


def test_each_client_keeps_its_own_path(tmp_path, monkeypatch):
    """
    Der eigentliche Zweck: hin und zurück wechseln verliert nichts.
    """

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    classic = _make_installation(tmp_path, "_classic_")

    forever = _make_installation(tmp_path, "_forever_")

    config = Config()

    config.set_wow_path(classic)

    config.set_wow_client(FOREVER.id)

    assert config.get_wow_path() is None

    config.set_wow_path(forever)

    assert config.get_wow_path() == forever

    config.set_wow_client(MOP_CLASSIC.id)

    assert config.get_wow_path() == classic

    assert config.get_wow_path(FOREVER.id) == forever


def test_a_path_that_disappeared_counts_as_none(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config = Config()

    config.set_wow_path(tmp_path / "abgezogene-platte")

    assert config.get_wow_path() is None


def test_the_legacy_key_follows_mop_classic(tmp_path, monkeypatch):
    """
    `classic_path` bleibt beschrieben, damit eine ältere
    Companion-Fassung, auf die jemand zurückgeht, ihren Ordner noch
    findet - und trägt dabei nie den Pfad einer anderen Spielversion.
    """

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    classic = _make_installation(tmp_path, "_classic_")

    forever = _make_installation(tmp_path, "_forever_")

    config = Config()

    config.set_wow_path(classic)

    assert config.data["classic_path"] == str(classic)

    config.set_wow_client(FOREVER.id)

    config.set_wow_path(forever)

    assert config.data["classic_path"] == str(classic)


def test_switching_takes_the_untouched_minimum_level_along(tmp_path, monkeypatch):
    """
    Bis 4.0 trug jede Konfiguration die 90 aus dem Backfill - also die
    Höchststufe von MoP Classic und keine eigene Wahl. Nach dem Wechsel
    wäre sie stillschweigend die Zahl der falschen Spielversion.
    """

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config = Config()

    config.data["characters_min_level"] = MOP_CLASSIC.max_level

    config.set_wow_client(FOREVER.id)

    assert config.data["characters_min_level"] == 0


def test_switching_keeps_a_deliberate_minimum_level(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config = Config()

    config.data["characters_min_level"] = 85

    config.set_wow_client(FOREVER.id)

    assert config.data["characters_min_level"] == 85
