"""Lektionen für Schamanen."""

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
    interrupt_check,
    uptime_check,
)

CLASS_NAME = "Shaman"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Wiederherstellung": (
        Lesson(
            lesson_id="shaman-resto.rotation.riptide",
            title="Springflut als Grundlage nutzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Springflut ist die günstigste Heilung der "
                "Spezialisierung und verstärkt die Kettenheilung."
            ),
            steps=(
                "Springflut bei jeder Verfügbarkeit setzen.",
                "Bevorzugt auf Ziele, die gleich Schaden bekommen.",
                "Vor der Kettenheilung auf das Startziel legen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Riptide", 80.0),),
        ),
        Lesson(
            lesson_id="shaman-resto.rotation.earth_shield",
            title="Erdschild auf dem Tank halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Erdschild kostet einmal Zeit und heilt danach den "
                "ganzen Kampf über von selbst."
            ),
            steps=(
                "Vor dem Pull auf dem aktiven Tank setzen.",
                "Die verbleibenden Ladungen im Blick behalten.",
                "Beim Tankwechsel umsetzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(hot_uptime_check("Earth Shield", 95.0),),
        ),
        Lesson(
            lesson_id="shaman-resto.cooldowns.healing_tide",
            title="Flut der Heilung an der Spitze setzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Flut wirkt raidweit und gehört auf die planbar "
                "größte Schadensspitze, nicht in die Panik."
            ),
            steps=(
                "Den Zeitpunkt mit den anderen Heilern absprechen.",
                "Das Totem in Reichweite des Raids stellen.",
                "Bei jeder Verfügbarkeit erneut nutzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(cooldown_check("Healing Tide Totem"),),
        ),
        Lesson(
            lesson_id="shaman-resto.cooldowns.spirit_link",
            title="Totem der Geisterverbindung an die Spitze legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Totem verteilt Leben um und mindert Schaden - es "
                "rettet dort, wo Heilung zu langsam wäre, aber nur "
                "innerhalb seines Radius."
            ),
            steps=(
                "Den Zeitpunkt mit der Raidleitung vereinbaren.",
                "Das Totem dorthin stellen, wo der Raid steht.",
                "Bei jeder Verfügbarkeit erneut einplanen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
            checks=(cooldown_check("Spirit Link Totem"),),
        ),
        Lesson(
            lesson_id="shaman-resto.mechanics.purify",
            title="Geist reinigen fest übernehmen",
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
            lesson_id="shaman-resto.rotation.healing_rain",
            title="Heilenden Regen dorthin legen, wo gestanden wird",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Regen ist die günstigste Flächenheilung der "
                "Spezialisierung - und die am häufigsten falsch "
                "platzierte."
            ),
            steps=(
                "Vor der Mechanik wissen, wo der Raid stehen wird.",
                "Den Regen dorthin legen, nicht dorthin, wo er steht.",
                "Nach jedem Positionswechsel neu setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Wiederherstellung",
        ),
    ),

    "Elementar": (
        Lesson(
            lesson_id="shaman-elemental.rotation.flame_shock",
            title="Flammenschock ohne Lücke halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Flammenschock ermöglicht den Lavastoß - ohne ihn "
                "fehlt der stärkste Zauber der Rotation."
            ),
            steps=(
                "Flammenschock dauerhaft auf dem Ziel halten.",
                "Mit dem Lavastoß verlängern statt neu zu wirken.",
                "Beim Zielwechsel zuerst auftragen.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
            checks=(uptime_check("Flame Shock", 92.0),),
        ),
        Lesson(
            lesson_id="shaman-elemental.cooldowns.elemental_mastery",
            title="Elementarbeherrschung regelmäßig zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Mit anderthalb Minuten Abklingzeit passt sie mehrfach "
                "in jeden Kampf. Aufsparen kostet Einsätze."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nur für Heldentum kurz aufsparen.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
            checks=(cooldown_check("Elemental Mastery"),),
        ),
        Lesson(
            lesson_id="shaman-elemental.rotation.lava_burst",
            title="Lavaeruption nie auf der Abklingzeit stehen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Die Lavaeruption trifft garantiert kritisch und ist "
                "damit der stärkste Zauber der Spezialisierung. Jede "
                "Sekunde, die sie bereit steht, ist verlorener "
                "Schaden."
            ),
            steps=(
                "Die Abklingzeit deutlich anzeigen lassen.",
                "Sie sofort bei Verfügbarkeit setzen.",
                "Vorher prüfen, ob der Flammenschock noch läuft.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
        ),
        Lesson(
            lesson_id="shaman-elemental.cooldowns.fire_elemental",
            title="Feuerelementar früh und geplant rufen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Elementar läuft mehrere Minuten und macht "
                "unabhängig von der eigenen Rotation Schaden - "
                "aufgespart bringt es gar nichts."
            ),
            steps=(
                "Den ersten Ruf an den Kampfbeginn koppeln.",
                "Den zweiten auf das Heldentum planen.",
                "Nicht kurz vor einem Phasenwechsel rufen.",
            ),
            class_name=CLASS_NAME,
            spec="Elementar",
            checks=(cooldown_check("Fire Elemental Totem"),),
        ),
        Lesson(
            lesson_id="shaman-elemental.rotation.dummy_practice",
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
            spec="Elementar",
        ),
    ),

    "Verstärkung": (
        Lesson(
            lesson_id="shaman-enhancement.rotation.maelstrom",
            title="Mahlstrom nicht überlaufen lassen",
            category=CATEGORY_ROTATION,
            summary=(
                "Fünf Stapel Mahlstrom sind ein kostenloser Blitzschlag. "
                "Wer wartet, verliert Stapel."
            ),
            steps=(
                "Die Stapelanzeige deutlich einrichten.",
                "Bei fünf Stapeln sofort ausgeben.",
                "In Bewegungsphasen bewusst darauf sparen.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
        ),
        Lesson(
            lesson_id="shaman-enhancement.cooldowns.feral_spirit",
            title="Wilder Geist bei jeder Verfügbarkeit",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Wölfe laufen unabhängig von der eigenen Rotation "
                "und kosten nichts außer dem Tastendruck."
            ),
            steps=(
                "Direkt beim Pull rufen.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nicht auf sterbende Ziele setzen.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
            checks=(cooldown_check("Feral Spirit"),),
        ),
        Lesson(
            lesson_id="shaman-enhancement.rotation.unleash",
            title="Elemente entfesseln in den Ablauf einbauen",
            category=CATEGORY_ROTATION,
            summary=(
                "Entfesseln verstärkt den nächsten Zauber und steht "
                "fast durchgehend bereit - es fällt trotzdem als "
                "Erstes aus der Rotation."
            ),
            steps=(
                "Die Abklingzeit deutlich anzeigen lassen.",
                "Direkt vor dem verstärkten Zauber einsetzen.",
                "Nach Bewegungsphasen zuerst nachholen.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
        ),
        Lesson(
            lesson_id="shaman-enhancement.cooldowns.fire_elemental",
            title="Feuerelementar auch als Verstärker rufen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Elementar gehört auch beim Verstärker zum "
                "Schaden - vergessen wird es, weil es nicht in der "
                "Prioritätenliste steht."
            ),
            steps=(
                "Den ersten Ruf an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Mit den eigenen Verstärkungen bündeln.",
            ),
            class_name=CLASS_NAME,
            spec="Verstärkung",
            checks=(cooldown_check("Fire Elemental Totem"),),
        ),
        Lesson(
            lesson_id="shaman-enhancement.rotation.dummy_practice",
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
            spec="Verstärkung",
        ),
    ),

    "": (
        Lesson(
            lesson_id="shaman.mechanics.totems",
            title="Totems zur Kampfsituation wählen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Totems sind der wandelbarste Beitrag der Klasse - "
                "und der am häufigsten vergessene."
            ),
            steps=(
                "Vor dem Pull die vier Totems bewusst wählen.",
                "Beim Phasenwechsel prüfen, ob sie noch passen.",
                "Auf Reichweite achten - Totems haben Radius.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="shaman.mechanics.wind_shear",
            title="Windstoß fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Windstoß hat die kürzeste Abklingzeit aller "
                "Unterbrechungen im Spiel. Der Schamane sollte damit "
                "in jeder Unterbrecherreihenfolge ganz vorne stehen."
            ),
            steps=(
                "Vor dem Pull eine feste Unterbrecherreihenfolge "
                "vereinbaren.",
                "Den Windstoß auf eine gut erreichbare Taste legen.",
                "Nach dem Pull prüfen, ob eine Unterbrechung fehlte.",
            ),
            class_name=CLASS_NAME,
            checks=(interrupt_check(),),
        ),
        Lesson(
            lesson_id="shaman.cooldowns.heroism",
            title="Heldentum absprechen statt spontan zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Heldentum ist der einzige Cooldown, an dem sich "
                "der halbe Raid ausrichtet. Spontan gezündet trifft er "
                "genau niemandes Plan."
            ),
            steps=(
                "Vor dem Pull den Zeitpunkt mit der Raidleitung "
                "festlegen.",
                "Ihn im Kampf laut ansagen, bevor er kommt.",
                "Bei mehreren Schamanen die Reihenfolge klären.",
            ),
            class_name=CLASS_NAME,
        ),
        Lesson(
            lesson_id="shaman.survival.astral_shift",
            title="Astrale Verschiebung einplanen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die persönliche Minderung des Schamanen steht "
                "regelmäßig bereit und wird fast nie benutzt."
            ),
            steps=(
                "Die wiederkehrenden Treffer auf den eigenen "
                "Charakter benennen.",
                "Die Minderung fest darauf legen.",
                "Nach dem Pull prüfen, ob sie genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            checks=(defensive_check(),),
        ),
    ),

}
