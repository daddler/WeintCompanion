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
from core.sync_manager import SyncManager

from analyzer.academy.models import PlayerProfile, TrainingPlan
from analyzer.models import Actor, RaidSnapshot


ACTOR = Actor(name="Testchar", class_name="Warrior", spec="Waffen", role="dps")


class _Logger:

    def __init__(self):
        self.successes = []
        self.infos = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        pass

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

    def build_plan(self, profile, snapshot=None):
        return TrainingPlan()

    def completed_for(self, name):
        return frozenset(self.data["completed"].get(name, []))

    def excluded_for(self, name):
        return frozenset(self.data["excluded"].get(name, []))

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


class _Reader:

    def __init__(self):
        self.wow_path = None

    def exists(self):
        return False

    def get_messages(self):
        return []

    def remove_message(self, message_id):
        return True


@pytest.fixture
def sync_manager(monkeypatch):

    monkeypatch.setattr(SyncManager, "__init__", lambda self, manager: None)

    manager = _Manager(RaidSnapshot.empty())

    sync = SyncManager(manager)
    sync.manager = manager
    sync.reader = _Reader()

    return sync


def test_progress_from_the_addon_is_applied(sync_manager):

    sync_manager._apply_academy_progress(
        "Testchar|a,b|z;Zweitchar|c|"
    )

    academy = sync_manager.manager.academy

    assert academy.data["completed"]["Testchar"] == ["a", "b"]
    assert academy.data["excluded"]["Testchar"] == ["z"]
    assert academy.data["completed"]["Zweitchar"] == ["c"]
    assert academy.data["excluded"]["Zweitchar"] == []
    assert academy.saved == 1


def test_clearing_the_last_entry_reaches_the_desktop(sync_manager):

    academy = sync_manager.manager.academy

    academy.data["completed"]["Testchar"] = ["a"]

    # Das Addon meldet auch leere Listen - sonst bliebe der alte
    # Stand hier stehen und das Abwählen wäre folgenlos.
    sync_manager._apply_academy_progress("Testchar||")

    assert academy.data["completed"]["Testchar"] == []
    assert academy.saved == 1


def test_unchanged_progress_is_not_saved_again(sync_manager):

    academy = sync_manager.manager.academy

    academy.data["completed"]["Testchar"] = ["a"]
    academy.data["excluded"]["Testchar"] = []

    sync_manager._apply_academy_progress("Testchar|a|")

    assert academy.saved == 0


def test_malformed_blocks_are_skipped(sync_manager):

    sync_manager._apply_academy_progress("kaputt;Testchar|a|;|b|c")

    academy = sync_manager.manager.academy

    assert academy.data["completed"] == {"Testchar": ["a"]}


def test_empty_payload_does_nothing(sync_manager):

    sync_manager._apply_academy_progress("")

    assert sync_manager.manager.academy.saved == 0
