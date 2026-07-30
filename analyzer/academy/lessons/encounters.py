"""
Bossbezogene Lektionen.

Die Ebene, auf der aus "vermeidbarer Schaden" konkreter Lernstoff
wird: die Fähigkeiten hier sind dieselben, die
analyzer/data/avoidable.py als vermeidbar einordnet. Damit schließt
sich der Kreis - ein Treffer in der Analyse führt zu einer Lektion,
die genau diesen Treffer behandelt, und der Trainingsplan prüft
anschließend selbst, ob er ausgeblieben ist.

Der Schlüssel ist der **englische** Bossname, wie ihn WarcraftLogs
und das Combat-Log liefern - dieselbe Konvention wie in
analyzer/data/encounters.py.

Abgedeckt sind alle vierzehn Kämpfe der Schlacht um Orgrimmar sowie
Horridon (den bildet die Simulation nach).

Es stehen hier nur Kämpfe, für die auch Referenzdaten in
analyzer/data/avoidable.py hinterlegt sind - eine Lektion zu einem
Boss, dessen Fähigkeiten nirgends eingeordnet sind, könnte nie
geprüft werden und bliebe dauerhaft auf "keine Daten" stehen. Ein
Test hält diese Kopplung fest.
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_SURVIVAL,
    CHECK_AT_MOST,
    Lesson,
    LessonCheck,
)
from analyzer.models import MECHANIC_INTERRUPT, MECHANIC_MOVEMENT


def _no_hits(label: str) -> LessonCheck:
    """
    "Keine vermeidbaren Treffer" - das mit Abstand häufigste
    Kriterium bossbezogener Lektionen.
    """

    return LessonCheck(
        metric="avoidable_hits",
        comparison=CHECK_AT_MOST,
        target=0.0,
        unit="×",
        label=label,
    )


ENCOUNTER_LESSONS: dict[str, tuple[Lesson, ...]] = {

    "Horridon": (

        Lesson(
            lesson_id="boss-horridon.movement.double_swipe",
            title="Doppelhieb nicht kassieren",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Doppelhieb trifft alles vor dem Boss. Wer nicht im Rücken "
                "steht, nimmt ihn zwangsläufig mit."
            ),
            steps=(
                "Als Nahkämpfer grundsätzlich hinter dem Boss stehen.",
                "Nach jedem Tankwechsel die eigene Position prüfen.",
                "Bei Ansturm nicht vor den Boss zurücklaufen.",
            ),
            encounter="Horridon",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-horridon.movement.blazing_sunlight",
            title="Vor dem Sonnenlicht in Deckung gehen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Loderndes Sonnenlicht ist angekündigt und trifft jeden ohne "
                "Deckung. Es gibt keinen Grund, davon getroffen zu werden."
            ),
            steps=(
                "Die Deckungspunkte vor dem Pull festlegen.",
                "Beim Zauberbeginn sofort losgehen, nicht abwarten.",
                "Bis zum Ende des Zaubers in Deckung bleiben.",
            ),
            encounter="Horridon",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-horridon.mechanics.deadly_plague",
            title="Den Beschwörer unterbrechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Tödliche Seuche des Gurubashi-Beschwörers ist "
                "unterbrechbar - durchgelassen kostet sie den Raid erhebliche "
                "Heilung."
            ),
            steps=(
                "Eine feste Unterbrechungsreihenfolge festlegen.",
                "Den Beschwörer beim Erscheinen sofort markieren.",
                "Nach jeder Tür die Zuordnung neu bestätigen.",
            ),
            encounter="Horridon",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_INTERRUPT,
                    unit="×",
                    label="Verpasste Unterbrechungen",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-horridon.survival.venom",
            title="Aus der Giftpfütze heraus",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Giftpfütze richtet mit jeder Sekunde mehr Schaden an. Ein "
                "Schritt zur Seite beendet sie."
            ),
            steps=(
                "Die eigene Position nach jeder Salve prüfen.",
                "Nicht warten, bis die Heilung nachkommt.",
                "Die Pfützen nicht im Raid ablegen.",
            ),
            encounter="Horridon",
        ),

    ),

    "Immerseus": (

        Lesson(
            lesson_id="boss-immerseus.movement.swirl",
            title="Den Wasserwirbeln ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Wirbel bewegen sich langsam und vorhersehbar. Getroffen zu "
                "werden ist reine Unaufmerksamkeit."
            ),
            steps=(
                "Die Laufrichtung der Wirbel früh erkennen.",
                "Seitlich ausweichen, nicht davonlaufen.",
                "Beim Ausweichen weiter angreifen.",
            ),
            encounter="Immerseus",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-immerseus.survival.puddles",
            title="Nicht in die Sha-Pfützen laufen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Die Pfützen stehen still. Wer hineinläuft, tut das immer "
                "selbst."
            ),
            steps=(
                "Beim Sammeln der Kugeln auf den Boden achten.",
                "Den Weg vorher planen statt der Kugel hinterher.",
                "Nach der Phase die Position zurücksetzen.",
            ),
            encounter="Immerseus",
        ),

    ),

    "The Fallen Protectors": (

        Lesson(
            lesson_id="boss-fallen-protectors.movement.brew",
            title="Dem Verderbten Gebräu ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Das geworfene Fass ist angekündigt und hinterlässt eine "
                "Fläche, in der niemand stehen muss."
            ),
            steps=(
                "Auf den Wurf achten und sofort seitlich ausweichen.",
                "Die Fläche nicht im Nahkampfbereich ablegen lassen.",
                "Nach dem Ausweichen zurück auf die Ausgangsposition.",
            ),
            encounter="The Fallen Protectors",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-fallen-protectors.survival.ground",
            title="Besudelten Boden und Gift verlassen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Beide Flächen bleiben liegen. Der Schaden daraus ist reine "
                "Standzeit."
            ),
            steps=(
                "Nach jeder Fläche die eigene Position prüfen.",
                "Flächen am Rand ablegen, nicht in der Mitte.",
                "Nicht auf die Heilung warten.",
            ),
            encounter="The Fallen Protectors",
        ),

        Lesson(
            lesson_id="boss-fallen-protectors.mechanics.focus",
            title="Zielreihenfolge einhalten",
            category=CATEGORY_MECHANICS,
            summary=(
                "Drei Gegner mit getrennten Lebensbalken - wer am falschen "
                "steht, verlängert den Kampf für alle."
            ),
            steps=(
                "Die Zielpriorität vor dem Pull klären.",
                "Zielmarkierungen tatsächlich benutzen.",
                "Bei den Beschwörungen umschwenken.",
            ),
            encounter="The Fallen Protectors",
        ),

    ),

    "Norushen": (

        Lesson(
            lesson_id="boss-norushen.movement.blind_hatred",
            title="Dem Blinden Hass ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Kugel zieht eine berechenbare Bahn. Ein Treffer ist immer "
                "ein Positionsfehler."
            ),
            steps=(
                "Die Laufrichtung der Kugel früh erkennen.",
                "Rechtzeitig aus der Bahn treten, nicht im letzten Moment.",
                "Während des Ausweichens weiterspielen.",
            ),
            encounter="Norushen",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-norushen.mechanics.corruption",
            title="Die eigene Verderbnis rechtzeitig abbauen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Wer zu lange verderbt bleibt, verliert Wirkung und wird zur "
                "Belastung für den Raid."
            ),
            steps=(
                "Die eigene Verderbnisanzeige im Blick behalten.",
                "Rechtzeitig in die Prüfung gehen.",
                "Die Manifestation dort zügig töten.",
            ),
            encounter="Norushen",
        ),

    ),

    "Sha of Pride": (

        Lesson(
            lesson_id="boss-sha-of-pride.mechanics.pride",
            title="Stolz niedrig halten",
            category=CATEGORY_MECHANICS,
            summary=(
                "Stolz sammelt sich durch Fehler und schaltet ab bestimmten "
                "Schwellen zusätzliche Mechaniken frei."
            ),
            steps=(
                "Die eigene Stolzanzeige dauerhaft beobachten.",
                "Bei den Gefängnissen sofort helfen.",
                "In die Reinigungsfelder gehen, wenn zugewiesen.",
            ),
            encounter="Sha of Pride",
        ),

        Lesson(
            lesson_id="boss-sha-of-pride.movement.projection",
            title="Den Projektionen ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Spiegelbilder laufen auf ihr Ziel zu und sind vorhersehbar "
                "- ein Treffer kostet zusätzlich Stolz."
            ),
            steps=(
                "Die eigene Projektion früh erkennen.",
                "Vom Raid weg ausweichen, nicht hinein.",
                "Nach dem Ausweichen zurück in Reichweite.",
            ),
            encounter="Sha of Pride",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

    ),

    "Galakras": (

        Lesson(
            lesson_id="boss-galakras.movement.flames",
            title="Aus den Flammen Galakronds heraus",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Flammenfläche ist angekündigt und bleibt liegen. Dort zu "
                "stehen ist nie nötig."
            ),
            steps=(
                "Auf die Ankündigung achten, nicht auf den Schaden.",
                "Seitlich heraustreten statt nach hinten zu laufen.",
                "Die Fläche nicht am Sammelpunkt ablegen.",
            ),
            encounter="Galakras",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-galakras.mechanics.towers",
            title="Türme zügig freiräumen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Die Turmphase bestimmt die Länge des ganzen Kampfes - jede "
                "Verzögerung kostet zusätzliche Wellen."
            ),
            steps=(
                "Die Turmgruppe vor dem Pull festlegen.",
                "Adds am Fuß des Turms nicht liegen lassen.",
                "Nach dem Turm sofort zurück zur Gruppe.",
            ),
            encounter="Galakras",
        ),

    ),

    "Iron Juggernaut": (

        Lesson(
            lesson_id="boss-iron-juggernaut.movement.laser",
            title="Vor dem Schneidlaser laufen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Laser folgt einem Spieler und brennt eine Spur ein. "
                "Stehenbleiben ist der teuerste Fehler des Kampfes."
            ),
            steps=(
                "Beim Zielen sofort seitlich loslaufen.",
                "Die Spur nicht durch den Raid ziehen.",
                "Nach dem Laser die eigene Position zurücksetzen.",
            ),
            encounter="Iron Juggernaut",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-iron-juggernaut.survival.tar",
            title="Nicht im Teer stehen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Der Teer entzündet sich. Wer darin steht, wenn das passiert, "
                "hat es selbst in der Hand gehabt."
            ),
            steps=(
                "Teerflächen sofort verlassen, nicht nur meiden.",
                "Vor der Entzündung ausreichend Abstand nehmen.",
                "Die Bohrstelle nicht im Teer ablegen.",
            ),
            encounter="Iron Juggernaut",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-iron-juggernaut.movement.borer",
            title="Von der Bohrstelle weglaufen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Markierung ist eindeutig und der Schaden hoch - beides "
                "zusammen macht einen Treffer unnötig."
            ),
            steps=(
                "Bei der Markierung sofort loslaufen.",
                "Vom Raid weg, nicht hinein.",
                "Erst zurückkehren, wenn der Bohrer durch ist.",
            ),
            encounter="Iron Juggernaut",
        ),

    ),

    "Kor'kron Dark Shaman": (

        Lesson(
            lesson_id="boss-dark-shaman.movement.ashen_wall",
            title="Nicht durch die Aschewand laufen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Wand steht sichtbar im Raum. Ein Treffer entsteht "
                "ausschließlich durch Unachtsamkeit beim Laufweg."
            ),
            steps=(
                "Den Laufweg vor der Bewegung planen.",
                "Um die Wand herum, nicht hindurch.",
                "Bei Positionswechseln zuerst schauen.",
            ),
            encounter="Kor'kron Dark Shaman",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-dark-shaman.survival.storms",
            title="Giftwolken und Asche verlassen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Beide Flächen wandern langsam. Wer sie beobachtet, muss nie "
                "hineingeraten."
            ),
            steps=(
                "Die Wanderrichtung früh erkennen.",
                "Rechtzeitig ausweichen statt zu reagieren.",
                "Den Boss aus den Flächen heraustanken.",
            ),
            encounter="Kor'kron Dark Shaman",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

    ),

    "General Nazgrim": (

        Lesson(
            lesson_id="boss-nazgrim.movement.shockwave",
            title="Der Heroischen Schockwelle ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Schockwelle trifft nur nach vorn und ist angekündigt. Wer "
                "hinter dem Boss steht, ist sicher."
            ),
            steps=(
                "Grundsätzlich hinter dem Boss stehen.",
                "Bei der Ankündigung die Position prüfen.",
                "Fernkämpfer bleiben außerhalb der Reichweite.",
            ),
            encounter="General Nazgrim",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-nazgrim.mechanics.stance",
            title="Auf den Haltungswechsel reagieren",
            category=CATEGORY_MECHANICS,
            summary=(
                "Nazgrims Haltung entscheidet, ob Angriffe schaden oder helfen. "
                "Weiterzuspielen wie zuvor ist der häufigste Fehler."
            ),
            steps=(
                "Die drei Haltungen und ihre Bedeutung lernen.",
                "Bei Verteidigungshaltung den Schaden einstellen.",
                "Bei Berserkerhaltung die Unterbrechungen setzen.",
            ),
            encounter="General Nazgrim",
        ),

        Lesson(
            lesson_id="boss-nazgrim.mechanics.arcweaver",
            title="Den Arkanweber unterbrechen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Arkane Schock ist unterbrechbar und trifft den ganzen "
                "Raid. Eine verpasste Unterbrechung ist teuer."
            ),
            steps=(
                "Eine Unterbrechungsreihenfolge festlegen.",
                "Den Arkanweber beim Erscheinen markieren.",
                "Nach jeder Welle die Zuordnung bestätigen.",
            ),
            encounter="General Nazgrim",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_INTERRUPT,
                    unit="×",
                    label="Verpasste Unterbrechungen",
                ),
            ),
        ),

    ),

    "Malkorok": (

        Lesson(
            lesson_id="boss-malkorok.movement.imploding",
            title="Von der implodierenden Kugel weg",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Kugel kündigt ihre Implosion an. Der Schaden trifft nur, "
                "wer stehen bleibt."
            ),
            steps=(
                "Die Kugeln früh erkennen und Abstand halten.",
                "Nicht zwischen zwei Kugeln stehen bleiben.",
                "Nach der Implosion zurück in Reichweite.",
            ),
            encounter="Malkorok",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-malkorok.survival.shields",
            title="Die Schilde vor der Spitze füllen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "In diesem Kampf zählt kein Lebenspunkt, sondern der Schild. "
                "Wer ihn leer laufen lässt, stirbt trotz voller Heilung."
            ),
            steps=(
                "Den eigenen Schildwert dauerhaft beobachten.",
                "Vermeidbaren Schaden konsequent ausschließen.",
                "Vor dem Atem den Schild voll haben.",
            ),
            encounter="Malkorok",
            checks=(
                LessonCheck(
                    metric="deaths",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    unit="×",
                    label="Tode im Kampf",
                ),
            ),
        ),

    ),

    "Spoils of Pandaria": (

        Lesson(
            lesson_id="boss-spoils.mechanics.order",
            title="Kisten in der abgesprochenen Reihenfolge öffnen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Der Kampf steht und fällt mit der Reihenfolge - eine falsch "
                "geöffnete Kiste kostet die ganze Gruppe Zeit."
            ),
            steps=(
                "Die Reihenfolge vor dem Pull festlegen.",
                "Nicht eigenmächtig öffnen.",
                "Den Fortschritt der anderen Seite im Blick behalten.",
            ),
            encounter="Spoils of Pandaria",
        ),

        Lesson(
            lesson_id="boss-spoils.movement.set_to_blow",
            title="Zündbereit rechtzeitig entschärfen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Ladung ist sichtbar und hat eine Laufzeit. Ein Treffer "
                "heißt, dass niemand reagiert hat."
            ),
            steps=(
                "Die Ladung sofort ansagen.",
                "Gemeinsam abbauen statt einzeln.",
                "Sonst rechtzeitig Abstand nehmen.",
            ),
            encounter="Spoils of Pandaria",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

    ),

    "Thok the Bloodthirsty": (

        Lesson(
            lesson_id="boss-thok.movement.tail",
            title="Nicht hinter Thok stehen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Schwanzhieb trifft nur nach hinten. Die Position ist die "
                "ganze Mechanik."
            ),
            steps=(
                "Grundsätzlich seitlich vom Boss stehen.",
                "Beim Umtanken den Bogen laufen, nicht hindurch.",
                "Fernkämpfer halten Abstand zur Rückseite.",
            ),
            encounter="Thok the Bloodthirsty",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-thok.movement.breath",
            title="Den Atemspuren ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Ob Feuer, Eis oder Säure - alle drei Spuren bleiben liegen und "
                "sind angekündigt."
            ),
            steps=(
                "Die Phase am Atemtyp erkennen.",
                "Vor dem Atem die Laufrichtung festlegen.",
                "Spuren nicht durch den Raid ziehen.",
            ),
            encounter="Thok the Bloodthirsty",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-thok.survival.pace",
            title="Das Tempo des Kampfes überstehen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Thok wird mit jeder Phase schneller. Wer früh Heilung durch "
                "Eigenverschulden bindet, fehlt am Ende."
            ),
            steps=(
                "Persönliche Defensives auf die schnellen Phasen legen.",
                "Vermeidbaren Schaden konsequent ausschließen.",
                "Selbstheilung tatsächlich benutzen.",
            ),
            encounter="Thok the Bloodthirsty",
            checks=(
                LessonCheck(
                    metric="deaths",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    unit="×",
                    label="Tode im Kampf",
                ),
            ),
        ),

    ),

    "Siegecrafter Blackfuse": (

        Lesson(
            lesson_id="boss-blackfuse.movement.mines",
            title="Kriechminen nicht berühren",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Minen fahren sichtbar über den Boden. Ein Treffer ist "
                "immer vermeidbar."
            ),
            steps=(
                "Die Minen früh erkennen und ausweichen.",
                "Nicht rückwärts in eine Mine laufen.",
                "Beim Fließband auf den Boden achten.",
            ),
            encounter="Siegecrafter Blackfuse",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-blackfuse.mechanics.belt",
            title="Am Fließband zügig arbeiten",
            category=CATEGORY_MECHANICS,
            summary=(
                "Jede Waffe, die durchkommt, macht den restlichen Kampf "
                "schwerer - die Zeit am Band ist knapp bemessen."
            ),
            steps=(
                "Die Bandgruppe vor dem Pull festlegen.",
                "Cooldowns für das Band aufsparen.",
                "Sofort zurück, wenn die Waffe liegt.",
            ),
            encounter="Siegecrafter Blackfuse",
        ),

    ),

    "Paragons of the Klaxxi": (

        Lesson(
            lesson_id="boss-klaxxi.movement.aim",
            title="Aus der Schusslinie gehen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Hiseks Zielen ist angekündigt und lässt sich durch Deckung "
                "oder Bewegung vollständig vermeiden."
            ),
            steps=(
                "Auf die Zielansage achten.",
                "Deckung suchen oder aus der Linie treten.",
                "Nicht in der Gruppe stehen bleiben.",
            ),
            encounter="Paragons of the Klaxxi",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-klaxxi.survival.pools",
            title="Gift- und Blutlachen verlassen",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Beide Flächen bleiben liegen und wachsen. Standzeit darin ist "
                "reiner Eigenschaden."
            ),
            steps=(
                "Flächen am Rand ablegen.",
                "Nach jeder Fläche die Position prüfen.",
                "Nicht auf die Heilung warten.",
            ),
            encounter="Paragons of the Klaxxi",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-klaxxi.mechanics.order",
            title="Die Tötungsreihenfolge einhalten",
            category=CATEGORY_MECHANICS,
            summary=(
                "Neun Gegner mit wechselnden Fähigkeiten - die Reihenfolge "
                "entscheidet, welche Mechaniken überhaupt zusammentreffen."
            ),
            steps=(
                "Die Reihenfolge vor dem Pull festlegen.",
                "Zielmarkierungen benutzen.",
                "Beim Erwachen sofort umschwenken.",
            ),
            encounter="Paragons of the Klaxxi",
        ),

    ),

    "Garrosh Hellscream": (

        Lesson(
            lesson_id="boss-garrosh.movement.iron_star",
            title="Dem Eisernen Stern ausweichen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Der Stern rollt geradeaus und ist weithin sichtbar. Ein "
                "Treffer ist in aller Regel tödlich - und immer vermeidbar."
            ),
            steps=(
                "Die Bahn des Sterns früh erkennen.",
                "Seitlich ausweichen, nicht davonlaufen.",
                "Nach dem Stern zurück auf die Position.",
            ),
            encounter="Garrosh Hellscream",
            checks=(
                LessonCheck(
                    metric="mechanic_count",
                    comparison=CHECK_AT_MOST,
                    target=0.0,
                    subject=MECHANIC_MOVEMENT,
                    unit="×",
                    label="Treffer durch Bewegungsmechaniken",
                ),
            ),
        ),

        Lesson(
            lesson_id="boss-garrosh.movement.desecrate",
            title="Entweihten Boden verlassen",
            category=CATEGORY_MOVEMENT,
            summary=(
                "Die Fläche ist angekündigt und bleibt liegen. Wer darauf "
                "stehen bleibt, verliert den Rest der Phase."
            ),
            steps=(
                "Bei der Ankündigung sofort heraustreten.",
                "Die Fläche am Rand ablegen.",
                "Den Raum für die späteren Phasen freihalten.",
            ),
            encounter="Garrosh Hellscream",
            checks=(_no_hits("Vermeidbare Treffer in diesem Kampf"),),
        ),

        Lesson(
            lesson_id="boss-garrosh.survival.malice",
            title="Bei Bosheit vom Raid weg",
            category=CATEGORY_SURVIVAL,
            summary=(
                "Bosheit trifft alle in der Nähe. Wer stehen bleibt, macht aus "
                "dem eigenen Fehler den Fehler mehrerer."
            ),
            steps=(
                "Den Ausweichpunkt vor dem Pull festlegen.",
                "Sofort auf die Ansage reagieren.",
                "Erst zurück, wenn der Effekt abgelaufen ist.",
            ),
            encounter="Garrosh Hellscream",
        ),

        Lesson(
            lesson_id="boss-garrosh.mechanics.phases",
            title="Die Phasenwechsel sauber mitgehen",
            category=CATEGORY_MECHANICS,
            summary=(
                "Garroshs Phasen ändern Aufstellung und Prioritäten. Die "
                "meisten Wipes entstehen im Übergang, nicht in der Phase "
                "selbst."
            ),
            steps=(
                "Für jede Phase eine feste Position festlegen.",
                "Beim Wechsel zuerst positionieren, dann angreifen.",
                "Cooldowns auf die Phase legen, nicht auf den Wechsel.",
            ),
            encounter="Garrosh Hellscream",
        ),

    ),

}
