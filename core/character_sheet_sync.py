"""
Der Ausrüstungsstand eines Charakters - die Meldung des Addons.

Bis 2.0.0 wusste die App über Ausrüstung **nichts**. Die einzige
Charakter-Meldung war die Twinkliste (`"character"`, Name | Klasse |
Realm), die an den Bot weitergereicht und hier nicht einmal
gespeichert wird. Gegenstandsstufe, Verzauberungen, Sockel und offene
BiS-Plätze kamen in `core/`, `addon/` und `analyzer/` an keiner Stelle
vor - deshalb standen "Meine Charaktere" und "Vorbereitung" leer, und
das war richtig so: ein Ring bei 0 % hätte eine Messung behauptet, die
es nicht gab.

Seit WeintCodex 1.3.3.1 gibt es `"character_sheet"`. Die Nachricht
wird lokal verarbeitet und **nie an den Bot geschickt** - genau wie
`"academy"`, `"dummy_practice_session"` und `"character_report"`. Es
ist die eigene Ausrüstung, kein Gildenwissen. Dieses Modul importiert
deshalb kein `httpx`: es bleibt ohne Netzwerkschicht testbar.

Format (die Ausgangsrichtung kann `addon/sync_reader.py` nur als
Zeichenkette lesen, deshalb flach und positionsbasiert - verschachtelte
Tabellen gibt es nur in der Gegenrichtung):

    <KOPF> ~ <ZÄHLER> ~ <BIS> ~ <SLOTS> ~ <MÄNGEL>

Abschnitte mit ``~``, Datensätze mit ``;``, Felder mit ``|``. Der
volle Aufbau steht im Kopfkommentar von `modules/companion.lua` und
muss dort und hier in Schritt bleiben.

**Alles ist optional.** Ein fehlender Abschnitt, ein fehlendes Feld
oder ein zusätzliches Feld darf die Meldung nicht verwerfen; nur ohne
Namen ist sie wertlos. Das Addon darf das Format also erweitern, ohne
eine ältere Companion zu brechen - dieselbe Regel wie bei
`character_report`.

**Eine fehlende Angabe ist `None`, keine Null.** Das ist die Trennung,
an der die ganze Anzeige hängt: `bis is None` heißt "für diese Spec
ist keine Liste gepflegt", `bis["open"] == 0` heißt "nichts offen".
Wer beides zu einer Null zusammenzieht, behauptet eine geprüfte
Vollständigkeit - derselbe Fehler, den `stars == 0` im Analyzer
verhindert.
"""

from __future__ import annotations


SECTION = "~"

RECORD = ";"

FIELD = "|"


#
# Die Statuswerte des Addons (modules/charakter.lua, Tabelle STATUS).
# "-" heißt "dieser Platz kennt so etwas nicht" - ein Hals hat keine
# Verzauberung, das ist kein Mangel.
#

STATUS_MISSING = "missing"

STATUS_NONE = "-"

KNOWN_STATUS = {
    "optimal",
    "ok",
    "wrong",
    "overcap",
    STATUS_MISSING,
    STATUS_NONE,
}


def _sections(payload: str) -> list[str]:

    if not isinstance(payload, str):
        return []

    return payload.split(SECTION)


def _section(sections: list[str], index: int) -> str:

    if index >= len(sections):
        return ""

    return sections[index]


def _records(section: str) -> list[list[str]]:
    """
    Ein Abschnitt in Datensätze und Felder. Leere Abschnitte ergeben
    eine leere Liste - `"".split(";")` wäre `[""]` und damit ein
    Geisterdatensatz.
    """

    section = section.strip()

    if not section:
        return []

    return [
        [field.strip() for field in record.split(FIELD)]
        for record in section.split(RECORD)
        if record.strip()
    ]


def _at(fields: list[str], index: int) -> str:

    if index >= len(fields):
        return ""

    return fields[index]


def _int(value: str, default: int = 0) -> int:

    try:
        return int(float(value))

    except (TypeError, ValueError):
        return default


def _float(value: str, default: float = 0.0) -> float:

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _status(value: str) -> str:
    """
    Ein unbekannter Status wird durchgereicht, nicht ersetzt. Eine
    künftige Addon-Version darf einen vierten Wert einführen; die
    Oberfläche behandelt alles Unbekannte wie "keine Angabe", statt
    ihn zu einem Mangel umzudeuten.
    """

    value = (value or "").strip()

    return value or STATUS_NONE


def _counts(fields: list[str]) -> dict:

    return {
        "optimal": _int(_at(fields, 1)),
        "ok": _int(_at(fields, 2)),
        "wrong": _int(_at(fields, 3)),
        "overcap": _int(_at(fields, 4)),
        "missing": _int(_at(fields, 5)),
        "total": _int(_at(fields, 6)),
    }


def parse_character_sheet(payload: str) -> dict | None:
    """
    Zerlegt die Nutzlast. `None` heißt "unbrauchbar" - ohne Namen
    lässt sich die Meldung keinem Charakter zuordnen, und einen zu
    raten wäre genau der Fehler, den 1.7.0 abgestellt hat.
    """

    sections = _sections(payload)

    head = _records(_section(sections, 0))

    if not head:
        return None

    fields = head[0]

    name = _at(fields, 0)

    if not name:
        return None

    sheet = {
        "name": name,
        "realm": _at(fields, 1),
        "class": _at(fields, 2),
        "level": _int(_at(fields, 3)),
        "spec_key": _at(fields, 4),
        "spec": _at(fields, 5),
        "item_level_equipped": _float(_at(fields, 6)),
        "item_level_overall": _float(_at(fields, 7)),
        "score": _int(_at(fields, 8)),
        "grade": _at(fields, 9),
        "completeness": _int(_at(fields, 10)),
        "quality": _int(_at(fields, 11)),
        "updated": _int(_at(fields, 12)),
        "enchants": None,
        "gems": None,
        "bis": None,
        "slots": [],
        "issues": [],
    }

    #
    # Zähler
    #

    for record in _records(_section(sections, 1)):

        kind = _at(record, 0)

        if kind == "ench":
            sheet["enchants"] = _counts(record)

        elif kind == "gem":
            sheet["gems"] = _counts(record)

    #
    # BiS. Der ganze Abschnitt fehlt, wenn für die Spezialisierung
    # keine Liste gepflegt ist - dann bleibt `bis` None und die
    # Oberfläche sagt das, statt "0 offen" zu zeigen.
    #

    bis_records = _records(_section(sections, 2))

    if bis_records:

        counts = bis_records[0]

        sheet["bis"] = {
            "have": _int(_at(counts, 0)),
            "variant": _int(_at(counts, 1)),
            "open": _int(_at(counts, 2)),
            "total": _int(_at(counts, 3)),
            "open_slots": [
                slot
                for slot in (bis_records[1] if len(bis_records) > 1 else [])
                if slot
            ],
        }

    #
    # Slots
    #

    for record in _records(_section(sections, 3)):

        slot_name = _at(record, 1)

        if not slot_name:
            continue

        sheet["slots"].append({
            "slot_id": _int(_at(record, 0)),
            "slot": slot_name,
            "item": _at(record, 2),
            "item_level": _int(_at(record, 3)),
            "enchant": _status(_at(record, 4)),
            "gem": _status(_at(record, 5)),
        })

    #
    # Mängel
    #

    for record in _records(_section(sections, 4)):

        text = FIELD.join(record[2:]).strip()

        if not text:
            continue

        sheet["issues"].append({
            "priority": _int(_at(record, 0), 9),
            "status": _status(_at(record, 1)),
            "text": text,
        })

    return sheet


def sheet_key(name: str, realm: str) -> str:
    """
    Der Ablageschlüssel eines Charakters.

    Bewusst `Name-Realm` und nicht nur der Name: zwei Realms dürfen
    denselben Namen führen, und die Ausrüstung des einen darf die des
    anderen nicht überschreiben. Ohne Realm bleibt der blanke Name -
    ein fehlender Realm ist im ganzen Projekt ein Platzhalter und kein
    Widerspruch (siehe `analyzer/names.py`).
    """

    name = (name or "").strip()

    realm = (realm or "").strip()

    if not name:
        return ""

    if not realm:
        return name

    return f"{name}-{realm}"


def readiness(sheet: dict) -> float | None:
    """
    Wie weit ein Charakter vorbereitet ist, als Anteil von 0 bis 1.

    Gezählt wird, was das Addon tatsächlich geprüft hat: jede
    Verzauberung und jeder Sockel, die es gibt. `None` heißt "nichts
    geprüft" und ist **nicht** dasselbe wie 0.0 - genau diese
    Unterscheidung trennt einen leeren Ring von einem roten.

    Offene BiS-Plätze zählen hier bewusst **nicht** mit: sie hängen an
    Würfelglück, nicht an Vorbereitung, und würden einen frisch
    ausgestatteten Charakter dauerhaft rot färben für etwas, das er
    nicht abstellen kann.
    """

    total = 0

    filled = 0

    for counts in (sheet.get("enchants"), sheet.get("gems")):

        if not counts:
            continue

        total += counts.get("total", 0)

        filled += counts.get("total", 0) - counts.get("missing", 0)

    if total <= 0:
        return None

    return max(0.0, min(1.0, filled / total))


def open_slots(sheet: dict) -> list[str]:
    """
    Die Plätze mit einer fehlenden Verzauberung oder einem leeren
    Sockel, in der Reihenfolge des Charakterfensters.

    Nur `missing` - ein nicht ideal gewählter Stein ist ein
    Verbesserungsvorschlag, kein Loch. Beides in eine Liste zu werfen
    hieße, die dringende Frage ("wo fehlt etwas") mit der
    optionalen zu verwischen.
    """

    names = []

    for slot in sheet.get("slots") or []:

        if STATUS_MISSING in (slot.get("enchant"), slot.get("gem")):
            names.append(slot.get("slot", ""))

    return [name for name in names if name]
