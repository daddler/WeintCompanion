"""
Die Versionsnummer steht an drei Stellen - sie müssen übereinstimmen.

`core/version.py` ist die maßgebliche: nur sie vergleicht der
Updater. `packaging/installer.iss` trägt sie für den Windows-
Installer ein zweites Mal, und `CHANGELOG.md` braucht einen
Abschnitt, weil `gui/dialogs/whats_new_dialog.py` genau diese
Überschriften liest.

Vergessen wurde bisher regelmäßig die zweite Stelle. Das fällt sonst
niemandem auf, denn nichts schlägt fehl - der Windows-Installer
schreibt dann nur eine falsche Versionsnummer in die
Systemsteuerung.

Der Abgleich gegen den TAG passiert in der CI
(`scripts/check_version.py`, Job `version` in build.yml); hier wird
geprüft, dass das Repo für sich genommen stimmig ist.
"""

from core.version import VERSION

from scripts.check_version import (
    changelog_has,
    installer_iss,
    normalize,
    version_py,
)


def test_the_installer_carries_the_same_version():

    assert normalize(installer_iss()) == normalize(VERSION)


def test_version_py_is_read_the_same_way_the_ci_reads_it():
    """
    Die CI liest die Datei als Text, nicht als Modul - ein Umbau von
    core/version.py darf ihr nicht den Boden entziehen.
    """

    assert normalize(version_py()) == normalize(VERSION)


def test_the_changelog_documents_the_current_version():

    assert changelog_has(normalize(VERSION))


def test_the_version_is_a_three_part_number():
    """
    Der Tag hat die Form vX.Y.Z, und parse_version() füllt fehlende
    Teile mit Null auf - "1.2" und "1.2.0" wären damit dieselbe
    Version und ein Update von einem aufs andere unmöglich.
    """

    parts = normalize(VERSION).split(".")

    assert len(parts) == 3

    assert all(part.isdigit() for part in parts)
