"""Lektionen für Schamanen."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    Lesson,
    cooldown_check,
    hot_uptime_check,
    uptime_check,
)

CLASS_NAME = "Shaman"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Wiederherstellung": (
        Lesson(
            lesson_id="shaman-resto.rotation.riptide",
            title="Springflut als Grundlage nutzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Springflut ist die günstigste Heilung der "
                "Spezialisierung und verstärkt die Kettenheilung."
            ),
            steps=(
                "Springflut bei jeder Verfügbarkeit setzen.",
                "Bevorzugt auf Ziele, die gleich Schaden bekommen.",
                "Vor der Kettenheilung auf das Startziel legen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Riptide", 80.0),),
        ),
        Lesson(
            lesson_id="shaman-resto.rotation.earth_shield",
            title="Erdschild auf dem Tank halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Erdschild kostet einmal Zeit und heilt danach den "
                "ganzen Kampf über von selbst."
            ),
            steps=(
                "Vor dem Pull auf dem aktiven Tank setzen.",
                "Die verbleibenden Ladungen im Blick behalten.",
                "Beim Tankwechsel umsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Earth Shield", 95.0),),
        ),
        Lesson(
            lesson_id="shaman-resto.cooldowns.healing_tide",
            title="Flut der Heilung an der Spitze setzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Flut wirkt raidweit und gehört auf die planbar "
                "größte Schadensspitze, nicht in die Panik."
            ),
            steps=(
                "Den Zeitpunkt mit den anderen Heilern absprechen.",
                "Das Totem in Reichweite des Raids stellen.",
                "Bei jeder Verfügbarkeit erneut nutzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(cooldown_check("Healing Tide Totem"),),
        ),
    ),

    "Elementar": (
        Lesson(
            lesson_id="shaman-elemental.rotation.flame_shock",
            title="Flammenschock ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Flammenschock ermöglicht den Lavastoß - ohne ihn "
                "fehlt der stärkste Zauber der Rotation."
            ),
            steps=(
                "Flammenschock dauerhaft auf dem Ziel halten.",
                "Mit dem Lavastoß verlängern statt neu zu wirken.",
                "Beim Zielwechsel zuerst auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
            checks=(uptime_check("Flame Shock", 92.0),),
        ),
        Lesson(
            lesson_id="shaman-elemental.cooldowns.elemental_mastery",
            title="Elementarbeherrschung regelmäßig zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Mit anderthalb Minuten Abklingzeit passt sie mehrfach "
                "in jeden Kampf. Aufsparen kostet Einsätze."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nur für Heldentum kurz aufsparen.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
            checks=(cooldown_check("Elemental Mastery"),),
        ),
    ),

    "Verstärkung": (
        Lesson(
            lesson_id="shaman-enhancement.rotation.maelstrom",
            title="Mahlstrom nicht überlaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Fünf Stapel Mahlstrom sind ein kostenloser Blitzschlag. "
                "Wer wartet, verliert Stapel."
            ),
            steps=(
                "Die Stapelanzeige deutlich einrichten.",
                "Bei fünf Stapeln sofort ausgeben.",
                "In Bewegungsphasen bewusst darauf sparen.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
        ),
        Lesson(
            lesson_id="shaman-enhancement.cooldowns.feral_spirit",
            title="Wilder Geist bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Wölfe laufen unabhängig von der eigenen Rotation "
                "und kosten nichts außer dem Tastendruck."
            ),
            steps=(
                "Direkt beim Pull rufen.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nicht auf sterbende Ziele setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
            checks=(cooldown_check("Feral Spirit"),),
        ),
    ),

    "": (
        Lesson(
            lesson_id="shaman.mechanics.totems",
            title="Totems zur Kampfsituation wählen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Totems sind der wandelbarste Beitrag der Klasse - "
                "und der am häufigsten vergessene."
            ),
            steps=(
                "Vor dem Pull die vier Totems bewusst wählen.",
                "Beim Phasenwechsel prüfen, ob sie noch passen.",
                "Auf Reichweite achten - Totems haben Radius.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
