"""
Der Hinweistext, der eine leere Tiefenauswertung erklärt.

Er ist die einzige Stelle, an der WeintTV und die Academy dem Nutzer
sagen, WARUM Karten leer bzw. Bereiche unbewertet bleiben - und die
drei Fälle dürfen nicht durcheinandergeraten: "es läuft kein Raid"
ist etwas anderes als "die Quelle kann das nicht", und nur der
letzte Fall heißt "daran ändert sich bis zum nächsten Bot-Update
nichts".

Das Modul liegt zwar unter gui/, importiert aber kein Qt - deshalb
lässt es sich hier ohne laufende Oberfläche prüfen.
"""

from analyzer.models import (
    ActivityEntry,
    EncounterInfo,
    MovementEntry,
    RaidSnapshot,
)

from gui.widgets.tv.analysis_gap import (
    BLOCK_COOLDOWN_USAGE,
    BLOCK_HEAL_COOLDOWNS,
    BLOCK_MOVEMENT,
    BLOCK_RAID_COOLDOWNS,
    NO_PULL,
    NO_RAID,
    SUMS_ONLY,
    analysis_gap,
    analysis_gap_text,
    block_gap_text,
    rating_gap_text,
)


def _encounter() -> EncounterInfo:

    return EncounterInfo(encounter_id=1, name="Horridon")


def test_without_a_raid_the_reason_is_the_missing_raid():

    snapshot = RaidSnapshot.empty("Simulation")

    assert analysis_gap(snapshot) == NO_RAID

    assert "kein Raid" in analysis_gap_text(snapshot)


def test_between_pulls_the_reason_is_not_blamed_on_the_source():
    """
    Der Fall, der die erste Fassung falsch beschriftet hätte: ein
    erkannter Raid ohne laufenden Pull ist keine Schwäche der
    Datenquelle, sondern schlicht die Vorbereitungsphase.
    """

    snapshot = RaidSnapshot(
        source_label="Simulation",
        raid_size=25,
        encounter=_encounter(),
        in_combat=False,
        pull_seconds=0.0,
    )

    assert analysis_gap(snapshot) == NO_PULL

    text = analysis_gap_text(snapshot)

    assert "kein Pull" in text

    assert "Simulation" not in text


def test_a_running_pull_without_deep_values_blames_the_source():

    snapshot = RaidSnapshot(
        source_label="WarcraftLogs",
        raid_size=25,
        encounter=_encounter(),
        in_combat=True,
        pull_seconds=42.0,
    )

    assert analysis_gap(snapshot) == SUMS_ONLY

    assert "WarcraftLogs" in analysis_gap_text(snapshot)


def test_the_academy_only_explains_the_case_it_can_explain():
    """
    Ohne Raid und zwischen den Pulls steht auf jeder Bewertungszeile
    schon "noch keine Auswertung" - ein zweiter Satz darunter wäre
    nur Wiederholung. Erklärungsbedürftig ist allein der Fall, in dem
    ein Kampf ausgewertet wird und die Bereiche trotzdem leer bleiben.
    """

    assert rating_gap_text(RaidSnapshot.empty("Simulation")) == ""

    assert rating_gap_text(
        RaidSnapshot(
            source_label="Simulation",
            raid_size=25,
            encounter=_encounter(),
        )
    ) == ""

    text = rating_gap_text(
        RaidSnapshot(
            source_label="WarcraftLogs",
            raid_size=25,
            encounter=_encounter(),
            in_combat=True,
            pull_seconds=42.0,
        )
    )

    assert "WarcraftLogs" in text

    assert "keine Daten" in text


def test_a_snapshot_with_deep_values_needs_no_explanation():

    snapshot = RaidSnapshot(
        source_label="Wiedergabe",
        raid_size=25,
        encounter=_encounter(),
        in_combat=True,
        pull_seconds=42.0,
        activity=(
            ActivityEntry(actor_name="Pyrothal", active_percent=93.0),
        ),
    )

    assert snapshot.has_analysis is True

    assert rating_gap_text(snapshot) == ""


# --------------------------------------------------
# Einzelne Blöcke
# --------------------------------------------------
#
# Der Fall, den `has_analysis` nicht abdeckt: die Quelle liefert einen
# Teil der Tiefenauswertung und den Rest nicht. Dann verschwindet der
# erklärende Absatz über dem Bereich (weil "irgendetwas" da ist), und
# übrig bleibt der Platzhalter einer Karte - "Keine Raid-Cooldowns
# erkannt." ist aber von "der Raid hat keine gezündet" nicht zu
# unterscheiden. Genau diese Verwechslung von Datenlücke und Befund
# verhindert im Analyzer `stars == 0`.


def _partial() -> RaidSnapshot:
    """
    Ein laufender Pull, für den die Quelle Aktivzeit liefert - aber
    weder Laufwege noch Cooldowns.
    """

    return RaidSnapshot(
        source_label="WarcraftLogs (Bot)",
        encounter=_encounter(),
        in_combat=True,
        pull_seconds=60.0,
        activity=(
            ActivityEntry(
                actor_name="Njiah",
                active_percent=92.0,
                apm=38.0,
            ),
        ),
    )


def test_a_block_the_source_did_not_send_says_so():

    snapshot = _partial()

    assert snapshot.has_analysis

    for block in (
        BLOCK_MOVEMENT,
        BLOCK_COOLDOWN_USAGE,
        BLOCK_RAID_COOLDOWNS,
        BLOCK_HEAL_COOLDOWNS,
    ):

        text = block_gap_text(snapshot, block)

        assert "WarcraftLogs (Bot)" in text
        assert "nicht übertragen" in text

    assert "Laufwege" in block_gap_text(snapshot, BLOCK_MOVEMENT)
    assert "Heil-Cooldowns" in block_gap_text(snapshot, BLOCK_HEAL_COOLDOWNS)


def test_a_block_with_rows_needs_no_explanation():

    snapshot = RaidSnapshot(
        source_label="Simulation",
        encounter=_encounter(),
        in_combat=True,
        pull_seconds=60.0,
        movement=(
            MovementEntry(actor_name="Njiah", meters=400.0),
        ),
    )

    assert block_gap_text(snapshot, BLOCK_MOVEMENT) == ""


def test_without_any_deep_analysis_the_area_text_explains_it_alone():
    """
    Sonst stünde dieselbe Auskunft einmal über dem Bereich und
    nochmals auf jeder der vier Karten.
    """

    snapshot = RaidSnapshot(
        source_label="WarcraftLogs (Bot)",
        encounter=_encounter(),
        in_combat=True,
        pull_seconds=60.0,
    )

    assert not snapshot.has_analysis

    for block in (
        BLOCK_MOVEMENT,
        BLOCK_COOLDOWN_USAGE,
        BLOCK_RAID_COOLDOWNS,
        BLOCK_HEAL_COOLDOWNS,
    ):
        assert block_gap_text(snapshot, block) == ""


def test_an_unknown_block_name_is_silent_rather_than_wrong():

    assert block_gap_text(_partial(), "erfunden") == ""
