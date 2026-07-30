"""
Die automatische Prüfung des Trainingsplans.

Zwei Risiken sichert diese Datei ab, und beide sind still:

1. Ein Tippfehler im Metriknamen einer Lektion würde für immer
   "keine Daten" ergeben, ohne dass irgendetwas fehlschlägt.
2. Eine fehlende Kennzahl darf niemals als "nicht erfüllt" durchgehen -
   das wäre ein Vorwurf an den Spieler für eine Lücke der Datenquelle.
"""

import pytest

from analyzer.academy.checks import (
    METRIC_RESOLVERS,
    evaluate_check,
    evaluate_lesson,
    metric_names,
    resolve,
)
from analyzer.academy.lessons import all_lessons, find_lesson
from analyzer.academy.models import (
    CHECK_AT_LEAST,
    CHECK_AT_MOST,
    CHECK_EQUALS,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNKNOWN,
    Lesson,
    LessonCheck,
)
from analyzer.models import Actor, RaidSnapshot
from analyzer.providers.mock import PULL_SECONDS, MockRaidDataProvider


def _actor(name="Windschritt"):

    return Actor(
        name=name,
        class_name="Monk",
        spec="Windwandler",
        role="dps",
    )


def _snapshot():

    return MockRaidDataProvider()._combat_snapshot(1, PULL_SECONDS)


#
# --------------------------------------------------
# Katalog gegen Auflöser
# --------------------------------------------------
#


def test_every_metric_used_in_the_catalog_is_resolvable():
    """
    Der wichtigste Test dieser Datei.

    Ein Tippfehler in einem Metriknamen wäre sonst nicht zu bemerken:
    die Lektion bliebe dauerhaft auf "keine Daten" stehen, und das
    sieht von außen genauso aus wie eine ehrlich nicht messbare
    Lektion.
    """

    known = set(metric_names())

    unknown = [
        (lesson.lesson_id, check.metric)
        for lesson in all_lessons()
        for check in lesson.checks
        if check.metric not in known
    ]

    assert unknown == []


def test_every_resolver_survives_an_empty_snapshot():
    """
    Die Academy läuft auch, wenn gerade kein Kampf stattfindet.
    """

    snapshot = RaidSnapshot()

    for metric in metric_names():

        value = resolve(
            snapshot,
            _actor(),
            LessonCheck(metric=metric),
        )

        assert value is None or isinstance(value, float)


def test_an_unknown_metric_is_no_data_and_not_an_error():

    value = resolve(
        _snapshot(),
        _actor(),
        LessonCheck(metric="gibt.es.nicht"),
    )

    assert value is None


#
# --------------------------------------------------
# Vergleiche
# --------------------------------------------------
#


@pytest.mark.parametrize(
    "comparison, target, expected",
    [
        (CHECK_AT_LEAST, 50.0, STATUS_PASSED),
        (CHECK_AT_LEAST, 200.0, STATUS_FAILED),
        (CHECK_AT_MOST, 200.0, STATUS_PASSED),
        (CHECK_AT_MOST, 10.0, STATUS_FAILED),
    ],
)
def test_comparisons_decide_the_status(comparison, target, expected):

    result = evaluate_check(
        _snapshot(),
        _actor(),
        LessonCheck(
            metric="active_percent",
            comparison=comparison,
            target=target,
        ),
    )

    assert result.status == expected


def test_a_missing_value_never_becomes_a_failure():
    """
    Eine fehlende Kennzahl ist keine schlechte Leistung. Sie als
    "nicht erfüllt" zu werten wäre ein Vorwurf für eine Lücke der
    Datenquelle.
    """

    result = evaluate_check(
        RaidSnapshot(),
        _actor(),
        LessonCheck(
            metric="active_percent",
            comparison=CHECK_AT_LEAST,
            target=95.0,
        ),
    )

    assert result.status == STATUS_UNKNOWN
    assert result.value is None


def test_the_detail_names_value_and_target():
    """
    Ohne den Ist-gegen-Ziel-Text wäre "nicht erfüllt" für den Spieler
    nicht handlungsleitend.
    """

    result = evaluate_check(
        _snapshot(),
        _actor(),
        LessonCheck(
            metric="active_percent",
            comparison=CHECK_AT_LEAST,
            target=95.0,
            unit="%",
            label="Aktivzeit",
        ),
    )

    assert "Aktivzeit" in result.detail
    assert "Ziel" in result.detail
    assert "95" in result.detail


#
# --------------------------------------------------
# Zusammenfassung je Lektion
# --------------------------------------------------
#


def _lesson(*checks):

    return Lesson(
        lesson_id="test.lesson",
        title="Test",
        category="rotation",
        summary="",
        checks=checks,
    )


def test_all_checks_passing_means_passed():

    lesson = _lesson(
        LessonCheck(metric="active_percent", target=10.0),
        LessonCheck(metric="apm", target=1.0),
    )

    assert evaluate_lesson(_snapshot(), _actor(), lesson).status == STATUS_PASSED


def test_one_failing_check_is_enough_to_fail():

    lesson = _lesson(
        LessonCheck(metric="active_percent", target=10.0),
        LessonCheck(metric="apm", target=9999.0),
    )

    assert evaluate_lesson(_snapshot(), _actor(), lesson).status == STATUS_FAILED


def test_partial_evidence_stays_unknown():
    """
    Ein erfülltes Kriterium neben einem unbekannten ergibt kein
    "erfüllt" - auf halber Evidenz einen Haken zu setzen wäre eine
    Behauptung.
    """

    lesson = _lesson(
        LessonCheck(metric="active_percent", target=10.0),
        LessonCheck(metric="gibt.es.nicht", target=1.0),
    )

    assert evaluate_lesson(_snapshot(), _actor(), lesson).status == STATUS_UNKNOWN


def test_a_lesson_without_checks_is_unknown_not_passed():
    """
    Viele Lektionen sind grundsätzlich nicht messbar. Sie automatisch
    als erfüllt zu markieren wäre ein erfundener grüner Haken.
    """

    lesson = _lesson()

    result = evaluate_lesson(_snapshot(), _actor(), lesson)

    assert result.status == STATUS_UNKNOWN
    assert result.checks == ()


#
# --------------------------------------------------
# Sprungziel
# --------------------------------------------------
#


def test_a_failed_death_check_carries_the_moment():
    """
    Ohne Zeitpunkt gäbe es aus der Academy keinen Weg in die
    Wiedergabe.
    """

    snapshot = _snapshot()

    result = evaluate_lesson(
        snapshot,
        _actor("Bestienrufer"),
        find_lesson("generic.survival.stay_alive"),
    )

    assert result.status == STATUS_FAILED
    assert result.at_seconds > 0


def test_a_passed_check_has_no_moment():

    snapshot = _snapshot()

    result = evaluate_lesson(
        snapshot,
        _actor("Nachtblatt"),
        find_lesson("generic.survival.stay_alive"),
    )

    assert result.status == STATUS_PASSED
    assert result.at_seconds < 0
