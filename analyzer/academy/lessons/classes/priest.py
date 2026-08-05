"""Lektionen für Priester."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    defensive_check,
    dispel_check,
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
        Lesson(
            lesson_id="priest-discipline.cooldowns.barrier",
            title="Machtwort: Barriere vor die Spitze legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Barriere ist einer der stärksten Raid-Cooldowns "
                "des Spiels - und wirkt nur dort, wo der Raid steht, "
                "wenn sie fällt."
            ),
            steps=(
                "Den Zeitpunkt mit der Raidleitung vereinbaren.",
                "Sie dorthin legen, wo der Raid im Moment des Treffers "
                "steht.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Disziplin",
            checks=(cooldown_check("Power Word: Barrier"),),
        ),
        Lesson(
            lesson_id="priest-discipline.cooldowns.pain_suppression",
            title="Schmerzunterdrückung für den Tank reservieren",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Schmerzunterdrückung ist eine Minderung, die man "
                "einem anderen gibt. Als Nothilfe gedacht, kommt sie "
                "fast immer zu spät."
            ),
            steps=(
                "Mit den Tanks feste Zeitpunkte vereinbaren.",
                "Vor dem angesagten Treffer setzen, nicht danach.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Disziplin",
            checks=(cooldown_check("Pain Suppression"),),
        ),
        Lesson(
            lesson_id="priest-discipline.rotation.atonement",
            title="Sühne-Heilung als Grundlast begreifen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Disziplinpriester heilt, indem er Schaden macht. "
                "Wer in ruhigen Phasen gar nichts tut, verschenkt die "
                "billigste Heilung, die er hat."
            ),
            steps=(
                "In ruhigen Phasen den Boss angreifen statt zu warten.",
                "Auf Reichweite zum Ziel achten.",
                "Die Aktivzeit nach dem Pull im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Disziplin",
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
        Lesson(
            lesson_id="priest-holy.rotation.prayer_of_mending",
            title="Gebet der Besserung nie liegen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Das Gebet springt weiter und heilt kostenlos - "
                "solange es unterwegs ist. Auf der Abklingzeit stehen "
                "zu lassen ist reine Verschwendung."
            ),
            steps=(
                "Bei jeder Verfügbarkeit neu setzen.",
                "Bevorzugt auf Ziele, die gleich Schaden bekommen.",
                "Vor der Schadensspitze bewusst auf den Tank legen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(hot_uptime_check("Prayer of Mending", 70.0),),
        ),
        Lesson(
            lesson_id="priest-holy.cooldowns.guardian_spirit",
            title="Schutzgeist als geplante Rettung",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Schutzgeist rettet einen Tank auch dann, wenn die "
                "Heilung zu spät kommt - vorausgesetzt, er steht vor "
                "dem Treffer."
            ),
            steps=(
                "Mit den Tanks feste Zeitpunkte vereinbaren.",
                "Vor der angesagten Mechanik setzen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Heilig",
            checks=(cooldown_check("Guardian Spirit"),),
        ),
        Lesson(
            lesson_id="priest-holy.mechanics.dispel",
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
            spec="Heilig",
            checks=(dispel_check(),),
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
            lesson_id="priest-shadow.rotation.orbs",
            title="Schattenkugeln nicht überlaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Drei Schattenkugeln sind das Maximum. Jede weitere "
                "verfällt - und mit ihr der stärkste Zauber der "
                "Spezialisierung."
            ),
            steps=(
                "Die Kugelanzeige deutlich einrichten.",
                "Bei drei Kugeln sofort ausgeben.",
                "Vor Phasenwechseln bewusst leeren.",
            ),
            class_name=CLASS_NAME,
            spec="Schatten",
        ),
        Lesson(
            lesson_id="priest-shadow.survival.dispersion",
            title="Zerstreuung als Minderung einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Zerstreuung ist die stärkste persönliche "
                "Minderung im Spiel - benutzt wird sie meist nur für "
                "Mana, und dann zufällig."
            ),
            steps=(
                "Die größten Treffer auf den eigenen Charakter "
                "benennen.",
                "Die Zerstreuung fest darauf legen.",
                "Nach dem Pull prüfen, ob sie genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            spec="Schatten",
            checks=(cooldown_check("Dispersion"),),
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
                "Mindestens drei Minuten am Stück üben - kürzere "
                "Sitzungen zählen nicht.",
                "An drei Tagen in Folge mit guter Note üben - "
                "hakt sich danach von selbst ab.",
            ),
            class_name=CLASS_NAME,
            spec="Schatten",
        ),
    ),

    "": (
        Lesson(
            lesson_id="priest.mechanics.mass_dispel",
            title="Massenbannung vorbereiten",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Massenbannung löst in mehreren Kämpfen eine "
                "ganze Mechanik auf einmal - sie will vorher geübt "
                "sein, weil sie am Boden platziert wird."
            ),
            steps=(
                "Vor dem Pull klären, ob der Kampf sie braucht.",
                "Die Fähigkeit auf eine erreichbare Taste legen.",
                "Auf die Ansage reagieren, nicht auf den Schaden.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="priest.mechanics.leap_of_faith",
            title="Vertrauenssprung als Rettungsseil nutzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Vertrauenssprung zieht einen Mitspieler aus einer "
                "Mechanik heraus, die er selbst nicht mehr verlassen "
                "kann. Er wird fast nie benutzt."
            ),
            steps=(
                "Die Mechaniken benennen, bei denen jemand hängen "
                "bleibt.",
                "Die Fähigkeit auf eine erreichbare Taste legen.",
                "Im Voraus ansagen, wen man zieht.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="priest.survival.own_defensives",
            title="Die eigenen Minderungen zuteilen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Priester ist die zerbrechlichste Klasse im Raid "
                "und hat trotzdem in jeder Spezialisierung eine "
                "persönliche Minderung. Aufgespart wird sie fast nie "
                "benutzt."
            ),
            steps=(
                "Die eigenen Minderungen mit Dauer und Abklingzeit "
                "auflisten.",
                "Jeder eine feste Bossmechanik zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            class_name=CLASS_NAME,
            checks=(defensive_check(),),
        ),
    ),

}
