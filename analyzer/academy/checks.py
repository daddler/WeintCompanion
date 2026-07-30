"""
Kriterien einer Lektion gegen einen Snapshot prüfen.

Das ist die Stelle, die den Trainingsplan automatisch macht: eine
Lektion sagt deklarativ "Aktivzeit mindestens 95 %", und hier wird
nachgesehen, ob das im gewählten Kampf zutraf.

**Die einzige Stelle**, die Metriknamen auf Snapshot-Zugriffe
abbildet. Das ist wichtig, weil ein Tippfehler im Katalog sonst
stillschweigend zu "keine Daten" führen würde, und zwar für immer -
niemandem fiele auf, dass eine Lektion nie geprüft wird. Über
`metric_names()` prüft ein Test, dass jeder im Katalog verwendete Name
hier existiert.

Zwei Regeln, die den Unterschied zwischen brauchbar und irreführend
machen:

1. **`None` heißt "keine Daten", nicht 0.** Ein Spieler ohne
   gemeldete Aktivzeit hat keine Aktivzeit von null Prozent - über
   ihn ist nichts bekannt. Diese Unterscheidung durchzuhalten ist der
   Grund, warum jede Auflösungsfunktion `None` zurückgeben kann.
2. **Jede Kennzahl kommt aus dem Snapshot.** Damit funktioniert die
   Prüfung live, im Archiv und während der Wiedergabe völlig
   gleich - und die Academy bewertet automatisch den Stand der
   gerade gezeigten Sekunde, ohne davon zu wissen.
"""

from __future__ import annotations

from analyzer.analysis.damage import has_usable_classification
from analyzer.models import (
    UPTIME_DOT,
    UPTIME_HOT,
    Actor,
    RaidSnapshot,
)
from analyzer.academy.models import (
    CHECK_AT_LEAST,
    CHECK_AT_MOST,
    CHECK_EQUALS,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNKNOWN,
    CheckResult,
    Lesson,
    LessonCheck,
    LessonResult,
)


#
# --------------------------------------------------
# Auflösung einzelner Kennzahlen
# --------------------------------------------------
#
# Jede Funktion bekommt (snapshot, actor, check) und liefert eine Zahl
# oder None.
#


def _active_percent(snapshot, actor, check):

    entry = snapshot.activity_of(actor.name)

    return entry.active_percent if entry else None


def _apm(snapshot, actor, check):

    entry = snapshot.activity_of(actor.name)

    return entry.apm if entry else None


def _casts(snapshot, actor, check):

    entry = snapshot.activity_of(actor.name)

    return float(entry.casts) if entry else None


def _uptime(snapshot, actor, check, kind):
    """
    Wirkungsdauer.

    Ohne `subject` der Mittelwert über die eigenen Effekte - das ist
    die brauchbare Näherung für "halte deine Effekte oben", ohne dass
    der Katalog jede Fähigkeit einzeln kennen muss.
    """

    rows = snapshot.uptimes_of(actor.name, kind)

    if check.subject:

        rows = tuple(
            entry
            for entry in rows
            if entry.ability.lower() == check.subject.lower()
        )

    if not rows:
        return None

    return sum(entry.uptime_percent for entry in rows) / len(rows)


def _dot_uptime(snapshot, actor, check):

    return _uptime(snapshot, actor, check, UPTIME_DOT)


def _hot_uptime(snapshot, actor, check):

    return _uptime(snapshot, actor, check, UPTIME_HOT)


def _cooldowns(snapshot, actor, check):
    """
    Die eigenen Cooldowns, optional auf eine Fähigkeit eingeschränkt.
    """

    rows = snapshot.cooldowns_of(actor.name)

    if check.subject:

        rows = tuple(
            usage
            for usage in rows
            if usage.ability.lower() == check.subject.lower()
        )

    return rows


def _cooldown_usage(snapshot, actor, check):

    rows = [
        usage
        for usage in _cooldowns(snapshot, actor, check)
        if usage.possible > 0
    ]

    if not rows:
        return None

    return sum(usage.efficiency for usage in rows) / len(rows) * 100.0


def _cooldown_alignment(snapshot, actor, check):
    """
    Anteil der Einsätze, die in ein Heldentum-Fenster fielen.

    Ohne Fenster im Kampf ist die Frage nicht beantwortbar - dann
    None statt null Prozent, sonst würde ein Kampf ohne Heldentum
    jedem Spieler eine verpasste Ausrichtung anlasten.
    """

    if not snapshot.heroism_windows:
        return None

    rows = [
        usage
        for usage in _cooldowns(snapshot, actor, check)
        if usage.cast_times
    ]

    if not rows:
        return None

    used = sum(len(usage.cast_times) for usage in rows)

    in_burst = sum(usage.in_burst for usage in rows)

    return in_burst / used * 100.0 if used else None


def _cooldown_wasted(snapshot, actor, check):

    rows = [
        usage
        for usage in _cooldowns(snapshot, actor, check)
        if usage.possible > 0
    ]

    if not rows:
        return None

    return float(sum(usage.wasted for usage in rows))


def _movement_meters(snapshot, actor, check):

    entry = snapshot.movement_of(actor.name)

    return entry.meters if entry else None


def _movement_ratio(snapshot, actor, check):
    """
    Laufweg im Verhältnis zum Raidschnitt, in Prozent.

    100 heißt "genau Durchschnitt". Absolute Meter zu bewerten wäre
    unsinnig: ein Nahkämpfer läuft zwangsläufig weiter als ein
    Zauberer.
    """

    entry = snapshot.movement_of(actor.name)

    average = snapshot.movement_average

    if entry is None or average <= 0:
        return None

    return entry.meters / average * 100.0


def _damage_taken(snapshot, actor, check):

    entry = snapshot.damage_taken_of(actor.name)

    return entry.total if entry else None


def _avoidable_damage(snapshot, actor, check):

    entry = snapshot.damage_taken_of(actor.name)

    if not has_usable_classification(entry):
        return None

    return entry.avoidable


def _avoidable_share(snapshot, actor, check):

    entry = snapshot.damage_taken_of(actor.name)

    if not has_usable_classification(entry):
        return None

    return entry.avoidable_share * 100.0


def _avoidable_hits(snapshot, actor, check):

    entry = snapshot.damage_taken_of(actor.name)

    if not has_usable_classification(entry):
        return None

    return float(entry.avoidable_hits)


def _deaths(snapshot, actor, check):

    if not snapshot.has_data:
        return None

    return float(len(snapshot.deaths_of(actor.name)))


def _interrupts(snapshot, actor, check):

    if not snapshot.interrupts:
        return None

    return float(len(snapshot.interrupts_of(actor.name)))


def _dispels(snapshot, actor, check):

    if not snapshot.dispels:
        return None

    return float(len(snapshot.dispels_of(actor.name)))


def _mechanic_count(snapshot, actor, check):
    """
    Zahl der Mechanikfehler, optional auf eine MECHANIC_*-Kategorie
    eingeschränkt.
    """

    if not snapshot.has_data:
        return None

    return float(
        sum(
            issue.count
            for issue in snapshot.mechanics
            if issue.actor_name == actor.name
            and (not check.subject or issue.category == check.subject)
        )
    )


def _consumables_missing(snapshot, actor, check):

    if not snapshot.consumables:
        return None

    return float(
        sum(
            1
            for state in snapshot.consumables
            if actor.name in state.missing
        )
    )


def _rank_ratio(rows, actor):

    if not rows:
        return None

    best = rows[0].value

    for entry in rows:

        if entry.actor.name == actor.name:

            return entry.value / best * 100.0 if best > 0 else None

    return None


def _damage_rank_ratio(snapshot, actor, check):

    return _rank_ratio(snapshot.top_damage, actor)


def _healing_rank_ratio(snapshot, actor, check):

    return _rank_ratio(snapshot.top_healing, actor)


#
# --------------------------------------------------
# Registrierung
# --------------------------------------------------
#

METRIC_RESOLVERS = {

    "active_percent": _active_percent,
    "apm": _apm,
    "casts": _casts,

    "dot_uptime": _dot_uptime,
    "hot_uptime": _hot_uptime,

    "cooldown_usage": _cooldown_usage,
    "cooldown_alignment": _cooldown_alignment,
    "cooldown_wasted": _cooldown_wasted,

    "movement_meters": _movement_meters,
    "movement_ratio": _movement_ratio,

    "damage_taken": _damage_taken,
    "avoidable_damage": _avoidable_damage,
    "avoidable_share": _avoidable_share,
    "avoidable_hits": _avoidable_hits,

    "deaths": _deaths,
    "interrupts": _interrupts,
    "dispels": _dispels,
    "mechanic_count": _mechanic_count,
    "consumables_missing": _consumables_missing,

    "damage_rank_ratio": _damage_rank_ratio,
    "healing_rank_ratio": _healing_rank_ratio,

}


def metric_names() -> tuple[str, ...]:
    """
    Alle auflösbaren Kennzahlen. Der Katalogtest hängt daran: ein
    Tippfehler in einer Lektion soll die Testsuite rot machen und
    nicht still zu "keine Daten" führen.
    """

    return tuple(sorted(METRIC_RESOLVERS))


def resolve(
    snapshot: RaidSnapshot,
    actor: Actor,
    check: LessonCheck,
) -> float | None:
    """
    Der Wert einer Kennzahl, oder None wenn sie sich nicht bestimmen
    lässt.

    Wirft nie: eine unbekannte Kennzahl oder ein Fehler beim Auflesen
    ist "keine Daten", nicht ein Absturz der Academy.
    """

    resolver = METRIC_RESOLVERS.get(check.metric)

    if resolver is None or actor is None or snapshot is None:
        return None

    try:
        return resolver(snapshot, actor, check)

    except Exception:
        return None


#
# --------------------------------------------------
# Prüfung
# --------------------------------------------------
#


def _compare(value: float, comparison: str, target: float) -> bool:

    if comparison == CHECK_AT_MOST:
        return value <= target

    if comparison == CHECK_EQUALS:
        return abs(value - target) < 1e-9

    return value >= target


def _format(value: float, unit: str) -> str:

    if unit == "%":
        return f"{value:.0f} %"

    if unit == "m":
        return f"{value:.0f} m"

    if unit == "×":
        return f"{value:.0f}×"

    if float(value).is_integer():
        return f"{value:.0f}"

    return f"{value:.1f}"


def _moment(snapshot: RaidSnapshot, actor: Actor, check: LessonCheck) -> float:
    """
    Der Zeitpunkt, an dem sich ein gescheitertes Kriterium festmacht -
    das Sprungziel in die Wiedergabe. -1, wenn es keinen gibt.
    """

    if check.metric == "deaths":

        deaths = snapshot.deaths_of(actor.name)

        return deaths[0].at_seconds if deaths else -1.0

    if check.metric in ("avoidable_hits", "avoidable_share", "avoidable_damage"):

        for issue in snapshot.mechanics:

            if issue.actor_name == actor.name and issue.at_seconds >= 0:
                return issue.at_seconds

    if check.metric == "cooldown_alignment" and snapshot.heroism_windows:

        return snapshot.heroism_windows[0].start

    return -1.0


def evaluate_check(
    snapshot: RaidSnapshot,
    actor: Actor,
    check: LessonCheck,
) -> CheckResult:

    value = resolve(snapshot, actor, check)

    if value is None:

        return CheckResult(
            check=check,
            status=STATUS_UNKNOWN,
            detail=(
                check.label
                or f"{check.metric}: im gewählten Log nicht messbar."
            ),
        )

    passed = _compare(value, check.comparison, check.target)

    arrow = {
        CHECK_AT_LEAST: "≥",
        CHECK_AT_MOST: "≤",
        CHECK_EQUALS: "=",
    }.get(check.comparison, "≥")

    return CheckResult(
        check=check,
        status=STATUS_PASSED if passed else STATUS_FAILED,
        value=value,
        detail=(
            f"{check.label or check.metric}: "
            f"{_format(value, check.unit)} "
            f"(Ziel {arrow} {_format(check.target, check.unit)})"
        ),
        at_seconds=(
            -1.0
            if passed
            else _moment(snapshot, actor, check)
        ),
    )


def evaluate_lesson(
    snapshot: RaidSnapshot,
    actor: Actor,
    lesson: Lesson,
) -> LessonResult:
    """
    Das Gesamturteil zu einer Lektion.

    Kombinationsregel: ein gescheitertes Kriterium genügt für "nicht
    erfüllt". "Erfüllt" verlangt, dass alle Kriterien geprüft **und**
    erfüllt sind - bei Datenlücken bleibt es bei "keine Daten". Auf
    halber Evidenz einen Haken zu setzen wäre eine Behauptung.
    """

    if not lesson.checks or actor is None or snapshot is None:
        return LessonResult(lesson=lesson, status=STATUS_UNKNOWN)

    results = tuple(
        evaluate_check(snapshot, actor, check)
        for check in lesson.checks
    )

    if any(result.failed for result in results):
        status = STATUS_FAILED

    elif all(result.passed for result in results):
        status = STATUS_PASSED

    else:
        status = STATUS_UNKNOWN

    return LessonResult(
        lesson=lesson,
        status=status,
        checks=results,
    )
