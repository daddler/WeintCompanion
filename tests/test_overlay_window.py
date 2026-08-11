"""
Das Overlay-Fenster: Anmelden, Abmelden, Schliessen.

Diese Datei existiert wegen eines Absturzes, den keine der übrigen
Prüfungen finden konnte, weil er **keine Python-Ausnahme auslöst**:
`closeEvent()` gab sein QCloseEvent an `hideEvent()` weiter, und das
reichte es an `QWidget::hideEvent(QHideEvent*)` durch. Qt liest den
Zeiger dort ungeprüft als QHideEvent - das Schließen des Overlays
beendete den Prozess mit SIGSEGV. Ein Test, der nur "wirft es eine
Ausnahme?" fragt, hätte das nie gesehen; dass dieser hier überhaupt
zu Ende läuft, IST die Zusicherung.

Wie tests/test_raid_data_service.py hängt die ganze Datei an PySide6
und überspringt sich ohne es selbst.
"""

import os

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("httpx")


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class _Logger:

    def info(self, *a):
        pass

    def error(self, *a):
        pass

    def success(self, *a):
        pass

    def warning(self, *a):
        pass


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


class _Academy:
    """
    Das Overlay hebt die eigene Zeile in der Rangliste hervor und
    fragt dafür, wer "ich" ist.
    """

    def player_name(self) -> str:
        return ""


class _Manager:
    """
    Nur, was das Overlay tatsächlich anfasst.
    """

    def __init__(self):
        self.logger = _Logger()
        self.config = _Config()
        self.academy = _Academy()


def _overlay():

    _app()

    from PySide6.QtCore import QObject, Signal

    from analyzer.models import RaidSnapshot

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())

    class _Feed(QObject):
        """
        Zählt Anmeldungen mit, statt einen Poll-Thread zu starten.

        `current()` liefert `RaidSnapshot.empty()` und nicht `None` -
        genau wie der echte Dienst, dessen `_snapshot` von Anfang an
        auf einem leeren Snapshot steht. Ein `None` hier wäre kein
        strengerer Test, sondern ein falscher: das Overlay darf sich
        auf die Zusage von `current()` verlassen.
        """

        snapshotChanged = Signal(object)

        def __init__(self):
            super().__init__()
            self.attached = 0
            self.detached = 0

        def attach(self):
            self.attached += 1

        def detach(self):
            self.detached += 1

        def current(self):
            return RaidSnapshot.empty()

    from gui.overlay.overlay_window import OverlayWindow

    manager = _Manager()

    manager.raid_data = _Feed()

    return OverlayWindow(manager), manager.raid_data


# --------------------------------------------------


def test_closing_the_overlay_does_not_kill_the_process():
    """
    Der Regressionstest zum SIGSEGV.

    Ein abgestürzter Prozess kann nichts behaupten - erreicht die
    letzte Zeile den Assert, hat `close()` überlebt.
    """

    overlay, feed = _overlay()

    overlay.show()

    overlay.close()

    assert feed.detached == 1


def test_showing_attaches_once_and_hiding_releases():

    overlay, feed = _overlay()

    overlay.show()

    assert feed.attached == 1

    overlay.hide()

    assert feed.detached == 1

    overlay.close()


def test_hide_then_close_releases_only_once():
    """
    `close()` löst auf manchen Plattformen zusätzlich ein hideEvent
    aus. Würde beide Wege je einmal abmelden, sänke der
    Referenzzähler des Dienstes unter den Stand der wirklich
    angemeldeten Interessenten - und der Poll-Thread stoppte,
    während WeintTV noch zusieht.
    """

    overlay, feed = _overlay()

    overlay.show()

    overlay.hide()

    overlay.close()

    assert feed.detached == 1


def test_repeated_show_and_close_stays_balanced():

    overlay, feed = _overlay()

    for _ in range(3):

        overlay.show()

        overlay.close()

    assert feed.attached == 3

    assert feed.detached == 3
