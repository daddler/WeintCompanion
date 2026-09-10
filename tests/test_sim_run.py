"""
Der Sim-Lauf: eine Klammer um zwei Auskünfte.

WAS HIER FESTGENAGELT WIRD, UND WARUM ES SONST NIEMAND MERKEN WUERDE.

Der ganze Sinn dieser Schicht ist, Fehler sichtbar zu machen, die sich
sonst als *korrekte Empfehlung* tarnen. Alle vier sehen im Spiel
identisch aus zu „so wollte es der Sim":

1. **Es wurde gar nicht optimiert.** Der Sim gibt heraus, was gerade
   eingestellt ist; wer importiert und sofort exportiert, bekommt seinen
   Ausgangszustand. Im Spiel bringt der jede Empfehlung zum Schweigen.
2. **Es fehlt eine Hälfte.** Eine Gewichtung ohne Zielzustand ist eine
   gültige Auskunft - aber wer beides wollte und nur eins bekam, sieht
   den Unterschied nirgends.
3. **Es passt nicht mehr zur Ausrüstung.** Ein Zielzustand gilt für
   genau die Ausrüstung, mit der gesimmt wurde.
4. **Es sind zwei verschiedene Läufe.** Eine Gewichtung von gestern
   neben einem Zielzustand von heute - beide für sich in Ordnung,
   zusammen eine Aussage über zwei verschiedene Ausrüstungen.

Kein Qt, keine Datei - wie die beiden Module darunter.
"""

from __future__ import annotations

import json
from pathlib import Path

from core import sim_run
from core.target_gear import parse_target
from core.wowsims_export import parse_export


DATA = Path(__file__).parent / "data" / "wowsims_mop_output.json"


def _sim_json() -> str:

    return DATA.read_text(encoding="utf-8")


def _export(items=None, char_class="deathknight", spec="blood"):
    """
    Eine Meldung des WowSimsExporters aus derselben echten Sim-Ausgabe.

    Genau das ist der Normalfall des Verdachts: Ausgangszustand und
    Ergebnis sind Stück für Stück dasselbe.
    """

    payload = json.loads(_sim_json())

    return parse_export(
        json.dumps(
            {
                "class": char_class,
                "spec": spec,
                "level": 90,
                "name": "Aldrin",
                "realm": "Everlook",
                "gear": {
                    "items": items
                    if items is not None
                    else payload["player"]["equipment"]["items"]
                },
            }
        )
    )


def _changed_items():
    """
    Dieselbe Ausrüstung, aber an zwei Plätzen anders gesteint und
    umgeschmiedet - der Iststand VOR einer Optimierung.
    """

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    items[0] = dict(items[0], gems=[76895, 76653], reforging=140)

    items[4] = dict(items[4], reforging=150)

    return items


def _run_with(target=True, weights=True, export=None, spec="DEATHKNIGHT_BLOOD"):

    run = sim_run.start_run(spec, export=export, reported_at=1788186000)

    if weights:
        run = sim_run.with_weights(
            run, {"strength": 100, "crit": 58}, "sim", "deathknight"
        )

    if target:
        run = sim_run.with_target(run, parse_target(_sim_json()))

    return run


# --------------------------------------------------
# Die Kennung
# --------------------------------------------------


def test_the_run_id_hangs_on_the_run_not_on_the_clock():
    """
    Zweimal derselbe Ausgangszustand ist derselbe Lauf.

    Ohne diese Regel wäre die Kennung eine laufende Nummer: die
    Gewichtung bekäme eine andere als der Zielzustand, obwohl beide aus
    einem Lauf stammen - und die Korrelation wäre genau falsch herum.
    """

    export = _export()

    eins = sim_run.start_run("DEATHKNIGHT_BLOOD", export=export, reported_at=1788186000)

    zwei = sim_run.start_run("DEATHKNIGHT_BLOOD", export=export, reported_at=1788186000)

    assert eins.run_id
    assert eins.run_id == zwei.run_id

    assert eins.run_id.startswith("SIM-")


def test_a_different_gear_is_a_different_run():
    """
    Wer zwischendurch ein Teil wechselt und neu bereitstellt, hat einen
    anderen Lauf - und das ist richtig: ein Zielzustand gilt für genau
    die Ausrüstung, mit der gesimmt wurde.
    """

    eins = sim_run.start_run(
        "DEATHKNIGHT_BLOOD", export=_export(), reported_at=1788186000
    )

    zwei = sim_run.start_run(
        "DEATHKNIGHT_BLOOD",
        export=_export(_changed_items()),
        reported_at=1788186000,
    )

    assert eins.run_id != zwei.run_id


def test_a_run_without_gear_has_no_id():
    """
    EIN LAUF OHNE ANKER HAT KEINE IDENTITAET.

    Eine zu erfinden wäre schlimmer als keine: sie hinge an der Uhr
    dieses Rechners, wäre bei jedem Betreten der Seite eine andere, und
    die Frage „gehören diese beiden zusammen" bekäme jedes Mal ein
    falsches Nein. Dieselbe Regel wie `at == -1`.
    """

    run = sim_run.start_run("DEATHKNIGHT_BLOOD", export=None, now=1788186000)

    assert run.run_id == ""

    assert run.input_gear is None


def test_the_started_at_comes_from_the_game_clock():
    """
    Der Startzeitpunkt ist der Zeitstempel des Exports, nicht die Uhr
    dieses Rechners. Daran hängt der Handshake im Spiel: das Addon merkt
    sich beim *Bereitstellen* dieselbe Zahl.
    """

    run = sim_run.start_run(
        "DEATHKNIGHT_BLOOD", export=_export(), reported_at=1788186000, now=999
    )

    assert run.started_at == 1788186000


# --------------------------------------------------
# Die sechs Zustände
# --------------------------------------------------


def test_nothing_read_is_the_starting_point_not_an_error():

    befund = sim_run.validate(None)

    assert befund.state == sim_run.EMPTY

    assert befund.usable is False

    leer = sim_run.validate(sim_run.start_run("DEATHKNIGHT_BLOOD"))

    assert leer.state == sim_run.EMPTY


def test_weights_alone_are_incomplete_but_usable():
    """
    Eine Gewichtung allein ist eine vollwertige Auskunft - sie
    zurückzuhalten, bis der zweite Export da ist, wäre eine Strafe für
    einen Zwischenstand. Sie ist nur nicht *vollständig*.
    """

    befund = sim_run.validate(
        _run_with(target=False, export=_export()),
        expected_spec="DEATHKNIGHT_BLOOD",
    )

    assert befund.state == sim_run.INCOMPLETE

    assert befund.missing == ("target",)

    assert befund.usable is True

    assert befund.complete is False

    assert "optimierte ausrüstung fehlt noch" in sim_run.headline(befund).lower()

    assert "Export → Link" in sim_run.next_step(befund)


def test_target_alone_is_incomplete_the_other_way_round():

    befund = sim_run.validate(
        _run_with(weights=False, export=_export(_changed_items())),
        expected_spec="DEATHKNIGHT_BLOOD",
    )

    assert befund.state == sim_run.INCOMPLETE

    assert befund.missing == ("weights",)

    assert "Stat Weights" in sim_run.next_step(befund)


def test_both_together_and_something_changed_is_ready():

    befund = sim_run.validate(
        _run_with(export=_export(_changed_items())),
        expected_spec="DEATHKNIGHT_BLOOD",
    )

    assert befund.state == sim_run.READY

    assert befund.complete is True

    assert sim_run.next_step(befund) == ""

    #
    # Und die Zahlen sind nachzählbar: zwei Plätze, ein getauschter
    # Stein, zwei geänderte Umschmiedungen.
    #

    assert befund.checked_slots > 0

    assert befund.changed_slots == 2

    assert befund.gem_changes == 1

    assert befund.reforge_changes == 2

    assert "Kopf" in sim_run.change_line(befund)


def test_no_change_is_not_success():
    """
    DER VERDACHTSFALL. Ein Zielzustand, der Stück für Stück der
    Iststand ist, brächte im Spiel jede Empfehlung zum Schweigen - und
    das wäre von einer wirklich fertigen Ausrüstung nicht zu
    unterscheiden. Beide Möglichkeiten stehen da, keine wird behauptet.
    """

    befund = sim_run.validate(
        _run_with(export=_export()), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.UNCHANGED

    assert befund.changed_slots == 0

    satz = sim_run.change_line(befund)

    assert "kein Unterschied" in satz

    assert "bereits alles optimal" in satz

    assert "kein Optimierungslauf" in satz


def test_a_foreign_class_is_named_not_rejected():
    """
    Vielleicht simmt jemand für seinen Zweitcharakter. Er soll es
    wissen - abgewiesen wird es nicht, und `usable` bleibt wahr.
    """

    run = sim_run.start_run(
        "MAGE_FIRE", export=_export(), reported_at=1788186000
    )

    run = sim_run.with_weights(run, {"intellect": 100}, "sim", "deathknight")

    befund = sim_run.validate(run, expected_spec="MAGE_FIRE")

    assert befund.state == sim_run.MISMATCH

    assert befund.usable is True

    assert "Todesritter" in sim_run.class_note(run, "MAGE_FIRE")


def test_a_matching_class_says_nothing():

    run = _run_with(export=_export())

    assert sim_run.class_note(run, "DEATHKNIGHT_BLOOD") == ""


def test_a_result_for_another_gear_is_stale_not_incomplete():
    """
    VERALTET IST NICHT UNVOLLSTAENDIG. Den fehlenden Teil nachzuliefern
    hilft daran nichts - gesimmt wurde mit einer anderen Ausrüstung.

    Ein EINZELNES getauschtes Teil ist dagegen der Normalfall (ein Drop
    zwischen Simmen und Einfügen); dafür gibt es im Spiel den Rückfall
    je Platz, und den ganzen Lauf deswegen zu verwerfen wäre die teure
    Antwort in die falsche Richtung.
    """

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    for index, entry in enumerate(items):

        # Ein leerer Platz bleibt leer: aus einer fehlenden
        # Gegenstandsnummer eine zu machen hiesse, Ausruestung zu
        # erfinden, die es nicht gibt.
        if entry.get("id"):
            items[index] = dict(entry, id=int(entry["id"]) + 1000)

    befund = sim_run.validate(
        _run_with(export=_export(items)), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.STALE

    assert befund.foreign_slots >= 2

    assert "neu bereitstellen" in sim_run.next_step(befund)


def test_one_swapped_item_is_a_note_and_not_a_state():

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    items[0] = dict(items[0], id=int(items[0]["id"]) + 1000)

    items[4] = dict(items[4], reforging=150)

    befund = sim_run.validate(
        _run_with(export=_export(items)), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.READY

    assert befund.foreign_slots == 1

    assert "foreign" in befund.notes


def test_without_reported_gear_the_question_stays_open():
    """
    Nichts wird geraten. Ohne Ausgangszustand bleibt „wurde überhaupt
    optimiert" **offen** statt mit „ja" beantwortet zu werden.
    """

    befund = sim_run.validate(
        _run_with(export=None), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.comparable is False

    assert befund.state == sim_run.READY

    assert "unverifiable" in befund.notes

    assert "lässt sich hier nicht prüfen" in sim_run.change_line(befund)


def test_a_healer_run_is_complete_without_a_target():
    """
    QE Live gibt keinen Zielzustand heraus. Einen zu vermissen wäre
    eine Aufforderung ins Leere - dieselbe Zurückhaltung wie beim
    ausgeblendeten *Export kopieren* im Heiler-Zweig.
    """

    run = sim_run.start_run("PRIEST_HOLY", export=None)

    run = sim_run.with_weights(run, {"intellect": 100}, "qelive", "")

    befund = sim_run.validate(
        run, expected_spec="PRIEST_HOLY", target_expected=False
    )

    assert befund.state == sim_run.READY

    assert befund.complete is True

    assert befund.missing == ()

    assert "Optimierte Ausrüstung" not in sim_run.parts_line(befund)


# --------------------------------------------------
# Sammeln statt ersetzen
# --------------------------------------------------


def test_the_second_paste_adds_to_the_same_run():
    """
    DAS IST DER KERN. Bis 3.2.0 war das zweite Einfügen ein zweiter
    Vorgang mit eigenem Knopf; wer ihn vergaß, bekam im Spiel eine
    halbe Auskunft, der man das nicht ansieht.
    """

    run = sim_run.start_run(
        "DEATHKNIGHT_BLOOD", export=_export(_changed_items()), reported_at=1788186000
    )

    run = sim_run.with_weights(run, {"strength": 100}, "sim", "deathknight")

    assert sim_run.validate(run, "DEATHKNIGHT_BLOOD").state == sim_run.INCOMPLETE

    run = sim_run.with_target(run, parse_target(_sim_json()))

    #
    # Die Gewichtung ist noch da - und beide tragen dieselbe Kennung.
    #

    assert run.have_weights is True

    assert run.have_target is True

    assert sim_run.validate(run, "DEATHKNIGHT_BLOOD").state == sim_run.READY


def test_a_second_weight_paste_replaces_rather_than_adds():
    """
    Niemand fügt dieselbe Auskunft zweimal ein, um beide zu behalten.
    """

    run = sim_run.start_run("DEATHKNIGHT_BLOOD", export=_export())

    run = sim_run.with_weights(run, {"strength": 100}, "sim", "deathknight")

    run = sim_run.with_weights(run, {"crit": 100}, "sim", "deathknight")

    assert run.weights == {"crit": 100}


# --------------------------------------------------
# Korrelation: gehört das Abgelegte zusammen?
# --------------------------------------------------


class _Entry:

    def __init__(self, run_id=""):
        self.run_id = run_id


def test_two_runs_side_by_side_are_named():
    """
    Der Fall, den man einer Empfehlung im Spiel nicht ansieht: eine
    Gewichtung aus dem Lauf von gestern neben einem Zielzustand von
    heute. Beide für sich in Ordnung.
    """

    stored = sim_run.stored_state(
        _Entry("SIM-20260908-AAAA"), _Entry("SIM-20260909-BBBB")
    )

    assert stored.mixed is True

    satz = sim_run.mixed_note(stored)

    assert "SIM-20260908-AAAA" in satz

    assert "SIM-20260909-BBBB" in satz


def test_the_same_run_is_not_flagged():

    stored = sim_run.stored_state(
        _Entry("SIM-20260909-BBBB"), _Entry("SIM-20260909-BBBB")
    )

    assert stored.mixed is False

    assert stored.belongs("SIM-20260909-BBBB") is True

    assert sim_run.mixed_note(stored) == ""


def test_without_an_id_nothing_is_claimed():
    """
    Eine von Hand getippte Gewichtung hat keine Kennung, und jeder
    Eintrag von vor 3.3.0 ebenfalls. „Gemischt" wäre dort eine Warnung
    über etwas, das niemand nachsehen kann.
    """

    stored = sim_run.stored_state(_Entry(""), _Entry("SIM-20260909-BBBB"))

    assert stored.mixed is False

    assert sim_run.mixed_note(stored) == ""

    assert stored.belongs("SIM-20260909-BBBB") is False


def test_only_one_side_stored_is_never_mixed():

    stored = sim_run.stored_state(_Entry("SIM-20260909-BBBB"), None)

    assert stored.have_target is False

    assert stored.mixed is False


# --------------------------------------------------
# Die Sätze
# --------------------------------------------------


def test_the_parts_line_speaks_the_users_language():
    """
    `stat_weights` und `target_gear` sind Namen aus dem Quelltext. Wer
    sie liest, muss sie erst übersetzen - und genau das soll diese
    Seite dem Nutzer abnehmen.
    """

    befund = sim_run.validate(
        _run_with(export=_export(_changed_items())),
        expected_spec="DEATHKNIGHT_BLOOD",
    )

    zeile = sim_run.parts_line(befund)

    assert "Gewichtung ✓" in zeile

    assert "Optimierte Ausrüstung ✓" in zeile

    assert "stat_weights" not in zeile

    assert "target_gear" not in zeile


def test_the_run_label_can_be_read_back():

    run = _run_with(export=_export())

    zeile = sim_run.run_label(run)

    assert run.run_id in zeile

    assert "Blut" in zeile or "DEATHKNIGHT" in zeile.upper()


def test_the_source_line_names_what_was_read():

    run = _run_with(export=_export())

    zeile = sim_run.source_line(run)

    assert "Sockelsteine" in zeile

    assert "Umschmiedungen" in zeile


# --------------------------------------------------
# Was der Durchgang als Nutzer zutage gefördert hat
# --------------------------------------------------
#
# Vier Befunde aus dem Durchspielen des ganzen Wegs — jeder davon eine
# Aussage, die stimmte, solange man sie nicht mit einer zweiten daneben
# gelesen hat.


def test_all_items_swapped_is_never_already_optimal():
    """
    DER SCHLIMMSTE DER VIER. Ein Ergebnis, bei dem an **keinem** Platz
    mehr dasselbe Teil steckt, hat null Unterschiede — und der Satz
    dazu lautete „kein Unterschied. Möglicherweise ist bereits alles
    optimal". Genau in die teure Richtung falsch: die Frage nach der
    Optimierung ist dort gar nicht gestellt worden.
    """

    payload = json.loads(_sim_json())

    items = []

    for entry in payload["player"]["equipment"]["items"]:

        entry = dict(entry)

        if entry.get("id"):
            entry["id"] = int(entry["id"]) + 1000

        items.append(entry)

    befund = sim_run.validate(
        _run_with(export=_export(items)), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.STALE

    satz = sim_run.change_line(befund)

    assert "bereits alles optimal" not in satz

    assert "kein Unterschied" not in satz

    assert "steckt noch das Teil" in satz


def test_unchanged_counts_only_comparable_slots():
    """
    Ein Platz mit einem anderen Teil ist keine Aussage über die
    Optimierung. Ihn in „N Plätze geprüft, kein Unterschied"
    mitzuzählen macht aus einer fehlenden Vergleichsmöglichkeit ein
    „schon optimal".
    """

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    items[0] = dict(items[0], id=int(items[0]["id"]) + 1000)

    befund = sim_run.validate(
        _run_with(export=_export(items)), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.UNCHANGED

    assert befund.foreign_slots == 1

    satz = sim_run.change_line(befund)

    assert f"{befund.checked_slots - 1} vergleichbare" in satz


def test_the_foreign_count_is_named_in_both_cases():
    """
    Wer 15 von 15 fremden Plätzen hat, will die 15 lesen — und wer 1
    von 15 hat, ebenfalls. Der Zustand sagt, wie schlimm es ist; die
    Notiz sagt, wie viel.
    """

    payload = json.loads(_sim_json())

    items = []

    for entry in payload["player"]["equipment"]["items"]:

        entry = dict(entry)

        if entry.get("id"):
            entry["id"] = int(entry["id"]) + 1000

        items.append(entry)

    befund = sim_run.validate(
        _run_with(export=_export(items)), expected_spec="DEATHKNIGHT_BLOOD"
    )

    assert befund.state == sim_run.STALE

    assert "foreign" in befund.notes


def test_a_target_for_another_class_is_a_mismatch_too():
    """
    Eine andere **Spezialisierung** ist ein Hinweis — die Zweitspec mit
    laufender Ausrüstung zu simmen ist der Normalfall. Eine andere
    **Klasse** ist ein Missverhältnis: der Zielzustand nennt
    Gegenstandsnummern, die dieser Charakter nie tragen wird.

    Abgewiesen wird auch er nicht; benannt schon.
    """

    run = sim_run.start_run(
        "MAGE_FIRE", export=_export(_changed_items()), reported_at=1788186000
    )

    run = sim_run.with_target(run, parse_target(_sim_json()))

    befund = sim_run.validate(run, expected_spec="MAGE_FIRE")

    assert befund.state == sim_run.MISMATCH

    assert befund.usable is True

    assert "other_spec" in befund.notes


def test_another_spec_of_the_same_class_stays_a_note():

    run = sim_run.start_run(
        "DEATHKNIGHT_FROST",
        export=_export(_changed_items()),
        reported_at=1788186000,
    )

    run = sim_run.with_weights(run, {"strength": 100}, "sim", "deathknight")

    run = sim_run.with_target(run, parse_target(_sim_json()))

    befund = sim_run.validate(run, expected_spec="DEATHKNIGHT_FROST")

    assert befund.state != sim_run.MISMATCH

    assert "other_spec" in befund.notes


# --------------------------------------------------
# Was für ein Text ist das?
# --------------------------------------------------


def test_a_sim_result_is_recognized_without_being_read():
    """
    Die Frage muss gestellt werden können, **ohne etwas zu tun** -
    sonst darf die Seite nicht von sich aus in die Zwischenablage
    sehen.
    """

    assert sim_run.recognize(_sim_json()) == sim_run.TARGET

    assert sim_run.recognize("Hit 1,77\nCrit 0,89") == sim_run.WEIGHTS


def test_everything_else_is_nothing():
    """
    Im Lauf eines Abends liegt in derselben Zwischenablage ein
    Dateipfad, ein Zitat, ein halber Befehl. Ein „vielleicht doch"
    hiesse hier: ein Eingabefeld, das sich mit Fremdem füllt.
    """

    for fremd in (
        "",
        "   ",
        "hallo welt",
        "C:\\Users\\Kelthuzad\\Desktop",
        "https://example.com/keine-ausgabe",
        "SIM-20260909-7F4A",
    ):

        assert sim_run.recognize(fremd) == sim_run.NOTHING


def test_what_goes_into_the_game_is_never_read_back():
    """
    `WCIMPORT:` ist der Weg *ins Spiel*. Ihn zurückzulesen hiesse, das
    eigene Ergebnis für ein neues zu halten.
    """

    run = sim_run.start_run(
        "DEATHKNIGHT_FROST",
        export=_export(),
        reported_at=1788186000,
    )

    run = sim_run.with_weights(run, {"strength": 100}, "sim", "deathknight")

    for umschlag in (
        "WCIMPORT:SW:deathknight_frost:x:1:Kel:sim:strength|100:"
        + run.run_id
        + ":1788186000",
        "WCIMPORT:TG:deathknight_frost:x:1:Kel:sim:head|76895-0:"
        + run.run_id
        + ":1788186000",
    ):

        assert sim_run.recognize(umschlag) == sim_run.NOTHING


def test_a_result_without_a_single_gem_is_still_a_result():
    """
    Erkannt heisst nicht brauchbar, und das ist Absicht: für den
    Export, in dem kein Sockelstein gerechnet wurde, hat die Seite
    einen eigenen roten Satz (*Include gems* fehlt). Wäre er hier
    `NOTHING`, käme er nie so weit - und der Nutzer sähe gar nichts.
    """

    roh = json.loads(_sim_json())

    for item in roh["player"]["equipment"]["items"]:

        item.pop("gems", None)

        item.pop("reforging", None)

    text = json.dumps(roh)

    assert sim_run.recognize(text) == sim_run.TARGET

    assert parse_target(text).usable is False
