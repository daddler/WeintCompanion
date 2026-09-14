"""
Der gemeinsame Raid-Kontext - die Qt-freie Hälfte des Umbaus auf 4.0.

Geprüft wird hier `core/raid_context.py`: was der Kopfblock des Raid
Centers über einen Pull sagt, und woher jedes Feld kommt. Das ist die
Stelle, an der ein Fehler am unauffälligsten wäre - ein erfundenes
Datum, ein "Pull 0", ein "Wipe" über einem laufenden Kampf werfen keine
Ausnahme, sie stehen einfach falsch da.

Kein Qt in dieser Datei: die Projektion liest ihren Dienst über
`getattr` und lässt sich deshalb gegen ein paar Attrappen prüfen.
"""

from dataclasses import replace
from datetime import datetime

from analyzer.models import EncounterInfo, RaidSnapshot
from analyzer.providers.warcraftlogs_payload import FightSummary, ReportSummary

from core.raid_context import (
    OUTCOME_KILL,
    OUTCOME_OPEN,
    OUTCOME_UNKNOWN,
    OUTCOME_WIPE,
    RaidContext,
    context_from,
    empty_hint,
    empty_line,
    facts_line,
    instance_line,
    mode_label,
    outcome_of,
    same_pull,
    when_line,
)
from core.raid_state import (
    ArchiveState,
    MODE_ARCHIVE,
    MODE_LIVE,
    MODE_REPLAY,
    ReplayState,
)


REPORT = ReportSummary(
    code="aBcDeF12",
    title="Mittwochsraid",
    zone="Belagerung von Orgrimmar",
    start="2026-09-02T18:30:00+02:00",
)

FIGHT = FightSummary(
    fight_id=3,
    encounter_id=1623,
    encounter_name="Garrosh Höllschrei",
    difficulty="25 Heroisch",
    kill=False,
    boss_percentage=42.0,
    duration=391.0,
    start="2026-09-02T21:43:00+02:00",
    size=25,
    pull_number=17,
)


class _Service:
    """
    Nur die vier Zugänge, die `context_from()` benutzt.
    """

    def __init__(self, snapshot=None, state=None, source="warcraftlogs"):

        self._snapshot = snapshot if snapshot is not None else RaidSnapshot.empty()

        self._state = state if state is not None else ArchiveState()

        self._source = source

    def current(self):
        return self._snapshot

    def archive_state(self):
        return self._state

    def replay_state(self):
        return ReplayState()

    def active_source(self):
        return self._source


def _archive_state(**extra):

    return ArchiveState(
        mode=MODE_ARCHIVE,
        reports=(REPORT,),
        selected_report=REPORT.code,
        fights=(FIGHT,),
        selected_fight=FIGHT.fight_id,
        **extra,
    )


def _pull_snapshot(**extra):

    base = dict(
        source_label="WarcraftLogs",
        in_combat=False,
        encounter=EncounterInfo(
            encounter_id=1623,
            name="Garrosh Höllschrei",
            instance="Belagerung von Orgrimmar",
            difficulty="25 Heroisch",
            raid_size=25,
        ),
        pull_number=17,
        pull_seconds=391.0,
        boss_health_percent=42.0,
        raid_size=25,
    )

    base.update(extra)

    return RaidSnapshot(**base)


# --------------------------------------------------
# Der Ausgang ist dreiwertig
# --------------------------------------------------


def test_a_running_fight_has_an_open_outcome():
    """
    Ihn am aktuellen Bossbalken als Wipe auszugeben wäre eine
    Behauptung über einen Kampf, der noch läuft - in einer Wiedergabe
    viermal je Sekunde eine andere.
    """

    assert outcome_of(True, True, 42.0) == OUTCOME_OPEN

    assert outcome_of(True, False, 42.0) == OUTCOME_WIPE

    assert outcome_of(True, False, 0.0) == OUTCOME_KILL


def test_without_data_there_is_no_outcome_at_all():
    """
    Vier Fälle und nicht drei: "es liegt kein Kampf vor" ist eine
    Auskunft über das Fehlen eines Kampfes, "läuft noch" eine über den
    Kampf.
    """

    assert outcome_of(False, False, 100.0) == OUTCOME_UNKNOWN


def test_the_one_derivation_is_shared_with_the_rating_line():
    """
    `encounter_meta.outcome_text()` formuliert nur - entschieden wird in
    `outcome_of()`. Zwei Ableitungen derselben drei Fälle liefen beim
    nächsten Sonderfall auseinander.
    """

    from gui.widgets.tv.encounter_meta import outcome_text

    assert outcome_text(_pull_snapshot(in_combat=True)) == "läuft"

    assert outcome_text(_pull_snapshot(boss_health_percent=0.0)) == "Kill"

    assert "42" in outcome_text(_pull_snapshot())

    assert outcome_text(RaidSnapshot.empty()) == ""


# --------------------------------------------------
# Woher jedes Feld kommt
# --------------------------------------------------


def test_the_snapshot_says_what_runs_and_the_fight_list_says_when():
    """
    Ein `RaidSnapshot` trägt keinen Zeitstempel des Pulls - er
    beschreibt einen Moment, nicht einen Kalendereintrag. Die
    `FightSummary` dagegen schon. Beides zusammen ergibt den Kontext.
    """

    context = context_from(
        _Service(_pull_snapshot(), _archive_state())
    )

    assert context.boss == "Garrosh Höllschrei"
    assert context.pull_number == 17
    assert context.boss_percent == 42.0
    assert context.outcome == OUTCOME_WIPE

    assert context.started is not None

    expected = datetime.fromisoformat(FIGHT.start).astimezone()

    assert context.started == expected


def test_an_unloaded_pull_is_still_described_by_the_fight_list():
    """
    Zwischen Klick und Antwort des Bots liegen Minuten. In dieser Zeit
    muss der Kopfblock sagen können, auf welchen Pull gewartet wird -
    sonst stünde dort "kein Kampf", während einer unterwegs ist.
    """

    context = context_from(
        _Service(RaidSnapshot.empty(), _archive_state(fight_loading=True))
    )

    assert context.known
    assert context.loading
    assert context.boss == "Garrosh Höllschrei"
    assert context.pull_number == 17
    assert context.outcome == OUTCOME_WIPE


def test_without_a_fight_the_placeholder_boss_name_is_not_adopted():
    """
    `RaidSnapshot.encounter_name` antwortet ohne Kampf mit "Kein
    Kampf". Als Bossname übernommen könnte der Kopfblock nicht mehr
    unterscheiden, ob ein Kampf vorliegt - und verlöre seinen
    Leerzustand samt nächstem Schritt.
    """

    context = context_from(_Service())

    assert context.boss == ""
    assert not context.known


def test_the_archive_identity_is_what_a_deep_link_carries():

    context = context_from(_Service(_pull_snapshot(), _archive_state()))

    assert context.archived
    assert context.report_code == "aBcDeF12"
    assert context.fight_id == 3

    assert not context_from(_Service()).archived


def test_a_replay_is_not_live_although_it_moves():

    state = replace(_archive_state(), mode=MODE_REPLAY)

    context = context_from(_Service(_pull_snapshot(), state))

    assert context.replaying
    assert context.browsing
    assert not context.live


def test_the_character_is_never_guessed():
    """
    Leer heisst "noch niemand gewählt" - dieselbe Regel wie in
    `analyzer/names.py`.
    """

    assert context_from(_Service()).character == ""

    assert context_from(_Service(), "Njiah").character == "Njiah"


# --------------------------------------------------
# Beschriftung
# --------------------------------------------------


def test_the_facts_line_names_pull_outcome_share_and_duration():

    context = context_from(_Service(_pull_snapshot(), _archive_state()))

    assert facts_line(context) == "Pull 17 · Wipe · 42 % · 06:31"


def test_a_kill_does_not_carry_a_boss_share_beside_it():
    """
    "Kill · 0 %" ist dieselbe Auskunft zweimal, und die zweite liest
    sich wie ein Mangel.
    """

    context = context_from(
        _Service(_pull_snapshot(boss_health_percent=0.0), _archive_state())
    )

    line = facts_line(context)

    assert "Kill" in line
    assert "%" not in line


def test_every_part_of_the_facts_line_falls_away_on_its_own():

    assert facts_line(RaidContext()) == ""

    assert facts_line(RaidContext(pull_number=4)) == "Pull 4"


def test_the_instance_line_carries_zone_and_difficulty():

    context = context_from(_Service(_pull_snapshot(), _archive_state()))

    assert instance_line(context) == "BELAGERUNG VON ORGRIMMAR · 25 HEROISCH"


def test_the_raid_size_stands_in_for_an_unknown_difficulty():
    """
    "25er" ist weniger als "25 Heroisch", aber mehr als nichts - und
    vor allem nichts Erfundenes. Dieselbe Regel wie bei
    `FightSummary.difficulty_label`.
    """

    context = RaidContext(instance="Thron des Donners", raid_size=10)

    assert instance_line(context) == "THRON DES DONNERS · 10ER"


def test_an_unknown_moment_stays_empty_instead_of_midnight():
    """
    Eine erfundene Uhrzeit wäre von einer echten nicht zu
    unterscheiden.
    """

    assert when_line(RaidContext()) == ""


def test_the_report_start_stands_in_for_a_missing_pull_time():
    """
    Die Uhrzeit je Pull kennt der Bot erst seit der Runde zu 3.0.0. Der
    Beginn des Berichts ist dann der richtige *Abend* - und mehr
    behauptet die Zeile auch nicht.
    """

    state = _archive_state()

    state = replace(state, fights=(replace(FIGHT, start=""),))

    context = context_from(_Service(RaidSnapshot.empty(), state))

    assert context.started is not None

    assert when_line(context).startswith("Mittwoch")


def test_the_mode_chip_answers_two_questions_in_one_word():
    """
    Bis 3.6.0 taten das zwei Chips auf verschiedenen Seiten - und ein
    "LIVE" neben einem archivierten Pull war dadurch möglich.
    """

    live = context_from(
        _Service(_pull_snapshot(live=True), ArchiveState(mode=MODE_LIVE))
    )

    assert mode_label(live) == "LIVE"

    quiet = context_from(_Service(RaidSnapshot.empty(), ArchiveState()))

    assert mode_label(quiet) == "KEINE DATEN"

    archive = context_from(_Service(_pull_snapshot(), _archive_state()))

    assert mode_label(archive) == "ARCHIV"

    replaying = context_from(
        _Service(_pull_snapshot(), replace(_archive_state(), mode=MODE_REPLAY))
    )

    assert mode_label(replaying) == "WIEDERGABE"


def test_four_empty_situations_get_four_different_sentences():
    """
    Ein gemeinsames "Keine Daten" für "fehlgeschlagen", "lädt gerade",
    "niemand kämpft" und "nichts gewählt" wäre der Zustand, aus dem man
    nicht weiterkommt.
    """

    failed = RaidContext(mode=MODE_ARCHIVE, error="Bot nicht erreichbar")

    loading = RaidContext(loading=True, mode=MODE_ARCHIVE)

    live = RaidContext(mode=MODE_LIVE)

    archive = RaidContext(mode=MODE_ARCHIVE)

    lines = {
        empty_line(failed),
        empty_line(loading),
        empty_line(live),
        empty_line(archive),
    }

    assert len(lines) == 4

    #
    # Und jeder Satz darunter nennt einen nächsten Schritt, nicht den
    # Mangel. Beim Fehlschlag ist der Grund der nächste Schritt.
    #

    for context in (failed, loading, live, archive):
        assert empty_hint(context).strip()

    assert empty_hint(failed) == "Bot nicht erreichbar"


def test_a_failed_fetch_is_not_reported_as_nothing_chosen():
    """
    Der Kopfblock sagte "Kein Pull gewählt", obwohl einer gewählt war -
    und den Grund fand man nur, wenn man von sich aus in die
    Quellenansicht wechselte. Ein Leerzustand, der einen Fehler als
    Absicht ausgibt, ist die schlechteste Sorte Leerzustand.
    """

    state = replace(
        _archive_state(),
        fight_error="Der Bot hat nicht geantwortet.",
    )

    context = context_from(_Service(RaidSnapshot.empty(), state))

    assert context.error == "Der Bot hat nicht geantwortet."

    assert empty_line(context) == "Pull nicht geladen"


def test_a_chosen_but_undescribed_pull_is_loading_not_missing():
    """
    Ein Tiefenverweis wählt Bericht und Kampf, bevor die Pullliste
    dieses Berichts da ist. "Kein Pull gewählt" wäre dann das Gegenteil
    der Wahrheit.
    """

    state = ArchiveState(
        mode=MODE_ARCHIVE,
        selected_report="aBcDeF12",
        selected_fight=3,
    )

    context = context_from(_Service(RaidSnapshot.empty(), state))

    assert context.archived

    assert not context.known

    assert empty_line(context) == "Pull wird geladen …"


def test_live_mode_does_not_inherit_an_old_archive_error():
    """
    Ein Fehler von vorhin über dem laufenden Raid wäre schlicht falsch.
    """

    state = ArchiveState(mode=MODE_LIVE, fight_error="Bot nicht erreichbar")

    assert context_from(_Service(state=state)).error == ""


# --------------------------------------------------
# Perspektivwechsel oder Pullwechsel?
# --------------------------------------------------


def test_a_moving_replay_is_still_the_same_pull():
    """
    Während einer Wiedergabe ändern sich Bossanteil, Dauer und Ausgang
    viermal je Sekunde - der Pull dabei nie. Genau diese Unterscheidung
    braucht das Raid Center, um einen Perspektivwechsel von einem
    Pullwechsel zu trennen.
    """

    first = context_from(_Service(_pull_snapshot(), _archive_state()))

    later = context_from(
        _Service(
            _pull_snapshot(boss_health_percent=8.0, pull_seconds=500.0),
            _archive_state(),
        )
    )

    assert first.boss_percent != later.boss_percent

    assert same_pull(first, later)


def test_another_fight_of_the_same_report_is_another_pull():

    other = replace(_archive_state(), selected_fight=9)

    assert not same_pull(
        context_from(_Service(_pull_snapshot(), _archive_state())),
        context_from(_Service(_pull_snapshot(), other)),
    )


def test_without_an_archive_identity_the_boss_and_pull_decide():
    """
    Der Live-Feed nennt keinen Bericht. Über einen Raidabend hinweg ist
    "dritter Pull auf Malkorok" aber eindeutig - dieselbe Überlegung
    wie bei `progression.pull_key()`.
    """

    live = context_from(
        _Service(_pull_snapshot(live=True), ArchiveState(mode=MODE_LIVE))
    )

    same = context_from(
        _Service(
            _pull_snapshot(live=True, boss_health_percent=3.0),
            ArchiveState(mode=MODE_LIVE),
        )
    )

    assert same_pull(live, same)

    next_pull = context_from(
        _Service(
            _pull_snapshot(live=True, pull_number=18),
            ArchiveState(mode=MODE_LIVE),
        )
    )

    assert not same_pull(live, next_pull)
