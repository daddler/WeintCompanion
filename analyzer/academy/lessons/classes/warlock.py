"""Lektionen für Hexenmeister."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
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
        Lesson(
            lesson_id="warlock-affliction.rotation.haunt",
            title="Heimsuchung als Verstärker einsetzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Die Heimsuchung verstärkt alle laufenden Effekte auf "
                "dem Ziel. Splitter dafür aufzusparen ist verschenkter "
                "Schaden, denn sie erzeugen sich nach."
            ),
            steps=(
                "Die Splitter nicht am Maximum stehen lassen.",
                "Die Heimsuchung vor den großen Verstärkungen setzen.",
                "Vor Phasenwechseln bewusst ausgeben.",
            ),
            class_name=CLASS_NAME,
            spec="Gebrechen",
        ),
        Lesson(
            lesson_id="warlock-affliction.rotation.dummy_practice",
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
                "hakt sich danach von selbst ab.",
            ),
            class_name=CLASS_NAME,
            spec="Gebrechen",
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
        Lesson(
            lesson_id="warlock-destruction.cooldowns.dark_soul",
            title="Dunkle Seele mit vollen Splittern zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Verstärkung wirkt nur so lange, wie man sie auch "
                "in Schaden umsetzen kann - ohne Splitter im Vorrat "
                "verpufft die halbe Wirkung."
            ),
            steps=(
                "Vor dem Zünden Splitter ansammeln.",
                "Erst danach die Dunkle Seele auslösen.",
                "Auf das Heldentum legen, wenn es dorthin passt.",
            ),
            class_name=CLASS_NAME,
            spec="Zerstörung",
            checks=(cooldown_check("Dark Soul: Instability"),),
        ),
        Lesson(
            lesson_id="warlock-destruction.rotation.dummy_practice",
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
                "hakt sich danach von selbst ab.",
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
        Lesson(
            lesson_id="warlock-demonology.rotation.doom",
            title="Verdammnis in der Dämonenform auftragen",
            category=CATEGORY_ROTATION,
            summary=(
                "Verdammnis läuft sehr lange und trägt einen großen "
                "Teil des Schadens - vergessen wird sie, weil sie nur "
                "in der Form gewirkt werden kann."
            ),
            steps=(
                "Beim ersten Wechsel in die Form sofort auftragen.",
                "Vor Ablauf erneut in die Form wechseln.",
                "Bei mehreren Zielen auf allen verteilen.",
            ),
            class_name=CLASS_NAME,
            spec="Dämonologie",
            checks=(uptime_check("Doom", 90.0),),
        ),
        Lesson(
            lesson_id="warlock-demonology.cooldowns.dark_soul",
            title="Dunkle Seele an die Dämonenform koppeln",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Verstärkung wirkt am stärksten, während die "
                "verstärkten Zauber der Form laufen - getrennt "
                "gezündet verschenken sich beide."
            ),
            steps=(
                "Vor dem Zünden genug Wut für die Form ansammeln.",
                "Beide gemeinsam auslösen.",
                "Auf das Heldentum legen, wenn es dorthin passt.",
            ),
            class_name=CLASS_NAME,
            spec="Dämonologie",
            checks=(cooldown_check("Dark Soul: Knowledge"),),
        ),
        Lesson(
            lesson_id="warlock-demonology.rotation.dummy_practice",
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
                "hakt sich danach von selbst ab.",
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
        Lesson(
            lesson_id="warlock.mechanics.soulstone",
            title="Seelenstein vor dem Pull setzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Seelenstein ist eine zusätzliche Wiederbelebung, "
                "die nichts kostet - vergessen wird sie regelmäßig "
                "genau in den Pulls, in denen sie den Kill gerettet "
                "hätte."
            ),
            steps=(
                "Vor jedem Pull ein festes Ziel setzen - meist ein "
                "Heiler.",
                "Nach jedem Wipe erneut prüfen.",
                "Mit der Raidleitung klären, wer ihn bekommt.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="warlock.survival.unending_resolve",
            title="Unendliche Entschlossenheit einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die persönliche Minderung des Hexenmeisters "
                "unterbricht kein Zaubern und steht regelmäßig "
                "bereit - es gibt kaum einen Grund, sie nicht zu "
                "benutzen."
            ),
            steps=(
                "Die wiederkehrenden Treffer auf den eigenen "
                "Charakter benennen.",
                "Die Minderung fest darauf legen.",
                "Nach dem Pull prüfen, ob sie genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Unending Resolve"),),
        ),
        Lesson(
            lesson_id="warlock.mechanics.gateway",
            title="Dämonisches Portal für lange Wege stellen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Das Portal spart dem ganzen Raid Laufweg. Es hilft "
                "nur, wenn es vor der Mechanik steht - und wenn alle "
                "wissen, wo."
            ),
            steps=(
                "Vor dem Pull klären, welche Wege der Kampf verlangt.",
                "Das Portal vor der Phase stellen, nicht darin.",
                "Die Position im Raidchat ansagen.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
