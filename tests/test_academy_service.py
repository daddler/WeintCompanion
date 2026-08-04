"""
Fortschritt und Lektionsauswahl der Academy auf der Platte.

Der Kernpunkt: gespeichert werden die **abgewählten** Lektionen, nicht
die gewählten. Andersherum wäre jeder Katalogausbau für bestehende
Nutzer unsichtbar geblieben - eine neu hinzugefügte Lektion stünde in
keiner gespeicherten Auswahl und würde nie erscheinen.

Dazu die übliche Absicherung einer Datei, die der Nutzer verlieren
kann: eine kaputte Datei darf die Academy nicht unbenutzbar machen,
und ein Absturz mitten im Schreiben keine halbe Datei hinterlassen.
"""

import json

from analyzer.academy.lessons import GENERIC_LESSONS
from analyzer.academy.models import Lesson, PlayerProfile
from analyzer.models import Actor

from core.academy_service import PROGRESS_FILE, AcademyService
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


def _profile():

    return PlayerProfile(
        actor=Actor(
            name="Windschritt",
            class_name="Monk",
            spec="Windwandler",
            role="dps",
        ),
        ratings=(),
    )


#
# --------------------------------------------------
# Abwahl
# --------------------------------------------------
#


def test_nothing_is_excluded_by_default(tmp_path, monkeypatch):
    """
    Alles an, ohne dass der Nutzer je etwas bestätigen musste.
    """

    service = _service(tmp_path, monkeypatch)

    assert service.excluded_for("Windschritt") == frozenset()

    assert service.is_enabled("Windschritt", "generic.rotation.uptime")


def test_excluding_a_lesson_persists(tmp_path, monkeypatch):

    service = _service(tmp_path, monkeypatch)

    service.set_enabled("Windschritt", "generic.rotation.uptime", False)

    reloaded = _service(tmp_path, monkeypatch)

    assert reloaded.is_enabled("Windschritt", "generic.rotation.uptime") is False

    #
    # Und nur für diesen Charakter.
    #

    assert reloaded.is_enabled("Nachtblatt", "generic.rotation.uptime") is True


def test_a_new_lesson_is_active_without_any_migration(tmp_path, monkeypatch):
    """
    Der eigentliche Grund für die Speicherung von Ausschlüssen: eine
    Lektion, die es beim letzten Speichern noch gar nicht gab, muss
    trotzdem aktiv sein.
    """

    service = _service(tmp_path, monkeypatch)

    service.set_enabled("Windschritt", "generic.rotation.uptime", False)

    assert service.is_enabled("Windschritt", "brandneue.lektion") is True


def test_re_enabling_removes_the_exclusion(tmp_path, monkeypatch):

    service = _service(tmp_path, monkeypatch)

    service.set_enabled("Windschritt", "generic.rotation.uptime", False)
    service.set_enabled("Windschritt", "generic.rotation.uptime", True)

    assert service.excluded_for("Windschritt") == frozenset()


def test_reset_selection_brings_everything_back(tmp_path, monkeypatch):

    service = _service(tmp_path, monkeypatch)

    for lesson in GENERIC_LESSONS[:3]:

        service.set_enabled("Windschritt", lesson.lesson_id, False)

    service.reset_selection("Windschritt")

    assert service.excluded_for("Windschritt") == frozenset()


def test_excluded_lessons_leave_the_progress_denominator(tmp_path, monkeypatch):
    """
    Sonst könnte die Fortschrittsanzeige nie 100 Prozent erreichen:
    der Nenner enthielte Lektionen, die der Spieler ausdrücklich nicht
    bearbeiten will.
    """

    service = _service(tmp_path, monkeypatch)

    profile = _profile()

    _done, before = service.progress_for(profile)

    service.set_enabled(profile.name, GENERIC_LESSONS[0].lesson_id, False)

    _done, after = service.progress_for(profile)

    assert after == before - 1


#
# --------------------------------------------------
# Datei
# --------------------------------------------------
#


def test_an_old_file_without_the_new_section_still_loads(tmp_path, monkeypatch):
    """
    Bestandsdateien kennen nur "completed". Sie dürfen nicht
    verworfen werden.
    """

    (tmp_path / PROGRESS_FILE).write_text(
        json.dumps({"completed": {"Windschritt": ["generic.rotation.uptime"]}}),
        encoding="utf-8",
    )

    service = _service(tmp_path, monkeypatch)

    assert service.is_completed("Windschritt", "generic.rotation.uptime")

    assert service.excluded_for("Windschritt") == frozenset()


def test_a_corrupt_file_is_discarded_with_a_warning(tmp_path, monkeypatch):
    """
    Ein defekter Fortschritt darf die Academy nicht unbenutzbar
    machen.
    """

    (tmp_path / PROGRESS_FILE).write_text("{kein json", encoding="utf-8")

    service = _service(tmp_path, monkeypatch)

    assert service.data == {"completed": {}, "excluded": {}, "dummy_practice": {}}

    assert service.manager.logger.warnings


def test_saving_leaves_no_temporary_file(tmp_path, monkeypatch):
    """
    Geschrieben wird erst temporär, dann ersetzt - ein Absturz mitten
    im Schreiben darf keine halbe Datei hinterlassen.
    """

    service = _service(tmp_path, monkeypatch)

    service.set_enabled("Windschritt", "generic.rotation.uptime", False)

    assert (tmp_path / PROGRESS_FILE).exists()

    assert not list(tmp_path.glob("*.tmp"))


def test_completed_and_excluded_are_independent(tmp_path, monkeypatch):
    """
    Der Haken ist die eigene Angabe, die Abwahl eine Anzeigefrage.
    Das eine zurückzusetzen darf das andere nicht anfassen.
    """

    service = _service(tmp_path, monkeypatch)

    lesson_id = GENERIC_LESSONS[0].lesson_id

    service.set_completed("Windschritt", lesson_id, True)
    service.set_enabled("Windschritt", lesson_id, False)

    service.reset("Windschritt")

    assert service.is_completed("Windschritt", lesson_id) is False
    assert service.is_enabled("Windschritt", lesson_id) is False

    service.set_completed("Windschritt", lesson_id, True)
    service.reset_selection("Windschritt")

    assert service.is_completed("Windschritt", lesson_id) is True
    assert service.is_enabled("Windschritt", lesson_id) is True
