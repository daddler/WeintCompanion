"""
Lektionskatalog der WeintAcademy.

Der Katalog ist zweistufig aufgebaut:

* **Spezialisierungs-Lektionen** - konkrete Inhalte für eine
  bestimmte Klasse/Spezialisierung aus Mists of Pandaria.
* **Allgemeine Lektionen** - gelten für jede Klasse.

Dadurch bekommt jeder Spieler einen sinnvollen Trainingsplan, auch
wenn für seine Spezialisierung noch keine eigenen Inhalte
hinterlegt sind: die allgemeinen Lektionen füllen immer auf.

Die Spezialisierungsnamen entsprechen den deutschen Bezeichnungen,
wie sie auch im Roster verwendet werden ("Gleichgewicht",
"Disziplin", ...).
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    Lesson,
)
from analyzer.models import Actor


#
# --------------------------------------------------
# Allgemeine Lektionen
# --------------------------------------------------
#

GENERIC_LESSONS: tuple[Lesson, ...] = (

    Lesson(
        lesson_id="generic.rotation.uptime",
        title="Uptime am Ziel halten",
        category=CATEGORY_ROTATION,
        summary=(
            "Jede Sekunde ohne Angriff kostet Schaden. Ziel ist eine "
            "Aktivitätszeit von über 95 Prozent im Kampf."
        ),
        steps=(
            "Im Log die Lücken zwischen zwei Fähigkeiten suchen.",
            "Die drei längsten Lücken einer Ursache zuordnen: "
            "Bewegung, Ressourcenmangel oder Reaktionszeit.",
            "Für jede Ursache eine Gegenmaßnahme festlegen.",
        ),
    ),

    Lesson(
        lesson_id="generic.rotation.resources",
        title="Ressourcen nicht überlaufen lassen",
        category=CATEGORY_ROTATION,
        summary=(
            "Volle Energie, volles Runenmal oder volle Combopunkte "
            "sind verschenkter Schaden."
        ),
        steps=(
            "Den Ressourcenverlauf über einen ganzen Pull ansehen.",
            "Zeitpunkte markieren, an denen das Maximum erreicht wurde.",
            "Den Ausgeber vorziehen, bevor das Maximum erreicht wird.",
        ),
    ),

    Lesson(
        lesson_id="generic.movement.instants",
        title="Bewegung mit Instants überbrücken",
        category=CATEGORY_MOVEMENT,
        summary=(
            "Bewegung muss keinen Schadensverlust bedeuten - sie muss "
            "nur geplant sein."
        ),
        steps=(
            "Die eigenen Fähigkeiten ohne Zauberzeit auflisten.",
            "Sie bewusst für angekündigte Bewegungsphasen aufsparen.",
            "Lange Zauber vor einer Bewegungsphase nicht mehr anfangen.",
        ),
    ),

    Lesson(
        lesson_id="generic.movement.preposition",
        title="Vorpositionieren statt nachlaufen",
        category=CATEGORY_MOVEMENT,
        summary=(
            "Wer sich vor der Mechanik bewegt, verliert keine Zeit - "
            "wer danach reagiert, verliert immer."
        ),
        steps=(
            "Die wiederkehrenden Mechaniken des Bosses notieren.",
            "Für jede einen festen Zielpunkt im Raum bestimmen.",
            "Den Weg dorthin schon vor der Ankündigung antreten.",
        ),
    ),

    Lesson(
        lesson_id="generic.cooldowns.early",
        title="Cooldowns früh und oft einsetzen",
        category=CATEGORY_COOLDOWNS,
        summary=(
            "Ein Cooldown, der am Ende des Kampfes noch bereit ist, "
            "war ein verschenkter Cooldown."
        ),
        steps=(
            "Kampfdauer durch die Abklingzeit teilen - das ist die "
            "Zahl der möglichen Einsätze.",
            "Die tatsächlichen Einsätze im Log dagegenhalten.",
            "Feste Einsatzzeitpunkte für den nächsten Pull festlegen.",
        ),
    ),

    Lesson(
        lesson_id="generic.cooldowns.potion",
        title="Potion-Timing",
        category=CATEGORY_COOLDOWNS,
        summary=(
            "Zwei Kampftränke pro Kampf sind möglich: einer vor dem "
            "Pull, einer zusammen mit den großen Cooldowns."
        ),
        steps=(
            "Den Vorkampf-Trank zwei Sekunden vor dem Pull trinken.",
            "Den zweiten Trank mit Heldentum bündeln.",
            "Im Log prüfen, dass beide Tränke wirklich gewirkt haben.",
        ),
    ),

    Lesson(
        lesson_id="generic.mechanics.interrupts",
        title="Unterbrechungsreihenfolge absprechen",
        category=CATEGORY_MECHANICS,
        summary=(
            "Eine verpasste Unterbrechung ist fast immer ein "
            "Absprachefehler, kein Reaktionsfehler."
        ),
        steps=(
            "Eine feste Reihenfolge im Raid festlegen.",
            "Die eigene Position in der Reihenfolge kennen.",
            "Nach dem Pull prüfen, welche Zauber durchkamen.",
        ),
    ),

    Lesson(
        lesson_id="generic.mechanics.defensives",
        title="Defensives gegen angekündigten Schaden",
        category=CATEGORY_MECHANICS,
        summary=(
            "Für jeden planbaren Schadensmoment sollte eine "
            "Verteidigungsfähigkeit fest eingeplant sein."
        ),
        steps=(
            "Die planbaren Schadensspitzen des Bosses auflisten.",
            "Jeder Spitze eine eigene Defensivfähigkeit zuordnen.",
            "Die Zuordnung als feste Gewohnheit einüben.",
        ),
    ),

)


#
# --------------------------------------------------
# Lektionen je Spezialisierung
# --------------------------------------------------
#
# Schlüssel: (Klasse, Spezialisierung)
#

SPEC_LESSONS: dict[tuple[str, str], tuple[Lesson, ...]] = {

    ("Druid", "Gleichgewicht"): (

        Lesson(
            lesson_id="druid.balance.celestial_alignment",
            title="Celestial Alignment optimieren",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Celestial Alignment friert den Eclipse-Zustand ein - "
                "der Einsatzzeitpunkt entscheidet über den Gewinn."
            ),
            steps=(
                "Celestial Alignment am Rand einer Eclipse zünden, "
                "nicht mittendrin.",
                "Vorher beide Punkteffekte frisch auftragen.",
                "Mit Trank und Schmuckstück-Procs bündeln.",
            ),
            class_name="Druid",
            spec="Gleichgewicht",
        ),

        Lesson(
            lesson_id="druid.balance.moonfire",
            title="Moonfire-Uptime halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Moonfire und Sunfire sollten über den ganzen Kampf "
                "nahezu lückenlos stehen."
            ),
            steps=(
                "Die Uptime beider Effekte im Log ablesen.",
                "Verlängerungen im passenden Eclipse-Zustand auffrischen.",
                "Auf unter 95 Prozent Uptime mit einer festen "
                "Auffrischroutine reagieren.",
            ),
            class_name="Druid",
            spec="Gleichgewicht",
        ),

        Lesson(
            lesson_id="druid.balance.eclipse",
            title="Eclipse-Zyklus sauber fahren",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Wechsel zwischen Sonne und Mond bestimmt den "
                "gesamten Schadensausstoß."
            ),
            steps=(
                "Den Zeitpunkt des Wechsels vorausplanen.",
                "Starsurge nicht überlaufen lassen.",
                "Bewegungsphasen in den Wechsel legen.",
            ),
            class_name="Druid",
            spec="Gleichgewicht",
        ),

    ),

    ("Mage", "Feuer"): (

        Lesson(
            lesson_id="mage.fire.combustion",
            title="Combustion vorbereiten",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Combustion überträgt die laufenden Brandeffekte - "
                "sie ist nur so stark wie der Moment davor."
            ),
            steps=(
                "Vor Combustion einen kritischen Pyroblast landen.",
                "Erst danach Combustion einsetzen.",
                "Den Einsatz mit Alter Time und Trank verbinden.",
            ),
            class_name="Mage",
            spec="Feuer",
        ),

        Lesson(
            lesson_id="mage.fire.heating_up",
            title="Heating Up sauber verwerten",
            category=CATEGORY_ROTATION,
            summary=(
                "Ein verfallener Pyroblast-Proc ist der teuerste "
                "Fehler dieser Spezialisierung."
            ),
            steps=(
                "Auf den Proc mit einer Anzeige aufmerksam machen.",
                "Den Proc sofort verwerten, nicht aufsparen.",
                "Bei Bewegung den Proc als Instant nutzen.",
            ),
            class_name="Mage",
            spec="Feuer",
        ),

    ),

    ("Warlock", "Gebrechen"): (

        Lesson(
            lesson_id="warlock.affliction.dots",
            title="Punkteffekte unter Procs auffrischen",
            category=CATEGORY_ROTATION,
            summary=(
                "Gebrechen lebt davon, die Effekte im richtigen "
                "Moment zu erneuern - nicht möglichst oft."
            ),
            steps=(
                "Nur bei aktivem Proc auffrischen.",
                "Die verbleibende Laufzeit vor jedem Auffrischen prüfen.",
                "Pandemic-Fenster ausnutzen statt zu früh zu erneuern.",
            ),
            class_name="Warlock",
            spec="Gebrechen",
        ),

    ),

    ("Priest", "Disziplin"): (

        Lesson(
            lesson_id="priest.discipline.spirit_shell",
            title="Spirit Shell auf Schadensspitzen legen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Spirit Shell wandelt Heilung in Schilde um - der "
                "Nutzen entsteht nur vor dem Schaden, nicht danach."
            ),
            steps=(
                "Die planbaren Schadensspitzen des Bosses notieren.",
                "Spirit Shell rund acht Sekunden vorher starten.",
                "Während des Fensters auf Gruppenheilung wechseln.",
            ),
            class_name="Priest",
            spec="Disziplin",
        ),

    ),

    ("Shaman", "Wiederherstellung"): (

        Lesson(
            lesson_id="shaman.resto.riptide",
            title="Riptide als Grundlage halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Riptide ist die Voraussetzung für effiziente "
                "Kettenheilung - nicht nur eine Einzelheilung."
            ),
            steps=(
                "Riptide durchgehend auf Tanks halten.",
                "Chain Heal auf ein Ziel mit Riptide starten.",
                "Die Abklingzeit nicht ungenutzt verstreichen lassen.",
            ),
            class_name="Shaman",
            spec="Wiederherstellung",
        ),

        Lesson(
            lesson_id="shaman.resto.healing_tide",
            title="Healing Tide Totem als Raid-Cooldown",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Das Totem ist ein Raid-Cooldown und gehört in die "
                "Absprache der Raidleitung."
            ),
            steps=(
                "Feste Einsatzzeitpunkte mit den anderen Heilern absprechen.",
                "Das Totem in Reichweite der Gruppe stellen.",
                "Nach dem Pull den überlappenden Einsatz prüfen.",
            ),
            class_name="Shaman",
            spec="Wiederherstellung",
        ),

    ),

    ("Warrior", "Schutz"): (

        Lesson(
            lesson_id="warrior.protection.mitigation",
            title="Aktive Schadensminderung ohne Lücke",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Shield Block und Shield Barrier sollen den ganzen "
                "Kampf über abwechselnd laufen."
            ),
            steps=(
                "Wut nicht für Angriffe verbrauchen, wenn Schaden ansteht.",
                "Shield Block gegen viele kleine Treffer einsetzen.",
                "Shield Barrier gegen einzelne große Treffer einsetzen.",
            ),
            class_name="Warrior",
            spec="Schutz",
        ),

    ),

    ("Monk", "Braumeister"): (

        Lesson(
            lesson_id="monk.brewmaster.stagger",
            title="Stagger mit Purifying Brew steuern",
            category=CATEGORY_MECHANICS,
            summary=(
                "Stagger verteilt Schaden über Zeit - er muss aktiv "
                "abgebaut werden, sonst summiert er sich tödlich."
            ),
            steps=(
                "Die Stagger-Stufe dauerhaft im Blick behalten.",
                "Bei schwerem Stagger sofort reinigen.",
                "Braukugeln nicht ungenutzt liegen lassen.",
            ),
            class_name="Monk",
            spec="Braumeister",
        ),

    ),

    ("Rogue", "Meucheln"): (

        Lesson(
            lesson_id="rogue.assassination.uptime",
            title="Rupture und Slice and Dice halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Beide Effekte dürfen im ganzen Kampf nie auslaufen."
            ),
            steps=(
                "Beide Laufzeiten dauerhaft anzeigen lassen.",
                "Envenom erst danach einplanen.",
                "Vor Bewegungsphasen vorsorglich auffrischen.",
            ),
            class_name="Rogue",
            spec="Meucheln",
        ),

    ),

    ("Hunter", "Treffsicherheit"): (

        Lesson(
            lesson_id="hunter.marksmanship.steady_focus",
            title="Steady Focus dauerhaft halten",
            category=CATEGORY_ROTATION,
            summary=(
                "Der Effekt bestimmt Fokusregeneration und "
                "Angriffstempo gleichermaßen."
            ),
            steps=(
                "Immer zwei Steady Shots hintereinander einsetzen.",
                "Den Effekt vor dem Auslaufen erneuern.",
                "Die Uptime nach dem Pull kontrollieren.",
            ),
            class_name="Hunter",
            spec="Treffsicherheit",
        ),

    ),

    ("Paladin", "Vergeltung"): (

        Lesson(
            lesson_id="paladin.retribution.inquisition",
            title="Inquisition-Uptime sichern",
            category=CATEGORY_ROTATION,
            summary=(
                "Inquisition ist die Grundlage des gesamten "
                "Schadens - Lücken kosten überproportional viel."
            ),
            steps=(
                "Inquisition mit drei Kraftsiegeln verlängern.",
                "Nie unter zehn Sekunden Restlaufzeit fallen.",
                "Vor großen Cooldowns frisch auftragen.",
            ),
            class_name="Paladin",
            spec="Vergeltung",
        ),

    ),

    ("Death Knight", "Unheilig"): (

        Lesson(
            lesson_id="deathknight.unholy.dark_transformation",
            title="Dark Transformation rechtzeitig einsetzen",
            category=CATEGORY_COOLDOWNS,
            summary=(
                "Der Diener verliert deutlich an Wert, wenn die "
                "Verwandlung verzögert wird."
            ),
            steps=(
                "Schatteninfusion bis fünf Stapel aufbauen.",
                "Sofort danach verwandeln.",
                "Die Verwandlung mit den eigenen Cooldowns bündeln.",
            ),
            class_name="Death Knight",
            spec="Unheilig",
        ),

    ),

}


# --------------------------------------------------


def lessons_for_actor(actor: Actor | None) -> tuple[Lesson, ...]:
    """
    Alle Lektionen, die für diesen Spieler in Frage kommen: erst die
    seiner Spezialisierung, danach die allgemeinen.
    """

    if actor is None:
        return GENERIC_LESSONS

    specific = SPEC_LESSONS.get(
        (actor.class_name, actor.spec),
        (),
    )

    return specific + GENERIC_LESSONS


def lessons_in_category(
    actor: Actor | None,
    category: str,
) -> tuple[Lesson, ...]:
    """
    Die passenden Lektionen eines Bereichs, Spezialisierung zuerst.
    """

    return tuple(
        lesson
        for lesson in lessons_for_actor(actor)
        if lesson.category == category
    )


def all_lessons() -> tuple[Lesson, ...]:
    """
    Der komplette Katalog - für Übersicht und Suche in der Academy.
    """

    lessons: list[Lesson] = []

    for entries in SPEC_LESSONS.values():

        lessons.extend(entries)

    lessons.extend(GENERIC_LESSONS)

    return tuple(lessons)


def find_lesson(lesson_id: str) -> Lesson | None:

    for lesson in all_lessons():

        if lesson.lesson_id == lesson_id:
            return lesson

    return None
