"""
Die Seitenregistrierung ist die Stelle, an der ein Fehler am
teuersten wäre: eine verschobene Reihenfolge lenkt die
Dashboard-Karten stillschweigend auf die falschen Ziele um, ohne
dass irgendetwas abstürzt.
"""

import pytest

from gui.navigation import PageId


def test_page_ids_are_a_gapless_sequence_from_zero():
    """
    Die Werte SIND die Indizes im QStackedWidget. Eine Lücke oder ein
    Versatz würde bedeuten, dass eine Seite auf eine andere zeigt.
    """

    values = [int(page_id) for page_id in PageId]

    assert values == sorted(values)
    assert values == list(range(len(values)))


def test_page_ids_are_unique():

    values = [int(page_id) for page_id in PageId]

    assert len(set(values)) == len(values)


def test_expected_navigation_order():
    """
    Die vom Produkt vorgegebene Reihenfolge der Hauptbereiche
    (WeintCompanion 4.0, gruppiert nach RAID / CHARAKTER / SYSTEM).

    **RAID hat zwei Einträge, nicht vier.** WeintTV, Academy und Archiv
    waren drei gleichwertige Navigationspunkte auf denselben Pull; sie
    sind Perspektiven des Raid Centers geworden. Dass sie hier nicht
    mehr auftauchen, ist die Prüfung, dass sie nicht als drei alte
    Seiten unter einem neuen Namen weiterleben.
    """

    assert [page_id.name for page_id in PageId] == [
        "OVERVIEW",
        "RAID_CENTER",
        "CHARACTERS",
        "PREPARATION",
        "SIM",
        "WEAKAURAS",
        "CHARACTER_LINKS",
        "ADDON",
        "CONNECTIONS",
        "SETTINGS",
        "LOGS",
    ]


def test_the_raid_group_has_exactly_two_entries():
    """
    Die Zahl selbst ist die Aussage: "wo muss ich jetzt hin" entstand
    daraus, dass vier Einträge dieselbe Frage beantworteten.

    `build_page_specs()` baut die echten Seitenklassen auf - anders
    als der Rest dieser Datei also nicht Qt-frei, siehe
    `pytest.importorskip()` unten.
    """

    pytest.importorskip("PySide6")

    from gui.navigation import GROUP_RAID, build_page_specs

    raid = [spec.label for spec in build_page_specs() if spec.group == GROUP_RAID]

    assert raid == ["Übersicht", "Raid Center"]


def test_the_four_perspectives_are_keys_and_not_numbers():
    """
    Sie stehen in Tiefenverweisen. Eine 2 in einem Signal ist beim
    nächsten Umbau eine andere Ansicht als vorher.
    """

    from gui.navigation import (
        RAID_VIEW_HINTS,
        RAID_VIEW_KEYS,
        RAID_VIEW_LABELS,
    )

    assert RAID_VIEW_KEYS == ("live", "analysis", "learn", "source")

    for key in RAID_VIEW_KEYS:

        assert RAID_VIEW_LABELS[key]

        #
        # Jede Ansicht sagt in einem Satz, welche Frage man dort
        # stellt. "Live" benennt, was dahintersteckt - nicht, was man
        # dort tut.
        #

        assert len(RAID_VIEW_HINTS[key]) > 30


def test_a_raid_link_leaves_untouched_what_it_does_not_carry():
    """
    Das ist die Bedingung dafür, dass ein Perspektivwechsel den Pull
    nicht verliert: `RaidLink(view=…)` heisst "derselbe Kampf, anderer
    Blick" und nicht "irgendein Kampf".
    """

    from gui.navigation import RAID_VIEW_LEARN, RaidLink

    link = RaidLink(view=RAID_VIEW_LEARN)

    assert link.report_code == ""
    assert link.fight_id is None
    assert link.player == ""

    #
    # `seconds is None` heisst "nicht springen" und nicht "Sekunde 0" -
    # dieselbe Linie wie bei `at == -1` im Analyzer.
    #

    assert link.seconds is None

    assert not link.has_pull

    assert RaidLink(report_code="aBc", fight_id=3).has_pull

    #
    # Eine halbe Kennung kann nichts laden und darf die bestehende
    # Auswahl deshalb auch nicht verwerfen.
    #

    assert not RaidLink(report_code="aBc").has_pull
    assert not RaidLink(fight_id=3).has_pull


def test_page_id_behaves_like_int():
    """
    pageRequested ist ein Signal(int) und setCurrentIndex erwartet
    ein int - PageId muss dort ohne Umwandlung einsetzbar bleiben.
    """

    #
    # Bewusst gegen die Position in der Aufzaehlung geprueft und nicht
    # gegen eine feste Zahl: welche Reihenfolge gilt, haelt der Test
    # darueber fest. Zwei Stellen mit derselben Zahl waeren beim
    # naechsten neuen Bereich wieder auseinandergelaufen, und dieser
    # Test haette dann etwas gemeldet, mit dem er gar nichts zu tun
    # hat.
    #

    assert PageId.SETTINGS == list(PageId).index(PageId.SETTINGS)
    assert isinstance(PageId.SETTINGS, int)
