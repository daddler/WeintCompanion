"""
Referenzdaten: welcher Schaden war vermeidbar.

WarcraftLogs sagt nur, *wer wodurch* Schaden bekam. Ob ein Treffer
vermeidbar war, ist Spielwissen pro Boss - eine Wertung, keine
Messung. Diese Wertung liegt bewusst hier und nicht im Bot:

- Sie muss für WeintTV und die WeintAcademy identisch sein. Eine
  Tabelle im Analyzer ist genau eine Quelle der Wahrheit.
- Sie ist eine Balance-Meinung und ändert sich mit Schwierigkeitsgrad
  und Taktik. Hier ist sie in einem Diff nachvollziehbar und ohne
  Bot-Deploy korrigierbar.
- Sie ist ohne Netzwerkzugriff testbar.

Wichtigste Entscheidung: das Urteil ist **dreiwertig**. Eine
Fähigkeit, die hier nicht steht, ist VERDICT_UNKNOWN und nicht
"unvermeidbar". Würde Unbekanntes als unvermeidbar gelten, bekäme
jeder Boss ohne Referenzdaten automatisch eine tadellose Bewertung -
und die Tabelle deckt anfangs nur eine Handvoll Bosse ab. Umgekehrt
wäre "unbekannt = vermeidbar" eine Unterstellung.

Nachschlagen läuft wie in analyzer.data.encounters über den
kleingeschriebenen Namen, mit einem beim Import gebauten Index.
Unbekannte Eingaben liefern None und werfen nie.

Abdeckung: alle vierzehn Kämpfe der Schlacht um Orgrimmar sowie
Horridon (den bildet die Simulation nach). Vollständig heißt hier
"jeder Kampf ist vertreten", nicht "jede Fähigkeit jedes Bosses steht
hier". Erfasst sind die Fähigkeiten, bei denen die Zuordnung
eindeutig ist: Bodenflächen, angekündigte Kegel, Zauber mit
Unterbrechungsfenster, Tankangriffe.

Was fehlt, bleibt bewusst offen. Eine falsch als vermeidbar
eingeordnete Fähigkeit ist schlimmer als eine Lücke: sie erzeugt
einen Vorwurf gegen einen Spieler, der nichts falsch gemacht hat.

Erweitern: einen Eintrag in ENCOUNTER_ABILITIES ergänzen. Die
Fähigkeitsnamen sind die *englischen* aus dem Combat-Log bzw. der
WarcraftLogs-Antwort, `label`/`note` sind der deutsche Text für die
Oberfläche. Die Übersetzungstabelle für Bot-Texte entsteht daraus von
selbst - siehe ABILITY_ALIASES weiter unten.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.models import (
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_OTHER,
    MECHANIC_POSITIONING,
)


#
# --------------------------------------------------
# Urteile
# --------------------------------------------------
#

VERDICT_AVOIDABLE = "avoidable"
VERDICT_UNAVOIDABLE = "unavoidable"
VERDICT_UNKNOWN = "unknown"


#
# Ab welchem Anteil eingeordneten Schadens eine Aussage über
# "vermeidbar" überhaupt zulässig ist. Darunter fehlen zu viele
# Referenzdaten, und die Academy gibt "keine Daten" statt einer
# Bewertung, die nur die Lücken der Tabelle abbildet.
#

MIN_CLASSIFIED_SHARE = 0.25


@dataclass(frozen=True)
class AbilityRule:
    """
    Die Einordnung einer Fähigkeit.

    `category` ist eine der MECHANIC_*-Konstanten und der Grund,
    warum aus einer Schadenszeile überhaupt ein der Academy
    zuordenbarer Fehler werden kann.

    `note` ist der kurze deutsche Hinweis, was man anders machen
    sollte - er landet unverändert in der Oberfläche.

    `tank_exempt` markiert Fähigkeiten, die für Tanks zum Job
    gehören: einen Nahkampfangriff "vermeidbar" zu nennen, wäre für
    den Tank unsinnig, für alle anderen richtig.
    """

    ability: str

    label: str = ""

    verdict: str = VERDICT_AVOIDABLE

    category: str = MECHANIC_MOVEMENT

    severity: str = "warning"

    note: str = ""

    source_name: str = ""

    tank_exempt: bool = False


#
# --------------------------------------------------
# Kampfunabhängige Wahrheiten
# --------------------------------------------------
#
# Diese gelten überall und sind deshalb aus jeder Bosstabelle
# herausgehalten.
#

GLOBAL_ABILITIES: tuple[AbilityRule, ...] = (

    AbilityRule(
        ability="Falling",
        label="Sturzschaden",
        category=MECHANIC_MOVEMENT,
        note="Sturzschaden lässt sich immer vermeiden.",
    ),
    AbilityRule(
        ability="Fatigue",
        label="Erschöpfung",
        category=MECHANIC_POSITIONING,
        note="Kampfgebiet verlassen - zurück in die Arena.",
    ),
    AbilityRule(
        ability="Drowning",
        label="Ertrinken",
        category=MECHANIC_POSITIONING,
        note="Nicht unter Wasser bleiben.",
    ),
    AbilityRule(
        ability="Melee",
        label="Nahkampfangriff",
        verdict=VERDICT_UNAVOIDABLE,
        category=MECHANIC_OTHER,
        tank_exempt=True,
    ),

)


#
# --------------------------------------------------
# Bossspezifische Einordnung
# --------------------------------------------------
#
# Bewusst lückenhaft statt geraten: hier stehen nur Kämpfe, deren
# Mechaniken eindeutig sind. Alles andere bleibt VERDICT_UNKNOWN und
# wird ehrlich als "nicht eingeordnet" angezeigt, statt eine
# Bewertung zu erfinden.
#
# Horridon steht hier, weil der Simulations-Anbieter
# (analyzer/providers/mock.py) diesen Kampf nachbildet - dadurch ist
# die Verdrahtung zwischen Referenzdaten und Auswertung ohne Bot
# vorführbar. Der Bot schickt für Immerseus zusätzlich eine eigene
# Regel mit: so wird das Zusammenführen beider Quellen tatsächlich
# durchlaufen.
#

ENCOUNTER_ABILITIES: dict[str, tuple[AbilityRule, ...]] = {

    "Horridon": (

        AbilityRule(
            ability="Triple Puncture",
            label="Dreifacher Stich",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Double Swipe",
            label="Doppelhieb",
            category=MECHANIC_POSITIONING,
            severity="error",
            note="Nicht vor dem Boss stehen bleiben.",
        ),
        AbilityRule(
            ability="Dire Call",
            label="Unheilvoller Ruf",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Venom Bolt Volley",
            label="Giftbolzensalve",
            category=MECHANIC_MOVEMENT,
            note="Aus der Giftpfütze herauslaufen.",
        ),
        AbilityRule(
            ability="Blazing Sunlight",
            label="Loderndes Sonnenlicht",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Hinter eine Deckung laufen, bevor der Zauber endet.",
        ),
        AbilityRule(
            ability="Deadly Plague",
            label="Tödliche Seuche",
            category=MECHANIC_INTERRUPT,
            note="Den Zauber des Gurubashi-Beschwörers unterbrechen.",
        ),
        AbilityRule(
            ability="Rending Charge",
            label="Zerfetzender Ansturm",
            category=MECHANIC_MOVEMENT,
            note="Der Ansturmbahn ausweichen.",
        ),

    ),

    #
    # --------------------------------------------------
    # Schlacht um Orgrimmar
    # --------------------------------------------------
    #
    # Vollständig in dem Sinn, dass jeder der vierzehn Kämpfe
    # vertreten ist. Nicht vollständig in dem Sinn, dass jede
    # Fähigkeit jedes Bosses hier stünde - das wäre geraten, und
    # Geratenes ist hier schlimmer als eine Lücke: eine falsch als
    # vermeidbar eingeordnete Fähigkeit erzeugt einen Vorwurf gegen
    # einen Spieler, der nichts falsch gemacht hat.
    #
    # Erfasst sind deshalb die Fähigkeiten, bei denen die Zuordnung
    # eindeutig ist: Bodenflächen, angekündigte Kegel, Zauber mit
    # Unterbrechungsfenster, Tankangriffe. Was fehlt, bleibt "nicht
    # eingeordnet" und senkt niemandes Bewertung.
    #

    "Immerseus": (

        AbilityRule(
            ability="Corrosive Blast",
            label="Ätzender Schlag",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Swirl",
            label="Wirbel",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Den Wasserwirbeln ausweichen.",
        ),
        AbilityRule(
            ability="Sha Puddle",
            label="Sha-Pfütze",
            category=MECHANIC_POSITIONING,
            note="Nicht in die Pfütze laufen.",
        ),
        AbilityRule(
            ability="Sha Pool",
            label="Sha-Lache",
            category=MECHANIC_POSITIONING,
            note="Nicht in der Lache stehen bleiben.",
        ),
        AbilityRule(
            ability="Sha Bolt",
            label="Sha-Blitz",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "The Fallen Protectors": (

        AbilityRule(
            ability="Vengeful Strikes",
            label="Rachsüchtige Schläge",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Corrupted Brew",
            label="Verderbtes Gebräu",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Dem geworfenen Fass ausweichen.",
        ),
        AbilityRule(
            ability="Defiled Ground",
            label="Besudelter Boden",
            category=MECHANIC_POSITIONING,
            note="Die verseuchte Fläche verlassen.",
        ),
        AbilityRule(
            ability="Noxious Poison",
            label="Schädliches Gift",
            category=MECHANIC_POSITIONING,
            note="Nicht in der Giftlache stehen bleiben.",
        ),
        AbilityRule(
            ability="Calamity",
            label="Unheil",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Sha Sear",
            label="Sha-Versengung",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Shadow Word: Bane",
            label="Schattenwort: Verderben",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Norushen": (

        AbilityRule(
            ability="Blind Hatred",
            label="Blinder Hass",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Der kreisenden Kugel ausweichen.",
        ),
        AbilityRule(
            ability="Titanic Smash",
            label="Titanischer Schlag",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Unleashed Anger",
            label="Entfesselter Zorn",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Burst of Corruption",
            label="Ausbruch der Verderbnis",
            category=MECHANIC_MOVEMENT,
            note="Die Manifestation rechtzeitig töten oder ausweichen.",
        ),

    ),

    "Sha of Pride": (

        AbilityRule(
            ability="Wounded Pride",
            label="Verletzter Stolz",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - nur der Tank darf getroffen werden.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Mocking Blast",
            label="Spöttischer Stoß",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Swelling Pride",
            label="Anschwellender Stolz",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Projection",
            label="Projektion",
            category=MECHANIC_MOVEMENT,
            note="Den Projektionen ausweichen.",
        ),
        AbilityRule(
            ability="Self-Reflection",
            label="Selbstreflexion",
            category=MECHANIC_MOVEMENT,
            note="Dem Spiegelbild aus dem Weg gehen.",
        ),

    ),

    "Galakras": (

        AbilityRule(
            ability="Flames of Galakrond",
            label="Flammen Galakronds",
            category=MECHANIC_POSITIONING,
            severity="error",
            note="Nicht in den Flammen stehen bleiben.",
        ),
        AbilityRule(
            ability="Flame Breath",
            label="Flammenatem",
            category=MECHANIC_POSITIONING,
            note="Nicht vor dem Drachen stehen.",
        ),
        AbilityRule(
            ability="Crush",
            label="Zermalmen",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Poison-Tipped Blades",
            label="Giftbestrichene Klingen",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Iron Juggernaut": (

        AbilityRule(
            ability="Ignite Armor",
            label="Rüstung entzünden",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - Wechsel bei zu vielen Stapeln.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Cutter Laser",
            label="Schneidlaser",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Vor dem Laser weglaufen, nicht stehen bleiben.",
        ),
        AbilityRule(
            ability="Laser Burn",
            label="Laserbrand",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Die Laserspur verlassen.",
        ),
        AbilityRule(
            ability="Borer Drill",
            label="Bohrer",
            category=MECHANIC_MOVEMENT,
            note="Von der markierten Bohrstelle weglaufen.",
        ),
        AbilityRule(
            ability="Explosive Tar",
            label="Explosiver Teer",
            category=MECHANIC_POSITIONING,
            note="Nicht im Teer stehen.",
        ),
        AbilityRule(
            ability="Flame Vents",
            label="Flammenschlote",
            category=MECHANIC_MOVEMENT,
            note="Aus der Reichweite der Schlote laufen.",
        ),
        AbilityRule(
            ability="Shock Pulse",
            label="Schockpuls",
            category=MECHANIC_POSITIONING,
            note="Abstand halten - der Puls wirft nach hinten.",
        ),
        AbilityRule(
            ability="Demolisher Cannon",
            label="Zerstörerkanone",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Kor'kron Dark Shaman": (

        AbilityRule(
            ability="Froststorm Strike",
            label="Froststurmschlag",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Ashen Wall",
            label="Aschewand",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Nicht durch die Aschewand laufen.",
        ),
        AbilityRule(
            ability="Falling Ash",
            label="Fallende Asche",
            category=MECHANIC_MOVEMENT,
            note="Aus dem markierten Bereich laufen.",
        ),
        AbilityRule(
            ability="Foul Stream",
            label="Übler Strom",
            category=MECHANIC_POSITIONING,
            note="Nicht in den Strahl stellen.",
        ),
        AbilityRule(
            ability="Toxic Storm",
            label="Giftiger Sturm",
            category=MECHANIC_POSITIONING,
            note="Der Wolke ausweichen.",
        ),
        AbilityRule(
            ability="Iron Tomb",
            label="Eisernes Grab",
            category=MECHANIC_MOVEMENT,
            note="Nicht neben dem Totem stehen bleiben.",
        ),
        AbilityRule(
            ability="Toxic Mist",
            label="Giftiger Nebel",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "General Nazgrim": (

        AbilityRule(
            ability="Sundering Blow",
            label="Spaltender Hieb",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - Wechsel bei zu vielen Stapeln.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Heroic Shockwave",
            label="Heroische Schockwelle",
            category=MECHANIC_POSITIONING,
            severity="error",
            note="Aus dem Kegel vor dem Boss heraus.",
        ),
        AbilityRule(
            ability="Ravager",
            label="Verwüster",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Vom rotierenden Verwüster weglaufen.",
        ),
        AbilityRule(
            ability="War Song",
            label="Kriegslied",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Arcane Shock",
            label="Arkaner Schock",
            category=MECHANIC_INTERRUPT,
            note="Den Arkanweber unterbrechen.",
        ),

    ),

    "Malkorok": (

        AbilityRule(
            ability="Arcing Smash",
            label="Bogenschlag",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Seismic Slam",
            label="Seismischer Schlag",
            category=MECHANIC_MOVEMENT,
            note="Vom markierten Ziel Abstand halten.",
        ),
        AbilityRule(
            ability="Imploding Energy",
            label="Implodierende Energie",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Von der Kugel wegbewegen, bevor sie implodiert.",
        ),
        AbilityRule(
            ability="Displaced Energy",
            label="Verschobene Energie",
            category=MECHANIC_POSITIONING,
            note="Vom Raid entfernt aufstellen.",
        ),
        AbilityRule(
            ability="Breath of Y'Shaarj",
            label="Atem Y'Shaarjs",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Spoils of Pandaria": (

        AbilityRule(
            ability="Set to Blow",
            label="Zündbereit",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Die Ladung rechtzeitig abbauen oder Abstand nehmen.",
        ),
        AbilityRule(
            ability="Bouncing Bolt",
            label="Springender Blitz",
            category=MECHANIC_MOVEMENT,
            note="Den springenden Blitzen ausweichen.",
        ),
        AbilityRule(
            ability="Massive Stomp",
            label="Gewaltiges Stampfen",
            category=MECHANIC_MOVEMENT,
            note="Aus dem Stampfbereich laufen.",
        ),
        AbilityRule(
            ability="Matter Scramble",
            label="Materiewirrwarr",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Thok the Bloodthirsty": (

        AbilityRule(
            ability="Acid Breath",
            label="Säureatem",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - Wechsel bei zu vielen Stapeln.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Tail Lash",
            label="Schwanzhieb",
            category=MECHANIC_POSITIONING,
            severity="error",
            note="Nicht hinter dem Boss stehen.",
        ),
        AbilityRule(
            ability="Scorching Breath",
            label="Sengender Atem",
            category=MECHANIC_MOVEMENT,
            note="Der Feuerspur ausweichen.",
        ),
        AbilityRule(
            ability="Freezing Breath",
            label="Eisiger Atem",
            category=MECHANIC_MOVEMENT,
            note="Der Eisspur ausweichen.",
        ),
        AbilityRule(
            ability="Corrosive Blood",
            label="Ätzende Blutspur",
            category=MECHANIC_POSITIONING,
            note="Nicht in der Blutspur stehen bleiben.",
        ),
        AbilityRule(
            ability="Deafening Screech",
            label="Ohrenbetäubender Schrei",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Fearsome Roar",
            label="Furchterregendes Brüllen",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Siegecrafter Blackfuse": (

        AbilityRule(
            ability="Magnetic Crush",
            label="Magnetisches Zermalmen",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Death from Above",
            label="Tod von oben",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Aus dem markierten Bereich laufen.",
        ),
        AbilityRule(
            ability="Shockwave Missile",
            label="Schockwellenrakete",
            category=MECHANIC_MOVEMENT,
            note="Der Rakete ausweichen.",
        ),
        AbilityRule(
            ability="Superheated Crawler Mine",
            label="Überhitzte Kriechmine",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Die Mine nicht berühren.",
        ),
        AbilityRule(
            ability="Electrostatic Charge",
            label="Elektrostatische Ladung",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Overload",
            label="Überladung",
            category=MECHANIC_INTERRUPT,
            note="Den Häcksler rechtzeitig ausschalten.",
        ),

    ),

    "Paragons of the Klaxxi": (

        AbilityRule(
            ability="Shield Bash",
            label="Schildhieb",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - mit Defensive abfedern.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Caustic Blood",
            label="Ätzendes Blut",
            category=MECHANIC_POSITIONING,
            note="Nicht in der Blutlache stehen bleiben.",
        ),
        AbilityRule(
            ability="Toxic Catalyst",
            label="Giftiger Katalysator",
            category=MECHANIC_POSITIONING,
            note="Die Giftfläche verlassen.",
        ),
        AbilityRule(
            ability="Aim",
            label="Zielen",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Aus der Schusslinie gehen oder Deckung suchen.",
        ),
        AbilityRule(
            ability="Hurl Amber",
            label="Bernstein schleudern",
            category=MECHANIC_MOVEMENT,
            note="Dem geworfenen Bernstein ausweichen.",
        ),
        AbilityRule(
            ability="Mesmerize",
            label="Hypnotisieren",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

    "Garrosh Hellscream": (

        AbilityRule(
            ability="Gripping Despair",
            label="Packende Verzweiflung",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_DEFENSIVE,
            note="Tankschaden - Wechsel bei zu vielen Stapeln.",
            tank_exempt=True,
        ),
        AbilityRule(
            ability="Desecrate",
            label="Entweihen",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Aus der entweihten Fläche laufen.",
        ),
        AbilityRule(
            ability="Whirling Corruption",
            label="Wirbelnde Verderbnis",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Den Wellen ausweichen.",
        ),
        AbilityRule(
            ability="Iron Star",
            label="Eiserner Stern",
            category=MECHANIC_MOVEMENT,
            severity="error",
            note="Der Bahn des Sterns ausweichen.",
        ),
        AbilityRule(
            ability="Malice",
            label="Bosheit",
            category=MECHANIC_POSITIONING,
            note="Vom Raid entfernt aufstellen.",
        ),
        AbilityRule(
            ability="Hellscream's Warsong",
            label="Höllschreis Kriegslied",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),
        AbilityRule(
            ability="Touch of Y'Shaarj",
            label="Berührung Y'Shaarjs",
            verdict=VERDICT_UNAVOIDABLE,
            category=MECHANIC_OTHER,
        ),

    ),

}


#
# --------------------------------------------------
# Übersetzungshilfe für bereits eingeordnete Bot-Zeilen
# --------------------------------------------------
#
# Der Bot schickt seine eigenen Mechanikfehler mit deutschem Text
# ("Ätzender Schlag nicht getankt"), der Analyzer leitet seine aus
# englischen Fähigkeitsnamen ab. Ohne diese Brücke stünde derselbe
# Fehler zweimal in der Liste - einmal je Quelle. Siehe
# analyzer.analysis.damage.merge_mechanics.
#
# Die Tabelle wird aus den `label`-Feldern oben **abgeleitet** und
# nicht von Hand gepflegt. Bei einer Handvoll Bosse wäre beides
# gleich gut; bei vierzehn Kämpfen mit über hundert Fähigkeiten
# würde eine zweite Liste unweigerlich auseinanderlaufen - und das
# Symptom wäre ein doppelt gezählter Fehler, den niemand als solchen
# erkennt.
#
# EXTRA_ALIASES fängt die Fälle ab, in denen der Bot eine andere
# Formulierung benutzt als das Label hier.
#

EXTRA_ALIASES: dict[str, str] = {
    "wirbel": "Swirl",
    "sha-pfütze": "Sha Puddle",
    "eisenstern": "Iron Star",
}


def _build_aliases() -> dict[str, str]:

    table: dict[str, str] = {}

    for rules in list(ENCOUNTER_ABILITIES.values()) + [GLOBAL_ABILITIES]:

        for rule in rules:

            if not rule.label:
                continue

            table.setdefault(rule.label.strip().lower(), rule.ability)

    table.update(EXTRA_ALIASES)

    return table


ABILITY_ALIASES: dict[str, str] = _build_aliases()


#
# --------------------------------------------------
# Index
# --------------------------------------------------
#
# Beim Import gebaut, damit jedes Nachschlagen ein Dict-Zugriff ist -
# dieselbe Bauart wie in analyzer.data.encounters.
#

_BY_ENCOUNTER: dict[str, dict[str, tuple[AbilityRule, ...]]] = {}

_GLOBAL_INDEX: dict[str, tuple[AbilityRule, ...]] = {}


def _index(rules: tuple[AbilityRule, ...]) -> dict[str, tuple[AbilityRule, ...]]:

    table: dict[str, list[AbilityRule]] = {}

    for rule in rules:

        table.setdefault(rule.ability.lower(), []).append(rule)

    return {key: tuple(value) for key, value in table.items()}


_GLOBAL_INDEX = _index(GLOBAL_ABILITIES)

for _encounter_name, _rules in ENCOUNTER_ABILITIES.items():

    _BY_ENCOUNTER[_encounter_name.lower()] = _index(_rules)


#
# --------------------------------------------------
# Öffentliche API
# --------------------------------------------------
#


def classify(
    encounter_name: str,
    ability: str,
    source_name: str = "",
) -> AbilityRule | None:
    """
    Die Regel zu einer Fähigkeit, oder None wenn keine hinterlegt ist.

    Reihenfolge: Bosstabelle vor globaler Tabelle, und innerhalb der
    Bosstabelle eine auf `source_name` eingeschränkte Regel vor der
    allgemeinen - derselbe Fähigkeitsname kann von mehreren Gegnern
    kommen.
    """

    key = (ability or "").strip().lower()

    if not key:
        return None

    for table in (
        _BY_ENCOUNTER.get((encounter_name or "").strip().lower(), {}),
        _GLOBAL_INDEX,
    ):

        candidates = table.get(key)

        if not candidates:
            continue

        if source_name:

            for candidate in candidates:

                if candidate.source_name == source_name:
                    return candidate

        for candidate in candidates:

            if not candidate.source_name:
                return candidate

        return candidates[0]

    return None


def verdict(
    encounter_name: str,
    ability: str,
    source_name: str = "",
    role: str = "",
) -> str:
    """
    Das Urteil zu einer Fähigkeit - VERDICT_UNKNOWN, wenn nichts
    hinterlegt ist.

    `role` erlaubt die Tank-Ausnahme: was für den Tank zum Job
    gehört, ist für ihn nicht vermeidbar.
    """

    rule = classify(encounter_name, ability, source_name)

    if rule is None:
        return VERDICT_UNKNOWN

    if rule.tank_exempt and role == "tank":
        return VERDICT_UNAVOIDABLE

    return rule.verdict


def is_avoidable(
    encounter_name: str,
    ability: str,
    source_name: str = "",
    role: str = "",
) -> bool:

    return verdict(encounter_name, ability, source_name, role) == VERDICT_AVOIDABLE


def mechanic_category(encounter_name: str, ability: str) -> str:
    """
    Der trainierbare Bereich, dem die Fähigkeit zugeordnet ist.
    """

    rule = classify(encounter_name, ability)

    if rule is None:
        return MECHANIC_OTHER

    return rule.category


def rules_for(encounter_name: str) -> tuple[AbilityRule, ...]:

    return ENCOUNTER_ABILITIES.get(
        _canonical_name(encounter_name),
        (),
    )


def known_encounters() -> tuple[str, ...]:
    """
    Kämpfe mit hinterlegten Referenzdaten - die Oberfläche kann damit
    erklären, warum eine Bewertung fehlt.
    """

    return tuple(sorted(ENCOUNTER_ABILITIES))


def alias_ability(text: str) -> str:
    """
    Der englische Fähigkeitsname zu einem deutschen Fehlertext des
    Bots, oder "" wenn keiner bekannt ist.
    """

    return ABILITY_ALIASES.get((text or "").strip().lower(), "")


def _canonical_name(encounter_name: str) -> str:
    """
    Die Original-Schreibweise eines Bossnamens, unabhängig von der
    Groß-/Kleinschreibung der Eingabe.
    """

    lowered = (encounter_name or "").strip().lower()

    for name in ENCOUNTER_ABILITIES:

        if name.lower() == lowered:
            return name

    return encounter_name or ""
