"""
Die WeakAura-Brücke: was eingetragen wird, kommt im Spiel an.

Geprüft wird die reine Hälfte (`core/weakaura_library.py`), die
Ablage (`core/weakaura_store.py`) und die Zustellung
(`core/weakaura_sync.py`). Die Oberfläche ist absichtlich nicht dabei -
alles, woran hier etwas falsch sein kann, ist ohne Fenster prüfbar,
und das ist der Grund für den Zuschnitt der Dateien.

Der Vertrag steht in `docs/weakaura-bridge.md`.
"""

from __future__ import annotations

import types

import pytest

from core.weakaura_library import (
    CatalogEntry,
    WeakAura,
    aura_from_catalog,
    clean_import_string,
    looks_like_export,
    make_id,
    normalize_category,
    parse_catalog,
    validate,
    warnings,
)
from core.weakaura_store import WeakAuraStore


EXPORT = "!WA:2!" + "aBcD3" * 20


class _Logger:

    def __init__(self):
        self.lines = []

    def info(self, message):
        self.lines.append(("info", message))

    def warning(self, message):
        self.lines.append(("warning", message))

    def error(self, message):
        self.lines.append(("error", message))

    def success(self, message):
        self.lines.append(("success", message))


@pytest.fixture
def store(tmp_path):

    manager = types.SimpleNamespace(logger=_Logger())

    return WeakAuraStore(manager, path=tmp_path / "weakauras.json")


# --------------------------------------------------
# Der Importstring
# --------------------------------------------------


def test_pasted_line_breaks_are_removed_instead_of_rejected():
    """
    Wer seinen String aus Discord oder einem Forumsbeitrag kopiert,
    bringt Umbrüche mit. WeakAuras-Exporte enthalten selbst keinen
    Leerraum - ihn zu entfernen ist eindeutig, das Einfügen
    abzulehnen wäre nur lästig.
    """

    pasted = "!WA:2!abc\ndef  ghi\r\n"

    assert clean_import_string(pasted) == "!WA:2!abcdefghi"


def test_a_missing_prefix_is_a_hint_and_not_an_error():
    """
    Ältere WeakAuras-Versionen exportieren ohne "!WA:". Eine Prüfung,
    die richtige Eingaben abweist, ist schlimmer als eine, die eine
    falsche durchlässt.
    """

    aura = WeakAura(name="Alt", version="1.0", string="dGVzdA" * 10)

    assert validate(aura) == []

    assert any("!WA:" in note for note in warnings(aura))

    assert not looks_like_export(aura.string)


def test_a_half_copied_string_is_caught():

    aura = WeakAura(name="Halb", version="1.0", string="!WA:2!ab")

    assert any("zu kurz" in problem for problem in validate(aura))


def test_what_is_missing_is_named_one_by_one():
    """
    Ein leeres Formular nennt beide Lücken, nicht nur die erste - wer
    zwei Felder vergessen hat, soll nicht zweimal auf "Fertig"
    drücken müssen, um das zu erfahren.
    """

    problems = validate(WeakAura())

    assert any("Namen" in problem for problem in problems)

    assert any("String" in problem for problem in problems)

    #
    # Rubrik und Version tragen brauchbare Voreinstellungen und
    # stehen deshalb NICHT drin: eine Vorgabe als Mangel zu melden
    # macht die Liste unlesbar.
    #

    assert len(problems) == 2


# --------------------------------------------------
# Die Kennung
# --------------------------------------------------


def test_the_id_is_readable_and_survives_umlauts():
    """
    "Mönch" muss "monch" werden und nicht "mnch": das "ö" zerfällt in
    "o" plus ein kombinierendes Trema, und nur das Trema fällt weg.
    """

    assert make_id("Mönch Braumeister") == "companion-monch-braumeister"

    assert make_id("Schädel & Knochen") == "companion-schadel-knochen"


def test_two_auras_of_the_same_name_get_different_ids():
    """
    Denselben Namen dürfen sie tragen (eine je Spec heisst gern
    gleich). Die Kennung nicht - sie ist der Schlüssel, unter dem das
    Addon ersetzt.
    """

    first = make_id("Rotation")

    second = make_id("Rotation", taken={first})

    assert first != second

    assert make_id("Rotation", taken={first, second}) not in {first, second}


def test_a_new_id_never_collides_with_a_shipped_aura():
    """
    Die mitgelieferten heissen DRUID, DUNGEONPACK, ... - ein neuer
    Eintrag darf keine davon treffen, sonst ersetzte er unabsichtlich
    etwas.
    """

    assert make_id("Druid").startswith("companion-")


def test_editing_a_shipped_aura_keeps_its_id():
    """
    Das ist der ganze Punkt von "aktualisieren": unter derselben
    Kennung gewinnt die neue Fassung im Addon, statt daneben zu
    stehen.
    """

    entry = CatalogEntry(
        id="DRUID",
        name="Druide",
        category="class",
        version="2.0.6",
        origin="addon",
    )

    aura = aura_from_catalog(entry)

    assert aura.id == "DRUID"

    assert aura.replaces_addon is True

    #
    # Der Importstring bleibt leer: das Addon meldet ihn nicht mit,
    # und ein geratener oder alter String wäre das Gegenteil einer
    # Aktualisierung.
    #

    assert aura.string == ""

    assert any("String" in problem for problem in validate(aura))


# --------------------------------------------------
# Die Rubrik
# --------------------------------------------------


def test_an_unknown_category_becomes_utility_instead_of_vanishing():
    """
    Dieselbe Regel wie im Addon (`NormalizeCategory` in
    `modules/weakauras.lua`): unsichtbar wäre der schlechtere Ausgang.
    """

    assert normalize_category("boss") == "utility"

    assert normalize_category("") == "utility"

    assert normalize_category("RAID") == "raid"


# --------------------------------------------------
# Die Katalogmeldung aus dem Spiel
# --------------------------------------------------


def test_the_catalog_report_is_read_positionally():

    entries = parse_catalog(
        "DRUID|Druide|class|2.0.6|addon;"
        "companion-x|Meine Aura|raid|1.2|companion"
    )

    assert [entry.id for entry in entries] == ["DRUID", "companion-x"]

    assert entries[0].from_addon is True

    assert entries[1].from_addon is False


def test_a_shorter_report_from_an_older_addon_still_reads():
    """
    Zwei Felder reichen. Ein älteres Addon darf weniger schicken, ein
    neueres mehr - beides ohne die Gegenseite zu brechen.
    """

    entries = parse_catalog("DRUID|Druide;X|Y|class|1.0|addon|zusaetzlich")

    assert len(entries) == 2

    assert entries[0].name == "Druide"

    assert entries[0].category == "utility"

    assert entries[1].id == "X"


def test_an_empty_report_yields_nothing_rather_than_a_phantom_row():

    assert parse_catalog("") == []

    assert parse_catalog(";;") == []

    assert parse_catalog(None) == []


# --------------------------------------------------
# Die Ablage
# --------------------------------------------------


def test_the_library_survives_a_restart(store, tmp_path):

    aura = WeakAura(
        id="companion-test",
        name="Test",
        category="raid",
        version="1.0",
        string=EXPORT,
    )

    store.put(aura)

    reopened = WeakAuraStore(
        types.SimpleNamespace(logger=_Logger()),
        path=tmp_path / "weakauras.json",
    )

    assert [entry.id for entry in reopened.auras()] == ["companion-test"]

    assert reopened.get("companion-test").string == EXPORT


def test_a_shipped_aura_with_an_own_version_is_listed_only_once(store):
    """
    Wer eine mitgelieferte Aura aktualisiert, legt hier einen Eintrag
    unter derselben Kennung an. Stünde sie danach zusätzlich unter
    "mit dem Addon geliefert", wäre nicht zu erkennen, welche der
    beiden im Spiel gewinnt.
    """

    store.apply_catalog(
        "DRUID|Druide|class|2.0.6|addon;DUNGEONPACK|Dungeon Pack|utility|1.2|addon"
    )

    assert {entry.id for entry in store.addon_entries()} == {"DRUID", "DUNGEONPACK"}

    store.put(
        WeakAura(
            id="DRUID",
            name="Druide",
            category="class",
            version="2.0.7",
            string=EXPORT,
        )
    )

    assert [entry.id for entry in store.addon_entries()] == ["DUNGEONPACK"]

    #
    # Belegt bleibt sie trotzdem: eine NEUE Aura darf die Kennung
    # nicht bekommen.
    #

    assert "DRUID" in store.taken_ids()


def test_an_unchanged_catalog_report_is_not_written_again(store):

    payload = "DRUID|Druide|class|2.0.6|addon"

    assert store.apply_catalog(payload) is True

    assert store.apply_catalog(payload) is False

    assert store.apply_catalog(payload + ";X|Y|raid|1.0|addon") is True


def test_a_broken_library_file_is_reported_and_not_overwritten(tmp_path):
    """
    Hinter der Datei steht Tipparbeit. Ein stummer Neuanfang wäre der
    Verlust einer Nachmittagsarbeit ohne eine einzige Zeile im
    Protokoll.
    """

    path = tmp_path / "weakauras.json"

    path.write_text("{ kaputt", encoding="utf-8")

    logger = _Logger()

    store = WeakAuraStore(types.SimpleNamespace(logger=logger), path=path)

    assert store.auras() == []

    assert any(level == "warning" for level, _ in logger.lines)

    assert path.read_text(encoding="utf-8") == "{ kaputt"
