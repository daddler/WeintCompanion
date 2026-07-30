"""
Lektionen nach Rolle.

Diese Ebene ist neu und schließt die größte Lücke des ersten
Katalogs: Ratschläge zu Überleben und Cooldowns unterscheiden sich
weit stärker nach Rolle als nach Spezialisierung. Ein Tank braucht
eine andere Antwort auf "vermeidbarer Schaden" als ein Zauberer, und
zwar unabhängig davon, ob er Krieger oder Mönch ist.

Ohne diese Ebene fiele beides auf die allgemeinen Lektionen zurück -
die notwendigerweise so allgemein sind, dass sie niemandem konkret
weiterhelfen.
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    CHECK_AT_LEAST,
    CHECK_AT_MOST,
    Lesson,
    LessonCheck,
)
from analyzer.models import (
    MECHANIC_DEFENSIVE,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
)


ROLE_LESSONS: dict[str, tuple[Lesson, ...]] = {

    #
    # --------------------------------------------------
    # Tank
    # --------------------------------------------------
    #

    ROLE_TANK: (

        Lesson(
            lesson_id="role-tank.survival.rotation",
            title="Defensives rotieren statt stapeln",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Zwei Defensivfähigkeiten gleichzeitig zu zünden "
                "verschenkt eine davon. Nacheinander decken sie die "
                "doppelte Zeit ab."
            ),
            steps=(
                "Alle eigenen Defensivfähigkeiten mit Dauer und "
                "Abklingzeit auflisten.",
                "Sie in eine feste Reihenfolge bringen.",
                "Im Log prüfen, ob sich zwei überlappt haben.",
            ),
            roles=(ROLE_TANK,),
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_DEFENSIVE,
                    unit="×",
                    label="Ungenutzte Defensivfenster",
                ),
            ),
        ),

        Lesson(
            lesson_id="role-tank.survival.active",
            title="Aktive Schadensminderung durchgehend halten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die kurze, ständig verfügbare Minderung trägt über "
                "einen Kampf mehr als jeder große Cooldown."
            ),
            steps=(
                "Die eigene aktive Minderung und ihre Laufzeit prüfen.",
                "Sie an den Angriffsrhythmus des Bosses koppeln.",
                "Nie zwei Bossangriffe ohne sie kassieren.",
            ),
            roles=(ROLE_TANK,),
        ),

        Lesson(
            lesson_id="role-tank.mechanics.swap",
            title="Tankwechsel sauber ausführen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Wechsel entscheidet sich in zwei Sekunden - "
                "vorher abgesprochen ist er unspektakulär, spontan "
                "ist er ein Wipe."
            ),
            steps=(
                "Den Auslöser des Wechsels benennen: Stapel, Zeit "
                "oder Zauber.",
                "Eine Ansage vereinbaren, die vor dem Wechsel kommt.",
                "Der übernehmende Tank steht bereits in Reichweite.",
            ),
            roles=(ROLE_TANK,),
        ),

        Lesson(
            lesson_id="role-tank.movement.positioning",
            title="Den Boss ruhig halten",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Jede unnötige Drehung des Bosses kostet den Nahkampf "
                "Schaden und riskiert Frontalangriffe im Raid."
            ),
            steps=(
                "Eine feste Tankposition je Phase festlegen.",
                "Den Boss nur bewegen, wenn eine Mechanik es verlangt.",
                "Beim Bewegen rückwärts gehen, nicht drehen.",
            ),
            roles=(ROLE_TANK,),
        ),

    ),

    #
    # --------------------------------------------------
    # Heiler
    # --------------------------------------------------
    #

    ROLE_HEALER: (

        Lesson(
            lesson_id="role-healer.rotation.hots",
            title="Heileffekte vor dem Schaden auftragen",
            category=CATEGORY_ROTATION,
            summary=(
                "Ein Heileffekt, der erst nach dem Treffer beginnt, "
                "kommt immer zu spät. Vorbereitete Heilung ist die "
                "günstigste Heilung."
            ),
            steps=(
                "Die wiederkehrenden Schadensspitzen des Kampfes "
                "notieren.",
                "Die eigenen Dauerheileffekte davor auftragen.",
                "Im Log die Uptime dieser Effekte prüfen.",
            ),
            roles=(ROLE_HEALER,),
            checks=(
                LessonCheck(
                    metric="hot_uptime",
                    comparison=CHECK_AT_LEAST,
                    target=80.0,
                    unit="%",
                    label="Mittlere HoT-Uptime",
                ),
            ),
        ),

        Lesson(
            lesson_id="role-healer.cooldowns.plan",
            title="Heil-Cooldowns im Raid absprechen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Zwei große Heil-Cooldowns zur selben Sekunde heilen "
                "nicht doppelt - sie überheilen doppelt."
            ),
            steps=(
                "Alle großen Heil-Cooldowns des Raids auflisten.",
                "Sie den Schadensspitzen des Kampfes fest zuordnen.",
                "Nach dem Pull prüfen, ob sich zwei überschnitten "
                "haben.",
            ),
            roles=(ROLE_HEALER,),
        ),

        Lesson(
            lesson_id="role-healer.mechanics.dispel",
            title="Effekte rechtzeitig entfernen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Ein entfernter Effekt spart mehr Heilung, als jede "
                "Heilung ihn ausgleichen könnte."
            ),
            steps=(
                "Die entfernbaren Effekte des Bosses auflisten.",
                "Klären, wer welchen entfernt.",
                "Die Entzauberung auf eine erreichbare Taste legen.",
            ),
            roles=(ROLE_HEALER,),
        ),

        Lesson(
            lesson_id="role-healer.rotation.mana",
            title="Mana über den ganzen Kampf einteilen",
            category=CATEGORY_ROTATION,
            summary=(
                "Wer in der ersten Hälfte alles verbrennt, fehlt "
                "genau dann, wenn der Kampf entschieden wird."
            ),
            steps=(
                "Den eigenen Manaverlauf über einen Pull ansehen.",
                "Die teuersten Zauber und ihren Anteil bestimmen.",
                "Feste Zeitpunkte für die Manawiederherstellung "
                "einplanen.",
            ),
            roles=(ROLE_HEALER,),
        ),

    ),

    #
    # --------------------------------------------------
    # Schadensausteiler
    # --------------------------------------------------
    #

    ROLE_DPS: (

        Lesson(
            lesson_id="role-dps.rotation.opener",
            title="Den Auftakt festlegen und üben",
            category=CATEGORY_ROTATION,
            summary=(
                "Die ersten zwanzig Sekunden sind die einzigen, in "
                "denen alle Cooldowns gleichzeitig bereit sind. Sie "
                "verdienen eine eingeübte Reihenfolge."
            ),
            steps=(
                "Die optimale Auftaktreihenfolge der eigenen "
                "Spezialisierung nachschlagen.",
                "Sie an der Übungspuppe zehnmal spielen.",
                "Im Log die ersten zwanzig Sekunden nachprüfen.",
            ),
            roles=(ROLE_DPS,),
        ),

        Lesson(
            lesson_id="role-dps.cooldowns.pairing",
            title="Cooldowns gemeinsam zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Cooldowns, die sich gegenseitig verstärken, gehören "
                "zusammen. Einzeln gezündet verschenken sie ihren "
                "Multiplikator."
            ),
            steps=(
                "Prüfen, welche eigenen Cooldowns sich verstärken.",
                "Sie zu festen Paaren zusammenfassen.",
                "Die Paare gemeinsam auf eine Makrotaste legen.",
            ),
            roles=(ROLE_DPS,),
        ),

        Lesson(
            lesson_id="role-dps.rotation.range",
            title="In Reichweite bleiben",
            category=CATEGORY_ROTATION,
            summary=(
                "Die häufigste Ursache für Lücken in der Aktivzeit ist "
                "nicht die Bewegung selbst, sondern der Weg zurück in "
                "Reichweite."
            ),
            steps=(
                "Die eigene maximale Reichweite kennen.",
                "Beim Ausweichen die kürzeste Strecke wählen.",
                "Nach der Mechanik sofort zurück in Reichweite.",
            ),
            roles=(ROLE_DPS,),
        ),

        Lesson(
            lesson_id="role-dps.mechanics.help",
            title="Nutzfähigkeiten tatsächlich einsetzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Verlangsamungen, Betäubungen und Schutzzauber "
                "gewinnen Kämpfe. Sie kosten keinen nennenswerten "
                "Schaden."
            ),
            steps=(
                "Die eigenen Nutzfähigkeiten auflisten.",
                "Jeder eine Situation im Kampf zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            roles=(ROLE_DPS,),
        ),

    ),

}
