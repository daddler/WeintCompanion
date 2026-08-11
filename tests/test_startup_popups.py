"""
Die App muss starten - auch beim ersten Start nach einem Update.

Der Bericht: nach dem Update von 2.0.2 auf 2.0.3 blieb der
Ladebalken unter Windows bei "Übersicht wird gezeichnet …" stehen,
das Fenster kam nie. Kein Absturz, kein Protokolleintrag, keine
Fehlermeldung.

Die Kette dahinter bestand aus drei Teilen, von denen jeder für sich
harmlos aussah:

1. `MainWindow.__init__` meldete die Start-Popups mit
   `QTimer.singleShot(0, …)` an - laut Kommentar, "damit das Fenster
   zuerst sichtbar wird".
2. app.py baut das Fenster hinter dem Startbildschirm und rief
   zwischen Bau und `show()` ein `processEvents()` auf, um den
   Ladebalken weiterzuzeichnen. Dort feuerte der 0-ms-Timer - also
   **vor** `window.show()`.
3. `show_whats_new_if_needed()` öffnet nach jedem Update einen
   modalen Dialog. `exec()` bleibt in einer eigenen
   Ereignisschleife stehen; der Startbildschirm liegt als
   `WindowStaysOnTopHint` darüber und wurde nie geschlossen, weil
   die Zeile dafür erst nach `show()` kommt.

Ergebnis: ein unsichtbarer Dialog wartete auf eine Antwort, die
niemand geben konnte. Unter Linux fiel es nicht auf, weil dort
manche Compositor den Dialog trotzdem nach vorn holen.

Geprüft wird deshalb nicht "erscheint das Popup", sondern die drei
Bedingungen, unter denen es überhaupt erscheinen darf.
"""

import ast
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parent.parent


def _tree(relative: str) -> ast.Module:

    return ast.parse((ROOT / relative).read_text(encoding="utf-8"))


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    raise AssertionError(f"{name}() nicht gefunden")


def _calls(node: ast.AST) -> list[str]:
    """
    Die Namen aller Aufrufe darin, als "objekt.methode" bzw. "name".
    """

    found = []

    for inner in ast.walk(node):

        if not isinstance(inner, ast.Call):
            continue

        target = inner.func

        if isinstance(target, ast.Attribute):

            owner = getattr(target.value, "id", "")

            found.append(
                f"{owner}.{target.attr}" if owner else target.attr
            )

        elif isinstance(target, ast.Name):

            found.append(target.id)

    return found


# --------------------------------------------------
# 1. Der Ladebalken darf keine Ereignisschleife laufen lassen
# --------------------------------------------------


def test_the_splash_repaints_itself_instead_of_running_the_loop():
    """
    `processEvents()` führt **alles** aus, was gerade ansteht - auch
    einen modalen Dialog, der dort nichts zu suchen hat. Ein
    Ladebalken soll zeichnen, nicht Arbeit erledigen.
    """

    stage = _function(_tree("app.py"), "_stage")

    calls = _calls(stage)

    assert "splash.repaint" in calls

    assert not [name for name in calls if "processEvents" in name]


def test_only_one_event_loop_run_and_only_before_the_window_exists():
    """
    Ein einziges `processEvents()` bleibt nötig, damit der
    Startbildschirm überhaupt eine Fläche bekommt. Es muss aber
    **vor** dem Bau des Fensters stehen: danach gäbe es wieder
    etwas, das dazwischenkommen kann.
    """

    tree = _tree("app.py")

    main = _function(tree, "main")

    show = _function(tree, "_show_main_window")

    inside = {id(node) for node in ast.walk(show)}

    runs = [
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "processEvents"
        and id(node) not in inside
    ]

    assert len(runs) == 1

    built = [
        node.lineno
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "MainWindow"
    ]

    #
    # MainWindow wird in _show_main_window gebaut, also weiter unten
    # in der Datei - die eine Schleife läuft davor.
    #

    assert built

    assert runs[0].lineno < min(built)


# --------------------------------------------------
# 2. Der Startbildschirm ist weg, bevor die Schleife weiterläuft
# --------------------------------------------------


def test_the_splash_is_closed_before_the_loop_regains_control():
    """
    Er liegt immer oben. Ist er noch da, wenn das erste Start-Popup
    aufgeht, liegt der modale Dialog darunter - und die App hängt,
    genau wie berichtet.
    """

    show = _function(_tree("app.py"), "_show_main_window")

    lines = {}

    for inner in ast.walk(show):

        if not isinstance(inner, ast.Call):
            continue

        target = inner.func

        if not isinstance(target, ast.Attribute):
            continue

        owner = getattr(target.value, "id", "")

        lines.setdefault(f"{owner}.{target.attr}", inner.lineno)

    assert "window.show" in lines

    assert "splash.close" in lines

    assert lines["window.show"] < lines["splash.close"]


# --------------------------------------------------
# 3. Die Popups hängen an der Sichtbarkeit, nicht am Konstruktor
# --------------------------------------------------


def test_the_constructor_does_not_schedule_the_startup_popups():
    """
    Ein Timer im Konstruktor sagt "später". Gebraucht wird "wenn das
    Fenster steht" - und das weiß nur das Fenster selbst.
    """

    tree = _tree("gui/main_window.py")

    for node in ast.walk(tree):

        if not isinstance(node, ast.ClassDef) or node.name != "MainWindow":
            continue

        init = _function(node, "__init__")

        names = [
            inner.attr
            for inner in ast.walk(init)
            if isinstance(inner, ast.Attribute)
        ]

        assert "_show_startup_popups" not in names

        assert "_queue_startup_popups" not in names

        return

    raise AssertionError("MainWindow nicht gefunden")


def test_the_popups_hang_on_the_window_becoming_visible():

    tree = _tree("gui/main_window.py")

    event = _function(tree, "showEvent")

    assert "self._queue_startup_popups" in _calls(event)


# --------------------------------------------------
# 4. Und einmal in echt
# --------------------------------------------------


#
# Die Prüfungen oben brauchen kein Qt - sie lesen Quelltext. Der
# `importorskip` steht deshalb in den beiden Tests darunter und nicht
# am Dateikopf: sonst nähme ein Rechner ohne Qt-Systembibliotheken
# genau die Prüfungen mit, die den berichteten Fehler beschreiben.
#


def _app():

    import os

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    existing = QApplication.instance()

    return existing if existing is not None else QApplication([])


def test_a_repaint_does_not_run_pending_work_but_processevents_does():
    """
    Die Qt-Eigenschaft, auf der der Fix beruht - einmal
    festgehalten, damit sie nicht als Geschmacksfrage gilt.

    `repaint()` malt synchron und führt dabei nichts anderes aus.
    `processEvents()` arbeitet ab, was ansteht - und beim
    fehlerhaften Start war das der modale Dialog.
    """

    pytest.importorskip("PySide6")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget

    app = _app()

    fired = []

    widget = QWidget()

    widget.show()

    app.processEvents()

    QTimer.singleShot(0, lambda: fired.append(True))

    widget.repaint()

    assert fired == []

    app.processEvents()

    assert fired == [True]

    widget.close()


def test_no_popup_runs_before_the_window_is_visible(monkeypatch):
    """
    Der berichtete Fehler, am echten Fenster.

    Nicht "erscheint der Dialog", sondern: solange das Fenster nicht
    sichtbar ist, darf **nichts** ihn anstoßen. Beim Nutzer war
    genau das die Lage - der Dialog lief, das Fenster stand noch
    hinter dem Startbildschirm, und `exec()` kam nie zurück.

    Die beiden Dialoge werden durch Aufzeichnungen ersetzt: ein
    echtes `exec()` würde diesen Test aufhängen, und zwar aus
    demselben Grund wie die App.
    """

    pytest.importorskip("PySide6")

    app = _app()

    from core.companion_manager import CompanionManager
    from core.config import Config
    from gui.theme.theme_manager import init_theme

    import gui.main_window as main_window

    #
    # Der Netzwerkteil des Starts gehört nicht zu dieser Frage.
    #

    monkeypatch.setattr(CompanionManager, "initialize", lambda self: None)

    seen = []

    monkeypatch.setattr(
        main_window,
        "show_whats_new_if_needed",
        lambda manager, parent=None: seen.append(
            bool(parent is not None and parent.isVisible())
        ),
    )

    monkeypatch.setattr(
        main_window,
        "show_discord_link_prompt_if_needed",
        lambda manager, parent=None: None,
    )

    init_theme(Config()).apply_stylesheet()

    window = main_window.MainWindow()

    try:

        #
        # So weit war die App beim Nutzer: gebaut, aber nicht
        # gezeigt - und der Startbildschirm ließ die Schleife
        # laufen.
        #

        for _ in range(3):
            app.processEvents()

        assert seen == []

        window.show()

        for _ in range(3):
            app.processEvents()

        assert seen == [True]

    finally:

        window.close()

        window.deleteLater()

        app.processEvents()


def test_the_popups_are_queued_once_not_on_every_restore():
    """
    `showEvent` feuert auch nach jedem Wiederherstellen aus dem
    Tray. Ohne Merker stünde der "Was ist neu"-Dialog dann bei jedem
    Aufklappen des Fensters wieder da.
    """

    pytest.importorskip("PySide6")

    from PySide6.QtCore import QTimer

    from gui.main_window import MainWindow

    app = _app()

    class _Stub:

        def __init__(self):

            self._startup_popups_queued = False

            self.shown = 0

        def _show_startup_popups(self):

            self.shown += 1

    stub = _Stub()

    for _ in range(3):
        MainWindow._queue_startup_popups(stub)

    #
    # Der Timer läuft erst in der Ereignisschleife.
    #

    assert stub.shown == 0

    QTimer.singleShot(0, lambda: None)

    app.processEvents()

    assert stub.shown == 1
