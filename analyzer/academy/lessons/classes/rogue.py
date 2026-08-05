"""Lektionen für Schurken."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    buff_uptime_check,
    cooldown_check,
    interrupt_check,
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
        Lesson(
            lesson_id="rogue-assassination.rotation.slice_and_dice",
            title="Schnetzeln durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Schnetzeln erhöht das Angriffstempo und damit die "
                "Energieregeneration - es abfallen zu lassen bremst "
                "die ganze Rotation, nicht nur den Autoangriff."
            ),
            steps=(
                "Direkt nach dem ersten Finisher setzen.",
                "Rechtzeitig vor Ablauf verlängern.",
                "Vor Phasenwechseln auffrischen.",
            ),
            class_name=CLASS_NAME,
            spec="Meucheln",
            checks=(buff_uptime_check("Slice and Dice", 95.0),),
        ),
        Lesson(
            lesson_id="rogue-assassination.rotation.dummy_practice",
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
            spec="Meucheln",
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
            checks=(buff_uptime_check("Slice and Dice", 95.0),),
        ),
        Lesson(
            lesson_id="rogue-combat.cooldowns.killing_spree",
            title="Amoklauf nicht in der Mechanik zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Amoklauf springt selbstständig zwischen Zielen - "
                "im falschen Moment gezündet steht man danach dort, wo "
                "man nicht stehen wollte."
            ),
            steps=(
                "Vor dem Zünden prüfen, welche Mechanik ansteht.",
                "Ihn im Adrenalinrausch nutzen, nicht daneben.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Kampf",
            checks=(cooldown_check("Killing Spree"),),
        ),
        Lesson(
            lesson_id="rogue-combat.rotation.dummy_practice",
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
        Lesson(
            lesson_id="rogue-subtlety.rotation.rupture",
            title="Blutung durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Auch in der Täuschung trägt die Blutung einen "
                "großen Teil des Schadens - und sie verstärkt "
                "zusätzlich die eigenen Angriffe."
            ),
            steps=(
                "Nur mit fünf Combopunkten erneuern.",
                "Vor dem Ablauf verlängern, nicht danach.",
                "Beim Zielwechsel zuerst wieder auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Täuschung",
            checks=(uptime_check("Rupture", 90.0),),
        ),
        Lesson(
            lesson_id="rogue-subtlety.cooldowns.shadow_dance",
            title="Schattentanz vollständig ausnutzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Schattentanz ist ein kurzes Fenster, in dem die "
                "stärksten Fähigkeiten offen stehen. Wer darin die "
                "falschen drückt, hat ihn verschenkt."
            ),
            steps=(
                "Vor dem Tanz genug Energie ansammeln.",
                "Im Fenster ausschließlich die Öffner-Angriffe nutzen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Täuschung",
            checks=(cooldown_check("Shadow Dance"),),
        ),
        Lesson(
            lesson_id="rogue-subtlety.rotation.dummy_practice",
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
        Lesson(
            lesson_id="rogue.mechanics.kick",
            title="Tritt fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Schurke hat eine der kürzesten Unterbrechungen im "
                "Spiel. Vergessen wird sie, weil niemand zugeteilt war."
            ),
            steps=(
                "Vor dem Pull eine feste Unterbrecherreihenfolge "
                "vereinbaren.",
                "Den Tritt auf eine gut erreichbare Taste legen.",
                "Nach dem Pull prüfen, ob eine Unterbrechung fehlte.",
            ),
            class_name=CLASS_NAME,
            checks=(interrupt_check(),),
        ),
        Lesson(
            lesson_id="rogue.survival.defensives",
            title="Umhang und Finte einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Umhang der Schatten hebt ganze Magiemechaniken "
                "auf, die Finte halbiert Flächenschaden. Beide sind "
                "billig und werden fast nie benutzt."
            ),
            steps=(
                "Die magischen und die flächigen Treffer trennen.",
                "Jedem der beiden Zauber eine Mechanik zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Cloak of Shadows"),),
        ),
    ),

}
