"""
`resolve_classic_folder` entscheidet, ob ein vom Nutzer gewählter
Ordner tatsächlich eine MoP-Classic-Installation ist - sowohl für
Einstellungen → WoW-Client als auch für die Einrichtung (§6.6). Beide
müssen dieselbe Antwort geben, deshalb die eine gemeinsame Funktion.
"""

from core.wow_folder import resolve_classic_folder


def _make_classic_folder(base):

    folder = base / "_classic_"

    (folder / "Interface" / "AddOns").mkdir(parents=True)

    (folder / "WTF").mkdir(parents=True)

    return folder


def test_a_direct_classic_folder_resolves_to_itself(tmp_path):

    folder = _make_classic_folder(tmp_path)

    assert resolve_classic_folder(folder) == folder


def test_the_battle_net_root_resolves_to_its_classic_subfolder(tmp_path):
    """
    Die meisten Nutzer wählen im Dateidialog die Wurzel
    "World of Warcraft", nicht den _classic_-Unterordner selbst.
    """

    root = tmp_path / "World of Warcraft"

    classic = _make_classic_folder(root)

    assert resolve_classic_folder(root) == classic


def test_an_unrelated_folder_is_rejected(tmp_path):

    empty = tmp_path / "Downloads"

    empty.mkdir()

    assert resolve_classic_folder(empty) is None


def test_a_folder_missing_only_wtf_is_rejected(tmp_path):
    """
    Alle drei Kennzeichen müssen vorliegen - ein halb entpacktes oder
    fremdes Verzeichnis darf nicht als Installation durchgehen.
    """

    folder = tmp_path / "_classic_"

    (folder / "Interface" / "AddOns").mkdir(parents=True)

    assert resolve_classic_folder(folder) is None


def test_accepts_a_string_path_too(tmp_path):

    folder = _make_classic_folder(tmp_path)

    assert resolve_classic_folder(str(folder)) == folder
