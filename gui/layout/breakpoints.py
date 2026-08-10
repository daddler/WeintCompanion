"""
WeintCompanion 2.0
Haltepunkte

Drei Schwellen entscheiden, wie sich das Fenster unter der
Entwurfsgroesse verhaelt (§4):

    < 1280 px   die rechte Nebenspalte wird zur Schublade
    < 1120 px   die Navigationsspalte klappt auf Symbole ein
    <  980 px   Kartenraster einspaltig, Tabellen scrollen seitlich

Warum das ein eigenes Modul ist und nicht drei `if` in `resizeEvent`:

**Hysterese.** Ein Fenster, dessen Breite genau auf einer Schwelle
steht, wechselt sonst bei jedem Pixel Mausbewegung hin und her - und
jeder Wechsel baut Layouts um, animiert die Navigationsspalte und
zeichnet neu. Die Schwelle zum Zurueckschalten liegt deshalb 40 px
oberhalb der zum Einschalten. Das macht die Funktion aber
**zustandsbehaftet**: sie braucht den vorherigen Zustand, und genau
solche Funktionen gehoeren dorthin, wo man sie ohne laufendes Fenster
pruefen kann.

Dieses Modul importiert deshalb kein Qt - dieselbe Trennung wie bei
`analyzer/` und `gui/widgets/tv/analysis_gap.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from gui.theme import tokens


@dataclass(frozen=True)
class LayoutState:
    """
    Was bei der aktuellen Fensterbreite gilt.

    Drei unabhaengige Aussagen statt einer Stufenzahl: die Schwellen
    liegen zwar der Groesse nach hintereinander, ihre Wirkungen sind
    aber verschieden, und eine Ansicht fragt jeweils nur nach einer.
    WeintTV etwa klappt die Navigation immer ein, unabhaengig von der
    Breite - es liest `single_column`, nicht `nav_collapsed`.
    """

    #
    # Rechte Nebenspalte als Overlay-Schublade statt fester Spalte.
    #
    drawer: bool = False

    #
    # Navigationsspalte auf 72 px. Die **Wahl des Nutzers** bleibt
    # davon unberuehrt und wird oberhalb der Schwelle wiederhergestellt
    # (siehe NavColumn.set_forced_collapsed).
    #
    nav_collapsed: bool = False

    #
    # Kartenraster einspaltig; Datentabellen erhalten waagerechten
    # Scroll, die erste Spalte bleibt stehen.
    #
    single_column: bool = False


def resolve(width: int, previous: LayoutState | None = None) -> LayoutState:
    """
    Der Layoutzustand fuer diese Breite.

    `previous` ist der zuletzt geltende Zustand; ohne ihn wird ohne
    Hysterese entschieden (richtig fuer den ersten Aufruf, wenn es noch
    kein "vorher" gibt).
    """

    if previous is None:
        previous = LayoutState()

    return LayoutState(
        drawer=_cross(
            width,
            tokens.BREAKPOINT_DRAWER,
            previous.drawer,
        ),
        nav_collapsed=_cross(
            width,
            tokens.BREAKPOINT_NAV,
            previous.nav_collapsed,
        ),
        single_column=_cross(
            width,
            tokens.BREAKPOINT_SINGLE_COLUMN,
            previous.single_column,
        ),
    )


def _cross(width: int, threshold: int, active: bool) -> bool:
    """
    Ob die Schwelle bei dieser Breite greift, mit Hysterese.

    Aktiv wird sie unterhalb der Schwelle, inaktiv erst wieder ein
    Stueck **oberhalb**. Zwischen beiden Werten aendert sich nichts -
    das ist der ganze Zweck.
    """

    if active:
        return width < threshold + tokens.BREAKPOINT_HYSTERESIS

    return width < threshold
