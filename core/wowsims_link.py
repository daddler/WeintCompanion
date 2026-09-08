"""
Der Weg IN den Sim: eine Ausrüstung als wowsims-Adresse.

Bis 2.5.1 nahm die Companion das *Ergebnis* eines Sims entgegen und
brachte es ins Spiel. Der Weg davor blieb von Hand: Ausrüstung im Sim
Stück für Stück nachstellen oder den Export eines weiteren Addons
irgendwo einfügen. Wer das einmal gemacht hat, simmt nicht jede Woche
erneut - und eine Gewichtung, die zur Ausrüstung von vor vier Wochen
gehört, ist schlechter als ihr Ruf.

Diese Datei baut die Adresse, die den Sim mit der **Ausrüstung von
gerade eben** öffnet. wowsims trägt seine Einstellungen selbst so
herum: der Teil hinter dem `#` ist ein Protobuf, mit Deflate gepackt
und Base64 geschrieben, und `?i=` sagt, WELCHE Bereiche daraus gelten
sollen. Genau dafür ist es gebaut - der Sim nennt es "partial link
import" und mischt die Lieferung in das, was der Nutzer dort schon
eingestellt hat.

DIESE DATEI IST AN EIN FREMDES FORMAT GEBUNDEN, UND ZWAR ALS EINZIGE.

Dieselbe Lage wie bei `parse_sim()` in `core/stat_weights.py`, und
dieselbe Konsequenz: **sie muss laut scheitern.** Ein Protobuf trägt
keine Feldnamen, sondern Feld*nummern*; verschiebt der Sim eine, käme
die Ausrüstung lautlos falsch an - ein Ring als Schmuckstück, eine
Verzauberung als Stein. Deshalb:

* Jede Feldnummer steht hier als benannte Konstante mit der Zeile aus
  `proto/common.proto` bzw. `proto/api.proto` daneben, aus der sie
  stammt. Abgeschrieben wird nicht, belegt wird.
* `tests/test_wowsims_link.py` baut die Nachricht aus einer **echten**
  Sim-Ausgabe (`tests/data/wowsims_mop_output.json`) und liest sie mit
  einem eigenen Decoder zurück. Kommt nicht Feld für Feld dasselbe
  heraus, fällt der Test um.
* `API_VERSION` ist die Fassung, in deren Form wir schreiben. Sie zu
  hoch anzugeben wäre der stille Fehler: der Sim überspränge dann
  seine eigenen Umbauten und läse alte Zahlen als neue.

WAS MITGESCHICKT WIRD, UND WAS NICHT.

Nur die **Ausrüstung** (`?i=g`). Das ist keine Sparsamkeit, sondern
dieselbe Linie wie `stars == 0`: der Sim räumt beim Einlesen jeden
Bereich vollständig ab, den die Adresse benennt. Talente und Glyphen
liegen dort in EINEM Bereich, und Glyphen führt der Sim als
Gegenstands-Nummern, während das Exporter-Addon Zauber-Nummern
meldet. Diese Übersetzung kennt nur der Sim selbst. Den Bereich
mitzuschicken hiesse also: Talente kommen an, Glyphen sind
**weg** - lautlos, denn eine leere Glyphenleiste sieht aus wie eine
Einstellung. Ein Bereich, den wir nicht vollständig füllen können,
wird nicht geschickt.

Die Ausrüstung ist ohnehin der Teil, der sich jede Woche ändert;
Talente und Glyphen stellt man einmal ein, und der Sim merkt sie sich
je Spezialisierung im Browser. Wer das ganze Bild will, hat den
zweiten Weg: den Export-Text in die Zwischenablage und im Sim unter
*Import → Addon* einfügen. Dort löst der Sim die Glyphen selbst auf.
Die Seite nennt beide Wege und sagt, was jeder bringt.

Rein: kein Qt, kein `httpx`, keine Datei - aus demselben Grund wie
`core/stat_weights.py` und `core/access_roles.build_profile_payload()`.
"""

from __future__ import annotations

import base64
import zlib
from dataclasses import dataclass


#
# --------------------------------------------------
# Die Feldnummern, belegt statt abgeschrieben
# --------------------------------------------------
#
# Quelle: https://github.com/wowsims/mop, Zweig master.
#
#   proto/common.proto
#       message ItemSpec {
#           int32 id = 2;
#           int32 random_suffix = 6;
#           int32 enchant = 3;
#           repeated int32 gems = 4;
#           int32 reforging = 5;
#           ItemLevelState upgrade_step = 7;
#           bool challenge_mode = 8;
#           int32 tinker = 9;
#       }
#       message EquipmentSpec { repeated ItemSpec items = 1; }
#
#   proto/api.proto
#       message Player {
#           int32 api_version = 54;
#           EquipmentSpec equipment = 3;
#       }
#
#   proto/ui.proto
#       message IndividualSimSettings {
#           int32 api_version = 15;
#           Player player = 3;
#       }
#

ITEM_ID = 2
ITEM_ENCHANT = 3
ITEM_GEMS = 4
ITEM_REFORGING = 5
ITEM_RANDOM_SUFFIX = 6
ITEM_UPGRADE_STEP = 7
ITEM_TINKER = 9

EQUIPMENT_ITEMS = 1

PLAYER_EQUIPMENT = 3
PLAYER_API_VERSION = 54

SETTINGS_PLAYER = 3
SETTINGS_API_VERSION = 15


#
# proto/common.proto, message ProtoVersion:
#
#     option (current_version_number) = 3;
#
# Der Sim führt jede gespeicherte Nachricht auf diesen Stand hoch,
# wenn sie eine ältere Fassung nennt. Wir schreiben in der Form von 3,
# also sagen wir 3 - dann läuft kein Umbau, und wenn der Sim eines
# Tages auf 4 geht, läuft seiner. Eine zu hohe Zahl überspränge ihn.
#

API_VERSION = 3


#
# Der Buchstabe für "nur die Ausrüstung", aus
# ui/core/constants/sim_settings.ts:
#
#     map.set(SimSettingCategories.Gear, 'g');
#
# Ein Bereich, der in dieser Liste NICHT vorkommt, bleibt im Sim
# unangetastet - das ist die ganze Vorsicht dieser Datei in einem
# Zeichen.
#

CATEGORY_GEAR = "g"


#
# Werte des Enums `ItemLevelState` (proto/common.proto). Das
# Exporter-Addon meldet die Aufwertungsstufe als blosse Zahl, eine
# Sim-Ausgabe schreibt sie als Namen - beide Schreibweisen kommen
# hier an, also versteht diese Tabelle beide.
#

UPGRADE_STEPS: dict[str, int] = {
    "Base": 0,
    "ChallengeMode": -1,
    "UpgradeStepOne": 1,
    "UpgradeStepTwo": 2,
    "UpgradeStepThree": 3,
    "UpgradeStepFour": 4,
}


MAX_UPGRADE_STEP = 4


#
# --------------------------------------------------
# Protobuf, so viel davon wie gebraucht wird
# --------------------------------------------------
#
# Bewusst keine Bibliothek: gebraucht werden zwei Drahtformate
# (Varint und längenbegrenzt) und sechs Nachrichtenfelder. Eine
# Abhängigkeit dafür in eine Anwendung zu ziehen, die auf 25
# Spielerrechnern als AppImage läuft, wäre teurer als diese dreissig
# Zeilen - und der Test liest sie unabhängig wieder zurück.
#


def encode_varint(value: int) -> bytes:
    """
    Eine Zahl im Varint-Format.

    Negative Zahlen werden als Zweierkomplement über 64 Bit
    geschrieben, so wie protobuf es für `int32` verlangt. Das ist
    nicht theoretisch: `ChallengeMode` ist -1.
    """

    if value < 0:
        value += 1 << 64

    out = bytearray()

    while True:

        chunk = value & 0x7F

        value >>= 7

        if value:
            out.append(chunk | 0x80)

        else:
            out.append(chunk)
            break

    return bytes(out)


def _tag(number: int, wire: int) -> bytes:

    return encode_varint((number << 3) | wire)


def field_varint(number: int, value: int) -> bytes:
    """
    Ein Zahlenfeld - leer, wenn der Wert 0 ist.

    Protobuf schreibt Vorgabewerte nicht mit, und der Sim liest ein
    fehlendes Feld als 0. Eine 0 mitzuschicken wäre also dasselbe in
    länger.
    """

    if not value:
        return b""

    return _tag(number, 0) + encode_varint(value)


def field_bytes(number: int, payload: bytes) -> bytes:
    """
    Ein längenbegrenztes Feld - auch dann, wenn es leer ist.

    Das "auch dann" ist der Punkt. Ein leerer Eintrag in der
    Ausrüstungsliste ist ein **leerer Platz** (keine Zweitwaffe), und
    er muss stehen bleiben, sonst rückt alles dahinter eine Stelle
    vor: die Zweitwaffe landet in der Waffenhand.
    """

    return _tag(number, 2) + encode_varint(len(payload)) + payload


def field_packed(number: int, values) -> bytes:
    """
    Eine Zahlenreihe im gepackten Format (proto3-Vorgabe für
    `repeated int32`).
    """

    values = list(values)

    if not values:
        return b""

    body = b"".join(encode_varint(value) for value in values)

    return _tag(number, 2) + encode_varint(len(body)) + body


#
# --------------------------------------------------
# Ein Ausrüstungsstück
# --------------------------------------------------
#


@dataclass(frozen=True)
class SimItem:
    """
    Ein Gegenstand, so wie der Sim ihn kennt.

    `empty` ist kein fehlender Gegenstand, sondern ein **leerer
    Platz**: der Sim führt die Ausrüstung als Liste, und ein Platz,
    der übersprungen wird, verschiebt jeden dahinter.
    """

    item_id: int = 0

    enchant: int = 0

    gems: tuple[int, ...] = ()

    reforging: int = 0

    random_suffix: int = 0

    upgrade_step: int = 0

    tinker: int = 0

    @property
    def empty(self) -> bool:

        return not self.item_id

    def encode(self) -> bytes:

        gems = list(self.gems)

        #
        # Nullen am Ende sind "kein Stein" und tragen nichts; Nullen
        # DAZWISCHEN müssen bleiben, weil die Position den Sockel
        # benennt.
        #

        while gems and not gems[-1]:
            gems.pop()

        return (
            field_varint(ITEM_ID, self.item_id)
            + field_varint(ITEM_ENCHANT, self.enchant)
            + field_packed(ITEM_GEMS, gems)
            + field_varint(ITEM_REFORGING, self.reforging)
            + field_varint(ITEM_RANDOM_SUFFIX, self.random_suffix)
            + field_varint(ITEM_UPGRADE_STEP, self.upgrade_step)
            + field_varint(ITEM_TINKER, self.tinker)
        )


def upgrade_step(value) -> int:
    """
    Die Aufwertungsstufe als Zahl - aus einer Zahl oder aus dem Namen,
    unter dem der Sim sie schreibt.

    Was weder das eine noch das andere ist, wird zu 0 ("nicht
    aufgewertet") und nicht geraten: eine erfundene Stufe rechnet dem
    Gegenstand gut 16 % Wertung zu, die er nicht hat.
    """

    if isinstance(value, bool):
        return 0

    if isinstance(value, (int, float)):

        number = int(value)

        if -1 <= number <= MAX_UPGRADE_STEP:
            return number

        return 0

    if isinstance(value, str):
        return UPGRADE_STEPS.get(value.strip(), 0)

    return 0


def item_from_payload(entry) -> SimItem:
    """
    Ein Eintrag aus der Ausrüstungsliste eines Exports.

    Gelesen wird nachsichtig, wie überall an einer fremden Grenze
    (siehe `analyzer/providers/warcraftlogs_payload.py`): `null`, ein
    leeres Objekt und ein Objekt ohne Gegenstandsnummer sind alle
    dasselbe - ein leerer Platz. Die beiden Schreibweisen der
    Feldnamen (`upgrade_step` aus dem Addon, `upgradeStep` aus einer
    Sim-Ausgabe) werden beide verstanden.
    """

    if not isinstance(entry, dict):
        return SimItem()

    def number(*names) -> int:

        for name in names:

            value = entry.get(name)

            if isinstance(value, bool):
                continue

            if isinstance(value, (int, float)):
                return int(value)

        return 0

    raw_gems = entry.get("gems")

    gems: list[int] = []

    if isinstance(raw_gems, list):

        for gem in raw_gems:

            if isinstance(gem, bool) or not isinstance(gem, (int, float)):
                gems.append(0)

            else:
                gems.append(int(gem))

    return SimItem(
        item_id=number("id"),
        enchant=number("enchant"),
        gems=tuple(gems),
        reforging=number("reforging"),
        random_suffix=number("random_suffix", "randomSuffix"),
        upgrade_step=upgrade_step(
            entry.get("upgrade_step", entry.get("upgradeStep")),
        ),
        tinker=number("tinker"),
    )


#
# --------------------------------------------------
# Die Nachricht
# --------------------------------------------------
#


def encode_equipment(items) -> bytes:
    """
    Die Ausrüstungsliste als `EquipmentSpec`.
    """

    return b"".join(
        field_bytes(EQUIPMENT_ITEMS, item.encode())
        for item in items
    )


def encode_settings(items) -> bytes:
    """
    Die vollständige `IndividualSimSettings` - mit nichts darin ausser
    der Ausrüstung.
    """

    player = (
        field_bytes(PLAYER_EQUIPMENT, encode_equipment(items))
        + field_varint(PLAYER_API_VERSION, API_VERSION)
    )

    return (
        field_bytes(SETTINGS_PLAYER, player)
        + field_varint(SETTINGS_API_VERSION, API_VERSION)
    )


def encode_fragment(items) -> bytes:
    """
    Der Teil hinter dem `#`, als Rohbytes.

    Gepackt mit Deflate im zlib-Rahmen: der Sim liest ihn mit
    `pako.inflate`, und das erwartet genau diesen Rahmen.
    """

    return base64.b64encode(zlib.compress(encode_settings(items), 9))


#
# --------------------------------------------------
# Und derselbe Weg zurueck
# --------------------------------------------------
#
# Der Sim gibt seine Einstellungen in genau der Form heraus, in der
# diese Datei sie schreibt: als Adresse mit einem gepackten Protobuf
# hinter dem `#`, oder als JSON. Beides ist nach einem Optimierungslauf
# die **Zielausruestung** - welche Steine und welche Umschmiedung der
# Sim fuer jeden Platz vorsieht.
#
# Bis hierher konnte die Companion nur hinein und nicht heraus, und
# deshalb musste WeintCodex jede Steinentscheidung selbst noch einmal
# treffen, obwohl sie im Sim laengst gefallen war. Der Rueckweg steht
# hier und nicht in einer eigenen Datei, weil er dieselben
# Feldnummern liest, die oben geschrieben werden: zwei Dateien mit
# denselben Konstanten sind genau die Doppelpflege, an der diese
# Grenze scheitern wuerde.
#
# GELESEN WIRD STRENG. Ein Protobuf traegt keine Feldnamen; ein
# unbekanntes Feld wird uebersprungen (so verlangt es das Format), ein
# BESCHAEDIGTER Rahmen dagegen fuehrt zu None statt zu einer halben
# Ausruestung. Eine Ausruestung, der drei Plaetze fehlen, sieht aus
# wie eine, die drei Plaetze frei hat.
#


class DecodeError(ValueError):
    """Der Rahmen war keiner - siehe `read_varint`/`iter_fields`."""


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """
    Eine Varint-Zahl ab `pos`; gibt Wert und die neue Stelle zurueck.

    Zehn Gruppen sind das Maximum fuer 64 Bit - was darueber
    hinauslaeuft, ist kein Varint, sondern Zufall.
    """

    value = 0
    shift = 0

    while True:

        if pos >= len(data):
            raise DecodeError("Varint reicht ueber das Ende hinaus.")

        chunk = data[pos]

        pos += 1

        value |= (chunk & 0x7F) << shift

        if not chunk & 0x80:
            break

        shift += 7

        if shift > 63:
            raise DecodeError("Varint ist zu lang.")

    return value, pos


def iter_fields(data: bytes):
    """
    Die Felder einer Nachricht als `(Nummer, Drahtformat, Wert)`.

    `Wert` ist eine Zahl (Varint) oder ein `bytes` (laengenbegrenzt).
    Die beiden festen Breiten (32/64 Bit) kommen in den Nachrichten
    dieser Datei nicht vor, werden aber uebersprungen statt den Lauf
    abzubrechen - sie koennten in einem Feld stehen, das uns nicht
    interessiert.
    """

    pos = 0

    while pos < len(data):

        tag, pos = read_varint(data, pos)

        number, wire = tag >> 3, tag & 0x07

        if number == 0:
            raise DecodeError("Feldnummer 0 gibt es nicht.")

        if wire == 0:
            value, pos = read_varint(data, pos)
            yield number, wire, value

        elif wire == 2:

            length, pos = read_varint(data, pos)

            if pos + length > len(data):
                raise DecodeError("Feldlaenge reicht ueber das Ende hinaus.")

            yield number, wire, data[pos:pos + length]

            pos += length

        elif wire == 5:
            pos += 4

        elif wire == 1:
            pos += 8

        else:
            raise DecodeError(f"Unbekanntes Drahtformat {wire}.")

        if pos > len(data):
            raise DecodeError("Nachricht endet mitten in einem Feld.")


def _signed32(value: int) -> int:
    """
    Protobuf schreibt ein negatives `int32` als Zweierkomplement ueber
    64 Bit (siehe `encode_varint`). Zurueck also genauso.
    """

    if value >= 1 << 63:
        value -= 1 << 64

    return value


def decode_item(blob: bytes) -> SimItem:
    """
    Ein `ItemSpec`. Ein leerer Rumpf ist ein **leerer Platz** und kein
    Fehler - genau dafuer schreibt `field_bytes` ihn auch mit.
    """

    item_id = enchant = reforging = random_suffix = 0
    step = tinker = 0

    gems: list[int] = []

    for number, wire, value in iter_fields(blob):

        if number == ITEM_ID and wire == 0:
            item_id = value

        elif number == ITEM_ENCHANT and wire == 0:
            enchant = value

        elif number == ITEM_GEMS:

            if wire == 2:

                pos = 0

                while pos < len(value):
                    gem, pos = read_varint(value, pos)
                    gems.append(gem)

            elif wire == 0:

                #
                # Die ungepackte Schreibweise. proto3 packt von sich
                # aus, aber ein Erzeuger darf beides - und ein Stein,
                # der dabei verlorenginge, verschoebe alle dahinter.
                #

                gems.append(value)

        elif number == ITEM_REFORGING and wire == 0:
            reforging = value

        elif number == ITEM_RANDOM_SUFFIX and wire == 0:
            random_suffix = value

        elif number == ITEM_UPGRADE_STEP and wire == 0:
            step = _signed32(value)

        elif number == ITEM_TINKER and wire == 0:
            tinker = value

    return SimItem(
        item_id=item_id,
        enchant=enchant,
        gems=tuple(gems),
        reforging=reforging,
        random_suffix=random_suffix,
        upgrade_step=step if -1 <= step <= MAX_UPGRADE_STEP else 0,
        tinker=tinker,
    )


def decode_equipment(blob: bytes) -> tuple[SimItem, ...]:
    """
    Die Ausruestungsliste eines `EquipmentSpec` - **in ihrer
    Reihenfolge**, leere Plaetze eingeschlossen. Die Position ist der
    Platz; sie zu verdichten hiesse, die Zweitwaffe in die Waffenhand
    zu schieben.
    """

    return tuple(
        decode_item(value)
        for number, wire, value in iter_fields(blob)
        if number == EQUIPMENT_ITEMS and wire == 2
    )


def decode_settings(blob: bytes) -> tuple[SimItem, ...]:
    """
    Die Ausruestung aus einer `IndividualSimSettings`.

    Fehlt der Spielerblock oder die Ausruestung darin, kommt eine leere
    Liste zurueck - das ist etwas anderes als ein kaputter Rahmen, der
    `DecodeError` wirft.
    """

    for number, wire, value in iter_fields(blob):

        if number != SETTINGS_PLAYER or wire != 2:
            continue

        for inner, inner_wire, inner_value in iter_fields(value):

            if inner == PLAYER_EQUIPMENT and inner_wire == 2:
                return decode_equipment(inner_value)

    return ()


def decode_fragment(fragment: str) -> tuple[SimItem, ...]:
    """
    Der Teil hinter dem `#` einer Sim-Adresse.

    Base64, darin Deflate im zlib-Rahmen, darin die Nachricht - genau
    umgekehrt zu `encode_fragment()`. Der Sim schreibt das Base64 ohne
    Fuellzeichen, deshalb werden sie hier ergaenzt.
    """

    text = "".join((fragment or "").split())

    if not text:
        return ()

    text = text.replace("-", "+").replace("_", "/")

    text += "=" * (-len(text) % 4)

    try:
        packed = base64.b64decode(text, validate=False)

    except Exception as exc:
        raise DecodeError(f"Kein Base64: {exc}") from exc

    try:
        raw = zlib.decompress(packed)

    except zlib.error:

        #
        # Rohes Deflate ohne zlib-Rahmen. `pako.deflateRaw` kommt im
        # Sim ebenfalls vor; ein Rahmen, den wir nicht kennen, ist
        # kein Grund, eine lesbare Nachricht wegzuwerfen.
        #

        try:
            raw = zlib.decompressobj(-zlib.MAX_WBITS).decompress(packed)

        except zlib.error as exc:
            raise DecodeError(f"Nicht entpackbar: {exc}") from exc

    return decode_settings(raw)


def fragment_of(url: str) -> str:
    """
    Der Teil hinter dem `#` einer Adresse - oder "", wenn keiner da
    ist. Ein blosser Rumpf (jemand hat nur den Teil hinter dem `#`
    kopiert) gilt als er selbst.
    """

    text = (url or "").strip()

    if "#" in text:
        return text.split("#", 1)[1].strip()

    return "" if text.startswith(("http://", "https://")) else text


def build_link(url: str, items) -> str:
    """
    Die vollständige Adresse: Seite der Spezialisierung, `?i=g` für
    "nur die Ausrüstung", dahinter die Ausrüstung selbst.

    `url` kommt aus `stat_weights.sim_url()` und ist damit dieselbe
    Adresse, die der Knopf "Nur die Seite öffnen" benutzt - zwei
    Tabellen für dieselbe Zuordnung liefen irgendwann auseinander.
    """

    base = (url or "").split("#", 1)[0]

    separator = "&" if "?" in base else "?"

    fragment = encode_fragment(items).decode("ascii")

    return f"{base}{separator}i={CATEGORY_GEAR}#{fragment}"
