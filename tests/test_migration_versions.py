"""
Die Versionslogik des Generationswechsels.

Der Fall, um den es geht: 4.1.0 -> 5.0.0 ist ein Wechsel, 4.1.0 ->
4.9.0 ist keiner, und 5.0.0 -> 5.0.0 darf nicht zum zweiten Mal
angeboten werden. Dass das stimmt, haengt an zwei Dingen - einer
strengen Lesart von Versionsangaben (`parse_release`) und daran,
dass die Zielgeneration *gerechnet* und nicht eingetippt wird
(`next_major`).
"""

from core.migration.target import (
    BETA,
    DEVELOPMENT,
    MIGRATION_ENABLED_DEFAULT,
    MigrationTarget,
    STABLE,
    migration_enabled,
    next_major,
    target_for,
)
from core.version import is_newer, major_of, parse_release


class FakeConfig:

    def __init__(self, data=None):

        self.data = data or {}
        self.saved = 0

    def save(self):
        self.saved += 1


# --------------------------------------------------
# Lesen
# --------------------------------------------------


def test_a_tag_is_read_with_or_without_the_v():

    assert parse_release("v5.0.0") == parse_release("5.0.0")


def test_a_prerelease_is_recognisable_as_one():

    version = parse_release("v5.0.0-beta.1")

    assert version.is_prerelease

    assert version.prerelease == "beta.1"


def test_something_that_is_not_a_version_is_not_one():
    """
    `parse_version()` (die alte, nachsichtige Lesart) macht aus
    "latest" die Fassung 0.0.0. Hier lesen wir fremde Tags - und aus
    einem "latest" darf keine Fassung werden, die dann auch noch
    mitverglichen wird.
    """

    for value in ("latest", "nightly", "release-5", "", None):

        assert parse_release(value) is None


def test_major_of_reads_the_generation():

    assert major_of("v5.1.2") == 5

    assert major_of("kaputt") is None


# --------------------------------------------------
# Vergleichen
# --------------------------------------------------


def test_the_generation_change_is_newer():

    assert is_newer("5.0.0", "4.1.0")

    assert is_newer("5.0.0", "4.9.0")


def test_a_later_v4_is_not_a_v5():

    assert is_newer("4.9.0", "4.1.0")

    assert major_of("4.9.0") != 5


def test_the_same_version_is_not_newer():

    assert not is_newer("5.0.0", "5.0.0")


def test_within_the_new_generation_it_keeps_comparing():

    assert is_newer("5.2.0", "5.1.0")


def test_a_finished_version_beats_its_own_prerelease():

    assert is_newer("5.0.0", "5.0.0-rc.1")

    assert not is_newer("5.0.0-rc.1", "5.0.0")


def test_prereleases_are_ordered_by_number_not_by_text():
    """
    "beta.10" kommt nach "beta.9" - als Text waere es davor.
    """

    assert is_newer("5.0.0-beta.10", "5.0.0-beta.9")


# --------------------------------------------------
# Das Ziel
# --------------------------------------------------


def test_the_target_generation_is_the_next_one_not_a_typed_five():

    assert next_major("4.1.0") == 5

    assert next_major("4.9.0") == 5

    #
    # Genau das ist der Grund fuer die Rechnung: eine App, die selbst
    # 5.x ist, sucht 6 - der Wechsel auf 5 kann sich nicht
    # wiederholen.
    #

    assert next_major("5.0.0") == 6


def test_the_default_target_is_the_forever_repository():

    target = target_for(None)

    assert target.slug == "daddler/Companion-Forever"

    assert target.major == 5

    assert target.channel == STABLE


def test_the_target_can_be_overridden_for_testing():

    config = FakeConfig(
        {
            "forever_migration": {
                "repository": "someone/Else",
                "target_major": 7,
                "channel": "beta",
            }
        }
    )

    target = target_for(config)

    assert target.slug == "someone/Else"

    assert target.major == 7

    assert target.channel == BETA


def test_a_target_major_of_zero_means_automatic():

    config = FakeConfig({"forever_migration": {"target_major": 0}})

    assert target_for(config).major == next_major()


# --------------------------------------------------
# Kanaele
# --------------------------------------------------


def _target(channel):

    return MigrationTarget(
        owner="daddler",
        repo="Companion-Forever",
        product_name="Companion-Forever",
        major=5,
        channel=channel,
    )


def test_stable_takes_only_finished_versions():

    target = _target(STABLE)

    assert target.accepts(parse_release("5.0.0"))

    assert not target.accepts(parse_release("5.0.0-beta.1"))

    assert not target.accepts(parse_release("5.0.0-rc.1"))


def test_beta_takes_beta_and_rc_but_not_nightly():

    target = _target(BETA)

    assert target.accepts(parse_release("5.0.0-beta.1"))

    assert target.accepts(parse_release("5.0.0-rc.2"))

    assert not target.accepts(parse_release("5.0.0-nightly.4"))


def test_development_takes_everything_of_its_generation():

    target = _target(DEVELOPMENT)

    assert target.accepts(parse_release("5.0.0-nightly.4"))

    assert target.accepts(parse_release("5.0.0-alpha.1"))


def test_a_version_of_another_generation_is_never_accepted():

    target = _target(DEVELOPMENT)

    assert not target.accepts(parse_release("4.9.0"))

    assert not target.accepts(parse_release("6.0.0"))

    assert not target.accepts(None)


# --------------------------------------------------
# Der Schalter
# --------------------------------------------------


def test_the_migration_is_off_by_default():
    """
    Die wichtigste Zusicherung dieser ganzen Schicht: solange
    Companion-Forever nicht veroeffentlicht ist, tut sie nichts.
    Wer diesen Test aendert, gibt die Migration frei - und das soll
    eine bewusste Handlung sein, kein Nebeneffekt.
    """

    assert MIGRATION_ENABLED_DEFAULT is False

    assert migration_enabled(None) is False

    assert migration_enabled(FakeConfig()) is False


def test_the_switch_can_be_flipped_in_the_configuration():

    config = FakeConfig({"forever_migration": {"enabled": True}})

    assert migration_enabled(config) is True


def test_the_environment_wins_over_the_configuration(monkeypatch):

    config = FakeConfig({"forever_migration": {"enabled": True}})

    monkeypatch.setenv("WEINT_FOREVER_MIGRATION", "0")

    assert migration_enabled(config) is False
