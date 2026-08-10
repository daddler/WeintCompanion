"""
Die Nutzlasten, die WeintTV und die Academy ins Addon bringen.

Zwei Dinge werden hier festgenagelt, weil sie sonst unbemerkt
auseinanderlaufen:

* Die Feldnamen. Das Addon liest sie in modules/weinttv.lua und
  modules/academy.lua wörtlich - ein umbenanntes Feld fällt dort
  nicht als Fehler auf, die Spalte bleibt einfach leer.
* Die beiden Konventionen aus der Companion: null Sterne heißen
  "keine Daten" und nicht "schlecht", und at == -1 heißt "kein
  Zeitpunkt bekannt" und nicht "Sekunde 0". Würde eines von beidem
  beim Übersetzen normalisiert, läse das Addon eine schlechte
  Bewertung bzw. einen Zeitstempel, wo in Wahrheit nichts vorliegt.
"""

import pytest

from addon.addon_payloads import (
    build_academy_catalog,
    build_academy_state,
    build_weinttv_report,
)
from analyzer.academy.models import (
    CheckResult,
    Lesson,
    LessonCheck,
    LessonResult,
    PlanItem,
    PlayerProfile,
    SkillRating,
    TrainingPlan,
)
from analyzer.models import (
    AbilityDamage,
    ActivityEntry,
    Actor,
    ConsumableState,
    CooldownUsage,
    DamageTakenEntry,
    EncounterInfo,
    MechanicIssue,
    MovementEntry,
    RaidSnapshot,
    SupportEvent,
    UptimeEntry,
)


ACTOR = Actor(
    name="Testchar",
    class_name="Warrior",
    spec="Waffen",
    role="dps",
)


def _snapshot() -> RaidSnapshot:

    return RaidSnapshot(
        captured_at=1735689600.7,
        source_label="WarcraftLogs",
        in_combat=True,
        encounter=EncounterInfo(
            encounter_id=1,
            name="Horridon",
            instance="Thron des Donners",
            difficulty="Heroisch",
            raid_size=25,
        ),
        pull_number=7,
        pull_seconds=187.0,
        boss_health_percent=42.0,
        raid_size=25,
        damage_taken=(
            DamageTakenEntry(
                actor_name="Testchar",
                total=812000.0,
                avoidable=120000.0,
                unavoidable=692000.0,
                hits=84,
                avoidable_hits=3,
                abilities=(
                    AbilityDamage(
                        ability="Triple Puncture",
                        amount=120000.0,
                        hits=3,
                        verdict="avoidable",
                        note="Frontalkegel verlassen",
                        source_name="Horridon",
                    ),
                ),
            ),
        ),
        dot_uptimes=(
            UptimeEntry(
                actor_name="Testchar",
                ability="Tiefe Wunden",
                uptime_percent=88.5,
                kind="dot",
                applications=12,
                target="Horridon",
                expected_percent=95.0,
            ),
        ),
        hot_uptimes=(
            UptimeEntry(
                actor_name="Heiler",
                ability="Verjüngung",
                uptime_percent=71.0,
                kind="hot",
            ),
        ),
        activity=(
            ActivityEntry(
                actor_name="Testchar",
                active_percent=92.1,
                casts=210,
                apm=41.3,
                longest_gap=4.2,
            ),
        ),
        movement=(
            MovementEntry(
                actor_name="Testchar",
                meters=312.5,
                meters_per_second=1.7,
                avoidable_hits=3,
            ),
        ),
        cooldown_usage=(
            CooldownUsage(
                actor_name="Testchar",
                ability="Todeswunsch",
                cast_times=(),
                cooldown=180.0,
                possible=2,
                in_burst=0,
            ),
        ),
        interrupts=(
            SupportEvent(
                actor_name="Testchar",
                kind="interrupt",
                at_seconds=45.0,
                target="Dinomantin",
                ability="Zurechtstutzen",
            ),
        ),
        dispels=(
            SupportEvent(
                actor_name="Heiler",
                kind="dispel",
                at_seconds=60.0,
            ),
        ),
        mechanics=(
            MechanicIssue(
                actor_name="Testchar",
                mechanic="In der Fläche gestanden",
                count=3,
                severity="error",
                category="movement",
                at_seconds=-1.0,
            ),
        ),
        consumables=(
            ConsumableState(
                label="Flask",
                used=24,
                total=25,
                missing=("Dritter",),
            ),
        ),
        warnings=("Datenquelle 20 s alt",),
    )


# --------------------------------------------------
# WeintTV
# --------------------------------------------------


def test_report_carries_the_fight_context():

    report = build_weinttv_report(_snapshot(), "Testchar")

    assert report["me"] == "Testchar"
    assert report["pull"] == 7
    assert report["encounter"]["name"] == "Horridon"
    assert report["encounter"]["difficulty"] == "Heroisch"
    assert report["encounter"]["size"] == 25

    # Der Zeitstempel muss eine ganze Zahl sein: das Addon gibt ihn
    # unverändert an date() weiter.
    assert isinstance(report["capturedAt"], int)


def test_report_keeps_the_ability_verdict_and_advice():

    report = build_weinttv_report(_snapshot(), "Testchar")

    ability = report["damageTaken"][0]["abilities"][0]

    assert ability["verdict"] == "avoidable"
    assert ability["note"] == "Frontalkegel verlassen"

    # Die Ingame-Seite filtert selbst auf verdict == "avoidable" -
    # "unknown" darf hier nicht vorsorglich zu "avoidable" werden.
    assert ability["source"] == "Horridon"


def test_report_merges_dot_and_hot_into_one_list():

    report = build_weinttv_report(_snapshot(), "Testchar")

    kinds = sorted(entry["kind"] for entry in report["uptimes"])

    assert kinds == ["dot", "hot"]


def test_report_merges_interrupts_and_dispels():

    report = build_weinttv_report(_snapshot(), "Testchar")

    kinds = sorted(entry["kind"] for entry in report["support"])

    assert kinds == ["dispel", "interrupt"]


def test_report_keeps_missing_timestamp_as_minus_one():

    report = build_weinttv_report(_snapshot(), "Testchar")

    # -1 heißt "kein Zeitpunkt bekannt". Auf 0 normalisiert würde das
    # Addon "00:00" anzeigen und damit einen Zeitpunkt behaupten.
    assert report["mechanics"][0]["at"] == -1.0


def test_report_keeps_unused_cooldowns():

    report = build_weinttv_report(_snapshot(), "Testchar")

    cooldown = report["cooldowns"][0]

    assert cooldown["uses"] == 0
    assert cooldown["castTimes"] == []
    assert cooldown["possible"] == 2


def test_report_marks_a_kill_by_boss_health():

    snapshot = _snapshot()

    assert build_weinttv_report(snapshot, "")["kill"] is False

    killed = RaidSnapshot(
        raid_size=25,
        in_combat=True,
        pull_seconds=10.0,
        boss_health_percent=0.0,
    )

    assert build_weinttv_report(killed, "")["kill"] is True


def test_report_names_the_reason_when_analysis_is_missing():

    # Kein Raid erkannt: hasAnalysis False UND eine benannte Ursache,
    # damit das Addon nicht nur eine leere Tabelle zeigt.
    empty = RaidSnapshot.empty("Keine Datenquelle")

    report = build_weinttv_report(empty, "")

    assert report["hasAnalysis"] is False
    assert report["gap"] == "no_raid"


def test_report_has_no_gap_when_the_analysis_is_complete():

    report = build_weinttv_report(_snapshot(), "Testchar")

    assert report["hasAnalysis"] is True
    assert report["gap"] == ""


# --------------------------------------------------
# Academy
# --------------------------------------------------


def _lesson(lesson_id="gen_active", **kwargs) -> Lesson:

    defaults = dict(
        lesson_id=lesson_id,
        title="Aktivzeit hochhalten",
        category="rotation",
        summary="Weniger Leerlauf.",
        steps=("Instants nutzen", "Vorab casten"),
        class_name="",
        spec="",
        encounter="",
        roles=(),
        checks=(),
    )

    defaults.update(kwargs)

    return Lesson(**defaults)


def test_catalog_lists_every_category_in_the_companion_order():

    catalog = build_academy_catalog([_lesson()])

    assert [entry["id"] for entry in catalog["categories"]] == [
        "rotation", "movement", "cooldowns", "mechanics", "survival", "output",
    ]

    assert catalog["categories"][0]["label"] == "Rotation"
    assert catalog["categories"][0]["hint"]


def test_catalog_uses_the_field_names_the_addon_reads():

    lesson = _lesson(class_name="Warrior", roles=("dps",), encounter="Horridon")

    entry = build_academy_catalog([lesson])["lessons"][0]

    # class_name/lesson_id heißen im Addon class/id - AppliesToMe in
    # modules/academy.lua vergleicht genau diese Felder.
    assert entry["id"] == "gen_active"
    assert entry["class"] == "Warrior"
    assert entry["roles"] == ["dps"]
    assert entry["encounter"] == "Horridon"
    assert entry["steps"] == ["Instants nutzen", "Vorab casten"]


def _profile(ratings) -> PlayerProfile:

    return PlayerProfile(
        actor=ACTOR,
        ratings=ratings,
        encounter_name="Horridon",
        sample_size=7,
    )


def test_state_keeps_zero_stars_as_zero():

    profile = _profile((
        SkillRating(category="rotation", stars=4, detail="Aktivzeit 92 %."),
        SkillRating(category="survival", stars=0, detail=""),
    ))

    state = build_academy_state(
        profile,
        TrainingPlan(),
        _snapshot(),
        frozenset(),
        frozenset(),
    )

    stars = {entry["category"]: entry["stars"] for entry in state["ratings"]}

    # 0 heißt "keine Daten". Weder anheben noch die Zeile weglassen -
    # sonst zeigt das Addon eine schlechte statt gar keiner Bewertung.
    assert stars == {"rotation": 4, "survival": 0}


def test_state_preserves_the_plan_order():

    lessons = [_lesson("a"), _lesson("b"), _lesson("c")]

    plan = TrainingPlan(
        items=tuple(PlanItem(lesson=lesson) for lesson in lessons),
    )

    state = build_academy_state(
        _profile(()),
        plan,
        _snapshot(),
        frozenset(),
        frozenset(),
    )

    # Die Reihenfolge entsteht in evaluator.build_plan() aus den
    # schwächsten Bereichen - das Addon darf sie nicht neu sortieren
    # und bekommt sie deshalb fertig.
    assert state["plan"] == ["a", "b", "c"]


def test_state_carries_check_details_but_not_lessons_without_result():

    check = LessonCheck(metric="active_percent", target=95.0)

    with_result = PlanItem(
        lesson=_lesson("with_result"),
        result=LessonResult(
            lesson=_lesson("with_result"),
            status="failed",
            checks=(
                CheckResult(
                    check=check,
                    status="failed",
                    value=92.0,
                    detail="Aktivzeit: 92 % (Ziel ≥ 95 %)",
                    at_seconds=142.5,
                ),
            ),
        ),
    )

    without_result = PlanItem(lesson=_lesson("without_result"))

    state = build_academy_state(
        _profile(()),
        TrainingPlan(items=(with_result, without_result)),
        _snapshot(),
        frozenset(),
        frozenset(),
    )

    assert set(state["results"]) == {"with_result"}

    result = state["results"]["with_result"]

    assert result["status"] == "failed"
    assert result["checks"][0]["detail"] == "Aktivzeit: 92 % (Ziel ≥ 95 %)"


def test_state_reports_progress_sorted_and_stable():

    state = build_academy_state(
        _profile(()),
        TrainingPlan(),
        _snapshot(),
        frozenset({"b", "a"}),
        frozenset({"z"}),
    )

    # Sortiert, damit der Vergleich in AddonAnalysisSync nicht bei
    # jedem Lauf durch eine andere Mengenreihenfolge anschlägt.
    assert state["completed"] == ["a", "b"]
    assert state["excluded"] == ["z"]


def test_state_describes_the_character():

    state = build_academy_state(
        _profile(()),
        TrainingPlan(),
        _snapshot(),
        frozenset(),
        frozenset(),
    )

    assert state["character"] == "Testchar"
    assert state["actor"] == {
        "name": "Testchar",
        "class": "Warrior",
        "spec": "Waffen",
        "role": "dps",
    }
    assert state["encounter"] == "Horridon"
    assert state["pull"] == 7


def test_state_survives_a_profile_without_actor():

    profile = PlayerProfile(actor=None, ratings=(), encounter_name="")

    state = build_academy_state(
        profile,
        TrainingPlan(),
        RaidSnapshot.empty(),
        frozenset(),
        frozenset(),
    )

    assert state["actor"]["class"] == ""
    assert state["gap"] == "no_raid"


# --------------------------------------------------
# Eine Identität, nicht zwei
# --------------------------------------------------
#
# Bis 1.6.2 trug `academy_state.character` den `PlayerProfile.name` -
# und der ist wörtlich `"-"`, sobald der gewählte Spieler im Snapshot
# nicht gefunden wurde. `weinttv_report.me` trug im selben Atemzug den
# echten Namen. Das Addon bekam also zwei Antworten auf dieselbe Frage
# und musste raten, welche gilt; sichtbar wurde das als "im Spiel
# steht ein anderer Charakter".
# --------------------------------------------------


def test_beide_nutzlasten_nennen_denselben_charakter():

    profile = PlayerProfile(actor=None, ratings=(), encounter_name="")

    snapshot = RaidSnapshot.empty()

    state = build_academy_state(
        profile,
        TrainingPlan(),
        snapshot,
        frozenset(),
        frozenset(),
        character="Aldrin",
    )

    report = build_weinttv_report(snapshot, "Aldrin")

    assert state["character"] == report["me"] == "Aldrin"


def test_der_unname_erreicht_die_leitung_nie():
    """
    Weder als `character` noch als Anzeigename im `actor`-Block.
    """

    profile = PlayerProfile(actor=None, ratings=(), encounter_name="")

    state = build_academy_state(
        profile,
        TrainingPlan(),
        RaidSnapshot.empty(),
        frozenset(),
        frozenset(),
        character="Aldrin",
    )

    assert profile.name == "-"          # die Quelle des Problems
    assert state["character"] == "Aldrin"
    assert state["actor"]["name"] == "Aldrin"


def test_hasActor_unterscheidet_unbewertet_von_schlecht():
    """
    Ohne diese Angabe zeigt das Addon fünf Null-Stern-Zeilen und kann
    nicht sagen, ob die Bewertung fehlt oder schlecht ist.
    """

    ohne = build_academy_state(
        PlayerProfile(actor=None, ratings=(), encounter_name=""),
        TrainingPlan(),
        RaidSnapshot.empty(),
        frozenset(),
        frozenset(),
        character="Aldrin",
    )

    mit = build_academy_state(
        PlayerProfile(actor=ACTOR, ratings=(), encounter_name=""),
        TrainingPlan(),
        RaidSnapshot.empty(),
        frozenset(),
        frozenset(),
        character="Testchar",
    )

    assert ohne["hasActor"] is False
    assert mit["hasActor"] is True
