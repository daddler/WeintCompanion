"""Lektionen für Priester."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_ROTATION,
    Lesson,
    cooldown_check,
    hot_uptime_check,
    uptime_check,
)

CLASS_NAME = "Priest"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Disziplin": (
        Lesson(
            lesson_id="priest-discipline.cooldowns.spirit_shell",
            title="Geistschild vor der Spitze aufbauen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Geistschild wandelt Heilung in Schilde um - er muss "
                "vor dem Schaden stehen, nicht danach."
            ),
            steps=(
                "Die Schadensspitze im Kampf benennen.",
                "Etwa acht Sekunden vorher zünden.",
                "Währenddessen möglichst breit heilen.",
            ),
            class_name=CLASS_NAME,
            spec="Disziplin",
            checks=(cooldown_check("Spirit Shell"),),
        ),
        Lesson(
            lesson_id="priest-discipline.rotation.shield",
            title="Machtwort Schild vorbeugend setzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Ein Schild verhindert Schaden, Heilung gleicht ihn "
                "nur aus. Vorbeugen ist immer günstiger."
            ),
            steps=(
                "Die Ziele der nächsten Mechanik vorher bestimmen.",
                "Den Schild vor dem Treffer setzen.",
                "Die Schwächungsdauer im Blick behalten.",
            ),
            class_name=CLASS_NAME,
            spec="Disziplin",
            checks=(
                hot_uptime_check("Power Word: Shield", 55.0),
            ),
        ),
    ),

    "Heilig": (
        Lesson(
            lesson_id="priest-holy.rotation.chakra",
            title="Chakra zur Kampfphase passend wählen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der falsche Chakra-Zustand kostet über einen ganzen "
                "Kampf mehr als jede einzelne Fehlentscheidung."
            ),
            steps=(
                "Vor dem Pull den Schwerpunkt bestimmen: Einzelziel "
                "oder Raid.",
                "Den passenden Zustand vor dem Pull setzen.",
                "Bei Phasenwechseln bewusst umschalten.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
        ),
        Lesson(
            lesson_id="priest-holy.cooldowns.divine_hymn",
            title="Göttliche Hymne abstimmen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Zwei große Raidheil-Cooldowns zur selben Sekunde "
                "heilen nicht doppelt, sondern überheilen doppelt."
            ),
            steps=(
                "Die Reihenfolge mit den anderen Heilern festlegen.",
                "Vor dem Kanalisieren sicher stehen.",
                "Nach dem Pull auf Überschneidungen prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(cooldown_check("Divine Hymn"),),
        ),
    ),

    "Schatten": (
        Lesson(
            lesson_id="priest-shadow.rotation.dots",
            title="Schmerz und Berührung durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Beide Dauereffekte erzeugen die Ressource der "
                "Spezialisierung. Ohne sie steht die Rotation still."
            ),
            steps=(
                "Beide Effekte in der Zielleiste beobachten.",
                "Vor dem Ablauf erneuern, nicht danach.",
                "Beim Zielwechsel zuerst beide auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Schatten",
            checks=(
                uptime_check("Shadow Word: Pain", 95.0),
                uptime_check("Vampiric Touch", 95.0),
            ),
        ),
        Lesson(
            lesson_id="priest-shadow.cooldowns.shadowfiend",
            title="Schattengeist regelmäßig einsetzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Schattengeist liefert Schaden und Mana - ihn "
                "aufzusparen bringt beides nicht."
            ),
            steps=(
                "Direkt nach Kampfbeginn zum ersten Mal rufen.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nicht auf sterbende Ziele setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Schatten",
            checks=(cooldown_check("Shadowfiend"),),
        ),
        Lesson(
            lesson_id="priest-shadow.rotation.dummy_practice",
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
            spec="Schatten",
        ),
    ),

}
