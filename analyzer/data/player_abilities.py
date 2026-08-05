"""
Spielerfähigkeiten in beiden Sprachen.

Der Lektionskatalog nennt Fähigkeiten **englisch** ("Avenging Wrath",
"Shield Block") - das ist die Schreibweise, in der sie überall
dokumentiert sind und in der der Bot sie idealerweise liefert.
WarcraftLogs gibt Fähigkeitsnamen aber in der Sprache des Clients
zurück, der den Bericht hochgeladen hat: bei einer deutschen Gilde
steht dort "Zorn des Rächers" und "Schildblock". Genau dieser Fehler
hat schon einmal dafür gesorgt, dass sämtliche Cooldown-Listen leer
ankamen (siehe docs/warcraftlogs-bridge.md, "Warum die v2-Felder leer
ankamen") - dort ist er auf der Bot-Seite behoben worden, hier
passiert dasselbe für die Prüfkriterien der Academy.

Ohne diese Tabelle wäre jedes Kriterium, das eine bestimmte Fähigkeit
nennt, in einem deutschen Log dauerhaft "keine Daten" - ohne Fehler,
ohne Warnung, und in der Oberfläche nicht davon zu unterscheiden, dass
der Bot den Block gar nicht liefert.

Drei Regeln, nach denen diese Tabelle gepflegt wird:

* **Sie ist additiv.** Ein fehlender Eintrag kostet einen Treffer, er
  erfindet keinen. Wer eine Fähigkeit vermisst, trägt sie nach; nichts
  anderes im System hängt davon ab.
* **Englisch ist der Schlüssel.** Der Katalog schreibt englisch, und
  die kanonische Form ist der englische Name - so bleibt eine Lektion
  lesbar, auch wenn eine Übersetzung sich ändert.
* **Sie ist von analyzer.data.avoidable getrennt.** Dort stehen
  **Boss**fähigkeiten mit einer Wertung ("war das vermeidbar"), hier
  **Spieler**fähigkeiten ganz ohne Wertung. Beides in eine Tabelle zu
  legen hieße, zwei Fragen zu vermischen, die sich unterschiedlich oft
  ändern.
"""

from __future__ import annotations

from analyzer.data import class_abilities


#
# --------------------------------------------------
# Übersetzungen
# --------------------------------------------------
#
# Englischer Name -> deutsche Schreibweisen. Mehrere sind erlaubt:
# einzelne Fähigkeiten sind im Lauf der Erweiterungen umbenannt
# worden, und ein zusätzlicher Eintrag schadet nicht (siehe Regel
# "additiv" oben).
#

ABILITY_NAMES: dict[str, tuple[str, ...]] = {

    #
    # --------------------------------------------------
    # Todesritter
    # --------------------------------------------------
    #

    "Blood Plague": ("Blutseuche",),
    "Frost Fever": ("Frostfieber",),
    "Bone Shield": ("Knochenschild",),
    "Blood Shield": ("Blutschild",),
    "Death Strike": ("Todesstoß",),
    "Vampiric Blood": ("Vampirblut",),
    "Dancing Rune Weapon": ("Tanzende Runenwaffe",),
    "Icebound Fortitude": ("Eisgebundene Unverwüstlichkeit",),
    "Anti-Magic Shell": ("Anti-Magie-Hülle",),
    "Anti-Magic Zone": ("Anti-Magie-Zone",),
    "Pillar of Frost": ("Säule des Frosts",),
    "Unholy Frenzy": ("Unheilige Raserei",),
    "Summon Gargoyle": ("Gargoyle beschwören",),
    "Dark Transformation": ("Dunkle Wandlung",),
    "Army of the Dead": ("Armee der Toten",),
    "Death and Decay": ("Tod und Verfall",),
    "Soul Reaper": ("Seelenernter",),
    "Outbreak": ("Ausbruch",),
    "Howling Blast": ("Heulende Böe",),
    "Obliterate": ("Auslöschen",),
    "Scourge Strike": ("Geißelstoß",),
    "Horn of Winter": ("Horn des Winters",),
    "Mind Freeze": ("Geistesgefrierung",),

    #
    # --------------------------------------------------
    # Druide
    # --------------------------------------------------
    #

    "Moonfire": ("Mondfeuer",),
    "Sunfire": ("Sonnenfeuer",),
    "Starfall": ("Sternenregen",),
    "Celestial Alignment": ("Himmlische Ausrichtung",),
    "Rake": ("Krallenhieb",),
    "Rip": ("Zerfetzen",),
    "Savage Roar": ("Wildes Brüllen",),
    "Tiger's Fury": ("Raserei des Tigers",),
    "Berserk": ("Berserker",),
    "Survival Instincts": ("Überlebensinstinkte",),
    "Barkskin": ("Baumrinde",),
    "Frenzied Regeneration": ("Rasende Regeneration",),
    "Savage Defense": ("Wilde Verteidigung",),
    "Ironbark": ("Eisenrinde",),
    "Rejuvenation": ("Verjüngung",),
    "Lifebloom": ("Blühendes Leben",),
    "Wild Growth": ("Wildwuchs",),
    "Swiftmend": ("Rasche Heilung",),
    "Tranquility": ("Seelenruhe",),
    "Innervate": ("Anregen",),
    "Mark of the Wild": ("Mal der Wildnis",),
    "Symbiosis": ("Symbiose",),
    "Nature's Cure": ("Heilung der Natur",),

    #
    # --------------------------------------------------
    # Jäger
    # --------------------------------------------------
    #
    # "Serpent Sting" steht mit beiden im Umlauf befindlichen
    # Übersetzungen drin - siehe Regel "additiv": die zusätzliche
    # Zeile kostet nichts, eine fehlende einen Treffer.
    #

    "Serpent Sting": ("Schlangengift", "Schlangenstich"),
    "Hunter's Mark": ("Jägermal",),
    "Rapid Fire": ("Schnellfeuer",),
    "Bestial Wrath": ("Animalischer Zorn",),
    "Stampede": ("Stampede",),
    "Deterrence": ("Abschreckung",),
    "Feign Death": ("Totstellen",),
    "Disengage": ("Rückzug",),
    "Misdirection": ("Ablenkung",),
    "Black Arrow": ("Schwarzer Pfeil",),
    "Kill Shot": ("Tödlicher Schuss",),
    "Chimaera Shot": ("Chimärenschuss",),
    "Tranquilizing Shot": ("Beruhigender Schuss",),
    "Explosive Trap": ("Explosivfalle",),

    #
    # --------------------------------------------------
    # Magier
    # --------------------------------------------------
    #

    "Living Bomb": ("Lebende Bombe",),
    "Nether Tempest": ("Nethersturm",),
    "Frost Bomb": ("Frostbombe",),
    "Combustion": ("Verbrennung",),
    "Ignite": ("Entzünden",),
    "Pyroblast": ("Pyroschlag",),
    "Arcane Power": ("Arkane Macht",),
    "Icy Veins": ("Eisige Adern",),
    "Presence of Mind": ("Geistesgegenwart",),
    "Ice Block": ("Eisblock",),
    "Ice Barrier": ("Eisbarriere",),
    "Evocation": ("Hervorrufung",),
    "Time Warp": ("Zeitkrümmung",),
    "Counterspell": ("Gegenzauber",),
    "Blink": ("Blinzeln",),
    "Frost Nova": ("Frostnova",),
    "Invisibility": ("Unsichtbarkeit",),
    "Rune of Power": ("Rune der Macht",),
    "Arcane Brilliance": ("Arkane Brillanz",),

    #
    # --------------------------------------------------
    # Mönch
    # --------------------------------------------------
    #

    "Shuffle": ("Mischen",),
    "Elusive Brew": ("Flüchtiges Gebräu",),
    "Guard": ("Wache",),
    "Purifying Brew": ("Reinigendes Gebräu",),
    "Fortifying Brew": ("Stärkendes Gebräu",),
    "Zen Meditation": ("Zen-Meditation",),
    "Dampen Harm": ("Schaden dämpfen",),
    "Diffuse Magic": ("Magie zerstreuen",),
    "Renewing Mist": ("Erneuernder Nebel",),
    "Soothing Mist": ("Beruhigender Nebel",),
    "Enveloping Mist": ("Einhüllender Nebel",),
    "Life Cocoon": ("Lebenskokon",),
    "Revival": ("Neubelebung",),
    "Mana Tea": ("Manatee",),
    "Tigereye Brew": ("Tigeraugengebräu",),
    "Energizing Brew": ("Energetisierendes Gebräu",),
    "Rising Sun Kick": ("Tritt der aufgehenden Sonne",),
    "Spear Hand Strike": ("Speerhandstoß",),
    "Detox": ("Entgiften",),

    #
    # --------------------------------------------------
    # Paladin
    # --------------------------------------------------
    #

    "Shield of the Righteous": ("Schild des Rechtschaffenen",),
    "Sacred Shield": ("Heiliger Schild",),
    "Divine Protection": ("Göttlicher Schutz",),
    "Divine Shield": ("Gottesschild",),
    "Ardent Defender": ("Glühender Verteidiger",),
    "Guardian of Ancient Kings": ("Wächter der alten Könige",),
    "Avenging Wrath": ("Zorn des Rächers",),
    "Holy Avenger": ("Heiliger Rächer",),
    "Beacon of Light": ("Lichtblick",),
    "Aura Mastery": ("Aurameisterschaft",),
    "Devotion Aura": ("Aura der Hingabe",),
    "Divine Favor": ("Göttliche Gunst",),
    "Hand of Sacrifice": ("Hand der Aufopferung",),
    "Hand of Protection": ("Hand des Schutzes",),
    "Hand of Freedom": ("Hand der Freiheit",),
    "Blessing of Kings": ("Segen der Könige",),
    "Blessing of Might": ("Segen der Macht",),
    "Inquisition": ("Inquisition",),
    "Seal of Truth": ("Siegel der Wahrheit",),
    "Lay on Hands": ("Handauflegung",),
    "Cleanse": ("Reinigen",),

    #
    # --------------------------------------------------
    # Priester
    # --------------------------------------------------
    #

    "Power Word: Shield": ("Machtwort: Schild",),
    "Power Word: Barrier": ("Machtwort: Barriere",),
    "Shadow Word: Pain": ("Schattenwort: Schmerz",),
    "Vampiric Touch": ("Vampirberührung",),
    "Devouring Plague": ("Verschlingende Seuche",),
    "Shadowfiend": ("Schattengeist",),
    "Mindbender": ("Gedankenschinder",),
    "Renew": ("Erneuerung",),
    "Prayer of Mending": ("Gebet der Besserung",),
    "Divine Hymn": ("Göttliche Hymne",),
    "Hymn of Hope": ("Hymne der Hoffnung",),
    "Guardian Spirit": ("Schutzgeist",),
    "Pain Suppression": ("Schmerzunterdrückung",),
    "Spirit Shell": ("Geisthülle",),
    "Dispersion": ("Zerstreuung",),
    "Fade": ("Verblassen",),
    "Dispel Magic": ("Magie bannen",),
    "Mass Dispel": ("Massenbannung",),
    "Leap of Faith": ("Vertrauenssprung",),
    "Archangel": ("Erzengel",),

    #
    # --------------------------------------------------
    # Schurke
    # --------------------------------------------------
    #

    "Rupture": ("Blutung",),
    "Slice and Dice": ("Schnetzeln",),
    "Recuperate": ("Erholung",),
    "Deadly Poison": ("Tödliches Gift",),
    "Adrenaline Rush": ("Adrenalinrausch",),
    "Killing Spree": ("Amoklauf",),
    "Shadow Blades": ("Schattenklingen",),
    "Shadow Dance": ("Schattentanz",),
    "Vendetta": ("Vendetta",),
    "Cloak of Shadows": ("Umhang der Schatten",),
    "Evasion": ("Ausweichen",),
    "Feint": ("Finte",),
    "Kick": ("Tritt",),
    "Tricks of the Trade": ("Kniffe des Handwerks",),
    "Smoke Bomb": ("Rauchbombe",),
    "Combat Readiness": ("Kampfbereitschaft",),
    "Sprint": ("Sprinten",),
    "Blind": ("Blenden",),

    #
    # --------------------------------------------------
    # Schamane
    # --------------------------------------------------
    #

    "Flame Shock": ("Flammenschock",),
    "Lava Burst": ("Lavaeruption",),
    "Elemental Mastery": ("Elementarbeherrschung",),
    "Ascendance": ("Aufstieg",),
    "Fire Elemental Totem": ("Feuerelementartotem",),
    "Feral Spirit": ("Wilder Geist",),
    "Stormstrike": ("Sturmschlag",),
    "Unleash Elements": ("Elemente entfesseln",),
    "Searing Totem": ("Sengendes Totem",),
    "Healing Rain": ("Heilender Regen",),
    "Healing Stream Totem": ("Totem des heilenden Stroms",),
    "Riptide": ("Springflut",),
    "Earth Shield": ("Erdschild",),
    "Spirit Link Totem": ("Totem der Geisterverbindung",),
    "Healing Tide Totem": ("Totem der heilenden Flut",),
    "Mana Tide Totem": ("Totem der Manaflut",),
    "Chain Heal": ("Kettenheilung",),
    "Wind Shear": ("Windstoß",),
    "Purify Spirit": ("Geist reinigen",),
    "Capacitor Totem": ("Kondensatortotem",),
    "Earthbind Totem": ("Erdfesseltotem",),
    "Tremor Totem": ("Bebentotem",),
    "Shamanistic Rage": ("Schamanistische Wut",),
    "Astral Shift": ("Astrale Verschiebung",),
    "Bloodlust": ("Kampfrausch",),
    "Heroism": ("Heldentum",),

    #
    # --------------------------------------------------
    # Hexenmeister
    # --------------------------------------------------
    #

    "Agony": ("Pein",),
    "Corruption": ("Verderbnis",),
    "Unstable Affliction": ("Instabiles Gebrechen",),
    "Immolate": ("Feuerbrand",),
    "Doom": ("Verdammnis",),
    "Haunt": ("Heimsuchung",),
    "Dark Soul: Misery": ("Dunkle Seele: Elend",),
    "Dark Soul: Instability": ("Dunkle Seele: Instabilität",),
    "Dark Soul: Knowledge": ("Dunkle Seele: Wissen",),
    "Unending Resolve": ("Unendliche Entschlossenheit",),
    "Dark Bargain": ("Dunkler Handel",),
    "Soulstone": ("Seelenstein",),
    "Healthstone": ("Gesundheitsstein",),
    "Demonic Gateway": ("Dämonisches Portal",),
    "Life Tap": ("Aderlass",),
    "Curse of the Elements": ("Fluch der Elemente",),

    #
    # --------------------------------------------------
    # Krieger
    # --------------------------------------------------
    #

    "Shield Block": ("Schildblock",),
    "Shield Barrier": ("Schildbarriere",),
    "Shield Wall": ("Schildwall",),
    "Last Stand": ("Letztes Gefecht",),
    "Demoralizing Shout": ("Demoralisierender Ruf",),
    "Rallying Cry": ("Sammelschrei",),
    "Recklessness": ("Rücksichtslosigkeit",),
    "Avatar": ("Avatar",),
    "Bloodbath": ("Blutbad",),
    "Rend": ("Verwunden",),
    "Enraged Regeneration": ("Wütende Regeneration",),
    "Spell Reflection": ("Zauberreflexion",),
    "Mass Spell Reflection": ("Massenzauberreflexion",),
    "Berserker Rage": ("Berserkerwut",),
    "Battle Shout": ("Schlachtruf",),
    "Commanding Shout": ("Befehlsruf",),
    "Heroic Leap": ("Heldenhafter Satz",),
    "Charge": ("Sturmangriff",),
    "Vigilance": ("Wachsamkeit",),
    "Pummel": ("Knüppeln",),

}


#
# --------------------------------------------------
# Index
# --------------------------------------------------
#


def _key(value: str) -> str:
    """
    Vergleichsform eines Namens.

    Alles außer Buchstaben und Ziffern fällt weg, damit
    "Machtwort: Schild", "Machtwort Schild" und "machtwort:schild"
    denselben Schlüssel ergeben - Doppelpunkte, Apostrophe und
    Bindestriche schreibt nicht jede Quelle gleich.
    """

    return "".join(
        char
        for char in (value or "").casefold()
        if char.isalnum()
    )


def _all_names() -> dict[str, tuple[str, ...]]:
    """
    Diese Tabelle **plus** die Übersetzungen aus
    analyzer/data/class_abilities.py.

    Dort steht ohnehin zu jeder Fähigkeit einer Spezialisierung beides
    - englisch und deutsch -, und zwei Listen derselben Übersetzungen
    laufen unweigerlich auseinander. Das Symptom wäre still: eine
    Lektion, deren Kriterium eine Fähigkeit nennt, die hier fehlt,
    sagt für immer "keine Daten", ohne dass irgendwo ein Fehler
    auftaucht. Die Einträge dieser Datei gewinnen, wo sich beide
    überschneiden - sie sind die von Hand gepflegten.
    """

    merged: dict[str, set[str]] = {
        english: set(german)
        for english, german in class_abilities.translations().items()
    }

    for english, german in ABILITY_NAMES.items():
        merged.setdefault(english, set()).update(german)

    return {
        english: tuple(sorted(german))
        for english, german in merged.items()
    }


def _build_groups() -> dict[str, frozenset[str]]:
    """
    Zu jedem Namensschlüssel die Menge aller gleichbedeutenden
    Schlüssel. Ein Vergleich ist damit ein Mengentest und keine
    Schleife über die ganze Tabelle.
    """

    groups: dict[str, frozenset[str]] = {}

    for english, german in _all_names().items():

        keys = frozenset(
            _key(name)
            for name in (english,) + tuple(german)
            if _key(name)
        )

        for key in keys:
            groups[key] = keys

    return groups


def _build_canonical() -> dict[str, str]:

    table: dict[str, str] = {}

    for english, german in _all_names().items():

        for name in (english,) + tuple(german):
            table[_key(name)] = english

    return table


_GROUPS: dict[str, frozenset[str]] = _build_groups()

_CANONICAL: dict[str, str] = _build_canonical()


#
# --------------------------------------------------
# Abgleich
# --------------------------------------------------
#


def aliases_of(name: str) -> tuple[str, ...]:
    """
    Alle bekannten Schreibweisen einer Fähigkeit, englisch zuerst.
    Unbekanntes liefert sich selbst - eine Fähigkeit ohne Eintrag ist
    kein Sonderfall, sie hat nur keine Übersetzung.
    """

    english = _CANONICAL.get(_key(name))

    if english is None:
        return ((name or "").strip(),) if (name or "").strip() else ()

    return (english,) + ABILITY_NAMES[english]


def canonical(name: str) -> str:
    """
    Der englische Name einer Fähigkeit, oder der Eingabewert.
    """

    return _CANONICAL.get(_key(name), (name or "").strip())


def matches(subject: str, ability: str) -> bool:
    """
    Ob `ability` die in `subject` gemeinte Fähigkeit ist - unabhängig
    von der Sprache.

    Ohne `subject` gilt alles als Treffer: ein Kriterium ohne
    Fähigkeitsangabe meint ausdrücklich "alle eigenen" (siehe
    `_uptime` in analyzer/academy/checks.py).
    """

    wanted = _key(subject)

    if not wanted:
        return True

    found = _key(ability)

    if not found:
        return False

    if wanted == found:
        return True

    return found in _GROUPS.get(wanted, frozenset())


def known_abilities() -> tuple[str, ...]:
    """
    Alle englischen Namen der Tabelle - der Katalogtest hängt daran:
    nennt eine Lektion eine Fähigkeit, die hier fehlt, ist sie in einem
    deutschen Log nicht prüfbar.
    """

    return tuple(sorted(ABILITY_NAMES))
