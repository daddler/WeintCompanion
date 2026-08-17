"""
Die Seitenregistrierung ist die Stelle, an der ein Fehler am
teuersten wäre: eine verschobene Reihenfolge lenkt die
Dashboard-Karten stillschweigend auf die falschen Ziele um, ohne
dass irgendetwas abstürzt.
"""

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
    (WeintCompanion 2.0, gruppiert nach RAID / CHARAKTER / SYSTEM).
    """

    assert [page_id.name for page_id in PageId] == [
        "OVERVIEW",
        "WEINTTV",
        "ACADEMY",
        "ARCHIVE",
        "CHARACTERS",
        "PREPARATION",
        "CHARACTER_LINKS",
        "ADDON",
        "CONNECTIONS",
        "SETTINGS",
        "LOGS",
    ]


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
