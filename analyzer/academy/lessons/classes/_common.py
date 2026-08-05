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
from analyzer.models import (  # noqa: F401
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
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


def buff_uptime_check(ability: str, target: float = 90.0) -> LessonCheck:
    """
    Wie `uptime_check`, aber für Effekte auf einem selbst - die aktive
    Schadensminderung eines Tanks und die Selbstbuffs, die zur
    Rotation gehören (Schnetzeln, Wildes Brüllen, Inquisition).

    Eine eigene Kennzahl, weil ein Effekt auf einem selbst weder DoT
    noch HoT ist: über die DoT-Liste gesucht wäre er nie zu finden und
    die Lektion dauerhaft "keine Daten".
    """

    return LessonCheck(
        metric="buff_uptime",
        comparison=CHECK_AT_LEAST,
        target=target,
        subject=ability,
        unit="%",
        label=f"Uptime von {ability}",
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


def interrupt_check() -> LessonCheck:
    """
    Keine verpasste Unterbrechung.

    Absichtlich über die **Fehler** und nicht über die Zahl der
    erfolgreichen Unterbrechungen: wie viele Gelegenheiten jemand
    hatte, hängt von Aufstellung und Zuteilung ab - wer nie an der
    Reihe war, hätte sonst dauerhaft eine schlechte Bewertung.
    """

    return LessonCheck(
        metric="mechanic_count",
        comparison=CHECK_AT_MOST,
        target=0.0,
        subject=MECHANIC_INTERRUPT,
        unit="×",
        label="Verpasste Unterbrechungen",
    )


def defensive_check() -> LessonCheck:
    """
    Kein ungenutztes Defensivfenster.
    """

    return LessonCheck(
        metric="mechanic_count",
        comparison=CHECK_AT_MOST,
        target=0.0,
        subject=MECHANIC_DEFENSIVE,
        unit="×",
        label="Ungenutzte Defensivfenster",
    )


def dispel_check(target: float = 1.0) -> LessonCheck:
    """
    Mindestens so viele entfernte Effekte.

    Anders als bei den Unterbrechungen ist der Zähler hier
    aussagekräftig: entfernbare Effekte liegen im Raid an, ob jemand
    zuständig war oder nicht - und `_dispels` liefert ausdrücklich
    "keine Daten", wenn der Kampf gar keine kannte.
    """

    return LessonCheck(
        metric="dispels",
        comparison=CHECK_AT_LEAST,
        target=target,
        unit="×",
        label="Entfernte Effekte",
    )
