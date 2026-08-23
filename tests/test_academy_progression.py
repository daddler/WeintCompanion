"""
Die Lernkurve der Academy - Aufzeichnen, Ordnen, Ablesen.

Ohne Qt und ohne Netz, wie der Rest von `analyzer/`. Geprüft wird vor
allem das, was ohne sichtbares Symptom bricht: ein Pull, der zweimal
gezählt wird, eine Kurve in der Reihenfolge der Klicks statt der
Kämpfe, und ein unbewerteter Bereich, der als Null in die Linie
geht - der letzte wäre in der Anzeige von einem eingebrochenen
Ergebnis nicht zu unterscheiden.
"""

import json

from analyzer.academy.models import (
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ROTATION,
    PlayerProfile,
    SkillRating,
)
from analyzer.academy.progression import (
    MIN_PULL_SECONDS,
    PullRecord,
    build_trend,
    from_dict,
    pull_key,
    qualifies,
    record_from_profile,
    select,
    sort_records,
    summary_text,
    to_dict,
    weakest_category,
)
from analyzer.models import Actor, EncounterInfo, RaidSnapshot

from core.academy_history import HISTORY_FILE, AcademyHistory, day_from_iso
from core.paths import Paths


# --------------------------------------------------
# Hilfsmittel
# --------------------------------------------------


def _snapshot(
    in_combat=False,
    seconds=240.0,
    raid_size=25,
    pull=3,
    boss="Malkorok",
    health=0.0,
):

    return RaidSnapshot(
        in_combat=in_combat,
        encounter=EncounterInfo(encounter_id=1, name=boss),
        pull_number=pull,
        pull_seconds=seconds,
        raid_size=raid_size,
        boss_health_percent=health,
    )


def _profile(spec="Vergeltung", **stars):

    return PlayerProfile(
        actor=Actor(name="Njiah", class_name="Paladin", spec=spec),
        ratings=tuple(
            SkillRating(category=category, stars=value)
            for category, value in stars.items()
        ),
    )


def _record(key, day="2026-08-12", sequence=0, source="warcraftlogs", **stars):

    return PullRecord(
        key=key,
        day=day,
        sequence=sequence,
        source=source,
        spec="Vergeltung",
        encounter="Malkorok",
        ratings=tuple(stars.items()),
    )


# --------------------------------------------------
# Was aufgezeichnet wird
# --------------------------------------------------


def test_a_running_pull_is_never_recorded():
    """
    Während des Kampfes ändern sich alle sechs Bewertungen im
    Sekundentakt. Ein Punkt aus der Mitte beschriebe einen Pull, den
    es so nie gab - und in der Wiedergabe entstünde einer je Bild.
    """

    assert not qualifies(_snapshot(in_combat=True))

    assert qualifies(_snapshot(in_combat=False))


def test_the_pause_between_two_pulls_is_not_a_pull():
    """
    Die Simulation liefert zwischen zwei Pulls ausdrücklich einen
    Snapshot ohne Raid - `has_data` ist dort falsch.
    """

    assert not qualifies(_snapshot(raid_size=0, seconds=0.0))


def test_an_instant_wipe_stays_out_of_the_curve():
    """
    Zwölf Sekunden haben keine Aktivzeit, keine Wirkungsdauern und
    keine Cooldowns. Was der Bewerter daraus rechnet, misst den Pull
    und nicht den Spieler.
    """

    assert not qualifies(_snapshot(seconds=MIN_PULL_SECONDS - 1))

    assert qualifies(_snapshot(seconds=MIN_PULL_SECONDS))


def test_an_unrated_area_is_no_point_at_all():
    """
    `stars == 0` heisst "keine Daten" und ist keine schlechte
    Bewertung - der Bereich darf deshalb gar nicht erst im Datensatz
    landen. Als Null in der Kurve wäre er von einem Einbruch nicht zu
    unterscheiden.
    """

    record = record_from_profile(
        _profile(rotation=4, movement=0, mechanics=2),
        _snapshot(),
        key="k",
    )

    assert record.stars(CATEGORY_ROTATION) == 4

    assert record.stars(CATEGORY_MOVEMENT) == 0

    assert [name for name, _ in record.ratings] == [
        CATEGORY_ROTATION,
        CATEGORY_MECHANICS,
    ]


def test_the_average_ignores_what_was_not_rated():
    """
    Sonst fiele die Gesamtlinie genau dann, wenn die Datenquelle
    einen Block nicht geliefert hat - und das sähe wie ein schlechter
    Abend aus.
    """

    record = record_from_profile(
        _profile(rotation=4, movement=0, mechanics=2),
        _snapshot(),
        key="k",
    )

    assert record.average == 3.0


def test_a_kill_is_read_the_same_way_as_in_the_pull_history():

    assert record_from_profile(
        _profile(rotation=4), _snapshot(health=0.4), key="k"
    ).killed

    assert not record_from_profile(
        _profile(rotation=4), _snapshot(health=12.0), key="k"
    ).killed


# --------------------------------------------------
# Ein Pull, ein Punkt
# --------------------------------------------------


def test_the_same_archived_fight_always_gets_the_same_key():
    """
    Aus dem Archiv (und aus der Wiedergabe, die von dort kommt) ist
    der Kampf durch Bericht und Kampfnummer eindeutig benannt.
    Derselbe Pull morgen wieder geöffnet darf keinen zweiten Punkt
    ergeben.
    """

    erst = pull_key(_snapshot(), "abc123#7", "2026-08-12")

    spaeter = pull_key(_snapshot(seconds=241.0), "abc123#7", "2026-08-20")

    assert erst == spaeter


def test_a_live_pull_is_keyed_by_its_day():
    """
    Die Live-Quelle nennt keinen Bericht und liefert denselben
    beendeten Kampf minutenlang weiter aus. Innerhalb eines Abends
    ist "dritter Pull auf Malkorok" eindeutig - über zwei Abende
    hinweg wiederholt sich die Nummer, und ohne den Tag verschluckte
    die Kurve den zweiten.
    """

    mittwoch = pull_key(_snapshot(), "", "2026-08-12")

    donnerstag = pull_key(_snapshot(), "", "2026-08-13")

    assert mittwoch != donnerstag

    assert mittwoch == pull_key(_snapshot(seconds=250.0), "", "2026-08-12")


# --------------------------------------------------
# Reihenfolge
# --------------------------------------------------


def test_the_curve_follows_the_fights_and_not_the_clicks():
    """
    Wer im Archiv erst Pull 5 und dann Pull 2 ansieht, hat sie in
    dieser Reihenfolge aufgezeichnet. Als Kurve gelesen wäre das ein
    Rückschritt, den es nie gab.
    """

    spaet = _record("b", sequence=42, rotation=4)

    frueh = _record("a", sequence=11, rotation=2)

    geordnet = sort_records([spaet, frueh])

    assert [record.key for record in geordnet] == ["a", "b"]


def test_an_older_raid_night_sorts_before_a_newer_one():

    geordnet = sort_records([
        _record("neu", day="2026-08-20", sequence=1),
        _record("alt", day="2026-08-12", sequence=99),
    ])

    assert [record.key for record in geordnet] == ["alt", "neu"]


# --------------------------------------------------
# Auswahl
# --------------------------------------------------


def test_the_simulation_never_shares_a_curve_with_a_real_report():
    """
    Die Voreinstellung der Datenquelle ist die Simulation, und ihre
    Pulls sind gerechnet. Sie stehen im selben Speicher, aber nie in
    derselben Kurve.
    """

    records = [
        _record("s1", source="mock", rotation=5),
        _record("w1", source="warcraftlogs", rotation=2),
    ]

    assert [r.key for r in select(records, "mock")] == ["s1"]

    assert [r.key for r in select(records, "warcraftlogs")] == ["w1"]


def test_two_specs_are_two_curves():
    """
    Eine Rotationsbewertung als Frost sagt nichts über die Rotation
    als Feuer; eine Linie durch beide zeigte einen Bruch, den nie
    jemand gespielt hat.
    """

    from dataclasses import replace

    records = [
        _record("a", rotation=4),
        replace(_record("b", rotation=2), spec="Heilig"),
    ]

    assert [r.key for r in select(records, "", "Vergeltung")] == ["a"]


def test_without_a_known_spec_nothing_is_filtered():
    """
    Sonst bliebe die Kurve für jede Quelle leer, die keine
    Spezialisierung meldet - und das sähe von "es gibt keine Pulls"
    nicht anders aus.
    """

    records = [_record("a", rotation=4), _record("b", rotation=3)]

    assert len(select(records, "", "")) == 2


def test_only_the_last_points_are_shown():

    records = [_record(f"k{index}", sequence=index, rotation=3) for index in range(20)]

    gewaehlt = select(records, "", "", 5)

    assert [r.key for r in gewaehlt] == ["k15", "k16", "k17", "k18", "k19"]


# --------------------------------------------------
# Die Kurve selbst
# --------------------------------------------------


def test_one_pull_is_no_trend():
    """
    Eine Linie aus einem Punkt wäre eine Behauptung.
    """

    assert build_trend([_record("a", rotation=3)]) is None


def test_a_missing_area_leaves_a_gap_and_not_a_zero():
    """
    Der Pull ohne Bewertung dieses Bereichs fällt aus der Linie
    heraus; die übrigen rücken zusammen. Ein Nullpunkt wäre die eine
    Sorte Fehler, gegen die dieses Modul geschrieben ist.
    """

    records = [
        _record("a", rotation=4),
        _record("b", mechanics=2),
        _record("c", rotation=5),
    ]

    trend = build_trend(records, CATEGORY_ROTATION)

    assert trend.points == (4.0, 5.0)


def test_the_direction_needs_more_than_a_rounding_difference():
    """
    Der Fall, gegen den die Schwelle geschrieben ist: im zweiten Pull
    wurde ein Bereich *mehr* bewertet, und schon verschiebt sich das
    Mittel - ohne dass jemand anders gespielt hätte. 3,50 auf 3,67
    ist keine Entwicklung.
    """

    gleich = build_trend([
        _record("a", rotation=4, mechanics=3),
        _record("b", rotation=4, mechanics=3, movement=4),
    ])

    assert gleich.direction == "flat"

    besser = build_trend([
        _record("a", rotation=2, mechanics=2),
        _record("b", rotation=4, mechanics=4),
    ])

    assert besser.direction == "up"


def test_the_weakest_area_is_the_average_and_not_the_last_pull():
    """
    Sonst entschiede ein einzelner schlechter Kampf, welche Linie die
    Karte zeigt, und sie sprünge von Pull zu Pull auf einen anderen
    Bereich.
    """

    records = [
        _record("a", rotation=2, mechanics=5),
        _record("b", rotation=2, mechanics=5),
        _record("c", rotation=2, mechanics=1),
    ]

    assert weakest_category(records) == CATEGORY_ROTATION


def test_an_area_with_a_single_point_is_not_the_second_line():

    records = [
        _record("a", rotation=4, mechanics=1),
        _record("b", rotation=3),
    ]

    assert weakest_category(records) == CATEGORY_ROTATION


def test_the_summary_names_the_number_of_pulls_before_the_direction():

    records = [
        _record("a", rotation=2, mechanics=2),
        _record("b", rotation=4, mechanics=4),
    ]

    text = summary_text(records, build_trend(records))

    assert "2 Pulls" in text

    assert "besser" in text


def test_a_single_pull_says_what_is_missing():

    assert "zweite" in summary_text([_record("a", rotation=3)], None)


# --------------------------------------------------
# Ablage
# --------------------------------------------------


def test_a_record_survives_the_round_trip():

    record = _record("a", sequence=7, rotation=4, mechanics=2)

    wieder = from_dict(json.loads(json.dumps(to_dict(record))))

    assert wieder == record


def test_a_record_without_a_single_rating_is_discarded():
    """
    Er trägt nichts zur Kurve bei, und ein Punkt ohne Sterne wäre in
    der Linie eine Null.
    """

    assert from_dict({"key": "a", "ratings": {}}) is None

    assert from_dict({"key": "", "ratings": {"rotation": 3}}) is None

    assert from_dict("kaputt") is None


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


def _history(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    return AcademyHistory(_Manager())


def test_the_same_pull_is_noted_once(tmp_path, monkeypatch):
    """
    Die Live-Quelle liefert denselben beendeten Kampf minutenlang
    weiter aus - ohne diese Prüfung würde aus einem Pull ein ganzer
    Abend voller Punkte.
    """

    history = _history(tmp_path, monkeypatch)

    assert history.note("Njiah", _record("a", rotation=4))

    assert not history.note("Njiah", _record("a", rotation=4))

    assert len(history.all_records("Njiah")) == 1


def test_the_curve_survives_a_restart(tmp_path, monkeypatch):

    history = _history(tmp_path, monkeypatch)

    history.note("Njiah", _record("a", rotation=4))

    history.note("Njiah", _record("b", sequence=2, rotation=5))

    wieder = _history(tmp_path, monkeypatch)

    assert [record.key for record in wieder.all_records("Njiah")] == ["a", "b"]


def test_a_broken_file_is_reported_and_not_fatal(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    (tmp_path / HISTORY_FILE).write_text("{kaputt", encoding="utf-8")

    manager = _Manager()

    history = AcademyHistory(manager)

    assert history.all_records("Njiah") == ()

    assert manager.logger.messages


def test_every_character_has_their_own_curve(tmp_path, monkeypatch):

    history = _history(tmp_path, monkeypatch)

    history.note("Njiah", _record("a", rotation=4))

    assert history.all_records("Bob") == ()


def test_the_report_day_is_read_in_the_local_timezone():
    """
    Der Bot nennt ihn in UTC. Unlesbares bleibt leer - ein geratener
    Tag brächte die Kurve in eine Reihenfolge, die nie jemand
    gespielt hat.
    """

    assert day_from_iso("2026-08-12T18:00:00Z").startswith("2026-08-1")

    assert day_from_iso("") == ""

    assert day_from_iso("übermorgen") == ""


# --------------------------------------------------
# Der Dienst: welcher Pull wirklich aufgezeichnet wird
# --------------------------------------------------


class _ServiceConfig:

    def __init__(self, **values):
        self.data = {"academy_player_name": ""}
        self.data.update(values)

    def save(self):
        pass


class _ServiceManager:

    def __init__(self, **config):
        self.logger = _Logger()
        self.config = _ServiceConfig(**config)


def _service(tmp_path, monkeypatch, name="Njiah"):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    from core.academy_service import AcademyService

    return AcademyService(_ServiceManager(academy_player_name=name))


def _pull_snapshot(name="Njiah", **kwargs):
    """
    Ein beendeter Pull, in dem der Spieler auch vorkommt - sonst
    entstünde ein leeres Profil und damit kein Punkt.
    """

    from dataclasses import replace

    from analyzer.models import MetricEntry

    return replace(
        _snapshot(**kwargs),
        top_damage=(
            MetricEntry(
                actor=Actor(
                    name=name,
                    class_name="Paladin",
                    spec="Vergeltung",
                    role="dps",
                ),
                value=120000.0,
                total=120000.0 * 240,
                share=0.52,
            ),
            MetricEntry(
                actor=Actor(
                    name="Kollege",
                    class_name="Magier",
                    spec="Feuer",
                    role="dps",
                ),
                value=110000.0,
                total=110000.0 * 240,
                share=0.48,
            ),
        ),
    )


def test_a_finished_pull_is_recorded_exactly_once(tmp_path, monkeypatch):
    """
    Die Live-Quelle liefert denselben beendeten Kampf weiter aus -
    aus einem Pull darf trotzdem nur ein Punkt werden.
    """

    service = _service(tmp_path, monkeypatch)

    snapshot = _pull_snapshot()

    assert service.note_snapshot(snapshot, source="warcraftlogs")

    assert not service.note_snapshot(snapshot, source="warcraftlogs")

    assert len(service.curve("Njiah", "warcraftlogs")) == 1


def test_a_running_pull_reaches_nothing(tmp_path, monkeypatch):

    service = _service(tmp_path, monkeypatch)

    assert not service.note_snapshot(
        _pull_snapshot(in_combat=True),
        source="warcraftlogs",
    )

    assert service.curve("Njiah", "warcraftlogs") == ()


def test_without_a_chosen_character_nothing_is_recorded(tmp_path, monkeypatch):
    """
    `resolve_player_name()` rät nicht. Eine Kurve unter einem
    geratenen Namen wäre die Kurve eines Fremden - und sie fiele erst
    Wochen später auf.
    """

    service = _service(tmp_path, monkeypatch, name="")

    assert not service.note_snapshot(_pull_snapshot(), source="warcraftlogs")


def test_a_player_who_was_not_in_the_pull_gets_no_point(tmp_path, monkeypatch):
    """
    Ohne Kampfdaten entsteht ein leeres Profil. Ein Punkt daraus wäre
    eine Null, wo nichts gemessen wurde.
    """

    service = _service(tmp_path, monkeypatch, name="Fremdling")

    assert not service.note_snapshot(_pull_snapshot(), source="warcraftlogs")


def test_the_same_archived_pull_from_two_visits_is_one_point(
    tmp_path,
    monkeypatch,
):

    service = _service(tmp_path, monkeypatch)

    erst = service.note_snapshot(
        _pull_snapshot(),
        origin="abc#7",
        day="2026-08-12",
        sequence=7,
        source="warcraftlogs",
    )

    #
    # Zweiter Besuch, anderer Tag, minimal andere Dauer - derselbe
    # Kampf.
    #

    nochmal = service.note_snapshot(
        _pull_snapshot(seconds=241.0),
        origin="abc#7",
        day="2026-08-12",
        sequence=7,
        source="warcraftlogs",
    )

    assert erst

    assert not nochmal
