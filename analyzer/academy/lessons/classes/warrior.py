"""Lektionen für Krieger."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    buff_uptime_check,
    cooldown_check,
    defensive_check,
    interrupt_check,
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
            checks=(buff_uptime_check("Shield Block", 55.0),),
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
        Lesson(
            lesson_id="warrior-protection.rotation.rage",
            title="Wut zwischen Block und Barriere aufteilen",
            category=CATEGORY_ROTATION,
            summary=(
                "Schildblock hilft gegen viele kleine Treffer, die "
                "Schildbarriere gegen einen großen. Wer immer dasselbe "
                "drückt, mindert die Hälfte der Zeit das Falsche."
            ),
            steps=(
                "Vor dem Pull klären, ob der Boss körperlich oder "
                "magisch schlägt.",
                "Gegen Nahkampffolgen den Block halten.",
                "Gegen einzelne große Treffer und Magie die Barriere "
                "setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
        ),
        Lesson(
            lesson_id="warrior-protection.mechanics.taunt",
            title="Spott und Tankwechsel absprechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Ein Spott zur falschen Sekunde dreht den Boss in den "
                "Raid - der Wechsel gehört vorher besprochen, nicht im "
                "Moment entschieden."
            ),
            steps=(
                "Den Auslöser des Wechsels benennen: Stapel, Zeit oder "
                "Zauber.",
                "Vor dem Spott bereits in Reichweite stehen.",
                "Nach dem Spott sofort die aktive Minderung setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
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
            lesson_id="warrior-arms.rotation.colossus_smash",
            title="Das Rüstungsfenster vollständig füllen",
            category=CATEGORY_ROTATION,
            summary=(
                "Waffen dreht sich um das kurze Fenster, in dem die "
                "Rüstung des Ziels ausgehebelt ist. Alles, was daneben "
                "fällt, trifft auf volle Rüstung."
            ),
            steps=(
                "Vor dem Fenster genug Wut ansammeln.",
                "Im Fenster ausschließlich die stärksten Angriffe "
                "setzen.",
                "Fülzauber bewusst außerhalb des Fensters unterbringen.",
            ),
            class_name=CLASS_NAME,
            spec="Waffen",
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
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
            lesson_id="warrior-fury.cooldowns.recklessness",
            title="Tollkühnheit mit dem Wutrausch bündeln",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Tollkühnheit wirkt multiplikativ mit allem, was "
                "gleichzeitig läuft - einzeln gezündet verschenkt sie "
                "den größten Teil davon."
            ),
            steps=(
                "Tollkühnheit, Trank und Wutrausch zu einem Paket "
                "bündeln.",
                "Das Paket auf den Kampfbeginn und das Heldentum legen.",
                "Im Log prüfen, wie viele Einsätze möglich gewesen "
                "wären.",
            ),
            class_name=CLASS_NAME,
            spec="Furor",
            checks=(cooldown_check("Recklessness"),),
        ),
        Lesson(
            lesson_id="warrior-fury.survival.enraged_regeneration",
            title="Die eigene Heilung nicht vergessen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Furorkrieger heilt sich selbst - im Raid wird das "
                "regelmäßig vergessen und der Heiler bezahlt es."
            ),
            steps=(
                "Die eigene Heilfähigkeit auf eine erreichbare Taste "
                "legen.",
                "Sie nach jeder großen Mechanik einsetzen.",
                "Nicht auf den Notfall warten - sie heilt über Zeit.",
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
                "hakt sich danach von selbst ab.",
            ),
            class_name=CLASS_NAME,
            spec="Furor",
        ),
    ),

    "": (
        Lesson(
            lesson_id="warrior.mechanics.pummel",
            title="Knüppeln fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Jede Spezialisierung des Kriegers bringt eine "
                "Unterbrechung mit kurzer Abklingzeit mit. Vergessen "
                "wird sie, weil niemand zugeteilt war."
            ),
            steps=(
                "Vor dem Pull eine feste Unterbrecherreihenfolge "
                "vereinbaren.",
                "Die Unterbrechung auf eine gut erreichbare Taste legen.",
                "Nach dem Pull prüfen, ob eine Unterbrechung fehlte.",
            ),
            class_name=CLASS_NAME,
            checks=(interrupt_check(),),
        ),
        Lesson(
            lesson_id="warrior.cooldowns.rallying_cry",
            title="Sammelschrei als Raid-Cooldown einplanen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Sammelschrei gibt dem ganzen Raid Leben und ist "
                "damit ein Raid-Cooldown - er gehört in den Plan der "
                "Raidleitung, nicht in die eigene Panik."
            ),
            steps=(
                "Mit der Raidleitung einen festen Zeitpunkt vereinbaren.",
                "Ihn vor der Schadensspitze auslösen, nicht danach.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Rallying Cry"),),
        ),
        Lesson(
            lesson_id="warrior.mechanics.spell_reflection",
            title="Zauberreflexion gegen angesagte Zauber",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Reflexion verhindert nicht nur Schaden, sie gibt "
                "ihn zurück - vorausgesetzt, sie steht vor dem Zauber "
                "und nicht nach ihm."
            ),
            steps=(
                "Die reflektierbaren Zauber des Bosses auflisten.",
                "Die Reflexion fest darauf legen.",
                "Auf die Ansage achten, nicht auf den Treffer.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="warrior.survival.defensive_stance",
            title="Für angesagte Spitzen in die Verteidigungshaltung",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Haltung zu wechseln kostet ein paar Sekunden "
                "Schaden und halbiert dafür einen Treffer, der sonst "
                "tödlich ist. Im Raid wird sie fast nie benutzt, weil "
                "sie nicht in der Rotation steht."
            ),
            steps=(
                "Die angesagten Flächentreffer des Kampfes benennen.",
                "Für genau diese in die Verteidigungshaltung wechseln.",
                "Danach sofort zurückwechseln, nicht darin bleiben.",
            ),
            class_name=CLASS_NAME,
            checks=(defensive_check(),),
        ),
    ),

}
