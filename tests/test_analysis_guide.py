"""
Der Wegweiser durch die vier Ansichten des Raid Centers.

Gemeldet wurde: "Viele wissen nicht, inwieweit man alles ueberhaupt
bedienen muss/kann und wo man was findet." Die Antwort darauf sind drei
Dinge, und alle drei werden hier festgehalten:

* die Texte selbst (`core/analysis_guide.py`, Qt-frei),
* die Quellenzeile, die sagt, woher die Zahlen kommen - und bei
  Beispieldaten warnt,
* und der Kopfblock, der in jeder Ansicht nennt, welchen Pull man vor
  sich hat.
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


def test_der_wegweiser_nennt_alle_vier_ansichten():
    """
    Und die beiden Modulnamen dazu: WeintTV und WeintAcademy stehen in
    den Einstellungen, im Addon und auf dem Discord. Wer sie dort liest,
    muss hier erfahren, welche Ansicht dahintersteckt - sonst hat der
    Umbau nur ein Vokabular gegen ein anderes getauscht.
    """

    text = GUIDE_INTRO + " ".join(
        f"{s.title} {s.purpose} {s.actions} {s.needs}"
        for s in GUIDE_SECTIONS
    )

    for ansicht in ("Live", "Analyse", "Lernen", "Quelle"):
        assert ansicht in text

    for modul in ("WeintTV", "WeintAcademy", "Archiv"):
        assert modul in text


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
# Der Kopfblock des Raid Centers
# --------------------------------------------------
#
# Er ist der Nachfolger von drei Dingen: dem Bossnamen in WeintTVs
# Kopfblock, dem Satz `encounter_meta()` in der Academy und dem Titel
# der Archiv-Seite. Drei Formulierungen desselben Sachverhalts, von
# denen keine Datum und Uhrzeit nannte - und die beim Umschalten kurz
# auseinanderliefen. Geprueft wird hier, dass die eine, die es noch
# gibt, den geladenen Pull benennt.


@pytest.fixture
def context_header():

    from gui.theme.theme_manager import init_theme

    _app()

    class _Config:

        def __init__(self):
            self.data = {}

        def save(self):
            pass

    config = _Config()

    init_theme(config)

    from core.academy_service import AcademyService

    class _Manager:

        def __init__(self):

            self.config = config

            self.logger = _Logger()

            self.raid_data = _service("warcraftlogs")

            self.academy = AcademyService(self)

    from gui.widgets.raid.context_header import RaidContextHeader

    return RaidContextHeader(_Manager())


def _load_a_pull(header):

    from dataclasses import replace

    from analyzer.providers.warcraftlogs_payload import (
        FightSummary,
        ReportSummary,
    )

    from core.raid_data_service import MODE_ARCHIVE

    service = header.service

    service.state = replace(
        service.state,
        mode=MODE_ARCHIVE,
        reports=(
            ReportSummary(
                code="aBcDeF12",
                title="Mittwochsraid",
                zone="Belagerung von Orgrimmar",
                start="2026-09-02T19:58:00+02:00",
            ),
        ),
        selected_report="aBcDeF12",
        fights=(
            FightSummary(
                fight_id=3,
                encounter_id=1607,
                encounter_name="Garrosh Höllschrei",
                difficulty="25 Heroisch",
                kill=False,
                boss_percentage=42.0,
                duration=391.0,
                start="2026-09-02T21:43:00+02:00",
                pull_number=17,
            ),
        ),
        selected_fight=3,
    )

    header.refresh()


def test_ohne_kampf_nennt_der_kopf_den_naechsten_schritt(context_header):
    """
    "Keine Daten" ist der Zustand, aus dem man nicht weiterkommt. Drei
    verschiedene Lagen (laedt, niemand kaempft, nichts gewaehlt)
    brauchen drei verschiedene Saetze.
    """

    assert context_header.boss.text() == "Kein laufender Kampf"

    assert "Quelle" in context_header.when.text()


def test_mit_geladenem_pull_steht_da_welcher(context_header):
    """
    Boss, Zone, Schwierigkeit, Pullnummer, Ausgang, Bossanteil, Dauer,
    Wochentag, Datum, Uhrzeit - alle in **einem** Block, der beim
    Wechsel der Ansicht stehen bleibt.
    """

    _load_a_pull(context_header)

    assert context_header.boss.text() == "Garrosh Höllschrei"

    assert "BELAGERUNG VON ORGRIMMAR" in context_header.instance.text()

    facts = context_header.facts.text()

    assert "Pull 17" in facts
    assert "Wipe" in facts
    assert "42 %" in facts
    assert "06:31" in facts

    #
    # Die Uhrzeit in der Zeitzone **dieses** Rechners: der Bot liefert
    # UTC-Offsets, und ein festverdrahtetes "21:43" würde nur in einer
    # Zeitzone gelten (siehe `day_label()` und `time_label`).
    #

    from datetime import datetime

    local = datetime.fromisoformat("2026-09-02T21:43:00+02:00").astimezone()

    when = context_header.when.text()

    assert "Mittwoch" in when
    assert local.strftime("%d.%m.") in when
    assert local.strftime("%H:%M") in when


def test_der_ausgang_steht_als_chip_daneben(context_header):

    _load_a_pull(context_header)

    assert context_header.outcome.label.text() == "WIPE"

    assert context_header.mode.label.text() == "ARCHIV"


def test_der_weg_zurueck_zum_raid_erscheint_nur_im_archiv(context_header):
    """
    Er lag bis 3.6.0 in einem Zweifachschalter auf drei Seiten, den man
    erst finden musste. Im Live-Modus waere er ein Knopf ohne Wirkung.
    """

    context_header.show()

    assert not context_header.live_button.isVisible()

    _load_a_pull(context_header)

    assert context_header.live_button.isVisible()

    context_header.hide()


def test_die_quelle_steht_als_chip_im_kopf(context_header):
    """
    Derselbe Zugang wie die Quellenzeile (`active_source()`) - der alte
    Fehler war ein zweiter Chip aus **einer anderen** Quelle (dem Label
    des Snapshots), der der Einstellung nach jedem Wechsel kurz
    widersprach.
    """

    assert "WARCRAFTLOGS" in context_header.source_chip.label.text()

    context_header.service.set_source(SOURCE_MOCK)

    assert "SIMULATION" in context_header.source_chip.label.text()


def test_eine_beispielquelle_wird_im_kopf_als_solche_benannt(context_header):
    """
    Eine Beispielquelle fuer den eigenen Abend zu halten war die
    haeufigste Verwechslung in diesem Bereich.
    """

    from gui.theme import tokens

    context_header.service.set_source(SOURCE_MOCK)

    assert context_header.source_chip._variant == "warn"

    assert tokens.STATE.get("warn")
