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

#
# Zwei Bereiche sind hinzugekommen, und beide lösen ein konkretes
# Problem der ersten Fassung:
#
# ÜBERLEBEN, weil erhaltener Schaden vorher nirgends bewertet wurde.
# Er ist die Zahl, die am ehesten erklärt, warum ein Pull schiefging.
#
# LEISTUNG, weil "Rotation" vorher nichts anderes war als der Platz in
# der Schadensliste. Das ist keine Rotationsbewertung, sondern eine
# Ausrüstungsbewertung. Der Rang bleibt sichtbar - aber als eigener
# Bereich, damit er die Frage "habe ich meine Knöpfe richtig gedrückt"
# nicht länger überlagert.
#

CATEGORY_SURVIVAL = "survival"
CATEGORY_OUTPUT = "output"


#
# Die bestehenden vier behalten ihre Reihenfolge, die neuen kommen
# hinten dazu. Die Reihenfolge ist nicht nur Anzeige: sie ist der
# stabile Zweitschlüssel, mit dem `PlayerProfile.weakest` bei
# gleicher Sternezahl sortiert - änderte sie sich, würde der
# Trainingsplan bei jedem Neuzeichnen umspringen.
#

CATEGORY_ORDER: tuple[str, ...] = (

    CATEGORY_ROTATION,
    CATEGORY_MOVEMENT,
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_SURVIVAL,
    CATEGORY_OUTPUT,

)


CATEGORY_LABELS: dict[str, str] = {

    CATEGORY_ROTATION: "Rotation",
    CATEGORY_MOVEMENT: "Movement",
    CATEGORY_COOLDOWNS: "Cooldowns",
    CATEGORY_MECHANICS: "Mechaniken",
    CATEGORY_SURVIVAL: "Überleben",
    CATEGORY_OUTPUT: "Leistung",

}


#
# Kurzbeschreibung je Bereich - die Oberfläche kann damit erklären,
# was überhaupt bewertet wird, statt nur Sterne zu zeigen.
#

CATEGORY_HINTS: dict[str, str] = {

    CATEGORY_ROTATION: "Aktivzeit und Wirkungsdauern",
    CATEGORY_MOVEMENT: "Vermeidbare Treffer und Laufwege",
    CATEGORY_COOLDOWNS: "Genutzte Einsätze und ihr Zeitpunkt",
    CATEGORY_MECHANICS: "Unterbrechungen und Bossmechaniken",
    CATEGORY_SURVIVAL: "Erhaltener Schaden und Tode",
    CATEGORY_OUTPUT: "Platz im Ranking der eigenen Rolle",

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

    `stars = 0` bedeutet ausdrücklich **keine Daten** und ist keine
    schlechte Bewertung. Der Unterschied ist wichtig: fehlt einer
    Datenquelle ein Block, darf der Spieler dafür nicht bestraft
    werden - und der Trainingsplan darf sich nicht auf einen Bereich
    stürzen, über den schlicht nichts bekannt ist.

    `detail` ist die Begründung in einem Satz - ohne sie wäre eine
    Sternewertung für den Spieler nicht handlungsleitend.

    `at_seconds` benennt den Moment, an dem sich die Bewertung
    festmacht (ein Tod, ein vermeidbarer Treffer). Er ist der Griff
    für den Sprung in die Wiedergabe; -1 heißt "kein Moment".
    """

    category: str

    stars: int

    detail: str = ""

    metric_text: str = ""

    at_seconds: float = -1.0

    @property
    def label(self) -> str:

        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def hint(self) -> str:

        return CATEGORY_HINTS.get(self.category, "")

    @property
    def has_data(self) -> bool:

        return self.stars > 0

    @property
    def is_weak(self) -> bool:

        return self.has_data and self.stars <= 3


#
# --------------------------------------------------
# Prüfbare Kriterien
# --------------------------------------------------
#
# Der Kern der Automatisierung: eine Lektion trägt nicht nur Text,
# sondern ein **deklaratives** Kriterium. "Aktivzeit über 95 %" wird
# damit zu (metric="active_percent", comparison=">=", target=95).
#
# Deklarativ und nicht als Funktion, aus drei Gründen: der Katalog
# bleibt reine Daten und damit ohne Codeänderung erweiterbar; ein
# Test kann prüfen, dass jeder verwendete Metrikname überhaupt
# auflösbar ist (ein Tippfehler wäre sonst ein stilles "keine
# Daten"); und die Oberfläche kann Ist und Ziel getrennt anzeigen.
#

CHECK_AT_LEAST = ">="
CHECK_AT_MOST = "<="
CHECK_EQUALS = "=="


#
# Drei Ergebnisse, nicht zwei. "Keine Daten" ist ein eigener Zustand
# und darf niemals als "nicht erfüllt" durchgehen: viele Lektionen
# sind grundsätzlich nicht messbar ("lege feste Einsatzzeitpunkte
# fest"), und viele Datenquellen liefern einzelne Blöcke nicht. Einen
# grünen Haken zu erfinden wäre schlimmer, aber ein rotes Kreuz für
# fehlende Daten wäre schlicht falsch.
#

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"


STATUS_LABELS: dict[str, str] = {

    STATUS_PASSED: "erfüllt",
    STATUS_FAILED: "nicht erfüllt",
    STATUS_UNKNOWN: "keine Daten",

}


@dataclass(frozen=True)
class LessonCheck:
    """
    Ein prüfbares Kriterium einer Lektion.

    `subject` schränkt die Kennzahl ein, wo das nötig ist - bei
    Wirkungsdauern auf eine Fähigkeit, bei Mechanikfehlern auf eine
    MECHANIC_*-Kategorie.
    """

    metric: str

    comparison: str = CHECK_AT_LEAST

    target: float = 0.0

    subject: str = ""

    unit: str = ""

    label: str = ""


@dataclass(frozen=True)
class CheckResult:
    """
    Das Ergebnis einer einzelnen Prüfung.
    """

    check: LessonCheck

    status: str = STATUS_UNKNOWN

    value: float | None = None

    detail: str = ""

    at_seconds: float = -1.0

    @property
    def passed(self) -> bool:

        return self.status == STATUS_PASSED

    @property
    def failed(self) -> bool:

        return self.status == STATUS_FAILED


@dataclass(frozen=True)
class LessonResult:
    """
    Das Gesamturteil zu einer Lektion.

    Kombinationsregel (siehe analyzer.academy.checks): ein
    fehlgeschlagenes Kriterium genügt für "nicht erfüllt", "erfüllt"
    verlangt dagegen, dass ALLE Kriterien erfüllt und geprüft sind.
    Ein Teilerfolg mit Datenlücken bleibt "keine Daten" - auf halber
    Evidenz einen Haken zu setzen wäre eine Behauptung.
    """

    lesson: "Lesson"

    status: str = STATUS_UNKNOWN

    checks: tuple[CheckResult, ...] = ()

    @property
    def passed(self) -> bool:

        return self.status == STATUS_PASSED

    @property
    def failed(self) -> bool:

        return self.status == STATUS_FAILED

    @property
    def unknown(self) -> bool:

        return self.status == STATUS_UNKNOWN

    @property
    def label(self) -> str:

        return STATUS_LABELS.get(self.status, self.status)

    @property
    def at_seconds(self) -> float:
        """
        Der erste Moment, an dem sich ein gescheitertes Kriterium
        festmacht - das Sprungziel in die Wiedergabe.
        """

        for result in self.checks:

            if result.failed and result.at_seconds >= 0:
                return result.at_seconds

        return -1.0


@dataclass(frozen=True)
class Lesson:
    """
    Eine Lektion des Lernpfads.

    `spec`/`class_name` leer bedeutet: gilt für alle. Damit deckt der
    Katalog jede Klasse ab, auch wenn für sie noch keine speziellen
    Inhalte hinterlegt sind. `encounter` und `roles` schränken analog
    auf einen Boss bzw. bestimmte Rollen ein.

    `checks` leer heißt: diese Lektion ist nicht messbar. Sie
    verhält sich dann genau wie bisher - Text, den man liest und
    selbst abhakt.
    """

    lesson_id: str

    title: str

    category: str

    summary: str

    steps: tuple[str, ...] = ()

    class_name: str = ""

    spec: str = ""

    encounter: str = ""

    roles: tuple[str, ...] = ()

    checks: tuple[LessonCheck, ...] = ()

    @property
    def category_label(self) -> str:

        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def is_generic(self) -> bool:

        return not self.spec and not self.class_name

    @property
    def is_measurable(self) -> bool:

        return bool(self.checks)


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
    def rated(self) -> tuple[SkillRating, ...]:
        """
        Nur die Bereiche, zu denen tatsächlich Daten vorliegen.

        Ohne diese Trennung würde eine fehlende Kennzahl (null Sterne)
        wie die schlechteste aller Bewertungen wirken und den
        Trainingsplan komplett an sich reißen - obwohl über sie
        schlicht nichts bekannt ist.
        """

        return tuple(
            entry
            for entry in self.ratings
            if entry.has_data
        )

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
                self.rated,
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

        rated = self.rated

        if not rated:
            return 0.0

        return sum(entry.stars for entry in rated) / len(rated)


@dataclass(frozen=True)
class PlanItem:
    """
    Ein Eintrag des Trainingsplans.

    Zwei voneinander unabhängige Wahrheiten stehen hier
    nebeneinander, und das ist Absicht:

    `result` ist die **Evidenz aus dem Log** - was die Auswertung im
    gewählten Kampf tatsächlich gemessen hat.

    `completed` ist die **eigene Angabe** des Spielers, der Haken.

    Sie werden nie ineinander überführt. Einen vom Nutzer gesetzten
    Haken automatisch zu entfernen, weil ein einzelner Pull schlecht
    lief, würde dessen eigenen Verlauf zerstören - und einen Haken
    automatisch zu setzen, würde eine Behauptung über sein Können
    aufstellen, die aus einem Pull nicht folgt.
    """

    lesson: Lesson

    result: LessonResult | None = None

    completed: bool = False

    # --------------------------------------------------

    @property
    def lesson_id(self) -> str:

        return self.lesson.lesson_id

    @property
    def status(self) -> str:

        if self.result is None:
            return STATUS_UNKNOWN

        return self.result.status

    @property
    def status_label(self) -> str:

        return STATUS_LABELS.get(self.status, self.status)

    @property
    def done(self) -> bool:
        """
        Erledigt ist, was der Spieler abgehakt hat ODER was das Log
        nachweislich zeigt.
        """

        return self.completed or self.status == STATUS_PASSED


@dataclass(frozen=True)
class TrainingPlan:
    """
    Die geordnete Abfolge der nächsten Lektionen.

    `items` trägt jetzt zusätzlich das Prüfergebnis je Lektion;
    `lessons` bleibt als abgeleitete Eigenschaft erhalten, damit
    bestehende Aufrufer unverändert funktionieren.
    """

    items: tuple[PlanItem, ...] = ()

    completed: frozenset[str] = frozenset()

    # --------------------------------------------------

    @classmethod
    def from_lessons(
        cls,
        lessons: tuple[Lesson, ...],
        completed: frozenset[str] = frozenset(),
    ) -> "TrainingPlan":
        """
        Plan ohne Auswertung - für den Fall, dass noch keine
        Kampfdaten vorliegen.
        """

        return cls(
            items=tuple(
                PlanItem(
                    lesson=lesson,
                    completed=lesson.lesson_id in completed,
                )
                for lesson in lessons
            ),
            completed=completed,
        )

    @property
    def lessons(self) -> tuple[Lesson, ...]:

        return tuple(item.lesson for item in self.items)

    @property
    def open_items(self) -> tuple[PlanItem, ...]:

        return tuple(
            item
            for item in self.items
            if not item.done
        )

    @property
    def open_lessons(self) -> tuple[Lesson, ...]:

        return tuple(item.lesson for item in self.open_items)

    @property
    def next_lesson(self) -> Lesson | None:

        open_items = self.open_items

        if not open_items:
            return None

        return open_items[0].lesson

    def item(self, lesson_id: str) -> PlanItem | None:

        for entry in self.items:

            if entry.lesson_id == lesson_id:
                return entry

        return None

    def is_completed(self, lesson_id: str) -> bool:

        return lesson_id in self.completed
