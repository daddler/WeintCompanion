"""
Wo der Generationswechsel auftauchen darf - und wo nicht.

Zwei Regeln, die sich beide erst im Zusammenspiel zeigen und
deshalb hier stehen und nicht bei den Bausteinen:

**Ohne Freigabe kein Fenster.** Der Dialog wird nicht "leer"
angezeigt oder "ausgegraut" - er wird gar nicht gebaut. Solange
Companion-Forever entwickelt wird, verhaelt sich die App, als gaebe
es diese Schicht nicht.

**Die Pruefung geht ins Netz und gehoert deshalb nicht in eine
Seite.** `refresh()` darf nur zeichnen (siehe
docs/architecture/navigation.md); der Aufruf steht im
Hintergrundlauf des Managers. Das wird strukturell geprueft, so wie
`tests/test_install_failure.py` den weggeworfenen `WorkflowResult`
strukturell prueft: eine Regel, die nur an einer von zwei Stellen
befolgt wird, ist keine Regel.
"""

import ast
import os
import pathlib
import types

import pytest


ROOT = pathlib.Path(__file__).resolve().parent.parent


# --------------------------------------------------
# Strukturell: kein Netz in einer Seite
# --------------------------------------------------


def _python_files(folder: str):

    return sorted((ROOT / folder).rglob("*.py"))


def test_no_page_checks_for_the_next_generation_itself():
    """
    Die Pruefung geht ins Netz. Stuende sie in einer Seite, waere sie
    im schlimmsten Fall in deren `refresh()` - und `refresh()` wird
    von `state_changed` ausgeloest, das die Pruefung selbst wieder
    meldet. Genau dieser Kreis hat die ConnectionsPage einmal bis zur
    Rekursionsgrenze getrieben.

    Geprueft wird der **Aufruf**, nicht das Wort: ein Verweis im
    Kommentar oder Docstring ist genau das, was dort stehen soll.
    """

    for path in _python_files("gui"):

        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            function = node.func

            if not isinstance(function, ast.Attribute):
                continue

            if function.attr == "check_forever_migration":

                raise AssertionError(
                    f"{path.relative_to(ROOT)} prueft selbst auf die "
                    "naechste Generation - das gehoert in den "
                    "Hintergrundlauf des Managers."
                )

            if (
                function.attr == "check"
                and isinstance(function.value, ast.Attribute)
                and function.value.attr == "migration"
            ):

                raise AssertionError(
                    f"{path.relative_to(ROOT)} startet die "
                    "Release-Pruefung selbst."
                )


def test_the_offer_is_shown_at_most_once_per_session():
    """
    Der Merker muss gesetzt sein, BEVOR der Dialog in die Schlange
    geht: `state_changed` kommt auch aus der Hintergrundwache, und
    ein zweiter Dialog hinter dem ersten waere niemandem zu
    erklaeren.
    """

    tree = ast.parse(
        (ROOT / "gui" / "main_window.py").read_text(encoding="utf-8")
    )

    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_announce_forever_migration"
    )

    lines = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and target.attr == "_forever_migration_offered"
            for target in node.targets
        )
    ]

    calls = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "singleShot"
    ]

    assert lines and calls

    assert min(lines) < min(calls), (
        "Der Merker wird erst nach dem Oeffnen gesetzt - dann kann eine "
        "zweite Pruefung einen zweiten Dialog anmelden."
    )


# --------------------------------------------------
# Verhalten: der Dialog erscheint nur mit Freigabe
# --------------------------------------------------


def _app():
    """
    Die Qt-Tests dieser Datei ueberspringen sich selbst, wenn PySide6
    fehlt - der Testlauf in der CI installiert nur pytest und httpx.
    Der Aufruf steht deshalb IN den Tests und nicht am Dateianfang:
    ein `importorskip` auf Modulebene wuerde die strukturellen Tests
    oben mit ueberspringen, und genau die sollen dort laufen.
    """

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeService:

    def __init__(self, enabled=False, offer=None):

        self._enabled = enabled
        self._offer = offer

    def enabled(self):
        return self._enabled

    def offer(self, result=None):
        return self._offer


def _manager(service):

    return types.SimpleNamespace(migration=service)


def test_a_disabled_migration_builds_no_dialog(monkeypatch):

    _app()

    from gui.dialogs import migration_dialog

    built = []

    monkeypatch.setattr(
        migration_dialog,
        "MigrationDialog",
        lambda *args, **kwargs: built.append(args) or _Never(),
    )

    migration_dialog.show_migration_offer_if_needed(
        _manager(FakeService(enabled=False))
    )

    assert built == []


def test_without_an_offer_no_dialog_either(monkeypatch):

    _app()

    from gui.dialogs import migration_dialog

    built = []

    monkeypatch.setattr(
        migration_dialog,
        "MigrationDialog",
        lambda *args, **kwargs: built.append(args) or _Never(),
    )

    migration_dialog.show_migration_offer_if_needed(
        _manager(FakeService(enabled=True, offer=None))
    )

    assert built == []


def test_a_manager_without_the_service_is_no_crash():
    """
    Aeltere Aufrufer und die Tests reichen hier Namensraeume ohne
    `migration` durch - daraus einen Absturz beim Start zu machen
    waere der zweite Fehler nach dem ersten.
    """

    _app()

    from gui.dialogs import migration_dialog

    migration_dialog.show_migration_offer_if_needed(types.SimpleNamespace())


class _Never:
    """
    Steht fuer einen Dialog, der nie gebaut werden darf - `exec()`
    wuerde im Test eine Ereignisschleife oeffnen.
    """

    def exec(self):
        raise AssertionError("Der Dialog wurde trotzdem geoeffnet.")
