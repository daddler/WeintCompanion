"""
Die **Zielausrüstung** aus dem Sim - gelesen, normalisiert, weiter-
gereicht.

WARUM ES DIESE DATEI GIBT.

WeintCodex empfiehlt Sockelsteine und Umschmiedungen aus den
Wertegewichten eines Spec-Profils. Das ist eine eigene Optimierung
neben der des Sims - und damit die zweite Antwort auf eine Frage, die
schon eine hat. Die gemeldeten Fehlgriffe bei Steinen sind fast alle
von dieser Sorte: nicht "die Rechnung ist falsch", sondern "es wird
überhaupt gerechnet, obwohl wowsims die Entscheidung längst getroffen
hat".

Der Weg **in** den Sim gab es schon (`core/wowsims_link.py`). Was
fehlte, war der Rückweg: **das Ergebnis** eines Optimierungslaufs -
welchen Stein und welche Umschmiedung der Sim für jeden Platz vorsieht.
Diese Datei liest ihn und macht daraus einen Zielzustand, den
WeintCodex nur noch mit dem Iststand vergleicht.

DREI GESTALTEN, EINE STRUKTUR.

Der Sim gibt sein Ergebnis in drei Formen heraus, und alle drei landen
hier:

1. **Adresse** (`…/mop/<klasse>/<spec>/?…#<base64>`) - *Export → Link*.
   Der Rumpf ist genau die Nachricht, die `core/wowsims_link.py`
   schreibt; gelesen wird er mit `decode_fragment()` von dort.
2. **Sim-JSON** (`IndividualSimSettings`) - *Export → JSON*. Die
   Ausrüstung steht unter `player.equipment.items`.
3. **Addon-JSON** (`gear.items`) - die Form des WowSimsExporter, die
   auch *Export → Addon* im Sim ausgibt.

`SimItem` aus `core/wowsims_link.py` ist in allen drei Fällen das Ziel
- **keine zweite Struktur daneben.** Sie trägt bereits genau die
Felder, um die es geht (`item_id`, `gems`, `reforging`, `enchant`), und
zwei Datentypen für dieselbe Sache laufen ab der ersten Änderung
auseinander.

WAS DIESE DATEI NICHT WEISS - UND DESHALB SAGT.

**Ob das Ergebnis wirklich optimiert ist, steht in keiner der drei
Formen drin.** Der Sim schreibt heraus, was gerade in seiner Oberfläche
eingestellt ist. Wer importiert und sofort exportiert, bekommt seinen
Ausgangszustand zurück - und der sähe hier aus wie ein Optimierungs-
ergebnis. Deshalb gibt es `compare()`: die Seite stellt den Zielzustand
neben das, was der WowSimsExporter als **angelegt** meldet, und sagt,
wie viele Plätze sich unterscheiden. Bei null Unterschieden steht dort
"identisch mit deiner angelegten Ausrüstung - im Sim lief vermutlich
noch kein Optimierungslauf", und nicht schweigend "übernommen".

Das ist keine Vorsicht um ihrer selbst willen: eine Zielausrüstung, die
in Wahrheit der Iststand ist, brächte im Spiel **jede** Empfehlung zum
Schweigen ("alles schon richtig") - und das wäre von einer perfekt
optimierten Ausrüstung nicht zu unterscheiden. Dieselbe Linie wie
`stars == 0` im Analyzer.

Rein: kein Qt, kein `httpx`, keine Datei - wie `core/stat_weights.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from core.wowsims_link import (
    DecodeError,
    SimItem,
    decode_fragment,
    fragment_of,
    item_from_payload,
)
from core.stat_weights import SPECS as SIM_SPECS
from core.wowsims_export import SPEC_KEYS


#
# --------------------------------------------------
# Ausrüstungsplatz: Position im Sim -> Platz im Spiel
# --------------------------------------------------
#
# Der Sim führt die Ausrüstung als **Liste**, und die Position darin
# ist der Platz. Die Reihenfolge stammt aus `proto/common.proto`:
#
#     enum ItemSlot {
#         ItemSlotHead = 0;  ItemSlotNeck = 1;   ItemSlotShoulder = 2;
#         ItemSlotBack = 3;  ItemSlotChest = 4;  ItemSlotWrist = 5;
#         ItemSlotHands = 6; ItemSlotWaist = 7;  ItemSlotLegs = 8;
#         ItemSlotFeet = 9;  ItemSlotFinger1 = 10; ItemSlotFinger2 = 11;
#         ItemSlotTrinket1 = 12; ItemSlotTrinket2 = 13;
#         ItemSlotMainHand = 14; ItemSlotOffHand = 15; ItemSlotRanged = 16;
#     }
#
# Die Zahlen daneben sind die Plätze des Spiels (`INVSLOT_*`), also
# genau die, mit denen `EQUIP_SLOTS` in `modules/charakter.lua` drüben
# arbeitet.
#
# DAS IST DIE GANZE ANTWORT AUF RING 1 / RING 2, SCHMUCK 1 / SCHMUCK 2
# UND HAUPT- / NEBENHAND. Zugeordnet wird über die **Position**, nie
# über den Namen und nie über die Gegenstandsnummer allein - zwei
# gleiche Ringe sind zwei Ringe, und welcher von beiden welche Steine
# bekommt, entscheidet der Platz.
#

SLOT_IDS: tuple[int, ...] = (
    1,   # Kopf
    2,   # Hals
    3,   # Schultern
    15,  # Umhang
    5,   # Brust
    9,   # Handgelenke
    10,  # Hände
    6,   # Taille
    7,   # Beine
    8,   # Füße
    11,  # Finger 1
    12,  # Finger 2
    13,  # Schmuck 1
    14,  # Schmuck 2
    16,  # Haupthand
    17,  # Nebenhand
    18,  # Distanz / Relikt
)


SLOT_NAMES: dict[int, str] = {
    1: "Kopf",
    2: "Hals",
    3: "Schultern",
    5: "Brust",
    6: "Taille",
    7: "Beine",
    8: "Füße",
    9: "Handgelenke",
    10: "Hände",
    11: "Finger 1",
    12: "Finger 2",
    13: "Schmuck 1",
    14: "Schmuck 2",
    15: "Umhang",
    16: "Haupthand",
    17: "Nebenhand",
    18: "Distanz",
}


#
# Woher der Zielzustand gelesen wurde. Reicht bis ins Spiel durch und
# steht dort an der Zeile - "aus dem Sim (Adresse)" und "aus dem
# Sim (JSON)" sind für eine Rückfrage zwei verschiedene Auskünfte.
#

SOURCE_LINK = "wowsims_link"

SOURCE_JSON = "wowsims_json"

SOURCE_ADDON = "wowsims_addon"


SOURCE_LABELS: dict[str, str] = {
    SOURCE_LINK: "wowsims-Adresse",
    SOURCE_JSON: "wowsims-Ausgabe (JSON)",
    SOURCE_ADDON: "wowsims-Ausgabe (Addon-Form)",
}


#
# Der grösste Umschmiedewert, den der Client kennt: acht Werte, jeder
# in jeden anderen ausser sich selbst, also 8 × 7 = 56 Paare ab 113
# (siehe `data/reforge.lua` drüben, `TABLE_BASE = 112`). Was ausserhalb
# liegt, ist keine Umschmiedung - und wird verworfen statt
# weitergereicht, denn im Spiel würde daraus eine laufende Nummer, die
# es nicht gibt.
#

REFORGE_MIN = 113

REFORGE_MAX = 168


@dataclass(frozen=True)
class TargetItem:
    """
    Ein Platz im Zielzustand.

    `slot` ist der Platz des Spiels, `gems` die Steine **in
    Sockelreihenfolge** - eine 0 ist ein Sockel, der leer bleiben soll,
    und sie muss stehen bleiben: die Position benennt den Sockel.
    """

    slot: int

    item_id: int = 0

    gems: tuple[int, ...] = ()

    reforging: int = 0

    enchant: int = 0

    @property
    def slot_name(self) -> str:

        return SLOT_NAMES.get(self.slot, f"Platz {self.slot}")

    @property
    def empty(self) -> bool:

        return not self.item_id


@dataclass(frozen=True)
class TargetGear:
    """
    Der Zielzustand einer ganzen Ausrüstung.

    `known` ist die eine Frage, die die Oberfläche stellt. Alles andere
    ist erst dann aussagekräftig.
    """

    known: bool = False

    source: str = ""

    spec_key: str = ""

    character: str = ""

    realm: str = ""

    items: tuple[TargetItem, ...] = ()

    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def source_label(self) -> str:

        return SOURCE_LABELS.get(self.source, self.source or "unbekannt")

    @property
    def item_count(self) -> int:

        return sum(1 for item in self.items if not item.empty)

    @property
    def gem_count(self) -> int:

        return sum(
            1
            for item in self.items
            for gem in item.gems
            if gem
        )

    @property
    def reforge_count(self) -> int:

        return sum(1 for item in self.items if item.reforging)

    @property
    def usable(self) -> bool:
        """
        Ob sich daraus im Spiel etwas ableiten lässt.

        Ohne einen einzigen Gegenstand nein. Ohne einen einzigen Stein
        UND ohne eine einzige Umschmiedung ebenfalls nein - so ein
        Zielzustand sagt über die beiden Fragen, um die es geht, gar
        nichts, und im Spiel sähe er aus wie "alles ist schon richtig".
        """

        return bool(self.item_count) and bool(
            self.gem_count or self.reforge_count
        )

    @property
    def id(self) -> str:
        """
        Kennung des Vorschlags - hängt am **Inhalt**, nicht an der Uhr.

        Dieselbe Regel wie bei den Sim-Gewichten: derselbe Zielzustand
        ist derselbe Vorschlag (und wird im Spiel nicht erneut
        angeboten), ein geänderter ein neuer.
        """

        #
        # LEERE PLAETZE ZAEHLEN NICHT MIT. Sie tragen keine Aussage
        # ueber Steine oder Umschmiedungen, und sie ueberleben die
        # Ablage nicht (`target_gear_store` schreibt nur belegte
        # Plaetze). Zaehlten sie mit, haette derselbe Zielzustand nach
        # einem Neustart der App eine andere Kennung - und im Spiel
        # stuende er als neuer Vorschlag da.
        #

        roh = "|".join(
            "{}:{}:{}:{}:{}".format(
                item.slot,
                item.item_id,
                "-".join(str(gem) for gem in item.gems),
                item.reforging,
                item.enchant,
            )
            for item in self.items
            if not item.empty
        )

        return hashlib.sha1(
            f"{self.spec_key}#{roh}".encode("utf-8")
        ).hexdigest()[:12]


#
# --------------------------------------------------
# Einlesen
# --------------------------------------------------
#


def _clean(value) -> str:

    return value.strip() if isinstance(value, str) else ""


def _reforging(value) -> int:
    """
    Der Umschmiedewert, oder 0.

    Ausserhalb der 56 Paare wird **verworfen**: im Spiel wird daraus
    eine laufende Nummer im Umschmieder, und eine erfundene schmiedet
    etwas anderes, als auf der Seite steht (siehe `data/reforge.lua`).
    """

    number = int(value or 0)

    return number if REFORGE_MIN <= number <= REFORGE_MAX else 0


def _items(specs) -> tuple[TargetItem, ...]:
    """
    Die Liste des Sims auf Plätze abbilden.

    Sie darf **kürzer** sein als `SLOT_IDS` (ein Zweihandkämpfer meldet
    keinen Distanzplatz), aber nie umsortiert: was über die Liste
    hinausragt, fällt weg, statt einen Platz zu erfinden.
    """

    out: list[TargetItem] = []

    for index, spec in enumerate(specs):

        if index >= len(SLOT_IDS):
            break

        out.append(
            TargetItem(
                slot=SLOT_IDS[index],
                item_id=int(spec.item_id or 0),
                gems=tuple(int(gem or 0) for gem in spec.gems),
                reforging=_reforging(spec.reforging),
                enchant=int(spec.enchant or 0),
            )
        )

    return tuple(out)


def _spec_key(char_class: str, spec: str) -> str:

    return SPEC_KEYS.get(
        (_clean(char_class).lower(), _clean(spec).lower()),
        "",
    )


#
# Die Adresse, aus der die Spezialisierung ablesbar ist:
#
#     https://www.wowsims.com/mop/death_knight/frost/?…#…
#
# Sie ist die einzige der drei Gestalten, die den Charakter nicht
# nennt; die Spezialisierung steht dafür im Pfad.
#
# ABGELESEN WIRD SIE AUS `stat_weights.SPECS`, RÜCKWÄRTS. Dieselbe
# Tabelle sagt, wohin der Knopf *Sim öffnen* führt - und die
# Schreibweisen dort sind genau die des Sims (`beast_mastery`,
# `death_knight`) und ausdrücklich nicht die des Exporter-Addons
# (`marksman`, `deathknight`), die `SPEC_KEYS` führt. Zwei Tabellen
# für dieselbe Zuordnung liefen irgendwann auseinander, und dann
# stünde eine Zielausrüstung unter der falschen Spezialisierung -
# was von der richtigen nicht zu unterscheiden wäre.
#

#
# Der ERSTE Eintrag gewinnt, und das ist kein Zufall: die fünf
# `*_OFFENSIVE`-Profile der Tanks zeigen auf die Seite ihrer
# Basis-Spec, stehen in der Tabelle aber dahinter. Ohne diese Regel
# hiesse `…/mop/death_knight/blood/` rückwärts
# `DEATHKNIGHT_BLOOD_OFFENSIVE` - eine Haltung, die der Sim gar nicht
# kennt und die der Spieler nie gewählt hat.
#

_SPEC_BY_URL: dict[str, str] = {}

for _entry in SIM_SPECS:

    _pfad = _entry.url.split("/mop/", 1)[-1].strip("/").lower()

    _SPEC_BY_URL.setdefault(_pfad, _entry.key)


_URL_SPEC = re.compile(
    r"wowsims\.com/mop/([a-z_]+/[a-z_]+)",
    re.IGNORECASE,
)


def _spec_from_url(text: str) -> str:

    hit = _URL_SPEC.search(text or "")

    return _SPEC_BY_URL.get(hit.group(1).lower(), "") if hit else ""


def parse_target(text: str) -> TargetGear | None:
    """
    Ein Sim-Ergebnis in einer seiner drei Gestalten - oder `None`, wenn
    der Text keine davon ist.

    `None` heisst "das war kein Sim-Ergebnis" und ist etwas anderes als
    ein Ergebnis ohne Ausrüstung: der Aufrufer sagt dazu zwei
    verschiedene Sätze (dieselbe Trennung wie in
    `wowsims_export.parse_export()`).
    """

    text = (text or "").strip()

    if not text:
        return None

    #
    # 1) Adresse oder blosser Rumpf. Zuerst geprüft, weil ein
    #    Base64-Rumpf zufällig auch mit "{" beginnen könnte - JSON
    #    dagegen nie mit "http".
    #

    if "wowsims.com" in text or _looks_like_fragment(text):
        return _from_link(text)

    #
    # 2) und 3) JSON, in beiden Formen.
    #

    try:
        payload = json.loads(text)

    except (ValueError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    return _from_json(payload)


def _looks_like_fragment(text: str) -> bool:
    """
    Ein nackter Rumpf: nur Base64-Zeichen, und lang genug, dass er
    keine getippte Zeile sein kann.

    Absichtlich streng. Ein zu breiter Riecher würde eine getippte
    Gewichtung ("Hit 1.77") als kaputte Adresse melden, statt sie den
    Sim-Gewichten zu überlassen - beide Texte kommen in **dasselbe**
    Eingabefeld.
    """

    kompakt = "".join(text.split())

    if len(kompakt) < 40:
        return False

    return bool(re.fullmatch(r"[A-Za-z0-9+/=_-]+", kompakt))


def _from_link(text: str) -> TargetGear:

    rumpf = fragment_of(text)

    if not rumpf:

        return TargetGear(
            source=SOURCE_LINK,
            spec_key=_spec_from_url(text),
            problems=(
                "Die Adresse trägt keine Ausrüstung — im Sim unter "
                "„Export → Link“ kopieren, dann steht sie hinter dem #.",
            ),
        )

    try:
        specs = decode_fragment(rumpf)

    except DecodeError as exc:

        #
        # LAUT SCHEITERN. Ein halb gelesener Rumpf wäre eine Ausrüstung
        # mit fehlenden Plätzen, und die sieht aus wie eine mit freien.
        #

        return TargetGear(
            source=SOURCE_LINK,
            spec_key=_spec_from_url(text),
            problems=(f"Die Adresse war nicht lesbar: {exc}",),
        )

    return _build(SOURCE_LINK, _spec_from_url(text), "", "", specs)


def _from_json(payload: dict) -> TargetGear | None:

    #
    # Sim-Ausgabe: die Ausrüstung sitzt am Spieler.
    #

    player = payload.get("player")

    if isinstance(player, dict):

        equipment = player.get("equipment")

        if isinstance(equipment, dict) and isinstance(
            equipment.get("items"), list
        ):

            return _build(
                SOURCE_JSON,
                _spec_from_json(player),
                _clean(player.get("name")),
                "",
                tuple(
                    item_from_payload(entry)
                    for entry in equipment["items"]
                ),
            )

    #
    # Addon-Form: `gear.items` an der Wurzel. Dieselbe Gestalt, die
    # `wowsims_export.parse_export()` liest - hier wird sie als
    # ZIELzustand gelesen, dort als Iststand. Welche der beiden es ist,
    # entscheidet, wer den Text kopiert hat, und deshalb sagt die Seite
    # es dazu.
    #

    gear = payload.get("gear")

    if isinstance(gear, dict) and isinstance(gear.get("items"), list):

        return _build(
            SOURCE_ADDON,
            _spec_key(payload.get("class"), payload.get("spec")),
            _clean(payload.get("name")).split("-")[0],
            _clean(payload.get("realm")),
            tuple(item_from_payload(entry) for entry in gear["items"]),
        )

    return None


#
# Der Sim schreibt Klasse und Spezialisierung in seiner eigenen
# Schreibweise (`ClassDeathKnight`, und die Spec als Schlüssel des
# Spieler-Objekts wie `frostDeathKnight`). Beides ist eine Tabelle wert
# und keine Ableitung - dieselbe Lehre wie bei `sim_url()`.
#

_SIM_CLASSES: dict[str, str] = {
    "ClassDeathKnight": "deathknight",
    "ClassDruid": "druid",
    "ClassHunter": "hunter",
    "ClassMage": "mage",
    "ClassMonk": "monk",
    "ClassPaladin": "paladin",
    "ClassPriest": "priest",
    "ClassRogue": "rogue",
    "ClassShaman": "shaman",
    "ClassWarlock": "warlock",
    "ClassWarrior": "warrior",
}


#
# Der Schlüssel, unter dem der Sim die Spezialisierungs-Einstellungen
# ablegt (`player.frostDeathKnight`), auf unseren Profilschlüssel.
# Genau die Namen, die das Sim-Repository in `proto/api.proto` unter
# `oneof spec` führt.
#

_SIM_SPECS: dict[str, str] = {
    "bloodDeathKnight": "DEATHKNIGHT_BLOOD",
    "frostDeathKnight": "DEATHKNIGHT_FROST",
    "unholyDeathKnight": "DEATHKNIGHT_UNHOLY",
    "balanceDruid": "DRUID_BALANCE",
    "feralDruid": "DRUID_FERAL",
    "guardianDruid": "DRUID_GUARDIAN",
    "restorationDruid": "DRUID_RESTORATION",
    "beastMasteryHunter": "HUNTER_BEASTMASTERY",
    "marksmanshipHunter": "HUNTER_MARKSMANSHIP",
    "survivalHunter": "HUNTER_SURVIVAL",
    "arcaneMage": "MAGE_ARCANE",
    "fireMage": "MAGE_FIRE",
    "frostMage": "MAGE_FROST",
    "brewmasterMonk": "MONK_BREWMASTER",
    "mistweaverMonk": "MONK_MISTWEAVER",
    "windwalkerMonk": "MONK_WINDWALKER",
    "holyPaladin": "PALADIN_HOLY",
    "protectionPaladin": "PALADIN_PROTECTION",
    "retributionPaladin": "PALADIN_RETRIBUTION",
    "disciplinePriest": "PRIEST_DISCIPLINE",
    "holyPriest": "PRIEST_HOLY",
    "shadowPriest": "PRIEST_SHADOW",
    "assassinationRogue": "ROGUE_ASSASSINATION",
    "combatRogue": "ROGUE_COMBAT",
    "subtletyRogue": "ROGUE_SUBTLETY",
    "elementalShaman": "SHAMAN_ELEMENTAL",
    "enhancementShaman": "SHAMAN_ENHANCEMENT",
    "restorationShaman": "SHAMAN_RESTORATION",
    "afflictionWarlock": "WARLOCK_AFFLICTION",
    "demonologyWarlock": "WARLOCK_DEMONOLOGY",
    "destructionWarlock": "WARLOCK_DESTRUCTION",
    "armsWarrior": "WARRIOR_ARMS",
    "furyWarrior": "WARRIOR_FURY",
    "protectionWarrior": "WARRIOR_PROTECTION",
}


def _spec_from_json(player: dict) -> str:
    """
    Die Spezialisierung einer Sim-Ausgabe.

    Sie steht dort nicht als Feld, sondern als **Name des Blocks**, in
    dem die Spec-Einstellungen liegen. Findet sich keiner, bleibt sie
    leer - dann trägt die Oberfläche die gewählte Spec bei, und der
    Nutzer sieht, welche.
    """

    for key in player:

        spec = _SIM_SPECS.get(key)

        if spec:
            return spec

    return ""


def _build(
    source: str,
    spec_key: str,
    character: str,
    realm: str,
    specs,
) -> TargetGear:

    items = _items(specs)

    problems: list[str] = []

    if not spec_key:

        problems.append(
            "Die Ausgabe nennt keine Spezialisierung, die hier "
            "hinterlegt ist."
        )

    if not any(not item.empty for item in items):
        problems.append("Darin steht kein einziges Ausrüstungsteil.")

    return TargetGear(
        known=True,
        source=source,
        spec_key=spec_key,
        character=character,
        realm=realm,
        items=items,
        problems=tuple(problems),
    )


#
# --------------------------------------------------
# Ziel gegen Ist - die Frage nach dem Optimierungslauf
# --------------------------------------------------
#


@dataclass(frozen=True)
class SlotDiff:

    slot: int

    item_id: int = 0

    same_item: bool = True

    gems_differ: bool = False

    reforge_differs: bool = False

    enchant_differs: bool = False

    #
    # WIEVIELE SOCKEL, NICHT NUR OB EINER. Die Seite sagt seit 3.3.0
    # „7 Sockeländerungen" statt „4 Teile geändert" - eine Zahl, die
    # sich im Spiel nachzählen lässt, ist der Beleg dafür, dass wirklich
    # optimiert wurde. `gems_differ` bleibt daneben stehen: es ist die
    # Frage, die `changed_slots()` stellt, und zwei Namen für dieselbe
    # Zahl liefen ab der ersten Aenderung auseinander.
    #

    gem_changes: int = 0

    @property
    def slot_name(self) -> str:

        return SLOT_NAMES.get(self.slot, f"Platz {self.slot}")

    @property
    def differs(self) -> bool:

        return (
            self.gems_differ
            or self.reforge_differs
            or self.enchant_differs
        )


def compare(target: TargetGear | None, current) -> tuple[SlotDiff, ...]:
    """
    Zielzustand gegen den zuletzt gemeldeten Iststand.

    `current` ist die Ausrüstung, die der WowSimsExporter gemeldet hat
    (`wowsims_export.SimExport.items`, also `SimItem` in derselben
    Reihenfolge). Verglichen wird **je Platz**, nicht als Menge: zwei
    gleiche Ringe sind zwei Ringe.

    **Wofür das da ist.** Der Sim schreibt heraus, was gerade
    eingestellt ist - ob davor ein Optimierungslauf lief, steht in der
    Ausgabe nicht. Ein Zielzustand ohne einen einzigen Unterschied ist
    deshalb der Verdachtsfall: entweder ist bereits alles richtig, oder
    es wurde importiert und sofort wieder exportiert. Die Seite nennt
    beide Möglichkeiten, statt eine davon zu behaupten.

    Ein Platz, auf dem ein **anderer** Gegenstand steckt, zählt nicht
    als Unterschied: dann ist nicht die Optimierung eine andere,
    sondern die Ausrüstung. `same_item` sagt das getrennt.
    """

    if target is None or not target.known:
        return ()

    ist: dict[int, SimItem] = {}

    for index, item in enumerate(current or ()):

        if index < len(SLOT_IDS):
            ist[SLOT_IDS[index]] = item

    out: list[SlotDiff] = []

    for item in target.items:

        if item.empty:
            continue

        gegen = ist.get(item.slot)

        if gegen is None or not gegen.item_id:

            out.append(
                SlotDiff(slot=item.slot, item_id=item.item_id, same_item=False)
            )

            continue

        if gegen.item_id != item.item_id:

            out.append(
                SlotDiff(slot=item.slot, item_id=item.item_id, same_item=False)
            )

            continue

        soll = _gems(item.gems)

        ist_gems = _gems(gegen.gems)

        out.append(
            SlotDiff(
                slot=item.slot,
                item_id=item.item_id,
                same_item=True,
                gems_differ=soll != ist_gems,
                gem_changes=_gem_changes(soll, ist_gems),
                reforge_differs=item.reforging != _reforging(gegen.reforging),
                #
                # Eine fehlende Verzauberung im Ziel ist keine Aussage:
                # der Sim führt sie nur mit, wenn sie eingestellt ist.
                # Sie als Unterschied zu zählen hiesse, jedem eine
                # Änderung zu melden, die keine ist.
                #
                enchant_differs=bool(item.enchant)
                and item.enchant != gegen.enchant,
            )
        )

    return tuple(out)


def _gems(gems) -> tuple[int, ...]:
    """
    Die Steinliste ohne Nullen **am Ende** - die zählen als "kein
    Sockel". Nullen dazwischen bleiben: sie sind ein leerer Sockel, und
    die Position benennt ihn.
    """

    out = [int(gem or 0) for gem in gems or ()]

    while out and not out[-1]:
        out.pop()

    return tuple(out)


def _gem_changes(soll, ist) -> int:
    """
    Wieviele **Sockel** sich unterscheiden - Position für Position.

    Eine 0 im Ziel zählt nicht mit. Sie heisst „das Ziel nennt für
    diesen Sockel keinen Stein" und ausdrücklich nicht „nimm deinen
    Stein heraus"; sie als Änderung zu zählen wäre eine Empfehlung in
    die teure Richtung (dieselbe Regel wie `TG.GemFor` drüben und wie
    `headroom == nil`).
    """

    count = 0

    for index, gem in enumerate(soll):

        if not gem:
            continue

        vorher = ist[index] if index < len(ist) else 0

        if gem != vorher:
            count += 1

    return count


def changed_slots(diffs) -> tuple[SlotDiff, ...]:

    return tuple(diff for diff in diffs if diff.differs)


def foreign_slots(diffs) -> tuple[SlotDiff, ...]:

    return tuple(diff for diff in diffs if not diff.same_item)


#
# --------------------------------------------------
# Hinüber ins Spiel
# --------------------------------------------------
#
# Zwei Wege, aus demselben Grund wie bei den Sim-Gewichten: WoW liest
# seine SavedVariables zur Laufzeit **nicht** erneut, die Zustellung
# über die Addon-Brücke wirkt also erst nach dem nächsten `/reload`.
# Wer gerade im Raid steht, lädt nicht neu - dafür der
# `WCIMPORT:TG:`-String, der ohne Neuladen wirkt. Beide tragen
# dieselben Angaben und landen in derselben Ablage.
#


@dataclass(frozen=True)
class TargetSet:
    """
    Ein abgelegter Zielzustand - der Zielzustand selbst plus die
    Angaben, die erst beim Ablegen entstehen (Zeitpunkt, Charakter).

    Getrennt von `TargetGear`, weil das Einlesen nichts davon weiss:
    eine Adresse nennt keinen Charakter, und die Uhr gehört nicht in
    eine reine Umwandlung.
    """

    gear: TargetGear

    spec_key: str = ""

    character: str = ""

    realm: str = ""

    created: int = 0

    #
    # AUS WELCHEM SIM-LAUF ER STAMMT (seit 3.3.0).
    #
    # Er ändert an dieser Struktur nichts weiter: die Zuordnung im Spiel
    # läuft weiter über Spezialisierung und Gegenstandsnummer, und ein
    # leeres Feld ist genauso gültig wie vorher (jeder Zielzustand, der
    # vor 3.3.0 abgelegt wurde, hat keins). Er beantwortet die eine
    # Frage, die vorher niemand stellen konnte: gehören diese
    # Zielausrüstung und jene Gewichtung zu **einem** Lauf?
    #
    # Siehe `core/sim_run.py`.
    #

    run_id: str = ""

    #
    # DER ZEITSTEMPEL DER AUSRUESTUNG, MIT DER GESIMMT WURDE.
    #
    # Er stammt aus der Uhr des **Spiels** (der WowSimsExporter hat ihn
    # geschrieben) und ist damit die einzige Zahl, die auf beiden Seiten
    # dieselbe ist. Das Addon merkt sich beim *Bereitstellen* denselben
    # Wert und kann daran erkennen, ob das Ankommende zu genau dem Lauf
    # gehört, auf den es wartet — ohne einen zweiten Kanal und ohne eine
    # Vermutung. 0 heisst „nicht feststellbar", nicht „Sekunde 0".
    #

    started_at: int = 0

    @property
    def id(self) -> str:
        return self.gear.id

    @property
    def source(self) -> str:
        return self.gear.source

    @property
    def items(self) -> tuple[TargetItem, ...]:
        return self.gear.items


#
# Die drei Trennzeichen des WCIMPORT-Formats plus der Bindestrich, mit
# dem die Steine eines Gegenstands aneinanderhängen. Alles davon wird
# aus jedem freien Text entfernt - der Charaktername kommt aus dem
# Spiel (dieselbe Regel wie `clean_field()` bei den Sim-Gewichten).
#

_UNSAFE = re.compile(r"[:|,~\r\n\\\"-]")


def clean_field(value: str) -> str:

    return _UNSAFE.sub(" ", (value or "")).strip()


#
# Die Kennung des Laufs geht NICHT durch `clean_field()`: dort fällt der
# Bindestrich weg, weil er innerhalb eines Datensatzes die Steine
# trennt. In einem eigenen `:`-Abschnitt kann er das nicht - dort ist er
# ein gewöhnliches Zeichen, und `SIM-20260909-7F4A` ohne Bindestriche
# wäre eine andere Kennung als die, die überall sonst steht.
#

_RUN_UNSAFE = re.compile(r"[^A-Za-z0-9-]")


def clean_run_id(value: str) -> str:

    return _RUN_UNSAFE.sub("", (value or "")).strip("-")[:32]


def build_transfer(entry: TargetSet) -> str:
    """
    Der Übertragungsstring für den Import im Spiel.

        WCIMPORT:TG:<Spec>:<Kennung>:<Zeit>:<Charakter>:<Quelle>:
            <slot>|<itemId>|<gem1>-<gem2>-<gem3>|<reforge>|<enchant>,…

    Abschnitte mit `:`, Datensätze mit `,`, Felder mit `|` - dieselbe
    Form wie die übrigen Importe, damit im Addon kein zweiter Parser
    entsteht. Die Steine eines Gegenstands hängen mit `-` aneinander,
    weil die drei übrigen Zeichen vergeben sind; sie sind Ziffern, ein
    Bindestrich kann darin nicht vorkommen.

    **Ein leerer Sockel steht als `0`, und die Position zählt.** Ein
    Gegenstand mit drei Sockeln, von denen der mittlere leer bleiben
    soll, schreibt `1234-0-5678` - würde die 0 weggelassen, rutschte
    der dritte Stein in den zweiten Sockel.

    Ein Platz **ohne** Gegenstand fällt weg: das Ziel sagt über einen
    leeren Platz nichts, und ein Datensatz mit lauter Nullen sähe aus
    wie "hier soll nichts hin".
    """

    rows = []

    for item in entry.items:

        if item.empty:
            continue

        gems = "-".join(str(int(gem or 0)) for gem in item.gems)

        rows.append(
            "{}|{}|{}|{}|{}".format(
                item.slot,
                item.item_id,
                gems,
                item.reforging,
                item.enchant,
            )
        )

    fields = [
        clean_field(entry.spec_key),
        entry.id,
        str(int(entry.created or 0)),
        clean_field(entry.character),
        clean_field(entry.source or "wowsims"),
        ",".join(rows),
        #
        # ABSCHNITT 7 IST ANGEHAENGT UND DARF ES BLEIBEN (seit 3.3.0).
        #
        # `TG.ParseTransfer` drüben liest die Felder 1 bis 6 über feste
        # Positionen; was dahinter steht, ignoriert es. Ein älteres
        # WeintCodex bekommt damit genau denselben Zielzustand wie
        # bisher - die Kennung fällt weg, sonst nichts. Das ist der
        # Unterschied zu zwei Umschlägen in einer Zeile, wo genau diese
        # Nachsicht die zweite Auskunft still verschluckt hätte: dort
        # fehlte eine ganze Auskunft, hier nur ihre Herkunft.
        #
        clean_run_id(entry.run_id),
        str(int(entry.started_at or 0)),
    ]

    return "WCIMPORT:TG:" + ":".join(fields)


def payload(entries) -> dict:
    """
    Die Nutzlast der Inbox-Nachricht `target_gear`.

    Zugestellt wird **immer die ganze Liste**, aus demselben Grund wie
    bei den Sim-Gewichten und der WeakAura-Bibliothek: das Addon
    ersetzt seine Ablage damit, und ein gelöschter Zielzustand
    verschwindet allein dadurch, dass er in der nächsten Zustellung
    fehlt.

    `gems` ist eine Liste mit Nullen darin und **nicht** verdichtet -
    die Position benennt den Sockel.
    """

    return {
        "version": 1,
        "sets": [
            {
                "id": entry.id,
                "spec": entry.spec_key,
                "character": entry.character,
                "realm": entry.realm,
                "source": entry.source or "wowsims",
                "created": int(entry.created or 0),
                "run": clean_run_id(entry.run_id),
                "startedAt": int(entry.started_at or 0),
                "items": [
                    {
                        "slot": item.slot,
                        "itemId": item.item_id,
                        "gems": [int(gem or 0) for gem in item.gems],
                        "reforge": item.reforging,
                        "enchant": item.enchant,
                    }
                    for item in entry.items
                    if not item.empty
                ],
            }
            for entry in entries
        ],
    }
