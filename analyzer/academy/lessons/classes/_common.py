"""
Gemeinsame Importe der Klassendateien.

Jede Klassendatei braucht dieselbe Handvoll Namen. Sie hier zu
bündeln hält die eigentlichen Katalogdateien bei dem, worum es geht -
den Lektionen - statt bei zwölf Importzeilen.
"""

from analyzer.academy.models import (  # noqa: F401
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_OUTPUT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    CHECK_AT_LEAST,
    CHECK_AT_MOST,
    Lesson,
    LessonCheck,
)


def uptime_check(ability: str, target: float = 90.0) -> LessonCheck:
    """
    Ein Uptime-Kriterium für eine bestimmte Fähigkeit.

    Die weitaus häufigste Prüfung im Klassenkatalog - als Helfer
    geschrieben, damit eine Lektion nicht aus mehr Gerüst als Inhalt
    besteht.
    """

    return LessonCheck(
        metric="dot_uptime",
        comparison=CHECK_AT_LEAST,
        target=target,
        subject=ability,
        unit="%",
        label=f"Uptime von {ability}",
    )


def cooldown_check(ability: str, target: float = 85.0) -> LessonCheck:
    """
    Ein Nutzungskriterium für einen bestimmten Cooldown.
    """

    return LessonCheck(
        metric="cooldown_usage",
        comparison=CHECK_AT_LEAST,
        target=target,
        subject=ability,
        unit="%",
        label=f"Einsätze von {ability}",
    )


def hot_uptime_check(ability: str, target: float = 80.0) -> LessonCheck:
    """
    Wie `uptime_check`, aber für Heileffekte.

    Die Trennung ist nötig, weil DoTs und HoTs im Snapshot in
    getrennten Listen stehen - ein Heileffekt wäre über die
    DoT-Kennzahl nie auffindbar und die Lektion dauerhaft "keine
    Daten".
    """

    return LessonCheck(
        metric="hot_uptime",
        comparison=CHECK_AT_LEAST,
        target=target,
        subject=ability,
        unit="%",
        label=f"Uptime von {ability}",
    )
