"""
Wann die Auswertung ins Addon gestellt wird - und wann nicht.

Drei Eigenschaften stehen hier im Vordergrund:

* Ohne ausgewertete Daten wird nichts zugestellt, und vor allem wird
  ein bereits zugestellter Bericht nicht gelöscht: ein alter Bericht
  ist besser als gar keiner.
* Unveränderte Daten werden nicht erneut geschrieben. Jede Zustellung
  fasst WoWs komplette SavedVariables-Datei an und die Nutzlast ist
  einige Dutzend Kilobyte groß - im Fünf-Minuten-Takt wäre das
  Verschwendung.
* Der Zeitstempel ändert sich bei jedem Poll und darf deshalb nicht
  als Änderung zählen, sonst greift die Sperre oben nie.

Dazu der Rückweg: der ingame gesetzte Fortschritt muss auf dem
Desktop ankommen, auch wenn der Spieler den letzten Haken wieder
entfernt hat.
"""

import pytest

from core.addon_analysis_sync import AddonAnalysisSync
from core.academy_progress_sync import apply_addon_progress, parse_addon_progress

from analyzer.academy.progression import PullRecord
from analyzer.academy.models import PlayerProfile, TrainingPlan
from analyzer.models import Actor, RaidSnapshot


ACTOR = Actor(name="Testchar", class_name="Warrior", spec="Waffen", role="dps")


class _Logger:

    def __init__(self):
        self.successes = []
        self.infos = []
        self.errors = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        self.errors.append(message)

    def success(self, message):
        self.successes.append(message)

    def warning(self, message):
        pass


class _RaidData:

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def current(self):
        return self.snapshot


class _Academy:

    def __init__(self):
        self.data = {"completed": {}, "excluded": {}}
        self.saved = 0

    def resolve_player_name(self, snapshot):
        return "Testchar"

    def build_profile(self, snapshot):
        return PlayerProfile(
            actor=ACTOR,
            ratings=(),
            encounter_name="Horridon",
            sample_size=snapshot.pull_number,
        )

    #
    # `character` wird seit 1.7.0 durchgereicht: das Profil allein
    # kann den Namen nicht liefern, weil `PlayerProfile.name` "-"
    # ist, sobald der Spieler im Pull fehlt.
    #
    def build_plan(self, profile, snapshot=None, character=""):
        self.plan_character = character
        return TrainingPlan()

    def completed_for(self, name):
        return frozenset(self.data["completed"].get(name, []))

    def excluded_for(self, name):
        return frozenset(self.data["excluded"].get(name, []))

    #
    # Seit 2.8.0 geht der zurückgemeldete Stand über den Service, weil
    # dort entschieden wird, welcher Charakter gemeint ist.
    #
    def set_progress(self, character, completed, excluded):

        changed = False

        for section, values in (
            ("completed", list(completed)),
            ("excluded", list(excluded)),
        ):

            if self.data[section].get(character) != values:

                self.data[section][character] = values
                changed = True

        return changed

    #
    # Die Lernkurve und die Übungsserie reisen seit 2.8.0 mit. Hier
    # bleiben sie leer - dass eine leere Kurve keine Linie behauptet,
    # prüft tests/test_addon_payloads.py.
    #
    def curve_for(self, profile, character=""):
        return ()

    def practice_for(self, character):
        return {}

    def save(self):
        self.saved += 1


class _Inbox:

    def __init__(self, ok=True):
        self.ok = ok
        self.published = []

    def publish(self, channel, messages):
        self.published.append((channel, messages))
        return self.ok


class _Manager:

    def __init__(self, snapshot, inbox=None):
        self.logger = _Logger()
        self.raid_data = _RaidData(snapshot)
        self.academy = _Academy()
        self.config = type("C", (), {"data": {}})()
        self.state = type("S", (), {"wow_path": None})()


def _snapshot(pull=1, captured_at=1000.0, boss=42.0) -> RaidSnapshot:

    return RaidSnapshot(
        captured_at=captured_at,
        source_label="WarcraftLogs",
        in_combat=True,
        raid_size=25,
        pull_number=pull,
        pull_seconds=120.0,
        boss_health_percent=boss,
    )


# --------------------------------------------------


def test_nothing_is_delivered_without_data():

    inbox = _Inbox()
    manager = _Manager(RaidSnapshot.empty())

    AddonAnalysisSync(manager, inbox).process()

    # Auch nicht geleert: der zuletzt zugestellte Bericht soll im
    # Addon stehen bleiben.
    assert inbox.published == []


def test_delivers_all_three_messages():

    inbox = _Inbox()
    manager = _Manager(_snapshot())

    AddonAnalysisSync(manager, inbox).process()

    assert len(inbox.published) == 1

    channel, messages = inbox.published[0]

    assert channel == "analysis"
    assert [message["type"] for message in messages] == [
        "academy_catalog", "academy_state", "weinttv_report",
    ]

    assert manager.logger.successes


def test_unchanged_data_is_not_written_again():

    inbox = _Inbox()
    manager = _Manager(_snapshot())

    sync = AddonAnalysisSync(manager, inbox)

    sync.process()
    sync.process()

    assert len(inbox.published) == 1


def test_a_new_timestamp_alone_is_not_a_change():

    inbox = _Inbox()
    manager = _Manager(_snapshot(captured_at=1000.0))

    sync = AddonAnalysisSync(manager, inbox)

    sync.process()

    # Genau das passiert bei jedem Poll: neuer Zeitstempel, sonst
    # nichts. Würde das als Änderung zählen, liefe die Sperre leer.
    manager.raid_data.snapshot = _snapshot(captured_at=2000.0)

    sync.process()

    assert len(inbox.published) == 1


def test_changed_data_is_delivered_again():

    inbox = _Inbox()
    manager = _Manager(_snapshot(boss=42.0))

    sync = AddonAnalysisSync(manager, inbox)

    sync.process()

    manager.raid_data.snapshot = _snapshot(boss=12.0)

    sync.process()

    assert len(inbox.published) == 2


def test_a_failed_write_is_retried_next_time():

    inbox = _Inbox(ok=False)
    manager = _Manager(_snapshot())

    sync = AddonAnalysisSync(manager, inbox)

    sync.process()
    sync.process()

    # Fehlgeschlagen heißt nicht zugestellt - der Stand darf nicht
    # als erledigt vermerkt werden, sonst bliebe es dauerhaft aus.
    assert len(inbox.published) == 2
    assert manager.logger.successes == []


# --------------------------------------------------
# Rückweg: Fortschritt aus dem Addon
# --------------------------------------------------


def test_progress_from_the_addon_is_applied():

    academy = _Academy()

    assert apply_addon_progress(academy, "Testchar|a,b|z;Zweitchar|c|") is True

    assert academy.data["completed"]["Testchar"] == ["a", "b"]
    assert academy.data["excluded"]["Testchar"] == ["z"]
    assert academy.data["completed"]["Zweitchar"] == ["c"]
    assert academy.data["excluded"]["Zweitchar"] == []
    assert academy.saved == 1


def test_clearing_the_last_entry_reaches_the_desktop():

    academy = _Academy()

    academy.data["completed"]["Testchar"] = ["a"]

    # Das Addon meldet auch leere Listen - sonst bliebe der alte
    # Stand hier stehen und das Abwaehlen waere folgenlos.
    apply_addon_progress(academy, "Testchar||")

    assert academy.data["completed"]["Testchar"] == []
    assert academy.saved == 1


def test_unchanged_progress_is_not_saved_again():

    academy = _Academy()

    academy.data["completed"]["Testchar"] = ["a"]
    academy.data["excluded"]["Testchar"] = []

    assert apply_addon_progress(academy, "Testchar|a|") is False
    assert academy.saved == 0


def test_malformed_blocks_are_skipped():

    academy = _Academy()

    apply_addon_progress(academy, "kaputt;Testchar|a|;|b|c")

    assert academy.data["completed"] == {"Testchar": ["a"]}


def test_empty_payload_does_nothing():

    academy = _Academy()

    assert apply_addon_progress(academy, "") is False
    assert academy.saved == 0


def test_parsing_returns_both_lists_per_character():

    parsed = parse_addon_progress("A|x,y|z;B||")

    assert parsed == {"A": (["x", "y"], ["z"]), "B": ([], [])}


def test_parsing_survives_a_missing_academy():

    # Der SyncManager reicht getattr(..., "academy", None) durch -
    # eine halb aufgebaute Anwendung darf hier nicht abstuerzen.
    assert apply_addon_progress(None, "A|x|") is False


# --------------------------------------------------
# Sofortzustellung
# --------------------------------------------------
#
# Der Merker verhindert überflüssige Schreibvorgänge - er darf aber
# nichts verhindern, was sich ausserhalb der Nutzlast geändert hat.
# Der Auswahlwechsel eines Charakters ist genau so ein Fall gewesen:
# er wartete auf den nächsten Takt und fiel meist ganz aus, weil ohne
# geöffnete Seite kein ausgewerteter Snapshot vorliegt.
# --------------------------------------------------


def test_invalidate_schreibt_gleichen_inhalt_erneut():

    inbox = _Inbox()
    manager = _Manager(_snapshot(), inbox)
    sync = AddonAnalysisSync(manager, inbox)

    sync.process()
    sync.process()

    assert len(inbox.published) == 1

    sync.invalidate()
    sync.process()

    assert len(inbox.published) == 2


def test_publish_now_stellt_sofort_zu():

    inbox = _Inbox()
    manager = _Manager(_snapshot(), inbox)
    sync = AddonAnalysisSync(manager, inbox)

    sync.publish_now()
    sync.publish_now()

    assert len(inbox.published) == 2


def test_publish_now_reisst_den_aufrufer_nicht_mit():
    """
    Aufgerufen wird sie aus der Oberfläche, beim blossen Umstellen
    eines Namens. Ein Fehler dabei ist eine Logzeile, kein Absturz.
    """

    class _Kaputt:

        ok = True

        def publish(self, channel, messages):
            raise RuntimeError("Platte voll")

    manager = _Manager(_snapshot())
    sync = AddonAnalysisSync(manager, _Kaputt())

    sync.publish_now()

    assert manager.logger.errors


def test_ohne_ausgewaehlten_charakter_wird_nichts_zugestellt():
    """
    Eine geratene Identität hat auf der Leitung nichts verloren.
    """

    inbox = _Inbox()
    manager = _Manager(_snapshot(), inbox)
    manager.academy.resolve_player_name = lambda snapshot: ""

    AddonAnalysisSync(manager, inbox).process()

    assert inbox.published == []


#
# --------------------------------------------------
# Lernkurve und Übungsserie reisen mit
# --------------------------------------------------
#
# Beide entstehen auf dem Desktop und wurden bis 2.8.0 nicht
# zugestellt. Der Test hängt an der **Verdrahtung**: dass die Kurve
# aus `curve_for()` kommt (derselbe Aufruf, aus dem auch die
# Reihenfolge des Trainingsplans folgt) und die Serie aus dem
# Übungsspeicher - ein vergessenes Argument fiele sonst nirgends auf,
# das Feld wäre schlicht leer.
#


def test_the_curve_and_the_practice_streak_are_delivered():

    manager = _Manager(_snapshot())

    manager.academy.curve_for = lambda profile, character="": (
        PullRecord(
            key="r#1",
            day="20260901",
            sequence=1,
            ratings=(("rotation", 2),),
        ),
        PullRecord(
            key="r#2",
            day="20260902",
            sequence=2,
            ratings=(("rotation", 4),),
        ),
    )

    manager.academy.practice_for = lambda character: {
        "WARRIOR_ARMS": {
            "lastDate": "20260902",
            "streak": 2,
        },
    }

    inbox = _Inbox()

    AddonAnalysisSync(manager, inbox).process()

    state = next(
        message["payload"]
        for message in inbox.published[0][1]
        if message["type"] == "academy_state"
    )

    assert state["progress"]["pulls"] == 2
    assert state["progress"]["points"] == [2.0, 4.0]

    #
    # Die Serie kommt fertig formuliert an - und mit der Lektions-ID,
    # damit die Zeile im Spiel an der richtigen Karte landet.
    #

    assert state["practice"][0]["specKey"] == "WARRIOR_ARMS"
    assert (
        state["practice"][0]["lessonId"]
        == "warrior-arms.rotation.dummy_practice"
    )
    assert state["practice"][0]["text"]
