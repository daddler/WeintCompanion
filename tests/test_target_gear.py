"""
Die Zielausrüstung aus dem Sim - lesen, zuordnen, weiterreichen.

Ohne Qt und ohne Netz für alles ausser dem letzten Abschnitt (der baut
die Seite einmal offscreen auf, damit ein Tippfehler im Kartenaufbau
nicht erst im Spiel auffällt).

DREI FRAGEN, DIE HIER FESTGENAGELT WERDEN, weil sie im Betrieb nicht
mehr auffallen würden:

1. **Landet der Stein im richtigen Sockel?** Die Position in `gems` ist
   die ganze Aussage; eine Null, die verlorengeht, verschiebt jeden
   Stein dahinter.
2. **Landet das Teil im richtigen Platz?** Ring 1 und Ring 2 können
   dasselbe Teil sein. Zugeordnet wird über die POSITION in der Liste
   des Sims, nie über einen Namen.
3. **Ist das überhaupt ein Optimierungsergebnis?** Der Sim schreibt
   heraus, was gerade eingestellt ist - wer importiert und sofort
   exportiert, bekommt seinen Ausgangszustand zurück. `compare()` ist
   die einzige Stelle, an der sich das prüfen lässt.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.target_gear import (
    REFORGE_MAX,
    REFORGE_MIN,
    SLOT_IDS,
    TargetGear,
    TargetItem,
    TargetSet,
    build_transfer,
    changed_slots,
    compare,
    foreign_slots,
    parse_target,
    payload,
)
from core.wowsims_link import (
    DecodeError,
    SimItem,
    build_link,
    decode_fragment,
    fragment_of,
    item_from_payload,
)


DATA = Path(__file__).parent / "data" / "wowsims_mop_output.json"


def _sim_json() -> str:

    return DATA.read_text(encoding="utf-8")


def _sim_items() -> tuple[SimItem, ...]:

    payload_json = json.loads(_sim_json())

    return tuple(
        item_from_payload(entry)
        for entry in payload_json["player"]["equipment"]["items"]
    )


#
# --------------------------------------------------
# Der Rückweg aus dem Sim
# --------------------------------------------------
#


def test_the_link_decoder_reads_back_what_the_encoder_wrote():
    """
    Die Adresse ist das Format, in dem der Sim sein Ergebnis herausgibt.
    Geprüft wird an einer **echten** Sim-Ausgabe und Feld für Feld: eine
    verschobene Feldnummer käme sonst lautlos falsch an - ein Ring als
    Schmuckstück, eine Verzauberung als Stein.
    """

    items = _sim_items()

    link = build_link("https://www.wowsims.com/mop/death_knight/blood/", items)

    assert decode_fragment(fragment_of(link)) == items


def test_a_broken_fragment_fails_loudly():
    """
    Halb gelesen wäre eine Ausrüstung mit fehlenden Plätzen - und die
    sieht aus wie eine mit freien.
    """

    for text in ("nicht base64 ###", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"):

        try:
            decode_fragment(text)

        except DecodeError:
            continue

        except Exception as exc:  # pragma: no cover - Diagnose
            raise AssertionError(f"falscher Fehlertyp: {exc!r}")

        raise AssertionError(f"„{text}“ hätte scheitern müssen")


def test_an_empty_fragment_is_no_gear_and_no_error():

    assert decode_fragment("") == ()


#
# --------------------------------------------------
# Alle drei Gestalten sagen dasselbe
# --------------------------------------------------
#


def test_the_three_shapes_produce_the_same_target():
    """
    Sim-JSON, Adresse und Addon-Form sind derselbe Zielzustand. Ihre
    Kennung hängt am **Inhalt**, also muss sie dieselbe sein - sonst
    stünde im Spiel derselbe Vorschlag dreimal.
    """

    aus_json = parse_target(_sim_json())

    aus_link = parse_target(
        build_link(
            "https://www.wowsims.com/mop/death_knight/blood/",
            _sim_items(),
        )
    )

    aus_addon = parse_target(
        json.dumps(
            {
                "class": "deathknight",
                "spec": "blood",
                "name": "Aldrin",
                "realm": "Everlook",
                "gear": {
                    "items": json.loads(_sim_json())["player"]["equipment"]["items"]
                },
            }
        )
    )

    for target in (aus_json, aus_link, aus_addon):
        assert target is not None and target.known
        assert target.spec_key == "DEATHKNIGHT_BLOOD"

    assert aus_json.id == aus_link.id == aus_addon.id

    assert aus_json.items == aus_link.items == aus_addon.items


def test_the_source_is_carried_along():
    """
    „Aus der Adresse“ und „aus der JSON-Ausgabe“ sind für eine Rückfrage
    zwei verschiedene Auskünfte.
    """

    assert parse_target(_sim_json()).source == "wowsims_json"

    assert (
        parse_target(
            build_link(
                "https://www.wowsims.com/mop/death_knight/blood/", _sim_items()
            )
        ).source
        == "wowsims_link"
    )


def test_a_typed_weight_list_is_not_a_target():
    """
    Beide Textsorten landen in demselben Eingabefeld. Diese hier gehört
    den Sim-Gewichten - `parse_target()` muss sie durchfallen lassen,
    statt sie als kaputte Adresse zu melden.
    """

    for text in (
        "Hit 1.77\nCrit 0.89\nHaste 1.5",
        "strength|100,crit|58",
        "",
        "   ",
        "Das ist ein Satz.",
    ):
        assert parse_target(text) is None


def test_the_spec_comes_from_the_sims_own_url_table():
    """
    Die Schreibweisen im Sim-Pfad (`death_knight`, `beast_mastery`) sind
    andere als die des Exporter-Addons (`deathknight`, `marksman`).
    Gelesen wird deshalb rückwärts aus derselben Tabelle, die auch den
    Knopf „Sim öffnen“ füllt - eine zweite liefe auseinander.
    """

    items = _sim_items()

    for pfad, erwartet in (
        ("death_knight/blood", "DEATHKNIGHT_BLOOD"),
        ("hunter/beast_mastery", "HUNTER_BEASTMASTERY"),
        ("hunter/marksmanship", "HUNTER_MARKSMANSHIP"),
        ("priest/discipline", "PRIEST_DISCIPLINE"),
    ):
        target = parse_target(
            build_link(f"https://www.wowsims.com/mop/{pfad}/", items)
        )

        assert target.spec_key == erwartet, pfad


def test_a_tank_url_resolves_to_the_base_spec_not_the_offensive_variant():
    """
    Die fünf `*_OFFENSIVE`-Profile zeigen auf die Seite ihrer Basis-Spec.
    Rückwärts darf daraus nicht die Haltung werden - die kennt der Sim
    gar nicht, und der Spieler hat sie nie gewählt.
    """

    target = parse_target(
        build_link(
            "https://www.wowsims.com/mop/warrior/protection/", _sim_items()
        )
    )

    assert target.spec_key == "WARRIOR_PROTECTION"


#
# --------------------------------------------------
# Platz und Position
# --------------------------------------------------
#


def test_the_position_in_the_list_is_the_slot():
    """
    Der Sim führt die Ausrüstung als Liste; die Position ist der Platz.
    Genau daran hängt die Unterscheidung Ring 1 / Ring 2, Schmuck 1 /
    Schmuck 2 und Haupthand / Nebenhand.
    """

    assert SLOT_IDS == (
        1, 2, 3, 15, 5, 9, 10, 6, 7, 8, 11, 12, 13, 14, 16, 17, 18,
    )

    target = parse_target(_sim_json())

    plaetze = {item.slot: item for item in target.items}

    # Kopf: Meta plus ein farbiger Stein, in dieser Reihenfolge.
    assert plaetze[1].item_id == 86920
    assert plaetze[1].gems == (76895, 76639)

    # Finger 1 und Finger 2 sind zwei Einträge, nicht einer.
    assert plaetze[11].item_id == 86946
    assert plaetze[12].item_id == 87158
    assert plaetze[12].reforging == 143


def test_two_identical_items_stay_two_entries():
    """
    Zwei gleiche Ringe sind zwei Ringe. Über die Gegenstandsnummer
    allein wäre nicht zu unterscheiden, welcher welche Steine bekommt.
    """

    items = [SimItem() for _ in range(17)]

    items[10] = SimItem(item_id=86946, gems=(76692,))
    items[11] = SimItem(item_id=86946, gems=(76680,))

    target = parse_target(
        build_link("https://www.wowsims.com/mop/druid/feral/", items)
    )

    ringe = [item for item in target.items if item.slot in (11, 12)]

    assert len(ringe) == 2
    assert ringe[0].slot == 11 and ringe[0].gems == (76692,)
    assert ringe[1].slot == 12 and ringe[1].gems == (76680,)


def test_an_empty_slot_does_not_shift_the_ones_behind_it():
    """
    Ein leerer Platz ist ein Platz. Fällt er heraus, rückt die
    Zweitwaffe in die Waffenhand - derselbe Fehler, den `field_bytes`
    beim Schreiben ausdrücklich vermeidet.
    """

    items = [SimItem() for _ in range(17)]

    items[14] = SimItem(item_id=87176)       # Haupthand
    items[15] = SimItem()                    # Nebenhand leer
    items[16] = SimItem(item_id=89999)       # Distanz

    target = parse_target(
        build_link("https://www.wowsims.com/mop/hunter/survival/", items)
    )

    plaetze = {item.slot: item.item_id for item in target.items}

    assert plaetze[16] == 87176
    assert plaetze.get(17, 0) == 0
    assert plaetze[18] == 89999


def test_a_hole_between_gems_is_preserved():
    """
    Eine Null ZWISCHEN zwei Steinen ist ein leerer Sockel, und die
    Position benennt ihn. Wird sie verdichtet, rutscht der dritte Stein
    in den zweiten Sockel.
    """

    items = [SimItem() for _ in range(17)]

    items[4] = SimItem(item_id=86918, gems=(76692, 0, 76680))

    target = parse_target(
        build_link("https://www.wowsims.com/mop/druid/feral/", items)
    )

    brust = next(item for item in target.items if item.slot == 5)

    assert brust.gems == (76692, 0, 76680)


#
# --------------------------------------------------
# Umschmiedungen
# --------------------------------------------------
#


def test_only_real_reforge_ids_survive():
    """
    Der Umschmiedewert wird im Spiel zu einer laufenden Nummer im
    Umschmieder. Eine erfundene schmiedet etwas anderes, als auf der
    Seite steht - und das fällt erst am Ergebnis auf, nachdem Gold
    ausgegeben wurde.
    """

    items = [SimItem() for _ in range(17)]

    items[0] = SimItem(item_id=1, gems=(76692,), reforging=REFORGE_MIN)
    items[1] = SimItem(item_id=2, gems=(76692,), reforging=REFORGE_MAX)
    items[2] = SimItem(item_id=3, gems=(76692,), reforging=REFORGE_MAX + 1)
    items[3] = SimItem(item_id=4, gems=(76692,), reforging=42)

    target = parse_target(
        build_link("https://www.wowsims.com/mop/druid/feral/", items)
    )

    werte = {item.slot: item.reforging for item in target.items}

    assert werte[1] == REFORGE_MIN
    assert werte[2] == REFORGE_MAX
    assert werte[15] == 0
    assert werte[5] == 0


def test_the_real_sim_output_carries_reforges_and_gems():
    """
    Die Grundfrage dieser ganzen Änderung: steht in dem, was der Sim
    herausgibt, überhaupt beides drin?
    """

    target = parse_target(_sim_json())

    assert target.gem_count == 16
    assert target.reforge_count == 11
    assert target.usable is True


#
# --------------------------------------------------
# Ziel gegen Ist: lief überhaupt ein Optimierungslauf?
# --------------------------------------------------
#


def test_an_unchanged_target_is_reported_as_unchanged():
    """
    Der Verdachtsfall. Wer im Sim importiert und sofort exportiert,
    bekommt seinen Ausgangszustand zurück - und der sähe aus wie eine
    Optimierung. Im Spiel brächte er JEDE Empfehlung zum Schweigen.
    """

    target = parse_target(_sim_json())

    diffs = compare(target, _sim_items())

    assert diffs
    assert changed_slots(diffs) == ()
    assert foreign_slots(diffs) == ()


def test_a_changed_gem_and_a_changed_reforge_are_both_seen():

    target = parse_target(_sim_json())

    ist = list(_sim_items())

    ist[0] = SimItem(
        item_id=86920,
        gems=(76895, 76653),          # zweiter Stein anders
        reforging=140,                # und die Umschmiedung
        upgrade_step=2,
    )

    geaendert = changed_slots(compare(target, ist))

    assert [diff.slot for diff in geaendert] == [1]
    assert geaendert[0].gems_differ is True
    assert geaendert[0].reforge_differs is True
    assert geaendert[0].slot_name == "Kopf"


def test_a_different_item_in_the_slot_is_not_a_change():
    """
    Dann ist nicht die Optimierung eine andere, sondern die
    Ausrüstung - und für diesen Platz gilt das Ziel im Spiel gar nicht.
    Ein Text für beides wäre für einen der beiden Fälle falsch.
    """

    target = parse_target(_sim_json())

    ist = list(_sim_items())

    ist[0] = SimItem(item_id=99999, gems=(1, 2), reforging=113)

    diffs = compare(target, ist)

    assert changed_slots(diffs) == ()

    assert [diff.slot for diff in foreign_slots(diffs)] == [1]


def test_a_missing_enchant_in_the_target_is_no_difference():
    """
    Der Sim führt Verzauberungen nur mit, wenn sie eingestellt sind.
    Eine fehlende als Unterschied zu zählen hiesse, jedem eine Änderung
    zu melden, die keine ist.
    """

    target = TargetGear(
        known=True,
        source="wowsims_json",
        spec_key="DRUID_FERAL",
        items=(TargetItem(slot=1, item_id=5, gems=(76692,), enchant=0),),
    )

    ist = [SimItem(item_id=5, gems=(76692,), enchant=4805)]

    assert changed_slots(compare(target, ist)) == ()


#
# --------------------------------------------------
# Hinüber ins Spiel
# --------------------------------------------------
#


def _set() -> TargetSet:

    target = parse_target(_sim_json())

    return TargetSet(
        gear=target,
        spec_key=target.spec_key,
        character="Aldrin",
        realm="Everlook",
        created=1788186037,
    )


def test_the_transfer_string_has_the_shape_of_the_other_imports():

    text = build_transfer(_set())

    assert text.startswith("WCIMPORT:TG:")

    abschnitte = text.split(":")

    assert abschnitte[2] == "DEATHKNIGHT_BLOOD"
    assert abschnitte[5] == "Aldrin"

    zeilen = abschnitte[7].split(",")

    # Erster Platz: Kopf, mit Meta und farbigem Stein.
    assert zeilen[0].startswith("1|86920|76895-76639|161|")


def test_the_transfer_string_keeps_a_hole_between_gems():

    entry = TargetSet(
        gear=TargetGear(
            known=True,
            source="wowsims_json",
            spec_key="DRUID_FERAL",
            items=(TargetItem(slot=5, item_id=86918, gems=(76692, 0, 76680)),),
        ),
        spec_key="DRUID_FERAL",
        created=1,
    )

    assert "5|86918|76692-0-76680|0|0" in build_transfer(entry)


def test_the_payload_carries_slot_gems_and_reforge():

    data = payload([_set()])

    assert data["version"] == 1

    satz = data["sets"][0]

    assert satz["spec"] == "DEATHKNIGHT_BLOOD"
    assert satz["character"] == "Aldrin"

    kopf = satz["items"][0]

    assert kopf["slot"] == 1
    assert kopf["itemId"] == 86920
    assert kopf["gems"] == [76895, 76639]
    assert kopf["reforge"] == 161

    # Leere Plätze gehören nicht in die Zustellung: über einen Platz
    # ohne Gegenstand sagt das Ziel nichts.
    assert all(row["itemId"] for row in satz["items"])


def test_the_id_changes_with_the_content_and_only_with_it():

    erst = parse_target(_sim_json())

    items = list(_sim_items())

    items[0] = SimItem(item_id=86920, gems=(76895, 76653), reforging=161,
                       upgrade_step=2)

    anders = parse_target(
        build_link("https://www.wowsims.com/mop/death_knight/blood/", items)
    )

    assert erst.id != anders.id

    nochmal = parse_target(_sim_json())

    assert erst.id == nochmal.id


#
# --------------------------------------------------
# Ablage
# --------------------------------------------------
#


class _Logger:

    def info(self, *_):
        pass

    def warning(self, *_):
        pass

    def error(self, *_):
        pass

    def success(self, *_):
        pass


class _Manager:

    def __init__(self):
        self.logger = _Logger()


def test_the_store_survives_a_restart(tmp_path):
    """
    `target_gear.json` liegt unter `config()` und nicht unter `cache()`:
    dahinter steht ein Sim-Lauf.
    """

    from core.target_gear_store import TargetGearStore

    pfad = tmp_path / "target_gear.json"

    erst = TargetGearStore(_Manager(), path=pfad)

    erst.put(_set())

    danach = TargetGearStore(_Manager(), path=pfad)

    entry = danach.get("DEATHKNIGHT_BLOOD")

    assert entry is not None
    assert entry.character == "Aldrin"
    assert entry.items[0].slot == 1
    assert entry.items[0].gems == (76895, 76639)
    assert entry.items[0].reforging == 161

    # Und die Kennung bleibt dieselbe - sonst stünde derselbe
    # Zielzustand nach jedem Neustart als neuer Vorschlag da.
    assert entry.id == _set().id


def test_one_target_per_spec(tmp_path):

    from core.target_gear_store import TargetGearStore

    store = TargetGearStore(_Manager(), path=tmp_path / "t.json")

    store.put(_set())
    store.put(_set())

    assert len(store.sets()) == 1

    assert store.remove("DEATHKNIGHT_BLOOD") is True
    assert store.get("DEATHKNIGHT_BLOOD") is None


# --------------------------------------------------
# Die Kennung des Sim-Laufs (seit 3.3.0)
# --------------------------------------------------


def test_the_run_id_is_appended_and_breaks_no_older_addon():
    """
    ABSCHNITT 7 IST ANGEHAENGT, UND DAS IST DIE GANZE VERTRAEGLICHKEIT.

    `TG.ParseTransfer` drüben liest die Felder 1 bis 6 über feste
    Positionen und ignoriert alles dahinter. Ein älteres WeintCodex
    bekommt damit genau denselben Zielzustand wie bisher - die Kennung
    fällt weg, sonst nichts.

    Das ist der Unterschied zu zwei Umschlägen in einer Zeile, wo genau
    diese Nachsicht die zweite Auskunft still verschluckt hätte: dort
    fehlte eine ganze Auskunft, hier nur ihre Herkunft.
    """

    entry = TargetSet(
        gear=TargetGear(
            known=True,
            source="wowsims_json",
            spec_key="DEATHKNIGHT_BLOOD",
            items=(TargetItem(slot=1, item_id=86920, gems=(76895, 0, 76639)),),
        ),
        spec_key="DEATHKNIGHT_BLOOD",
        created=1788186037,
        run_id="SIM-20260909-7F4A",
        started_at=1788185000,
    )

    text = build_transfer(entry)

    parts = text[len("WCIMPORT:TG:"):].split(":")

    # Die sechs alten Abschnitte stehen unverändert an ihrem Platz.
    assert parts[0] == "DEATHKNIGHT_BLOOD"
    assert parts[2] == "1788186037"
    assert parts[5].startswith("1|86920|76895-0-76639|")

    # Und die Kennung dahinter, mit ihren Bindestrichen - plus der
    # Zeitstempel der Ausrüstung, mit der gesimmt wurde. Der stammt aus
    # der Uhr des SPIELS und ist die Zahl, an der das Addon erkennt, ob
    # das hier der Lauf ist, auf den es wartet.
    assert parts[6] == "SIM-20260909-7F4A"
    assert parts[7] == "1788185000"


def test_a_run_id_never_takes_the_string_apart():
    """
    Sie ist unsere eigene Zeichenkette - aber sie kommt aus einer Datei,
    und eine Datei kann alles enthalten. Der Bindestrich bleibt (er
    trennt nur INNERHALB eines Datensatzes die Steine, nicht zwischen
    zwei `:`-Abschnitten), alles andere fällt weg.
    """

    from core.target_gear import clean_run_id

    assert clean_run_id("SIM-20260909-7F4A") == "SIM-20260909-7F4A"

    assert clean_run_id("SIM:2026|09,09") == "SIM20260909"

    assert clean_run_id("") == ""


def test_an_entry_without_a_run_id_stays_valid():
    """
    Jeder Zielzustand von vor 3.3.0 hat keine Kennung. Das ist kein
    Fehler und wird keiner - er sagt nur nichts über seine Herkunft.
    """

    entry = TargetSet(
        gear=TargetGear(
            known=True,
            spec_key="DEATHKNIGHT_BLOOD",
            items=(TargetItem(slot=1, item_id=86920, gems=(76895,)),),
        ),
        spec_key="DEATHKNIGHT_BLOOD",
    )

    assert entry.run_id == ""

    assert build_transfer(entry).endswith(":0")

    assert payload([entry])["sets"][0]["run"] == ""

    assert payload([entry])["sets"][0]["startedAt"] == 0


def test_gem_changes_count_sockets_and_ignore_the_zero():
    """
    Die Seite sagt „7 Sockeländerungen", nicht „4 Teile". Eine 0 im Ziel
    zählt dabei NICHT mit: sie heisst „das Ziel nennt für diesen Sockel
    keinen Stein" und nicht „nimm den Stein heraus" - sie als Änderung
    zu zählen wäre eine Empfehlung in die teure Richtung.
    """

    target = TargetGear(
        known=True,
        spec_key="DEATHKNIGHT_BLOOD",
        items=(TargetItem(slot=1, item_id=86920, gems=(76895, 0, 76639)),),
    )

    ist = (SimItem(item_id=86920, gems=(76653, 76653, 76639)),)

    diffs = compare(target, ist)

    assert len(diffs) == 1

    # Sockel 1 ist anders, Sockel 2 sagt das Ziel nichts, Sockel 3 gleich.
    assert diffs[0].gem_changes == 1

    assert diffs[0].gems_differ is True
