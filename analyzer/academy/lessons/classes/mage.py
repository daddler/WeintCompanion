"""Lektionen für Magier."""

from analyzer.academy.lessons.classes._common import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    Lesson,
    cooldown_check,
    interrupt_check,
)

CLASS_NAME = "Mage"

SPEC_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Feuer": (
        Lesson(
            lesson_id="mage-fire.cooldowns.combustion",
            title="Verbrennung erst bei starkem Zündschaden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Verbrennung kopiert den laufenden Zündschaden. Zu "
                "früh gezündet halbiert sie ihren eigenen Wert."
            ),
            steps=(
                "Den aktuellen Zündschaden im Blick behalten.",
                "Erst nach einem kritischen Treffer zünden.",
                "Vorher alle Verstärkungen aktivieren.",
            ),
            class_name=CLASS_NAME,
            spec="Feuer",
            checks=(cooldown_check("Combustion"),),
        ),
        Lesson(
            lesson_id="mage-fire.rotation.heating_up",
            title="Aufwärmen sauber in Hitzewallung umsetzen",
            category=CATEGORY_ROTATION,
            summary=(
                "Ein verlorener Aufwärmen-Effekt ist ein verlorener "
                "kostenloser Feuerschlag."
            ),
            steps=(
                "Die Anzeige für beide Effekte deutlich einrichten.",
                "Bei Hitzewallung sofort den Feuerschlag setzen.",
                "Bei Aufwärmen zuerst einen Zauber mit Kritchance.",
            ),
            class_name=CLASS_NAME,
            spec="Feuer",
        ),
        Lesson(
            lesson_id="mage-fire.movement.scorch",
            title="Beim Laufen weiterzaubern",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Feuermagier hat einen Zauber, den er in Bewegung "
                "wirken kann. Wer stattdessen wartet, verliert die "
                "gesamte Laufzeit."
            ),
            steps=(
                "Die Bewegungsphasen des Kampfes vorher benennen.",
                "In Bewegung durchgehend weiterzaubern.",
                "Die Aktivzeit nach dem Pull im Log prüfen.",
            ),
            class_name=CLASS_NAME,
            spec="Feuer",
        ),
        Lesson(
            lesson_id="mage-fire.rotation.dummy_practice",
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
            spec="Feuer",
        ),
    ),

    "Arkan": (
        Lesson(
            lesson_id="mage-arcane.rotation.burn_conserve",
            title="Brenn- und Sparphase klar trennen",
            category=CATEGORY_ROTATION,
            summary=(
                "Arkan lebt vom Wechsel zwischen Verbrennen und "
                "Sparen. Wer dazwischen hängt, verliert in beidem."
            ),
            steps=(
                "Eine feste Manaschwelle für den Phasenwechsel "
                "festlegen.",
                "In der Brennphase keine Sparzauber mehr wirken.",
                "Die Brennphase auf Heldentum legen.",
            ),
            class_name=CLASS_NAME,
            spec="Arkan",
        ),
        Lesson(
            lesson_id="mage-arcane.cooldowns.arcane_power",
            title="Arkane Macht mit der Brennphase koppeln",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Arkane Macht außerhalb der Brennphase verschenkt den "
                "größten Teil ihrer Wirkung."
            ),
            steps=(
                "Arkane Macht nie einzeln zünden.",
                "Zusammen mit vollen Arkanen Aufladungen auslösen.",
                "Im Log prüfen, wie viele Einsätze im Heldentum lagen.",
            ),
            class_name=CLASS_NAME,
            spec="Arkan",
            checks=(cooldown_check("Arcane Power"),),
        ),
        Lesson(
            lesson_id="mage-arcane.cooldowns.evocation",
            title="Hervorrufung als Teil der Rotation begreifen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Hervorrufung ist beim Arkanmagier kein Notnagel, "
                "sondern der geplante Übergang zurück in die "
                "Brennphase."
            ),
            steps=(
                "Eine feste Manaschwelle für die Hervorrufung "
                "festlegen.",
                "Sie in einer ruhigen Phase einplanen, nicht in der "
                "Mechanik.",
                "Danach sofort wieder in die Brennphase gehen.",
            ),
            class_name=CLASS_NAME,
            spec="Arkan",
            checks=(cooldown_check("Evocation"),),
        ),
        Lesson(
            lesson_id="mage-arcane.rotation.dummy_practice",
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
            spec="Arkan",
        ),
    ),

    "Frost": (
        Lesson(
            lesson_id="mage-frost.rotation.procs",
            title="Frostblitz-Effekte sofort verwerten",
            category=CATEGORY_ROTATION,
            summary=(
                "Frost lebt von Zufallseffekten. Ein verfallener "
                "Effekt ist unwiederbringlich."
            ),
            steps=(
                "Die Effektanzeigen deutlich sichtbar einrichten.",
                "Effekte immer vor dem Fülzauber verwerten.",
                "Nie zwei Effekte gleichzeitig anstehen lassen.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
        Lesson(
            lesson_id="mage-frost.movement.blink",
            title="Blinzeln als Werkzeug, nicht als Notausgang",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Blinzeln spart mehr Zeit, wenn es geplant ist, als "
                "wenn es die Rettung sein muss."
            ),
            steps=(
                "Die weiten Wege des Kampfes vorher benennen.",
                "Blinzeln fest dafür einplanen.",
                "Für echte Notfälle einen zweiten Ausweg behalten.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
        ),
        Lesson(
            lesson_id="mage-frost.cooldowns.icy_veins",
            title="Eisige Adern regelmäßig zünden",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Eisige Adern haben eine kurze Abklingzeit und passen "
                "mehrfach in jeden Kampf - aufzusparen kostet ganze "
                "Einsätze."
            ),
            steps=(
                "Den ersten Einsatz an den Kampfbeginn koppeln.",
                "Danach bei jeder Verfügbarkeit erneut.",
                "Nur kurz für das Heldentum zurückhalten.",
            ),
            class_name=CLASS_NAME,
            spec="Frost",
            checks=(cooldown_check("Icy Veins"),),
        ),
        Lesson(
            lesson_id="mage-frost.rotation.dummy_practice",
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

    "": (
        Lesson(
            lesson_id="mage.mechanics.counterspell",
            title="Gegenzauber fest zuteilen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Gegenzauber ist die einzige Unterbrechung des "
                "Magiers und hat eine lange Abklingzeit - umso mehr "
                "gehört er in eine abgesprochene Reihenfolge."
            ),
            steps=(
                "Vor dem Pull eine feste Unterbrecherreihenfolge "
                "vereinbaren.",
                "Den Gegenzauber auf eine erreichbare Taste legen.",
                "Nach dem Pull prüfen, ob eine Unterbrechung fehlte.",
            ),
            class_name=CLASS_NAME,
            checks=(interrupt_check(),),
        ),
        Lesson(
            lesson_id="mage.survival.ice_block",
            title="Eisblock gegen ganze Mechaniken einsetzen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Eisblock hebt Schaden und Effekte vollständig "
                "auf. In mehreren Kämpfen ist er die sauberste Antwort "
                "auf eine Mechanik - benutzt wird er meist erst in "
                "der Panik."
            ),
            steps=(
                "Die Mechaniken benennen, die er aufhebt.",
                "Den Block fest darauf legen.",
                "Nach dem Pull prüfen, ob er genutzt wurde.",
            ),
            class_name=CLASS_NAME,
            checks=(cooldown_check("Ice Block"),),
        ),
        Lesson(
            lesson_id="mage.cooldowns.time_warp",
            title="Zeitkrümmung absprechen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Die Zeitkrümmung ist der einzige Cooldown, an dem "
                "sich der halbe Raid ausrichtet. Spontan gezündet "
                "trifft sie genau niemandes Plan."
            ),
            steps=(
                "Vor dem Pull den Zeitpunkt mit der Raidleitung "
                "festlegen.",
                "Ihn im Kampf laut ansagen, bevor er kommt.",
                "Klären, wer ihn stellt, wenn mehrere ihn haben.",
            ),
            class_name=CLASS_NAME,
        ),
    ),

}
