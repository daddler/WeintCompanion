"""
Die Unversehrtheit des Lektionskatalogs.

Der Katalog ist auf über hundert Lektionen in fünfzehn Dateien
gewachsen. Genau dort schleichen sich Fehler ein, die niemandem
auffallen: eine doppelte ID vermischt den Fortschritt zweier
Lektionen unter einem Schlüssel, ein falscher Bereich lässt eine
Lektion nirgends erscheinen, ein falsch geschriebener Klassenname
macht sie für jeden Spieler unsichtbar.

Nichts davon wirft eine Ausnahme. Deshalb diese Datei.
"""

from analyzer.academy.lessons import (
    ENCOUNTER_LESSONS,
    GENERIC_LESSONS,
    ROLE_LESSONS,
    SPEC_LESSONS,
    all_lessons,
    find_lesson,
    lessons_for_actor,
    lessons_in_category,
)
from analyzer.academy.models import CATEGORY_ORDER
from analyzer.data import avoidable, encounters
from analyzer.models import ROLE_DPS, ROLE_HEALER, ROLE_TANK, Actor
from gui.theme.wow_colors import CLASS_COLORS


def test_lesson_ids_are_unique_across_the_whole_catalog():
    """
    Die ID ist der Schlüssel des gespeicherten Fortschritts. Eine
    doppelte würde zwei verschiedene Lektionen unter einem Eintrag
    zusammenwerfen - und die zweite wäre über find_lesson() nie
    erreichbar.
    """

    ids = [lesson.lesson_id for lesson in all_lessons()]

    assert len(ids) == len(set(ids))


def test_every_lesson_uses_a_known_category():
    """
    Ein Tippfehler im Bereich würde die Lektion aus jeder Ansicht
    verschwinden lassen, ohne dass etwas fehlschlägt.
    """

    for lesson in all_lessons():

        assert lesson.category in CATEGORY_ORDER, lesson.lesson_id


def test_every_lesson_has_title_and_summary():

    for lesson in all_lessons():

        assert lesson.title.strip(), lesson.lesson_id
        assert lesson.summary.strip(), lesson.lesson_id


def test_class_names_match_the_spelling_used_everywhere_else():
    """
    Die Klassennamen müssen exakt der Schreibweise des Combat-Logs
    entsprechen - sonst findet weder die Klassenfarbe noch die
    Lektionsauswahl ihren Eintrag.
    """

    for class_name, _spec in SPEC_LESSONS:

        assert class_name in CLASS_COLORS, class_name


def test_encounter_lessons_reference_known_bosses():

    for name in ENCOUNTER_LESSONS:

        assert encounters.instance_for(name), name


def test_encounter_lessons_only_exist_where_reference_data_does():
    """
    Eine bossbezogene Lektion, deren Fähigkeiten nirgends eingeordnet
    sind, könnte nie geprüft werden - sie wäre dauerhaft "keine
    Daten".
    """

    for name in ENCOUNTER_LESSONS:

        assert avoidable.rules_for(name), name


def test_role_lessons_declare_their_role():

    for role, lessons in ROLE_LESSONS.items():

        for lesson in lessons:

            assert role in lesson.roles, lesson.lesson_id


#
# --------------------------------------------------
# Auswahl
# --------------------------------------------------
#


def _actor(class_name="Druid", spec="Gleichgewicht", role=ROLE_DPS):

    return Actor(
        name="Testheld",
        class_name=class_name,
        spec=spec,
        role=role,
    )


def test_selection_order_is_specific_before_general():
    """
    Wer Inhalte für seine Spezialisierung hat, soll sie vor den
    allgemeinen Ratschlägen bekommen - und was gerade gespielt wird,
    steht noch davor.
    """

    lessons = lessons_for_actor(_actor(), "Horridon")

    ids = [lesson.lesson_id for lesson in lessons]

    boss = next(i for i, key in enumerate(ids) if key.startswith("boss-"))
    spec = next(i for i, key in enumerate(ids) if key.startswith("druid-"))
    role = next(i for i, key in enumerate(ids) if key.startswith("role-"))
    generic = next(i for i, key in enumerate(ids) if key.startswith("generic."))

    assert boss < spec < role < generic


def test_an_unknown_class_still_gets_a_full_plan():
    """
    Die Zusicherung aus der ersten Fassung: jeder Spieler bekommt
    Lektionen, auch wenn für ihn nichts hinterlegt ist.
    """

    lessons = lessons_for_actor(_actor("Demon Hunter", "Verwüstung"))

    assert lessons

    for category in CATEGORY_ORDER:

        assert lessons_in_category(
            _actor("Demon Hunter", "Verwüstung"),
            category,
        ), category


def test_every_category_is_covered_for_every_role():
    """
    Sonst hätte ein Bereich mit schlechter Bewertung keine Lektion,
    aus der der Trainingsplan schöpfen könnte.
    """

    for role in (ROLE_TANK, ROLE_HEALER, ROLE_DPS):

        actor = _actor(role=role)

        for category in CATEGORY_ORDER:

            assert lessons_in_category(actor, category), (role, category)


def test_role_specific_lessons_do_not_leak_to_other_roles():

    healer = _actor(
        "Priest",
        "Heilig",
        ROLE_HEALER,
    )

    ids = {lesson.lesson_id for lesson in lessons_for_actor(healer)}

    assert "role-tank.mechanics.swap" not in ids
    assert "role-healer.mechanics.dispel" in ids


def test_class_wide_lessons_reach_every_specialisation():
    """
    Nutzfähigkeiten wie die Anti-Magie-Zone gehören zur Klasse, nicht
    zu einer Spezialisierung - sie sind einmal hinterlegt und müssen
    trotzdem überall ankommen.
    """

    for spec in ("Unheilig", "Frost", "Blut"):

        ids = {
            lesson.lesson_id
            for lesson in lessons_for_actor(_actor("Death Knight", spec))
        }

        assert "deathknight.mechanics.anti_magic_zone" in ids, spec


def test_find_lesson_returns_none_for_unknown_ids():

    assert find_lesson("gibt.es.nicht") is None

    assert find_lesson(GENERIC_LESSONS[0].lesson_id) is GENERIC_LESSONS[0]


def test_the_catalog_actually_grew():
    """
    Die erste Fassung hatte 23 Lektionen und deckte vier Bereiche ab.
    Fällt der Katalog wieder darunter, ist beim Zusammenführen etwas
    verlorengegangen.
    """

    assert len(all_lessons()) > 80

    measurable = [
        lesson
        for lesson in all_lessons()
        if lesson.is_measurable
    ]

    assert len(measurable) > 30


def test_every_siege_of_orgrimmar_boss_has_lessons():
    """
    Steht der Raid an einem Boss, soll die Academy dazu auch etwas zu
    sagen haben - sonst fällt sie auf die allgemeinen Ratschläge
    zurück, die notwendigerweise so allgemein sind, dass sie niemandem
    konkret weiterhelfen.
    """

    from analyzer.data.encounters import (
        INSTANCE_ENCOUNTERS,
        SIEGE_OF_ORGRIMMAR,
    )

    missing = [
        name
        for name in INSTANCE_ENCOUNTERS[SIEGE_OF_ORGRIMMAR]
        if name not in ENCOUNTER_LESSONS
    ]

    assert missing == []


def test_encounter_lessons_are_reachable_for_every_role():
    """
    Bosslektionen tragen keine Rollenbeschränkung - was am Boden liegt,
    schadet jedem gleich.
    """

    for role in (ROLE_TANK, ROLE_HEALER, ROLE_DPS):

        ids = {
            lesson.lesson_id
            for lesson in lessons_for_actor(_actor(role=role), "Garrosh Hellscream")
        }

        assert any(key.startswith("boss-garrosh") for key in ids), role


def test_encounter_lessons_declare_their_encounter():

    for name, lessons in ENCOUNTER_LESSONS.items():

        for lesson in lessons:

            assert lesson.encounter == name, lesson.lesson_id
