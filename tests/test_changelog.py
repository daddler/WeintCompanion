"""
Der Changelog-Leser und seine beiden Quellen.

Der Kern dieser Tests ist ein einziger Satz: **beide Repositorys
schreiben ihre Überschriften anders.** Die Companion nutzt `## 2.0.1`,
das Addon `## [1.3.3.1] – 2026-08-11`. Beide landen in derselben
Ansicht, also muss ein Leser beide verstehen - und ein Fehler dort ist
still: eine leere Liste ist von "es gab keine Änderungen" nicht zu
unterscheiden.
"""

from pathlib import Path

from core.changelog_reader import (
    format_changelog_body,
    read_changelog_sections,
    read_entries,
    split_entries,
    strip_markdown,
)
from core.changelog_source import (
    ADDON,
    COMPANION,
    addon_entries,
    companion_entries,
    find_entry,
    latest_entry,
)


COMPANION_STYLE = """
# Changelog

Ein Vorwort, das keine Fassung ist.

## 2.0.1

**Etwas Fettes.** Ein Absatz über zwei
Zeilen.

- Ein Punkt
  mit Fortsetzung
- Noch ein Punkt

## 2.0.0

Der erste Wurf.
"""


ADDON_STYLE = """
# Changelog

## [1.3.3.1] – 2026-08-11

### Neu
- **Erstes** mit `Code`
- Zweites

### Geändert
- Drittes

## [1.3.3.0] – 2026-08-10

### Behoben
- Viertes
"""


class FakeState:

    addon_found = False

    addon_path = None

    addon_version = "-"

    github_version = ""

    github_changelog = ""

    companion_latest_version = ""


def test_both_header_styles_are_understood():

    companion = split_entries(COMPANION_STYLE)

    assert [entry.version for entry in companion] == ["2.0.1", "2.0.0"]

    #
    # Die Companion schreibt kein Datum in die Überschrift - das darf
    # nicht dazu führen, dass der Rest der Zeile als eines gilt.
    #

    assert companion[0].date == ""

    addon = split_entries(ADDON_STYLE)

    assert [entry.version for entry in addon] == ["1.3.3.1", "1.3.3.0"]

    assert addon[0].date == "2026-08-11"


def test_the_intro_before_the_first_version_is_not_one():

    for text in (COMPANION_STYLE, ADDON_STYLE):

        for entry in split_entries(text):
            assert entry.version[0].isdigit()


def test_a_heading_does_not_land_inside_the_previous_bullet():
    """
    Der Fehler, den `### Neu` vorher ausgelöst hat: jede Zeile ohne
    "- " galt als Fortsetzung des laufenden Punktes, also klebte die
    Zwischenüberschrift mitten im vorherigen Satz.
    """

    body = split_entries(ADDON_STYLE)[0].body

    text = format_changelog_body(body)

    assert "NEU" in text
    assert "GEÄNDERT" in text

    for line in text.splitlines():

        assert not line.startswith("• Zweites Geändert")


def test_plain_paragraphs_survive():
    """
    Die Companion schreibt ihren Changelog überwiegend als Absätze.
    Der alte Formatierer kannte nur Aufzählungen, also war genau
    dieser Changelog leer.
    """

    text = format_changelog_body(split_entries(COMPANION_STYLE)[0].body)

    assert "Ein Absatz über zwei Zeilen." in text

    assert "• Ein Punkt mit Fortsetzung" in text


def test_markup_is_stripped_not_shown():

    assert strip_markdown("**fett** und `code`") == "fett und code"

    assert strip_markdown("[Text](https://example.invalid)") == "Text"

    text = format_changelog_body(split_entries(ADDON_STYLE)[0].body)

    assert "**" not in text
    assert "`" not in text


def test_a_missing_file_is_an_empty_list_not_an_error():

    assert read_entries(None) == []

    assert read_entries(Path("/nicht/vorhanden/CHANGELOG.md")) == []


def test_the_real_files_of_both_repos_parse(tmp_path):
    """
    Der eigentliche Punkt: die mitgelieferte CHANGELOG.md dieser
    Anwendung wird gelesen, und zwar mit mehr als einer Fassung.
    """

    entries = companion_entries()

    assert len(entries) > 1

    assert entries[0].version[0].isdigit()

    assert format_changelog_body(entries[0].body)


def test_the_addon_changelog_comes_from_the_addon_folder(tmp_path):

    (tmp_path / "CHANGELOG.md").write_text(
        ADDON_STYLE, encoding="utf-8",
    )

    state = FakeState()

    state.addon_found = True

    state.addon_path = tmp_path

    entries = addon_entries(state)

    assert [entry.version for entry in entries] == [
        "1.3.3.1",
        "1.3.3.0",
    ]


def test_without_a_file_the_release_text_stands_in():
    """
    Eine Addon-Fassung von vor dieser Regel bringt keine CHANGELOG.md
    mit. Dann ist der Text des GitHub-Releases besser als nichts - er
    beschreibt allerdings nur die eine neue Fassung, und genau so
    kommt er auch an.
    """

    state = FakeState()

    state.github_version = "v1.4.0.0"

    state.github_changelog = "- Etwas Neues"

    entries = addon_entries(state)

    assert len(entries) == 1

    assert entries[0].version == "1.4.0.0"


def test_nothing_at_all_is_an_empty_list():

    assert addon_entries(FakeState()) == []


def test_the_offered_version_wins_over_the_newest_local_one():
    """
    Solange nicht aktualisiert wurde, ist die lokale Datei einen
    Schritt zurück. Für den Update-Hinweis zählt aber die Fassung, die
    angeboten wird - sonst stünde unter "Update verfügbar" der Text
    der bereits installierten.
    """

    entries = split_entries(ADDON_STYLE)

    assert find_entry(entries, "1.3.3.0").body.strip().startswith("###")

    #
    # Mit und ohne "v", Groß-/Kleinschreibung egal - GitHub-Tags
    # tragen es, die Datei nicht.
    #

    assert find_entry(entries, "V1.3.3.1") is not None

    assert find_entry(entries, "9.9.9.9") is None

    assert find_entry(entries, "") is None


def test_latest_entry_falls_back_to_the_top(tmp_path):

    (tmp_path / "CHANGELOG.md").write_text(
        ADDON_STYLE, encoding="utf-8",
    )

    state = FakeState()

    state.addon_found = True

    state.addon_path = tmp_path

    #
    # Eine Fassung, die in der Datei nicht vorkommt (das Release ist
    # neuer als das installierte Addon): dann der oberste Eintrag,
    # statt gar keiner.
    #

    state.github_version = "v1.4.0.0"

    assert latest_entry(ADDON, state).version == "1.3.3.1"


def test_read_changelog_sections_still_serves_the_whats_new_dialog():
    """
    Das "Was ist neu"-Fenster liest über denselben Zerleger. Ein
    Umbau, der ihn stillschweigend anders schneidet, hätte dort einen
    leeren Dialog zur Folge.
    """

    sections = read_changelog_sections(
        companion_entries()[0].version,
    )

    assert len(sections) == 1

    version, body = sections[0]

    assert version == companion_entries()[0].version

    assert body
