from core.changelog_reader import (
    format_changelog_body,
    read_changelog_sections,
)
from core.resources import Resources

SAMPLE_CHANGELOG = """# Changelog

Alle nennenswerten Änderungen, von Version 0.7.2 bis 1.1.0.

## 1.1.0

- Neu: Feature A wurde ergänzt.
- Fix: Bug B behoben, der unter bestimmten
  Umständen auftrat.

## 1.0.0

- Erster offizieller Release.

## 0.9.1

- Bridge "Charakter-Roster" aktiv.

## 0.9.0

- Bridge "Gilden-Kalender" korrigiert.
"""


def _write_changelog(tmp_path, monkeypatch, text=SAMPLE_CHANGELOG):
    (tmp_path / "CHANGELOG.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(Resources, "root", staticmethod(lambda: tmp_path))


def test_read_without_since_returns_only_matching_version(tmp_path, monkeypatch):
    _write_changelog(tmp_path, monkeypatch)

    sections = read_changelog_sections("1.0.0")

    assert [v for v, _ in sections] == ["1.0.0"]
    assert "Erster offizieller Release" in sections[0][1]


def test_read_with_since_returns_sections_in_between_exclusive(tmp_path, monkeypatch):
    _write_changelog(tmp_path, monkeypatch)

    sections = read_changelog_sections("1.1.0", since_version="1.0.0")

    assert [v for v, _ in sections] == ["1.1.0"]


def test_read_skips_multiple_versions_when_since_is_further_back(tmp_path, monkeypatch):
    _write_changelog(tmp_path, monkeypatch)

    sections = read_changelog_sections("1.1.0", since_version="0.9.0")

    assert [v for v, _ in sections] == ["1.1.0", "1.0.0", "0.9.1"]


def test_read_respects_limit(tmp_path, monkeypatch):
    _write_changelog(tmp_path, monkeypatch)

    sections = read_changelog_sections("1.1.0", since_version="0.9.0", limit=2)

    assert [v for v, _ in sections] == ["1.1.0", "1.0.0"]


def test_read_returns_empty_when_version_not_found(tmp_path, monkeypatch):
    _write_changelog(tmp_path, monkeypatch)

    assert read_changelog_sections("9.9.9") == []


def test_read_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(Resources, "root", staticmethod(lambda: tmp_path))

    assert read_changelog_sections("1.0.0") == []


def test_format_changelog_body_joins_wrapped_lines_and_bullets():
    body = (
        '- Neu: Feature A wurde ergänzt.\n'
        '- Fix: Bug B behoben, der unter bestimmten\n'
        '  Umständen auftrat.\n'
    )

    formatted = format_changelog_body(body)

    assert formatted == (
        "• Neu: Feature A wurde ergänzt.\n\n"
        "• Fix: Bug B behoben, der unter bestimmten Umständen auftrat."
    )


def test_format_changelog_body_handles_empty_input():
    assert format_changelog_body("") == ""
