"""
Die Adresse, die den Sim mit der eigenen Ausrüstung öffnet.

Hier steckt die einzige Stelle der Companion, die ein **fremdes
Binärformat** schreibt, und sie hat die unangenehmste Eigenschaft
eines solchen: ein Protobuf trägt keine Feldnamen, sondern
Feldnummern. Sitzt eine daneben, kommt die Ausrüstung trotzdem an -
nur eben falsch, und niemand sieht es. Dieselbe Fehlerklasse wie die
Positionsliste der Sim-Ausgabe und die laufende Nummer des
Umschmieders.

Geprüft wird deshalb mit einem **eigenen Decoder**, der nichts von
`core/wowsims_link.py` weiss: er zerlegt die Bytes nach den Regeln von
protobuf und sagt, unter welcher Nummer was gelandet ist. Ein Encoder,
der sich selbst bestätigt, hätte nichts bewiesen.

Und die Ausrüstung kommt aus `tests/data/wowsims_mop_output.json` -
einer **echten** Ausgabe von wowsims.com/mop, nicht aus einem
nachgebauten Beispiel. Was dort steht, hat der Sim selbst geschrieben,
also ist der Vergleich damit die Probe aufs Exempel.
"""

import base64
import json
import zlib
from pathlib import Path

from core.wowsims_link import (
    API_VERSION,
    CATEGORY_GEAR,
    EQUIPMENT_ITEMS,
    ITEM_ENCHANT,
    ITEM_GEMS,
    ITEM_ID,
    ITEM_REFORGING,
    ITEM_TINKER,
    ITEM_UPGRADE_STEP,
    PLAYER_API_VERSION,
    PLAYER_EQUIPMENT,
    SETTINGS_API_VERSION,
    SETTINGS_PLAYER,
    SimItem,
    build_link,
    encode_settings,
    encode_varint,
    item_from_payload,
    upgrade_step,
)


SIM_OUTPUT = json.loads(
    (
        Path(__file__).resolve().parent / "data" / "wowsims_mop_output.json"
    ).read_text(encoding="utf-8")
)


#
# --------------------------------------------------
# Ein unabhängiger Decoder
# --------------------------------------------------
#


def read_varint(data: bytes, index: int):

    shift = 0

    value = 0

    while True:

        byte = data[index]

        index += 1

        value |= (byte & 0x7F) << shift

        if not byte & 0x80:
            break

        shift += 7

    return value, index


def decode(data: bytes) -> dict:
    """
    Eine Protobuf-Nachricht in `{Feldnummer: [Werte]}`.

    Längenbegrenzte Felder kommen als Bytes zurück; was darin steckt,
    entscheidet der Test.
    """

    out: dict[int, list] = {}

    index = 0

    while index < len(data):

        key, index = read_varint(data, index)

        number, wire = key >> 3, key & 7

        if wire == 0:
            value, index = read_varint(data, index)

        elif wire == 2:

            length, index = read_varint(data, index)

            value = data[index:index + length]

            index += length

        else:
            raise AssertionError(f"Unerwartetes Drahtformat {wire}")

        out.setdefault(number, []).append(value)

    return out


def signed(value: int) -> int:
    """
    Ein `int32` aus dem Varint - protobuf schreibt negative Zahlen als
    Zweierkomplement über 64 Bit.
    """

    return value - (1 << 64) if value >= 1 << 63 else value


def items_of(payload: bytes) -> list[dict]:
    """
    Die Ausrüstungsliste aus einer fertigen Nachricht.
    """

    settings = decode(payload)

    player = decode(settings[SETTINGS_PLAYER][0])

    equipment = decode(player[PLAYER_EQUIPMENT][0])

    return [decode(entry) for entry in equipment[EQUIPMENT_ITEMS]]


def packed(data: bytes) -> list[int]:

    out = []

    index = 0

    while index < len(data):

        value, index = read_varint(data, index)

        out.append(value)

    return out


# --------------------------------------------------
# Varint
# --------------------------------------------------


def test_varint_kleine_zahlen():

    assert encode_varint(0) == b"\x00"

    assert encode_varint(1) == b"\x01"

    assert encode_varint(127) == b"\x7f"

    assert encode_varint(128) == b"\x80\x01"

    assert encode_varint(300) == b"\xac\x02"


def test_varint_negative_zahl_ist_zehn_byte():
    """
    `ChallengeMode` ist -1, und das ist kein Sonderfall aus der
    Theorie: ein Gegenstand aus einem Herausforderungsmodus trägt
    genau diesen Wert. Protobuf schreibt ihn als Zweierkomplement über
    64 Bit, also zehn Bytes.
    """

    encoded = encode_varint(-1)

    assert len(encoded) == 10

    value, _ = read_varint(encoded, 0)

    assert signed(value) == -1


# --------------------------------------------------
# Ein Gegenstand
# --------------------------------------------------


def test_felder_landen_unter_ihren_nummern():

    item = SimItem(
        item_id=86920,
        enchant=4805,
        gems=(76895, 76639),
        reforging=161,
        upgrade_step=2,
        tinker=4898,
    )

    fields = decode(item.encode())

    assert fields[ITEM_ID][0] == 86920

    assert fields[ITEM_ENCHANT][0] == 4805

    assert packed(fields[ITEM_GEMS][0]) == [76895, 76639]

    assert fields[ITEM_REFORGING][0] == 161

    assert fields[ITEM_UPGRADE_STEP][0] == 2

    assert fields[ITEM_TINKER][0] == 4898


def test_nullen_zwischen_steinen_bleiben():
    """
    Die Position sagt, in welchem Sockel ein Stein sitzt. Eine Null am
    Ende ist "kein Stein" und trägt nichts; eine Null DAZWISCHEN
    verschöbe jeden Stein dahinter um einen Sockel.
    """

    item = SimItem(item_id=1, gems=(0, 76653, 0, 0))

    assert packed(decode(item.encode())[ITEM_GEMS][0]) == [0, 76653]


def test_leerer_platz_bleibt_als_platz_stehen():
    """
    Der Fall, an dem sich das entscheidet: ein Blut-Todesritter trägt
    eine Zweihandwaffe, sein Zweitwaffenplatz ist leer. Fällt der
    Platz heraus, rückt alles dahinter vor - und der Sim vergibt die
    Plätze der Reihe nach.
    """

    payload = encode_settings([
        SimItem(item_id=11),
        SimItem(),
        SimItem(item_id=33),
    ])

    entries = items_of(payload)

    assert len(entries) == 3

    assert entries[0][ITEM_ID][0] == 11

    assert entries[1] == {}

    assert entries[2][ITEM_ID][0] == 33


def test_aufwertungsstufe_aus_zahl_und_aus_namen():
    """
    Das Addon meldet die Stufe als Zahl, eine Sim-Ausgabe schreibt sie
    als Namen. Beide Wege enden hier, also versteht die Tabelle beide -
    und was weder das eine noch das andere ist, wird 0 statt geraten:
    eine erfundene Stufe rechnet dem Gegenstand gut 16 % Wertung zu,
    die er nicht hat.
    """

    assert upgrade_step(2) == 2

    assert upgrade_step("UpgradeStepTwo") == 2

    assert upgrade_step("ChallengeMode") == -1

    assert upgrade_step("Quatsch") == 0

    assert upgrade_step(None) == 0

    assert upgrade_step(99) == 0

    assert upgrade_step(True) == 0


def test_null_in_der_liste_ist_ein_leerer_platz():
    """
    Das Exporter-Addon schreibt einen unbesetzten Platz als `null`
    (seine JSON-Bibliothek füllt Lücken einer Liste so auf).
    """

    assert item_from_payload(None).empty

    assert item_from_payload({}).empty

    assert item_from_payload({"gems": [1]}).empty


# --------------------------------------------------
# Die ganze Nachricht
# --------------------------------------------------


def test_fassungsnummer_steht_an_beiden_stellen():
    """
    Der Sim führt jede Nachricht auf seinen aktuellen Stand hoch, wenn
    sie eine ältere Fassung nennt. Eine zu hohe Zahl überspränge diese
    Umbauten - der stille Fehler, der alte Zahlen als neue liest.
    """

    fields = decode(encode_settings([SimItem(item_id=1)]))

    assert fields[SETTINGS_API_VERSION][0] == API_VERSION

    player = decode(fields[SETTINGS_PLAYER][0])

    assert player[PLAYER_API_VERSION][0] == API_VERSION


def test_nur_die_ausruestung_steht_drin():
    """
    Der Sim räumt jeden Bereich vollständig ab, den die Adresse
    benennt. Talente und Glyphen liegen bei ihm in EINEM Bereich, und
    die Glyphen könnten wir nicht füllen (er führt sie als
    Gegenstands-Nummern, das Addon meldet Zauber-Nummern). Stünde hier
    mehr als die Ausrüstung, wäre der Preis dafür eine leere
    Glyphenleiste - lautlos.
    """

    player = decode(decode(encode_settings([SimItem(item_id=1)]))[
        SETTINGS_PLAYER
    ][0])

    assert set(player) == {PLAYER_EQUIPMENT, PLAYER_API_VERSION}


def test_echte_sim_ausgabe_kommt_feld_fuer_feld_zurueck():
    """
    Die Probe aufs Exempel: die Ausrüstung einer echten Sim-Ausgabe
    durch den Encoder und mit fremden Augen wieder heraus.
    """

    original = SIM_OUTPUT["player"]["equipment"]["items"]

    entries = items_of(
        encode_settings([item_from_payload(entry) for entry in original]),
    )

    assert len(entries) == len(original)

    steps = {
        "Base": 0,
        "UpgradeStepOne": 1,
        "UpgradeStepTwo": 2,
        "UpgradeStepThree": 3,
        "UpgradeStepFour": 4,
    }

    for source, decoded in zip(original, entries):

        if not source:

            assert decoded == {}

            continue

        assert decoded.get(ITEM_ID, [0])[0] == source.get("id", 0)

        assert decoded.get(ITEM_ENCHANT, [0])[0] == source.get("enchant", 0)

        assert decoded.get(ITEM_REFORGING, [0])[0] == source.get(
            "reforging", 0,
        )

        assert decoded.get(ITEM_TINKER, [0])[0] == source.get("tinker", 0)

        assert signed(
            decoded.get(ITEM_UPGRADE_STEP, [0])[0],
        ) == steps[source.get("upgradeStep", "Base")]

        gems = [gem or 0 for gem in source.get("gems", [])]

        while gems and not gems[-1]:
            gems.pop()

        assert packed(decoded.get(ITEM_GEMS, [b""])[0]) == gems


# --------------------------------------------------
# Die Adresse
# --------------------------------------------------


def test_adresse_traegt_bereich_und_nutzlast():

    link = build_link(
        "https://www.wowsims.com/mop/death_knight/blood/",
        [SimItem(item_id=86920)],
    )

    head, fragment = link.split("#", 1)

    assert head == (
        "https://www.wowsims.com/mop/death_knight/blood/"
        f"?i={CATEGORY_GEAR}"
    )

    #
    # Der Sim liest den Teil hinter dem `#` mit `pako.inflate`, und
    # das erwartet den zlib-Rahmen - nicht rohes Deflate.
    #

    raw = zlib.decompress(base64.b64decode(fragment))

    assert items_of(raw)[0][ITEM_ID][0] == 86920


def test_ein_vorhandenes_fragezeichen_wird_nicht_verdoppelt():

    link = build_link("https://example.test/mop/x/?lang=de", [SimItem(1)])

    assert "?lang=de&i=g#" in link


def test_ein_altes_fragment_wird_ersetzt():
    """
    Sonst stünden zwei Nutzlasten in einer Adresse, und welche gälte,
    entschiede der Browser.
    """

    link = build_link("https://example.test/mop/x/#alt", [SimItem(1)])

    assert link.count("#") == 1

    assert "#alt" not in link
