"""
Datenmodelle der WeintAcademy.

Wie im übrigen Analyzer sind alle Strukturen eingefroren: ein Profil
wird aus einem Snapshot berechnet und danach nur noch gelesen.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.models import Actor


#
# --------------------------------------------------
# Trainierbare Bereiche
# --------------------------------------------------
#

CATEGORY_ROTATION = "rotation"
CATEGORY_MOVEMENT = "movement"
CATEGORY_COOLDOWNS = "cooldowns"
CATEGORY_MECHANICS = "mechanics"


CATEGORY_ORDER: tuple[str, ...] = (

    CATEGORY_ROTATION,
    CATEGORY_MOVEMENT,
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,

)


CATEGORY_LABELS: dict[str, str] = {

    CATEGORY_ROTATION: "Rotation",
    CATEGORY_MOVEMENT: "Movement",
    CATEGORY_COOLDOWNS: "Cooldowns",
    CATEGORY_MECHANICS: "Mechaniken",

}


#
# Höchste erreichbare Bewertung. Zentral, damit Auswertung und
# Sterne-Widget nie auseinanderlaufen.
#

MAX_STARS = 5


# --------------------------------------------------


@dataclass(frozen=True)
class SkillRating:
    """
    Bewertung eines Bereichs von 1 bis MAX_STARS.

    `detail` ist die Begründung in einem Satz - ohne sie wäre eine
    Sternewertung für den Spieler nicht handlungsleitend.
    """

    category: str

    stars: int

    detail: str = ""

    @property
    def label(self) -> str:

        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def is_weak(self) -> bool:

        return self.stars <= 3


@dataclass(frozen=True)
class Lesson:
    """
    Eine Lektion des Lernpfads.

    `spec`/`class_name` leer bedeutet: gilt für alle. Damit deckt der
    Katalog jede Klasse ab, auch wenn für sie noch keine speziellen
    Inhalte hinterlegt sind.
    """

    lesson_id: str

    title: str

    category: str

    summary: str

    steps: tuple[str, ...] = ()

    class_name: str = ""

    spec: str = ""

    @property
    def category_label(self) -> str:

        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def is_generic(self) -> bool:

        return not self.spec and not self.class_name


@dataclass(frozen=True)
class PlayerProfile:
    """
    Das Lernprofil eines Spielers zu einem Auswertungsstand.
    """

    actor: Actor | None = None

    ratings: tuple[SkillRating, ...] = ()

    encounter_name: str = ""

    sample_size: int = 0

    note: str = ""

    # --------------------------------------------------

    @property
    def name(self) -> str:

        if self.actor is None:
            return "-"

        return self.actor.name

    @property
    def class_name(self) -> str:

        if self.actor is None:
            return ""

        return self.actor.class_name

    @property
    def spec(self) -> str:

        if self.actor is None:
            return ""

        return self.actor.spec

    @property
    def title(self) -> str:
        """
        "Gleichgewicht Druid" - die Überschrift des Profils.
        """

        if self.actor is None:
            return "Kein Charakter gewählt"

        if not self.actor.spec:
            return self.actor.class_name

        return f"{self.actor.spec} {self.actor.class_name}"

    @property
    def has_data(self) -> bool:

        return self.actor is not None and bool(self.ratings)

    # --------------------------------------------------

    def rating(self, category: str) -> SkillRating | None:

        for entry in self.ratings:

            if entry.category == category:
                return entry

        return None

    @property
    def weakest(self) -> tuple[SkillRating, ...]:
        """
        Bereiche mit der niedrigsten Bewertung zuerst. Bei
        Gleichstand entscheidet die feste Reihenfolge aus
        CATEGORY_ORDER, damit sich der Trainingsplan nicht bei jedem
        Aufruf umsortiert.
        """

        return tuple(
            sorted(
                self.ratings,
                key=lambda entry: (
                    entry.stars,
                    CATEGORY_ORDER.index(entry.category)
                    if entry.category in CATEGORY_ORDER
                    else len(CATEGORY_ORDER),
                ),
            )
        )

    @property
    def average_stars(self) -> float:

        if not self.ratings:
            return 0.0

        return sum(entry.stars for entry in self.ratings) / len(self.ratings)


@dataclass(frozen=True)
class TrainingPlan:
    """
    Die geordnete Abfolge der nächsten Lektionen.

    `completed` enthält die IDs bereits erledigter Lektionen; sie
    bleiben im Plan sichtbar, damit der Fortschritt erkennbar ist.
    """

    lessons: tuple[Lesson, ...] = ()

    completed: frozenset[str] = frozenset()

    # --------------------------------------------------

    @property
    def open_lessons(self) -> tuple[Lesson, ...]:

        return tuple(
            lesson
            for lesson in self.lessons
            if lesson.lesson_id not in self.completed
        )

    @property
    def next_lesson(self) -> Lesson | None:

        open_lessons = self.open_lessons

        if not open_lessons:
            return None

        return open_lessons[0]

    def is_completed(self, lesson_id: str) -> bool:

        return lesson_id in self.completed
