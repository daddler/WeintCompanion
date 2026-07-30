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

Erweitern: einen Eintrag in ENCOUNTER_ABILITIES ergänzen. Die
Fähigkeitsnamen sind die *englischen* aus dem Combat-Log bzw. der
WarcraftLogs-Antwort, `label`/`note` sind der deutsche Text für die
Oberfläche.
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
# vorführbar. Immerseus steht hier, weil der Bot für genau diesen
# Kampf schon eine eigene Regel mitschickt: so wird das
# Zusammenführen beider Quellen tatsächlich durchlaufen.
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

ABILITY_ALIASES: dict[str, str] = {
    "ätzender schlag": "Corrosive Blast",
    "dreifacher stich": "Triple Puncture",
    "wirbel": "Swirl",
    "zerfetzender ansturm": "Rending Charge",
    "doppelhieb": "Double Swipe",
    "loderndes sonnenlicht": "Blazing Sunlight",
    "giftbolzensalve": "Venom Bolt Volley",
    "tödliche seuche": "Deadly Plague",
    "sha-pfütze": "Sha Puddle",
}


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
