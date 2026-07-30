"""Lektionen für Hexenmeister."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    uptime_check,
)

CLASS_NAME = "Warlock"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Gebrechen": (
        Lesson(
            lesson_id="warlock-affliction.rotation.dots",
            title="Alle drei Dauereffekte oben halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Gebrechen ist eine Buchhaltung. Jede Sekunde ohne "
                "einen der drei Effekte ist verlorener Schaden."
            ),
            steps=(
                "Agonie, Verderbnis und Instabiles Gebrechen im Blick "
                "behalten.",
                "Nur mit aktiver Verstärkung erneuern.",
                "Vor Phasenwechseln alle drei frisch auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Gebrechen",
            checks=(
                uptime_check("Agony", 95.0),
                uptime_check("Corruption", 95.0),
                uptime_check("Unstable Affliction", 92.0),
            ),
        ),
        Lesson(
            lesson_id="warlock-affliction.cooldowns.dark_soul",
            title="Dunkle Seele mit frischen Effekten zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Verstärkung wirkt auf den Effekten, die beim "
                "Auftragen bestanden - nicht rückwirkend."
            ),
            steps=(
                "Vor dem Zünden alle Effekte erneuern.",
                "Erst danach die Dunkle Seele auslösen.",
                "Während der Wirkung nicht neu auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Gebrechen",
            checks=(cooldown_check("Dark Soul: Misery"),),
        ),
    ),

    "Zerstörung": (
        Lesson(
            lesson_id="warlock-destruction.rotation.immolate",
            title="Feuerbrand ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Feuerbrand erzeugt die Glutsplitter. Läuft er ab, "
                "versiegt die gesamte Ressource."
            ),
            steps=(
                "Feuerbrand dauerhaft auf dem Hauptziel halten.",
                "Kurz vor Ablauf erneuern, nicht danach.",
                "Nach jeder Bewegungsphase zuerst nachlegen.",
            ),
            class_name=CLASS_NAME,
            spec="Zerstörung",
            checks=(uptime_check("Immolate", 95.0),),
        ),
        Lesson(
            lesson_id="warlock-destruction.rotation.embers",
            title="Glutsplitter nicht überlaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Volle Glutsplitter sind verschenkter Schaden - der "
                "Zuwachs verfällt einfach."
            ),
            steps=(
                "Die Splitteranzeige im Blick behalten.",
                "Vor dem Maximum einen Chaosblitz setzen.",
                "Splitter nur für Verstärkungen aufsparen.",
            ),
            class_name=CLASS_NAME,
            spec="Zerstörung",
        ),
    ),

    "Dämonologie": (
        Lesson(
            lesson_id="warlock-demonology.rotation.metamorphosis",
            title="Dämonische Wut sinnvoll ausgeben",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Wechsel in die Dämonenform lohnt nur mit genug "
                "Wut - zu früh gewechselt kostet mehr als er bringt."
            ),
            steps=(
                "Eine feste Wutschwelle für den Wechsel festlegen.",
                "In der Form nur die verstärkten Zauber nutzen.",
                "Vor dem Wechsel die Effekte auffrischen.",
            ),
            class_name=CLASS_NAME,
            spec="Dämonologie",
        ),
    ),

    "": (
        Lesson(
            lesson_id="warlock.survival.healthstone",
            title="Gesundheitssteine für den Raid stellen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Stein ist die günstigste Lebensversicherung des "
                "Raids - und niemand außer dem Hexenmeister kann ihn "
                "stellen."
            ),
            steps=(
                "Vor jedem Boss neu beschwören.",
                "Nach jedem Wipe erneut prüfen.",
                "Den eigenen Stein selbst benutzen.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
