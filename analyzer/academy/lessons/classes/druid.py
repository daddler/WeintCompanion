"""Lektionen für Druiden."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    hot_uptime_check,
    uptime_check,
)

CLASS_NAME = "Druid"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Gleichgewicht": (
        Lesson(
            lesson_id="druid-balance.cooldowns.celestial_alignment",
            title="Himmlische Ausrichtung im Eclipse-Höhepunkt",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Himmlische Ausrichtung wirkt nur dann voll, wenn sie "
                "im Maximum der aktuellen Eclipse gezündet wird."
            ),
            steps=(
                "Den Eclipse-Zeiger vor dem Zünden prüfen.",
                "Erst am Höhepunkt der Eclipse auslösen.",
                "Beide Schadenszauber währenddessen abwechseln.",
            ),
            class_name=CLASS_NAME,
            spec="Gleichgewicht",
            checks=(cooldown_check("Celestial Alignment"),),
        ),
        Lesson(
            lesson_id="druid-balance.rotation.moonfire",
            title="Mondfeuer und Sonnenfeuer durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Beide Dauereffekte laufen unabhängig von der Eclipse "
                "weiter und dürfen nie ablaufen."
            ),
            steps=(
                "Beide Effekte in der Zielleiste im Blick behalten.",
                "In der jeweils passenden Eclipse verlängern.",
                "Nach jeder Bewegungsphase zuerst nachlegen.",
            ),
            class_name=CLASS_NAME,
            spec="Gleichgewicht",
            checks=(
                uptime_check("Moonfire", 95.0),
                uptime_check("Sunfire", 95.0),
            ),
        ),
        Lesson(
            lesson_id="druid-balance.movement.instants",
            title="Eclipse-Wechsel für Bewegung nutzen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Moment des Eclipse-Wechsels ist die günstigste "
                "Gelegenheit, sich neu zu positionieren."
            ),
            steps=(
                "Bewegungsphasen des Kampfes notieren.",
                "Den Eclipse-Wechsel gedanklich darauf legen.",
                "Während der Bewegung nur Sofortzauber wirken.",
            ),
            class_name=CLASS_NAME,
            spec="Gleichgewicht",
        ),
        Lesson(
            lesson_id="druid-balance.rotation.dummy_practice",
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
            spec="Gleichgewicht",
        ),
    ),

    "Wiederherstellung": (
        Lesson(
            lesson_id="druid-resto.rotation.lifebloom",
            title="Lebensblüte auf dem Tank halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Lebensblüte ist die Grundlage der eigenen Heilung. "
                "Läuft sie ab, bricht die gesamte Kette weg."
            ),
            steps=(
                "Lebensblüte fest auf dem aktiven Tank halten.",
                "Rechtzeitig vor Ablauf auffrischen.",
                "Beim Tankwechsel sofort umsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Lifebloom", 95.0),),
        ),
        Lesson(
            lesson_id="druid-resto.rotation.rejuvenation",
            title="Verjüngung vor der Schadensspitze verteilen",
            category=CATEGORY_ROTATION,
            summary=(
                "Verjüngung entfaltet ihre Wirkung über Zeit - nach "
                "dem Treffer aufgetragen kommt sie zu spät."
            ),
            steps=(
                "Die Schadensspitzen des Kampfes notieren.",
                "Etwa fünf Sekunden vorher verteilen.",
                "Im Log die Uptime auf dem Raid prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Rejuvenation", 80.0),),
        ),
        Lesson(
            lesson_id="druid-resto.cooldowns.tranquility",
            title="Seelenruhe an die richtige Stelle legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Seelenruhe ist der stärkste Raidheil-Cooldown der "
                "Klasse und gehört an die planbar größte Spitze."
            ),
            steps=(
                "Mit den anderen Heilern die Reihenfolge abstimmen.",
                "Einen festen Zeitpunkt im Kampf vereinbaren.",
                "Vor dem Kanalisieren sicher stehen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(cooldown_check("Tranquility"),),
        ),
    ),

    "Wilder Kampf": (
        Lesson(
            lesson_id="druid-feral.rotation.bleeds",
            title="Blutungen nie ablaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Riss und Fetzen tragen den Großteil des Schadens. "
                "Jede Sekunde ohne sie ist verloren."
            ),
            steps=(
                "Beide Blutungen dauerhaft im Blick behalten.",
                "Riss nur mit voller Combopunktzahl erneuern.",
                "Vor Phasenwechseln beide frisch auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Wilder Kampf",
            checks=(
                uptime_check("Rake", 90.0),
                uptime_check("Rip", 90.0),
            ),
        ),
        Lesson(
            lesson_id="druid-feral.survival.survival_instincts",
            title="Überlebensinstinkte einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Als Nahkämpfer steht man dort, wo der meiste "
                "vermeidbare Schaden liegt - die Defensive gehört fest "
                "in den Ablauf."
            ),
            steps=(
                "Die Bossmechanik mit dem höchsten Schaden benennen.",
                "Die Defensive fest darauf legen.",
                "Nach dem Pull prüfen, ob sie genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            spec="Wilder Kampf",
        ),
        Lesson(
            lesson_id="druid-feral.rotation.dummy_practice",
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
            spec="Wilder Kampf",
        ),
    ),

    "Wächter": (
        Lesson(
            lesson_id="druid-guardian.survival.savage_defense",
            title="Wilde Verteidigung durchgehend halten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die aktive Minderung des Wächters trägt über einen "
                "Kampf mehr als jeder große Cooldown."
            ),
            steps=(
                "Zorn nicht über das Maximum laufen lassen.",
                "Vor jedem Bossangriff aktiv halten.",
                "Im Log die Abdeckung prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Wächter",
        ),
    ),

}
