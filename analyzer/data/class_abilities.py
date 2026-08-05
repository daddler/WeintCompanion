"""
Was eine Spezialisierung überhaupt zu zeigen hätte.

Diese Tabelle beantwortet eine Frage, die vorher niemand beantwortet
hat: **welche** DoTs, HoTs, Selbstbuffs und Cooldowns gehören zu einer
Spezialisierung? Ohne sie konnte die Oberfläche nur wiedergeben, was
die Datenquelle geschickt hat - und wenn die nichts geschickt hat,
stand dort "Keine Angaben zu DoT-Uptimes", und zwar wortgleich für

* einen Schurken, der seine Blutung tatsächlich nie aufgelegt hat,
* einen Heiler, dessen HoTs die Quelle nicht mitliefert,
* und einen Kampf, für den es gar keine Tiefenauswertung gibt.

Drei völlig verschiedene Sachverhalte, eine einzige Zeile Text. Genau
deshalb hat diese Tabelle einen eigenen Platz: sie macht aus dem
Schweigen der Quelle eine Aussage, die man lesen kann - "für Meucheln
werden Blutung, Tödliches Gift und Blitzschlag erwartet, gemeldet
wurde davon nichts".

Vier Regeln, nach denen sie gepflegt wird:

* **Drei unabhängige Wege zur Erkennung.** Spell-ID, englischer Name,
  deutscher Name - einer genügt. Denselben Weg geht der Bot seit
  `services/warcraftlogs_spells.py` (siehe docs/warcraftlogs-bridge.md,
  "Warum die v2-Felder leer ankamen"): WarcraftLogs liefert
  Fähigkeitsnamen in der Sprache des Clients, der den Bericht
  hochgeladen hat. Eine falsch erinnerte ID macht einen Eintrag
  deshalb nicht kaputt, solange ein Name passt, und umgekehrt.
* **`optional` heißt: nur zeigen, wenn gemeldet.** Alles, was von
  einem Talent, einer Glyphe oder einem Ausrüstungsteil abhängt, ist
  optional. Eine Zeile "Inkarnation - kein Einsatz" bei einem
  Spieler, der das Talent gar nicht hat, wäre ein Vorwurf für etwas,
  das keiner falsch gemacht hat. Was ohne Talentwahl jeder dieser
  Spezialisierung hat, ist nicht optional - dort ist das Fehlen eine
  echte Aussage.
* **Der Richtwert gehört hierher, nicht in die Oberfläche.** WeintTV
  und die Academy messen denselben Effekt sonst an verschiedenen
  Maßstäben. Neunzig Prozent sind für Blutung mager und für
  Schildblock hervorragend.
* **Sie erfindet keine Zahlen.** Hier steht ausschließlich, was es
  gibt und was gut wäre - nie, was ein Spieler erreicht hat. Das
  bleibt Sache der Datenquelle.

Die Spell-IDs sind aus dem Raidlog-Analyzer übernommen (dort in
`DOT_REGISTRY`, `HOT_REGISTRY`, `DPS_COOLDOWNS`, `DPS_DEFENSIVES`,
`HEALER_COOLDOWNS`, `HEALER_DEFENSIVES`, `TANK_COOLDOWNS`,
`ACTIVE_MITIGATION`, `RAID_UTILITY_COOLDOWNS`) und dort um die Specs
ergänzt, für die er keine Einträge hatte - er wertet je Spieler eine
Rolle aus, diese Tabelle muss alle vierunddreißig Spezialisierungen
tragen. Wo eine Fähigkeit über mehrere IDs läuft (Talentvarianten,
umbenannte Ränge), stehen sie alle: die Erkennung nimmt die erste, die
passt.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzer.data import specs as spec_table
from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
)


#
# --------------------------------------------------
# Bausteine
# --------------------------------------------------
#


@dataclass(frozen=True)
class TrackedAura:
    """
    Ein Effekt, dessen Wirkungsdauer für diese Spezialisierung zählt.

    `kind` ist einer der UPTIME_*-Werte und entscheidet, in welcher
    der drei Listen des Snapshots der Effekt zu Hause ist - und damit
    auch, für wen die Academy ihn liest (DoTs für Schaden, HoTs für
    Heilung, eigene Buffs für die aktive Schadensminderung der Tanks).
    """

    english: str

    german: str

    spell_ids: tuple[int, ...]

    kind: str = UPTIME_DOT

    expected_percent: float = 0.0

    optional: bool = False

    #
    # Weitere Schreibweisen, unter denen eine Quelle denselben Effekt
    # melden kann. Dieselbe Regel wie in
    # analyzer/data/player_abilities.py: ein zusätzlicher Eintrag
    # schadet nie, ein fehlender kostet einen Treffer.
    #

    aliases: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:

        return (self.english, self.german, *self.aliases)


@dataclass(frozen=True)
class TrackedCooldown:
    """
    Ein Cooldown, dessen Einsätze für diese Spezialisierung zählen.

    `cooldown` ist die Abklingzeit in **Sekunden** - dieselbe Einheit
    wie in `CooldownUsage`, damit aus Kampfdauer und Abklingzeit die
    möglichen Einsätze folgen, ohne dass irgendwo umgerechnet wird.
    """

    english: str

    german: str

    spell_ids: tuple[int, ...]

    cooldown: float = 0.0

    category: str = CD_PERSONAL

    optional: bool = False

    aliases: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:

        return (self.english, self.german, *self.aliases)


@dataclass(frozen=True)
class SpecAbilities:
    """
    Der komplette Referenzbestand einer Spezialisierung.
    """

    class_name: str

    spec: str

    auras: tuple[TrackedAura, ...] = ()

    cooldowns: tuple[TrackedCooldown, ...] = ()

    def auras_of(self, kind: str) -> tuple[TrackedAura, ...]:

        return tuple(
            entry
            for entry in self.auras
            if entry.kind == kind
        )


#
# Kurzformen für die Tabelle unten. Ohne sie wäre jede Zeile dreimal
# so lang und die Tabelle nicht mehr am Stück lesbar - und Lesbarkeit
# ist bei einer Referenztabelle die halbe Pflege.
#


def _dot(
    english, german, ids, expected=95.0, optional=False, aliases=(),
) -> TrackedAura:

    return TrackedAura(
        english=english,
        german=german,
        spell_ids=tuple(ids),
        kind=UPTIME_DOT,
        expected_percent=expected,
        optional=optional,
        aliases=tuple(aliases),
    )


def _hot(
    english, german, ids, expected=85.0, optional=False, aliases=(),
) -> TrackedAura:

    return TrackedAura(
        english=english,
        german=german,
        spell_ids=tuple(ids),
        kind=UPTIME_HOT,
        expected_percent=expected,
        optional=optional,
        aliases=tuple(aliases),
    )


def _buff(
    english, german, ids, expected=0.0, optional=False, aliases=(),
) -> TrackedAura:

    return TrackedAura(
        english=english,
        german=german,
        spell_ids=tuple(ids),
        kind=UPTIME_BUFF,
        expected_percent=expected,
        optional=optional,
        aliases=tuple(aliases),
    )


def _cd(
    english,
    german,
    ids,
    seconds,
    category=CD_PERSONAL,
    optional=False,
    aliases=(),
) -> TrackedCooldown:

    return TrackedCooldown(
        english=english,
        german=german,
        spell_ids=tuple(ids),
        cooldown=float(seconds),
        category=category,
        optional=optional,
        aliases=tuple(aliases),
    )


#
# --------------------------------------------------
# Fähigkeiten, die mehrere Spezialisierungen teilen
# --------------------------------------------------
#
# Einmal benannt statt bei jeder Spec neu getippt: eine Abklingzeit,
# die an drei Stellen steht, steht früher oder später an zwei Stellen
# falsch.
#

_ANTI_MAGIC_SHELL = _cd(
    "Anti-Magic Shell", "Antimagische Hülle", (48707,), 45, CD_DEFENSIVE,
)

_ICEBOUND_FORTITUDE = _cd(
    "Icebound Fortitude", "Eisige Gegenwehr", (48792,), 180, CD_DEFENSIVE,
)

_ANTI_MAGIC_ZONE = _cd(
    "Anti-Magic Zone", "Antimagische Zone", (51052,), 120, CD_RAID,
)

_ARMY_OF_THE_DEAD = _cd(
    "Army of the Dead", "Armee der Toten", (42650,), 600, CD_PERSONAL, True,
)

_BARKSKIN = _cd("Barkskin", "Baumrinde", (22812,), 60, CD_DEFENSIVE)

_SURVIVAL_INSTINCTS = _cd(
    "Survival Instincts", "Überlebensinstinkte", (61336,), 180, CD_DEFENSIVE,
)

_REBIRTH = _cd("Rebirth", "Wiedergeburt", (20484,), 600, CD_RAID, True)

_STAMPEDING_ROAR = _cd(
    "Stampeding Roar", "Stampfendes Gebrüll", (77764, 106898), 120, CD_RAID,
)

_DETERRENCE = _cd(
    "Deterrence", "Abschreckung", (19263, 148467), 180, CD_DEFENSIVE,
)

_STAMPEDE = _cd("Stampede", "Stampede", (121818,), 300)

_SERPENT_STING = _dot(
    "Serpent Sting", "Schlangengift", (118253, 1978), 90.0,
    aliases=("Gift des Vipers",),
)

_ICE_BLOCK = _cd("Ice Block", "Eisblock", (45438,), 300, CD_DEFENSIVE)

_ICE_BARRIER = _cd("Ice Barrier", "Eisbarriere", (11426,), 25, CD_DEFENSIVE)

_MIRROR_IMAGE = _cd("Mirror Image", "Spiegelbilder", (55342,), 180)

_TIME_WARP = _cd("Time Warp", "Zeitkrümmung", (80353,), 300, CD_RAID)

_ALTER_TIME = _cd(
    "Alter Time", "Zeit verändern", (108978,), 180, CD_PERSONAL, True,
)

_FORTIFYING_BREW = _cd(
    "Fortifying Brew", "Stärkendes Gebräu", (115203,), 180, CD_DEFENSIVE,
)

_DAMPEN_HARM = _cd(
    "Dampen Harm", "Schaden dämpfen", (122278,), 120, CD_DEFENSIVE, True,
)

_DIFFUSE_MAGIC = _cd(
    "Diffuse Magic", "Magiediffusion", (122783,), 90, CD_DEFENSIVE, True,
)

_RING_OF_PEACE = _cd(
    "Ring of Peace", "Ring des Friedens", (116844,), 45, CD_RAID, True,
)

_DIVINE_PROTECTION = _cd(
    "Divine Protection", "Göttlicher Schutz", (498,), 60, CD_DEFENSIVE,
)

_DIVINE_SHIELD = _cd(
    "Divine Shield", "Gottesschild", (642,), 300, CD_DEFENSIVE,
)

_DEVOTION_AURA = _cd(
    "Devotion Aura", "Aura der Hingabe", (31821,), 180, CD_RAID,
)

_HAND_OF_SACRIFICE = _cd(
    "Hand of Sacrifice", "Hand der Aufopferung", (6940,), 120, CD_RAID,
)

_LAY_ON_HANDS = _cd(
    "Lay on Hands", "Handauflegung", (633,), 600, CD_DEFENSIVE,
)

_HOLY_AVENGER = _cd(
    "Holy Avenger", "Heiliger Rächer", (105809,), 180, CD_PERSONAL, True,
)

_AVENGING_WRATH = _cd(
    "Avenging Wrath", "Zornige Vergeltung", (31884,), 180,
    aliases=("Zorn der Gerechtigkeit",),
)

# 31842 stand bis hierher mit in der Zeile darüber - das ist aber
# **Göttliche Gunst**, eine eigene Fähigkeit mit eigener Abklingzeit.
# Ein Einsatz davon wurde dadurch als Avenging Wrath gezählt: eine
# Zahl, die stimmt, unter einem Namen, der nicht stimmt - schlimmer
# als eine fehlende Zeile, weil nichts daran auffällt.
_DIVINE_FAVOR = _cd(
    "Divine Favor", "Göttliche Gunst", (31842,), 180, CD_HEAL, True,
)

_DESPERATE_PRAYER = _cd(
    "Desperate Prayer", "Verzweifeltes Gebet", (19236,), 120,
    CD_DEFENSIVE, True,
)

_POWER_INFUSION = _cd(
    "Power Infusion", "Seele der Macht", (10060,), 120, CD_PERSONAL, True,
)

_SHADOWFIEND = _cd(
    "Shadowfiend", "Schattengeist", (34433,), 180,
)

# 123040 ist **Gedankenschinder**, der Talent-Ersatz für den
# Schattengeist - und eben nicht derselbe Zauber: 60 Sekunden
# Abklingzeit statt 180. Zusammen in einer Zeile wurde jeder
# Gedankenschinder gegen die dreifache Abklingzeit gemessen, also
# dauerhaft als "kaum genutzt" bewertet.
_MINDBENDER = _cd(
    "Mindbender", "Gedankenschinder", (123040,), 60, CD_PERSONAL, True,
)

_MASS_DISPEL = _cd(
    "Mass Dispel", "Massenbannung", (32375,), 15, CD_RAID, True,
)

_SLICE_AND_DICE = _buff(
    "Slice and Dice", "Zerhäckseln", (5171,), 90.0,
    aliases=("Schnetzeln",),
)

_DEADLY_POISON = _dot(
    "Deadly Poison", "Tödliches Gift", (2818,), 95.0,
)

_RUPTURE = _dot("Rupture", "Blutung", (1943,), 90.0)

_SHADOW_BLADES = _cd("Shadow Blades", "Schattenklingen", (121471,), 180)

_CLOAK_OF_SHADOWS = _cd(
    "Cloak of Shadows", "Mantel der Schatten", (31224,), 60, CD_DEFENSIVE,
)

_EVASION = _cd("Evasion", "Entrinnen", (5277,), 120, CD_DEFENSIVE)

_FEINT = _cd("Feint", "Finte", (1966,), 15, CD_DEFENSIVE)

_SMOKE_BOMB = _cd("Smoke Bomb", "Rauchbombe", (76577,), 180, CD_RAID)

_FLAME_SHOCK = _dot("Flame Shock", "Flammenschock", (8050,), 90.0)

_ELEMENTAL_MASTERY = _cd(
    "Elemental Mastery", "Elementarbeherrschung", (16166,), 90,
    CD_PERSONAL, True,
)

_FIRE_ELEMENTAL = _cd(
    "Fire Elemental Totem", "Totem des Feuerelementars", (2894,), 300,
)

_SHAMANISTIC_RAGE = _cd(
    "Shamanistic Rage", "Schamanistische Wut", (30823,), 60, CD_DEFENSIVE,
)

_ASTRAL_SHIFT = _cd(
    "Astral Shift", "Astralverschiebung", (108271,), 90, CD_DEFENSIVE, True,
)

_HEALING_TIDE = _cd(
    "Healing Tide Totem", "Totem der Heilungsflut", (108280,), 180, CD_HEAL,
)

_SPIRIT_LINK = _cd(
    "Spirit Link Totem", "Totem der Geistverbindung", (98008,), 180, CD_HEAL,
)

_ANCESTRAL_GUIDANCE = _cd(
    "Ancestral Guidance", "Führung der Ahnen", (108281,), 120, CD_HEAL, True,
)

_UNENDING_RESOLVE = _cd(
    "Unending Resolve", "Unendliche Entschlossenheit", (104773,), 180,
    CD_DEFENSIVE,
)

_SACRIFICIAL_PACT = _cd(
    "Sacrificial Pact", "Opferpakt", (108416,), 60, CD_DEFENSIVE, True,
)

_DARK_BARGAIN = _cd(
    "Dark Bargain", "Dunkler Handel", (110913,), 180, CD_DEFENSIVE, True,
)

_SUMMON_DOOMGUARD = _cd(
    "Summon Doomguard", "Verdammniswache beschwören",
    (18540, 112870, 112927), 600, CD_PERSONAL, True,
)

_SUMMON_INFERNAL = _cd(
    "Summon Infernal", "Höllenbestie beschwören",
    (1122, 112921), 600, CD_PERSONAL, True,
)

_SOULSTONE = _cd("Soulstone", "Seelenstein", (20707,), 600, CD_RAID, True)

_CORRUPTION = _dot("Corruption", "Verderbnis", (172, 146739), 95.0)

_DEEP_WOUNDS = _dot("Deep Wounds", "Tiefe Wunden", (115767,), 90.0)

_COLOSSUS_SMASH = _dot(
    "Colossus Smash", "Kolossales Schmettern", (86346,), 30.0,
)

_RECKLESSNESS = _cd("Recklessness", "Tollkühnheit", (1719,), 180)

_AVATAR = _cd("Avatar", "Avatar", (107574,), 180, CD_PERSONAL, True)

_BLOODBATH = _cd("Bloodbath", "Blutbad", (12292,), 60, CD_PERSONAL, True)

_SKULL_BANNER = _cd(
    "Skull Banner", "Schädelbanner", (114207,), 180, CD_RAID, True,
)

_RALLYING_CRY = _cd(
    "Rallying Cry", "Sammelschrei", (97462,), 180, CD_RAID,
)

_DEMORALIZING_BANNER = _cd(
    "Demoralizing Banner", "Demoralisierendes Banner", (114203,), 180,
    CD_RAID, True,
)

_DIE_BY_THE_SWORD = _cd(
    "Die by the Sword", "Durch das Schwert umkommen", (118038,), 120,
    CD_DEFENSIVE,
)

_BERSERKER_RAGE = _cd(
    "Berserker Rage", "Berserkerwut", (18499,), 30, CD_DEFENSIVE,
)


#
# --------------------------------------------------
# Die vierunddreißig Spezialisierungen
# --------------------------------------------------
#
# Reihenfolge wie in analyzer/data/specs.py, damit sich beide Tabellen
# nebeneinander lesen lassen. Ein Test hält fest, dass keine Spec
# fehlt und keine leer ist.
#

SPEC_ABILITIES: tuple[SpecAbilities, ...] = (

    #
    # --------------------------------------------------
    # Todesritter
    # --------------------------------------------------
    #

    SpecAbilities(
        "Death Knight", "Blut",
        auras=(
            _dot("Blood Plague", "Blutseuche", (55078,), 90.0),
            _dot("Frost Fever", "Frostfieber", (55095,), 90.0),
            _buff("Bone Shield", "Knochenschild", (49222,), 85.0),
            _buff("Blood Shield", "Blutschild", (77535,), 60.0),
        ),
        cooldowns=(
            _cd("Vampiric Blood", "Vampirblut", (55233,), 60, CD_DEFENSIVE),
            _ICEBOUND_FORTITUDE,
            _cd(
                "Dancing Rune Weapon", "Tanzende Runenwaffe",
                (49028,), 90, CD_DEFENSIVE,
            ),
            _ANTI_MAGIC_SHELL,
            _ANTI_MAGIC_ZONE,
            _ARMY_OF_THE_DEAD,
        ),
    ),

    SpecAbilities(
        "Death Knight", "Frost",
        auras=(
            _dot("Frost Fever", "Frostfieber", (55095,), 90.0),
            _dot("Blood Plague", "Blutseuche", (55078,), 90.0),
        ),
        cooldowns=(
            _cd("Pillar of Frost", "Säule des Frosts", (51271,), 60),
            _cd(
                "Empower Rune Weapon", "Runenwaffe stärken",
                (47568,), 300,
            ),
            _ARMY_OF_THE_DEAD,
            _ANTI_MAGIC_SHELL,
            _ICEBOUND_FORTITUDE,
            _ANTI_MAGIC_ZONE,
        ),
    ),

    SpecAbilities(
        "Death Knight", "Unheilig",
        auras=(
            _dot("Frost Fever", "Frostfieber", (55095,), 90.0),
            _dot("Blood Plague", "Blutseuche", (55078,), 90.0),
        ),
        cooldowns=(
            _cd("Unholy Frenzy", "Unheilige Raserei", (49016,), 180),
            _cd("Summon Gargoyle", "Gargoyle beschwören", (49206,), 180),
            _cd(
                "Dark Transformation", "Dunkle Wandlung",
                (63560,), 30,
            ),
            _ARMY_OF_THE_DEAD,
            _ANTI_MAGIC_SHELL,
            _ICEBOUND_FORTITUDE,
            _ANTI_MAGIC_ZONE,
        ),
    ),

    #
    # --------------------------------------------------
    # Druide
    # --------------------------------------------------
    #

    SpecAbilities(
        "Druid", "Gleichgewicht",
        auras=(
            _dot("Moonfire", "Mondfeuer", (8921, 164812), 95.0),
            _dot("Sunfire", "Sonnenfeuer", (93402, 164815), 95.0),
        ),
        cooldowns=(
            _cd(
                "Celestial Alignment", "Himmlische Ausrichtung",
                (112071,), 180,
            ),
            _cd(
                "Incarnation: Chosen of Elune", "Inkarnation: Elunes Auserwählte",
                (102560,), 180, CD_PERSONAL, True,
            ),
            _cd(
                "Nature's Vigil", "Wachsamkeit der Natur",
                (124974,), 90, CD_PERSONAL, True,
            ),
            _BARKSKIN,
            _cd("Tranquility", "Seelenruhe", (740,), 180, CD_RAID,
                aliases=("Gelassenheit",)),
            _STAMPEDING_ROAR,
            _REBIRTH,
        ),
    ),

    SpecAbilities(
        "Druid", "Wilder Kampf",
        auras=(
            _dot("Rip", "Blutung", (1079,), 90.0),
            _dot("Rake", "Krallenhieb", (1822,), 90.0),
            _dot("Thrash", "Hauen", (106830,), 70.0, True),
            _buff("Savage Roar", "Wildes Brüllen", (52610, 127538), 90.0),
        ),
        cooldowns=(
            _cd("Tiger's Fury", "Tigerfuror", (5217,), 30),
            _cd("Berserk", "Berserker", (106951, 106952, 50334), 180),
            _cd(
                "Incarnation: King of the Jungle", "Inkarnation: König des Dschungels",
                (102543,), 180, CD_PERSONAL, True,
            ),
            _cd(
                "Nature's Vigil", "Wachsamkeit der Natur",
                (124974,), 90, CD_PERSONAL, True,
            ),
            _BARKSKIN,
            _SURVIVAL_INSTINCTS,
            _STAMPEDING_ROAR,
            _REBIRTH,
        ),
    ),

    SpecAbilities(
        "Druid", "Wächter",
        auras=(
            _buff("Savage Defense", "Wilde Verteidigung", (62606, 132402), 50.0),
            _dot("Lacerate", "Aufschlitzen", (33745,), 90.0),
            _dot("Thrash", "Hauen", (77758,), 90.0),
            _buff(
                "Tooth and Claw", "Zahn und Klaue",
                (135286,), 30.0, True,
            ),
        ),
        cooldowns=(
            _SURVIVAL_INSTINCTS,
            _BARKSKIN,
            _cd(
                "Might of Ursoc", "Macht von Ursoc",
                (106922,), 180, CD_DEFENSIVE,
            ),
            _cd(
                "Frenzied Regeneration", "Rasende Regeneration",
                (22842,), 0, CD_DEFENSIVE,
            ),
            _cd(
                "Incarnation: Son of Ursoc", "Inkarnation: Sohn von Ursoc",
                (102558,), 180, CD_PERSONAL, True,
            ),
            _STAMPEDING_ROAR,
            _REBIRTH,
        ),
    ),

    SpecAbilities(
        "Druid", "Wiederherstellung",
        auras=(
            _hot("Rejuvenation", "Verjüngung", (774,), 80.0),
            _hot("Lifebloom", "Blühendes Leben", (33763,), 95.0),
            _hot("Wild Growth", "Wildwuchs", (48438,), 70.0),
            _hot("Regrowth", "Nachwachsen", (8936,), 40.0, True),
        ),
        cooldowns=(
            _cd("Tranquility", "Seelenruhe", (740,), 180, CD_HEAL,
                aliases=("Gelassenheit",)),
            _cd(
                "Ironbark", "Eisenborke", (102342,), 60, CD_HEAL,
            ),
            _cd(
                "Nature's Swiftness", "Schnelligkeit der Natur",
                (132158,), 60, CD_HEAL,
            ),
            _cd(
                "Incarnation: Tree of Life", "Inkarnation: Baum des Lebens",
                (33891,), 180, CD_HEAL, True,
            ),
            _BARKSKIN,
            _STAMPEDING_ROAR,
            _REBIRTH,
        ),
    ),

    #
    # --------------------------------------------------
    # Jäger
    # --------------------------------------------------
    #

    SpecAbilities(
        "Hunter", "Tierherrschaft",
        auras=(
            _SERPENT_STING,
        ),
        cooldowns=(
            _cd("Bestial Wrath", "Zorn des Wildtiers", (19574,), 60),
            _cd("Rapid Fire", "Schnellfeuer", (3045,), 300),
            _STAMPEDE,
            _cd(
                "A Murder of Crows", "Krähenschwarm",
                (131894,), 120, CD_PERSONAL, True,
            ),
            _DETERRENCE,
        ),
    ),

    SpecAbilities(
        "Hunter", "Treffsicherheit",
        auras=(
            _SERPENT_STING,
            _dot(
                "Piercing Shots", "Durchschlagende Schüsse",
                (63468,), 60.0, True,
            ),
        ),
        cooldowns=(
            _cd("Rapid Fire", "Schnellfeuer", (3045,), 300),
            _cd("Readiness", "Bereitschaft", (23989,), 180),
            _STAMPEDE,
            _cd(
                "A Murder of Crows", "Krähenschwarm",
                (131894,), 120, CD_PERSONAL, True,
            ),
            _DETERRENCE,
        ),
    ),

    SpecAbilities(
        "Hunter", "Überleben",
        auras=(
            _SERPENT_STING,
            _dot("Black Arrow", "Schwarzer Pfeil", (3674,), 90.0),
        ),
        cooldowns=(
            _cd("Rapid Fire", "Schnellfeuer", (3045,), 300),
            _STAMPEDE,
            _cd(
                "A Murder of Crows", "Krähenschwarm",
                (131894,), 120, CD_PERSONAL, True,
            ),
            _DETERRENCE,
        ),
    ),

    #
    # --------------------------------------------------
    # Magier
    # --------------------------------------------------
    #

    SpecAbilities(
        "Mage", "Arkan",
        auras=(
            # Der DoT des Arkan-Magiers - fehlte hier komplett, obwohl
            # er in der Rückmeldung ausdrücklich genannt war. Ohne ihn
            # hatte die Spezialisierung überhaupt keinen nicht-
            # optionalen DoT, und "Rotation" blieb dauerhaft unbewertet.
            _dot(
                "Nether Tempest", "Nethersturm", (114923,), 90.0,
                aliases=("Netherorkan",),
            ),
            _dot("Living Bomb", "Lebende Bombe", (44457,), 80.0, True),
            _buff("Arcane Charge", "Arkane Ladung", (36032,), 0.0, True),
        ),
        cooldowns=(
            _cd("Arcane Power", "Arkane Macht", (12042,), 90),
            _cd(
                "Presence of Mind", "Geistesgegenwart",
                (12043,), 90, CD_PERSONAL, True,
            ),
            _MIRROR_IMAGE,
            _ALTER_TIME,
            _ICE_BLOCK,
            _ICE_BARRIER,
            _TIME_WARP,
        ),
    ),

    SpecAbilities(
        "Mage", "Feuer",
        auras=(
            _dot("Pyroblast", "Pyroschlag", (11366,), 60.0),
            _dot("Ignite", "Entzünden", (12654,), 85.0),
            _dot("Living Bomb", "Lebende Bombe", (44457,), 80.0, True),
        ),
        cooldowns=(
            _cd("Combustion", "Einäschern", (11129,), 45),
            _MIRROR_IMAGE,
            _ALTER_TIME,
            _ICE_BLOCK,
            _ICE_BARRIER,
            _TIME_WARP,
        ),
    ),

    SpecAbilities(
        "Mage", "Frost",
        auras=(
            _dot("Living Bomb", "Lebende Bombe", (44457,), 80.0, True),
        ),
        cooldowns=(
            _cd("Icy Veins", "Eisige Adern", (12472, 131078), 180),
            _cd("Frozen Orb", "Gefrorene Kugel", (84714,), 60),
            _MIRROR_IMAGE,
            _ALTER_TIME,
            _ICE_BLOCK,
            _ICE_BARRIER,
            _TIME_WARP,
        ),
    ),

    #
    # --------------------------------------------------
    # Mönch
    # --------------------------------------------------
    #

    SpecAbilities(
        "Monk", "Braumeister",
        auras=(
            _buff("Shuffle", "Beinarbeit", (115307,), 90.0),
            _buff("Elusive Brew", "Flüchtiges Gebräu", (115308,), 25.0),
            _buff("Guard", "Schutz", (115295,), 40.0),
        ),
        cooldowns=(
            _cd("Guard", "Schutz", (115295,), 30, CD_DEFENSIVE),
            _cd(
                "Elusive Brew", "Flüchtiges Gebräu",
                (115308,), 60, CD_DEFENSIVE,
            ),
            _FORTIFYING_BREW,
            _cd(
                "Zen Meditation", "Zenmeditation",
                (115176,), 180, CD_DEFENSIVE,
            ),
            _DAMPEN_HARM,
            _DIFFUSE_MAGIC,
            _RING_OF_PEACE,
        ),
    ),

    SpecAbilities(
        "Monk", "Nebelwirker",
        auras=(
            _hot("Renewing Mist", "Erneuernder Nebel", (119611,), 85.0),
            _hot(
                "Enveloping Mist", "Einhüllender Nebel",
                (132120,), 30.0, True,
            ),
        ),
        cooldowns=(
            _cd("Revival", "Belebung", (115310,), 180, CD_HEAL),
            _cd("Life Cocoon", "Lebenskokon", (116849,), 120, CD_HEAL),
            _cd(
                "Thunder Focus Tea", "Tee der Donnerfokussierung",
                (116680,), 45, CD_HEAL,
            ),
            _cd("Mana Tea", "Manatee", (115294,), 0, CD_HEAL, True),
            _FORTIFYING_BREW,
            _DAMPEN_HARM,
            _DIFFUSE_MAGIC,
        ),
    ),

    SpecAbilities(
        "Monk", "Windwandler",
        auras=(
            _buff("Tigereye Brew", "Tigeraugengebräu", (116740,), 30.0),
            _dot("Blackout Kick", "Blackout-Tritt", (100784,), 80.0, True),
        ),
        cooldowns=(
            _cd("Tigereye Brew", "Tigeraugengebräu", (116740,), 60),
            _cd("Energizing Brew", "Belebendes Gebräu", (115288,), 60),
            _cd(
                "Invoke Xuen, the White Tiger",
                "Xuen den Weißen Tiger beschwören",
                (123904,), 180, CD_PERSONAL, True,
            ),
            _cd(
                "Touch of Karma", "Karmaberührung",
                (122470, 124280), 90, CD_DEFENSIVE,
            ),
            _FORTIFYING_BREW,
            _DAMPEN_HARM,
            _DIFFUSE_MAGIC,
            _RING_OF_PEACE,
        ),
    ),

    #
    # --------------------------------------------------
    # Paladin
    # --------------------------------------------------
    #

    SpecAbilities(
        "Paladin", "Heilig",
        auras=(
            _hot("Beacon of Light", "Flamme des Glaubens", (53563,), 95.0),
            _hot(
                "Eternal Flame", "Ewige Flamme",
                (114163,), 60.0, True,
            ),
            _hot(
                "Illuminated Healing", "Erleuchtete Heilung",
                (86273,), 0.0, True,
            ),
        ),
        cooldowns=(
            _cd(
                "Guardian of Ancient Kings",
                "Wächter der Uralten Könige",
                (86669,), 300, CD_HEAL,
            ),
            _AVENGING_WRATH,
            _DIVINE_FAVOR,
            _DEVOTION_AURA,
            _HOLY_AVENGER,
            _HAND_OF_SACRIFICE,
            _LAY_ON_HANDS,
            _DIVINE_PROTECTION,
            _DIVINE_SHIELD,
        ),
    ),

    SpecAbilities(
        "Paladin", "Schutz",
        auras=(
            _buff(
                "Shield of the Righteous", "Schild der Rechtschaffenen",
                (132403,), 55.0,
            ),
            _buff(
                "Sacred Shield", "Heiliger Schild",
                (65148,), 90.0, True,
            ),
            _buff(
                "Bastion of Glory", "Bastion des Ruhms",
                (114637,), 0.0, True,
            ),
        ),
        cooldowns=(
            _cd(
                "Ardent Defender", "Unermüdlicher Verteidiger",
                (31850,), 180, CD_DEFENSIVE,
            ),
            _cd(
                "Guardian of Ancient Kings",
                "Wächter der Uralten Könige",
                (86659,), 300, CD_DEFENSIVE,
            ),
            _DIVINE_PROTECTION,
            _AVENGING_WRATH,
            _HOLY_AVENGER,
            _DEVOTION_AURA,
            _HAND_OF_SACRIFICE,
            _LAY_ON_HANDS,
            _DIVINE_SHIELD,
        ),
    ),

    SpecAbilities(
        "Paladin", "Vergeltung",
        auras=(
            _dot("Censure", "Tadel", (31803,), 95.0),
            _buff("Inquisition", "Inquisition", (84963,), 95.0),
        ),
        cooldowns=(
            _AVENGING_WRATH,
            _cd(
                "Guardian of Ancient Kings",
                "Wächter der Uralten Könige",
                (86698,), 300,
            ),
            _HOLY_AVENGER,
            _cd(
                "Execution Sentence", "Richtspruch",
                (114157,), 60, CD_PERSONAL, True,
            ),
            _DIVINE_PROTECTION,
            _DIVINE_SHIELD,
            _DEVOTION_AURA,
            _HAND_OF_SACRIFICE,
            _LAY_ON_HANDS,
        ),
    ),

    #
    # --------------------------------------------------
    # Priester
    # --------------------------------------------------
    #

    SpecAbilities(
        "Priest", "Disziplin",
        auras=(
            _hot("Power Word: Shield", "Machtwort: Schild", (17,), 60.0),
            _hot("Divine Aegis", "Göttliche Aegis", (47753,), 40.0),
            _hot("Renew", "Erneuerung", (139,), 30.0, True),
        ),
        cooldowns=(
            _cd(
                "Power Word: Barrier", "Machtwort: Barriere",
                (62618,), 180, CD_HEAL,
            ),
            _cd(
                "Pain Suppression", "Schmerzunterdrückung",
                (33206,), 180, CD_HEAL,
            ),
            _cd("Spirit Shell", "Geisterhülle", (109964,), 60, CD_HEAL, True),
            _cd("Divine Hymn", "Gotteshymne", (64843, 64844), 180, CD_HEAL),
            _POWER_INFUSION,
            _SHADOWFIEND,
            _MINDBENDER,
            _DESPERATE_PRAYER,
            _MASS_DISPEL,
        ),
    ),

    SpecAbilities(
        "Priest", "Heilig",
        auras=(
            _hot("Renew", "Erneuerung", (139,), 70.0),
            _hot("Echo of Light", "Echo des Lichts", (77489,), 0.0, True),
        ),
        cooldowns=(
            _cd("Divine Hymn", "Gotteshymne", (64843, 64844), 180, CD_HEAL),
            _cd(
                "Guardian Spirit", "Schutzgeist",
                (47788,), 180, CD_HEAL,
            ),
            _cd("Lightwell", "Lichtbrunnen", (724,), 180, CD_HEAL, True),
            _cd(
                "Hymn of Hope", "Hymne der Hoffnung",
                (64901,), 360, CD_HEAL, True,
            ),
            _POWER_INFUSION,
            _SHADOWFIEND,
            _MINDBENDER,
            _DESPERATE_PRAYER,
            _MASS_DISPEL,
        ),
    ),

    SpecAbilities(
        "Priest", "Schatten",
        auras=(
            _dot("Shadow Word: Pain", "Schattenwort: Schmerz", (589,), 95.0),
            _dot("Vampiric Touch", "Vampirberührung", (34914,), 95.0),
            _dot(
                "Devouring Plague", "Verschlingende Seuche",
                (2944,), 40.0, True,
            ),
        ),
        cooldowns=(
            _SHADOWFIEND,
            _MINDBENDER,
            _POWER_INFUSION,
            _cd("Dispersion", "Dispersion", (47585,), 120, CD_DEFENSIVE),
            _DESPERATE_PRAYER,
            _MASS_DISPEL,
        ),
    ),

    #
    # --------------------------------------------------
    # Schurke
    # --------------------------------------------------
    #

    SpecAbilities(
        "Rogue", "Meucheln",
        auras=(
            _RUPTURE,
            _DEADLY_POISON,
            _SLICE_AND_DICE,
            _dot("Garrote", "Erdrosseln", (703,), 20.0, True),
        ),
        cooldowns=(
            _cd("Vendetta", "Vendetta", (79140,), 120),
            _SHADOW_BLADES,
            _CLOAK_OF_SHADOWS,
            _EVASION,
            _FEINT,
            _SMOKE_BOMB,
        ),
    ),

    SpecAbilities(
        "Rogue", "Kampf",
        auras=(
            _SLICE_AND_DICE,
            _dot("Revealing Strike", "Enthüllender Stoß", (84617,), 90.0),
            _DEADLY_POISON,
            _RUPTURE,
        ),
        cooldowns=(
            _cd("Adrenaline Rush", "Adrenalinrausch", (13750,), 180),
            _cd(
                "Killing Spree", "Mordlust", (51690,), 120,
                aliases=("Blutrausch",),
            ),
            _SHADOW_BLADES,
            _CLOAK_OF_SHADOWS,
            _EVASION,
            _FEINT,
            _SMOKE_BOMB,
        ),
    ),

    SpecAbilities(
        "Rogue", "Täuschung",
        auras=(
            _RUPTURE,
            _dot("Hemorrhage", "Blutsturz", (89775,), 90.0),
            _SLICE_AND_DICE,
            _DEADLY_POISON,
        ),
        cooldowns=(
            _cd("Shadow Dance", "Schattentanz", (51713,), 60),
            _cd("Vanish", "Verschwinden", (1856,), 120),
            _SHADOW_BLADES,
            _CLOAK_OF_SHADOWS,
            _EVASION,
            _FEINT,
            _SMOKE_BOMB,
        ),
    ),

    #
    # --------------------------------------------------
    # Schamane
    # --------------------------------------------------
    #

    SpecAbilities(
        "Shaman", "Elementar",
        auras=(
            _FLAME_SHOCK,
            _buff("Lightning Shield", "Blitzschlagschild", (324,), 95.0),
        ),
        cooldowns=(
            _cd(
                "Ascendance", "Aszendenz",
                (114050, 114049), 180, CD_PERSONAL, True,
            ),
            _ELEMENTAL_MASTERY,
            _FIRE_ELEMENTAL,
            _HEALING_TIDE,
            _SPIRIT_LINK,
            _ANCESTRAL_GUIDANCE,
            _SHAMANISTIC_RAGE,
            _ASTRAL_SHIFT,
        ),
    ),

    SpecAbilities(
        "Shaman", "Verstärkung",
        auras=(
            _FLAME_SHOCK,
            _buff("Lightning Shield", "Blitzschlagschild", (324,), 95.0),
            _buff("Maelstrom Weapon", "Mahlstromwaffe", (53817,), 0.0, True),
        ),
        cooldowns=(
            _cd("Feral Spirit", "Wildgeist", (51533,), 120),
            _cd(
                "Ascendance", "Aszendenz",
                (114051, 114049), 180, CD_PERSONAL, True,
            ),
            _ELEMENTAL_MASTERY,
            _FIRE_ELEMENTAL,
            _HEALING_TIDE,
            _SPIRIT_LINK,
            _ANCESTRAL_GUIDANCE,
            _SHAMANISTIC_RAGE,
            _ASTRAL_SHIFT,
        ),
    ),

    SpecAbilities(
        "Shaman", "Wiederherstellung",
        auras=(
            _hot("Riptide", "Springflut", (61295,), 85.0),
            _hot("Earth Shield", "Erdschild", (974,), 95.0),
            _hot("Earthliving", "Erdleben", (51945,), 0.0, True),
        ),
        cooldowns=(
            _HEALING_TIDE,
            _SPIRIT_LINK,
            _cd(
                "Mana Tide Totem", "Totem der Manaflut",
                (16190,), 180, CD_HEAL,
            ),
            _cd(
                "Ascendance", "Aszendenz",
                (114052, 114049), 180, CD_HEAL, True,
            ),
            _cd(
                "Spiritwalker's Grace", "Anmut des Geisterwandlers",
                (79206,), 120, CD_HEAL,
            ),
            _ANCESTRAL_GUIDANCE,
            _ASTRAL_SHIFT,
        ),
    ),

    #
    # --------------------------------------------------
    # Hexenmeister
    # --------------------------------------------------
    #

    SpecAbilities(
        "Warlock", "Gebrechen",
        auras=(
            _dot("Agony", "Agonie", (980, 131737), 95.0),
            _CORRUPTION,
            _dot(
                "Unstable Affliction", "Instabiles Gebrechen",
                (30108, 131736), 95.0,
            ),
            _dot("Haunt", "Heimsuchung", (48181,), 40.0, True),
        ),
        cooldowns=(
            _cd(
                "Dark Soul: Misery", "Finstere Seele: Elend",
                (113860,), 120,
            ),
            _SUMMON_DOOMGUARD,
            _SUMMON_INFERNAL,
            _UNENDING_RESOLVE,
            _DARK_BARGAIN,
            _SACRIFICIAL_PACT,
            _SOULSTONE,
        ),
    ),

    SpecAbilities(
        "Warlock", "Dämonologie",
        auras=(
            _CORRUPTION,
            _dot("Doom", "Verdammnis", (603,), 95.0),
            _dot("Shadowflame", "Schattenflamme", (47960,), 60.0, True),
        ),
        cooldowns=(
            _cd(
                "Dark Soul: Knowledge", "Finstere Seele: Wissen",
                (113861,), 120,
            ),
            _SUMMON_DOOMGUARD,
            _SUMMON_INFERNAL,
            _UNENDING_RESOLVE,
            _DARK_BARGAIN,
            _SOULSTONE,
        ),
    ),

    SpecAbilities(
        "Warlock", "Zerstörung",
        auras=(
            _dot("Immolate", "Feuerbrand", (348,), 90.0),
        ),
        cooldowns=(
            _cd(
                "Dark Soul: Instability", "Finstere Seele: Instabilität",
                (113858,), 120,
            ),
            _SUMMON_DOOMGUARD,
            _SUMMON_INFERNAL,
            _UNENDING_RESOLVE,
            _DARK_BARGAIN,
            _SACRIFICIAL_PACT,
            _SOULSTONE,
        ),
    ),

    #
    # --------------------------------------------------
    # Krieger
    # --------------------------------------------------
    #

    SpecAbilities(
        "Warrior", "Waffen",
        auras=(
            _DEEP_WOUNDS,
            _COLOSSUS_SMASH,
            _dot("Rend", "Verwunden", (772,), 90.0),
        ),
        cooldowns=(
            _RECKLESSNESS,
            _AVATAR,
            _BLOODBATH,
            _SKULL_BANNER,
            _RALLYING_CRY,
            _DEMORALIZING_BANNER,
            _DIE_BY_THE_SWORD,
            _BERSERKER_RAGE,
        ),
    ),

    SpecAbilities(
        "Warrior", "Furor",
        auras=(
            _DEEP_WOUNDS,
            _COLOSSUS_SMASH,
            _buff("Enrage", "Wutanfall", (12880,), 40.0),
        ),
        cooldowns=(
            _RECKLESSNESS,
            _AVATAR,
            _BLOODBATH,
            _SKULL_BANNER,
            _RALLYING_CRY,
            _DEMORALIZING_BANNER,
            _DIE_BY_THE_SWORD,
            _BERSERKER_RAGE,
        ),
    ),

    SpecAbilities(
        "Warrior", "Schutz",
        auras=(
            _buff("Shield Block", "Schildblock", (132404,), 55.0),
            _buff("Shield Barrier", "Schildbarriere", (112048,), 20.0),
            _DEEP_WOUNDS,
        ),
        cooldowns=(
            _cd("Shield Wall", "Schildwall", (871,), 180, CD_DEFENSIVE),
            _cd(
                "Last Stand", "Letztes Gefecht",
                (12975,), 180, CD_DEFENSIVE,
            ),
            _cd(
                "Demoralizing Banner", "Demoralisierendes Banner",
                (114203,), 180, CD_RAID,
            ),
            _cd("Vigilance", "Wachsamkeit", (114030,), 120, CD_RAID, True),
            _RALLYING_CRY,
            _RECKLESSNESS,
            _AVATAR,
            _BERSERKER_RAGE,
        ),
    ),

)


#
# --------------------------------------------------
# Index
# --------------------------------------------------
#
# Beim Import gebaut - dieselbe Bauart wie in analyzer/data/specs.py
# und analyzer/data/avoidable.py. Jedes Nachschlagen ist danach ein
# Wörterbuchzugriff, was zählt: die Anreicherung läuft bei einer
# Wiedergabe viermal je Sekunde über alle 25 Spieler.
#


def _key(value: str) -> str:
    """
    Vergleichsform eines Namens: kleingeschrieben, ohne Leerzeichen und
    Satzzeichen. "Machtwort: Schild", "machtwort schild" und
    "MACHTWORT:SCHILD" werden damit derselbe Schlüssel.
    """

    return "".join(
        char
        for char in (value or "").casefold()
        if char.isalnum()
    )


def normalize_name(value: str) -> str:
    """
    Die Vergleichsform eines Fähigkeitsnamens - öffentlich, weil die
    Anreicherung (analyzer/analysis/spec_reference.py) dieselbe Form
    braucht, um gemeldete und erwartete Zeilen als dieselbe Fähigkeit
    zu erkennen. Zwei Schreibweisen dieser Normalisierung wären zwei
    Ergebnisse.
    """

    return _key(value)


def _build_index() -> dict[tuple[str, str], SpecAbilities]:

    table: dict[tuple[str, str], SpecAbilities] = {}

    for entry in SPEC_ABILITIES:

        spec = spec_table.find(entry.class_name, entry.spec)

        #
        # Über die Spec-Tabelle indizieren statt über die eigene
        # Schreibweise: dort stehen englische Namen, Umlautvarianten
        # und die Aliase, die WarcraftLogs tatsächlich schickt. Zwei
        # getrennte Namenslisten wären genau die Art Doppelpflege, an
        # der die Spec-Erkennung schon einmal still gescheitert ist.
        #

        names = (
            (spec.name, spec.english)
            if spec is not None
            else (entry.spec,)
        )

        for name in names:
            table[(_key(entry.class_name), _key(name))] = entry

    return table


_BY_SPEC: dict[tuple[str, str], SpecAbilities] = _build_index()


def _build_aura_index() -> dict[int, TrackedAura]:

    table: dict[int, TrackedAura] = {}

    for entry in SPEC_ABILITIES:

        for aura in entry.auras:

            for spell_id in aura.spell_ids:
                table.setdefault(spell_id, aura)

    return table


def _build_name_index() -> dict[str, TrackedAura]:

    table: dict[str, TrackedAura] = {}

    for entry in SPEC_ABILITIES:

        for aura in entry.auras:

            for name in aura.names:
                table.setdefault(_key(name), aura)

    return table


_AURA_BY_ID: dict[int, TrackedAura] = _build_aura_index()

_AURA_BY_NAME: dict[str, TrackedAura] = _build_name_index()


def _build_ability_index() -> tuple[dict[int, object], dict[str, object]]:
    """
    Auren **und** Cooldowns über alle Specs - der spec-unabhängige
    Weg, den `display_name()` braucht: eine Raid-Cooldown-Liste nennt
    ihren Wirker, aber nicht dessen Spezialisierung.
    """

    by_id: dict[int, object] = {}

    by_name: dict[str, object] = {}

    for entry in SPEC_ABILITIES:

        for ability in (*entry.auras, *entry.cooldowns):

            for spell_id in ability.spell_ids:
                by_id.setdefault(spell_id, ability)

            for name in ability.names:
                by_name.setdefault(_key(name), ability)

    return by_id, by_name


_BY_ID, _BY_NAME_ANY = _build_ability_index()


#
# --------------------------------------------------
# Nachschlagen
# --------------------------------------------------
#


def for_spec(class_name: str, spec_name: str) -> SpecAbilities | None:
    """
    Der Referenzbestand einer Spezialisierung, oder None.

    Unbekanntes liefert None statt einer leeren Hülle: "diese Spec
    kenne ich nicht" und "diese Spec hat nichts" sind verschiedene
    Aussagen, und nur die erste darf die Anreicherung stillhalten
    lassen.
    """

    spec = spec_table.find(class_name, spec_name)

    if spec is not None:

        found = _BY_SPEC.get((_key(spec.class_name), _key(spec.name)))

        if found is not None:
            return found

    return _BY_SPEC.get((_key(class_name), _key(spec_name)))


def for_actor(actor) -> SpecAbilities | None:
    """
    Derselbe Zugriff für einen Spieler aus dem Snapshot.

    Fehlt die Spezialisierung, entscheidet **Klasse und Rolle** - aber
    nur, wenn beide zusammen eindeutig sind: ein heilender Druide kann
    nur Wiederherstellung sein, ein Krieger, der tankt, nur Schutz.
    Ein heilender Priester dagegen ist Disziplin *oder* Heilig, und
    dann bleibt es bei "unbekannt". Diese Rückfallebene ist nicht
    kosmetisch: eine Quelle, die `spec` nicht mitschickt (der
    Live-Endpunkt tut das für Heiler regelmäßig), bekäme sonst für
    ihren halben Raid keine einzige Referenzzeile.
    """

    class_name = getattr(actor, "class_name", "")

    found = for_spec(class_name, getattr(actor, "spec", ""))

    if found is not None:
        return found

    role = getattr(actor, "role", "")

    if not role:
        return None

    candidates = [
        spec
        for spec in spec_table.specs_for_class(class_name)
        if spec.role == role
    ]

    if len(candidates) != 1:
        return None

    return for_spec(candidates[0].class_name, candidates[0].name)


#
# Wonach `match()` sucht. Manche Fähigkeiten sind beides: "Schutz"
# des Braumeisters ist ein Cooldown, den man drückt, **und** ein
# Schild mit einer Wirkungsdauer - unter derselben Spell-ID. Ohne
# diese Angabe entschiede die Reihenfolge im Verzeichnis, welcher der
# beiden Einträge zurückkommt, und die gemeldete Cooldown-Zeile bekäme
# die Abklingzeit einer Aura, also keine.
#

KIND_AURA = "aura"

KIND_COOLDOWN = "cooldown"


def _build_spec_lookup() -> dict[tuple[str, str], dict]:
    """
    Je Spezialisierung ein Verzeichnis nach Spell-ID und nach
    Namensschlüssel, getrennt nach Auren und Cooldowns.

    Beim Import gebaut, weil `match()` im heißen Pfad liegt: bei einer
    Wiedergabe läuft die Anreicherung viermal je Sekunde über bis zu
    150 gemeldete Zeilen. Als lineare Suche mit
    Namensnormalisierung je Vergleich war das der teuerste Posten
    eines Bildes.
    """

    table: dict[tuple[str, str], dict] = {}

    for entry in SPEC_ABILITIES:

        index = {
            KIND_AURA: ({}, {}),
            KIND_COOLDOWN: ({}, {}),
        }

        for kind, abilities in (
            (KIND_AURA, entry.auras),
            (KIND_COOLDOWN, entry.cooldowns),
        ):

            by_id, by_name = index[kind]

            for ability in abilities:

                for spell_id in ability.spell_ids:
                    by_id.setdefault(spell_id, ability)

                for name in ability.names:
                    by_name.setdefault(_key(name), ability)

        table[(entry.class_name, entry.spec)] = index

    return table


_SPEC_LOOKUP: dict[tuple[str, str], dict] = _build_spec_lookup()

_EMPTY_INDEX = {KIND_AURA: ({}, {}), KIND_COOLDOWN: ({}, {})}


def match(
    abilities: SpecAbilities | None,
    name: str = "",
    spell_id: int = 0,
    prefer: str = KIND_AURA,
) -> TrackedAura | TrackedCooldown | None:
    """
    Der Eintrag einer Spezialisierung zu einem gemeldeten Namen oder
    einer Spell-ID.

    Erst die ID, dann der Name - die ID ist die einzige Angabe, die
    keine Sprache hat. `prefer` entscheidet nur bei Fähigkeiten, die
    in beiden Listen stehen; gefunden wird auch die jeweils andere.
    """

    if abilities is None:
        return None

    index = _SPEC_LOOKUP.get(
        (abilities.class_name, abilities.spec),
        _EMPTY_INDEX,
    )

    order = (
        (KIND_COOLDOWN, KIND_AURA)
        if prefer == KIND_COOLDOWN
        else (KIND_AURA, KIND_COOLDOWN)
    )

    if spell_id:

        for kind in order:

            found = index[kind][0].get(spell_id)

            if found is not None:
                return found

    key = _key(name)

    if not key:
        return None

    for kind in order:

        found = index[kind][1].get(key)

        if found is not None:
            return found

    return None


def aura_kind(name: str = "", spell_id: int = 0) -> str:
    """
    Zu welcher der drei Listen ein Effekt gehört - **spec-unabhängig**.

    Der Grund dafür, dass diese Frage überhaupt ohne Spezialisierung
    beantwortbar sein muss: eine Quelle, die alles in einen Topf legt
    (oder einen HoT unter die Buffs sortiert), würde sonst ganze
    Karten leer lassen, obwohl die Daten da sind. Ein unbekannter
    Effekt liefert einen leeren String - dann bleibt es bei der
    Einordnung der Quelle.
    """

    if spell_id:

        found = _AURA_BY_ID.get(spell_id)

        if found is not None:
            return found.kind

    found = _AURA_BY_NAME.get(_key(name))

    return found.kind if found is not None else ""


def display_name(name: str = "", spell_id: int = 0) -> str:
    """
    Der deutsche Name einer Fähigkeit, spec-unabhängig - oder der
    gemeldete Name, wenn sie unbekannt ist.

    Damit stehen in der Oberfläche nicht dieselbe Fähigkeit einmal
    englisch (weil sie aus der Raid-Cooldown-Liste kommt) und einmal
    deutsch (weil sie aus der Spec-Anreicherung kommt).
    """

    found = None

    if spell_id:
        found = _BY_ID.get(spell_id)

    if found is None:
        found = _BY_NAME_ANY.get(_key(name))

    if found is None:
        return name

    return getattr(found, "german", "") or name


def translations() -> dict[str, tuple[str, ...]]:
    """
    Englischer Name -> deutsche Schreibweisen, über alle Specs.

    Für analyzer.data.player_abilities: die Kriterien der Academy
    nennen Fähigkeiten englisch, ein deutscher Bericht liefert sie
    deutsch. Statt beide Listen von Hand gleichzuhalten, zieht die
    dortige Tabelle diese hier mit ein - eine zweite Liste würde
    driften, und das Symptom wäre eine Lektion, die dauerhaft "keine
    Daten" sagt.
    """

    table: dict[str, set[str]] = {}

    for entry in SPEC_ABILITIES:

        for ability in (*entry.auras, *entry.cooldowns):

            if not ability.english:
                continue

            for german in (ability.german, *ability.aliases):

                if german and german != ability.english:
                    table.setdefault(ability.english, set()).add(german)

    return {
        english: tuple(sorted(german))
        for english, german in table.items()
    }


def known_specs() -> tuple[tuple[str, str], ...]:
    """
    (Klasse, Spezialisierung) aller hinterlegten Einträge - für Tests
    und die Vollständigkeitsprüfung.
    """

    return tuple(
        (entry.class_name, entry.spec)
        for entry in SPEC_ABILITIES
    )
