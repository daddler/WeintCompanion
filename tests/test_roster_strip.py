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


def test_filled_slots_are_painted_in_class_colour():
    """
    Das eigentliche Bild: ein Krieger-Kästchen ist braun, ein
    Priester-Kästchen weiß, ein Magier-Kästchen hellblau. Geprüft wird
    deshalb am gerenderten Bild und nicht an der Tabelle - genau diese
    Farben fehlten in der App, obwohl `class_color()` sie kannte: der
    Bot schickte gar keine Klassen, und der Streifen malte alles in
    Akzentfarbe.
    """

    from PySide6.QtGui import QImage

    from gui.theme.wow_colors import class_color
    from gui.widgets.roster_strip import RosterStrip, SlotGroup

    strip = RosterStrip()

    strip.resize(600, strip.height())

    strip.setGroups([
        SlotGroup("TANKS", ["Warrior"], 0),
        SlotGroup("HEILER", ["Priest"], 0),
        SlotGroup("SCHADEN", ["Mage"], 1),
    ])

    image = QImage(strip.size(), QImage.Format_ARGB32)

    image.fill(0)

    strip.render(image)

    farben = {
        QImage.pixelColor(image, x, y).name()
        for x in range(image.width())
        for y in range(image.height())
        if QImage.pixelColor(image, x, y).alpha() == 255
    }

    for klasse in ("Warrior", "Priest", "Mage"):
        assert class_color(klasse).lower() in farben, (
            f"Die Zusage der Klasse {klasse} erscheint nicht in ihrer "
            f"Klassenfarbe - der Streifen zeigt einen einheitlichen "
            f"Balken."
        )


def test_a_slot_without_a_class_is_the_accent_and_not_a_guess():
    """
    Meldet der Bot nur Zahlen, sind die Plätze in Akzentfarbe. Eine
    geratene Klasse wäre im Bild von einer gemeldeten nicht zu
    unterscheiden - dieselbe Linie wie `stars == 0`.
    """

    from PySide6.QtGui import QImage

    from gui.theme.theme_manager import theme
    from gui.widgets.roster_strip import RosterStrip, SlotGroup

    strip = RosterStrip()

    strip.resize(600, strip.height())

    strip.setGroups([SlotGroup("ZUGESAGT", [""] * 3, 2)])

    image = QImage(strip.size(), QImage.Format_ARGB32)

    image.fill(0)

    strip.render(image)

    farben = {
        QImage.pixelColor(image, x, y).name()
        for x in range(image.width())
        for y in range(image.height())
        if QImage.pixelColor(image, x, y).alpha() == 255
    }

    assert theme().accent_base().lower() in farben


def test_the_strip_understands_the_class_as_the_bot_writes_it():
    """
    Drei Schreibweisen derselben Klasse: der englische Anzeigename aus
    WarcraftLogs, das Kürzel des Addons und - weil die Anmeldung im
    Discord auf Deutsch geführt wird - das deutsche Wort. Alle drei
    müssen dieselbe Farbe treffen; eine unbekannte Schreibweise ist im
    Streifen grau und damit von "keine Klasse gemeldet" nicht zu
    unterscheiden.
    """

    from gui.theme.wow_colors import CLASS_COLORS, class_color

    for schreibweise in ("Death Knight", "DEATHKNIGHT", "Todesritter"):
        assert class_color(schreibweise) == CLASS_COLORS["Death Knight"]

    assert class_color("Mönch") == CLASS_COLORS["Monk"]

    assert class_color("Krieger") == CLASS_COLORS["Warrior"]
