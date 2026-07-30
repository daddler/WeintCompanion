"""
Klassenspezifische Lektionen, eine Datei je Klasse.

Diese Aufteilung ist Absicht: eine Datei je Klasse bleibt auch mit
mehreren Lektionen pro Spezialisierung überschaubar, und eine
Umstellung im Spiel betrifft genau eine Datei. Alles in einer Datei
wären mehrere tausend Zeilen, in denen niemand mehr etwas findet.
"""

from analyzer.academy.lessons.classes import (
    death_knight,
    druid,
    hunter,
    mage,
    monk,
    paladin,
    priest,
    rogue,
    shaman,
    warlock,
    warrior,
)


MODULES = (
    death_knight,
    druid,
    hunter,
    mage,
    monk,
    paladin,
    priest,
    rogue,
    shaman,
    warlock,
    warrior,
)


def spec_lessons() -> dict[tuple[str, str], tuple]:
    """
    Der zusammengeführte Katalog, geschlüsselt nach
    `(Klassenname, Spezialisierung)`.

    Eine leere Spezialisierung bedeutet "gilt für die ganze Klasse" -
    so lassen sich Nutzfähigkeiten (Gesundheitssteine, Totems,
    Anti-Magie-Zone) einmal hinterlegen statt in jeder Spezialisierung
    erneut.
    """

    table: dict[tuple[str, str], tuple] = {}

    for module in MODULES:

        for spec, lessons in module.SPEC_LESSONS.items():

            table[(module.CLASS_NAME, spec)] = lessons

    return table
