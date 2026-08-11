"""
Einstellungen -> Erscheinungsbild: die drei Wahlmöglichkeiten.

Der `ThemeManager` beherrscht Akzent, Dichte und reduzierte Bewegung
seit 2.0 vollständig - samt Speicherung in `config.json` und je einem
Signal. Zu setzen waren sie trotzdem nur im Einrichtungsassistenten
beim ersten Start; der Bereich, dessen Aufgabe das Erscheinungsbild
ist, zeigte vier Farbfelder und einen Satz. Wer den Assistenten einmal
durchlaufen hatte, kam nie wieder an die Wahl heran.

Diese Datei hält fest, dass die Bedienelemente da sind **und wirken** -
dass also nicht nur ein Schalter existiert, sondern der ThemeManager
ihm folgt und die Wahl in der Konfiguration landet.
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
        self.saves = 0

    def save(self):
        self.saves += 1


class _Manager:

    def __init__(self, config):
        self.config = config


@pytest.fixture
def section():
    """
    Ein frischer Abschnitt auf einer frischen Konfiguration.

    `init_theme()` bindet den (einzigen) ThemeManager an diese
    Konfiguration - damit prüft der Test wirklich, was gespeichert
    wird, und nicht die config.json des Rechners.
    """

    _app()

    from gui.theme import tokens
    from gui.theme.theme_manager import init_theme, theme

    config = _Config()

    init_theme(config)

    theme().set_accent(tokens.ACCENT_DEFAULT)

    theme().set_density(tokens.DENSITY_DEFAULT)

    theme().set_motion_reduced(False)

    theme().set_system_motion_reduced(False)

    from gui.pages.settings_sections.appearance import AppearanceSection

    widget = AppearanceSection(_Manager(config))

    widget.config = config

    yield widget

    widget.close()


def _click(widget):
    """
    Ein echter Mausklick: die Vorschaukarten reagieren auf
    mousePressEvent, nicht auf ein clicked-Signal.
    """

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QMouseEvent

    widget.mousePressEvent(
        QMouseEvent(
            QMouseEvent.MouseButtonPress,
            QPoint(4, 4),
            widget.mapToGlobal(QPoint(4, 4)),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
    )


def _marked(swatches) -> list[str]:
    """
    Welche Karten ihr "GEWÄHLT" zeigen.

    `isHidden()` und nicht `isVisible()`: der Abschnitt wird im Test
    nie angezeigt, und unter einem unsichtbaren Vorfahren ist
    `isVisible()` fuer JEDES Kind falsch - die Pruefung waere immer
    leer und damit wertlos. `isHidden()` fragt das Element selbst.
    """

    return [
        name
        for name, swatch in swatches.items()
        if not swatch.check.isHidden()
    ]


# --------------------------------------------------
# Es gibt überhaupt Bedienelemente
# --------------------------------------------------


def test_every_accent_variant_can_be_chosen():
    """
    Nicht drei fest verdrahtete Karten: kommt eine vierte Variante in
    die Token-Tabelle, muss sie hier von allein auftauchen.
    """

    from gui.theme import tokens

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())

    from gui.pages.settings_sections.appearance import AppearanceSection

    widget = AppearanceSection(_Manager(_Config()))

    assert set(widget.accent_swatches) == set(tokens.ACCENTS)

    widget.close()


def test_every_density_can_be_chosen(section):

    from gui.theme import tokens

    assert set(section.density_swatches) == set(tokens.DENSITY)


# --------------------------------------------------
# Sie wirken
# --------------------------------------------------


@pytest.mark.parametrize("name", ["arcane", "jade", "amber"])
def test_clicking_an_accent_applies_and_stores_it(section, name):

    from gui.theme.theme_manager import theme

    #
    # Erst auf etwas anderes stellen: `set_accent()` kehrt bei einem
    # unveränderten Wert früh zurück und speichert dann nichts - ein
    # Klick auf die ohnehin aktive Variante wäre kein Nachweis.
    #

    other = next(
        key for key in section.accent_swatches if key != name
    )

    _click(section.accent_swatches[other])

    _click(section.accent_swatches[name])

    assert theme().accent_name() == name

    assert section.config.data["accent"] == name


@pytest.mark.parametrize("name", ["compact", "comfortable"])
def test_clicking_a_density_applies_and_stores_it(section, name):

    from gui.theme.theme_manager import theme

    other = next(
        key for key in section.density_swatches if key != name
    )

    _click(section.density_swatches[other])

    _click(section.density_swatches[name])

    assert theme().density_name() == name

    assert section.config.data["density"] == name


def test_exactly_one_accent_is_marked_as_chosen(section):
    """
    Zwei Häkchen wären schlimmer als keines: der Nutzer wüsste nicht,
    was gilt.
    """

    for name in section.accent_swatches:

        _click(section.accent_swatches[name])

        assert _marked(section.accent_swatches) == [name]


def test_the_motion_switch_stores_the_choice(section):

    from gui.theme.theme_manager import theme

    section.motion_toggle.setChecked(True)

    assert theme().user_motion_reduced() is True

    assert section.config.data["motion_reduced"] is True

    section.motion_toggle.setChecked(False)

    assert theme().user_motion_reduced() is False

    assert section.config.data["motion_reduced"] is False


# --------------------------------------------------
# Die Anzeige lügt nicht
# --------------------------------------------------


def test_the_switch_shows_the_user_choice_not_the_system_default(section):
    """
    `motion_reduced()` ist die ODER-Verknüpfung mit der
    Systemvorgabe. Zeigte der Schalter sie, stünde er bei gesetzter
    Systemvorgabe auf "ein", und ein Klick darauf änderte sichtbar
    nichts - er sähe kaputt aus. Ein Hinweis darunter erklärt die
    Lage stattdessen.
    """

    from gui.theme.theme_manager import theme

    theme().set_motion_reduced(False)

    theme().set_system_motion_reduced(True)

    section.refresh()

    assert theme().motion_reduced() is True

    assert section.motion_toggle.isChecked() is False

    assert section.motion_hint.isHidden() is False

    theme().set_system_motion_reduced(False)

    section.refresh()

    assert section.motion_hint.isHidden() is True


def test_the_palette_follows_the_accent(section):
    """
    Die beiden Akzentfelder standen vorher auf `Colors.PRIMARY` - dem
    statischen Bernstein des Übergangsmoduls. Auf genau der Seite, auf
    der man den Akzent wechselt, blieb die Vorschau damit falsch.
    """

    from gui.theme import tokens
    from gui.theme.theme_manager import theme

    seen = set()

    for name, variant in tokens.ACCENTS.items():

        theme().set_accent(name)

        sheets = tuple(s.styleSheet() for s in section._palette)

        seen.add(sheets)

        #
        # Nicht nur "es ändert sich", sondern der richtige Ton.
        #

        assert variant["base"] in sheets[2]

        assert variant["light"] in sheets[3]

    assert len(seen) == len(tokens.ACCENTS)


def test_a_theme_change_from_elsewhere_updates_the_section(section):
    """
    Der Assistent setzt denselben ThemeManager. Änderte er den Akzent,
    während dieser Bereich schon gebaut ist, müsste die Markierung
    mitgehen - sonst zeigt die Seite eine Wahl, die nicht mehr gilt.
    """

    from gui.theme.theme_manager import theme

    theme().set_accent("jade")

    assert _marked(section.accent_swatches) == ["jade"]


def test_switching_the_theme_does_not_multiply_connections(section):
    """
    CLAUDE.md: im Konstruktor verbinden, nie im Handler, den sie
    auslöst. `refresh()` hängt hier an allen drei Signalen - baute es
    die Verbindung selbst auf, wüchse sie mit jedem Wechsel.
    """

    from gui.theme import tokens
    from gui.theme.theme_manager import theme

    manager = theme()

    signals = (
        "2accent_changed(QString)",
        "2density_changed(QString)",
        "2motion_changed(bool)",
    )

    before = tuple(manager.receivers(s) for s in signals)

    for _ in range(4):

        for name in tokens.ACCENTS:
            manager.set_accent(name)

        for name in tokens.DENSITY:
            manager.set_density(name)

        for reduced in (True, False):
            manager.set_motion_reduced(reduced)

    assert tuple(manager.receivers(s) for s in signals) == before
