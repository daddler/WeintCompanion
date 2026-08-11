"""
Der Ausrüstungsstand vom Addon -> Charakterliste -> die zwei Seiten.

Zwei Fragen, die dieser Test offen hält, weil ihre Antwort still
falsch werden kann:

* **Verträgt der Parser eine ältere und eine neuere Addon-Version?**
  Das Format ist positionsbasiert und darf wachsen. Ein fehlender
  Abschnitt muss `None` ergeben, kein Absturz und keine Null - und
  zusätzliche Felder müssen ignoriert werden, damit eine ältere
  Companion an einem erweiterten Format nicht scheitert.
* **Bleibt "keine Prüfung" von "nichts vorbereitet" unterscheidbar?**
  `readiness()` liefert `None` statt `0.0`, wenn das Addon nichts
  geprüft hat. Wer beides zusammenzieht, macht aus einer Datenlücke
  einen Befund - dieselbe Regel wie `stars == 0` im Analyzer.
"""

import time

import pytest

from core.character_sheet_sync import (
    open_slots,
    parse_character_sheet,
    readiness,
    sheet_key,
)
from core.character_store import CharacterStore
from core.paths import Paths


#
# Eine vollständige Meldung, wie modules/companion.lua sie baut.
#

FULL = (
    "Njiah|Everlook|PALADIN|90|PALADIN_RETRIBUTION|Vergeltung|"
    "551.8|553.2|82|B|94|87|1786453093"
    "~ench|8|1|0|0|1|10;gem|5|0|1|0|1|7"
    "~9|2|3|14;Hals|Schmuck|Umhang"
    "~1|Kopf|Helm|553|-|optimal"
    ";5|Brust|Brustplatte|553|optimal|missing"
    ";11|Finger 1|Ring|553|missing|-"
    "~1|missing|Finger 1: Verzauberung fehlt"
    ";2|overcap|Treffer über dem Cap"
)


class _Logger:

    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)

    def warning(self, message):
        self.messages.append(message)

    def error(self, message):
        self.messages.append(message)


class _Manager:

    def __init__(self):
        self.logger = _Logger()


@pytest.fixture
def store(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    return CharacterStore(_Manager())


# --------------------------------------------------
# Parser
# --------------------------------------------------


def test_a_complete_report_is_read_field_by_field():

    sheet = parse_character_sheet(FULL)

    assert sheet["name"] == "Njiah"
    assert sheet["realm"] == "Everlook"
    assert sheet["class"] == "PALADIN"
    assert sheet["level"] == 90
    assert sheet["spec"] == "Vergeltung"
    assert sheet["item_level_equipped"] == pytest.approx(551.8)
    assert sheet["grade"] == "B"

    assert sheet["enchants"]["missing"] == 1
    assert sheet["gems"]["total"] == 7

    assert sheet["bis"]["open"] == 3
    assert sheet["bis"]["open_slots"] == ["Hals", "Schmuck", "Umhang"]

    assert len(sheet["slots"]) == 3
    assert sheet["slots"][1]["gem"] == "missing"

    assert [issue["priority"] for issue in sheet["issues"]] == [1, 2]


def test_a_report_without_a_name_is_worthless():
    """
    Ohne Namen ließe sich die Meldung keinem Charakter zuordnen, und
    einen zu raten ist genau der Fehler, den 1.7.0 abgestellt hat.
    """

    assert parse_character_sheet("") is None
    assert parse_character_sheet("|Everlook|PALADIN") is None
    assert parse_character_sheet(None) is None
    assert parse_character_sheet(42) is None


def test_missing_sections_stay_none_instead_of_becoming_zero():
    """
    Eine ältere Addon-Version schickt weniger. Ein `0` an dieser
    Stelle behauptete "geprüft und nichts gefunden".
    """

    sheet = parse_character_sheet("Bob|Everlook|MAGE|90")

    assert sheet["enchants"] is None
    assert sheet["gems"] is None
    assert sheet["bis"] is None
    assert sheet["slots"] == []
    assert sheet["issues"] == []

    assert readiness(sheet) is None


def test_an_empty_bis_section_is_not_the_same_as_nothing_open():

    without = parse_character_sheet(
        "Bob|Everlook|MAGE|90|MAGE_FIRE|Feuer|0|0|0||0|0|1~ench|0|0|0|0|0|0~~~"
    )

    assert without["bis"] is None

    nothing_open = parse_character_sheet(
        "Bob|Everlook|MAGE|90|MAGE_FIRE|Feuer|0|0|0||0|0|1~~14|0|0|14;~~"
    )

    assert nothing_open["bis"]["open"] == 0
    assert nothing_open["bis"]["open_slots"] == []


def test_extra_fields_are_ignored_so_the_format_may_grow():
    """
    Das Addon darf Felder anhängen; eine ältere Companion muss die
    Meldung trotzdem lesen können.
    """

    sheet = parse_character_sheet(
        FULL + "|neu|noch neuer~zusätzlicher Abschnitt"
    )

    assert sheet["name"] == "Njiah"
    assert sheet["updated"] == 1786453093


def test_an_issue_text_containing_a_separator_is_not_cut_off():
    """
    Das Addon säubert Trennzeichen, aber eine ältere Version tat das
    nicht - der Rest gehört an den Text und nicht in den Papierkorb.
    """

    sheet = parse_character_sheet(
        "Bob|Everlook~~~~1|missing|Brust: A|B"
    )

    assert sheet["issues"][0]["text"] == "Brust: A|B"


# --------------------------------------------------
# Ableitungen
# --------------------------------------------------


def test_readiness_counts_what_was_checked_and_nothing_else():

    sheet = parse_character_sheet(FULL)

    # 10 Verzauberungen + 7 Sockel, zwei davon fehlen.
    assert readiness(sheet) == pytest.approx(15 / 17)


def test_readiness_ignores_open_bis_slots():
    """
    Offene BiS-Plätze hängen an Würfelglück, nicht an Vorbereitung.
    Zählten sie mit, wäre der Ring eines frisch ausgestatteten
    Charakters dauerhaft rot für etwas, das er nicht abstellen kann.
    """

    complete = parse_character_sheet(
        "Bob|Everlook|MAGE|90|MAGE_FIRE|Feuer|0|0|0||0|0|1"
        "~ench|9|0|0|0|0|9;gem|6|0|0|0|0|6"
        "~0|0|14|14;Kopf|Hals~~"
    )

    assert readiness(complete) == 1.0


def test_open_slots_names_only_what_is_missing():
    """
    Ein nicht ideal gewählter Stein ist ein Verbesserungsvorschlag,
    kein Loch - beides in eine Liste zu werfen verwischt die dringende
    Frage mit der optionalen.
    """

    assert open_slots(parse_character_sheet(FULL)) == ["Brust", "Finger 1"]


def test_the_key_carries_the_realm():
    """
    Zwei Realms dürfen denselben Namen führen; ohne Realm im Schlüssel
    überschriebe der eine Charakter die Ausrüstung des anderen.
    """

    assert sheet_key("Njiah", "Everlook") == "Njiah-Everlook"
    assert sheet_key("Njiah", "") == "Njiah"
    assert sheet_key("", "Everlook") == ""


# --------------------------------------------------
# Ablage
# --------------------------------------------------


def test_the_store_collects_one_character_per_login(store):
    """
    Das Addon meldet immer nur den gerade gespielten Charakter - die
    Liste über mehrere Twinks entsteht erst hier.
    """

    store.apply(FULL)
    store.apply("Zwergi|Everlook|WARRIOR|90|WARRIOR_ARMS|Waffen|540|541|100|S|100|100|2")

    names = [sheet["name"] for sheet in store.characters()]

    assert sorted(names) == ["Njiah", "Zwergi"]


def test_a_later_report_replaces_the_earlier_one(store):
    """
    Ergänzen statt Ersetzen würde eine entfernte Verzauberung weiter
    als vorhanden zeigen, nur weil die vorige Meldung sie kannte.
    """

    store.apply(FULL)

    store.apply(
        "Njiah|Everlook|PALADIN|90|PALADIN_RETRIBUTION|Vergeltung|"
        "560|560|100|S|100|100|1786453999"
        "~ench|10|0|0|0|0|10;gem|7|0|0|0|0|7~~~"
    )

    assert len(store.characters()) == 1

    sheet = store.get("Njiah", "Everlook")

    assert sheet["issues"] == []
    assert readiness(sheet) == 1.0


def test_the_newest_report_comes_first(store):

    store.apply("Alt|Everlook|MAGE|90|||0|0|0||0|0|100")
    store.apply("Neu|Everlook|MAGE|90|||0|0|0||0|0|900")

    assert [sheet["name"] for sheet in store.characters()] == ["Neu", "Alt"]


def test_a_report_without_a_timestamp_still_sorts(store):
    """
    Ohne Zeitstempel wäre "zuletzt gespielt" beliebig - der
    Empfangszeitpunkt ist die ehrlichste Näherung.
    """

    before = int(time.time())

    store.apply("Ohne|Everlook|MAGE|90")

    assert store.get("Ohne")["updated"] >= before


def test_the_bare_name_finds_the_qualified_entry(store):
    """
    Der Client kennt nur den nackten Namen - ein fehlender Realm ist
    im ganzen Projekt ein Platzhalter, kein Widerspruch.
    """

    store.apply(FULL)

    assert store.get("Njiah") is not None
    assert store.get("njiah") is not None
    assert store.get("Fremder") is None


def test_the_list_survives_a_restart(store, tmp_path, monkeypatch):

    store.apply(FULL)

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    again = CharacterStore(_Manager())

    assert again.get("Njiah", "Everlook")["spec"] == "Vergeltung"


def test_a_broken_file_is_reported_and_not_fatal(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    (tmp_path / "characters.json").write_text("{kaputt", encoding="utf-8")

    manager = _Manager()

    store = CharacterStore(manager)

    assert store.characters() == []
    assert manager.logger.messages


def test_the_summary_says_none_when_nothing_was_checked(store):
    """
    Eine Null stünde für "alles offen" - und wäre eine Messung, die es
    nicht gab.
    """

    assert store.preparation_summary()["ratio"] is None

    store.apply("Ohne|Everlook|MAGE|90")

    summary = store.preparation_summary()

    assert summary["characters"] == 1
    assert summary["rated"] == 0
    assert summary["ratio"] is None


def test_the_summary_averages_only_the_checked_characters(store):

    store.apply(FULL)
    store.apply("Ohne|Everlook|MAGE|90")

    summary = store.preparation_summary()

    assert summary["characters"] == 2
    assert summary["rated"] == 1
    assert summary["ratio"] == pytest.approx(15 / 17)
    assert summary["open"] == 2
