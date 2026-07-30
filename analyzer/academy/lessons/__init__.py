"""
Der Lektionskatalog der WeintAcademy.

Aus einer Datei ist ein Paket geworden, weil ein Katalog, der jede
Klasse, jede Spezialisierung, jede Rolle und einzelne Bosse abdeckt,
in einer Datei mehrere tausend Zeilen hätte - und weil eine
Anpassung an einer Klasse dann jedes Mal dieselbe Datei berührt.

Aufbau:

    generic.py    allgemeine Lektionen, alle sechs Bereiche
    roles.py      nach Rolle (Tank, Heiler, Schadensausteiler)
    classes/      eine Datei je Klasse
    encounters.py bossbezogene Lektionen
    registry.py   Zusammenführung, Auswahlreihenfolge, ID-Prüfung

Die öffentlichen Namen sind unverändert geblieben, damit Bewerter,
Dienst und Oberfläche nichts davon merken.
"""

from analyzer.academy.lessons.encounters import ENCOUNTER_LESSONS
from analyzer.academy.lessons.generic import GENERIC_LESSONS
from analyzer.academy.lessons.registry import (
    SPEC_LESSONS,
    all_lessons,
    find_lesson,
    known_encounters,
    lessons_for_actor,
    lessons_for_encounter,
    lessons_in_category,
)
from analyzer.academy.lessons.roles import ROLE_LESSONS

__all__ = [
    "ENCOUNTER_LESSONS",
    "GENERIC_LESSONS",
    "ROLE_LESSONS",
    "SPEC_LESSONS",
    "all_lessons",
    "find_lesson",
    "known_encounters",
    "lessons_for_actor",
    "lessons_for_encounter",
    "lessons_in_category",
]
