"""
`check_client_folder` entscheidet, ob ein vom Nutzer gewählter Ordner
die Installation einer Spielversion ist - sowohl für Einstellungen →
WoW-Client als auch für die Einrichtung (§6.6). Beide müssen dieselbe
Antwort geben, deshalb die eine gemeinsame Funktion.

Der zweite Gegenstand dieser Datei ist der Fall, für den sie 4.1
umgebaut wurde: eine Spielversion, deren **Ordnername noch nicht
bekannt ist** (Forever). Dort entscheiden allein die Kennzeichen einer
Installation - und genau dann darf nicht geraten werden.
"""

from core.wow_clients import FOREVER, MOP_CLASSIC, WowClient
from core.wow_folder import check_client_folder, resolve_client_folder


def _make_installation(base, name):

    folder = base / name

    (folder / "Interface" / "AddOns").mkdir(parents=True)

    (folder / "WTF").mkdir(parents=True)

    return folder


def _make_classic_folder(base):

    return _make_installation(base, "_classic_")


# --------------------------------------------------
# Bekannter Ordnername (MoP Classic)
# --------------------------------------------------


def test_a_direct_classic_folder_resolves_to_itself(tmp_path):

    folder = _make_classic_folder(tmp_path)

    assert resolve_client_folder(folder, MOP_CLASSIC) == folder


def test_the_battle_net_root_resolves_to_its_classic_subfolder(tmp_path):
    """
    Die meisten Nutzer wählen im Dateidialog die Wurzel
    "World of Warcraft", nicht den _classic_-Unterordner selbst.
    """

    root = tmp_path / "World of Warcraft"

    classic = _make_classic_folder(root)

    assert resolve_client_folder(root, MOP_CLASSIC) == classic


def test_the_known_name_wins_over_a_sibling_installation(tmp_path):
    """
    Wer beide Spielversionen installiert hat, soll bei MoP Classic
    `_classic_` bekommen - und nicht den Ordner, der alphabetisch
    zuerst kommt.
    """

    root = tmp_path / "World of Warcraft"

    classic = _make_classic_folder(root)

    _make_installation(root, "_retail_")

    assert resolve_client_folder(root, MOP_CLASSIC) == classic


def test_an_unrelated_folder_is_rejected(tmp_path):

    empty = tmp_path / "Downloads"

    empty.mkdir()

    check = check_client_folder(empty, MOP_CLASSIC)

    assert not check.ok

    assert "Interface/AddOns" in check.reason


def test_a_folder_missing_only_wtf_is_rejected(tmp_path):
    """
    Alle drei Kennzeichen müssen vorliegen - ein halb entpacktes oder
    fremdes Verzeichnis darf nicht als Installation durchgehen.
    """

    folder = tmp_path / "_classic_"

    (folder / "Interface" / "AddOns").mkdir(parents=True)

    assert resolve_client_folder(folder, MOP_CLASSIC) is None


def test_accepts_a_string_path_too(tmp_path):

    folder = _make_classic_folder(tmp_path)

    assert resolve_client_folder(str(folder), MOP_CLASSIC) == folder


def test_a_folder_that_does_not_exist_says_so(tmp_path):

    check = check_client_folder(tmp_path / "gibt-es-nicht", MOP_CLASSIC)

    assert not check.ok

    assert "gibt es nicht" in check.reason


# --------------------------------------------------
# Unbekannter Ordnername (Forever)
# --------------------------------------------------


def test_an_unknown_folder_name_is_found_by_its_markers(tmp_path):
    """
    Der Kern der Vorbereitung: Forever trägt (noch) keinen bekannten
    Ordnernamen, und trotzdem findet die Wurzelauswahl seinen
    Unterordner - über die Kennzeichen einer Installation.
    """

    root = tmp_path / "World of Warcraft"

    forever = _make_installation(root, "_whatever_they_call_it_")

    assert resolve_client_folder(root, FOREVER) == forever


def test_a_foreign_flavour_is_never_taken_for_forever(tmp_path):
    """
    Ohne diesen Ausschluss landete das Addon in `_classic_`, sobald
    jemand mit gewählter Spielversion Forever die Wurzel auswählt -
    und nichts daran wäre sichtbar.
    """

    root = tmp_path / "World of Warcraft"

    _make_classic_folder(root)

    _make_installation(root, "_retail_")

    check = check_client_folder(root, FOREVER)

    assert not check.ok

    assert "andere Spielversion" in check.reason


def test_several_candidates_are_not_guessed_between(tmp_path):
    """
    Zwei unbekannte Installationen nebeneinander: raten wäre hier
    teuer, also sagt die Antwort, dass der Nutzer selbst wählen muss.
    """

    root = tmp_path / "Spiele"

    _make_installation(root, "wow_a")

    _make_installation(root, "wow_b")

    check = check_client_folder(root, FOREVER)

    assert not check.ok

    assert "mehrere Installationen" in check.reason

    assert "wow_a" in check.reason and "wow_b" in check.reason


def test_the_chosen_folder_itself_still_wins(tmp_path):
    """
    Wer den Installationsordner direkt wählt, bekommt ihn - auch wenn
    der Name zu keiner bekannten Spielversion gehört.
    """

    forever = _make_installation(tmp_path, "_forever_")

    assert resolve_client_folder(forever, FOREVER) == forever


def test_a_client_can_carry_its_own_markers(tmp_path):
    """
    Sollte Forever den Aufbau einer Installation ändern, ist das ein
    Feld im Eintrag und kein Eingriff in diese Prüfung.
    """

    strange = WowClient(
        id="strange",
        name="Strange",
        short_name="Strange",
        markers=(("Data",),),
    )

    folder = tmp_path / "irgendwas"

    (folder / "Data").mkdir(parents=True)

    assert resolve_client_folder(folder, strange) == folder
