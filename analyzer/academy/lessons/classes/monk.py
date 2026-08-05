"""Lektionen für Mönche."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    buff_uptime_check,
    cooldown_check,
    defensive_check,
    dispel_check,
    hot_uptime_check,
    interrupt_check,
)

CLASS_NAME = "Monk"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Braumeister": (
        Lesson(
            lesson_id="monk-brewmaster.survival.stagger",
            title="Benommenheit aktiv abbauen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Benommenheit verteilt Schaden über Zeit. Wer sie "
                "nicht abbaut, stirbt an der Summe statt am Treffer."
            ),
            steps=(
                "Die Benommenheitsstufe im Blick behalten.",
                "Ab der mittleren Stufe abbauen.",
                "Im Log prüfen, wie oft die hohe Stufe erreicht wurde.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
        ),
        Lesson(
            lesson_id="monk-brewmaster.survival.guard",
            title="Wache regelmäßig einsetzen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Wache hat eine kurze Abklingzeit und passt vielfach "
                "in jeden Kampf - aufzusparen kostet Einsätze."
            ),
            steps=(
                "Wache an den Angriffsrhythmus des Bosses koppeln.",
                "Nicht auf den Notfall warten.",
                "Im Log die Zahl der Einsätze prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
            checks=(cooldown_check("Guard"),),
        ),
        Lesson(
            lesson_id="monk-brewmaster.rotation.shuffle",
            title="Mischen ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Mischen erhöht den Anteil des Schadens, der in die "
                "Benommenheit wandert. Ohne Mischen trifft der Boss "
                "sofort statt über Zeit - das ist der Unterschied "
                "zwischen zwei Sekunden Reaktionszeit und keiner."
            ),
            steps=(
                "Mischen als oberste Priorität der Rotation behandeln.",
                "Chi dafür reservieren, nicht für Schaden ausgeben.",
                "Die Abdeckung im Log prüfen, nicht nach Gefühl gehen.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
            checks=(buff_uptime_check("Shuffle", 90.0),),
        ),
        Lesson(
            lesson_id="monk-brewmaster.cooldowns.fortifying_brew",
            title="Stärkendes Gebräu und Zen-Meditation trennen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Gebräu wirkt gegen alles, die Meditation gegen "
                "Magie. Gleichzeitig gezündet decken sie ein Fenster "
                "ab, nacheinander zwei."
            ),
            steps=(
                "Beide je einer festen Bossmechanik zuordnen.",
                "Die Meditation nur dort, wo nicht geschlagen wird.",
                "Im Log auf Überschneidungen prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
            checks=(cooldown_check("Fortifying Brew"),),
        ),
        Lesson(
            lesson_id="monk-brewmaster.mechanics.taunt",
            title="Tankwechsel mit dem Mittank abstimmen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Braumeister nimmt Schaden verzögert - genau "
                "deshalb ist der falsche Wechselzeitpunkt bei ihm "
                "besonders gefährlich: die Benommenheit läuft weiter."
            ),
            steps=(
                "Vor dem Wechsel die Benommenheit abbauen.",
                "Den Auslöser des Wechsels vorher benennen.",
                "Nach dem Spott Mischen sofort wieder aufbauen.",
            ),
            class_name=CLASS_NAME,
            spec="Braumeister",
        ),
    ),

    "Nebelwirker": (
        Lesson(
            lesson_id="monk-mistweaver.rotation.renewing_mist",
            title="Erneuernder Nebel dauerhaft im Umlauf",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Nebel springt weiter und erzeugt die Ressource "
                "der Spezialisierung. Er darf nie stillstehen."
            ),
            steps=(
                "Bei jeder Verfügbarkeit neu setzen.",
                "Bevorzugt auf Ziele in der Nähe anderer.",
                "Im Log die Uptime auf dem Raid prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(hot_uptime_check("Renewing Mist", 80.0),),
        ),
        Lesson(
            lesson_id="monk-mistweaver.cooldowns.revival",
            title="Erweckung an der Spitze setzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Erweckung heilt raidweit und entfernt Effekte - beide "
                "Wirkungen wollen den richtigen Moment."
            ),
            steps=(
                "Den Zeitpunkt mit den Heilern abstimmen.",
                "Bevorzugt nutzen, wenn zusätzlich Effekte anliegen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(cooldown_check("Revival"),),
        ),
        Lesson(
            lesson_id="monk-mistweaver.rotation.mana",
            title="Manatee bewusst einplanen",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Nebelwirker sammelt seine Manarückgewinnung "
                "selbst an. Wer sie nie trinkt, heilt die zweite "
                "Kampfhälfte mit halber Kraft."
            ),
            steps=(
                "Die Stapel im Blick behalten, nicht erst das Mana.",
                "Feste ruhige Momente zum Trinken einplanen.",
                "Nicht in der Schadensspitze trinken.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
        ),
        Lesson(
            lesson_id="monk-mistweaver.cooldowns.life_cocoon",
            title="Lebenskokon vor dem Treffer setzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Kokon ist ein Schild und keine Heilung - nach dem "
                "Treffer gesetzt rettet er niemanden mehr."
            ),
            steps=(
                "Mit der Raidleitung ein festes Ziel vereinbaren.",
                "Ihn vor der angesagten Mechanik setzen.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(cooldown_check("Life Cocoon"),),
        ),
        Lesson(
            lesson_id="monk-mistweaver.mechanics.detox",
            title="Entgiften fest übernehmen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Ein entfernter Effekt spart mehr Heilung, als jede "
                "Heilung ihn ausgleichen könnte."
            ),
            steps=(
                "Die entfernbaren Effekte des Bosses auflisten.",
                "Klären, wer welchen entfernt.",
                "Das Entgiften auf eine erreichbare Taste legen.",
            ),
            class_name=CLASS_NAME,
            spec="Nebelwirker",
            checks=(dispel_check(),),
        ),
    ),

    "Windwandler": (
        Lesson(
            lesson_id="monk-windwalker.rotation.tiger_power",
            title="Tigerkraft nicht auslaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Tigerkraft senkt die Rüstung des Ziels und wirkt auf "
                "jeden folgenden Treffer."
            ),
            steps=(
                "Die Anzeige deutlich einrichten.",
                "Vor Ablauf erneuern, nicht danach.",
                "Nach Bewegungsphasen zuerst nachsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
        ),
        Lesson(
            lesson_id="monk-windwalker.cooldowns.tigereye_brew",
            title="Tigeraugengebräu gesammelt ausgeben",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Gebräu wirkt umso stärker, je mehr Stapel es "
                "hat - einzeln getrunken verschenkt es genau diesen "
                "Vorteil."
            ),
            steps=(
                "Bis zu einer festen Stapelzahl sammeln.",
                "Erst dann und möglichst im Heldentum trinken.",
                "Vor Kampfende nichts übrig lassen.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
            checks=(cooldown_check("Tigereye Brew"),),
        ),
        Lesson(
            lesson_id="monk-windwalker.survival.defensives",
            title="Die eigenen Minderungen einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Windwandler bringt gleich mehrere persönliche "
                "Minderungen mit und benutzt in der Praxis meist "
                "keine davon."
            ),
            steps=(
                "Die eigenen Minderungen mit Dauer und Abklingzeit "
                "auflisten.",
                "Jeder eine feste Bossmechanik zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
            checks=(defensive_check(),),
        ),
        Lesson(
            lesson_id="monk-windwalker.rotation.dummy_practice",
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
            spec="Windwandler",
        ),
        Lesson(
            lesson_id="monk-windwalker.mechanics.ring_of_peace",
            title="Nutzfähigkeiten des Mönchs einsetzen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Mönch bringt Unterbrechung, Betäubung und "
                "Verlangsamung mit - alle drei werden regelmäßig "
                "vergessen."
            ),
            steps=(
                "Die eigenen Nutzfähigkeiten auflisten.",
                "Jeder eine Kampfsituation zuordnen.",
                "Nach dem Pull prüfen, ob sie genutzt wurden.",
            ),
            class_name=CLASS_NAME,
            spec="Windwandler",
        ),
    ),

    "": (
        Lesson(
            lesson_id="monk.mechanics.spear_hand_strike",
            title="Speerhandstoß fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Jede Spezialisierung des Mönchs hat eine "
                "Unterbrechung mit kurzer Abklingzeit. Vergessen wird "
                "sie, weil niemand zugeteilt war."
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
            lesson_id="monk.survival.diffuse_magic",
            title="Gegen Magieschaden vorbereitet sein",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Mönch hat für Magieschaden eine eigene Antwort. "
                "Sie hilft nur, wenn sie vor dem Zauber steht - danach "
                "ist sie eine verschenkte Abklingzeit."
            ),
            steps=(
                "Die magischen Angriffe des Bosses auflisten.",
                "Die passende Fähigkeit fest darauf legen.",
                "Auf die Ansage reagieren, nicht auf den Treffer.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
