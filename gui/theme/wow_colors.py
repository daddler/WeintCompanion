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
# Klassenwappen
# --------------------------------------------------
#
# Der Dateiname unter `resources/icons/`, ohne Endung. Die Symbole
# sind **eigene Zeichnungen** und keine Blizzard-Grafik: die
# Klassensymbole des Spiels liegen in CASC und nicht als Datei vor,
# und eine Kopie wäre fremdes Material im Installationspaket.
#
# Der Schlüssel ist wieder der englische Anzeigename, damit dieselbe
# Normalisierung wie bei Farbe und Bezeichnung greift - das Addon
# meldet `PALADIN`, WarcraftLogs "Paladin".
#

CLASS_ICONS: dict[str, str] = {

    "Death Knight": "class_deathknight",
    "Druid": "class_druid",
    "Hunter": "class_hunter",
    "Mage": "class_mage",
    "Monk": "class_monk",
    "Paladin": "class_paladin",
    "Priest": "class_priest",
    "Rogue": "class_rogue",
    "Shaman": "class_shaman",
    "Warlock": "class_warlock",
    "Warrior": "class_warrior",

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


#
# --------------------------------------------------
# Die zweite Schreibweise: WoWs classFile
# --------------------------------------------------
#
# Die Tabellen oben sind auf den englischen Anzeigenamen geschlüsselt
# ("Death Knight"), wie ihn Combat-Log und WarcraftLogs liefern. Das
# Addon meldet stattdessen `UnitClass()`s zweiten Rückgabewert -
# grossgeschrieben und ohne Leerzeichen ("DEATHKNIGHT"). Beides ist
# dieselbe Klasse; ohne diese Zuordnung wäre jeder ingame gemeldete
# Charakter grau, was wie "unbekannte Klasse" aussieht statt wie
# "andere Schreibweise".
#

CLASS_FILE_NAMES: dict[str, str] = {
    name.upper().replace(" ", ""): name
    for name in CLASS_COLORS
}


#
# --------------------------------------------------
# Die dritte Schreibweise: die deutsche
# --------------------------------------------------
#
# Der Bot fuehrt seine Anmeldungen auf Deutsch - "Todesritter",
# "Mönch", so wie es in den Auswahlmenues von Discord steht. Er
# uebersetzt sie zwar, bevor er sie schickt, aber diese Tabelle ist
# billig und die Alternative teuer: eine Klasse, die hier nicht
# ankommt, ist in der Aufstellung grau, und Grau heisst dort "Klasse
# nicht gemeldet". Der Unterschied zwischen "andere Schreibweise" und
# "keine Angabe" ist genau der, den `class_icon()` mit seinem `None`
# zieht - additiv gedacht wie `player_abilities`: ein fehlender
# Eintrag kostet die Zuordnung, er erfindet keine.
#
# Der Schluessel ist grossgeschrieben und ohne Umlaut-Sonderfaelle
# nachgeschlagen, damit "Mönch" und "MÖNCH" dasselbe treffen.
#

CLASS_GERMAN_NAMES: dict[str, str] = {
    label.upper(): name
    for name, label in CLASS_LABELS.items()
}


def normalize_class(class_name: str) -> str:
    """
    Alle drei Schreibweisen auf den englischen Anzeigenamen bringen.
    Was keine von ihnen ist, bleibt unverändert - dieselbe Regel wie
    bei unbekannten Spezialisierungen im Analyzer.
    """

    class_name = (class_name or "").strip()

    if class_name in CLASS_COLORS:
        return class_name

    key = class_name.upper()

    if key in CLASS_GERMAN_NAMES:
        return CLASS_GERMAN_NAMES[key]

    return CLASS_FILE_NAMES.get(
        key.replace(" ", ""),
        class_name,
    )


# --------------------------------------------------


def class_color(class_name: str) -> str:
    """
    Klassenfarbe, oder die neutrale Textfarbe bei unbekannter Klasse.
    """

    return CLASS_COLORS.get(
        normalize_class(class_name),
        Colors.TEXT_SECONDARY,
    )


def class_label(class_name: str) -> str:
    """
    Deutsche Klassenbezeichnung, sonst der Originalname.
    """

    class_name = normalize_class(class_name)

    return CLASS_LABELS.get(class_name, class_name)


def class_icon(class_name: str) -> str | None:
    """
    Der Name des Klassenwappens, oder `None` bei unbekannter Klasse.

    `None` heißt hier "keine Angabe", nicht "kein Wappen vorhanden" -
    dieselbe Unterscheidung wie überall sonst im Projekt. Der Aufrufer
    zeichnet dafür ein neutrales Zeichen und behauptet keine Klasse,
    die er nicht kennt.
    """

    return CLASS_ICONS.get(normalize_class(class_name))


def role_label(role: str) -> str:

    return ROLE_LABELS.get(role, role)


def role_color(role: str) -> str:

    return ROLE_COLORS.get(role, Colors.TEXT_SECONDARY)
