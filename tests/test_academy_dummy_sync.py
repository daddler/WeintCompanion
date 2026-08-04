"""
Rotationstrainer-Sitzungen vom Addon -> Streak -> Trainingsplan.

Der Kernpunkt: nur Tage mit ausreichender Trefferquote zählen, und nur
KALENDERTAG-AUF-KALENDERTAG ohne Lücke verlängert die Serie. Nach drei
solchen Tagen hakt sich die zugehörige Lektion automatisch ab - über
denselben AcademyService.set_completed(), den auch das manuell
gesetzte Häkchen benutzt.
"""

from core.academy_dummy_sync import (
    STREAK_TARGET,
    apply_dummy_practice_session,
    parse_dummy_practice_session,
)
from core.academy_service import AcademyService
from core.paths import Paths


class _Logger:

    def __init__(self):
        self.warnings = []

    def info(self, message):
        pass

    def error(self, message):
        pass

    def success(self, message):
        pass

    def warning(self, message):
        self.warnings.append(message)


class _Config:

    def __init__(self):
        self.data = {"academy_player_name": ""}

    def save(self):
        pass


class _Manager:

    def __init__(self):
        self.logger = _Logger()
        self.config = _Config()


def _service(tmp_path, monkeypatch):

    monkeypatch.setattr(
        Paths,
        "config",
        staticmethod(lambda: tmp_path),
    )

    return AcademyService(_Manager())


def _payload(character="Windschritt", spec_key="WARRIOR_ARMS", date="20260804",
             duration=90, hits=40, compliant=36, compliance=90.0):

    return "|".join([
        character, spec_key, date,
        str(duration), str(hits), str(compliant), str(compliance),
    ])


#
# --------------------------------------------------
# Parsen
# --------------------------------------------------
#


def test_parses_a_well_formed_session():

    session = parse_dummy_practice_session(_payload())

    assert session["character"] == "Windschritt"
    assert session["spec_key"] == "WARRIOR_ARMS"
    assert session["date"] == "20260804"
    assert session["compliance"] == 90.0


def test_a_malformed_payload_is_ignored():

    assert parse_dummy_practice_session("Windschritt|WARRIOR_ARMS|zu wenig Felder") is None
    assert parse_dummy_practice_session("") is None


#
# --------------------------------------------------
# Streak
# --------------------------------------------------
#


def test_a_qualifying_day_starts_a_streak_of_one(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(academy, _payload(date="20260804", compliance=90.0))

    record = academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]

    assert record["streak"] == 1
    assert record["lastDate"] == "20260804"


def test_a_day_below_the_threshold_is_ignored(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    changed = apply_dummy_practice_session(
        academy, _payload(date="20260804", compliance=40.0)
    )

    assert changed is False
    assert academy.data["dummy_practice"] == {}


def test_consecutive_days_extend_the_streak(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(academy, _payload(date="20260804"))
    apply_dummy_practice_session(academy, _payload(date="20260805"))

    record = academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]

    assert record["streak"] == 2


def test_a_second_session_on_the_same_day_does_not_change_the_streak(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(academy, _payload(date="20260804"))
    changed = apply_dummy_practice_session(academy, _payload(date="20260804"))

    record = academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]

    assert changed is False
    assert record["streak"] == 1


def test_a_gap_resets_the_streak(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(academy, _payload(date="20260804"))
    apply_dummy_practice_session(academy, _payload(date="20260805"))
    apply_dummy_practice_session(academy, _payload(date="20260810"))  # Lücke

    record = academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]

    assert record["streak"] == 1


def test_three_consecutive_days_complete_the_lesson(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    assert STREAK_TARGET == 3

    apply_dummy_practice_session(academy, _payload(date="20260804"))
    apply_dummy_practice_session(academy, _payload(date="20260805"))

    assert academy.is_completed("Windschritt", "warrior-arms.rotation.dummy_practice") is False

    apply_dummy_practice_session(academy, _payload(date="20260806"))

    assert academy.is_completed("Windschritt", "warrior-arms.rotation.dummy_practice") is True


def test_an_unknown_spec_key_is_rejected_with_a_warning(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    changed = apply_dummy_practice_session(
        academy, _payload(spec_key="PRIEST_HOLY")
    )

    assert changed is False
    assert academy.manager.logger.warnings


def test_streaks_are_tracked_per_character_and_spec(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(
        academy, _payload(character="Windschritt", spec_key="WARRIOR_ARMS", date="20260804")
    )
    apply_dummy_practice_session(
        academy, _payload(character="Nachtblatt", spec_key="MAGE_FIRE", date="20260804")
    )

    assert academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]["streak"] == 1
    assert academy.data["dummy_practice"]["Nachtblatt"]["MAGE_FIRE"]["streak"] == 1
