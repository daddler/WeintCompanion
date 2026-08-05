"""Lektionen für Todesritter."""

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

CLASS_NAME = "Death Knight"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Unheilig": (
        Lesson(
            lesson_id="deathknight-unholy.cooldowns.dark_transformation",
            title="Dunkle Verwandlung bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Verwandlung hat eine kurze Abklingzeit und passt "
                "vielfach in einen Kampf - jeder ausgelassene Einsatz "
                "zählt."
            ),
            steps=(
                "Genug Schattenmale ansammeln.",
                "Bei jeder Verfügbarkeit sofort verwandeln.",
                "Im Log die Zahl der Einsätze prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
            checks=(cooldown_check("Dark Transformation"),),
        ),
        Lesson(
            lesson_id="deathknight-unholy.rotation.diseases",
            title="Beide Seuchen durchgehend halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Blutseuche und Frostfieber verstärken den gesamten "
                "übrigen Schaden. Ohne sie steht die Rotation halb "
                "still."
            ),
            steps=(
                "Beide Seuchen beim Pull auftragen.",
                "Mit dem passenden Angriff verlängern.",
                "Beim Zielwechsel zuerst neu auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
            checks=(
                uptime_check("Blood Plague", 92.0),
                uptime_check("Frost Fever", 92.0),
            ),
        ),
        Lesson(
            lesson_id="deathknight-unholy.cooldowns.summon_gargoyle",
            title="Gargoyle mit den Verstärkungen zusammen rufen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Gargoyle übernimmt die Werte im Moment des Rufens. "
                "Ohne aktive Verstärkungen fliegt er den ganzen Kampf "
                "mit schlechteren Werten."
            ),
            steps=(
                "Erst Verstärkungen und Trank zünden, dann rufen.",
                "Den Ruf auf das Heldentum legen, wenn er dorthin passt.",
                "Nicht kurz vor einem Phasenwechsel rufen.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
            checks=(cooldown_check("Summon Gargoyle"),),
        ),
        Lesson(
            lesson_id="deathknight-unholy.mechanics.adds",
            title="Tod und Verfall auf die Gruppen legen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Unheilig ist die stärkste Antwort auf mehrere Ziele - "
                "vorausgesetzt, die Seuchen und die Fläche liegen dort, "
                "wo die Adds stehen."
            ),
            steps=(
                "Den Sammelpunkt der Adds vorher kennen.",
                "Die Seuchen zuerst verteilen, dann die Fläche legen.",
                "Die Fläche nicht dort setzen, wo die Adds gleich "
                "weggezogen werden.",
            ),
            class_name=CLASS_NAME,
            spec="Unheilig",
        ),
        Lesson(
            lesson_id="deathknight-unholy.rotation.dummy_practice",
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
            spec="Unheilig",
        ),
    ),

    "Frost": (
        Lesson(
            lesson_id="deathknight-frost.cooldowns.pillar_of_frost",
            title="Säule des Frosts regelmäßig zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Eine Minute Abklingzeit bedeutet viele mögliche "
                "Einsätze - aufsparen lohnt nur fürs Heldentum."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Mit dem Kampftrank bündeln.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
            checks=(cooldown_check("Pillar of Frost"),),
        ),
        Lesson(
            lesson_id="deathknight-frost.rotation.runes",
            title="Runen nicht voll stehen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Voll regenerierte Runen sind verschenkte Zeit - die "
                "Regeneration läuft dann ins Leere."
            ),
            steps=(
                "Die Runenanzeige deutlich einrichten.",
                "Nie mehr als zwei Runen gleichzeitig bereit halten.",
                "Runenmacht vor dem Maximum ausgeben.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
        Lesson(
            lesson_id="deathknight-frost.rotation.soul_reaper",
            title="Seelenernter in der Hinrichtungsphase setzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Unter fünfunddreißig Prozent Bossleben ist der "
                "Seelenernter die stärkste Fähigkeit der "
                "Spezialisierung - und die am häufigsten vergessene."
            ),
            steps=(
                "Eine Ansage oder Anzeige für die Schwelle einrichten.",
                "Ab der Schwelle bei jeder Verfügbarkeit setzen.",
                "Danach sofort den nächsten Angriff nachschieben.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
        Lesson(
            lesson_id="deathknight-frost.survival.anti_magic_shell",
            title="Anti-Magie-Hülle gegen Magieschaden einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Hülle schluckt Magieschaden vollständig und "
                "erzeugt dabei noch Runenmacht - sie ungenutzt zu "
                "lassen kostet doppelt."
            ),
            steps=(
                "Die magischen Angriffe des Bosses auflisten.",
                "Die Hülle fest auf den größten davon legen.",
                "Nach dem Pull prüfen, ob sie überhaupt lief.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
            checks=(cooldown_check("Anti-Magic Shell"),),
        ),
        Lesson(
            lesson_id="deathknight-frost.rotation.dummy_practice",
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
            spec="Frost",
        ),
    ),

    "Blut": (
        Lesson(
            lesson_id="deathknight-blood.survival.blood_shield",
            title="Blutschild aufrechterhalten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Blutschild ist die aktive Minderung des "
                "Blut-Todesritters und trägt mehr als jeder große "
                "Cooldown."
            ),
            steps=(
                "Todesstoß rechtzeitig setzen.",
                "Den Schild vor jedem Bossangriff auffrischen.",
                "Die Abdeckung im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Blut",
            checks=(buff_uptime_check("Blood Shield", 55.0),),
        ),
        Lesson(
            lesson_id="deathknight-blood.rotation.bone_shield",
            title="Knochenschild nie ablaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Knochenschild mindert jeden Treffer und ist die "
                "billigste Minderung, die der Blut-Todesritter hat - "
                "sie kostet nur den rechtzeitigen Tastendruck."
            ),
            steps=(
                "Vor dem Pull mit vollen Ladungen aufstellen.",
                "Die Ladungen im Blick behalten, nicht erst die Dauer.",
                "Nach jedem Ladungsverlust sofort nachsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Blut",
            checks=(buff_uptime_check("Bone Shield", 85.0),),
        ),
        Lesson(
            lesson_id="deathknight-blood.cooldowns.vampiric_blood",
            title="Vampirblut auf die geplante Spitze legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Vampirblut erhöht Leben und erhaltene Heilung - beides "
                "wirkt nur, wenn es vor dem Schaden steht."
            ),
            steps=(
                "Die härteste Angriffsfolge des Bosses benennen.",
                "Vampirblut fest darauf legen, nicht auf die Panik.",
                "Mit den Heilern absprechen, wann es kommt.",
            ),
            class_name=CLASS_NAME,
            spec="Blut",
            checks=(cooldown_check("Vampiric Blood"),),
        ),
        Lesson(
            lesson_id="deathknight-blood.mechanics.adds",
            title="Adds mit Todesgriff und Höllenpforte einsammeln",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Blut-Todesritter sammelt Gegner schneller ein als "
                "jeder andere Tank - genutzt wird das selten."
            ),
            steps=(
                "Vor dem Pull klären, wo die Adds gebunden werden.",
                "Den Todesgriff für den ersten Kontakt reservieren.",
                "Tod und Verfall vor die Gruppe legen, nicht darunter.",
            ),
            class_name=CLASS_NAME,
            spec="Blut",
        ),

    ),

    "": (
        Lesson(
            lesson_id="deathknight.mechanics.anti_magic_zone",
            title="Anti-Magie-Zone für den Raid setzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Zone ist ein Raid-Cooldown und gehört abgesprochen "
                "auf eine bestimmte Mechanik."
            ),
            steps=(
                "Mit der Raidleitung einen Zeitpunkt vereinbaren.",
                "Die Zone dort setzen, wo der Raid steht.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Anti-Magic Zone"),),
        ),
        Lesson(
            lesson_id="deathknight.mechanics.mind_freeze",
            title="Geistesgefrierung fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Jede Spezialisierung des Todesritters hat eine "
                "Unterbrechung mit kurzer Abklingzeit. Sie wird trotzdem "
                "regelmäßig vergessen, weil niemand zugeteilt wurde."
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
            lesson_id="deathknight.survival.icebound_fortitude",
            title="Eisgebundene Unverwüstlichkeit einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die persönliche Minderung des Todesritters steht in "
                "jedem Kampf mehrfach zur Verfügung - ungenutzt ist sie "
                "verschenkt."
            ),
            steps=(
                "Die zwei größten Treffer auf den eigenen Charakter "
                "benennen.",
                "Die Minderung fest darauf legen.",
                "Im Log prüfen, wie viele Einsätze möglich gewesen wären.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Icebound Fortitude"),),
        ),

    ),

}
