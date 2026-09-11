"""
Der Cooldown-Zeitstrahl und die Wartekarte - die beiden neuen
Widgets aus 3.6.0.

Sie bauen Widgets und brauchen deshalb Qt. Geprüft wird das, was ein
reiner Test nicht sehen kann: dass beide ohne Daten nicht abstürzen,
dass der Zeitstrahl einen Defensivcooldown nicht als Versäumnis malt,
und dass die Wartekarte ihren Takt nur laufen lässt, solange wirklich
etwas geholt wird.
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


# --------------------------------------------------
# Zeitstrahl
# --------------------------------------------------


def test_an_empty_timeline_draws_its_placeholder_without_raising():

    _app()

    from gui.widgets.tv.cooldown_timeline import CooldownTimeline

    strahl = CooldownTimeline()

    strahl.setPlaceholder("Keine Angaben zur Cooldown-Nutzung.")

    strahl.setTimeline((), 0.0, ())

    strahl.resize(600, 120)

    strahl.grab()


def test_the_timeline_grows_with_its_rows():
    """
    Eine feste Höhe würde die letzten Zeilen abschneiden - genau das,
    was eine Übersicht unbrauchbar macht.
    """

    _app()

    from gui.widgets.tv.cooldown_timeline import (
        ROW_HEIGHT,
        CooldownTimeline,
        TimelineRow,
    )

    strahl = CooldownTimeline()

    eine = [TimelineRow(label="Berserkerwut", casts=(10.0,), cooldown=180.0)]

    strahl.setTimeline(eine, 300.0)

    klein = strahl.minimumHeight()

    strahl.setTimeline(eine * 5, 300.0)

    assert strahl.minimumHeight() >= klein + 4 * ROW_HEIGHT


def test_a_cooldown_that_waits_for_its_moment_is_drawn_without_gaps():
    """
    `judged=False` heisst: für diese Zeile gibt es keine
    Nutzungsquote. Eine gelbe Lückenmarkierung dort hiesse, Umsicht
    als Versäumnis zu malen.
    """

    _app()

    from gui.widgets.tv.cooldown_timeline import CooldownTimeline, TimelineRow

    strahl = CooldownTimeline()

    strahl.setTimeline(
        [
            TimelineRow(
                label="Schildwall",
                casts=(120.0,),
                cooldown=300.0,
                gaps=((0.0, 120.0),),
                judged=False,
                tone="info",
            ),
        ],
        400.0,
        [(60.0, 100.0)],
    )

    strahl.resize(700, 120)

    strahl.grab()


def test_setting_the_same_timeline_twice_is_a_no_op():
    """
    Der Strahl hängt am Snapshot-Strom, und der tickt in einer
    Wiedergabe viermal je Sekunde.
    """

    _app()

    from gui.widgets.tv.cooldown_timeline import CooldownTimeline, TimelineRow

    strahl = CooldownTimeline()

    rows = [TimelineRow(label="Berserkerwut", casts=(10.0,), cooldown=180.0)]

    strahl.setTimeline(rows, 300.0)

    hoehe = strahl.minimumHeight()

    strahl.setTimeline(list(rows), 300.0)

    assert strahl.minimumHeight() == hoehe


# --------------------------------------------------
# Wartekarte
# --------------------------------------------------


class _Service:
    """
    Genug RaidDataService, um die Karte zu bauen: ein Signal und ein
    Zustand.
    """

    def __init__(self, state):

        from PySide6.QtCore import QObject, Signal

        self._state = state

        holder = type(
            "_Holder",
            (QObject,),
            {"archiveChanged": Signal()},
        )

        self._holder = holder()

        self.archiveChanged = self._holder.archiveChanged

    def archive_state(self):

        return self._state


def _state(**overrides):

    from core.raid_data_service import MODE_ARCHIVE, ArchiveState

    base = dict(mode=MODE_ARCHIVE)

    base.update(overrides)

    return ArchiveState(**base)


def test_the_waiting_card_stays_invisible_while_nothing_is_loading():

    _app()

    from gui.widgets.tv.loading_card import LoadingCard

    karte = LoadingCard(_Service(_state()))

    assert not karte.isVisible()

    assert not karte._timer.isActive()


def test_the_waiting_card_names_the_pull_and_shows_a_number():

    import time

    _app()

    from gui.widgets.tv.loading_card import LoadingCard

    service = _Service(
        _state(
            fight_loading=True,
            fight_started_at=time.monotonic() - 20.0,
            fight_expected=60.0,
            fight_label="Garrosh Höllschrei",
        )
    )

    karte = LoadingCard(service)

    assert "Garrosh" in karte.title.text()

    assert "20 s" in karte.status.text()

    assert "etwa" in karte.status.text()

    #
    # Der Balken steht sichtbar, aber nie am Ende.
    #

    assert 0.0 < karte.bar._value < 1.0


def test_the_waiting_card_says_when_it_takes_longer_than_usual():

    import time

    _app()

    from gui.widgets.tv.loading_card import LoadingCard

    karte = LoadingCard(
        _Service(
            _state(
                fight_loading=True,
                fight_started_at=time.monotonic() - 200.0,
                fight_expected=60.0,
                fight_label="Garrosh Höllschrei",
            )
        )
    )

    assert "länger" in karte.status.text()

    assert karte.bar._value < 1.0


def test_the_elapsed_time_is_zero_when_no_fetch_runs():
    """
    Ohne laufenden Abruf gibt es keine verstrichene Zeit - und keine
    hochgezählte Sekundenzahl, die aussieht, als hinge etwas.
    """

    assert _state().elapsed(1000.0) == 0.0

    assert _state(fight_loading=True).elapsed(1000.0) == 0.0
