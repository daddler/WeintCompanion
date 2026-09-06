"""
Die Einführung.

Zwei Sorten Fehler werden hier abgefangen, und beide sind von aussen
unsichtbar:

- **Ein Symbol, das es nicht gibt.** `QSvgRenderer` meldet einen
  fehlenden oder kaputten Pfad nicht als Fehler; `tinted_pixmap()`
  antwortet dann mit einem vollständig durchsichtigen Bild. Auf der
  Seite bleibt einfach eine Lücke - kein Absturz, keine Logzeile.
  Dieselbe Prüfung wie in `test_class_avatar.py`, aus demselben Grund.

- **Eine Tour, die stillschweigend wieder veraltet.** Genau das ist
  zwischen 1.0 und 2.8 passiert: fünf Seiten, während acht Bereiche
  dazukamen. Die Untergrenzen unten sind deshalb keine Zierde - sie
  halten fest, dass jede Gruppe der Navigationsspalte vorkommt.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")

from gui.navigation import build_page_specs  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    """
    Eine QApplication fuer die Prueflinge, die wirklich zeichnen.

    Dieselbe Bauform wie in `test_accent_follows.py`: offscreen, und
    eine bereits laufende Instanz wird weiterverwendet - eine zweite
    QApplication im selben Prozess ist ein Absturz ohne Traceback.
    """

    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication.instance() or QApplication([])

    return app


def test_every_tour_page_is_complete():

    from gui.dialogs.whats_new_dialog import TOUR_PAGES

    assert len(TOUR_PAGES) >= 15

    for page in TOUR_PAGES:

        assert page.icon
        assert page.chapter
        assert page.title
        assert len(page.body) > 120, page.title

        #
        # Ein Knopf ist entweder ganz da oder gar nicht. Ein Paar aus
        # Beschriftung und Adresse mit einer leeren Hälfte wäre ein
        # Knopf, der nirgendwohin führt.
        #

        assert len(page.action) in (0, 2)

        for part in page.action:
            assert part


def test_tour_pages_keep_their_chapter_order():
    """
    Die Kapitel stehen zusammen.

    Eine Seite, die zwischen zwei Kapitel eines dritten gerät, sieht in
    der Kopfzeile aus wie ein Sprung zurück - und die Tour hat ihre
    Gliederung genau deshalb, damit man weiss, wo man ist.
    """

    from gui.dialogs.whats_new_dialog import TOUR_PAGES

    seen: list[str] = []

    for page in TOUR_PAGES:

        if not seen or seen[-1] != page.chapter:

            assert page.chapter not in seen, page.chapter

            seen.append(page.chapter)

    assert len(seen) >= 4


def test_tour_mentions_every_navigation_group():
    """
    Kein Bereich der App bleibt unerwähnt.

    Geprüft wird über die Beschriftungen aus `build_page_specs()`, also
    über dieselbe eine Liste, aus der auch die Navigationsspalte
    entsteht - eine neue Seite fällt damit hier auf und nicht erst,
    wenn jemand sie vermisst.
    """

    from gui.dialogs.whats_new_dialog import TOUR_PAGES

    text = " ".join(
        f"{page.title} {page.body}" for page in TOUR_PAGES
    ).lower()

    missing = [
        spec.label
        for spec in build_page_specs()
        if spec.label.lower() not in text
    ]

    assert not missing, missing


def test_settings_pages_say_what_a_switch_costs():
    """
    Ein Schalter ohne Folgenangabe ist eine Frage ohne Antwort.

    Wer nicht weiss, was er sich abschaltet, lässt im Zweifel alles an
    oder alles aus — und beides ist geraten. Die Tour muss deshalb für
    die Einstellungen sagen, was das Einschalten bringt, was das
    Ausschalten kostet, und dass die Entscheidung umkehrbar ist. Das
    Letzte ist das Wichtigste: es nimmt der Frage das Endgültige.
    """

    from gui.dialogs.whats_new_dialog import TOUR_PAGES

    pages = [p for p in TOUR_PAGES if "Einstellungen" in p.title]

    assert pages, "keine Seite über die Einstellungen"

    for page in pages:

        body = page.body.lower()

        #
        # Umkehrbar - in irgendeiner der üblichen Formulierungen.
        #

        assert any(
            word in body
            for word in ("jederzeit", "wieder umlegen", "nicht endgültig")
        ), page.title

        #
        # Und beide Richtungen, nicht nur die schöne.
        #

        assert "aus " in body or "ausgeschaltet" in body, page.title

        assert "an " in body or "eingeschaltet" in body, page.title


def test_every_tour_icon_actually_draws(qt_app):

    from gui.dialogs.whats_new_dialog import TOUR_PAGES
    from gui.theme.icons import tinted_pixmap

    empty = []

    for page in TOUR_PAGES:

        image = tinted_pixmap(page.icon, "#D4A24A", 34).toImage()

        opaque = sum(
            1
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).alpha() > 0
        )

        if opaque < 20:
            empty.append(page.icon)

    assert not empty, empty


def test_emphasis_escapes_before_it_formats():
    """
    Der Fließtext geht als Rich Text ins Label.

    Ein `<` in einem Satz würde dort als Auszeichnung gelesen und
    nähme dem Label den Rest der Seite weg - stumm, wie immer bei
    Qt-Rich-Text.
    """

    from gui.dialogs.whats_new_dialog import _render_emphasis

    assert _render_emphasis("a <b> & c") == "a &lt;b&gt; &amp; c"

    assert _render_emphasis("**x** y") == "<b>x</b> y"

    #
    # Unpaarige Sterne lassen kein offenes Tag zurück: der Rest wird
    # fett, aber er wird auch wieder geschlossen. Ein offenes <b>
    # würde alles darunter mitnehmen.
    #

    unpaired = _render_emphasis("**x")

    assert unpaired.count("<b>") == unpaired.count("</b>")

    assert _render_emphasis("a\n\nb") == "a<br><br>b"


def test_skip_button_comes_back_when_paging_backwards(qt_app):
    """
    Der Ausgang bleibt erreichbar.

    Er wird auf der letzten Seite ausgeblendet (dort heisst der
    Hauptknopf ohnehin "Los geht's"). Fragte die Sichtbarkeit dabei den
    Knopf selbst statt der gespeicherten Absicht, käme er beim
    Zurückblättern nicht wieder.
    """

    from gui.dialogs.whats_new_dialog import WhatsNewDialog, _build_tour_pages

    dialog = WhatsNewDialog(
        _build_tour_pages(), finish_label="Los geht's", skippable=True
    )

    last = dialog.stack.count() - 1

    dialog.stack.setCurrentIndex(0)
    assert not dialog.skip_button.isHidden()

    dialog.stack.setCurrentIndex(last)
    assert dialog.skip_button.isHidden()

    dialog.stack.setCurrentIndex(last - 1)
    assert not dialog.skip_button.isHidden()

    dialog.deleteLater()


def test_changelog_mode_has_no_skip_button(qt_app):
    """
    Übersprungen wird die Tour, nicht das Changelog.

    Das Popup nach einem Update ist meist eine Seite lang; ein zweiter
    Knopf daneben, der dasselbe tut wie "Schließen", ist eine Wahl ohne
    Unterschied.
    """

    from gui.dialogs.whats_new_dialog import TOUR_PAGES, WhatsNewDialog

    dialog = WhatsNewDialog(
        [TOUR_PAGES[0]], finish_label="Schließen", skippable=False
    )

    assert dialog.skip_button.isHidden()

    dialog.deleteLater()


class _Config:

    def __init__(self, data):
        self.data = dict(data)
        self.saved = 0

    def save(self):
        self.saved += 1


class _Manager:

    def __init__(self, config):
        self.config = config


def _run(monkeypatch, data):
    """
    `show_whats_new_if_needed()` ohne Fenster: der Dialog wird durch
    eine Attrappe ersetzt, die nur festhält, womit sie gebaut wurde.
    """

    from gui.dialogs import whats_new_dialog as module

    calls = {}

    class _FakeDialog:

        def __init__(self, pages, finish_label="", skippable=False, parent=None):
            calls["pages"] = pages
            calls["finish"] = finish_label
            calls["skippable"] = skippable

        def exec(self):
            calls["shown"] = True

        @property
        def dont_show_again(self):
            return False

    monkeypatch.setattr(module, "WhatsNewDialog", _FakeDialog)

    config = _Config(data)

    module.show_whats_new_if_needed(_Manager(config))

    return calls, config


def test_a_long_time_user_gets_the_rewritten_tour(monkeypatch):
    """
    Der eigentliche Grund für `TOUR_EDITION`.

    Wer die App seit 1.0 benutzt, hat eine Einführung gesehen, die von
    WeintTV, der Academy, dem Archiv, Simmen und den WeakAuras nichts
    wusste - und ein Changelog-Popup holt das nicht nach.
    """

    from gui.dialogs.whats_new_dialog import TOUR_EDITION, TOUR_PAGES

    calls, config = _run(monkeypatch, {
        "whats_new_enabled": True,
        "onboarding_seen_version": "1.0.0",
        "onboarding_tour_edition": 0,
    })

    assert calls["pages"] == list(TOUR_PAGES)
    assert calls["skippable"] is True

    assert config.data["onboarding_tour_edition"] == TOUR_EDITION


def test_the_tour_is_not_repeated_afterwards(monkeypatch):

    from gui.dialogs.whats_new_dialog import TOUR_EDITION

    from core.version import VERSION

    calls, _ = _run(monkeypatch, {
        "whats_new_enabled": True,
        "onboarding_seen_version": VERSION,
        "onboarding_tour_edition": TOUR_EDITION,
    })

    assert calls == {}


def test_an_ordinary_update_still_shows_the_changelog(monkeypatch):

    from gui.dialogs.whats_new_dialog import TOUR_EDITION, TOUR_PAGES

    calls, _ = _run(monkeypatch, {
        "whats_new_enabled": True,
        "onboarding_seen_version": "0.0.1",
        "onboarding_tour_edition": TOUR_EDITION,
    })

    assert calls["pages"] != list(TOUR_PAGES)
    assert calls["skippable"] is False


def test_an_unusable_edition_counts_as_never_seen(monkeypatch):
    """
    Ein kaputter Wert in der Konfiguration darf die Einführung nicht
    verschlucken - sie noch einmal zu zeigen ist der harmlosere der
    beiden Irrtümer.
    """

    from gui.dialogs.whats_new_dialog import TOUR_PAGES

    calls, _ = _run(monkeypatch, {
        "whats_new_enabled": True,
        "onboarding_seen_version": "2.8.0",
        "onboarding_tour_edition": "kaputt",
    })

    assert calls["pages"] == list(TOUR_PAGES)
