"""Lektionen für Schurken."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    Lesson,
    cooldown_check,
    uptime_check,
)

CLASS_NAME = "Rogue"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Meucheln": (
        Lesson(
            lesson_id="rogue-assassination.rotation.rupture",
            title="Blutung durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Die Blutung trägt einen großen Teil des Schadens und "
                "speist zusätzlich die Ressource."
            ),
            steps=(
                "Nur mit fünf Combopunkten erneuern.",
                "Vor dem Ablauf verlängern, nicht danach.",
                "Beim Zielwechsel zuerst wieder auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Meucheln",
            checks=(uptime_check("Rupture", 92.0),),
        ),
        Lesson(
            lesson_id="rogue-assassination.rotation.energy",
            title="Energie nicht überlaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Volle Energie ist verschenkter Schaden - die "
                "Regeneration läuft dann ins Leere."
            ),
            steps=(
                "Die Energieanzeige im Blick behalten.",
                "Vor dem Maximum einen Erzeuger einschieben.",
                "In Bewegungsphasen bewusst aufsparen.",
            ),
            class_name=CLASS_NAME,
            spec="Meucheln",
        ),
        Lesson(
            lesson_id="rogue-assassination.cooldowns.shadow_blades",
            title="Schattenklingen mit Verstärkungen bündeln",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Schattenklingen wirken multiplikativ mit den übrigen "
                "Cooldowns - einzeln gezündet verschenken sie das."
            ),
            steps=(
                "Alle eigenen Cooldowns zu einem Paket bündeln.",
                "Das Paket auf das Heldentum legen.",
                "Vorher die Blutung auffrischen.",
            ),
            class_name=CLASS_NAME,
            spec="Meucheln",
            checks=(cooldown_check("Shadow Blades"),),
        ),
    ),

    "Kampf": (
        Lesson(
            lesson_id="rogue-combat.cooldowns.adrenaline_rush",
            title="Adrenalinrausch früh und oft",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Rausch beschleunigt die gesamte Rotation. "
                "Aufsparen kostet vollständige Einsätze."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nur kurz für das Heldentum zurückhalten.",
            ),
            class_name=CLASS_NAME,
            spec="Kampf",
            checks=(cooldown_check("Adrenaline Rush"),),
        ),
        Lesson(
            lesson_id="rogue-combat.rotation.slice_and_dice",
            title="Schnetzeln ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Schnetzeln erhöht das Angriffstempo dauerhaft und "
                "darf nie ablaufen."
            ),
            steps=(
                "Direkt beim Pull setzen.",
                "Rechtzeitig vor Ablauf verlängern.",
                "Vor Phasenwechseln auffrischen.",
            ),
            class_name=CLASS_NAME,
            spec="Kampf",
        ),
    ),

    "Täuschung": (
        Lesson(
            lesson_id="rogue-subtlety.rotation.find_weakness",
            title="Schwachstelle finden ausnutzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Das Zeitfenster nach dem Öffnen aus der Verstohlenheit "
                "ist das stärkste der Spezialisierung."
            ),
            steps=(
                "Das Fenster bewusst mitzählen.",
                "Darin nur die stärksten Fähigkeiten nutzen.",
                "Das Öffnen für Phasenwechsel aufsparen.",
            ),
            class_name=CLASS_NAME,
            spec="Täuschung",
        ),
    ),

    "": (
        Lesson(
            lesson_id="rogue.mechanics.tricks",
            title="Schurkenhandel abgeben",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Handel verstärkt einen anderen Spieler und kostet "
                "den Schurken nichts."
            ),
            steps=(
                "Ein festes Ziel vereinbaren.",
                "Direkt beim Pull abgeben.",
                "Danach bei jeder Verfügbarkeit erneut.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
