"""Lektionen für Druiden."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    buff_uptime_check,
    cooldown_check,
    dispel_check,
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
            lesson_id="druid-balance.mechanics.adds",
            title="Beide Dauereffekte auf die Adds verteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Gleichgewichtsdruide ist eine der stärksten "
                "Antworten auf mehrere Ziele - vorausgesetzt, die "
                "Effekte liegen auch dort."
            ),
            steps=(
                "Beim Erscheinen der Adds zuerst die Effekte "
                "verteilen.",
                "Erst danach zum Hauptziel zurückkehren.",
                "Die Zielgesundheit im Blick behalten, damit nichts "
                "verpufft.",
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
        Lesson(
            lesson_id="druid-resto.cooldowns.ironbark",
            title="Eisenrinde auf den Tank legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Eisenrinde ist eine Minderung, die man einem anderen "
                "gibt - und die einzige des Wiederherstellungsdruiden. "
                "Ungenutzt ist sie in jedem Kampf mehrfach verschenkt."
            ),
            steps=(
                "Mit den Tanks feste Zeitpunkte vereinbaren.",
                "Sie vor dem angesagten Treffer setzen, nicht danach.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(cooldown_check("Ironbark"),),
        ),
        Lesson(
            lesson_id="druid-resto.mechanics.dispel",
            title="Effekte rechtzeitig entfernen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Ein entfernter Effekt spart mehr Heilung, als jede "
                "Heilung ihn ausgleichen könnte."
            ),
            steps=(
                "Die entfernbaren Effekte des Bosses auflisten.",
                "Klären, wer welchen entfernt.",
                "Die Entzauberung auf eine erreichbare Taste legen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(dispel_check(),),
        ),
        Lesson(
            lesson_id="druid-resto.rotation.mana",
            title="Verjüngung nicht blind über den Raid streuen",
            category=CATEGORY_ROTATION,
            summary=(
                "Verjüngung ist die teuerste Gewohnheit der "
                "Spezialisierung: auf unbeschädigte Ziele gelegt "
                "kostet sie Mana und heilt nichts."
            ),
            steps=(
                "Vor der Spitze verteilen, nicht dauerhaft überall.",
                "Ziele bevorzugen, die gleich Schaden bekommen.",
                "Den Manaverlauf nach dem Pull ansehen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
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
            lesson_id="druid-feral.rotation.savage_roar",
            title="Wildes Brüllen ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Wildes Brüllen verstärkt jeden Angriff und jede "
                "Blutung. Es abfallen zu lassen kostet mehr als jeder "
                "einzelne verpasste Finisher."
            ),
            steps=(
                "Direkt zu Kampfbeginn setzen.",
                "Vor Ablauf verlängern, notfalls mit wenigen "
                "Combopunkten.",
                "Vor Phasenwechseln bewusst auffrischen.",
            ),
            class_name=CLASS_NAME,
            spec="Wilder Kampf",
            checks=(buff_uptime_check("Savage Roar", 90.0),),
        ),
        Lesson(
            lesson_id="druid-feral.cooldowns.tigers_fury",
            title="Raserei des Tigers bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Raserei hat eine sehr kurze Abklingzeit und gibt "
                "zusätzlich Energie - jeder ausgelassene Einsatz ist "
                "doppelt verloren."
            ),
            steps=(
                "Vor dem Zünden Energie tief genug ausgeben.",
                "Bei jeder Verfügbarkeit sofort nutzen.",
                "Im Log die Zahl der Einsätze prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Wilder Kampf",
            checks=(cooldown_check("Tiger's Fury"),),
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
            checks=(buff_uptime_check("Savage Defense", 55.0),),
        ),
        Lesson(
            lesson_id="druid-guardian.rotation.rage",
            title="Zorn in Wilde Verteidigung umsetzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Wächter erzeugt Zorn dadurch, dass er geschlagen "
                "wird. Wer ihn nicht sofort in Minderung umsetzt, "
                "verliert ihn am Maximum - und mindert dann gar "
                "nichts."
            ),
            steps=(
                "Zorn nie über das Maximum laufen lassen.",
                "Die Minderung vor dem Bossangriff setzen, nicht "
                "danach.",
                "Die Erzeuger auf Abklingzeit halten.",
            ),
            class_name=CLASS_NAME,
            spec="Wächter",
        ),
        Lesson(
            lesson_id="druid-guardian.cooldowns.survival_instincts",
            title="Überlebensinstinkte und Baumrinde trennen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Zwei Minderungen gleichzeitig zu zünden deckt ein "
                "Fenster ab, nacheinander zwei."
            ),
            steps=(
                "Beide je einer festen Bossmechanik zuordnen.",
                "Nie gemeinsam auslösen.",
                "Im Log auf Überschneidungen prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Wächter",
            checks=(cooldown_check("Survival Instincts"),),
        ),
        Lesson(
            lesson_id="druid-guardian.mechanics.taunt",
            title="Tankwechsel und Adds absprechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Wächter sammelt Gegner schnell ein - der Wechsel "
                "entscheidet sich trotzdem in zwei Sekunden und gehört "
                "vorher besprochen."
            ),
            steps=(
                "Den Auslöser des Wechsels benennen: Stapel, Zeit oder "
                "Zauber.",
                "Vor dem Spott bereits in Reichweite stehen.",
                "Nach dem Spott sofort die aktive Minderung setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wächter",
        ),
    ),

    "": (
        Lesson(
            lesson_id="druid.survival.barkskin",
            title="Baumrinde regelmäßig einsetzen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Baumrinde hat eine kurze Abklingzeit, kostet nichts "
                "und unterbricht keine Zauber. Es gibt praktisch "
                "keinen Grund, sie nicht zu benutzen."
            ),
            steps=(
                "Die wiederkehrenden Treffer auf den eigenen Charakter "
                "benennen.",
                "Baumrinde fest darauf legen.",
                "Im Log prüfen, wie viele Einsätze möglich gewesen "
                "wären.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Barkskin"),),
        ),
        Lesson(
            lesson_id="druid.mechanics.symbiosis",
            title="Symbiose vor dem Pull setzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Symbiose verschenkt eine Fähigkeit an einen "
                "Mitspieler und bringt eine zurück. Vergessen wird sie "
                "fast immer - sie hält einen Tod lang."
            ),
            steps=(
                "Vor dem Pull ein festes Ziel vereinbaren.",
                "Nach jedem Tod und jedem Wipe neu setzen.",
                "Die erhaltene Fähigkeit auf eine Taste legen.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
