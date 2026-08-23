"""
Folgen die akzenttragenden Bausteine einem Akzentwechsel?

Der Entwurf lässt den Nutzer zwischen drei Akzentvarianten wählen
(Bernstein, Arkan, Jade). CLAUDE.md nennt den Fehler, der dabei
entsteht, ausdrücklich: eine Farbe, die beim Bauen gelesen wird,
überlebt den Wechsel, und das Widget behält die alte - **lautlos**,
denn nichts wirft eine Ausnahme.

Zwei Bausteine taten genau das. Beide lasen aus
`gui/theme/colors.py`, dem Übergangsmodul, dessen Werte laut seinem
eigenen Modulkommentar statisch sind und deshalb auf Bernstein stehen
bleiben:

- `HeroButton` - der Hauptknopf der Anwendung, in dreizehn Modulen
  benutzt ("Speichern", "Trennen", "Wiedergabe", "Tour anzeigen", ...).
  Er setzte seine Stylesheet einmal im Konstruktor.
- `MeterBar` - die Balken der WeintTV-Ranglisten. Er liest im
  paintEvent, aber aus der statischen Tabelle.

Geprüft wird nicht die Farbe selbst, sondern dass sich das **gerenderte
Bild** zwischen den Varianten unterscheidet. Eine Zusicherung auf einen
Hex-Wert würde bei jeder Anpassung der Token brechen, ohne dass etwas
kaputt wäre; "es ändert sich überhaupt" ist die Eigenschaft, um die es
geht.
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


def _render(widget) -> bytes:

    from PySide6.QtCore import QSize
    from PySide6.QtGui import QImage

    widget.resize(
        widget.sizeHint().expandedTo(QSize(160, 40))
    )

    image = QImage(widget.size(), QImage.Format_ARGB32)

    image.fill(0)

    widget.render(image)

    return bytes(image.constBits())


def _images_per_accent(build):
    """
    `build` liefert ein frisches Widget. Es wird EINMAL gebaut und
    dann unter jeder Akzentvariante gezeichnet - genau die Lage, um
    die es geht: ein bereits bestehendes Widget muss dem Wechsel
    folgen.
    """

    _app()

    from gui.theme import tokens
    from gui.theme.theme_manager import init_theme, theme

    init_theme(_Config())

    widget = build()

    widget.show()

    images = {}

    for name in tokens.ACCENTS:

        theme().set_accent(name)

        widget.update()

        #
        # Die Signale von set_accent() werden direkt zugestellt
        # (gleicher Thread), ein Durchlauf der Ereignisschlange
        # genügt, damit ein angefordertes Neuzeichnen greift.
        #

        _app().processEvents()

        images[name] = _render(widget)

    theme().set_accent(tokens.ACCENT_DEFAULT)

    widget.close()

    return images


# --------------------------------------------------


def test_hero_button_follows_the_accent():

    from gui.widgets.hero_banner import HeroButton

    images = _images_per_accent(
        lambda: HeroButton("Speichern")
    )

    assert len(set(images.values())) == len(images), (
        "Der Hauptknopf bleibt bernsteinfarben, obwohl eine andere "
        "Akzentvariante gewählt ist."
    )


def test_meter_bar_follows_the_accent():

    from gui.widgets.tv.meter_bar import MeterBar

    def build():
        bar = MeterBar()
        bar.setValue(0.7)
        return bar

    images = _images_per_accent(build)

    assert len(set(images.values())) == len(images), (
        "Die Ranglisten-Balken bleiben bernsteinfarben."
    )


def test_the_roster_strip_follows_the_accent():
    """
    Ein zugesagter Platz ohne gemeldete Klasse trägt die Akzentfarbe.
    Gelesen wird sie im `paintEvent` - im Konstruktor gelesen bliebe
    der Streifen bernsteinfarben, und zwar lautlos.
    """

    from gui.widgets.roster_strip import RosterStrip, SlotGroup

    def build():

        strip = RosterStrip()

        strip.setGroups([SlotGroup("ZUGESAGT", [""] * 8, 4)])

        return strip

    images = _images_per_accent(build)

    assert len(set(images.values())) == len(images), (
        "Die Plätze der Aufstellung bleiben bernsteinfarben."
    )


def test_a_class_coloured_slot_ignores_the_accent():
    """
    Die Gegenprobe: eine gemeldete Klasse hat ihre eigene Farbe, und
    die ist keine Frage des Themas. Änderte sie sich mit, wäre die
    Klassenfarbe nur Zierde.
    """

    from gui.widgets.roster_strip import RosterStrip, SlotGroup

    def build():

        strip = RosterStrip()

        strip.setGroups([SlotGroup("", ["Mage"] * 8, 0)])

        return strip

    images = _images_per_accent(build)

    assert len(set(images.values())) == 1


def test_a_secondary_hero_button_carries_no_accent():
    """
    Die Gegenprobe: der Zweitknopf ist bewusst neutral. Änderte auch
    er sich, wäre die Akzentfarbe an eine Fläche geraten, die sie laut
    Entwurf nicht tragen soll - und der Test oben würde nur beweisen,
    dass sich irgendetwas ändert.
    """

    from gui.widgets.hero_banner import HeroButton

    images = _images_per_accent(
        lambda: HeroButton("Changelog", primary=False)
    )

    assert len(set(images.values())) == 1


def test_the_on_accent_text_colour_comes_from_the_variant():
    """
    Jade ist heller als Bernstein und verlangt eine dunkle Schrift.
    Vorher stand hier hart `color:white`, also weißer Text auf einer
    hellen Fläche.
    """

    _app()

    from gui.theme import tokens
    from gui.theme.theme_manager import init_theme, theme

    init_theme(_Config())

    from gui.widgets.hero_banner import HeroButton

    button = HeroButton("Speichern")

    for name, variant in tokens.ACCENTS.items():

        theme().set_accent(name)

        sheet = button.styleSheet()

        assert f"color:{variant['onBase']}" in sheet, (
            f"Akzent {name}: die Schriftfarbe auf der Akzentfläche "
            f"stammt nicht aus der Variante."
        )

    theme().set_accent(tokens.ACCENT_DEFAULT)


def test_the_accent_connection_is_not_doubled():
    """
    CLAUDE.md: im Konstruktor verbinden, nie im Handler, den sie
    auslöst - sonst verdoppelt sich die Verbindung bei jedem Wechsel
    (gemessen 1, 2, 4, 8, 16). Das sieht nie wie ein Fehler aus, nur
    wie eine langsamer werdende Anwendung.
    """

    _app()

    from PySide6.QtCore import QMetaMethod

    from gui.theme import tokens
    from gui.theme.theme_manager import init_theme, theme

    init_theme(_Config())

    from gui.widgets.hero_banner import HeroButton

    button = HeroButton("Speichern")

    manager = theme()

    meta = manager.metaObject()

    index = meta.indexOfSignal("accent_changed(QString)")

    assert index >= 0

    method = meta.method(index)

    def receivers() -> int:
        return manager.receivers("2accent_changed(QString)")

    before = receivers()

    for name in list(tokens.ACCENTS) * 3:
        manager.set_accent(name)

    manager.set_accent(tokens.ACCENT_DEFAULT)

    assert receivers() == before, (
        "Die Zahl der Empfänger von accent_changed ist gewachsen - "
        "eine Verbindung wird im Handler aufgebaut."
    )

    assert isinstance(method, QMetaMethod)

    button.close()


def test_the_update_row_follows_the_accent():
    """
    Der Update-Hinweis auf der Übersicht ist seit 2.3.6 gemalt statt
    gestylt: Leiste, getönte Fläche und Rahmen in Akzentfarbe. Genau
    dort entsteht der Fehler, den CLAUDE.md beschreibt - eine im
    Konstruktor gelesene Farbe überlebt den Wechsel, und die Zeile
    bleibt bernsteinfarben, ohne dass irgendetwas fehlschlägt.

    Die Symbolkachel gehört mit dazu: sie ist eine **Pixmap** und
    macht einen Akzentwechsel deshalb nicht durch bloßes Neuzeichnen
    mit, sondern nur, wenn sie neu eingefärbt wird.
    """

    from gui.pages.overview import UpdateRow

    def build():

        row = UpdateRow("addon")

        row.apply("WeintCodex", "v2.3.1.0", "v2.4.0.0", "Behoben.")

        return row

    images = _images_per_accent(build)

    assert len(set(images.values())) == len(images), (
        "Die Update-Zeile bleibt bernsteinfarben, obwohl eine andere "
        "Akzentvariante gewählt ist."
    )
