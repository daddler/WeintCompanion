"""
Rotationstrainer-Sitzungen vom Addon -> Streak -> Trainingsplan.

Der Kernpunkt: nur Tage mit ausreichend langer Übung und ausreichender
Note zählen, und nur KALENDERTAG-AUF-KALENDERTAG ohne Lücke verlängert
die Serie. Nach drei solchen Tagen hakt sich die zugehörige Lektion
automatisch ab - über denselben AcademyService.set_completed(), den
auch das manuell gesetzte Häkchen benutzt.
"""

from core.academy_dummy_sync import (
    MIN_SESSION_SECONDS,
    STREAK_TARGET,
    apply_dummy_practice_session,
    parse_dummy_practice_session,
    practice_for_lessons,
    practice_payload,
    practice_text,
    streak_state,
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
             duration=240, hits=40, compliant=36, compliance=90.0):

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


def test_a_session_shorter_than_the_minimum_is_ignored(tmp_path, monkeypatch):
    #
    # Neuere Addon-Versionen melden solche Sitzungen gar nicht erst;
    # ältere schon, und auch die dürfen keine Serie tragen.
    #

    academy = _service(tmp_path, monkeypatch)

    changed = apply_dummy_practice_session(
        academy, _payload(date="20260804", duration=MIN_SESSION_SECONDS - 1)
    )

    assert changed is False
    assert academy.data["dummy_practice"] == {}


def test_a_session_at_the_minimum_counts(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    changed = apply_dummy_practice_session(
        academy, _payload(date="20260804", duration=MIN_SESSION_SECONDS)
    )

    assert changed is True
    assert academy.data["dummy_practice"]["Windschritt"]["WARRIOR_ARMS"]["streak"] == 1


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


#
# --------------------------------------------------
# Derselbe Charakter, zwei Schreibweisen
# --------------------------------------------------
#
# Der Trainer meldet den nackten Clientnamen, die Auswertung läuft
# unter der Schreibweise des Berichts. Bis 2.8.0 waren das zwei
# Charaktere: die Serie hakte die Lektion unter "Windschritt" ab, und
# gesucht wurde sie danach unter "Windschritt-DieAldor". Der Haken
# tauchte nirgends auf - nicht im Spiel, nicht auf dem Desktop, ohne
# Fehler und ohne Meldung.
#


def test_the_streak_finds_the_character_of_the_report(tmp_path, monkeypatch):

    academy = _service(tmp_path, monkeypatch)

    #
    # So kommt der Fortschritt aus dem Addon zurück: qualifiziert.
    #

    academy.set_completed(
        "Windschritt-DieAldor", "generic.rotation.uptime", True
    )

    for tag in ("20260804", "20260805", "20260806"):

        apply_dummy_practice_session(
            academy,
            _payload(
                character="Windschritt",
                spec_key="WARRIOR_ARMS",
                date=tag,
            ),
        )

    #
    # Ein Charakter, ein Schlüssel - und der Haken der Serie liegt
    # dort, wo die Auswertung ihn sucht.
    #

    assert list(academy.data["dummy_practice"]) == ["Windschritt-DieAldor"]

    assert (
        "warrior-arms.rotation.dummy_practice"
        in academy.completed_for("Windschritt-DieAldor")
    )

    assert (
        "warrior-arms.rotation.dummy_practice"
        in academy.completed_for("Windschritt")
    )


def test_two_spellings_on_disk_are_merged_on_load(tmp_path, monkeypatch):
    """
    Wer die alte Fassung benutzt hat, hat beide Schreibweisen in der
    Datei. Beim Laden werden sie zu einer - die qualifizierte gewinnt,
    weil ein fehlender Realm ein Platzhalter ist und den vollen Namen
    weiterhin findet.
    """

    academy = _service(tmp_path, monkeypatch)

    academy.data["completed"]["Windschritt-DieAldor"] = ["generic.a"]
    academy.data["completed"]["Windschritt"] = ["generic.b"]
    academy.data["dummy_practice"]["Windschritt"] = {
        "WARRIOR_ARMS": {"lastDate": "20260806", "streak": 2},
    }
    academy.save()

    reloaded = _service(tmp_path, monkeypatch)

    assert list(reloaded.data["completed"]) == ["Windschritt-DieAldor"]

    assert reloaded.completed_for("Windschritt") == frozenset(
        {"generic.a", "generic.b"}
    )

    assert reloaded.practice_for("Windschritt-DieAldor")[
        "WARRIOR_ARMS"
    ]["streak"] == 2


#
# --------------------------------------------------
# Was die Serie heute wert ist
# --------------------------------------------------
#


def test_a_stale_streak_is_not_a_running_one():
    """
    Eine drei Wochen alte Zwei als "Tag 2 von 3" auszugeben wäre ein
    Versprechen, das die nächste Sitzung bricht: sie beginnt bei eins.
    """

    state = streak_state({"lastDate": "20260801", "streak": 2}, "20260902")

    assert state["alive"] is False
    assert state["streak"] == 0
    assert state["missing"] == STREAK_TARGET

    assert "abgerissen" in practice_text(state)


def test_yesterday_keeps_the_streak_alive():

    state = streak_state({"lastDate": "20260901", "streak": 2}, "20260902")

    assert state["alive"] is True
    assert state["streak"] == 2
    assert state["missing"] == 1
    assert state["practicedToday"] is False

    assert "Tag 2 von 3" in practice_text(state)


def test_a_reached_target_says_so():

    state = streak_state({"lastDate": "20260902", "streak": 3}, "20260902")

    assert state["done"] is True
    assert state["missing"] == 0

    assert "abgehakt" in practice_text(state)


def test_without_a_session_nothing_is_claimed():

    assert streak_state({}, "20260902")["streak"] == 0

    assert practice_text(streak_state({}, "20260902")) == ""


def test_the_streak_is_matched_by_lesson_id(tmp_path, monkeypatch):
    """
    Zugeordnet wird über die Lektions-ID des Katalogs, nicht über eine
    zweite Übersetzung Spec -> Slug: die gäbe es dann zweimal, und die
    zweite läge irgendwann daneben.
    """

    academy = _service(tmp_path, monkeypatch)

    apply_dummy_practice_session(
        academy,
        _payload(character="Windschritt", spec_key="MAGE_FIRE", date="20260806"),
    )

    entries = practice_payload(academy, "Windschritt")

    assert entries[0]["lessonId"] == "mage-fire.rotation.dummy_practice"

    assert practice_for_lessons(
        entries, ["mage-fire.rotation.dummy_practice", "generic.a"]
    ) is entries[0]

    #
    # Ein fremder Katalog bekommt keine Serie untergeschoben.
    #

    assert practice_for_lessons(entries, ["warrior-arms.rotation.dummy_practice"]) is None
