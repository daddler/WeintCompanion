"""Lektionen für Krieger."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    uptime_check,
)

CLASS_NAME = "Warrior"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Schutz": (
        Lesson(
            lesson_id="warrior-protection.survival.shield_block",
            title="Schildblock durchgehend halten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die aktive Minderung des Schutzkriegers trägt über "
                "einen Kampf mehr als alle großen Cooldowns zusammen."
            ),
            steps=(
                "Wut nicht über das Maximum laufen lassen.",
                "Vor jedem Bossangriff aktiv halten.",
                "Im Log die Abdeckung über den Kampf prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
        ),
        Lesson(
            lesson_id="warrior-protection.cooldowns.shield_wall",
            title="Schildwall und Letztes Gefecht trennen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Beide gleichzeitig zu zünden verschenkt einen davon. "
                "Nacheinander decken sie die doppelte Zeit ab."
            ),
            steps=(
                "Beide festen Bossmechaniken zuordnen.",
                "Nie gemeinsam auslösen.",
                "Im Log auf Überschneidungen prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
            checks=(cooldown_check("Shield Wall"),),
        ),
    ),

    "Waffen": (
        Lesson(
            lesson_id="warrior-arms.rotation.rend",
            title="Verwunden ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Verwunden kostet wenig und trägt über den ganzen "
                "Kampf spürbaren Schaden bei."
            ),
            steps=(
                "Verwunden dauerhaft auf dem Ziel halten.",
                "Vor dem Ablauf erneuern.",
                "Beim Zielwechsel zuerst auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Waffen",
            checks=(uptime_check("Rend", 90.0),),
        ),
        Lesson(
            lesson_id="warrior-arms.cooldowns.recklessness",
            title="Tollkühnheit auf das Heldentum legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Tollkühnheit vervielfacht kritische Treffer - im "
                "Heldentum trifft sie am häufigsten."
            ),
            steps=(
                "Mit der Raidleitung das Heldentum abstimmen.",
                "Tollkühnheit bis dahin aufsparen, wenn möglich.",
                "Zusammen mit dem Kampftrank zünden.",
            ),
            class_name=CLASS_NAME,
            spec="Waffen",
            checks=(cooldown_check("Recklessness"),),
        ),
        Lesson(
            lesson_id="warrior-arms.rotation.dummy_practice",
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
            spec="Waffen",
        ),
    ),

    "Furor": (
        Lesson(
            lesson_id="warrior-fury.rotation.enrage",
            title="Wutrausch nicht auslaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Furor lebt vom Wutrausch. Jede Sekunde ohne ihn ist "
                "spürbar schwächer."
            ),
            steps=(
                "Die Wutrausch-Anzeige deutlich einrichten.",
                "Den Auslöser rechtzeitig nachsetzen.",
                "Verstärkte Fähigkeiten nur im Rausch nutzen.",
            ),
            class_name=CLASS_NAME,
            spec="Furor",
        ),
        Lesson(
            lesson_id="warrior-fury.rotation.dummy_practice",
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
            spec="Furor",
        ),
    ),

}
