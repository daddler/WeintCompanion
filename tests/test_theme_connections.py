"""
Bausteine, die den Akzent lesen, muessen wieder freigegeben werden.

Der `ThemeManager` ist ein Singleton und lebt so lange wie das
Programm. Wer sich mit einer **Lambda** an eines seiner Signale
haengt - `theme().accent_changed.connect(lambda _n: self.update())` -
uebergibt ihm damit eine harte Referenz auf `self`: das Widget wird
nie wieder freigegeben. Neun Bausteine machten das, unter ihnen
`ToggleSwitch`, `ProgressRing`, `Sparkline` und `SegmentedControl` -
also die, die in Listen und Tabellen zu Dutzenden vorkommen.

Der zweite, haesslichere Teil: wird das C++-Objekt trotzdem zerstoert,
weil ein Elternteil abgebaut wird, feuert die Lambda in ein
geloeschtes Objekt. Qt meldet dann `RuntimeError: Internal C++ object
already deleted` - aus einem Slot heraus, wo eine Ausnahme kaum zu
verfolgen ist. Genau das brachte tests/test_appearance_section.py beim
ersten Lauf zum Scheitern.

Eine **gebundene Methode** loest beides: PySide6 haelt den Empfaenger
nur schwach und Qt trennt die Verbindung, wenn er zerstoert wird.

`SegmentedControl` hatte zusaetzlich einen Kreis in sich selbst:
`button.toggled.connect(lambda checked, b=button: ...)` - der Knopf ist
ein Kind des Steuerelements, die Lambda haelt das Steuerelement, und
weil sie in der C++-Verbindung liegt, sieht die Speicherbereinigung den
Kreis nicht.
"""

import gc
import os

import pytest

pytest.importorskip("PySide6")


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


def _builders():
    """
    Jeder Baustein, der sich an ein Signal des ThemeManagers haengt.
    """

    from gui.widgets.academy.history_card import LegendEntry
    from gui.widgets.academy.progression_chart import ProgressionChart
    from gui.widgets.academy.star_rating import StarRating
    from gui.widgets.bar_row import BarRow
    from gui.widgets.card import Card
    from gui.widgets.hero_banner import HeroButton
    from gui.widgets.progress_ring import ProgressRing
    from gui.widgets.roster_strip import RosterStrip
    from gui.widgets.segmented_control import SegmentedControl
    from gui.widgets.sparkline import Sparkline
    from gui.widgets.toggle_switch import ToggleSwitch
    from gui.widgets.tv.meter_bar import MeterBar

    return {
        "BarRow": BarRow,
        "Card": Card,
        "HeroButton": lambda: HeroButton("Speichern"),
        "LegendEntry": lambda: LegendEntry(accent=True),
        "MeterBar": MeterBar,
        "ProgressionChart": ProgressionChart,
        "ProgressRing": ProgressRing,
        "RosterStrip": RosterStrip,
        "SegmentedControl": lambda: SegmentedControl(
            [("A", "a"), ("B", "b")]
        ),
        "Sparkline": Sparkline,
        "StarRating": StarRating,
        "ToggleSwitch": lambda: ToggleSwitch(True),
    }


@pytest.fixture(autouse=True)
def _theme():

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())


def _pump(ms: int = 60):

    from PySide6.QtCore import QDeadlineTimer, QEventLoop

    app = _app()

    deadline = QDeadlineTimer(ms)

    while not deadline.hasExpired():
        app.processEvents(QEventLoop.AllEvents, 5)


#
# Die Namen hier statt aus `_builders()`: der Parameter wird beim
# Einsammeln der Tests ausgewertet, und dort sollen noch keine
# Qt-Module geladen werden.
#

WIDGET_NAMES = (
    "BarRow",
    "Card",
    "HeroButton",
    "LegendEntry",
    "MeterBar",
    "ProgressionChart",
    "ProgressRing",
    "RosterStrip",
    "SegmentedControl",
    "Sparkline",
    "StarRating",
    "ToggleSwitch",
)


def test_every_widget_that_reads_the_theme_is_covered():
    """
    Damit die Liste oben nicht hinter den Bausteinen zurueckbleibt.
    """

    assert set(WIDGET_NAMES) == set(_builders())


@pytest.mark.parametrize("name", WIDGET_NAMES)
def test_the_widget_is_released_again(name):
    """
    Nach dem Fallenlassen der letzten Python-Referenz muss das
    C++-Objekt zerstoert werden. `destroyed` ist der einzige
    verlaessliche Nachweis: `QObject.receivers()` wird in PySide6 auch
    dann nicht heruntergezaehlt, wenn die Verbindung wirklich weg ist.
    """

    build = _builders()[name]

    widget = build()

    destroyed = {"value": False}

    #
    # Diese Lambda ist unbedenklich: sie haelt `destroyed`, nicht das
    # Widget, und haengt am Widget selbst statt am Singleton.
    #

    widget.destroyed.connect(
        lambda *_: destroyed.__setitem__("value", True)
    )

    del widget

    gc.collect()

    _pump(80)

    assert destroyed["value"], (
        f"{name} wird nicht freigegeben - etwas haelt eine harte "
        f"Referenz darauf, mutmasslich eine Lambda an einem Signal des "
        f"ThemeManagers."
    )


def test_no_lambda_is_connected_to_a_theme_signal():
    """
    Die Regel unmittelbar, statt nur ihre Folge.

    Ein Textvergleich, weil er den Fehler dort zeigt, wo er gemacht
    wird - der Freigabetest oben schlaegt erst an, wenn der Baustein
    schon in dieser Liste steht.
    """

    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "gui"

    offenders = []

    for path in sorted(root.rglob("*.py")):

        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):

            stripped = line.strip()

            if not stripped.startswith("theme()."):
                continue

            if ".connect(" not in stripped:
                continue

            if "lambda" in stripped:

                offenders.append(
                    f"{path.relative_to(root.parent)}:{number}"
                )

    assert not offenders, (
        "Lambda an einem Signal des ThemeManagers - der Empfaenger "
        "wird dadurch nie freigegeben. Gebundene Methode benutzen:\n  "
        + "\n  ".join(offenders)
    )
