"""
Der Zustand des Wechsels.

Zwei Dinge werden hier festgehalten: dass nur vorgesehene
Uebergaenge moeglich sind (ein "installiert" ohne "geprueft" darf es
nicht geben), und dass ein abgeschlossener Wechsel beim naechsten
Start nicht erneut angeboten wird.
"""

from core.migration.state import (
    MigrationRecord,
    MigrationState,
    MigrationStore,
    can_advance,
)
from core.migration.target import STATE_KEY


class FakeConfig:

    def __init__(self):

        self.data = {}
        self.saves = 0

    def save(self):
        self.saves += 1


def store():

    return MigrationStore(FakeConfig())


# --------------------------------------------------
# Uebergaenge
# --------------------------------------------------


def test_the_normal_way_through():

    order = [
        MigrationState.AVAILABLE,
        MigrationState.CONFIRMED,
        MigrationState.DOWNLOADING,
        MigrationState.DOWNLOADED,
        MigrationState.VERIFYING,
        MigrationState.INSTALLING,
        MigrationState.INSTALLED,
        MigrationState.COMPLETED,
    ]

    current = MigrationState.NOT_AVAILABLE

    for following in order:

        assert can_advance(current, following)

        current = following


def test_a_step_cannot_be_skipped():

    assert not can_advance(MigrationState.AVAILABLE, MigrationState.INSTALLED)

    assert not can_advance(MigrationState.DOWNLOADING, MigrationState.COMPLETED)


def test_almost_every_step_can_fail():

    for state in (
        MigrationState.CONFIRMED,
        MigrationState.DOWNLOADING,
        MigrationState.DOWNLOADED,
        MigrationState.VERIFYING,
        MigrationState.INSTALLING,
        MigrationState.INSTALLED,
    ):

        assert can_advance(state, MigrationState.FAILED)


def test_a_failure_is_not_the_end():
    """
    Aus FAILED geht es zurueck ins Angebot - ein Fehlschlag ist eine
    Runde, die nicht geklappt hat, kein Endzustand.
    """

    assert can_advance(MigrationState.FAILED, MigrationState.AVAILABLE)

    assert can_advance(MigrationState.FAILED, MigrationState.CONFIRMED)


def test_after_completion_nothing_follows():

    for state in MigrationState:

        if state is MigrationState.COMPLETED:
            continue

        assert not can_advance(MigrationState.COMPLETED, state)


# --------------------------------------------------
# Speichern
# --------------------------------------------------


def test_the_state_survives_in_the_configuration():

    config = FakeConfig()

    MigrationStore(config).advance(
        MigrationState.AVAILABLE,
        target="daddler/Companion-Forever",
        version="5.0.0",
        asset_name="Companion-Forever-5.0.0-x86_64.AppImage",
    )

    stored = config.data[STATE_KEY]

    assert stored["state"] == "available"

    assert stored["target_version"] == "5.0.0"

    assert MigrationStore(config).load().status is MigrationState.AVAILABLE


def test_an_impossible_step_changes_nothing():

    keeper = store()

    keeper.advance(MigrationState.AVAILABLE, version="5.0.0")

    keeper.advance(MigrationState.INSTALLED)

    assert keeper.load().status is MigrationState.AVAILABLE


def test_a_completed_migration_is_not_offered_again():

    keeper = store()

    for state in (
        MigrationState.AVAILABLE,
        MigrationState.CONFIRMED,
        MigrationState.DOWNLOADING,
        MigrationState.DOWNLOADED,
        MigrationState.VERIFYING,
        MigrationState.INSTALLING,
        MigrationState.INSTALLED,
        MigrationState.COMPLETED,
    ):
        keeper.advance(state, version="5.0.0")

    record = keeper.load()

    assert record.completed

    assert record.completed_at

    assert record.is_completed_for("5.0.0")


def test_a_completed_migration_does_not_swallow_the_next_version():
    """
    Fassungsgenau: wer 5.0.0 hinter sich hat, bekommt 5.1.0 trotzdem
    angeboten.
    """

    record = MigrationRecord(
        state=MigrationState.COMPLETED.value,
        completed=True,
        target_version="5.0.0",
    )

    assert record.is_completed_for("5.0.0")

    assert not record.is_completed_for("5.1.0")


def test_later_means_this_version_not_forever():

    keeper = store()

    keeper.advance(MigrationState.AVAILABLE, version="5.0.0")

    keeper.postpone("5.0.0")

    record = keeper.load()

    assert record.is_postponed_for("5.0.0")

    assert not record.is_postponed_for("5.1.0")


def test_a_failure_keeps_its_reason():

    keeper = store()

    keeper.advance(MigrationState.AVAILABLE, version="5.0.0")

    keeper.advance(MigrationState.CONFIRMED)

    keeper.advance(MigrationState.FAILED, error="Pruefsumme stimmt nicht")

    record = keeper.load()

    assert record.status is MigrationState.FAILED

    assert "Pruefsumme" in record.error


def test_an_unknown_state_in_the_file_does_not_crash_anything():
    """
    Eine von Hand veraenderte oder aeltere Konfiguration darf den
    Start nicht verhindern - sie faellt auf "nichts verfuegbar"
    zurueck.
    """

    config = FakeConfig()

    config.data[STATE_KEY] = {"state": "voellig anders", "unbekannt": 1}

    assert MigrationStore(config).load().status is MigrationState.NOT_AVAILABLE


def test_without_a_configuration_nothing_is_written():
    """
    Der Probelauf benutzt genau das: ein Zustandsspeicher ohne
    Konfiguration hinterlaesst nichts.
    """

    keeper = MigrationStore(None)

    keeper.advance(MigrationState.AVAILABLE, version="5.0.0")

    assert keeper.load().status is MigrationState.NOT_AVAILABLE
