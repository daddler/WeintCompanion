"""
Die Meldung des Addons, wer ingame angemeldet ist.

Bis WeintCodex 1.3.2.3 gab es sie nicht - die App musste "wer bin
ich" aus einer WarcraftLogs-Namensliste raten. Zwei Dinge stehen
hier deshalb im Vordergrund:

* **Das Format verträgt zwei bis fünf Felder.** Das Addon darf es
  erweitern, ohne eine ältere App zu brechen, und eine ältere
  Addon-Version, die nur Name und Realm schickt, funktioniert
  weiter. Für die Auswahl zählen ohnehin nur die ersten beiden.
* **Die Vorrangregel.** Eine Auswahl von Hand schlägt die
  Spielmeldung für den Charakter, auf dem sie getroffen wurde - und
  hört auf zu schlagen, sobald das Spiel einen anderen meldet.
  "Ich habe als Alice kurz Bobs Werte angesehen" darf nicht noch
  gelten, wenn ich als Carol einlogge.
"""

import pytest

from analyzer.models import Actor, MetricEntry, RaidSnapshot

from core.academy_service import AcademyService
from core.character_report_sync import (
    apply_character_report,
    parse_character_report,
)
from core.paths import Paths


# --------------------------------------------------
# Format
# --------------------------------------------------


def test_alle_fuenf_felder():

    report = parse_character_report("Aldrin|DieAldor|WARRIOR|90|WARRIOR_ARMS")

    assert report == {
        "name": "Aldrin",
        "realm": "DieAldor",
        "class": "WARRIOR",
        "level": 90,
        "spec": "WARRIOR_ARMS",
    }


def test_zwei_felder_reichen():
    """
    Mehr braucht die Charakterauswahl nicht.
    """

    report = parse_character_report("Aldrin|DieAldor")

    assert report["name"] == "Aldrin"
    assert report["realm"] == "DieAldor"
    assert report["class"] == ""
    assert report["level"] == 0
    assert report["spec"] == ""


def test_zusaetzliche_felder_werden_ignoriert():
    """
    Damit das Addon das Format erweitern kann, ohne diese Seite
    mitzuliefern.
    """

    report = parse_character_report("Aldrin|DieAldor|WARRIOR|90|ARMS|neu|noch neuer")

    assert report["name"] == "Aldrin"
    assert report["spec"] == "ARMS"


def test_ein_unlesbares_level_verwirft_die_meldung_nicht():
    """
    Der Name ist das Einzige, worauf es ankommt.
    """

    report = parse_character_report("Aldrin|DieAldor|WARRIOR|neunzig")

    assert report["name"] == "Aldrin"
    assert report["level"] == 0


def test_ohne_namen_ist_die_meldung_wertlos():

    assert parse_character_report("") is None
    assert parse_character_report("|DieAldor") is None
    assert parse_character_report(None) is None
    assert parse_character_report(42) is None


# --------------------------------------------------
# Anwendung auf die Auswahl
# --------------------------------------------------


class _Logger:

    def info(self, message):
        pass

    def error(self, message):
        pass

    def success(self, message):
        pass

    def warning(self, message):
        pass


class _Config:

    def __init__(self):
        self.data = {
            "academy_player_name": "",
            "academy_follow_game": True,
            "academy_ingame_character": "",
            "academy_ingame_realm": "",
            "academy_player_source": "",
            "academy_manual_for": "",
        }

    def save(self):
        pass


class _RaidData:

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def current(self):
        return self.snapshot


class _Manager:

    def __init__(self, snapshot):
        self.logger = _Logger()
        self.config = _Config()
        self.raid_data = _RaidData(snapshot)


def _snapshot(*names) -> RaidSnapshot:

    return RaidSnapshot(
        captured_at=1000.0,
        source_label="Test",
        raid_size=25,
        pull_number=1,
        top_damage=tuple(
            MetricEntry(
                actor=Actor(name=name, class_name="Warrior", spec="Waffen", role="dps"),
                value=1000.0,
            )
            for name in names
        ),
    )


@pytest.fixture
def academy(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    return AcademyService(_Manager(_snapshot("Aldrin", "Bordrin", "Cendrin")))


def test_die_auswahl_folgt_dem_angemeldeten_charakter(academy):

    academy.set_player_name("Aldrin")

    apply_character_report(academy, "Bordrin|DieAldor|WARRIOR|90|")

    assert academy.player_name() == "Bordrin"
    assert academy.manager.config.data["academy_player_source"] == "game"


def test_ein_charakter_ausserhalb_des_raids_stellt_nichts_um(academy):
    """
    Gemerkt wird er trotzdem - beim nächsten ensure_player_name()
    zählt er.
    """

    academy.set_player_name("Aldrin")

    apply_character_report(academy, "Dendrin|DieAldor")

    assert academy.player_name() == "Aldrin"
    assert academy.ingame_character() == "Dendrin"


def test_eine_wahl_von_hand_haelt_fuer_denselben_charakter(academy):

    apply_character_report(academy, "Aldrin|DieAldor")

    academy.note_manual_choice("Cendrin")

    # Erneuter Login mit demselben Charakter: die Wahl gilt weiter.
    apply_character_report(academy, "Aldrin|DieAldor")

    assert academy.player_name() == "Cendrin"


def test_eine_wahl_von_hand_weicht_einem_anderen_charakter(academy):
    """
    Genau der Punkt: die Handauswahl darf keine Identitätsleiche
    werden.
    """

    apply_character_report(academy, "Aldrin|DieAldor")

    academy.note_manual_choice("Cendrin")

    apply_character_report(academy, "Bordrin|DieAldor")

    assert academy.player_name() == "Bordrin"
    assert academy.manager.config.data["academy_player_source"] == "game"


def test_der_hauptschalter_haelt_alles_an(academy):

    academy.set_player_name("Aldrin")

    academy.manager.config.data["academy_follow_game"] = False

    apply_character_report(academy, "Bordrin|DieAldor")

    assert academy.player_name() == "Aldrin"
    # Gemerkt wird die Anmeldung trotzdem.
    assert academy.ingame_character() == "Bordrin"


def test_die_schreibweise_des_rosters_gewinnt(academy, tmp_path, monkeypatch):
    """
    Das Spiel kennt nur "Aldrin", der Bericht schreibt
    "Aldrin-Everlook" - gespeichert werden muss die Schreibweise des
    Berichts.
    """

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    service = AcademyService(_Manager(_snapshot("Aldrin-Everlook", "Bordrin")))

    apply_character_report(service, "Aldrin|Everlook")

    assert service.player_name() == "Aldrin-Everlook"


def test_ohne_academy_passiert_nichts():

    assert apply_character_report(None, "Aldrin|DieAldor") is None
