"""
Der Wegweiser durch WeintTV, Academy und Archiv.

Gemeldet wurde: "Viele wissen nicht, inwieweit man alles ueberhaupt
bedienen muss/kann und wo man was findet." Die Antwort darauf sind drei
Dinge, und alle drei werden hier festgehalten:

* die Texte selbst (`core/analysis_guide.py`, Qt-frei),
* die Quellenzeile, die auf allen drei Seiten sagt, woher die Zahlen
  kommen - und bei Beispieldaten warnt,
* und die Archiv-Seite, die den Browser jetzt selbst traegt statt auf
  WeintTV zu verweisen.
"""

import ast
import os
import pathlib

import pytest

pytest.importorskip("PySide6")

from core.analysis_guide import GUIDE_INTRO, GUIDE_SECTIONS
from core.raid_data_service import (
    SOURCE_LABELS,
    SOURCE_MOCK,
    SOURCE_SHORT,
    SOURCE_WARCRAFTLOGS,
    is_demo_source,
)


ROOT = pathlib.Path(__file__).resolve().parent.parent


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    return QApplication.instance() or QApplication([])


# --------------------------------------------------
# Die Texte
# --------------------------------------------------


def test_der_wegweiser_nennt_alle_drei_bereiche():

    text = GUIDE_INTRO + " ".join(
        f"{s.title} {s.purpose} {s.actions} {s.needs}"
        for s in GUIDE_SECTIONS
    )

    for bereich in ("WeintTV", "Academy", "Archiv"):
        assert bereich in text


def test_jeder_abschnitt_beantwortet_alle_drei_fragen():
    """
    Einer, der einmal eine Voraussetzung nennt und beim naechsten
    nicht, liest sich wie eine Ausnahme, wo keine ist.
    """

    for section in GUIDE_SECTIONS:

        assert section.purpose.strip()
        assert section.actions.strip()
        assert section.needs.strip()


def test_jede_quelle_hat_eine_beschriftung_und_einen_satz():
    """
    Die Quellenzeile liest beide Tabellen. Eine Quelle, die nur in der
    einen steht, erschiene dort halb beschriftet.
    """

    for source in (SOURCE_MOCK, SOURCE_WARCRAFTLOGS):

        assert SOURCE_LABELS.get(source)
        assert SOURCE_SHORT.get(source)


def test_die_simulation_ist_als_beispielquelle_erkennbar():

    assert is_demo_source(SOURCE_MOCK)

    assert not is_demo_source(SOURCE_WARCRAFTLOGS)

    assert not is_demo_source("")


# --------------------------------------------------
# Typo-Token
# --------------------------------------------------


def test_jedes_benutzte_typo_token_gibt_es_wirklich():
    """
    `font()` faellt bei einem unbekannten Namen stumm auf `body`
    zurueck. Genau das ist einmal passiert: `font("caption")` gibt es
    nicht, und die betroffenen Zeilen standen jahrelang in Fliesstext-
    groesse statt klein, ohne dass irgendwo etwas fehlschlug.
    """

    from gui.theme import tokens

    benutzt = set()

    for path in (ROOT / "gui").rglob("*.py"):

        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Name) or node.func.id != "font":
                continue

            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue

            if isinstance(node.args[0].value, str):
                benutzt.add(node.args[0].value)

    unbekannt = sorted(benutzt - set(tokens.TYPE))

    assert not unbekannt, f"Unbekannte Typo-Token: {unbekannt}"


# --------------------------------------------------
# Die Quellenzeile
# --------------------------------------------------


class _Logger:

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def _service(source="mock"):

    from PySide6.QtCore import QObject, Signal

    from core.raid_data_service import ArchiveState, MODE_LIVE, ReplayState

    class _Service(QObject):

        snapshotChanged = Signal(object)
        archiveChanged = Signal()
        replayChanged = Signal()
        sourceChanged = Signal()

        def __init__(self):

            super().__init__()

            self.source = source

            self.state = ArchiveState(mode=MODE_LIVE)

        def configured_source(self):
            return self.source

        def active_source(self):
            return self.source

        def set_source(self, value):

            if value == self.source:
                return False

            self.source = value

            self.sourceChanged.emit()

            return True

        def archive_state(self):
            return self.state

        def replay_state(self):
            return ReplayState()

        def replay_available(self):
            return False

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    return _Service()


@pytest.fixture
def strip_factory():

    from gui.theme.theme_manager import init_theme

    _app()

    class _Config:

        def __init__(self):
            self.data = {}

        def save(self):
            pass

    init_theme(_Config())

    from gui.widgets.tv.source_strip import SourceStrip

    def build(source="mock"):

        service = _service(source)

        return SourceStrip(service), service

    return build


def test_beispieldaten_werden_als_solche_benannt(strip_factory):
    """
    Die haeufigste Verwechslung in diesem Bereich: erfundene Zahlen
    fuer den eigenen Raidabend zu halten.
    """

    from gui.theme import tokens

    strip, _ = strip_factory("mock")

    assert "Simulation" in strip.headline.text()

    assert "kein echter Raid" in strip.detail.text()

    assert tokens.STATE["warn"] in strip.headline.styleSheet()


def test_der_livelog_wird_nicht_als_warnung_gezeigt(strip_factory):

    from gui.theme import tokens

    strip, _ = strip_factory("warcraftlogs")

    assert "WarcraftLogs" in strip.headline.text()

    assert tokens.STATE["warn"] not in strip.headline.styleSheet()


def test_die_zeile_schaltet_die_quelle_wirklich_um(strip_factory):

    strip, service = strip_factory("mock")

    index = next(
        i for i in range(strip.picker.count())
        if strip.picker.itemData(i) == "warcraftlogs"
    )

    strip.picker.setCurrentIndex(index)

    assert service.source == "warcraftlogs"

    #
    # Und die Zeile zieht nach - ueber `sourceChanged`, denselben Weg,
    # den auch ein Wechsel in den Einstellungen nimmt.
    #

    assert "WarcraftLogs" in strip.headline.text()


# --------------------------------------------------
# Die Archiv-Seite
# --------------------------------------------------


@pytest.fixture
def archive_page():

    from gui.theme.theme_manager import init_theme

    _app()

    class _Config:

        def __init__(self):
            self.data = {}

        def save(self):
            pass

    config = _Config()

    init_theme(config)

    class _Manager:

        def __init__(self):

            self.config = config

            self.logger = _Logger()

            self.raid_data = _service("warcraftlogs")

    from gui.pages.archive import ArchivePage

    return ArchivePage(_Manager())


def test_das_archiv_traegt_die_auswahl_selbst(archive_page):
    """
    Bis 3.5.0 bestand die Seite aus einem Waehler und dem Satz "die
    Zahlen erscheinen in WeintTV" - ein Bereich, in dem es nichts zu
    finden gab, obwohl man genau dort sucht.
    """

    assert archive_page.browser is not None

    assert archive_page.browser.days_body is not None

    assert archive_page.browser.fights_body is not None


def test_kein_zweiter_weg_zur_selben_liste(archive_page):
    """
    Der Knopf "Log waehlen …" legte sonst ein Fenster ueber die Liste,
    die schon dasteht.
    """

    assert not archive_page.picker.browse_button.isVisibleTo(
        archive_page.picker
    )


def test_ohne_geladenen_pull_keine_knoepfe_ins_leere(archive_page):

    assert not archive_page.actions.isVisibleTo(archive_page)


def test_mit_geladenem_pull_steht_da_welcher(archive_page):

    from dataclasses import replace

    from analyzer.providers.warcraftlogs_payload import (
        FightSummary,
        ReportSummary,
    )

    service = archive_page.service

    service.state = replace(
        service.state,
        reports=(
            ReportSummary(
                code="aBcDeF12",
                title="Mittwochsraid",
                start="2026-09-02T19:58:00",
            ),
        ),
        selected_report="aBcDeF12",
        fights=(
            FightSummary(
                fight_id=3,
                encounter_id=1607,
                encounter_name="Garrosh Höllschrei",
                kill=True,
                pull_number=7,
            ),
        ),
        selected_fight=3,
    )

    archive_page._on_archive_changed()

    assert archive_page.actions.isVisibleTo(archive_page)

    #
    # Der Satz daneben wiederholt den Titel nicht, sondern nennt das,
    # was man von hier aus nicht sieht: die Auswahl gilt auch in
    # WeintTV und der Academy.
    #

    assert "WeintTV" in archive_page.loaded_label.text()

    #
    # Und im Kopf steht der Kampf statt der Aufforderung, einen zu
    # waehlen. Bis 3.5.0 las die Seite dort ein Feld, das es an
    # `ArchiveState` nie gab - der Titel aenderte sich nie.
    #

    assert "Garrosh" in archive_page.header.title.text()
