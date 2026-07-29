"""
Klassenfarben von World of Warcraft.

Gehört ins Theme und nicht in den Analyzer: es ist eine reine
Darstellungsentscheidung. Der Analyzer liefert den Klassennamen, die
Oberfläche entscheidet, wie er aussieht.

Enthalten sind genau die elf Klassen von Mists of Pandaria - der
Mönch ist dabei, spätere Klassen bewusst nicht.
"""

from __future__ import annotations

from gui.theme.colors import Colors


#
# --------------------------------------------------
# Farben
# --------------------------------------------------
#
# Schlüssel ist der englische Klassenname, wie er im Combat-Log und
# in analyzer.models.Actor.class_name steht.
#

CLASS_COLORS: dict[str, str] = {

    "Death Knight": "#C41F3B",
    "Druid": "#FF7D0A",
    "Hunter": "#ABD473",
    "Mage": "#69CCF0",
    "Monk": "#00FF96",
    "Paladin": "#F58CBA",
    "Priest": "#FFFFFF",
    "Rogue": "#FFF569",
    "Shaman": "#0070DE",
    "Warlock": "#9482C9",
    "Warrior": "#C79C6E",

}


#
# --------------------------------------------------
# Deutsche Bezeichnungen
# --------------------------------------------------
#

CLASS_LABELS: dict[str, str] = {

    "Death Knight": "Todesritter",
    "Druid": "Druide",
    "Hunter": "Jäger",
    "Mage": "Magier",
    "Monk": "Mönch",
    "Paladin": "Paladin",
    "Priest": "Priester",
    "Rogue": "Schurke",
    "Shaman": "Schamane",
    "Warlock": "Hexenmeister",
    "Warrior": "Krieger",

}


#
# --------------------------------------------------
# Rollen
# --------------------------------------------------
#

ROLE_LABELS: dict[str, str] = {

    "tank": "Tank",
    "healer": "Heiler",
    "dps": "Schaden",

}


ROLE_COLORS: dict[str, str] = {

    "tank": Colors.INFO,
    "healer": Colors.SUCCESS,
    "dps": Colors.WARNING,

}


# --------------------------------------------------


def class_color(class_name: str) -> str:
    """
    Klassenfarbe, oder die neutrale Textfarbe bei unbekannter Klasse.
    """

    return CLASS_COLORS.get(class_name, Colors.TEXT_SECONDARY)


def class_label(class_name: str) -> str:
    """
    Deutsche Klassenbezeichnung, sonst der Originalname.
    """

    return CLASS_LABELS.get(class_name, class_name)


def role_label(role: str) -> str:

    return ROLE_LABELS.get(role, role)


def role_color(role: str) -> str:

    return ROLE_COLORS.get(role, Colors.TEXT_SECONDARY)
