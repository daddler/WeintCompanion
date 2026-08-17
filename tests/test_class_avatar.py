"""
Trägt jede Klasse ein Wappen - und wird es auch gezeichnet?

Das Charakterbild unter "Meine Charaktere" ist die Desktop-Antwort auf
das Porträt in der Charakterrubrik von WeintCodex. Es hängt an einer
SVG-Datei je Klasse, und genau da sitzt der lautlose Fehler: fehlt die
Datei oder ist sie fehlerhaft, liefert `QSvgRenderer.isValid()`
schlicht `False`, `tinted_pixmap()` gibt eine **durchsichtige** Pixmap
zurück und die Kachel bleibt leer. Nichts wirft, nichts wird
protokolliert - man sieht es nur, wenn man mit einem Schamanen
angemeldet war.

Geprüft wird deshalb nicht die Zuordnung allein, sondern dass beim
Zeichnen tatsächlich Farbe ankommt.
"""

import os

import pytest


# --------------------------------------------------
# Ohne Qt: die Zuordnung selbst
# --------------------------------------------------


def test_every_class_has_an_emblem():

    from gui.theme.wow_colors import CLASS_COLORS, CLASS_ICONS

    assert set(CLASS_ICONS) == set(CLASS_COLORS)


def test_every_emblem_exists_as_a_file():

    from core.resources import Resources
    from gui.theme.wow_colors import CLASS_ICONS

    for name in CLASS_ICONS.values():

        assert os.path.exists(
            Resources.path(f"resources/icons/{name}.svg")
        ), name


def test_the_addons_spelling_finds_the_emblem():
    """
    Das Addon meldet `UnitClass()`s zweiten Rückgabewert - `PALADIN`,
    `DEATHKNIGHT`. Ohne Normalisierung bliebe genau die Quelle ohne
    Bild, aus der diese Seite ihre Daten bezieht.
    """

    from gui.theme.wow_colors import class_icon

    assert class_icon("PALADIN") == "class_paladin"

    assert class_icon("DEATHKNIGHT") == "class_deathknight"

    assert class_icon("Death Knight") == "class_deathknight"


def test_an_unknown_class_gets_no_emblem():
    """
    `None` heißt "keine Angabe". Ein geratenes Wappen wäre von einem
    gemeldeten nicht zu unterscheiden.
    """

    from gui.theme.wow_colors import class_icon

    assert class_icon("") is None

    assert class_icon("Dämonenjäger") is None


# --------------------------------------------------
# Mit Qt: kommt beim Zeichnen etwas an?
# --------------------------------------------------


pytest.importorskip("PySide6")


class _Config:

    def __init__(self):
        self.data = {}

    def save(self):
        pass


def _app():

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())

    return app


def _opaque_pixels(widget) -> int:

    from PySide6.QtGui import QImage

    image = QImage(widget.size(), QImage.Format_ARGB32)

    image.fill(0)

    widget.render(image)

    widget.close()

    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    )


def test_every_emblem_really_renders():

    _app()

    from gui.theme.icons import tinted_pixmap
    from gui.theme.wow_colors import CLASS_ICONS

    for class_name, icon in CLASS_ICONS.items():

        pixmap = tinted_pixmap(icon, "#FFFFFF", 32)

        image = pixmap.toImage()

        filled = sum(
            1
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).alpha() > 0
        )

        #
        # Eine fehlerhafte SVG ergibt exakt null gefüllte Punkte. Die
        # Untergrenze liegt bewusst höher, damit auch ein Wappen
        # auffällt, das auf einen Strich zusammengeschrumpft ist.
        #

        assert filled > 40, class_name


def test_the_avatar_shows_the_class_it_was_given():
    """
    Zwei Klassen dürfen nicht dasselbe Bild ergeben - sonst hätte
    sich irgendwo ein Standardwappen eingeschlichen.
    """

    _app()

    from gui.widgets.class_avatar import ClassAvatar

    def rendered(class_name):

        from PySide6.QtGui import QImage

        widget = ClassAvatar(class_name, 56)

        image = QImage(widget.size(), QImage.Format_ARGB32)

        image.fill(0)

        widget.render(image)

        widget.close()

        return bytes(image.constBits())

    assert rendered("PALADIN") != rendered("DRUID")


def test_an_unknown_class_still_draws_a_tile():
    """
    Ohne gemeldete Klasse verschwindet die Kachel nicht: die Karte
    behält ihre Form, und der leere Platz wäre die zweite Behauptung
    nach dem falschen Wappen.
    """

    _app()

    from gui.widgets.class_avatar import ClassAvatar

    widget = ClassAvatar("", 56)

    assert _opaque_pixels(widget) > 500
