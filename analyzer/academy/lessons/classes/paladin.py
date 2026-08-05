"""Lektionen für Paladine."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    buff_uptime_check,
    cooldown_check,
    dispel_check,
    hot_uptime_check,
)

CLASS_NAME = "Paladin"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Vergeltung": (
        Lesson(
            lesson_id="paladin-retribution.rotation.inquisition",
            title="Inquisition ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Inquisition verstärkt den gesamten Heiligschaden. "
                "Jede Sekunde ohne sie ist spürbar schwächer."
            ),
            steps=(
                "Direkt beim Pull mit drei Kraft setzen.",
                "Vor Ablauf erneuern, nicht danach.",
                "Nie mit weniger als drei Kraft verlängern.",
            ),
            class_name=CLASS_NAME,
            spec="Vergeltung",
            checks=(buff_uptime_check("Inquisition", 90.0),),
        ),
        Lesson(
            lesson_id="paladin-retribution.cooldowns.avenging_wrath",
            title="Zorn des Rächers früh einsetzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Erst am Ende des Kampfes gezündet bringt der Zorn "
                "nur einen Bruchteil seiner möglichen Wirkung."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Vorher Inquisition setzen.",
                "Den zweiten Einsatz auf das Heldentum planen.",
            ),
            class_name=CLASS_NAME,
            spec="Vergeltung",
            checks=(cooldown_check("Avenging Wrath"),),
        ),
        Lesson(
            lesson_id="paladin-retribution.rotation.seal",
            title="Das richtige Siegel führen",
            category=CATEGORY_ROTATION,
            summary=(
                "Das Siegel wirkt auf jeden Angriff. Mit dem falschen "
                "oder gar keinem zu kämpfen ist ein dauerhafter "
                "Abzug, der in keiner Rotation auffällt."
            ),
            steps=(
                "Vor dem Pull das zum Kampf passende Siegel führen.",
                "Nach jedem Tod und jeder Rückkehr erneut prüfen.",
                "Bei vielen Zielen bewusst umschalten.",
            ),
            class_name=CLASS_NAME,
            spec="Vergeltung",
            checks=(buff_uptime_check("Seal of Truth", 95.0),),
        ),
        Lesson(
            lesson_id="paladin-retribution.rotation.dummy_practice",
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
            spec="Vergeltung",
        ),
    ),

    "Heilig": (
        Lesson(
            lesson_id="paladin-holy.rotation.beacon",
            title="Lichtblick sinnvoll setzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Lichtblick verdoppelt einen Teil jeder Heilung - "
                "auf dem falschen Ziel verpufft er."
            ),
            steps=(
                "Vor dem Pull auf dem Tank setzen, der Schaden nimmt.",
                "Beim Tankwechsel umsetzen.",
                "Die Uptime im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(hot_uptime_check("Beacon of Light", 90.0),),
        ),
        Lesson(
            lesson_id="paladin-holy.cooldowns.aura_mastery",
            title="Aurameisterschaft an der Spitze",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Aurameisterschaft wirkt raidweit und gehört auf "
                "die planbar größte Schadensspitze."
            ),
            steps=(
                "Die passende Aura vorher aktivieren.",
                "Den Zeitpunkt mit den Heilern abstimmen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(cooldown_check("Aura Mastery"),),
        ),
        Lesson(
            lesson_id="paladin-holy.rotation.holy_power",
            title="Heilige Kraft nicht liegen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Drei Heilige Kraft sind eine kostenlose, sehr starke "
                "Heilung. Sie ungenutzt stehen zu lassen ist die "
                "häufigste Manaverschwendung der Spezialisierung."
            ),
            steps=(
                "Die Anzeige für Heilige Kraft deutlich einrichten.",
                "Bei drei Kraft sofort ausgeben.",
                "Vor einer angesagten Spitze bewusst auf drei gehen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
        ),
        Lesson(
            lesson_id="paladin-holy.mechanics.cleanse",
            title="Reinigen fest übernehmen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Ein entfernter Effekt spart mehr Heilung, als jede "
                "Heilung ihn ausgleichen könnte - und der Heilige "
                "Paladin entfernt gleich drei Arten."
            ),
            steps=(
                "Die entfernbaren Effekte des Bosses auflisten.",
                "Klären, wer welchen entfernt.",
                "Das Reinigen auf eine erreichbare Taste legen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(dispel_check(),),
        ),
        Lesson(
            lesson_id="paladin-holy.cooldowns.lay_on_hands",
            title="Handauflegung als geplante Rettung",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Handauflegung ist ein volles Leben - benutzt wird sie "
                "meist zu spät oder gar nicht, weil niemand vorher "
                "wusste, wofür sie gedacht ist."
            ),
            steps=(
                "Mit der Raidleitung festlegen, wen sie im Notfall "
                "rettet.",
                "Sie auf eine Taste legen, die auch unter Druck sitzt.",
                "Nach dem Wipe prüfen, ob sie noch bereit war.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
        ),
    ),

    "Schutz": (
        Lesson(
            lesson_id="paladin-protection.survival.shield_of_righteous",
            title="Schild des Rechtschaffenen durchgehend halten",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die aktive Minderung des Schutzpaladins ist der "
                "größte Beitrag zum eigenen Überleben."
            ),
            steps=(
                "Heilige Kraft nicht überlaufen lassen.",
                "Vor jedem Bossangriff aktiv halten.",
                "Die Abdeckung im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
            checks=(buff_uptime_check("Shield of the Righteous", 55.0),),
        ),
        Lesson(
            lesson_id="paladin-protection.rotation.holy_power",
            title="Heilige Kraft ausschließlich in die Minderung stecken",
            category=CATEGORY_ROTATION,
            summary=(
                "Jede Heilige Kraft, die nicht im Schild des "
                "Rechtschaffenen landet, ist eine Sekunde ohne aktive "
                "Minderung - und die ist beim Schutzpaladin der "
                "größte Teil seines Überlebens."
            ),
            steps=(
                "Die Erzeuger auf Abklingzeit halten, nicht sammeln.",
                "Bei drei Kraft sofort die Minderung setzen.",
                "Nur für einen angesagten großen Treffer kurz sparen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
        ),
        Lesson(
            lesson_id="paladin-protection.cooldowns.ardent_defender",
            title="Glühender Verteidiger und Wächter trennen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Schutzpaladin hat zwei große Minderungen. "
                "Gleichzeitig gezündet decken sie ein Fenster ab, "
                "nacheinander zwei."
            ),
            steps=(
                "Beide je einer festen Bossmechanik zuordnen.",
                "Nie gemeinsam auslösen.",
                "Im Log auf Überschneidungen prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
            checks=(cooldown_check("Ardent Defender"),),
        ),
        Lesson(
            lesson_id="paladin-protection.mechanics.taunt",
            title="Tankwechsel und Handzauber absprechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Schutzpaladin kann als einziger Tank den "
                "Mittanks Schaden abnehmen - besprochen wird das "
                "selten, und dann kommt es zu spät."
            ),
            steps=(
                "Den Auslöser des Tankwechsels vorher benennen.",
                "Die Hand der Aufopferung fest auf den Wechsel legen.",
                "Nach dem Spott sofort die aktive Minderung setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Schutz",
        ),
    ),

    "": (
        Lesson(
            lesson_id="paladin.mechanics.hands",
            title="Die Handzauber tatsächlich verteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Hand des Schutzes, der Freiheit und der Aufopferung "
                "retten regelmäßig Pulls - sie werden vergessen, weil "
                "sie niemandem fest zugeteilt sind."
            ),
            steps=(
                "Für jede Hand eine Situation im Kampf benennen.",
                "Feste Ziele mit der Raidleitung vereinbaren.",
                "Die drei Zauber auf erreichbare Tasten legen.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="paladin.survival.divine_protection",
            title="Göttlichen Schutz regelmäßig einsetzen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Göttliche Schutz hat eine kurze Abklingzeit und "
                "passt vielfach in einen Kampf. Ihn für den Notfall "
                "aufzusparen heißt, ihn fast nie zu benutzen."
            ),
            steps=(
                "Die wiederkehrenden Treffer auf den eigenen Charakter "
                "benennen.",
                "Den Schutz fest darauf legen.",
                "Im Log prüfen, wie viele Einsätze möglich gewesen "
                "wären.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Divine Protection"),),
        ),
    ),

}
