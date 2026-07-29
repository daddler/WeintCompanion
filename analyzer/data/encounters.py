"""
Referenzdaten zu den Raid-Encountern von Mists of Pandaria Classic.

Bewusste Design-Entscheidung: nachgeschlagen wird über den
Encounter-NAMEN, nicht über die Encounter-ID.

Grund: der ENCOUNTER_START-Eintrag des Combat-Logs liefert Name,
Schwierigkeit und Gruppengröße bereits mit. Der Name ist damit die
verlässliche Information, die ohnehin vorliegt - eine eigene
ID-Tabelle wäre eine zweite Wahrheit, die bei jedem Patch
auseinanderlaufen kann. Diese Tabelle ergänzt deshalb nur, was das
Log NICHT mitliefert: zu welcher Instanz ein Boss gehört und in
welcher Reihenfolge er dort steht.

Unbekannte Bosse (z. B. aus einem künftigen Patch) sind kein
Fehlerfall: `lookup()` gibt dann einen EncounterInfo mit leerer
Instanz zurück, und die Oberfläche zeigt schlicht den Namen aus dem
Log an.
"""

from __future__ import annotations

from analyzer.models import EncounterInfo


#
# --------------------------------------------------
# Instanzen
# --------------------------------------------------
#

MOGUSHAN_VAULTS = "Mogu'shan-Schatzkammer"
HEART_OF_FEAR = "Herz der Angst"
TERRACE = "Terrasse des Endlosen Frühlings"
THRONE_OF_THUNDER = "Thron des Donners"
SIEGE_OF_ORGRIMMAR = "Belagerung von Orgrimmar"


#
# Reihenfolge der Bosse je Instanz, in Pull-Reihenfolge.
#

INSTANCE_ENCOUNTERS: dict[str, tuple[str, ...]] = {

    MOGUSHAN_VAULTS: (
        "The Stone Guard",
        "Feng the Accursed",
        "Gara'jal the Spiritbinder",
        "The Spirit Kings",
        "Elegon",
        "Will of the Emperor",
    ),

    HEART_OF_FEAR: (
        "Imperial Vizier Zor'lok",
        "Blade Lord Ta'yak",
        "Garalon",
        "Wind Lord Mel'jarak",
        "Amber-Shaper Un'sok",
        "Grand Empress Shek'zeer",
    ),

    TERRACE: (
        "Protectors of the Endless",
        "Tsulong",
        "Lei Shi",
        "Sha of Fear",
    ),

    THRONE_OF_THUNDER: (
        "Jin'rokh the Breaker",
        "Horridon",
        "Council of Elders",
        "Tortos",
        "Megaera",
        "Ji-Kun",
        "Durumu the Forgotten",
        "Primordius",
        "Dark Animus",
        "Iron Qon",
        "Twin Consorts",
        "Lei Shen",
        "Ra-den",
    ),

    SIEGE_OF_ORGRIMMAR: (
        "Immerseus",
        "The Fallen Protectors",
        "Norushen",
        "Sha of Pride",
        "Galakras",
        "Iron Juggernaut",
        "Kor'kron Dark Shaman",
        "General Nazgrim",
        "Malkorok",
        "Spoils of Pandaria",
        "Thok the Bloodthirsty",
        "Siegecrafter Blackfuse",
        "Paragons of the Klaxxi",
        "Garrosh Hellscream",
    ),

}


#
# Umgekehrter Index: Bossname (kleingeschrieben) -> (Instanz, Position)
#

_BY_NAME: dict[str, tuple[str, int]] = {}

for _instance, _bosses in INSTANCE_ENCOUNTERS.items():

    for _position, _boss in enumerate(_bosses, start=1):

        _BY_NAME[_boss.lower()] = (_instance, _position)


#
# --------------------------------------------------
# Schwierigkeitsgrade
# --------------------------------------------------
#
# Die difficultyID aus ENCOUNTER_START. Nur die für MoP relevanten
# Werte sind hinterlegt; alles andere fällt auf einen generischen
# Text zurück, statt eine falsche Bezeichnung zu behaupten.
#

DIFFICULTY_NAMES: dict[int, str] = {

    3: "10 Normal",
    4: "25 Normal",
    5: "10 Heroisch",
    6: "25 Heroisch",
    7: "Schlachtzugsbrowser",

}


def difficulty_name(difficulty_id: int) -> str:

    return DIFFICULTY_NAMES.get(
        difficulty_id,
        f"Schwierigkeit {difficulty_id}",
    )


#
# --------------------------------------------------
# Nachschlagen
# --------------------------------------------------
#


def instance_for(name: str) -> str:
    """
    Instanzname zu einem Boss, oder "" wenn unbekannt.
    """

    entry = _BY_NAME.get(name.strip().lower())

    if entry is None:
        return ""

    return entry[0]


def position_for(name: str) -> int:
    """
    Position des Bosses innerhalb seiner Instanz (1-basiert),
    oder 0 wenn unbekannt.
    """

    entry = _BY_NAME.get(name.strip().lower())

    if entry is None:
        return 0

    return entry[1]


def lookup(
    encounter_id: int,
    name: str,
    difficulty_id: int = 0,
    raid_size: int = 0,
) -> EncounterInfo:
    """
    Baut aus den Rohangaben eines ENCOUNTER_START-Eintrags einen
    EncounterInfo und ergänzt die Instanz aus der Tabelle oben.
    """

    return EncounterInfo(
        encounter_id=encounter_id,
        name=name,
        instance=instance_for(name),
        difficulty=(
            difficulty_name(difficulty_id)
            if difficulty_id
            else ""
        ),
        raid_size=raid_size,
    )


def all_encounter_names() -> tuple[str, ...]:
    """
    Alle bekannten Bossnamen in Instanz- und Pull-Reihenfolge.
    Wird von der Academy für Boss-bezogene Lerninhalte genutzt.
    """

    names: list[str] = []

    for bosses in INSTANCE_ENCOUNTERS.values():

        names.extend(bosses)

    return tuple(names)
