"""
Die Haltepunkte entscheiden, was unter der Entwurfsgröße passiert.

Der eigentliche Prüfgegenstand ist die **Hysterese**. Ohne sie
schaltet ein Fenster, dessen Breite genau auf einer Schwelle steht,
bei jedem Pixel Mausbewegung hin und her - und jeder Wechsel baut
Layouts um und animiert die Navigationsspalte. Das ist der Grund,
warum `resolve()` den vorherigen Zustand braucht, und der Grund,
warum es dafür ein eigenes, Qt-freies Modul gibt.
"""

from gui.layout.breakpoints import LayoutState, resolve
from gui.theme import tokens


def test_the_design_size_needs_no_adjustments():

    state = resolve(1440)

    assert state == LayoutState()


def test_each_threshold_engages_below_itself():

    assert resolve(tokens.BREAKPOINT_DRAWER - 1).drawer

    assert resolve(tokens.BREAKPOINT_NAV - 1).nav_collapsed

    assert resolve(tokens.BREAKPOINT_SINGLE_COLUMN - 1).single_column


def test_exactly_on_the_threshold_nothing_engages():
    """
    "< 1280" heißt < 1280, nicht <= 1280 - bei genau 1280 px gilt der
    Entwurf noch unverändert.
    """

    assert not resolve(tokens.BREAKPOINT_DRAWER).drawer

    assert not resolve(tokens.BREAKPOINT_NAV).nav_collapsed


def test_hysteresis_keeps_the_state_just_above_the_threshold():
    """
    Der Kern: einmal eingeklappt, bleibt es eingeklappt, bis das
    Fenster deutlich (40 px) über die Schwelle zurückgeschoben wird.
    Ein einzelner Pixel darf nicht zurückschalten.
    """

    narrow = resolve(tokens.BREAKPOINT_NAV - 1)

    assert narrow.nav_collapsed

    just_above = resolve(tokens.BREAKPOINT_NAV + 1, narrow)

    assert just_above.nav_collapsed, (
        "ein Pixel über der Schwelle darf nicht zurückschalten"
    )

    still_inside = resolve(
        tokens.BREAKPOINT_NAV + tokens.BREAKPOINT_HYSTERESIS - 1,
        just_above,
    )

    assert still_inside.nav_collapsed

    released = resolve(
        tokens.BREAKPOINT_NAV + tokens.BREAKPOINT_HYSTERESIS,
        still_inside,
    )

    assert not released.nav_collapsed


def test_hysteresis_does_not_stick_forever():
    """
    Weit oberhalb der Schwelle muss der Zustand in jedem Fall
    zurückfallen - sonst wäre aus der Hysterese eine Einbahnstraße
    geworden.
    """

    collapsed = LayoutState(drawer=True, nav_collapsed=True, single_column=True)

    assert resolve(1920, collapsed) == LayoutState()


def test_the_thresholds_are_independent_of_each_other():
    """
    Bei 1200 px ist die Nebenspalte eine Schublade, die Navigation
    aber noch ausgeschrieben - die drei Schwellen sind drei Aussagen
    und keine Stufenzahl.
    """

    state = resolve(1200)

    assert state.drawer

    assert not state.nav_collapsed

    assert not state.single_column


def test_the_smallest_supported_window_engages_everything():

    state = resolve(tokens.WINDOW_MIN[0])

    assert state.drawer

    assert state.nav_collapsed

    assert state.single_column
