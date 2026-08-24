"""
Sieht der Nutzer ein wartendes Update, ohne danach zu suchen?

Der 2.0-Umbau hat die Update-Anzeige aus einem Dashboard mit Hero-Banner
in zwei getrennte Orte verlegt: die Systemzeile der Übersicht und die
Seite "Addon & Updates". Zwei Dinge gingen dabei verloren.

**Die Übersicht zeigte den Stand von vor der Prüfung.** `refresh()`
hing ausschliesslich am Seitenwechsel, `full_refresh()` läuft aber in
einem Hintergrund-Thread und ist rund eine Sekunde NACH dem Zeichnen
der Übersicht fertig. Ein gefundenes Update war deshalb praktisch nie
beim ersten Hinsehen da - erst wer die Seite verliess und erneut
betrat, sah es. Deshalb gibt es `CompanionManager.state_changed`.

**Aussterhalb der Übersicht gab es keinen Hinweis.** `NavItem.setBadge()`
existierte seit 2.0 und wurde von niemandem aufgerufen: wer in WeintTV
oder der Academy sass, erfuhr nichts.

Geprüft wird beides plus die Bewegung der Systemzeile
(`motion.expand`), die vorher von 44 auf 132 px sprang.
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


def _pump(ms: int = 60):

    from PySide6.QtCore import QDeadlineTimer, QEventLoop

    app = _app()

    deadline = QDeadlineTimer(ms)

    while not deadline.hasExpired():
        app.processEvents(QEventLoop.AllEvents, 4)


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


class _State:
    """
    Nur die Felder, welche die Systemzeile und das Abzeichen lesen.
    """

    def __init__(self):
        self.addon_found = True
        self.addon_version = "1.7.0"
        self.github_version = "1.7.0"
        self.update_available = False
        self.companion_version = "2.0.0"
        self.companion_latest_version = "2.0.0"
        self.companion_update_available = False
        self.discord_connected = True
        self.discord_name = "Tester"


class _Manager:

    def __init__(self):
        self.state = _State()
        self.config = _Config()
        self.logger = _Logger()


@pytest.fixture
def row():

    _app()

    from gui.theme.theme_manager import init_theme, theme

    init_theme(_Config())

    theme().set_motion_reduced(False)

    theme().set_system_motion_reduced(False)

    from gui.pages.overview import SystemRow

    manager = _Manager()

    widget = SystemRow(manager)

    widget.manager = manager

    widget.refresh()

    _pump(300)

    yield widget

    widget.close()


# --------------------------------------------------
# Die Systemzeile
# --------------------------------------------------


def _dots(row) -> dict:

    return {
        key: dot.state()
        for key, (dot, _label) in row.entries.items()
    }


def test_without_updates_the_row_stays_closed(row):
    """
    Vier grüne Punkte sind eine Auskunft und brauchen keinen Platz.
    """

    assert _dots(row)["addon"] == "ok"

    assert _dots(row)["app"] == "ok"

    assert row.height() == row.COLLAPSED

    assert row.action.isHidden()


def test_an_addon_update_opens_the_row_and_offers_a_way_there(row):

    row.manager.state.update_available = True

    row.manager.state.github_version = "1.8.0"

    row.refresh()

    _pump(400)

    assert _dots(row)["addon"] == "warn"

    assert row.height() == row.EXPANDED

    assert not row.action.isHidden()

    assert "1.8.0" in row.detail_rows["addon"].text()


def test_a_companion_update_opens_the_row_too(row):
    """
    Der zweite, unabhängige Update-Kanal. Er darf nicht davon
    abhängen, dass auch das Addon eines hat.
    """

    row.manager.state.companion_update_available = True

    row.manager.state.companion_latest_version = "2.1.0"

    row.refresh()

    _pump(400)

    assert _dots(row)["app"] == "warn"

    assert row.height() == row.EXPANDED

    assert "2.1.0" in row.detail_rows["app"].text()


def test_the_row_closes_again_once_everything_is_current(row):

    row.manager.state.update_available = True

    row.refresh()

    _pump(400)

    assert row.height() == row.EXPANDED

    row.manager.state.update_available = False

    row.refresh()

    _pump(400)

    assert row.height() == row.COLLAPSED

    assert row.details.isHidden()


def test_opening_the_row_is_animated(row):
    """
    `motion.expand` ist für genau diese Zeile gedacht und war
    unbenutzt - die Höhe sprang von 44 auf 132. Der Auslöser ist meist
    eine Prüfung, die im Hintergrund fertig wird, also kein Klick: ohne
    Bewegung sieht es aus, als hätte die Seite gezuckt.
    """

    row.manager.state.update_available = True

    row.refresh()

    seen = set()

    for _ in range(12):
        _pump(20)
        seen.add(row.height())

    _pump(400)

    between = {
        height
        for height in seen
        if row.COLLAPSED < height < row.EXPANDED
    }

    assert between, (
        f"Keine Zwischenhöhen beobachtet ({sorted(seen)}) - die Zeile "
        f"springt statt zu wachsen."
    )

    assert row.height() == row.EXPANDED


def test_reduced_motion_sets_the_height_instead_of_animating(row):
    """
    "Bewegung reduzieren" ist eine Abschaltung, keine Abschwächung.
    Der Endzustand muss trotzdem stimmen - eine Zeile, die auf halber
    Höhe stehen bleibt, wäre schlimmer als eine Animation.
    """

    from gui.theme.theme_manager import theme

    theme().set_motion_reduced(True)

    try:

        row.manager.state.update_available = True

        row.refresh()

        _pump(20)

        assert row.height() == row.EXPANDED

        assert not row.details.isHidden()

        row.manager.state.update_available = False

        row.refresh()

        _pump(20)

        assert row.height() == row.COLLAPSED

        assert row.details.isHidden()

    finally:

        theme().set_motion_reduced(False)


# --------------------------------------------------
# Das Abzeichen in der Navigationsspalte
# --------------------------------------------------


@pytest.fixture
def nav():

    _app()

    from gui.theme.theme_manager import init_theme

    init_theme(_Config())

    from gui.navigation import build_page_specs
    from gui.widgets.nav_column import NavColumn

    manager = _Manager()

    #
    # NavColumn liest beim Zeichnen das verknüpfte Discord-Konto.
    #

    class _Store:
        def load(self):
            return None

    manager.discord_account = _Store()

    widget = NavColumn(manager, build_page_specs())

    widget.manager = manager

    yield widget

    widget.close()


def _badge(nav):

    from gui.navigation import PageId

    item = nav.items[int(PageId.ADDON)]

    return (
        not item.badge_dot.isHidden(),
        item.badge_text.text(),
    )


def test_no_badge_while_everything_is_current(nav):

    nav.refresh()

    assert _badge(nav) == (False, "")


def test_one_update_shows_a_one(nav):

    nav.manager.state.update_available = True

    nav.refresh()

    assert _badge(nav) == (True, "1")


def test_both_channels_show_a_two(nav):
    """
    Eine Zahl und kein Punkt, weil es zwei unabhängige Kanäle gibt und
    "2" die Nachfrage erspart, ob beide gemeint sind.
    """

    nav.manager.state.update_available = True

    nav.manager.state.companion_update_available = True

    nav.refresh()

    assert _badge(nav) == (True, "2")


def test_the_badge_disappears_again(nav):

    nav.manager.state.update_available = True

    nav.refresh()

    assert _badge(nav)[0] is True

    nav.manager.state.update_available = False

    nav.refresh()

    assert _badge(nav) == (False, "")


def test_a_missing_addon_is_not_counted_as_an_update(nav):
    """
    Ohne installiertes Addon steht die **Installation** aus, und das
    sagt die Systemzeile mit eigenem Wortlaut. Ein Abzeichen "1"
    behauptete eine Aktualisierung, wo noch nichts installiert ist.
    """

    nav.manager.state.addon_found = False

    nav.manager.state.update_available = False

    nav.refresh()

    assert _badge(nav) == (False, "")


# --------------------------------------------------
# Das Signal, das beides auslöst
# --------------------------------------------------


def test_full_refresh_reports_even_when_a_step_fails():
    """
    Die vorherigen Schritte haben den Zustand schon verändert. Eine
    halb aktualisierte Anzeige ist besser als eine, die auf dem Stand
    von vor der Prüfung stehen bleibt - und ohne das Signal bliebe sie
    genau dort.
    """

    pytest.importorskip("httpx")

    _app()

    from core.companion_manager import CompanionManager

    seen = []

    manager = CompanionManager.__new__(CompanionManager)

    #
    # QObject-Teil von Hand hochziehen: der echte Konstruktor baut ein
    # Dutzend Dienste, von denen hier keiner gebraucht wird.
    #

    from PySide6.QtCore import QObject

    QObject.__init__(manager)

    manager.logger = _Logger()

    manager.state_changed.connect(lambda: seen.append(True))

    def boom():
        raise RuntimeError("GitHub nicht erreichbar")

    manager.detect_wow = lambda: None
    manager.detect_addon = lambda: None
    manager.check_github = boom
    manager.check_discord = lambda: None

    with pytest.raises(RuntimeError):
        manager.full_refresh()

    assert seen == [True], (
        "state_changed wurde nicht gemeldet - die Oberflaeche bliebe "
        "auf dem Stand von vor der Pruefung."
    )


# --------------------------------------------------
# Die Rueckkopplung, die das Signal offengelegt hat
# --------------------------------------------------


def test_a_page_refresh_cannot_retrigger_the_refresh():
    """
    Eine Seite, deren `refresh()` selbst eine Prüfung anstösst,
    schliesst einen Kreis: die Prüfung meldet ihren Zustand, das
    Fenster zeichnet die Seite, die Seite prüft wieder.

    `ConnectionsPage.refresh()` tat genau das (ein blockierendes
    `full_refresh()`) und lief bis zur Rekursionsgrenze - gemessen 826
    GitHub-Abfragen in einem Durchlauf, der sonst sieben braucht.

    Geprüft wird die Sperre selbst, ohne ein Fenster zu bauen: der
    Slot wird ungebunden auf einem Doppel aufgerufen, dessen
    Zeichenschritt den Slot erneut aufruft.
    """

    from gui.main_window import MainWindow

    class _Reentrant:

        def __init__(self):
            self._refreshing_state = False
            self.draws = 0

        def _refresh_after_state_change(self):

            self.draws += 1

            #
            # Das, was ConnectionsPage.refresh() ausgelöst hat.
            #

            MainWindow._on_state_changed(self)

    stub = _Reentrant()

    MainWindow._on_state_changed(stub)

    assert stub.draws == 1, (
        f"Der Slot ist {stub.draws}-mal durchgelaufen - die "
        f"Wiedereintrittssperre greift nicht."
    )

    #
    # Und danach wieder offen, sonst käme nach dem ersten Kreis nie
    # mehr eine Aktualisierung an.
    #

    assert stub._refreshing_state is False

    MainWindow._on_state_changed(stub)

    assert stub.draws == 2


def test_no_page_refresh_starts_a_network_round():
    """
    `refresh()` zeichnet. `change_page()` ruft es bei jedem Betreten
    auf, und der Konstruktor der Seite gleich mit - ein
    `full_refresh()` darin hiess: das Fenster steht, sobald man die
    Seite öffnet, und zwar blockierend im Hauptthread.

    Ein Textvergleich, weil er den Fehler dort zeigt, wo er gemacht
    wird, und für jede künftige Seite gilt.
    """

    import ast
    import pathlib

    pages = pathlib.Path(__file__).resolve().parent.parent / "gui" / "pages"

    offenders = []

    for path in sorted(pages.rglob("*.py")):

        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            if node.name != "refresh":
                continue

            for inner in ast.walk(node):

                if not isinstance(inner, ast.Call):
                    continue

                target = inner.func

                if (
                    isinstance(target, ast.Attribute)
                    and target.attr in (
                        "full_refresh",
                        "refresh_update_status",
                    )
                ):

                    offenders.append(
                        f"{path.name}:{inner.lineno} -> {target.attr}()"
                    )

    assert not offenders, (
        "refresh() darf keine Prüfung anstossen - das blockiert den "
        "Hauptthread und schliesst mit state_changed einen Kreis:\n  "
        + "\n  ".join(offenders)
    )


# --------------------------------------------------
# Der atmende Ring der Update-Karte
# --------------------------------------------------
#
# Seit 2.4.0 trägt die Karte einen Ring in Akzentfarbe, dessen
# Deckkraft an der Pulsuhr hängt. Zwei Eigenschaften davon sind auf dem
# Bildschirm nicht zu sehen und deshalb genau die, die hier stehen.


@pytest.fixture
def card():

    _app()

    from gui.theme.theme_manager import init_theme, theme

    init_theme(_Config())

    theme().set_motion_reduced(False)

    theme().set_system_motion_reduced(False)

    from gui.pages.overview import UpdateCard

    widget = UpdateCard()

    yield widget

    widget.close()


def _warn_subscribers() -> int:
    """
    Wie viele sichtbare Warnquellen die Uhr gerade zählt.

    Der Zähler ist privat und hat keinen öffentlichen Weg nach draussen -
    gefragt ist hier aber genau die Differenz "einer mehr / einer
    weniger", und `active_kind()` beantwortet sie nicht: es meldet
    "warn", solange irgendein anderer Punkt noch angemeldet ist.
    """

    from gui.motion.pulse_clock import KIND_WARN, pulse_clock

    return pulse_clock()._counts[KIND_WARN]


def test_the_card_only_pulses_while_it_is_visible(card):
    """
    Angemeldet wird bei der Sichtbarkeit, nicht beim Bauen.

    Die Karte entsteht auf **jeder** Übersicht, gezeigt wird sie nur,
    wenn wirklich etwas aussteht. Eine Anmeldung im Konstruktor hielte
    die Uhr dauerhaft am Laufen: ein Zeitgeber mit 16 ms, der ins Leere
    tickt, weckt den Prozess sechzig Mal je Sekunde - neben einem
    Vollbildspiel.
    """

    before = _warn_subscribers()

    assert not card._pulsing, (
        "Die gebaute, aber nie gezeigte Karte hängt schon an der Uhr."
    )

    card.show()

    _pump(30)

    assert card._pulsing

    #
    # Mehr als eine: der Punkt im Chip meldet sich ebenfalls an. Genau
    # deshalb liest der Ring die Uhr mit, statt sich einen zweiten
    # Zeitgeber zu bestellen - zwei eigene Uhren liefen gegeneinander.
    #

    assert _warn_subscribers() > before

    card.hide()

    _pump(30)

    assert not card._pulsing

    assert _warn_subscribers() == before, (
        "Die verborgene Update-Karte bleibt bei der Pulsuhr "
        "angemeldet - die Uhr tickt dann für niemanden weiter."
    )


def test_an_already_counted_card_is_not_counted_twice(card):
    """
    `close()` erzeugt auf manchen Plattformen ein zweites Verbergen,
    und eine Karte wird beim Seitenwechsel mehrfach ein- und
    ausgeblendet. Ein doppelt gezählter Abgang drückte den Zähler unter
    die Zahl der echten Quellen und stellte die Uhr still, während
    anderswo noch etwas pulst - dieselbe Falle wie beim doppelten
    `detach()` des Overlay-Fensters.
    """

    before = _warn_subscribers()

    card._claim()

    counted = _warn_subscribers()

    assert counted == before + 1

    card._claim()

    assert _warn_subscribers() == counted, (
        "Eine zweite Anmeldung wird mitgezählt."
    )

    card._release()

    assert _warn_subscribers() == before

    card._release()

    assert _warn_subscribers() == before, (
        "Eine zweite Abmeldung zählt den Zähler unter die Zahl der "
        "wirklich sichtbaren Quellen."
    )


def test_a_standing_ring_stands_at_full_strength():
    """
    Bei reduzierter Bewegung und bei einem sichtbaren LIVE-Zeichen
    steht die Uhr, und `opacity()` liefert dauerhaft 1.0. Der Ring muss
    dann in **voller** Stärke stehenbleiben.

    Der Hinweis verschwindet also nicht, er hört nur auf, sich zu
    bewegen - dieselbe Linie, die den LIVE-Punkt bei reduzierter
    Bewegung zum Quadrat macht statt ihn auszublenden. Ein
    stehengebliebener, halb sichtbarer Ring wäre von einem
    Zeichenfehler nicht zu unterscheiden.
    """

    from gui.motion.pulse_clock import OPACITY_LOW
    from gui.pages.overview import (
        RING_ALPHA_MAX,
        RING_ALPHA_MIN,
        ring_strength,
    )

    assert ring_strength(1.0) == pytest.approx(RING_ALPHA_MAX)

    assert ring_strength(OPACITY_LOW) == pytest.approx(RING_ALPHA_MIN)

    assert RING_ALPHA_MIN < ring_strength(0.7) < RING_ALPHA_MAX


def test_reduced_motion_stops_the_ring_without_dimming_it(card):
    """
    Und zwar auch dann, wenn die Einstellung umgelegt wird, **während**
    die Karte auf dem Schirm steht.

    Die Pulsuhr entscheidet über ihren Zeitgeber nur beim An- und
    Abmelden; wer den Schalter in Einstellungen -> Erscheinungsbild
    umlegt, meldet sich dabei weder an noch ab. Die Uhr läuft also
    weiter, und ein Ring, der sich allein auf sie verliesse, atmete
    genau bei der Einstellung weiter, die das untersagt. Deshalb fragt
    `ring_alpha()` selbst - so wie es der `StatusDot` in seinem
    `paintEvent` tut.
    """

    from gui.pages.overview import RING_ALPHA_MAX, ring_alpha
    from gui.theme.theme_manager import theme

    card.show()

    _pump(40)

    theme().set_motion_reduced(True)

    try:
        assert ring_alpha() == pytest.approx(RING_ALPHA_MAX), (
            "Bei reduzierter Bewegung steht der Ring in einem "
            "Zwischenwert - er sieht dann aus wie ein Zeichenfehler."
        )

    finally:
        theme().set_motion_reduced(False)
