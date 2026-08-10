"""
Charakternamen vergleichen.

Die drei Regeln aus `analyzer/names.py` stehen hier als Test, weil
jede von ihnen ein Urteil ist und nicht aus dem Code folgt - und
weil ihr Bruch sich in der Oberfläche nicht als Fehler zeigt,
sondern als "dieser Spieler war wohl nicht im Raid".

Dieselben Regeln stehen im Addon in `core/names.lua`. Weicht eine
Seite ab, ist "ich" im Spiel jemand anderes als "ich" auf dem
Desktop - genau der Fehler, wegen dem diese Datei existiert.
"""

from analyzer.names import (
    match_name,
    names_equal,
    normalize_name,
    split_name,
)


# --------------------------------------------------
# split_name
# --------------------------------------------------


def test_ein_nackter_name_hat_keinen_realm():

    assert split_name("Aldrin") == ("Aldrin", "")


def test_getrennt_wird_am_ersten_bindestrich():
    """
    Realmnamen dürfen Bindestriche enthalten, Charakternamen nicht.
    """

    assert split_name("Aldrin-Kirin-Tor") == ("Aldrin", "Kirin-Tor")


def test_leerzeichen_im_realm_verschwinden():
    """
    GetRealmName() liefert "Die Aldor", WarcraftLogs "DieAldor".
    """

    assert split_name("Aldrin-Die Aldor") == ("Aldrin", "DieAldor")


def test_nichts_ergibt_zwei_leere_zeichenketten():

    assert split_name(None) == ("", "")
    assert split_name("") == ("", "")
    assert split_name("   ") == ("", "")
    assert split_name(42) == ("", "")


# --------------------------------------------------
# normalize_name
# --------------------------------------------------


def test_die_vergleichsform_kennt_weder_realm_noch_grossschreibung():

    assert normalize_name("Aldrin-Everlook") == "aldrin"
    assert normalize_name("ALDRIN") == "aldrin"


def test_umlaute_ueberleben_die_vergleichsform():
    """
    Ein deutscher Charaktername darf nicht daran scheitern, dass er
    Umlaute hat - casefold() muss beide Seiten gleich behandeln.
    """

    assert normalize_name("Wéintbär") == normalize_name("WÉINTBÄR")


# --------------------------------------------------
# names_equal
# --------------------------------------------------


def test_gleicher_name_verschiedene_schreibung():

    assert names_equal("Aldrin", "aldrin")


def test_ein_fehlender_realm_ist_ein_platzhalter():
    """
    Regel 3, und die wichtigste: der Client kennt nur den nackten
    Namen, WarcraftLogs qualifiziert nur realmfremde Zeilen. Wären
    diese beiden ungleich, fände "Nur ich" nie etwas.
    """

    assert names_equal("Aldrin", "Aldrin-Everlook")
    assert names_equal("Aldrin-Everlook", "Aldrin")


def test_zwei_genannte_realms_muessen_zusammenpassen():

    assert names_equal("Aldrin-Everlook", "Aldrin-Everlook")
    assert not names_equal("Aldrin-Everlook", "Aldrin-Blackrock")


def test_verschiedene_namen_bleiben_verschieden():

    assert not names_equal("Aldrin", "Bordrin")


def test_ohne_namen_kein_treffer():
    """
    Zwei leere Namen sind nicht "derselbe Charakter", sondern gar
    keiner. Andernfalls würde ein fehlendes Feld auf beiden Seiten
    als Übereinstimmung durchgehen.
    """

    assert not names_equal("", "")
    assert not names_equal(None, "Aldrin")


# --------------------------------------------------
# match_name
# --------------------------------------------------


def test_der_treffer_kommt_in_der_schreibweise_des_rosters():
    """
    Der eigentliche Zweck: gespeichert werden muss, wie der Bericht
    schreibt, nicht wie das Spiel schreibt - sonst findet
    find_actor() den Spieler beim nächsten Mal nicht mehr.
    """

    roster = ("Aldrin-Everlook", "Bordrin")

    assert match_name("aldrin", roster) == "Aldrin-Everlook"


def test_exakte_treffer_gewinnen_vor_normalisierten():
    """
    Stünden beide Schreibweisen im Roster, entschiede sonst die
    Reihenfolge der Liste.
    """

    roster = ("Aldrin-Everlook", "Aldrin")

    assert match_name("Aldrin", roster) == "Aldrin"


def test_kein_treffer_ist_none_und_nicht_der_suchbegriff():

    assert match_name("Aldrin", ("Bordrin", "Cendrin")) is None
    assert match_name("Aldrin", ()) is None
    assert match_name("", ("Aldrin",)) is None


def test_nicht_zeichenketten_im_roster_stoeren_nicht():
    """
    Die Rosterliste kommt aus einem Bericht; ein defektes Feld darf
    die Suche nicht abbrechen lassen.
    """

    assert match_name("Aldrin", (None, 7, "Aldrin")) == "Aldrin"
