"""
Die Combat-Log-Suche ist die Vorarbeit für die Live-Auswertung.
Wichtig ist vor allem, dass sie nie wirft und bei Misserfolg einen
Grund liefert, den die Oberfläche direkt anzeigen kann.
"""

from analyzer.combatlog.locator import find_combat_log, logs_directory


def test_missing_path_reports_a_reason_instead_of_failing():

    location = find_combat_log("")

    assert location.found is False
    assert location.reason
    assert location.path is None


def test_missing_logs_directory_reports_a_reason(tmp_path):

    location = find_combat_log(tmp_path)

    assert location.found is False
    assert "Logs" in location.reason or "combatlog" in location.reason.lower()


def test_empty_logs_directory_reports_a_reason(tmp_path):

    (tmp_path / "Logs").mkdir()

    location = find_combat_log(tmp_path)

    assert location.found is False
    assert location.reason


def test_finds_the_plain_combat_log(tmp_path):

    logs = tmp_path / "Logs"
    logs.mkdir()

    log_file = logs / "WoWCombatLog.txt"
    log_file.write_text("x" * 128, encoding="utf-8")

    location = find_combat_log(tmp_path)

    assert location.found is True
    assert location.path == log_file
    assert location.size == 128


def test_picks_the_most_recently_written_file(tmp_path):
    """
    Bei aktiviertem Datei-pro-Sitzung-Logging liegen mehrere Dateien
    nebeneinander - die des laufenden Raids ist die zuletzt
    geschriebene.
    """

    logs = tmp_path / "Logs"
    logs.mkdir()

    old = logs / "WoWCombatLog-010224_180000.txt"
    old.write_text("alt", encoding="utf-8")

    new = logs / "WoWCombatLog-010224_200000.txt"
    new.write_text("neu", encoding="utf-8")

    import os

    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    location = find_combat_log(tmp_path)

    assert location.path == new


def test_ignores_unrelated_files(tmp_path):

    logs = tmp_path / "Logs"
    logs.mkdir()

    (logs / "Screenshot.txt").write_text("nein", encoding="utf-8")
    (logs / "WoWCombatLog.txt.bak").write_text("nein", encoding="utf-8")

    location = find_combat_log(tmp_path)

    assert location.found is False


def test_logs_directory_helper(tmp_path):

    assert logs_directory("") is None
    assert logs_directory(tmp_path) is None

    (tmp_path / "Logs").mkdir()

    assert logs_directory(tmp_path) == tmp_path / "Logs"
