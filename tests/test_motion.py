"""
Bewegung.

Zwei Regeln werden hier festgehalten, weil ihre Verletzung stumm
bliebe:

**"Bewegung reduzieren" ist eine Abschaltung, keine Abschwächung.**
Jede Dauer läuft durch `duration()`; wer eine Dauer direkt aus der
Tabelle liest, umgeht die Einstellung, und niemand merkt es - außer
den Menschen, für die sie da ist.

**Was sich mehrmals pro Sekunde ändert, wird nicht animiert.** Eine
Wiedergabe tickt mit 4 Hz; eine 240 ms lange Zahlenanimation wäre
dann dauerhaft unterwegs und nie am Ziel.

Das Modul braucht Qt (`QEasingCurve`), aber keine Widgets - wie der
Rest von `tests/` baut also auch hier nichts eine Oberfläche auf.
"""

import pytest

pytest.importorskip("PySide6")

from gui.theme import motion
from gui.theme.theme_manager import ThemeManager


@pytest.fixture
def theme():
    """
    Ein eigener ThemeManager je Test - nicht das Singleton aus
    `theme()`, damit ein Test die Einstellungen der Anwendung nicht
    verstellt.

    `ThemeManager` ist ein QObject, und hier steht ausdrücklich
    **kein** `deleteLater()`. Das war der erste Versuch und hat einen
    Absturz erzeugt, der nicht einmal in dieser Datei auftrat:
    `deleteLater()` stellt die Löschung nur in eine Warteschlange, die
    eine laufende Ereignisschleife abarbeitet. In diesen Tests gibt es
    keine - die Löschung blieb also liegen, bis ein *anderer* Test
    (die Teardown-Vorrichtung von `test_raid_data_service.py`)
    `processEvents()` aufrief und das fremde Objekt mitten in seinem
    eigenen Abbau zerstörte. Der Segfault erschien dadurch in einer
    Datei, die damit nichts zu tun hat, und nur im Gesamtlauf.

    Ohne `deleteLater()` räumt CPythons Referenzzählung das Objekt
    sofort und im Hauptthread ab - deterministisch und genau dort, wo
    es entstanden ist.
    """

    yield ThemeManager()


def test_every_motion_token_has_a_duration_and_a_curve():

    for name, token in motion.MOTION.items():

        assert token.duration > 0, name

        assert token.curve is not None, name


def test_durations_match_the_specification(theme):
    """
    Die Zahlen aus §3 des Entwurfs. Sie stehen hier ein zweites Mal,
    damit ein versehentliches Verstellen auffällt.
    """

    assert motion.duration("page", theme) == 180

    assert motion.duration("number", theme) == 240

    assert motion.duration("bar", theme) == 220

    assert motion.duration("progress", theme) == 300


def test_reduced_motion_zeroes_every_duration(theme):

    theme.set_motion_reduced(True)

    for name in motion.MOTION:

        assert motion.duration(name, theme) == 0, name

    assert motion.is_reduced(theme)


def test_the_system_setting_also_reduces(theme):
    """
    Nutzerwahl ODER Systemvorgabe - beide sagen dasselbe aus.
    """

    theme.set_system_motion_reduced(True)

    assert motion.is_reduced(theme)

    #
    # Die ausdrückliche Wahl des Nutzers bleibt davon unberührt:
    # schaltet er die Systemvorgabe später ab, findet er nicht
    # plötzlich eine Einstellung vor, die er nie getroffen hat.
    #

    assert not theme.user_motion_reduced()


def test_an_unknown_token_costs_no_animation_instead_of_crashing(theme):

    assert motion.duration("gibtsnicht", theme) == 0


def test_large_number_jumps_are_set_instead_of_animated():
    """
    Der erste Messwert eines Pulls kommt aus dem Nichts. Eine Zahl,
    die 240 ms lang von 0 hochläuft, behauptet eine Entwicklung, die
    es nicht gab.
    """

    assert not motion.should_animate_number(0, 4_700_000)

    assert motion.should_animate_number(100, 110)

    assert not motion.should_animate_number(100, 200)


def test_identical_values_are_not_animated():

    assert not motion.should_animate_number(42, 42)

    assert not motion.should_animate_number(0, 0)


def test_playback_rates_suspend_value_animation():
    """
    Die Wiedergabe tickt mit 4 Hz, eine Live-Quelle mit rund 1 Hz.
    """

    assert motion.suspend_value_animation(4.0)

    assert not motion.suspend_value_animation(1.0)

    assert not motion.suspend_value_animation(2.0)


def test_the_skeleton_delay_is_long_enough_to_swallow_a_cache_hit():
    """
    Ein Abruf unter 250 ms zeigt nie ein Skelett - sonst blitzt bei
    jedem Zwischenspeichertreffer eine Ladefläche auf.
    """

    assert motion.SKELETON_DELAY >= 200
