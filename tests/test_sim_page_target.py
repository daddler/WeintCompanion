"""
Die Simmen-Seite - offscreen aufgebaut.

**Warum das eine eigene Datei mit Qt ist.** Alles Rechnende steht in
`core/target_gear.py` und `core/sim_run.py` und wird dort ohne Fenster
geprüft. Was hier zählt, ist die Verdrahtung: dass die Karten überhaupt
entstehen, dass **dasselbe Eingabefeld** beide Textsorten
auseinanderhält, dass beide sich im **selben Lauf sammeln** statt sich
zu ersetzen, und dass die Seite die Frage „lief da überhaupt ein
Optimierungslauf?" tatsächlich stellt. Ein Tippfehler im Kartenaufbau
fiele sonst erst dem Nutzer auf.

`refresh()` darf dabei nur zeichnen (siehe
`docs/architecture/navigation.md`) - deshalb wird sie hier mehrfach
gerufen, und die Seite muss das aushalten.
"""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")


DATA = Path(__file__).parent / "data" / "wowsims_mop_output.json"


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Logger:

    def __init__(self):
        self.lines = []

    def info(self, text=""):
        self.lines.append(text)

    def warning(self, text=""):
        self.lines.append(text)

    def error(self, text=""):
        self.lines.append(text)

    def success(self, text=""):
        self.lines.append(text)


class _State:

    wow_path = None

    #
    # Ab WeintCodex 3.1.2.0 gehen beide Umschläge zusammen in ein Feld;
    # davor verschluckt das Addon den zweiten still. Der Testlauf steht
    # deshalb bewusst auf einer Fassung, die es kann - der Gegenfall
    # bekommt seinen eigenen Test.
    #

    addon_found = True

    addon_version = "3.1.2.0"


class _Sync:

    def __init__(self):
        self.published = 0

    def publish_now(self):
        self.published += 1


class _Manager:

    def __init__(self, store, target_store):
        self.state = _State()
        self.logger = _Logger()
        self.characters = None
        self.stat_weights = store
        self.stat_weights_sync = _Sync()
        self.target_gear = target_store
        self.target_gear_sync = _Sync()


@pytest.fixture
def page(tmp_path):

    _app()

    from core.config import Config
    from core.stat_weights_store import StatWeightsStore
    from core.target_gear_store import TargetGearStore
    from gui.theme.theme_manager import init_theme

    init_theme(Config())

    from gui.pages.sim import SimPage

    manager = _Manager(None, None)

    manager.stat_weights = StatWeightsStore(manager, path=tmp_path / "w.json")

    manager.target_gear = TargetGearStore(manager, path=tmp_path / "t.json")

    seite = SimPage(manager)

    yield seite

    seite.deleteLater()


def _sim_json() -> str:

    return DATA.read_text(encoding="utf-8")


def test_the_page_builds_with_all_four_steps(page):

    assert page.apply_button.isEnabled() is False

    assert page.transfer.toPlainText() == ""

    assert "liegt noch nichts bereit" in page.stored.text()


def test_the_same_field_tells_the_two_kinds_apart(page):
    """
    In Schritt 3 gehört hinein, was aus dem Sim kommt. Welche der
    beiden Sorten es ist, entscheidet die Seite - nicht der Nutzer
    durch die Wahl eines Feldes.
    """

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nAgility 1.0")

    page._read()

    assert page._run.target is None
    assert page._run.weights
    assert page.apply_button.isEnabled() is True

    page._clear_input()

    page.input.setPlainText(_sim_json())

    page._read()

    assert page._run.target is not None
    assert page._run.weights == {}
    assert page.apply_button.isEnabled() is True
    assert "Sockelsteine" in page.notes.text()


def test_the_page_says_when_nothing_changed(page):
    """
    Der Verdachtsfall: importiert und sofort wieder exportiert. Ohne
    diesen Satz sähe der Ausgangszustand aus wie ein
    Optimierungsergebnis - und im Spiel brächte er jede Empfehlung zum
    Schweigen.
    """

    from core.wowsims_export import parse_export

    payload = json.loads(_sim_json())

    page._export = parse_export(
        json.dumps(
            {
                "class": "deathknight",
                "spec": "blood",
                "level": 90,
                "name": "Aldrin",
                "realm": "Everlook",
                "gear": {"items": payload["player"]["equipment"]["items"]},
            }
        )
    )

    page.input.setPlainText(_sim_json())

    page._read()

    assert "kein Optimierungslauf" in page.notes.text()


def test_the_page_names_what_would_change(page):

    from core.wowsims_export import parse_export

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    items[0] = dict(items[0], gems=[76895, 76653], reforging=140)

    page._export = parse_export(
        json.dumps(
            {
                "class": "deathknight",
                "spec": "blood",
                "level": 90,
                "name": "Aldrin",
                "realm": "Everlook",
                "gear": {"items": items},
            }
        )
    )

    page.input.setPlainText(_sim_json())

    page._read()

    text = page.notes.text()

    assert "1 Teilen" in text
    assert "Kopf" in text

    # Und die nachzählbaren Zahlen daneben: ein Sockel, eine
    # Umschmiedung. Eine Zahl ist nachprüfbar, ein "erfolgreich" nicht.
    assert "Ausrüstungsplätze geprüft" in text
    assert "1 Sockeländerungen" in text
    assert "1 Umschmiedungen" in text


def test_applying_stores_delivers_and_offers_the_string(page):

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    entry = page.target_gear_store_entry()

    assert entry is not None
    assert entry.spec_key == "DEATHKNIGHT_BLOOD"

    assert page.manager.target_gear_sync.published == 1

    assert page.transfer.toPlainText().startswith("WCIMPORT:TG:")

    assert "Optimierte Ausrüstung ✓" in page.stored.text()

    # Das Eingabefeld wird geleert, der Knopf ist wieder gesperrt.
    assert page.input.toPlainText() == ""
    assert page.apply_button.isEnabled() is False


def test_removing_delivers_too(page):
    """
    Im Spiel verschwindet der Zielzustand dadurch, dass er in der
    nächsten Zustellung fehlt.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    page._remove()

    assert page.manager.target_gear_sync.published == 2

    assert page.target_gear_store_entry() is None

    assert "liegt noch nichts bereit" in page.stored.text()


def test_refresh_only_draws(page):
    """
    Mehrfaches Zeichnen darf nichts verändern - `refresh()` läuft bei
    jeder `state_changed`.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    vorher = page.result.text()

    page.refresh()
    page.refresh()

    assert page.input.toPlainText() != ""
    assert page.result.text() == vorher
    assert page._run.target is not None


# --------------------------------------------------
# Die Vereinfachungen von 3.1.1
# --------------------------------------------------


def test_pasting_reads_by_itself(page):
    """
    *Einlesen* war ein Klick ohne eigene Entscheidung: es gibt keinen
    Grund, einen eingefügten Text nicht zu lesen. Geprüft wird die
    Verdrahtung (Feld → Zeitgeber) und das Ergebnis danach - ohne den
    Knopf je zu drücken.
    """

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nAgility 1.0")

    assert page._read_timer.isActive() is True

    page._read_quiet()

    assert page._run.weights
    assert page.apply_button.isEnabled() is True


def test_reading_along_stays_quiet_about_errors(page):
    """
    Wer mitten im Tippen ist, hat noch nichts falsch gemacht. Eine rote
    Zeile nach jedem Zeichen erzieht nur dazu, rote Zeilen zu
    übersehen - also sagt das Lesen nebenher nichts, und der Knopf sagt
    es.
    """

    page.input.setPlainText("völliger Unsinn ohne jede Zahl")

    page._read_quiet()

    assert page.problem.text() == ""
    assert page.apply_button.isEnabled() is False

    page._read()

    assert page.problem.text() != ""


def test_an_emptied_field_is_not_an_error(page):
    """
    Ein leeres Feld ist der Ausgangszustand, kein Fehler - auch dann,
    wenn der Nutzer den Text gerade selbst herausgelöscht hat.
    """

    page.input.setPlainText(_sim_json())

    page._read()

    assert page._run.target is not None

    page.input.setPlainText("")

    page._read_quiet()

    assert page._run.target is None
    assert page.result.text() == ""
    assert page.problem.text() == ""


def test_clearing_the_field_starts_no_read(page):
    """
    `_clear_input()` schreibt selbst ins Feld. Das ist keine Eingabe des
    Nutzers und darf den Zeitgeber nicht auslösen - sonst liefe nach
    jedem Übernehmen ein Lesevorgang über ein leeres Feld.
    """

    page.input.setPlainText("Hit 1.77")

    page._clear_input()

    assert page._read_timer.isActive() is False


def test_applying_leaves_the_string_in_the_clipboard(page):
    """
    *Übernehmen* und *String kopieren* waren zwei Klicks für eine
    Absicht. Der Zeitpunkt des Übernehmens ist auch der einzige, an dem
    die Frage "welcher der beiden Strings ist meiner" gar nicht erst
    entsteht.
    """

    from PySide6.QtGui import QGuiApplication

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nAgility 1.0")

    page._read()

    page._apply()

    clipboard = QGuiApplication.clipboard()

    assert clipboard is not None
    assert clipboard.text().startswith("WCIMPORT:SW:")
    assert clipboard.text() == page.transfer.toPlainText()

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    #
    # Und jetzt liegt BEIDES in der Zwischenablage - genau eine Zeile je
    # Umschlag. Das ist der ganze Punkt von Schritt 4: ein Ausgang.
    #

    zeilen = clipboard.text().splitlines()

    assert len(zeilen) == 2
    assert zeilen[0].startswith("WCIMPORT:SW:")
    assert zeilen[1].startswith("WCIMPORT:TG:")
    assert clipboard.text() == page.transfer.toPlainText()


def test_the_gear_wheel_hint_is_on_the_page(page):
    """
    Ohne *Include gems* hinter dem Zahnrad optimiert der Sim nur die
    Umschmiedungen. Das Ergebnis sieht danach vollständig aus und ist
    es nicht - der Satz muss deshalb dort stehen, wo man in den Sim
    geht.
    """

    text = page.source_hint.text()

    assert "Zahnrad" in text
    assert "Include gems" in text


# --------------------------------------------------
# Schritt 4: der eine Ausgang (3.2.0)
# --------------------------------------------------


def _fill_both(page):
    """
    Beide Auskünfte eines Sim-Laufs übernehmen - Gewichtung und
    Zielausrüstung, in der Reihenfolge, in der man sie im Sim holt.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    page._apply()

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()


def test_both_envelopes_share_one_field(page):
    """
    Aus einem Sim-Lauf kommen zwei Auskünfte. Zwei Felder mit je einem
    Knopf waren zwei Ausgänge für einen Vorgang - und der zweite blieb
    liegen.
    """

    _fill_both(page)

    zeilen = page.transfer.toPlainText().splitlines()

    assert len(zeilen) == 2
    assert zeilen[0].startswith("WCIMPORT:SW:")
    assert zeilen[1].startswith("WCIMPORT:TG:")

    assert page.copy_button.isEnabled() is True
    assert page.remove_button.isEnabled() is True

    assert page.delivery_warn.text() == ""


def test_an_old_addon_gets_only_one_line(page):
    """
    WeintCodex vor 3.1.2.0 liest nur den ersten Umschlag und verschluckt
    den zweiten **stillschweigend** - eine Erfolgsmeldung, in der die
    Zielausrüstung fehlt. Diese Sorte Fehler ist die schlimmste, also
    kommt beides dort gar nicht erst ins Feld.
    """

    page.manager.state.addon_version = "3.1.1.0"

    _fill_both(page)

    zeilen = page.transfer.toPlainText().splitlines()

    assert len(zeilen) == 1
    assert zeilen[0].startswith("WCIMPORT:SW:")

    # Und der Grund steht dabei, samt Ausweg - sonst sähe es aus, als
    # wäre die Zielausrüstung verloren. Sie ist es nicht.
    warnung = page.delivery_warn.text()

    assert "3.1.2.0" in warnung
    assert "/reload" in warnung


def test_an_unknown_addon_is_treated_as_old(page):
    """
    Nicht feststellbar ist nicht dasselbe wie „kann es" - und die
    vorsichtige Antwort kostet hier nur einen zweiten Einfügevorgang,
    während die unvorsichtige Daten verschluckt.
    """

    page.manager.state.addon_found = False

    _fill_both(page)

    assert len(page.transfer.toPlainText().splitlines()) == 1


def test_nothing_stored_says_so_without_a_field(page):

    assert page.transfer.toPlainText() == ""
    assert page.copy_button.isEnabled() is False
    assert page.delivery_warn.text() == ""
    assert "Sobald oben etwas übernommen ist" in page.delivery_hint.text()


# --------------------------------------------------
# Ein Lauf, ein Knopf (3.3.0)
# --------------------------------------------------


def _with_export(page, items=None):
    """
    Der Seite eine gemeldete Ausrüstung unterschieben - ohne sie kann
    sie die Frage „wurde überhaupt optimiert" gar nicht stellen.
    """

    from core.wowsims_export import parse_export

    payload = json.loads(_sim_json())

    page._export = parse_export(
        json.dumps(
            {
                "class": "deathknight",
                "spec": "blood",
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

    page._rebuild_run()

    return page


def test_the_second_paste_does_not_erase_the_first(page):
    """
    DER KERN DER UMSTELLUNG. Bis 3.2.0 stand die Gewichtung in einem
    Merker und die Zielausrüstung in einem zweiten; das zweite Einfügen
    hat den ersten Befund nicht ergänzt, sondern daneben gestellt - und
    er brauchte einen eigenen Knopf.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    assert page._run.have_weights is True

    #
    # Und jetzt das Zweite in dasselbe Feld - so, wie man es tut:
    # markieren und einfügen, nicht erst leeren.
    #

    page.input.setPlainText(_sim_json())

    page._read()

    assert page._run.have_weights is True
    assert page._run.have_target is True


def test_emptying_the_field_forgets_the_run_visibly(page):
    """
    *Feld leeren* heisst „nimm zurück, was ich eingefügt habe" - der
    Befund darüber verschwindet mit. Das ist kein stiller Verlust: die
    Häkchenzeile springt sichtbar auf „Gewichtung fehlt", und was
    bereits übernommen wurde, steht in Schritt 4 unberührt da.
    """

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    assert page._run.have_weights is True

    page._clear_input()

    assert page._run.have_weights is False

    assert page.result.text() == ""

    assert page.apply_button.isEnabled() is False


def test_one_click_stores_both(page):
    """
    Ein Vorgang, ein Knopf. Zwei Übernehmen-Knöpfe hiessen: wer den
    zweiten vergisst, bekommt im Spiel eine halbe Auskunft - und das
    sieht man einer Empfehlung nicht an.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    assert page.weights_store_entry() is not None
    assert page.target_gear_store_entry() is not None

    assert page.manager.stat_weights_sync.published == 1
    assert page.manager.target_gear_sync.published == 1

    zeilen = page.transfer.toPlainText().splitlines()

    assert len(zeilen) == 2


def test_both_carry_the_same_run_id(page):
    """
    Erst die gemeinsame Kennung macht aus zwei Auskünften einen
    Vorgang. Ohne gemeldete Ausrüstung gibt es keine - dann behauptet
    die Seite auch nichts über Zusammengehörigkeit.
    """

    _with_export(page)

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText("Hit 1.77\nStrength 1.0")

    page._read()

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    kennung = page.weights_store_entry().run_id

    assert kennung.startswith("SIM-")

    assert page.target_gear_store_entry().run_id == kennung

    # Und sie steht auf der Seite, damit eine Rückfrage sie nennen kann.
    assert kennung in page.run_line.text()


def test_a_run_without_reported_gear_has_no_id(page):

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply()

    assert page.target_gear_store_entry().run_id == ""

    assert page.run_line.text() == ""


def test_two_runs_side_by_side_are_warned_about(page):
    """
    Eine Gewichtung aus dem Lauf von gestern neben einem Zielzustand von
    heute: beide für sich in Ordnung, zusammen eine Aussage über zwei
    verschiedene Ausrüstungen. Im Spiel sieht man das nicht.
    """

    from core.stat_weights import WeightSet
    from core.target_gear import TargetSet, parse_target

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.store.put(
        WeightSet(
            spec_key="DEATHKNIGHT_BLOOD",
            weights={"strength": 100},
            run_id="SIM-20260908-AAAA",
        )
    )

    page.target_store.put(
        TargetSet(
            gear=parse_target(_sim_json()),
            spec_key="DEATHKNIGHT_BLOOD",
            run_id="SIM-20260909-BBBB",
        )
    )

    page.refresh()

    warnung = page.delivery_warn.text()

    assert "SIM-20260908-AAAA" in warnung
    assert "SIM-20260909-BBBB" in warnung


def test_discarding_takes_both(page):
    """
    Zwei Entfernen-Knöpfe waren die Möglichkeit, eine Hälfte
    stehenzulassen - und genau diese Hälfte ergibt später die Mischung
    aus zwei Läufen.
    """

    _fill_both(page)

    page._remove()

    assert page.weights_store_entry() is None
    assert page.target_gear_store_entry() is None

    assert page.transfer.toPlainText() == ""


def test_a_foreign_class_changes_the_button_rather_than_locking_it(page):
    """
    Vielleicht simmt jemand für seinen Zweitcharakter. Ein toter Knopf
    beantwortet nicht, warum er tot ist.
    """

    page.spec_select.select_value("MAGE_FIRE")

    page.input.setPlainText(
        '{"player":{"class":"ClassDeathKnight"},'
        '"statWeightsResult":{"dps":{"weights":{"stats":'
        '[0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}}}}'
    )

    page._read()

    if page._run.have_weights:

        assert page.apply_button.isEnabled() is True

        assert page.apply_button.text() == "Trotzdem übernehmen"


def test_a_read_error_does_not_lose_what_was_read_before(page):
    """
    Wer nach der Gewichtung Unsinn einfügt, hat die Gewichtung nicht
    zurückgenommen. Bis 3.2.0 wurde sie hier mit gelöscht, und das war
    von aussen ein stilles Verschwinden.
    """

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    assert page._run.have_weights is True

    page.input.setPlainText("völliger Unsinn ohne jede Zahl")

    page._read()

    assert page.problem.text() != ""

    assert page._run.have_weights is True


def test_the_stored_half_completes_the_run(page):
    """
    Wer die Gewichtung übernimmt und danach die Zielausrüstung einfügt,
    hat einen **vollständigen** Lauf — die erste Hälfte liegt nur schon
    im Speicher statt im Feld.

    Ohne die Zusammenführung stünde dort „Gewichtung fehlt", obwohl sie
    bereitliegt, und der Satz darunter schickte den Nutzer in den Sim
    für etwas, das er längst geholt hat.
    """

    #
    # Eine angelegte Ausrüstung, die sich vom Sim-Ergebnis
    # unterscheidet - sonst wäre der Befund „entspricht deiner
    # angelegten Ausrüstung", und der beantwortet eine andere Frage.
    #

    payload = json.loads(_sim_json())

    items = [dict(entry) for entry in payload["player"]["equipment"]["items"]]

    items[0] = dict(items[0], gems=[76895, 76653], reforging=140)

    _with_export(page, items)

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page._rebuild_run()

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nStrength 1.0")

    page._read()

    page._apply()

    assert page.weights_store_entry() is not None
    assert page.target_gear_store_entry() is None

    # Zweite Runde, derselbe Lauf.
    page.input.setPlainText(_sim_json())

    page._read()

    assert "vollständig" in page.result.text()

    assert "Gewichtung ✓" in page.parts.text()

    assert page.hint.text() == ""

    page._apply()

    assert (
        page.weights_store_entry().run_id
        == page.target_gear_store_entry().run_id
    )


def test_a_stored_half_from_another_run_does_not_complete_it(page):
    """
    Ein Eintrag aus einem anderen Lauf ist keine Hälfte dieses Laufs —
    er ist genau die Mischung, vor der Schritt 4 warnt.
    """

    from core.stat_weights import WeightSet

    _with_export(page)

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page._rebuild_run()

    page.store.put(
        WeightSet(
            spec_key="DEATHKNIGHT_BLOOD",
            weights={"strength": 100},
            run_id="SIM-20260101-ZZZZ",
        )
    )

    page.input.setPlainText(_sim_json())

    page._read()

    assert "Gewichtung fehlt" in page.parts.text()


def test_an_empty_slot_is_not_a_piece_of_gear(page):
    """
    Ein leerer Platz überlebt die Ablage ohnehin nicht. Frisch
    übernommen stünde hier sonst eine andere Zahl als nach dem
    nächsten Start der App.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    entry = page._run.target

    page._apply()

    assert f"{entry.item_count} Teile" in page.stored.text()
