"""
Zusammenführung und Auswahl des Lektionskatalogs.

Vier Ebenen, von speziell nach allgemein:

    Boss        gilt nur im jeweiligen Kampf
    Spezialisierung
    Klasse      (Spezialisierung leer)
    Rolle
    allgemein   gilt immer

Die Reihenfolge ist zugleich die Auswahlreihenfolge: Spezielleres
zuerst. Dadurch bekommt ein Spieler, für dessen Spezialisierung
Inhalte hinterlegt sind, diese vor den allgemeinen Ratschlägen - und
ein Spieler ohne hinterlegte Inhalte bekommt trotzdem einen
vollständigen Plan. Diese Zusicherung galt schon vorher und bleibt.

Beim Import wird der Katalog auf **eindeutige IDs** geprüft. Das ist
kein Übereifer: eine doppelte ID würde eine Lektion unerreichbar
machen und - schlimmer - den Fortschritt zweier verschiedener
Lektionen unter einem Schlüssel vermischen. Lieber beim Start
scheitern als still falsch rechnen.
"""

from __future__ import annotations

from analyzer.academy.lessons.classes import spec_lessons
from analyzer.academy.lessons.encounters import ENCOUNTER_LESSONS
from analyzer.academy.lessons.generic import GENERIC_LESSONS
from analyzer.academy.lessons.roles import ROLE_LESSONS
from analyzer.academy.models import Lesson
from analyzer.models import Actor


SPEC_LESSONS: dict[tuple[str, str], tuple[Lesson, ...]] = spec_lessons()


def _all_lessons() -> tuple[Lesson, ...]:

    collected: list[Lesson] = []

    for lessons in SPEC_LESSONS.values():
        collected.extend(lessons)

    for lessons in ENCOUNTER_LESSONS.values():
        collected.extend(lessons)

    for lessons in ROLE_LESSONS.values():
        collected.extend(lessons)

    collected.extend(GENERIC_LESSONS)

    return tuple(collected)


_ALL: tuple[Lesson, ...] = _all_lessons()


def _build_index() -> dict[str, Lesson]:

    index: dict[str, Lesson] = {}

    for lesson in _ALL:

        if lesson.lesson_id in index:

            raise ValueError(
                f"Doppelte Lektions-ID im Katalog: "
                f"'{lesson.lesson_id}'. IDs sind der Schlüssel des "
                f"gespeicherten Fortschritts und müssen eindeutig sein."
            )

        index[lesson.lesson_id] = lesson

    return index


_BY_ID: dict[str, Lesson] = _build_index()


#
# --------------------------------------------------
# Auswahl
# --------------------------------------------------
#


def _matches_role(lesson: Lesson, actor: Actor | None) -> bool:

    if not lesson.roles:
        return True

    if actor is None:
        return False

    return actor.role in lesson.roles


def lessons_for_actor(
    actor: Actor | None,
    encounter_name: str = "",
) -> tuple[Lesson, ...]:
    """
    Alle für einen Spieler in Frage kommenden Lektionen, Spezielles
    zuerst.

    Ohne `actor` bleiben die allgemeinen Lektionen - so bekommt auch
    ein noch nicht erkannter Charakter einen sinnvollen Einstieg.
    """

    collected: list[Lesson] = []

    #
    # Boss zuerst: was gerade gespielt wird, ist am dringendsten.
    #

    if encounter_name:

        for name, lessons in ENCOUNTER_LESSONS.items():

            if name.lower() == encounter_name.strip().lower():
                collected.extend(lessons)

    if actor is not None:

        collected.extend(SPEC_LESSONS.get((actor.class_name, actor.spec), ()))

        #
        # Klassenweite Lektionen (Spezialisierung leer) - dort stehen
        # die Nutzfähigkeiten, die jede Spezialisierung mitbringt.
        #

        collected.extend(SPEC_LESSONS.get((actor.class_name, ""), ()))

        collected.extend(ROLE_LESSONS.get(actor.role, ()))

    collected.extend(GENERIC_LESSONS)

    #
    # Rollenfilter und Entdopplung in einem Durchgang - dieselbe
    # Lektion kann über zwei Wege hereinkommen.
    #

    seen: set[str] = set()

    result: list[Lesson] = []

    for lesson in collected:

        if lesson.lesson_id in seen:
            continue

        if not _matches_role(lesson, actor):
            continue

        seen.add(lesson.lesson_id)

        result.append(lesson)

    return tuple(result)


def lessons_in_category(
    actor: Actor | None,
    category: str,
    encounter_name: str = "",
) -> tuple[Lesson, ...]:
    """
    Die Lektionen eines Bereichs, in derselben Reihenfolge.
    """

    return tuple(
        lesson
        for lesson in lessons_for_actor(actor, encounter_name)
        if lesson.category == category
    )


def lessons_for_encounter(encounter_name: str) -> tuple[Lesson, ...]:

    for name, lessons in ENCOUNTER_LESSONS.items():

        if name.lower() == (encounter_name or "").strip().lower():
            return lessons

    return ()


def all_lessons() -> tuple[Lesson, ...]:
    """
    Der vollständige Katalog - für Übersichten und für die Prüfung
    auf eindeutige IDs.
    """

    return _ALL


def find_lesson(lesson_id: str) -> Lesson | None:

    return _BY_ID.get(lesson_id)


def known_encounters() -> tuple[str, ...]:

    return tuple(sorted(ENCOUNTER_LESSONS))
