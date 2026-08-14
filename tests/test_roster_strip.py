"""
Der Aufstellungsstreifen der Übersicht.

Er baut Widgets und braucht deshalb Qt - aus demselben Grund wie
`test_accent_follows.py`: der Fehler, um den es hier geht, ist
ausschließlich im Bild zu sehen. Zwei Tanks sind 22 px breit, die
Rubrik "TANKS" mehr als das Doppelte davon, und ohne Untergrenze
schob sich die Beschriftung der nächsten Reihe in die vorige -
angezeigt wurde "TANKSHEILER", ohne dass irgendetwas fehlschlug.
"""

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


@pytest.fixture(autouse=True)
def _theme():

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())


def _strip(width: int = 900):

    from gui.widgets.roster_strip import RosterStrip, SlotGroup

    strip = RosterStrip()

    strip.resize(width, strip.height())

    strip.setGroups([
        SlotGroup("TANKS", ["Warrior", "Druid"], 0),
        SlotGroup("HEILER", ["Priest"] * 5, 1),
        SlotGroup("SCHADEN", ["Mage"] * 14, 3),
    ])

    return strip


def _measure(strip):

    from PySide6.QtGui import QFontMetricsF

    from gui.theme.fonts import font

    metrics = QFontMetricsF(font("micro"))

    slot, gap, group_gap, widths = strip._layout(metrics)

    return metrics, slot, gap, group_gap, widths


def test_a_row_is_never_narrower_than_its_own_caption():

    strip = _strip()

    metrics, _slot, _gap, _group_gap, widths = _measure(strip)

    for group, width in zip(strip.groups(), widths):

        assert width >= metrics.horizontalAdvance(group.label), (
            f"Die Reihe {group.label!r} ist schmaler als ihre "
            f"eigene Rubrik - die nächste Beschriftung überschreibt "
            f"sie."
        )


def test_the_strip_shrinks_instead_of_overflowing():
    """
    Unter 980 px stehen die beiden Karten der Übersicht
    untereinander, und die Aufstellung bekommt deutlich weniger
    Breite. Der Streifen ist ein Balken, kein Text: er wird schmaler,
    er bricht nicht um.
    """

    from gui.widgets.roster_strip import MIN_SLOT_WIDTH, SLOT_WIDTH

    wide = _measure(_strip(900))[1]

    narrow = _measure(_strip(320))[1]

    assert wide == SLOT_WIDTH

    assert MIN_SLOT_WIDTH <= narrow < wide


def test_rows_never_overlap_at_any_width():
    """
    Die Gegenprobe zur Untergrenze: gerechnet wird der linke Rand
    jeder Reihe, so wie `paintEvent` ihn setzt.
    """

    for width in (1200, 900, 640, 420, 300, 200):

        strip = _strip(width)

        _metrics, _slot, _gap, group_gap, widths = _measure(strip)

        assert group_gap > 0

        assert all(value > 0 for value in widths)


def test_an_empty_strip_draws_nothing_rather_than_a_frame():

    from gui.widgets.roster_strip import RosterStrip

    strip = RosterStrip()

    assert strip.is_empty()

    strip.setGroups([])

    assert strip.is_empty()


def test_the_same_content_twice_is_not_a_second_repaint():
    """
    Die Übersicht ruft `refresh()` bei jedem Seitenwechsel und bei
    jeder abgeschlossenen Hintergrundprüfung auf - derselbe Gedanke
    wie bei `restyle()`.
    """

    from gui.widgets.roster_strip import SlotGroup

    strip = _strip()

    repaints = []

    strip.update = lambda *args: repaints.append(1)

    strip.setGroups([
        SlotGroup("TANKS", ["Warrior", "Druid"], 0),
        SlotGroup("HEILER", ["Priest"] * 5, 1),
        SlotGroup("SCHADEN", ["Mage"] * 14, 3),
    ])

    assert repaints == []

    strip.setGroups([SlotGroup("ZUGESAGT", [""] * 10, 15)])

    assert repaints == [1]
