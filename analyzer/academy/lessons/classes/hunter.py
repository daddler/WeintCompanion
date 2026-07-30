"""Lektionen für Jäger."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    Lesson,
    cooldown_check,
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
    ),

}
