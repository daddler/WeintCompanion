"""
Auswertung: aus einem Kampf wird ein Lernprofil, aus dem Lernprofil
ein Trainingsplan.

Zwei bewusste Festlegungen:

* **Die Bewertung ist relativ, nicht absolut.** Ein fester
  Schadensschwellenwert wäre nach dem nächsten Ausrüstungsstand
  wertlos. Verglichen wird deshalb mit dem besten Wert der eigenen
  Rolle im selben Kampf.
* **Der Trainingsplan folgt der Schwäche.** Die Reihenfolge der
  Lektionen ergibt sich aus der schlechtesten Bewertung zuerst -
  genau die Reihenfolge, die den größten Fortschritt bringt.
"""

from __future__ import annotations

from analyzer.academy import lessons as lesson_catalog
from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ORDER,
    CATEGORY_ROTATION,
    MAX_STARS,
    Lesson,
    PlayerProfile,
    SkillRating,
    TrainingPlan,
)
from analyzer.models import (
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_POSITIONING,
    Actor,
    MetricEntry,
    RaidSnapshot,
)


#
# Wie viele Lektionen ein Trainingsplan höchstens enthält. Mehr
# überfordert; weniger führt zu einem leeren Plan, sobald zwei
# Lektionen erledigt sind.
#

PLAN_LENGTH = 6


#
# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
#


def _stars_from_ratio(ratio: float) -> int:
    """
    Leistungsverhältnis (eigener Wert / bester Wert der Rolle) in
    eine Sternebewertung übersetzen.
    """

    if ratio >= 0.95:
        return 5

    if ratio >= 0.87:
        return 4

    if ratio >= 0.76:
        return 3

    if ratio >= 0.62:
        return 2

    return 1


def _stars_from_mistakes(count: int) -> int:
    """
    Fehleranzahl in eine Sternebewertung übersetzen - fehlerfrei
    ergibt die volle Punktzahl.
    """

    if count <= 0:
        return MAX_STARS

    if count == 1:
        return 4

    if count == 2:
        return 3

    if count <= 4:
        return 2

    return 1


def _find_entry(
    rows: tuple[MetricEntry, ...],
    name: str,
) -> tuple[MetricEntry | None, int]:
    """
    Sucht den Eintrag eines Spielers und liefert zusätzlich seinen
    Platz im Ranking (1-basiert, 0 wenn nicht enthalten).
    """

    for position, entry in enumerate(rows, start=1):

        if entry.actor.name == name:
            return entry, position

    return None, 0


def find_actor(snapshot: RaidSnapshot, name: str) -> Actor | None:
    """
    Sucht einen Spieler in allen Listen eines Snapshots.
    """

    if not name:
        return None

    for rows in (snapshot.top_damage, snapshot.top_healing):

        entry, _position = _find_entry(rows, name)

        if entry is not None:
            return entry.actor

    for tank in snapshot.tanks:

        if tank.actor.name == name:
            return tank.actor

    return None


def roster_names(snapshot: RaidSnapshot) -> tuple[str, ...]:
    """
    Alle Spielernamen eines Snapshots, alphabetisch - die Auswahl,
    die die Academy dem Nutzer anbietet.
    """

    names = set()

    for rows in (snapshot.top_damage, snapshot.top_healing):

        for entry in rows:
            names.add(entry.actor.name)

    for tank in snapshot.tanks:
        names.add(tank.actor.name)

    return tuple(sorted(names))


def _mechanics_of(
    snapshot: RaidSnapshot,
    name: str,
    categories: tuple[str, ...],
) -> int:
    """
    Summiert die Fehler eines Spielers in den genannten Kategorien.
    """

    return sum(
        issue.count
        for issue in snapshot.mechanics
        if issue.actor_name == name and issue.category in categories
    )


def _missing_consumables(snapshot: RaidSnapshot, name: str) -> tuple[str, ...]:

    return tuple(
        state.label
        for state in snapshot.consumables
        if name in state.missing
    )


#
# --------------------------------------------------
# Einzelbewertungen
# --------------------------------------------------
#


def _comparison_group(
    snapshot: RaidSnapshot,
    actor: Actor,
) -> tuple[MetricEntry, ...]:
    """
    Die Vergleichsgruppe eines Spielers.

    Entscheidend ist, dass nach Rolle getrennt wird: ein Tank gegen
    das Schadensranking der Schadensausteiler zu messen, würde ihn
    dauerhaft mit einem Stern bewerten, obwohl er seine Aufgabe
    einwandfrei erfüllt.
    """

    if actor.is_healer:
        return snapshot.top_healing

    if actor.is_tank:

        return tuple(
            entry
            for entry in snapshot.top_damage
            if entry.actor.is_tank
        )

    return tuple(
        entry
        for entry in snapshot.top_damage
        if not entry.actor.is_tank
    )


def _rate_rotation(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:

    rows = _comparison_group(snapshot, actor)

    entry, position = _find_entry(rows, actor.name)

    metric = "Heilung" if actor.is_healer else "Schaden"

    if entry is None or not rows:

        return SkillRating(
            category=CATEGORY_ROTATION,
            stars=3,
            detail=(
                f"Noch keine {metric}sdaten für diesen Kampf - die "
                f"Bewertung entsteht mit dem ersten Pull."
            ),
        )

    best = rows[0].value

    ratio = entry.value / best if best > 0 else 0.0

    stars = _stars_from_ratio(ratio)

    return SkillRating(
        category=CATEGORY_ROTATION,
        stars=stars,
        detail=(
            f"Platz {position} von {len(rows)} · "
            f"{entry.value / 1000:.1f}k {metric} · "
            f"{ratio * 100:.0f} % der Spitzenleistung"
        ),
    )


def _rate_movement(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:

    count = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_MOVEMENT, MECHANIC_POSITIONING),
    )

    if count == 0:

        detail = "Keine vermeidbaren Treffer durch Positionierung."

    else:

        detail = (
            f"{count} vermeidbare Treffer durch Bewegung oder "
            f"Position."
        )

    return SkillRating(
        category=CATEGORY_MOVEMENT,
        stars=_stars_from_mistakes(count),
        detail=detail,
    )


def _rate_mechanics(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:

    count = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_INTERRUPT,),
    )

    #
    # Ein Tod ist der deutlichste Mechanikfehler überhaupt und wiegt
    # daher wie ein eigener Fehler.
    #

    deaths = sum(
        1
        for death in snapshot.deaths
        if death.actor_name == actor.name
    )

    total = count + deaths

    parts = []

    if count:
        parts.append(f"{count} verpasste Unterbrechungen")

    if deaths:
        parts.append(f"{deaths}× gestorben")

    detail = (
        " · ".join(parts)
        if parts
        else "Kampfmechaniken sauber ausgeführt."
    )

    return SkillRating(
        category=CATEGORY_MECHANICS,
        stars=_stars_from_mistakes(total),
        detail=detail,
    )


def _rate_cooldowns(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:

    defensive = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_DEFENSIVE,),
    )

    missing = _missing_consumables(snapshot, actor.name)

    total = defensive + len(missing)

    parts = []

    if defensive:
        parts.append(f"{defensive}× Defensive ungenutzt")

    if missing:
        parts.append("fehlt: " + ", ".join(missing))

    #
    # Eigene Raid-Cooldowns als Zusatzinfo - sie fließen nicht in die
    # Wertung ein, weil aus einem einzelnen Snapshot nicht sicher
    # hervorgeht, ob ein bereiter Cooldown ungenutzt oder gerade
    # wieder verfügbar ist.
    #

    own = [
        state
        for state in snapshot.raid_cooldowns + snapshot.heal_cooldowns
        if state.actor_name == actor.name
    ]

    if own:

        ready = sum(1 for state in own if state.ready)

        parts.append(f"{ready}/{len(own)} Cooldowns bereit")

    detail = (
        " · ".join(parts)
        if parts
        else "Cooldowns und Verbrauchsgüter vollständig."
    )

    return SkillRating(
        category=CATEGORY_COOLDOWNS,
        stars=_stars_from_mistakes(total),
        detail=detail,
    )


#
# --------------------------------------------------
# Profil
# --------------------------------------------------
#


def build_profile(
    snapshot: RaidSnapshot,
    player_name: str,
) -> PlayerProfile:
    """
    Baut das Lernprofil eines Spielers aus einem Snapshot.

    Ist der Spieler nicht enthalten (z. B. weil gerade kein Kampf
    läuft), entsteht ein leeres Profil mit erklärender Notiz statt
    eines Fehlers - die Oberfläche zeigt dann einfach den Hinweis an.
    """

    actor = find_actor(snapshot, player_name)

    if actor is None:

        return PlayerProfile(
            encounter_name=snapshot.encounter_name,
            sample_size=snapshot.pull_number,
            note=(
                "Noch keine Kampfdaten für diesen Charakter. Sobald "
                "ein Pull ausgewertet wurde, entsteht hier "
                "automatisch ein Lernprofil."
            ),
        )

    ratings = (
        _rate_rotation(snapshot, actor),
        _rate_movement(snapshot, actor),
        _rate_cooldowns(snapshot, actor),
        _rate_mechanics(snapshot, actor),
    )

    #
    # In der Reihenfolge von CATEGORY_ORDER ausgeben, damit die
    # Oberfläche die Zeilen nie umsortieren muss.
    #

    ordered = tuple(
        sorted(
            ratings,
            key=lambda entry: CATEGORY_ORDER.index(entry.category),
        )
    )

    return PlayerProfile(
        actor=actor,
        ratings=ordered,
        encounter_name=snapshot.encounter_name,
        sample_size=snapshot.pull_number,
    )


#
# --------------------------------------------------
# Trainingsplan
# --------------------------------------------------
#


def build_plan(
    profile: PlayerProfile,
    completed: frozenset[str] | set[str] | None = None,
) -> TrainingPlan:
    """
    Leitet aus einem Profil die nächsten Lektionen ab.

    Vorgehen: die Bereiche werden nach Bewertung sortiert
    (schlechtester zuerst) und reihum je eine Lektion beigesteuert.
    Dadurch beginnt der Plan bei der größten Schwäche, ohne die
    übrigen Bereiche vollständig auszublenden.
    """

    done = frozenset(completed or ())

    if not profile.has_data:

        #
        # Ohne Kampfdaten trotzdem ein sinnvoller Einstieg: die
        # allgemeinen Lektionen in fester Reihenfolge.
        #

        return TrainingPlan(
            lessons=lesson_catalog.GENERIC_LESSONS[:PLAN_LENGTH],
            completed=done,
        )

    #
    # Je Bereich die noch nicht erledigten Lektionen einsammeln,
    # Spezialisierung zuerst (dafür sorgt lessons_in_category).
    #

    buckets: list[list[Lesson]] = []

    for rating in profile.weakest:

        candidates = [
            lesson
            for lesson in lesson_catalog.lessons_in_category(
                profile.actor,
                rating.category,
            )
            if lesson.lesson_id not in done
        ]

        if candidates:
            buckets.append(candidates)

    selected: list[Lesson] = []

    seen: set[str] = set()

    #
    # Reihum aus den Bereichen ziehen: erst die jeweils erste
    # Lektion jedes Bereichs, dann die zweite und so weiter.
    #

    while buckets and len(selected) < PLAN_LENGTH:

        for bucket in list(buckets):

            if len(selected) >= PLAN_LENGTH:
                break

            lesson = bucket.pop(0)

            if lesson.lesson_id not in seen:

                selected.append(lesson)

                seen.add(lesson.lesson_id)

            if not bucket:
                buckets.remove(bucket)

    #
    # Bereits erledigte Lektionen hinten anhängen, damit der
    # Fortschritt sichtbar bleibt.
    #

    finished = [
        lesson
        for lesson in lesson_catalog.lessons_for_actor(profile.actor)
        if lesson.lesson_id in done
    ]

    return TrainingPlan(
        lessons=tuple(selected) + tuple(finished),
        completed=done,
    )
