"""
Die Simmen-Seite mit der Zielausrüstung - offscreen aufgebaut.

**Warum das eine eigene Datei mit Qt ist.** Alles Rechnende steht in
`core/target_gear.py` und wird dort ohne Fenster geprüft. Was hier
zählt, ist die Verdrahtung: dass die Karte überhaupt entsteht, dass
**dasselbe Eingabefeld** beide Textsorten auseinanderhält, und dass
die Seite die Frage „lief da überhaupt ein Optimierungslauf?"
tatsächlich stellt. Ein Tippfehler im Kartenaufbau fiele sonst erst
dem Nutzer auf.

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


def test_the_page_builds_with_the_target_card(page):

    assert page.target_apply.isEnabled() is False

    assert page.target_transfer.text() == ""

    assert "noch keine Zielausrüstung" in page.target_stored.text()


def test_the_same_field_tells_the_two_kinds_apart(page):
    """
    In Schritt 2 gehört hinein, was aus dem Sim kommt. Welche der
    beiden Sorten es ist, entscheidet die Seite - nicht der Nutzer
    durch die Wahl eines Feldes.
    """

    page.input.setPlainText("Hit 1.77\nCrit 0.89\nAgility 1.0")

    page._read()

    assert page._target is None
    assert page._weights
    assert page.apply_button.isEnabled() is True
    assert page.target_apply.isEnabled() is False

    page._clear_input()

    page.input.setPlainText(_sim_json())

    page._read()

    assert page._target is not None
    assert page.target_apply.isEnabled() is True
    assert "Sockelsteine" in page.target_result.text()


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

    assert "kein Optimierungslauf" in page.target_notes.text()


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

    text = page.target_notes.text()

    assert "1 Teilen" in text
    assert "Kopf" in text


def test_applying_stores_delivers_and_offers_the_string(page):

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply_target()

    entry = page.target_gear_store_entry()

    assert entry is not None
    assert entry.spec_key == "DEATHKNIGHT_BLOOD"

    assert page.manager.target_gear_sync.published == 1

    assert page.target_transfer.text().startswith("WCIMPORT:TG:")

    assert "Abgelegt:" in page.target_stored.text()

    # Das Eingabefeld wird geleert, der Knopf ist wieder gesperrt.
    assert page.input.toPlainText() == ""
    assert page.target_apply.isEnabled() is False


def test_removing_delivers_too(page):
    """
    Im Spiel verschwindet der Zielzustand dadurch, dass er in der
    nächsten Zustellung fehlt.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply_target()

    page._remove_target()

    assert page.manager.target_gear_sync.published == 2

    assert page.target_gear_store_entry() is None

    assert "noch keine Zielausrüstung" in page.target_stored.text()


def test_refresh_only_draws(page):
    """
    Mehrfaches Zeichnen darf nichts verändern - `refresh()` läuft bei
    jeder `state_changed`.
    """

    page.spec_select.select_value("DEATHKNIGHT_BLOOD")

    page.input.setPlainText(_sim_json())

    page._read()

    vorher = page.target_result.text()

    page.refresh()
    page.refresh()

    assert page.input.toPlainText() != ""
    assert page.target_result.text() == vorher
    assert page._target is not None


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

    assert page._weights
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

    assert page._target is not None

    page.input.setPlainText("")

    page._read_quiet()

    assert page._target is None
    assert page.target_problem.text() == ""
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
    assert clipboard.text() == page.transfer.text()

    page.input.setPlainText(_sim_json())

    page._read()

    page._apply_target()

    assert clipboard.text().startswith("WCIMPORT:TG:")
    assert clipboard.text() == page.target_transfer.text()


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
