"""Lektionen für Jäger."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    dispel_check,
    uptime_check,
)

CLASS_NAME = "Hunter"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Treffsicherheit": (
        Lesson(
            lesson_id="hunter-marksmanship.rotation.steady_focus",
            title="Stetigen Fokus aufrechterhalten",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Effekt erhöht die Fokusregeneration und muss "
                "regelmäßig erneuert werden."
            ),
            steps=(
                "Zwei gleiche Schüsse hintereinander setzen.",
                "Den Effekt vor Ablauf erneuern.",
                "Nach Bewegungsphasen zuerst nachsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Treffsicherheit",
        ),
        Lesson(
            lesson_id="hunter-marksmanship.rotation.serpent_sting",
            title="Schlangengift durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Das Gift kostet einmal Fokus und wirkt danach über "
                "den ganzen Kampf."
            ),
            steps=(
                "Direkt beim Pull auftragen.",
                "Vor Ablauf erneuern.",
                "Beim Zielwechsel zuerst setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Treffsicherheit",
            checks=(uptime_check("Serpent Sting", 92.0),),
        ),
        Lesson(
            lesson_id="hunter-marksmanship.cooldowns.rapid_fire",
            title="Schnellfeuer nicht bis zum Ende aufsparen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Mit fünf Minuten Abklingzeit passt Schnellfeuer nur "
                "ein- bis zweimal in einen Kampf. Ungenutzt ist es ganz "
                "verloren."
            ),
            steps=(
                "Den ersten Einsatz früh im Kampf setzen.",
                "Den zweiten fest auf das Heldentum legen.",
                "Im Log prüfen, ob es überhaupt genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            spec="Treffsicherheit",
            checks=(cooldown_check("Rapid Fire", 90.0),),
        ),
        Lesson(
            lesson_id="hunter-marksmanship.mechanics.tranquilizing_shot",
            title="Beruhigenden Schuss übernehmen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Jäger entfernt Wut- und Magieeffekte von Gegnern. "
                "In mehreren Kämpfen ist das die eigentliche Mechanik - "
                "und sie wird vergessen, weil sie kein Heilerzauber "
                "ist."
            ),
            steps=(
                "Vor dem Pull klären, welche Effekte zu entfernen sind.",
                "Den Schuss auf eine erreichbare Taste legen.",
                "Auf die Ansage reagieren, nicht auf den Schaden.",
            ),
            class_name=CLASS_NAME,
            spec="Treffsicherheit",
            checks=(dispel_check(),),
        ),
        Lesson(
            lesson_id="hunter-marksmanship.rotation.dummy_practice",
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
            spec="Treffsicherheit",
        ),
    ),

    "Tierherrschaft": (
        Lesson(
            lesson_id="hunter-beastmastery.cooldowns.bestial_wrath",
            title="Animalische Wut bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Eine Minute Abklingzeit bedeutet viele mögliche "
                "Einsätze - jeder ausgelassene ist spürbar."
            ),
            steps=(
                "Vorher genug Fokus ansammeln.",
                "Bei jeder Verfügbarkeit zünden.",
                "Auf die Reichweite des Begleiters achten.",
            ),
            class_name=CLASS_NAME,
            spec="Tierherrschaft",
            checks=(cooldown_check("Bestial Wrath"),),
        ),
        Lesson(
            lesson_id="hunter-beastmastery.rotation.pet",
            title="Den Begleiter am Ziel halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Ein Begleiter, der hinter dem Jäger herläuft, macht "
                "keinen Schaden - und er trägt einen großen Teil davon."
            ),
            steps=(
                "Den Begleiter vor dem Pull ans Ziel schicken.",
                "Nach jeder Mechanik die Position prüfen.",
                "Bei Phasenwechseln neu befehligen.",
            ),
            class_name=CLASS_NAME,
            spec="Tierherrschaft",
        ),
        Lesson(
            lesson_id="hunter-beastmastery.cooldowns.stampede",
            title="Stampede mit den Verstärkungen bündeln",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Stampede übernimmt die Verstärkungen im Moment "
                "des Rufens - allein gezündet ist sie ein Bruchteil "
                "wert."
            ),
            steps=(
                "Erst Verstärkungen und Trank, dann die Stampede.",
                "Auf das Heldentum legen, wenn es dorthin passt.",
                "Nicht kurz vor einem Zielwechsel rufen.",
            ),
            class_name=CLASS_NAME,
            spec="Tierherrschaft",
            checks=(cooldown_check("Stampede"),),
        ),
        Lesson(
            lesson_id="hunter-beastmastery.rotation.dummy_practice",
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
            spec="Tierherrschaft",
        ),
    ),

    "Überleben": (
        Lesson(
            lesson_id="hunter-survival.rotation.explosive",
            title="Explosivschuss als Vorrang behandeln",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Explosivschuss ist die stärkste Fähigkeit der "
                "Spezialisierung und hat immer Vorrang."
            ),
            steps=(
                "Genug Fokus für ihn zurückhalten.",
                "Bei jeder Verfügbarkeit sofort setzen.",
                "Nie durch einen Fülzauber verzögern.",
            ),
            class_name=CLASS_NAME,
            spec="Überleben",
        ),
        Lesson(
            lesson_id="hunter-survival.rotation.serpent_sting",
            title="Schlangengift durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Beim Überlebensjäger verstärkt das Gift zusätzlich "
                "den Explosivschuss - ohne es fehlt nicht nur der "
                "eigene Schaden, sondern auch der der Hauptfähigkeit."
            ),
            steps=(
                "Direkt beim Pull auftragen.",
                "Vor Ablauf erneuern.",
                "Beim Zielwechsel zuerst setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Überleben",
            checks=(uptime_check("Serpent Sting", 92.0),),
        ),
        Lesson(
            lesson_id="hunter-survival.cooldowns.black_arrow",
            title="Schwarzen Pfeil auf Abklingzeit halten",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Schwarze Pfeil erzeugt die Gelegenheiten für den "
                "Explosivschuss. Steht er ungenutzt, versiegt die "
                "halbe Rotation."
            ),
            steps=(
                "Bei jeder Verfügbarkeit sofort setzen.",
                "Nicht auf sterbende Ziele wirken.",
                "Nach Phasenwechseln zuerst nachholen.",
            ),
            class_name=CLASS_NAME,
            spec="Überleben",
            checks=(cooldown_check("Black Arrow"),),
        ),
        Lesson(
            lesson_id="hunter-survival.rotation.dummy_practice",
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
            spec="Überleben",
        ),
    ),

    "": (
        Lesson(
            lesson_id="hunter.movement.no_penalty",
            title="Den Bewegungsvorteil ausspielen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Jäger verliert beim Laufen fast keinen Schaden. "
                "Genau deshalb sollte er die Mechaniken übernehmen, die "
                "Bewegung verlangen."
            ),
            steps=(
                "Im Raid anbieten, laufintensive Aufgaben zu übernehmen.",
                "Beim Laufen weiter angreifen statt zu pausieren.",
                "Die Aktivzeit im Log gegenprüfen.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="hunter.mechanics.misdirection",
            title="Ablenkung beim Pull abgeben",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Ablenkung schenkt dem Tank die gesamte "
                "Bedrohung der nächsten Angriffe - sie kostet den "
                "Jäger nichts und wird trotzdem selten benutzt."
            ),
            steps=(
                "Ein festes Ziel mit den Tanks vereinbaren.",
                "Direkt vor dem Pull abgeben.",
                "Bei jedem Add-Ansturm erneut.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="hunter.survival.deterrence",
            title="Abschreckung als geplante Antwort",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Abschreckung hebt ganze Mechaniken auf. Als "
                "Notausgang benutzt kommt sie fast immer zu spät."
            ),
            steps=(
                "Die Mechaniken benennen, die sie aufhebt.",
                "Die Abschreckung fest darauf legen.",
                "Nach dem Pull prüfen, ob sie genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Deterrence"),),
        ),
    ),

}
