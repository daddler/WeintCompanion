"""
Was das Exporter-Addon meldet - gelesen, geprüft, zugeordnet.

Der [WowSimsExporter] ist das Addon, das wowsims selbst als Weg ins
Spiel nennt: es schreibt die eigene Ausrüstung als JSON in seine
SavedVariables, und im Sim fügt man den Text unter *Import → Addon*
ein. Genau dieses Einfügen nimmt die Companion ab - sie liest die
Datei, in der der Text ohnehin schon steht, und baut daraus die
Adresse (siehe `core/wowsims_link.py`).

Diese Datei ist die **reine** Hälfte davon: sie bekommt den Text und
gibt zurück, was drinsteht. Kein Qt, kein `httpx`, keine Datei - aus
demselben Grund wie `core/stat_weights.py`. Die Datei selbst sucht
`addon/wse_reader.py`.

DREI DINGE, DIE SIE NICHT TUT.

* **Sie rät keine Spezialisierung.** Die Zuordnung Klasse + Spec →
  Profilschlüssel ist eine Tabelle und keine Ableitung. Das Addon
  schreibt `marksman`, nicht `marksmanship`, und `disc`, nicht
  `discipline` - eine Ableitung, die bei zwei von 34 danebengreift,
  führt genau dort ins Leere, und eine Ausrüstung unter der falschen
  Spec sieht aus wie die richtige. Dieselbe Lehre wie bei `sim_url()`.
* **Sie wirft nichts weg, was unvollständig ist.** Eine Meldung ohne
  Stufe, ohne Spec oder mit einer Klasse, die der Sim nicht führt,
  wird trotzdem gelesen und der Mangel **benannt**. Was fehlt, sieht
  sonst genauso aus wie "das Addon hat nie exportiert".
* **Sie urteilt nicht über die Ausrüstung.** Ob eine Verzauberung
  fehlt, steht auf *Meine Charaktere*; hier zählt nur, was der Sim
  braucht.

EIN LEERER PLATZ IST EIN PLATZ.

Das Addon schreibt seine Ausrüstungsliste über alle 17 Plätze, und
ein Platz ohne Gegenstand steht als `null` darin. Diese Nullen bleiben
erhalten (als leerer `SimItem`), denn der Sim vergibt die Plätze der
Reihe nach: fällt der leere Platz heraus, rückt die Zweitwaffe in die
Waffenhand.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from addon.wse_reader import FOUND, NO_ADDON, NO_EXPORT, NO_WOW
from core.stat_weights import spec as spec_of
from core.wowsims_link import SimItem, item_from_payload


#
# --------------------------------------------------
# Klasse + Spec des Addons → unser Profilschlüssel
# --------------------------------------------------
#
# Die Schreibweisen stammen aus `Conditional_Mists.lua` des Addons
# (`Env.AddSpec(class, spec, url, …)`); geschrieben wird jeweils der
# erste der beiden Namen. Zwei davon sind die Fallen, wegen derer
# diese Tabelle existiert: `marksman` und `disc`.
#
# Ziel sind die Profilschlüssel, mit denen WeintCodex und
# `core/stat_weights.py` ohnehin arbeiten. Die fünf
# `*_OFFENSIVE`-Profile kommen hier nicht vor: welche Haltung ein Tank
# gerade spielt, kann das Addon nicht melden, und der Sim kennt den
# Unterschied auch nicht.
#

SPEC_KEYS: dict[tuple[str, str], str] = {

    ("deathknight", "blood"): "DEATHKNIGHT_BLOOD",
    ("deathknight", "frost"): "DEATHKNIGHT_FROST",
    ("deathknight", "unholy"): "DEATHKNIGHT_UNHOLY",

    ("druid", "balance"): "DRUID_BALANCE",
    ("druid", "feral"): "DRUID_FERAL",
    ("druid", "guardian"): "DRUID_GUARDIAN",
    ("druid", "restoration"): "DRUID_RESTORATION",

    ("hunter", "beast_mastery"): "HUNTER_BEASTMASTERY",
    ("hunter", "marksman"): "HUNTER_MARKSMANSHIP",
    ("hunter", "survival"): "HUNTER_SURVIVAL",

    ("mage", "arcane"): "MAGE_ARCANE",
    ("mage", "fire"): "MAGE_FIRE",
    ("mage", "frost"): "MAGE_FROST",

    ("monk", "brewmaster"): "MONK_BREWMASTER",
    ("monk", "mistweaver"): "MONK_MISTWEAVER",
    ("monk", "windwalker"): "MONK_WINDWALKER",

    ("paladin", "holy"): "PALADIN_HOLY",
    ("paladin", "protection"): "PALADIN_PROTECTION",
    ("paladin", "retribution"): "PALADIN_RETRIBUTION",

    ("priest", "disc"): "PRIEST_DISCIPLINE",
    ("priest", "holy"): "PRIEST_HOLY",
    ("priest", "shadow"): "PRIEST_SHADOW",

    ("rogue", "assassination"): "ROGUE_ASSASSINATION",
    ("rogue", "combat"): "ROGUE_COMBAT",
    ("rogue", "subtlety"): "ROGUE_SUBTLETY",

    ("shaman", "elemental"): "SHAMAN_ELEMENTAL",
    ("shaman", "enhancement"): "SHAMAN_ENHANCEMENT",
    ("shaman", "restoration"): "SHAMAN_RESTORATION",

    ("warlock", "affliction"): "WARLOCK_AFFLICTION",
    ("warlock", "demonology"): "WARLOCK_DEMONOLOGY",
    ("warlock", "destruction"): "WARLOCK_DESTRUCTION",

    ("warrior", "arms"): "WARRIOR_ARMS",
    ("warrior", "fury"): "WARRIOR_FURY",
    ("warrior", "protection"): "WARRIOR_PROTECTION",
}


#
# Wo es das Addon gibt. Der Satz "es fehlt" ist ohne diese Zeile eine
# Sackgasse - und der Desktop ist die eine von beiden Seiten, auf der
# sich etwas herunterladen lässt.
#

ADDON_URL = "https://www.curseforge.com/wow/addons/wowsimsexporter"


#
# Die Stufe, ab der eine Ausrüstung überhaupt eine Aussage ist -
# dieselbe Grenze, mit der `core/character_store.py` seine Twinks
# ausblendet.
#

MIN_LEVEL = 90


@dataclass(frozen=True)
class SimExport:
    """
    Eine Meldung des Exporter-Addons.

    `problems` sind Sätze für die Oberfläche, keine Fehler: der Export
    bleibt benutzbar, und was daran fehlt, steht daneben.
    """

    name: str = ""

    realm: str = ""

    char_class: str = ""

    spec: str = ""

    race: str = ""

    level: int = 0

    addon_version: str = ""

    talents: str = ""

    professions: tuple[str, ...] = ()

    items: tuple[SimItem, ...] = ()

    raw: str = ""

    problems: tuple[str, ...] = ()

    @property
    def spec_key(self) -> str:
        """
        Der Profilschlüssel, oder "" wenn die Zuordnung nicht
        eindeutig ist. Geraten wird nicht.
        """

        return SPEC_KEYS.get(
            (self.char_class, self.spec),
            "",
        )

    @property
    def full_name(self) -> str:

        return f"{self.name}-{self.realm}" if self.realm else self.name

    @property
    def item_count(self) -> int:
        """
        Wieviele Plätze tatsächlich belegt sind - leere Plätze zählen
        nicht mit, sie sind Ausrüstung, die es nicht gibt.
        """

        return sum(1 for item in self.items if not item.empty)

    @property
    def usable(self) -> bool:
        """
        Ob sich daraus eine Adresse bauen lässt.

        Ohne einen einzigen Gegenstand ist die Antwort nein - eine
        Adresse, die eine leere Ausrüstung anliefert, würde im Sim die
        vorhandene löschen, und das wäre die Sorte Knopf, die man
        einmal drückt.
        """

        return bool(self.item_count)


def _text(value) -> str:

    return value.strip() if isinstance(value, str) else ""


def _professions(value) -> tuple[str, ...]:

    if not isinstance(value, list):
        return ()

    names = []

    for entry in value:

        if isinstance(entry, dict):

            name = _text(entry.get("name"))

            if name:
                names.append(name)

    return tuple(names)


def parse_export(text: str) -> SimExport | None:
    """
    Ein Export des Addons, oder `None`, wenn der Text keiner ist.

    `None` heisst "das war nichts, was dieses Addon geschrieben hat" -
    ein Unterschied, den der Aufrufer braucht, weil er zu einer ganz
    anderen Auskunft führt als "der Export ist unvollständig".
    """

    text = (text or "").strip()

    if not text:
        return None

    try:
        payload = json.loads(text)

    except (ValueError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    gear = payload.get("gear")

    if not isinstance(gear, dict) or not isinstance(gear.get("items"), list):

        #
        # Ohne Ausrüstungsliste ist es kein Export dieses Addons,
        # sondern irgendein JSON.
        #

        return None

    char_class = _text(payload.get("class")).lower()

    spec = _text(payload.get("spec")).lower()

    level = payload.get("level")

    level = int(level) if isinstance(level, (int, float)) else 0

    items = tuple(item_from_payload(entry) for entry in gear["items"])

    problems: list[str] = []

    if not char_class:
        problems.append("Die Meldung nennt keine Klasse.")

    if not spec:

        problems.append(
            "Die Meldung nennt keine Spezialisierung — im Spiel war "
            "vermutlich keine gewählt."
        )

    elif char_class and (char_class, spec) not in SPEC_KEYS:

        problems.append(
            f"Die Spezialisierung „{spec}“ ist hier nicht hinterlegt."
        )

    if level and level < MIN_LEVEL:

        problems.append(
            f"Der Charakter ist Stufe {level}. Gesimmt wird auf "
            f"Stufe {MIN_LEVEL}."
        )

    if not any(not item.empty for item in items):

        problems.append(
            "In der Meldung steckt kein einziges Ausrüstungsteil."
        )

    return SimExport(
        name=_text(payload.get("name")),
        realm=_text(payload.get("realm")),
        char_class=char_class,
        spec=spec,
        race=_text(payload.get("race")),
        level=level,
        addon_version=_text(payload.get("version")),
        talents=_text(payload.get("talents")),
        professions=_professions(payload.get("professions")),
        items=items,
        raw=text,
        problems=tuple(problems),
    )


#
# --------------------------------------------------
# Die drei Fragen, die die Seite stellt
# --------------------------------------------------
#
# Sie stehen hier und nicht in `gui/pages/sim.py`, aus demselben Grund
# wie `gui/widgets/tv/analysis_gap.py`: welcher Satz dasteht, ist
# genau die Stelle, an der etwas falsch sein kann, und ein Fenster
# braucht man dafür nicht. `tests/test_wowsims_export.py` prüft sie
# ohne Qt.
#


def fits_spec(export: SimExport | None, spec_key: str) -> bool:
    """
    Ob diese Ausrüstung zu dieser Spezialisierung geschickt werden
    darf.

    Massstab ist die **Klasse**, nicht die Spezialisierung. Die
    Zweitspec mit der laufenden Ausrüstung zu simmen ist der Normalfall
    und soll gehen - der Sim führt je Spec eine Seite, aber die
    Rüstung ist dieselbe. Die Rüstung eines anderen Charakters dagegen
    wäre keine Auskunft: der Sim prüft die Klasse bei seinem eigenen
    Import ausdrücklich, und Platten auf einem Magier sind auch dann
    Unsinn, wenn niemand widerspricht.
    """

    if export is None or not export.usable:
        return False

    entry = spec_of(spec_key)

    if entry is None:
        return False

    return entry.class_token == export.char_class.upper()


def age_text(stamp: int, now: int | None = None) -> str:
    """
    Wann das Spiel zuletzt geschrieben hat, in der Grobheit, in der es
    zählt.

    Das **Alter** ist hier die eigentliche Auskunft und nicht die
    Uhrzeit: WoW schreibt seine SavedVariables nur beim Neuladen und
    beim Ausloggen, eine Meldung von gestern beschreibt also die
    Ausrüstung von gestern. Wer eine blosse Uhrzeit liest, rechnet das
    nicht nach.
    """

    if not stamp:
        return "ohne Datum"

    age = int(now if now is not None else time.time()) - int(stamp)

    if age < 0:

        #
        # Uhr des Rechners verstellt oder Zeitzone verrutscht. "Vor
        # -3 Minuten" wäre die schlechtere Auskunft als das blosse
        # Datum.
        #

        return time.strftime("%d.%m.%Y %H:%M", time.localtime(stamp))

    if age < 120:
        return "gerade eben"

    if age < 3600:
        return f"vor {age // 60} Minuten"

    if age < 86400:

        hours = age // 3600

        return "vor einer Stunde" if hours == 1 else f"vor {hours} Stunden"

    days = age // 86400

    if days == 1:
        return "gestern"

    if days < 30:
        return f"vor {days} Tagen"

    return time.strftime("%d.%m.%Y", time.localtime(stamp))


def gap_text(reason: str, export: SimExport | None) -> str:
    """
    Warum keine Ausrüstung dasteht - in dem Satz, der zum Grund passt.

    Vier Gründe, vier Antworten, und drei davon verlangen etwas
    völlig anderes: WoW nicht gefunden, Addon nicht installiert,
    installiert aber nie exportiert, exportiert aber ohne Ausrüstung.
    Ein gemeinsamer Satz wäre für drei von ihnen falsch - dieselbe
    Linie wie bei `block_gap_text()`.
    """

    if reason == NO_WOW:
        return "World of Warcraft wurde noch nicht gefunden."

    if reason == NO_ADDON:

        return (
            "Der WowSimsExporter ist nicht installiert. Er ist das "
            "Addon, das wowsims selbst dafür nennt: "
            f"{ADDON_URL}"
        )

    if reason == NO_EXPORT:

        return (
            "Der WowSimsExporter hat noch nichts gemeldet. Im Spiel "
            "unter Charakter \u2192 Simmen bereitstellen, oder /reload."
        )

    if reason == FOUND and export is not None and not export.usable:

        return (
            "Die Meldung enthält keine Ausrüstung: "
            + " ".join(export.problems)
        ).strip()

    return (
        "Die Meldung des WowSimsExporter war nicht lesbar. Im Spiel "
        "/wse export und danach /reload."
    )
