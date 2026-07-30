"""
Bossbezogene Lektionen.

Die Ebene, auf der aus "vermeidbarer Schaden" konkreter Lernstoff
wird: die Fähigkeiten hier sind dieselben, die
analyzer/data/avoidable.py als vermeidbar einordnet. Damit schließt
sich der Kreis - ein Treffer in der Analyse führt zu einer Lektion,
die genau diesen Treffer behandelt, und der Trainingsplan prüft
anschließend selbst, ob er ausgeblieben ist.

Der Schlüssel ist der **englische** Bossname, wie ihn WarcraftLogs
und das Combat-Log liefern - dieselbe Konvention wie in
analyzer/data/encounters.py.

Bewusst lückenhaft: hier stehen nur Kämpfe, für die auch
Referenzdaten hinterlegt sind. Eine Lektion zu einem Boss, dessen
Fähigkeiten nirgends eingeordnet sind, könnte nie geprüft werden.
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_SURVIVAL,
    CHECK_AT_MOST,
    Lesson,
    LessonCheck,
)
from analyzer.models import MECHANIC_INTERRUPT, MECHANIC_MOVEMENT


def _no_hits(label: str) -> LessonCheck:
    """
    "Keine vermeidbaren Treffer" - das mit Abstand häufigste
    Kriterium bossbezogener Lektionen.
    """

    return LessonCheck(
        metric="avoidable_hits",
        comparison=CHECK_AT_MOST,
        target=0.0,
        unit="×",
        label=label,
    )


ENCOUNTER_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Horridon": (

        Lesson(
            lesson_id="boss-horridon.movement.double_swipe",
            title="Doppelhieb nicht kassieren",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Doppelhieb trifft alles vor dem Boss. Wer nicht "
                "im Rücken steht, nimmt ihn zwangsläufig mit."
            ),
            steps=(
                "Als Nahkämpfer grundsätzlich hinter dem Boss stehen.",
                "Nach jedem Tankwechsel die eigene Position prüfen.",
                "Bei Ansturm nicht vor den Boss zurücklaufen.",
            ),
            encounter="Horridon",
            checks=(_no_hits("Vermeidbare Treffer bei Horridon"),),
        ),

        Lesson(
            lesson_id="boss-horridon.movement.blazing_sunlight",
            title="Vor dem Sonnenlicht in Deckung gehen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Loderndes Sonnenlicht ist angekündigt und trifft "
                "jeden ohne Deckung. Es gibt keinen Grund, davon "
                "getroffen zu werden."
            ),
            steps=(
                "Die Deckungspunkte vor dem Pull festlegen.",
                "Beim Zauberbeginn sofort losgehen, nicht abwarten.",
                "Bis zum Ende des Zaubers in Deckung bleiben.",
            ),
            encounter="Horridon",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-horridon.mechanics.deadly_plague",
            title="Den Beschwörer unterbrechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Tödliche Seuche des Gurubashi-Beschwörers ist "
                "unterbrechbar - durchgelassen kostet sie den Raid "
                "erhebliche Heilung."
            ),
            steps=(
                "Eine feste Unterbrechungsreihenfolge festlegen.",
                "Den Beschwörer beim Erscheinen sofort markieren.",
                "Nach jeder Tür die Zuordnung neu bestätigen.",
            ),
            encounter="Horridon",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_INTERRUPT,
                    unit="×",
                    label="Verpasste Unterbrechungen",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-horridon.survival.venom",
            title="Aus der Giftpfütze heraus",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Giftpfütze richtet mit jeder Sekunde mehr "
                "Schaden an. Ein Schritt zur Seite beendet sie."
            ),
            steps=(
                "Die eigene Position nach jeder Salve prüfen.",
                "Nicht warten, bis die Heilung nachkommt.",
                "Die Pfützen nicht im Raid ablegen.",
            ),
            encounter="Horridon",
        ),

    ),

    "Immerseus": (

        Lesson(
            lesson_id="boss-immerseus.movement.swirl",
            title="Den Wasserwirbeln ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Wirbel bewegen sich langsam und vorhersehbar. "
                "Getroffen zu werden ist reine Unaufmerksamkeit."
            ),
            steps=(
                "Die Laufrichtung der Wirbel früh erkennen.",
                "Seitlich ausweichen, nicht davonlaufen.",
                "Beim Ausweichen weiter angreifen.",
            ),
            encounter="Immerseus",
            checks=(_no_hits("Vermeidbare Treffer bei Immerseus"),),
        ),

        Lesson(
            lesson_id="boss-immerseus.survival.puddles",
            title="Nicht in die Sha-Pfützen laufen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Pfützen stehen still. Wer hineinläuft, tut das "
                "immer selbst."
            ),
            steps=(
                "Beim Sammeln der Kugeln auf den Boden achten.",
                "Den Weg vorher planen statt der Kugel hinterher.",
                "Nach der Phase die Position zurücksetzen.",
            ),
            encounter="Immerseus",
        ),

    ),

}
