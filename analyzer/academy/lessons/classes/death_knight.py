"""Lektionen für Todesritter."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    uptime_check,
)

CLASS_NAME = "Death Knight"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Unheilig": (
        Lesson(
            lesson_id="deathknight-unholy.cooldowns.dark_transformation",
            title="Dunkle Verwandlung bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Verwandlung hat eine kurze Abklingzeit und passt "
                "vielfach in einen Kampf - jeder ausgelassene Einsatz "
                "zählt."
            ),
            steps=(
                "Genug Schattenmale ansammeln.",
                "Bei jeder Verfügbarkeit sofort verwandeln.",
                "Im Log die Zahl der Einsätze prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
            checks=(cooldown_check("Dark Transformation"),),
        ),
        Lesson(
            lesson_id="deathknight-unholy.rotation.diseases",
            title="Beide Seuchen durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Blutseuche und Frostfieber verstärken den gesamten "
                "übrigen Schaden. Ohne sie steht die Rotation halb "
                "still."
            ),
            steps=(
                "Beide Seuchen beim Pull auftragen.",
                "Mit dem passenden Angriff verlängern.",
                "Beim Zielwechsel zuerst neu auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
            checks=(
                uptime_check("Blood Plague", 92.0),
                uptime_check("Frost Fever", 92.0),
            ),
        ),
        Lesson(
            lesson_id="deathknight-unholy.rotation.dummy_practice",
            title="Prioritätenliste an der Trainingspuppe üben",
            category=CATEGORY_ROTATION,
            summary=(
                "Die Prioritätenliste sitzt erst, wenn sie ohne "
                "Nachdenken kommt - eine Trainingspuppe ist der "
                "richtige Ort dafür, nicht der Raid."
            ),
            steps=(
                "Im Addon an eine Trainingspuppe treten oder "
                "/wc training nutzen.",
                "Das Fenster zeigt die Prioritätenliste live mit.",
                "An drei Tagen in Folge mit guter Trefferquote üben - "
                "hakt sich danach von selbst ab.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
        ),
    ),

    "Frost": (
        Lesson(
            lesson_id="deathknight-frost.cooldowns.pillar_of_frost",
            title="Säule des Frosts regelmäßig zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Eine Minute Abklingzeit bedeutet viele mögliche "
                "Einsätze - aufsparen lohnt nur fürs Heldentum."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Mit dem Kampftrank bündeln.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
            checks=(cooldown_check("Pillar of Frost"),),
        ),
        Lesson(
            lesson_id="deathknight-frost.rotation.runes",
            title="Runen nicht voll stehen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Voll regenerierte Runen sind verschenkte Zeit - die "
                "Regeneration läuft dann ins Leere."
            ),
            steps=(
                "Die Runenanzeige deutlich einrichten.",
                "Nie mehr als zwei Runen gleichzeitig bereit halten.",
                "Runenmacht vor dem Maximum ausgeben.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
        Lesson(
            lesson_id="deathknight-frost.rotation.dummy_practice",
            title="Prioritätenliste an der Trainingspuppe üben",
            category=CATEGORY_ROTATION,
            summary=(
                "Die Prioritätenliste sitzt erst, wenn sie ohne "
                "Nachdenken kommt - eine Trainingspuppe ist der "
                "richtige Ort dafür, nicht der Raid."
            ),
            steps=(
                "Im Addon an eine Trainingspuppe treten oder "
                "/wc training nutzen.",
                "Das Fenster zeigt die Prioritätenliste live mit.",
                "An drei Tagen in Folge mit guter Trefferquote üben - "
                "hakt sich danach von selbst ab.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
    ),

    "Blut": (
        Lesson(
            lesson_id="deathknight-blood.survival.blood_shield",
            title="Blutschild aufrechterhalten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Blutschild ist die aktive Minderung des "
                "Blut-Todesritters und trägt mehr als jeder große "
                "Cooldown."
            ),
            steps=(
                "Todesstoß rechtzeitig setzen.",
                "Den Schild vor jedem Bossangriff auffrischen.",
                "Die Abdeckung im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Blut",
        ),
    ),

    "": (
        Lesson(
            lesson_id="deathknight.mechanics.anti_magic_zone",
            title="Anti-Magie-Zone für den Raid setzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Zone ist ein Raid-Cooldown und gehört abgesprochen "
                "auf eine bestimmte Mechanik."
            ),
            steps=(
                "Mit der Raidleitung einen Zeitpunkt vereinbaren.",
                "Die Zone dort setzen, wo der Raid steht.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Anti-Magic Zone"),),
        ),
    ),

}
