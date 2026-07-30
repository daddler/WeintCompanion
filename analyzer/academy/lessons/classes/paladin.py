"""Lektionen für Paladine."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    hot_uptime_check,
)

CLASS_NAME = "Paladin"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Vergeltung": (
        Lesson(
            lesson_id="paladin-retribution.rotation.inquisition",
            title="Inquisition ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Inquisition verstärkt den gesamten Heiligschaden. "
                "Jede Sekunde ohne sie ist spürbar schwächer."
            ),
            steps=(
                "Direkt beim Pull mit drei Kraft setzen.",
                "Vor Ablauf erneuern, nicht danach.",
                "Nie mit weniger als drei Kraft verlängern.",
            ),
            class_name=CLASS_NAME,
            spec="Vergeltung",
        ),
        Lesson(
            lesson_id="paladin-retribution.cooldowns.avenging_wrath",
            title="Zorn des Rächers früh einsetzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Erst am Ende des Kampfes gezündet bringt der Zorn "
                "nur einen Bruchteil seiner möglichen Wirkung."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Vorher Inquisition setzen.",
                "Den zweiten Einsatz auf das Heldentum planen.",
            ),
            class_name=CLASS_NAME,
            spec="Vergeltung",
            checks=(cooldown_check("Avenging Wrath"),),
        ),
    ),

    "Heilig": (
        Lesson(
            lesson_id="paladin-holy.rotation.beacon",
            title="Lichtblick sinnvoll setzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Lichtblick verdoppelt einen Teil jeder Heilung - "
                "auf dem falschen Ziel verpufft er."
            ),
            steps=(
                "Vor dem Pull auf dem Tank setzen, der Schaden nimmt.",
                "Beim Tankwechsel umsetzen.",
                "Die Uptime im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(hot_uptime_check("Beacon of Light", 90.0),),
        ),
        Lesson(
            lesson_id="paladin-holy.cooldowns.aura_mastery",
            title="Aurameisterschaft an der Spitze",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Aurameisterschaft wirkt raidweit und gehört auf "
                "die planbar größte Schadensspitze."
            ),
            steps=(
                "Die passende Aura vorher aktivieren.",
                "Den Zeitpunkt mit den Heilern abstimmen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(cooldown_check("Aura Mastery"),),
        ),
    ),

    "Schutz": (
        Lesson(
            lesson_id="paladin-protection.survival.shield_of_righteous",
            title="Schild des Rechtschaffenen durchgehend halten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die aktive Minderung des Schutzpaladins ist der "
                "größte Beitrag zum eigenen Überleben."
            ),
            steps=(
                "Heilige Kraft nicht überlaufen lassen.",
                "Vor jedem Bossangriff aktiv halten.",
                "Die Abdeckung im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
        ),
    ),

}
