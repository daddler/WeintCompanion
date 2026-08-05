"""
Die Academy-Auswertung entscheidet, was ein Spieler als Nächstes
üben soll. Die Tests sichern vor allem zwei Eigenschaften ab:
Bewertungen müssen rollengerecht sein, und der Trainingsplan muss
der größten Schwäche folgen.
"""

from analyzer.academy.evaluator import build_plan, build_profile, roster_names
from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ORDER,
    CATEGORY_OUTPUT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    MAX_STARS,
)
from analyzer.models import (
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    Actor,
    EncounterInfo,
    MechanicIssue,
    MetricEntry,
    RaidSnapshot,
)


def _actor(name, role=ROLE_DPS, class_name="Mage", spec="Feuer"):

    return Actor(name=name, class_name=class_name, spec=spec, role=role)


def _snapshot(**overrides):

    top = _actor("Spitze")
    mid = _actor("Mitte")
    tank = _actor("Panzer", role=ROLE_TANK, class_name="Warrior", spec="Schutz")
    healer = _actor("Heilerin", role=ROLE_HEALER, class_name="Priest", spec="Disziplin")

    base = dict(
        raid_size=4,
        pull_number=3,
        encounter=None,
        top_damage=(
            MetricEntry(actor=top, value=100_000.0),
            MetricEntry(actor=mid, value=60_000.0),
            MetricEntry(actor=tank, value=30_000.0),
        ),
        top_healing=(
            MetricEntry(actor=healer, value=50_000.0),
        ),
        tanks=(),
    )

    base.update(overrides)

    return RaidSnapshot(**base)


# --------------------------------------------------


def test_unknown_player_yields_an_explaining_profile_not_an_error():

    profile = build_profile(_snapshot(), "GibtEsNicht")

    assert profile.has_data is False
    assert profile.note
    assert profile.actor is None


def test_roster_names_are_sorted_and_complete():

    names = roster_names(_snapshot())

    assert names == ("Heilerin", "Mitte", "Panzer", "Spitze")


def test_every_category_is_rated_once_and_in_fixed_order():

    profile = build_profile(_snapshot(), "Spitze")

    assert [rating.category for rating in profile.ratings] == list(
        CATEGORY_ORDER
    )


def test_top_performer_gets_the_best_output_rating():

    profile = build_profile(_snapshot(), "Spitze")

    assert profile.rating(CATEGORY_OUTPUT).stars == MAX_STARS


def test_weak_performer_gets_a_low_output_rating():

    profile = build_profile(_snapshot(), "Mitte")

    assert profile.rating(CATEGORY_OUTPUT).stars < MAX_STARS


def test_rotation_is_not_derived_from_the_damage_ranking():
    """
    Der eigentliche Grund für den Umbau: "Rotation" war vorher nichts
    anderes als der Platz in der Schadensliste. Das ist eine
    Ausrüstungsbewertung, keine Aussage darüber, ob jemand seine
    Knöpfe richtig gedrückt hat.

    Ohne Aktivzeit- und Uptime-Daten darf Rotation deshalb gar keine
    Bewertung liefern - und schon gar keine, die sich mit dem
    Schadensrang ändert.
    """

    strong = build_profile(_snapshot(), "Spitze")
    weak = build_profile(_snapshot(), "Mitte")

    assert strong.rating(CATEGORY_ROTATION).has_data is False
    assert weak.rating(CATEGORY_ROTATION).has_data is False

    #
    # Der Rang steckt jetzt in "Leistung" - und dort unterscheidet er
    # die beiden sehr wohl.
    #

    assert strong.rating(CATEGORY_OUTPUT).stars > weak.rating(CATEGORY_OUTPUT).stars


def test_tanks_are_compared_with_tanks_not_with_damage_dealers():
    """
    Ein Tank steht im Schadensranking immer hinten. Ohne getrennte
    Vergleichsgruppe bekäme er dauerhaft einen Stern, obwohl er
    seine Aufgabe erfüllt.
    """

    partner = _actor(
        "Zweitpanzer",
        role=ROLE_TANK,
        class_name="Paladin",
        spec="Schutz",
    )

    snapshot = _snapshot(
        top_damage=_snapshot().top_damage + (
            MetricEntry(actor=partner, value=20_000.0),
        ),
    )

    profile = build_profile(snapshot, "Panzer")

    assert profile.rating(CATEGORY_OUTPUT).stars == MAX_STARS

    #
    # Und der schwächere Tank eben nicht - verglichen wird innerhalb
    # der Rolle, nicht mit den Schadensausteilern.
    #

    assert build_profile(snapshot, "Zweitpanzer").rating(
        CATEGORY_OUTPUT
    ).stars < MAX_STARS


def test_healers_are_rated_against_the_healing_ranking():

    partner = _actor(
        "Zweitheiler",
        role=ROLE_HEALER,
        class_name="Druid",
        spec="Wiederherstellung",
    )

    snapshot = _snapshot(
        top_healing=_snapshot().top_healing + (
            MetricEntry(actor=partner, value=30_000.0),
        ),
    )

    profile = build_profile(snapshot, "Heilerin")

    assert profile.rating(CATEGORY_OUTPUT).stars == MAX_STARS


def test_a_lone_tank_or_healer_is_not_rated_against_himself():
    """
    Ist man der einzige Spieler seiner Rolle, wäre der Beste der
    Vergleichsgruppe man selbst - das Verhältnis immer 1,0 und die
    Bewertung immer fünf Sterne, egal wie der Kampf lief. Eine
    geschenkte Bestnote hilft niemandem; "keine Daten" ist die
    ehrliche Antwort.
    """

    snapshot = _snapshot()

    for name in ("Panzer", "Heilerin"):

        rating = build_profile(snapshot, name).rating(CATEGORY_OUTPUT)

        assert rating.has_data is False, name
        assert rating.detail


def test_mechanic_errors_lower_the_matching_category_only():

    snapshot = _snapshot(
        mechanics=(
            MechanicIssue(
                actor_name="Spitze",
                mechanic="Im Feuer gestanden",
                count=3,
                category=MECHANIC_MOVEMENT,
            ),
        ),
    )

    profile = build_profile(snapshot, "Spitze")

    assert profile.rating(CATEGORY_MOVEMENT).stars < MAX_STARS

    assert profile.rating(CATEGORY_MECHANICS).stars == MAX_STARS

    #
    # Cooldowns bleiben ohne Cooldown-Daten ausdrücklich unbewertet
    # (null Sterne = "keine Daten") - ein Bewegungsfehler darf daran
    # nichts ändern, aber volle Punktzahl für etwas zu vergeben, das
    # gar nicht gemessen wurde, wäre genauso falsch.
    #

    assert profile.rating(CATEGORY_COOLDOWNS).has_data is False


def test_missed_interrupts_lower_the_mechanics_rating():

    snapshot = _snapshot(
        mechanics=(
            MechanicIssue(
                actor_name="Spitze",
                mechanic="Unterbrechung verpasst",
                count=2,
                category=MECHANIC_INTERRUPT,
            ),
        ),
    )

    profile = build_profile(snapshot, "Spitze")

    assert profile.rating(CATEGORY_MECHANICS).stars < MAX_STARS


def test_weakest_category_comes_first_in_the_plan():

    snapshot = _snapshot(
        mechanics=(
            MechanicIssue(
                actor_name="Spitze",
                mechanic="Wiederholt nicht ausgewichen",
                count=6,
                category=MECHANIC_MOVEMENT,
            ),
        ),
    )

    profile = build_profile(snapshot, "Spitze")

    assert profile.weakest[0].category == CATEGORY_MOVEMENT

    plan = build_plan(profile)

    assert plan.next_lesson is not None
    assert plan.next_lesson.category == CATEGORY_MOVEMENT


def test_plan_exists_even_without_combat_data():
    """
    Ein leerer Lernbereich wäre für den Nutzer eine Sackgasse -
    ohne Daten greifen die allgemeinen Lektionen.
    """

    profile = build_profile(_snapshot(), "GibtEsNicht")

    plan = build_plan(profile)

    assert plan.lessons
    assert plan.next_lesson is not None


def test_completed_lessons_are_not_offered_again():

    profile = build_profile(_snapshot(), "Spitze")

    plan = build_plan(profile)

    first_id = plan.next_lesson.lesson_id

    updated = build_plan(profile, {first_id})

    assert updated.is_completed(first_id)

    assert first_id not in {
        lesson.lesson_id for lesson in updated.open_lessons
    }


def test_plan_lessons_are_unique():

    profile = build_profile(_snapshot(), "Spitze")

    plan = build_plan(profile)

    ids = [lesson.lesson_id for lesson in plan.lessons]

    assert len(set(ids)) == len(ids)


def test_specialisation_lessons_are_preferred_over_generic_ones():
    """
    Ein Feuermagier soll seine Feuermagier-Lektion sehen, nicht die
    allgemeine Fassung desselben Themas.
    """

    snapshot = _snapshot(
        mechanics=(
            MechanicIssue(
                actor_name="Spitze",
                mechanic="Defensive ungenutzt",
                count=5,
                category="defensive",
            ),
        ),
    )

    profile = build_profile(snapshot, "Spitze")

    plan = build_plan(profile)

    assert plan.next_lesson.category == CATEGORY_COOLDOWNS
    assert plan.next_lesson.class_name == "Mage"


#
# --------------------------------------------------
# Überleben
# --------------------------------------------------
#


def _damage_snapshot(rows):
    """
    Ein Snapshot mit erhaltenem Schaden, eingeordnet nach Horridon.
    """

    from analyzer.analysis.damage import build_damage_taken

    return _snapshot(
        encounter=EncounterInfo(encounter_id=0, name="Horridon"),
        damage_taken=tuple(
            build_damage_taken(name, "Horridon", entries)
            for name, entries in rows
        ),
    )


#
# "Double Swipe" ist vermeidbar, "Dire Call" nicht.
#

_AVOIDABLE = ("Double Swipe", 90000.0, 3, "")
_UNAVOIDABLE = ("Dire Call", 10000.0, 1, "")


def test_a_lone_player_of_their_role_is_still_rated_absolutely():
    """
    Der Fehler, den ein echter Garrosh-Pull aufgedeckt hat.

    Ist jemand der einzige Spieler seiner Rolle mit Daten, wäre der
    "Rollenschnitt" sein eigener Wert - er würde mit sich selbst
    verglichen und bekäme immer die volle Wertung, egal wie schlecht
    der Wert ist.
    """

    snapshot = _damage_snapshot([("Spitze", (_AVOIDABLE, _UNAVOIDABLE))])

    rating = build_profile(snapshot, "Spitze").rating(CATEGORY_SURVIVAL)

    assert rating.has_data is True

    assert rating.stars < MAX_STARS


def test_a_whole_role_making_the_same_mistake_is_not_excused():
    """
    Nur relativ zu bewerten würde Gleichförmigkeit belohnen: machen
    alle Schadensausteiler denselben Fehler, liegt jeder genau im
    Schnitt - und alle bekämen fünf Sterne, obwohl der ganze Raid
    etwas falsch macht.
    """

    snapshot = _damage_snapshot([
        ("Spitze", (_AVOIDABLE, _UNAVOIDABLE)),
        ("Mitte", (_AVOIDABLE, _UNAVOIDABLE)),
    ])

    for name in ("Spitze", "Mitte"):

        rating = build_profile(snapshot, name).rating(CATEGORY_SURVIVAL)

        assert rating.stars < MAX_STARS, name


def test_clean_play_still_earns_the_full_rating():

    snapshot = _damage_snapshot([
        ("Spitze", (_UNAVOIDABLE,)),
        ("Mitte", (_AVOIDABLE, _UNAVOIDABLE)),
    ])

    assert build_profile(snapshot, "Spitze").rating(
        CATEGORY_SURVIVAL
    ).stars == MAX_STARS


def test_survival_rates_the_share_not_the_absolute_sum():
    """
    Ein Tank bekommt zwangsläufig den meisten Schaden des Raids ab.
    Nach Summe zu bewerten hieße, ihn für seine Aufgabe zu bestrafen.
    """

    snapshot = _damage_snapshot([
        #
        # Der Tank kassiert das Zehnfache - aber nichts davon
        # vermeidbar.
        #
        ("Panzer", (("Dire Call", 1000000.0, 40, ""),)),
        ("Spitze", (_AVOIDABLE, _UNAVOIDABLE)),
    ])

    tank = build_profile(snapshot, "Panzer").rating(CATEGORY_SURVIVAL)
    dps = build_profile(snapshot, "Spitze").rating(CATEGORY_SURVIVAL)

    assert tank.stars == MAX_STARS
    assert tank.stars > dps.stars


def test_survival_declines_to_rate_an_unclassified_boss():
    """
    Sonst bildete die Bewertung nur die Lücken der Referenzdaten ab
    statt das Spiel des Spielers.
    """

    from analyzer.analysis.damage import build_damage_taken

    snapshot = _snapshot(
        encounter=EncounterInfo(encounter_id=0, name="Irgendein Boss"),
        damage_taken=(
            build_damage_taken(
                "Spitze",
                "Irgendein Boss",
                (("Unbekannte Fähigkeit", 500000.0, 5, ""),),
            ),
        ),
    )

    rating = build_profile(snapshot, "Spitze").rating(CATEGORY_SURVIVAL)

    assert rating.has_data is False
    assert "Referenzdaten" in rating.detail
