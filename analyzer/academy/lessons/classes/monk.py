"""Lektionen für Mönche."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    hot_uptime_check,
)

CLASS_NAME = "Monk"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Braumeister": (
        Lesson(
            lesson_id="monk-brewmaster.survival.stagger",
            title="Benommenheit aktiv abbauen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Benommenheit verteilt Schaden über Zeit. Wer sie "
                "nicht abbaut, stirbt an der Summe statt am Treffer."
            ),
            steps=(
                "Die Benommenheitsstufe im Blick behalten.",
                "Ab der mittleren Stufe abbauen.",
                "Im Log prüfen, wie oft die hohe Stufe erreicht wurde.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
        ),
        Lesson(
            lesson_id="monk-brewmaster.survival.guard",
            title="Wache regelmäßig einsetzen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Wache hat eine kurze Abklingzeit und passt vielfach "
                "in jeden Kampf - aufzusparen kostet Einsätze."
            ),
            steps=(
                "Wache an den Angriffsrhythmus des Bosses koppeln.",
                "Nicht auf den Notfall warten.",
                "Im Log die Zahl der Einsätze prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
            checks=(cooldown_check("Guard"),),
        ),
    ),

    "Nebelwirker": (
        Lesson(
            lesson_id="monk-mistweaver.rotation.renewing_mist",
            title="Erneuernder Nebel dauerhaft im Umlauf",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Nebel springt weiter und erzeugt die Ressource "
                "der Spezialisierung. Er darf nie stillstehen."
            ),
            steps=(
                "Bei jeder Verfügbarkeit neu setzen.",
                "Bevorzugt auf Ziele in der Nähe anderer.",
                "Im Log die Uptime auf dem Raid prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(hot_uptime_check("Renewing Mist", 80.0),),
        ),
        Lesson(
            lesson_id="monk-mistweaver.cooldowns.revival",
            title="Erweckung an der Spitze setzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Erweckung heilt raidweit und entfernt Effekte - beide "
                "Wirkungen wollen den richtigen Moment."
            ),
            steps=(
                "Den Zeitpunkt mit den Heilern abstimmen.",
                "Bevorzugt nutzen, wenn zusätzlich Effekte anliegen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(cooldown_check("Revival"),),
        ),
    ),

    "Windwandler": (
        Lesson(
            lesson_id="monk-windwalker.rotation.tiger_power",
            title="Tigerkraft nicht auslaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Tigerkraft senkt die Rüstung des Ziels und wirkt auf "
                "jeden folgenden Treffer."
            ),
            steps=(
                "Die Anzeige deutlich einrichten.",
                "Vor Ablauf erneuern, nicht danach.",
                "Nach Bewegungsphasen zuerst nachsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
        ),
        Lesson(
            lesson_id="monk-windwalker.rotation.dummy_practice",
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
            spec="Windwandler",
        ),
        Lesson(
            lesson_id="monk-windwalker.mechanics.ring_of_peace",
            title="Nutzfähigkeiten des Mönchs einsetzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Mönch bringt Unterbrechung, Betäubung und "
                "Verlangsamung mit - alle drei werden regelmäßig "
                "vergessen."
            ),
            steps=(
                "Die eigenen Nutzfähigkeiten auflisten.",
                "Jeder eine Kampfsituation zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
        ),
    ),

}
