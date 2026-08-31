"""
Wertegewichte aus einem Sim - die reine Hälfte.

**Die Companion simmt nicht selbst, und das ist eine Entscheidung.**
Ein brauchbarer Sim wäre eine eigene Spielsimulation; einer, der nur
so aussieht, wäre schlimmer als keiner, weil seine Zahlen aussehen
wie echte. Dieselbe Linie, aus der es im Addon keinen Sim gibt (siehe
`modules/statweights.lua` drüben) und aus der der Rotationshelfer den
Tankspecs keine Prioritätenliste andichtet.

Gesimmt wird deshalb weiterhin auf [wowsims.com/mop] - die Companion
öffnet die Seite auf der **richtigen Spezialisierung** und nimmt das
Ergebnis wieder entgegen. Was sie beisteuert, ist der Weg dahinter,
und der fehlte: eine Sim-Ausgabe war bisher nur von Hand ins Spiel
zu bekommen, und dort auch nur über ein Eingabefeld, das man erst
finden muss.

Diese Datei ist die Stelle, an der etwas falsch sein kann, und
deshalb ist sie **rein**: kein Qt, kein `httpx`, keine Datei. Aus
demselben Grund wie `core/access_roles.build_profile_payload()`,
`core/raid_schedule.parse_schedule()` und `core/roster_target()`.
`tests/test_stat_weights.py` prüft sie ohne Fenster und ohne Netz.

DIESELBEN ZWEI LESEWEGE WIE IM ADDON, UND AUS DENSELBEN GRÜNDEN.

1. **Wertepaare** - ein Wertname, dann eine Zahl. Der Normalfall und
   der Weg für alles, was Namen im Text stehen hat: eine abgeschriebene
   Tabelle, eine JSON-Zeile, eine getippte Liste.
2. **Die Ausgabe von wowsims.com/mop** - eine lange Zeichenkette, in
   der die Gewichte als blosse Zahlenreihe stehen und die **Position**
   sagt, welcher Wert gemeint ist. Sie ist als einzige an *ein*
   fremdes Format gebunden, und genau deshalb muss sie **laut
   scheitern**: verschiebt der Sim seine Reihenfolge, bekäme jeder
   Wert lautlos das Gewicht eines anderen, und die Gewichtung sähe
   vollständig aus. Geprüft wird deshalb die Länge der Reihe, bevor
   ein einziger Wert übernommen wird.

Die Umsetzung ist bewusst die **Übersetzung** von
`modules/statweights.lua` und keine zweite Idee davon: derselbe Text,
hier eingefügt oder ingame, muss dieselben Zahlen ergeben. Wo die
beiden Dateien auseinanderlaufen, widersprechen sich Spiel und
Desktop bei einer Frage, die nur eine Antwort hat.

WAS NICHT ÜBERTRAGEN WIRD: DIE GRENZEN.

Die Sim-Ausgabe trägt neben den Gewichten die Caps (7,5 % Treffer,
15 % Waffenkunde). Eine Grenze ist eine Aussage über das **Spiel** und
keine Einstellung - sie gilt für jeden gleich und steht deshalb im
Spec-Profil des Addons. Die Companion **nennt** sie und schickt sie
nicht mit; weicht der Sim ab, ist das eine Datenfrage für einen
Menschen, dieselbe Haltung wie bei `WeintCodex_ValidateGemWeights()`.
Dasselbe gilt für die Klasse: sie wird gemeldet, damit auffällt, wenn
jemand die Ausgabe eines fremden Charakters eingefügt hat.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


#
# --------------------------------------------------
# Die Werte, um die es geht
# --------------------------------------------------
#
# Reihenfolge wie `SW.ORDER` und `WEIGHT_STATS` drüben, damit die
# Anzeige hier dieselbe ist wie die Felder im Spiel.
#

STAT_ORDER: tuple[str, ...] = (
    "strength",
    "agility",
    "intellect",
    "stamina",
    "spirit",
    "hit",
    "expertise",
    "crit",
    "haste",
    "mastery",
    "dodge",
    "parry",
)


STAT_LABELS: dict[str, str] = {
    "strength": "Stärke",
    "agility": "Beweglichkeit",
    "intellect": "Intelligenz",
    "stamina": "Ausdauer",
    "spirit": "Willenskraft",
    "hit": "Trefferwertung",
    "expertise": "Waffenkunde",
    "crit": "Kritische Trefferwertung",
    "haste": "Tempowertung",
    "mastery": "Meisterschaftswertung",
    "dodge": "Ausweichwertung",
    "parry": "Parierwertung",
}


#
# Jede Schreibweise, unter der ein Wert auftauchen kann. Wortgleich
# mit `NAMES` in `modules/statweights.lua` - wie eine Quelle ihre
# Werte nennt, ist nicht unsere Entscheidung, und zwei gepflegte
# Listen laufen auseinander (die Lehre aus `player_abilities.py`).
#

STAT_NAMES: dict[str, tuple[str, ...]] = {

    "strength": ("Strength", "Str", "Stärke", "Staerke"),
    "agility": ("Agility", "Agi", "Beweglichkeit"),
    "intellect": ("Intellect", "Int", "Intelligenz"),
    "stamina": ("Stamina", "Sta", "Ausdauer"),
    "spirit": ("Spirit", "Spi", "Willenskraft"),

    "hit": (
        "HitRating", "Hit", "SpellHitRating", "SpellHit",
        "MeleeHitRating", "RangedHitRating", "PhysicalHitRating",
        "Trefferwertung", "Treffer",
    ),
    "crit": (
        "CritRating", "Crit", "CriticalStrike", "CritChance",
        "SpellCritRating", "SpellCrit", "MeleeCritRating",
        "RangedCritRating", "PhysicalCritRating",
        "KritischeTrefferwertung", "Krit",
    ),
    "haste": (
        "HasteRating", "Haste", "SpellHasteRating", "SpellHaste",
        "MeleeHasteRating", "RangedHasteRating",
        "Tempowertung", "Tempo",
    ),
    "expertise": (
        "ExpertiseRating", "Expertise", "Exp",
        "Waffenkundewertung", "Waffenkunde",
    ),
    "mastery": (
        "MasteryRating", "Mastery", "Meisterschaftswertung",
        "Meisterschaft",
    ),
    "dodge": ("DodgeRating", "Dodge", "Ausweichwertung", "Ausweichen"),
    "parry": (
        "ParryRating", "Parry", "Parierwertung", "Parieren",
        "Parierchance",
    ),
}


def _lookup() -> dict[str, str]:

    table: dict[str, str] = {}

    for key, names in STAT_NAMES.items():

        for name in names:
            table[re.sub(r"\s+", "", name).lower()] = key

    return table


LOOKUP = _lookup()


#
# --------------------------------------------------
# Wohin der Knopf führt
# --------------------------------------------------
#
# Der Sim hat je Spezialisierung eine eigene Seite
# (`/mop/<klasse>/<spec>/`), und ein Knopf, der auf der Startseite
# landet, verlangt genau den Handgriff, den er abnehmen sollte.
#
# Die Zuordnung steht als **Tabelle** da und wird nicht aus dem
# Profilschlüssel abgeleitet: `HUNTER_BEASTMASTERY` wäre abgeleitet
# `beastmastery` und heisst dort `beast_mastery`, `DEATHKNIGHT`
# heisst `death_knight`. Eine Ableitung, die für zwei von 34
# Einträgen danebengreift, führt genau dort ins Leere, und ein toter
# Knopf ist von einer nicht simmbaren Spec nicht zu unterscheiden.
#
# Die fünf `*_OFFENSIVE`-Profile der Tanks (offensive Haltung) zeigen
# auf die Seite ihrer Basis-Spec: der Sim kennt keine zwei Haltungen,
# die Gewichte dieses Profils sind aber eigene.
#

BASE_URL = "https://www.wowsims.com/mop/"


@dataclass(frozen=True)
class SpecSim:
    """
    Eine Spezialisierung, wie das Addon sie führt - plus der Weg zu
    ihrer Seite im Sim.
    """

    key: str

    label: str

    class_token: str

    path: str

    @property
    def url(self) -> str:

        return BASE_URL + self.path + "/"


SPECS: tuple[SpecSim, ...] = (

    SpecSim("DEATHKNIGHT_BLOOD", "Blut", "DEATHKNIGHT", "death_knight/blood"),
    SpecSim("DEATHKNIGHT_FROST", "Frost", "DEATHKNIGHT", "death_knight/frost"),
    SpecSim("DEATHKNIGHT_UNHOLY", "Unheilig", "DEATHKNIGHT", "death_knight/unholy"),

    SpecSim("DRUID_BALANCE", "Gleichgewicht", "DRUID", "druid/balance"),
    SpecSim("DRUID_FERAL", "Wilder Kampf", "DRUID", "druid/feral"),
    SpecSim("DRUID_GUARDIAN", "Wächter", "DRUID", "druid/guardian"),
    SpecSim("DRUID_RESTORATION", "Wiederherstellung", "DRUID", "druid/restoration"),

    SpecSim("HUNTER_BEASTMASTERY", "Tierherrschaft", "HUNTER", "hunter/beast_mastery"),
    SpecSim("HUNTER_MARKSMANSHIP", "Treffsicherheit", "HUNTER", "hunter/marksmanship"),
    SpecSim("HUNTER_SURVIVAL", "Überleben", "HUNTER", "hunter/survival"),

    SpecSim("MAGE_ARCANE", "Arkan", "MAGE", "mage/arcane"),
    SpecSim("MAGE_FIRE", "Feuer", "MAGE", "mage/fire"),
    SpecSim("MAGE_FROST", "Frost", "MAGE", "mage/frost"),

    SpecSim("MONK_BREWMASTER", "Braumeister", "MONK", "monk/brewmaster"),
    SpecSim("MONK_MISTWEAVER", "Nebelwirker", "MONK", "monk/mistweaver"),
    SpecSim("MONK_WINDWALKER", "Windwandler", "MONK", "monk/windwalker"),

    SpecSim("PALADIN_HOLY", "Heilig", "PALADIN", "paladin/holy"),
    SpecSim("PALADIN_PROTECTION", "Schutz", "PALADIN", "paladin/protection"),
    SpecSim("PALADIN_RETRIBUTION", "Vergeltung", "PALADIN", "paladin/retribution"),

    SpecSim("PRIEST_DISCIPLINE", "Disziplin", "PRIEST", "priest/discipline"),
    SpecSim("PRIEST_HOLY", "Heilig", "PRIEST", "priest/holy"),
    SpecSim("PRIEST_SHADOW", "Schatten", "PRIEST", "priest/shadow"),

    SpecSim("ROGUE_ASSASSINATION", "Meucheln", "ROGUE", "rogue/assassination"),
    SpecSim("ROGUE_COMBAT", "Kampf", "ROGUE", "rogue/combat"),
    SpecSim("ROGUE_SUBTLETY", "Täuschung", "ROGUE", "rogue/subtlety"),

    SpecSim("SHAMAN_ELEMENTAL", "Elementar", "SHAMAN", "shaman/elemental"),
    SpecSim("SHAMAN_ENHANCEMENT", "Verstärkung", "SHAMAN", "shaman/enhancement"),
    SpecSim("SHAMAN_RESTORATION", "Wiederherstellung", "SHAMAN", "shaman/restoration"),

    SpecSim("WARLOCK_AFFLICTION", "Gebrechen", "WARLOCK", "warlock/affliction"),
    SpecSim("WARLOCK_DEMONOLOGY", "Dämonologie", "WARLOCK", "warlock/demonology"),
    SpecSim("WARLOCK_DESTRUCTION", "Zerstörung", "WARLOCK", "warlock/destruction"),

    SpecSim("WARRIOR_ARMS", "Waffen", "WARRIOR", "warrior/arms"),
    SpecSim("WARRIOR_FURY", "Furor", "WARRIOR", "warrior/fury"),
    SpecSim("WARRIOR_PROTECTION", "Schutz", "WARRIOR", "warrior/protection"),

    #
    # Die offensive Haltung der Tanks. Eigene Profile im Addon, also
    # eigene Gewichte - aber dieselbe Seite im Sim.
    #

    SpecSim(
        "DEATHKNIGHT_BLOOD_OFFENSIVE", "Blut (offensiv)",
        "DEATHKNIGHT", "death_knight/blood",
    ),
    SpecSim(
        "DRUID_GUARDIAN_OFFENSIVE", "Wächter (offensiv)",
        "DRUID", "druid/guardian",
    ),
    SpecSim(
        "MONK_BREWMASTER_OFFENSIVE", "Braumeister (offensiv)",
        "MONK", "monk/brewmaster",
    ),
    SpecSim(
        "PALADIN_PROTECTION_OFFENSIVE", "Schutz (offensiv)",
        "PALADIN", "paladin/protection",
    ),
    SpecSim(
        "WARRIOR_PROTECTION_OFFENSIVE", "Schutz (offensiv)",
        "WARRIOR", "warrior/protection",
    ),

)


SPEC_BY_KEY: dict[str, SpecSim] = {entry.key: entry for entry in SPECS}


CLASS_LABELS: dict[str, str] = {
    "DEATHKNIGHT": "Todesritter",
    "DRUID": "Druide",
    "HUNTER": "Jäger",
    "MAGE": "Magier",
    "MONK": "Mönch",
    "PALADIN": "Paladin",
    "PRIEST": "Priester",
    "ROGUE": "Schurke",
    "SHAMAN": "Schamane",
    "WARLOCK": "Hexenmeister",
    "WARRIOR": "Krieger",
}


def spec(key: str) -> SpecSim | None:
    """
    Die Spezialisierung zu einem Profilschlüssel, oder `None`.

    Ein unbekannter Schlüssel wird nicht geraten: eine erfundene
    Zuordnung führte auf die Seite einer fremden Spec, und deren
    Ergebnis sähe genauso aus wie das richtige.
    """

    return SPEC_BY_KEY.get((key or "").strip().upper())


def sim_url(key: str) -> str | None:
    """
    Die Sim-Seite dieser Spezialisierung, oder `None`.

    `None` heisst "wir wissen nicht, wohin" - der Aufrufer bietet dann
    die Startseite an und sagt es dazu, statt einen Knopf ins Leere
    zeigen zu lassen.
    """

    entry = spec(key)

    return entry.url if entry else None


def spec_label(key: str) -> str:

    entry = spec(key)

    return entry.label if entry else (key or "")


def class_label(token: str) -> str:

    return CLASS_LABELS.get((token or "").strip().upper(), token or "")


#
# --------------------------------------------------
# Weg 1: Wertepaare
# --------------------------------------------------
#

_NUMBER = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")


def _is_number(token: str) -> bool:

    return _NUMBER.match(token) is not None


def _decimal_shape(text: str) -> str:
    """
    ZUERST DAS KOMMA ZWISCHEN ZIFFERN, DANN ERST TRENNEN.

    Ein Komma trennt hier Wertepaare - es steht im Deutschen aber auch
    zwischen Vor- und Nachkommastelle und im Englischen vor den
    Tausendern. Wer "Krit 0,68" einfügt, bekäme sonst den Wert 0
    zugeschrieben und die 68 als unbekannten Rest: der Wert fällt
    still auf null, und genau das fällt niemandem auf.

    Entschieden wird am **ganzen Text**, nicht an der einzelnen
    Stelle. Steht irgendwo ein Punkt zwischen Ziffern, schreibt diese
    Quelle Nachkommastellen mit Punkt - dann ist ein Komma ein
    Tausendertrennzeichen. Steht nirgends einer, ist das Komma die
    Nachkommastelle.

    Das genügt, weil unten auf "grösstes Gewicht = 100" skaliert wird:
    es zählt nur das Verhältnis der Zahlen zueinander, und die Lesart
    muss bloss innerhalb eines Textes einheitlich sein.
    """

    if re.search(r"\d\.\d", text):

        for _ in range(4):

            shortened = re.sub(r"(\d),(\d\d\d)", r"\1\2", text)

            if shortened == text:
                break

            text = shortened

        return text

    return re.sub(r"(\d),(\d+)", r"\1.\2", text)


def parse_pairs(text: str) -> tuple[dict[str, float], list[str]] | None:
    """
    Rohe Gewichte aus beliebigem Text, plus die Namen, die vor einer
    Zahl standen und die wir nicht kennen.

    `None`, wenn nicht ein einziges Paar darin steht.
    """

    flat = _decimal_shape(text)

    flat = re.sub(r"[()\[\]{}\"']", " ", flat)

    flat = re.sub(r"[=:,;\t\r\n]", " ", flat)

    tokens = flat.split()

    weights: dict[str, float] = {}

    ignored: list[str] = []

    seen: set[str] = set()

    found = 0

    for index, token in enumerate(tokens):

        if not _is_number(token):
            continue

        value = float(token)

        one = tokens[index - 1] if index >= 1 else None

        two = (
            tokens[index - 2] + tokens[index - 1]
            if index >= 2
            else None
        )

        #
        # Der Name steht vor der Zahl und kann aus zwei Wörtern
        # bestehen ("Crit Rating"). Der längere gewinnt, sonst träfe
        # "Rating" nie zu.
        #

        key = None

        if two:
            key = LOOKUP.get(re.sub(r"\s+", "", two).lower())

        if key is None and one:
            key = LOOKUP.get(re.sub(r"\s+", "", one).lower())

        if key:

            #
            # Mehrere Schreibweisen desselben Werts (SpellHitRating
            # neben HitRating): die grössere gewinnt, statt sie zu
            # addieren - es ist derselbe Wert, nicht zwei.
            #

            if key not in weights or value > weights[key]:
                weights[key] = value

            found += 1

        elif one and one[:1].isalpha() and one not in seen:

            seen.add(one)

            ignored.append(one)

    if found == 0:
        return None

    return weights, ignored


#
# --------------------------------------------------
# Weg 2: die Ausgabe von wowsims.com/mop
# --------------------------------------------------
#
# Belegt an einer echten Ausgabe (Blut-Todesritter): Stärke 1 /
# Beweglichkeit 0 / Intelligenz 0 passt zur Klasse, und die Grenze auf
# Platz 8 lautet 5100 Wertung - 15 % Waffenkunde bei 340 Wertung je
# Prozent, also genau der Wert, den das Spec-Profil führt. Dieselbe
# Tabelle wie in `modules/statweights.lua`; sie darf hier und dort
# nicht auseinanderlaufen, und `tests/test_stat_weights.py` hält sie
# gegen die Lua-Datei.
#

SIM_STAT_KEY: dict[int, str] = {
    0: "strength", 1: "agility", 2: "stamina",
    3: "intellect", 4: "spirit",
    5: "hit", 6: "crit", 7: "haste",
    8: "expertise", 9: "dodge", 10: "parry", 11: "mastery",
}


SIM_STAT_NAME: dict[int, str] = {
    12: "Angriffskraft", 13: "Distanzangriffskraft",
    14: "Zaubermacht", 15: "PvP-Abhärtung", 16: "PvP-Macht",
    17: "Rüstung", 18: "Zusatzrüstung",
    19: "Gesundheit", 20: "Mana", 21: "Mana alle 5 Sek.",
}


SIM_STAT_COUNT = 22


SIM_PSEUDO_NAME: dict[int, str] = {
    0: "Waffenschaden (Haupthand)", 1: "Waffenschaden (Nebenhand)",
    2: "Waffenschaden (Distanz)",
    3: "Blockchance", 4: "Ausweichchance", 5: "Parierchance",
    6: "Angriffstempo", 7: "Distanzangriffstempo", 8: "Zauberzeit",
    9: "Nahkampftempo", 10: "Distanztempo", 11: "Zaubertempo",
    12: "Trefferchance (physisch)", 13: "Trefferchance (Zauber)",
    14: "Kritische Chance (physisch)", 15: "Kritische Chance (Zauber)",
}


SIM_PSEUDO_CAP: dict[int, tuple[str, str]] = {
    12: ("hit", "melee"),
    13: ("hit", "spell"),
}


SIM_PSEUDO_COUNT = 16


#
# Waffenkunde und Treffer rechnen auf Stufe 90 mit derselben Zahl. Sie
# steht so auch in `modules/charakter.lua`; hier ist sie nur dafür da,
# eine Wertungsgrenze für die Anzeige in Prozent umzurechnen - was der
# Client meldet, weiss nur das Spiel.
#

RATING_PER_PCT = 340.0


@dataclass(frozen=True)
class CapHint:
    """
    Eine Grenze, wie der Sim sie mitgibt. Wird **genannt und nicht
    angewendet** - siehe der Kopf dieser Datei.
    """

    stat: str

    kind: str = ""

    rating: float = 0.0

    pct: float = 0.0

    @property
    def percent(self) -> float:

        if self.pct:
            return self.pct

        return self.rating / RATING_PER_PCT if self.rating else 0.0


@dataclass
class Parsed:
    """
    Was aus einem eingefügten Text herausgelesen wurde.

    `problem` ist der einzige Fall, in dem `weights` leer bleibt - und
    er trägt immer einen Satz, der sagt, was zu tun ist.

    DREI ANTWORTEN AUF "WARUM STEHT DAS NICHT IN DER LISTE", UND SIE
    RATEN ZU VERSCHIEDENEM.

    Bis 2.5.0 gab es dafür eine einzige Liste mit der Überschrift
    "kennt WeintCodex nicht" - und die war für den häufigsten Fall
    schlicht falsch. Angriffskraft und Waffenschaden kennt es sehr
    wohl; sie lassen sich nur nicht sockeln, verzaubern oder
    umschmieden, also gäbe es hier nichts, was ein Gewicht darauf
    steuern könnte. Der Satz las sich wie eine Lücke in unseren
    Tabellen, die jemand schliessen müsste, und genau so wurde er
    gemeldet.

    * `unusable` - ein echtes Gewicht auf einem Wert, den keine der
      drei Entscheidungen bewegen kann. Nichts zu tun.
    * `unknown` - ein Name, den wir nicht zuordnen konnten. Das ist
      der Fall, der eine Meldung wert ist.
    * `zeroed` - ein Wert, den die Quelle **mit null** gewichtet hat.
      Er fehlt in der Liste, und ohne diese Auskunft ist das von
      "verlorengegangen" nicht zu unterscheiden - dieselbe Linie wie
      `stars == 0` im Analyzer. Nur der Sim führt sie, denn seine
      Ausgabe trägt immer alle 22 Werte; eine getippte Paarliste sagt
      über einen Wert, der nicht darin steht, gar nichts.
    """

    weights: dict[str, float] = field(default_factory=dict)

    unusable: list[str] = field(default_factory=list)

    unknown: list[str] = field(default_factory=list)

    zeroed: list[str] = field(default_factory=list)

    caps: list[CapHint] = field(default_factory=list)

    caps_ignored: list[str] = field(default_factory=list)

    #
    # Schwellen, die im Sim von Hand gesetzt wurden
    # (`breakpointLimits`). Wie die Grenzen: genannt, nicht
    # angewendet - die Tempo-Treppe rechnet das Addon selbst aus
    # zwei Zahlen je Effekt aus (`data/breakpoints.lua`), und eine
    # abgeschriebene Wunschzahl wäre genau die Handpflege, gegen die
    # jene Datei geschrieben ist. Bis 2.5.0 fiel dieser dritte Block
    # der Ausgabe still unter den Tisch.
    #

    limits: list[str] = field(default_factory=list)

    sim_class: str = ""

    source: str = ""

    problem: str = ""

    @property
    def ok(self) -> bool:

        return bool(self.weights) and not self.problem


def looks_like_sim(text: str) -> bool:

    if not isinstance(text, str):
        return False

    if '"epWeightsStats"' in text:
        return True

    return '"reforgeSettings"' in text and '"player"' in text


def _sim_array(text: str, section: str, field_name: str) -> list[float] | None:
    """
    Die Zahlenreihe `field_name` innerhalb des Abschnitts `section`.

    Gesucht wird **ab** dem Abschnitt, damit "stats" nicht das
    erstbeste Vorkommen im ganzen Text trifft; das führende
    Anführungszeichen im Muster trennt dabei "stats" von
    "pseudoStats".

    Ein Feld, das keine reine Zahl ist, macht die ganze Reihe ungültig,
    statt eine 0 zu erfinden: eine 0 an falscher Stelle ist genau die
    stille Falschauskunft, gegen die die Längenprüfung steht.
    """

    start = text.find('"' + section + '"')

    if start < 0:
        return None

    match = re.compile(r'"' + re.escape(field_name) + r'"\s*:\s*\[').search(
        text,
        start,
    )

    if not match:
        return None

    close = text.find("]", match.end())

    if close < 0:
        return None

    out: list[float] = []

    body = text[match.end():close].strip()

    if not body:
        return out

    for token in body.split(","):

        token = token.strip()

        try:
            out.append(float(token))

        except ValueError:
            return None

    return out


def _sim_class(text: str) -> str:

    match = re.search(r'"class"\s*:\s*"Class(\w+)"', text)

    return match.group(1).upper() if match else ""


def parse_sim(text: str) -> Parsed:
    """
    Die Ausgabe von wowsims.com/mop.

    Die Länge der Zahlenreihe entscheidet, ob wir diese Ausgabe
    überhaupt verstehen. Zählt der Sim anders, wird **nichts** geraten.
    """

    stats = _sim_array(text, "epWeightsStats", "stats")

    if stats is None:

        return Parsed(problem=(
            "Das sieht nach einer Sim-Ausgabe aus, trägt aber keine "
            "Wertegewichte. Im Sim erst rechnen lassen (Suggest "
            "Reforges bzw. die Werteberechnung), dann exportieren."
        ))

    if len(stats) != SIM_STAT_COUNT:

        return Parsed(problem=(
            f"Diese Sim-Ausgabe zählt {len(stats)} Werte, WeintCompanion "
            f"kennt die Reihenfolge von {SIM_STAT_COUNT}. Damit ist nicht "
            "mehr sicher, welche Zahl zu welchem Wert gehört — und eine "
            "falsch zugeordnete Gewichtung sieht vollständig aus. Bitte "
            "melden."
        ))

    weights: dict[str, float] = {}

    unusable: list[str] = []

    unknown: list[str] = []

    zeroed: list[str] = []

    for index, value in enumerate(stats):

        key = SIM_STAT_KEY.get(index)

        if key:

            if value != 0:
                weights[key] = value

            else:

                #
                # Der Sim führt immer alle 22 Werte, also ist eine Null
                # hier eine Aussage: "bringt diesem Charakter nichts".
                # Sie muss gesagt werden - sonst verschwindet der Wert
                # aus der Liste, und das ist von "die App hat ihn
                # verloren" nicht zu unterscheiden.
                #

                zeroed.append(key)

        elif value != 0:

            name = SIM_STAT_NAME.get(index)

            if name:
                unusable.append(name)

            else:
                unknown.append(f"Feld {index}")

    pseudo = _sim_array(text, "epWeightsStats", "pseudoStats")

    if pseudo is not None and len(pseudo) == SIM_PSEUDO_COUNT:

        for index, value in enumerate(pseudo):

            if value == 0:
                continue

            name = SIM_PSEUDO_NAME.get(index)

            if name:
                unusable.append(name)

            else:
                unknown.append(f"Abgeleitetes Feld {index}")

    if not weights:

        return Parsed(problem=(
            "In dieser Sim-Ausgabe steht kein einziges Gewicht über null. "
            "Im Sim erst die Wertegewichte ausrechnen lassen."
        ))

    caps, caps_ignored = _sim_caps(text)

    return Parsed(
        weights=weights,
        unusable=unusable,
        unknown=unknown,
        zeroed=zeroed,
        caps=caps,
        caps_ignored=caps_ignored,
        limits=_sim_limits(text),
        sim_class=_sim_class(text),
        source="sim",
    )


def _sim_caps(text: str) -> tuple[list[CapHint], list[str]]:
    """
    Die Grenzen der Ausgabe.

    Waffenkunde steht dort als **Wertung** (5100), die Trefferchance
    als **Prozent** (7,5). Beides bleibt so, wie es dasteht;
    umgerechnet wird erst für die Anzeige.
    """

    caps: list[CapHint] = []

    ignored: list[str] = []

    cap_stats = _sim_array(text, "statCaps", "stats")

    if cap_stats is not None and len(cap_stats) == SIM_STAT_COUNT:

        for index, value in enumerate(cap_stats):

            if value <= 0:
                continue

            key = SIM_STAT_KEY.get(index)

            if key:
                caps.append(CapHint(stat=key, rating=value))

            else:
                ignored.append(SIM_STAT_NAME.get(index, f"Feld {index}"))

    cap_pseudo = _sim_array(text, "statCaps", "pseudoStats")

    if cap_pseudo is not None and len(cap_pseudo) != SIM_PSEUDO_COUNT:

        #
        # Dieselbe Überlegung wie bei der Länge oben, nur mit milderer
        # Folge: eine Grenze wird hier ohnehin nur genannt. Sie
        # stillschweigend wegzulassen wäre trotzdem falsch - dann
        # fehlte sie, und niemand wüsste warum.
        #

        ignored.append("abgeleitete Werte (Reihenfolge passt nicht)")

    elif cap_pseudo is not None:

        for index, value in enumerate(cap_pseudo):

            if value <= 0:
                continue

            mapped = SIM_PSEUDO_CAP.get(index)

            if mapped:
                caps.append(CapHint(stat=mapped[0], kind=mapped[1], pct=value))

            else:
                ignored.append(SIM_PSEUDO_NAME.get(index, f"Feld {index}"))

    return caps, ignored


def _sim_limits(text: str) -> list[str]:
    """
    Die Schwellen, die jemand im Sim von Hand gesetzt hat.

    Genannt und nicht angewendet, aus demselben Grund wie die Grenzen:
    die Tempo-Treppe rechnet das Addon aus Laufzeit und Grundtickabstand
    selbst aus, und eine abgeschriebene Wunschzahl gilt immer nur für
    eine Ausrüstungsstufe und eine Buffkombination.

    Bis 2.5.0 wurde dieser dritte Block der Ausgabe gar nicht gelesen -
    also fiel er still unter den Tisch, und das ist genau der Ausgang,
    gegen den der Rest dieser Datei geschrieben ist.
    """

    out: list[str] = []

    stats = _sim_array(text, "breakpointLimits", "stats")

    if stats is not None and len(stats) == SIM_STAT_COUNT:

        for index, value in enumerate(stats):

            if value <= 0:
                continue

            key = SIM_STAT_KEY.get(index)

            label = (
                STAT_LABELS.get(key, key)
                if key
                else SIM_STAT_NAME.get(index, f"Feld {index}")
            )

            out.append(f"{label} {value:g}")

    pseudo = _sim_array(text, "breakpointLimits", "pseudoStats")

    if pseudo is not None and len(pseudo) == SIM_PSEUDO_COUNT:

        for index, value in enumerate(pseudo):

            if value <= 0:
                continue

            label = SIM_PSEUDO_NAME.get(index, f"Feld {index}")

            out.append(f"{label} {value:g}")

    return out


def parse(text: str) -> Parsed:
    """
    Der Einstieg: welcher der beiden Wege gilt.

    Eine Sim-Ausgabe wird als Sim-Ausgabe gelesen oder gar nicht. Auf
    den Paarleser auszuweichen hiesse, aus Schlüsselnamen und Zahlen
    eine Gewichtung zu bauen, die niemand so gemeint hat.
    """

    if not isinstance(text, str) or not text.strip():
        return Parsed(problem="Da steht nichts.")

    if looks_like_sim(text):
        return parse_sim(text)

    result = parse_pairs(text)

    if result is None:

        return Parsed(problem=(
            "Darin steht kein einziges Wertepaar. Erwartet wird die "
            "Ausgabe von wowsims — oder ein Wertname und eine Zahl: "
            "Beweglichkeit 100, CritRating=0.55, eine Zeile je Wert."
        ))

    weights, unknown = result

    #
    # Hier ist "kennt WeintCodex nicht" die richtige Auskunft: vor der
    # Zahl stand ein Name, und den konnten wir nicht zuordnen. Anders
    # als bei der Sim-Ausgabe wissen wir nicht, was gemeint war.
    #

    return Parsed(weights=weights, unknown=unknown, source="pairs")


#
# --------------------------------------------------
# Auf die Skala des Addons bringen
# --------------------------------------------------
#
# Sims geben Gewichte relativ heraus: der Primärwert steht auf 1.0,
# alles andere darunter. Die Spec-Profile führen denselben Gedanken
# mit 100 für den Primärwert, und die Eingabefelder im Spiel nehmen
# ganze Zahlen von 0 bis 999.
#
# Das ist ausdrücklich **keine Wertung**, sondern ein Maßstabswechsel:
# welche Werte wie zueinander stehen, ändert sich dabei nicht - und
# genau darauf kommt es an, denn alle drei Seiten im Spiel vergleichen
# Gewichte nur untereinander.
#

TOP = 100

MAX_WEIGHT = 999


def normalize(raw: dict[str, float]) -> tuple[dict[str, int], list[str]]:
    """
    Rohe Gewichte auf "grösstes Gewicht = 100".

    NEGATIVE GEWICHTE WERDEN 0, NICHT VERSCHWIEGEN. Manche Skalen
    setzen einen Wert auf -1, um ihn zu meiden; die Skala des Addons
    kennt kein "meiden", nur "egal". Der Aufrufer bekommt die Liste
    und sagt es dazu.
    """

    if not raw:
        return {}, []

    top = 0.0

    negatives: list[str] = []

    for key in STAT_ORDER:

        if key not in raw:
            continue

        value = raw[key]

        if value < 0:
            negatives.append(key)

        if value > top:
            top = value

    if top <= 0:
        return {}, negatives

    out: dict[str, int] = {}

    for key, value in raw.items():

        scaled = int((value / top) * TOP + 0.5)

        scaled = max(0, min(MAX_WEIGHT, scaled))

        if scaled > 0:
            out[key] = scaled

    return out, negatives


#
# --------------------------------------------------
# Was ins Spiel geht
# --------------------------------------------------
#


@dataclass(frozen=True)
class WeightSet:
    """
    Eine fertige Gewichtung, so wie sie abgelegt und zugestellt wird.

    `spec_key` ist der Profilschlüssel des Addons - er entscheidet
    dort, für welche Spezialisierung der Vorschlag gilt. Ohne ihn
    liesse sich die Gewichtung keinem Profil zuordnen, und eine zu
    raten wäre genau der Fehler, den `analyzer/names.py` an anderer
    Stelle abgestellt hat.
    """

    spec_key: str

    weights: dict[str, int]

    character: str = ""

    realm: str = ""

    source: str = "sim"

    created: int = 0

    note: str = ""

    @property
    def id(self) -> str:
        """
        Die Kennung dieses Vorschlags.

        Sie entscheidet im Spiel darüber, ob ein Vorschlag **neu** ist:
        einen, den der Spieler übernommen oder verworfen hat, darf die
        nächste Zustellung nicht erneut anbieten - sonst stünde nach
        jedem Login dieselbe Frage wieder da.

        Deshalb hängt sie am Inhalt und nicht an der Uhrzeit allein:
        zweimal dieselbe Gewichtung ist derselbe Vorschlag.
        """

        parts = [self.spec_key]

        for key in STAT_ORDER:

            if key in self.weights:
                parts.append(f"{key}={self.weights[key]}")

        digest = hashlib.sha1(
            "|".join(parts).encode("utf-8"),
        ).hexdigest()

        return digest[:12]


def ordered(weights: dict[str, int]) -> list[tuple[str, int]]:
    """
    Die Gewichte in der Reihenfolge, in der das Spiel sie anzeigt.
    """

    return [
        (key, weights[key])
        for key in STAT_ORDER
        if weights.get(key)
    ]


#
# Die drei Zeichen, mit denen der Übertragungsstring gliedert. Was
# hineingerät, wird ersetzt - ein Charaktername kommt aus dem Spiel
# und könnte die Struktur sonst zerlegen (dieselbe Regel wie
# `CleanField()` im Addon).
#

_UNSAFE = re.compile(r"[:|,~\r\n\\\"]")


def clean_field(value: str) -> str:

    return _UNSAFE.sub(" ", (value or "")).strip()


def build_transfer(entry: WeightSet) -> str:
    """
    Der Übertragungsstring für den Import im Spiel.

        WCIMPORT:SW:<Profilschlüssel>:<Kennung>:<Zeitstempel>:<Charakter>:<Quelle>:<stat>|<wert>,...

    Er ist der Weg **ohne** `/reload`: die Zustellung über die
    Addon-Brücke wird erst beim nächsten Laden gelesen (WoW liest
    seine SavedVariables zur Laufzeit nicht erneut), ein eingefügter
    String dagegen sofort.

    Die Form ist die der übrigen Importe (`WCIMPORT:<TYP>:<Nutzlast>`,
    Abschnitte mit `:`, Datensätze mit `,`, Felder mit `|`) - ein
    zweites Format neben den fünf bestehenden wäre ein zweiter Parser
    im Addon.
    """

    pairs = ",".join(
        f"{key}|{value}"
        for key, value in ordered(entry.weights)
    )

    fields = [
        clean_field(entry.spec_key),
        entry.id,
        str(int(entry.created or 0)),
        clean_field(entry.character),
        clean_field(entry.source or "sim"),
        pairs,
    ]

    return "WCIMPORT:SW:" + ":".join(fields)


def payload(entries) -> dict:
    """
    Die Nutzlast der Inbox-Nachricht `stat_weights`.

    Zugestellt wird **immer die ganze Liste**, aus demselben Grund wie
    bei der WeakAura-Bibliothek: das Addon ersetzt seine Ablage damit,
    und eine gelöschte Gewichtung verschwindet allein dadurch, dass
    sie in der nächsten Zustellung fehlt.

    Die Grenzen aus der Sim-Ausgabe sind bewusst **nicht** dabei: sie
    stehen im Spec-Profil des Addons und gelten für jeden gleich.
    """

    return {
        "version": 1,
        "sets": [
            {
                "id": entry.id,
                "spec": entry.spec_key,
                "character": entry.character,
                "realm": entry.realm,
                "source": entry.source or "sim",
                "created": int(entry.created or 0),
                "weights": dict(entry.weights),
            }
            for entry in entries
        ],
    }
