"""
Die Integritaetspruefung vor der Installation.

Die entscheidende Zeile dieser Datei ist die letzte Gruppe: ein
**fehlender** Hash ist hier kein "dann eben ohne", sondern ein
Abbruch. Der Generationswechsel laedt eine ausfuehrbare Datei
herunter und startet sie - ohne Beweis, dass es die richtige ist,
passiert das nicht.
"""

import pytest

from core.migration.integrity import (
    IntegrityError,
    Sha256Verifier,
    parse_checksum,
    sha256_of_file,
    verifier_for,
)


CONTENT = b"Companion-Forever 5.0.0"

DIGEST = "5ad0a3b8e2e0ebd0a2d9b0f0b3d5a0"  # bewusst zu kurz, siehe unten


def payload(tmp_path):

    path = tmp_path / "Companion-Forever-5.0.0-x86_64.AppImage"

    path.write_bytes(CONTENT)

    return path


# --------------------------------------------------
# Der Hash selbst
# --------------------------------------------------


def test_the_correct_hash_passes(tmp_path):

    path = payload(tmp_path)

    verifier_for(sha256_of_file(path)).verify(path)


def test_the_hash_is_read_case_insensitively(tmp_path):

    path = payload(tmp_path)

    verifier_for(sha256_of_file(path).upper()).verify(path)


def test_a_wrong_hash_stops_the_migration(tmp_path):

    path = payload(tmp_path)

    with pytest.raises(IntegrityError) as error:
        verifier_for("a" * 64).verify(path)

    assert error.value.code == "CHECKSUM_MISMATCH"


def test_a_changed_file_is_noticed(tmp_path):
    """
    Der eigentliche Zweck: dieselbe Pruefsumme, andere Datei.
    """

    path = payload(tmp_path)

    expected = sha256_of_file(path)

    path.write_bytes(CONTENT + b" (etwas anderes)")

    with pytest.raises(IntegrityError):
        verifier_for(expected).verify(path)


def test_a_missing_hash_is_not_a_pass(tmp_path):

    path = payload(tmp_path)

    for value in (None, "", "   "):

        with pytest.raises(IntegrityError) as error:
            verifier_for(value).verify(path)

        assert error.value.code == "MISSING_CHECKSUM"


def test_a_truncated_hash_is_no_hash(tmp_path):

    path = payload(tmp_path)

    with pytest.raises(IntegrityError) as error:
        Sha256Verifier(DIGEST).verify(path)

    assert error.value.code == "MISSING_CHECKSUM"


# --------------------------------------------------
# Die Pruefsummendatei
# --------------------------------------------------


def test_a_bare_digest_is_understood():

    assert parse_checksum("a" * 64) == "a" * 64


def test_the_sha256sum_style_is_understood():

    text = f"{'b' * 64}  Companion-Forever-5.0.0-x86_64.AppImage\n"

    assert parse_checksum(text, "Companion-Forever-5.0.0-x86_64.AppImage") == "b" * 64


def test_the_binary_star_notation_is_understood():

    text = f"{'c' * 64} *Companion-Forever-Setup-5.0.0-x64.exe\n"

    assert parse_checksum(text, "Companion-Forever-Setup-5.0.0-x64.exe") == "c" * 64


def test_the_right_line_is_taken_from_a_file_with_several():

    text = (
        f"{'d' * 64}  Companion-Forever-5.0.0-x86_64.AppImage\n"
        f"{'e' * 64}  Companion-Forever-Setup-5.0.0-x64.exe\n"
    )

    assert parse_checksum(text, "Companion-Forever-Setup-5.0.0-x64.exe") == "e" * 64


def test_a_file_with_several_lines_and_no_match_gives_nothing():
    """
    Lieber keine Pruefsumme (und damit ein Abbruch) als die erste
    beste Zeile.
    """

    text = (
        f"{'d' * 64}  irgendwas.AppImage\n"
        f"{'e' * 64}  irgendwas-anderes.exe\n"
    )

    assert parse_checksum(text, "Companion-Forever-5.0.0-x86_64.AppImage") is None


def test_rubbish_is_not_a_checksum():

    for text in ("", "   ", "kein hash hier", None):

        assert parse_checksum(text, "irgendwas") is None
