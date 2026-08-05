"""
Bot-Antwort in eine `FightTimeline` übersetzen.

Dieselbe Rolle und dieselbe Bauart wie
analyzer/providers/warcraftlogs_payload.py, nur für den
Zeitleisten-Endpunkt: reine Umrechnung, kein Netzwerk, und **eine
unvollständige Antwort ist kein Fehler**. Der Bot darf die einzelnen
Blöcke nacheinander nachliefern; was fehlt, bleibt leer, und die
Wiedergabe zeigt dafür schlicht nichts an.

Ein Fallstrick, gegen den hier besonders abgesichert wird: Reihen
unterschiedlicher Länge. Kommen Bossleben mit 180 Werten und die
Schadensreihe eines Spielers mit 174, darf das keinen IndexError
geben - `snapshot_at()` liest ohnehin über eine Interpolation, die
mit jeder Länge zurechtkommt, aber die Reihen werden hier zusätzlich
auf eine plausible Länge gebracht.
"""

from __future__ import annotations

from analyzer.data import avoidable, encounters
from analyzer.models import (
    SUPPORT_DISPEL,
    SUPPORT_INTERRUPT,
    Actor,
    RaidSnapshot,
)
from analyzer.providers.warcraftlogs_payload import (
    _count,
    _flag,
    _mapping,
    _number,
    _percent,
    _sequence,
    _text,
    build_cooldown_usage,
    build_deaths,
    build_events,
    build_heroism_windows,
    build_mechanics,
    build_resurrections,
    build_support_events,
    build_uptimes,
    class_name,
    role_name,
    spec_name,
    snapshot_from_payload,
)
from analyzer.replay.models import (
    AvoidableHit,
    FightTimeline,
    PlayerSeries,
)


def _series(value) -> tuple[float, ...]:
    """
    Eine Zahlenreihe aus der Antwort. Alles, was sich nicht in eine
    endliche Zahl übersetzen lässt, wird zu 0.0 - eine Lücke mitten
    in der Reihe soll die ganze Wiedergabe nicht unbrauchbar machen.
    """

    return tuple(
        _number(entry)
        for entry in _sequence(value)
    )


def _actor(entry: dict) -> Actor:
    """
    Dieselbe Identität wie im Live-Weg - einschließlich der
    Übersetzung der Spezialisierung und der daraus abgeleiteten Rolle.
    Liefe das hier anders, wäre derselbe Spieler in der Wiedergabe ein
    anderer als im Live-Bild, und die Academy würde ihn anders
    bewerten.
    """

    actor_class = class_name(_text(entry.get("class")))

    spec = spec_name(actor_class, _text(entry.get("spec")))

    return Actor(
        name=_text(entry.get("name")),
        class_name=actor_class,
        spec=spec,
        role=role_name(
            _text(entry.get("role")),
            actor_class=actor_class,
            spec=spec,
        ),
    )


def build_player_series(rows: list) -> tuple[PlayerSeries, ...]:

    entries = []

    for row in rows:

        row = _mapping(row)

        actor = _actor(row)

        if not actor.name:
            continue

        entries.append(
            PlayerSeries(
                actor=actor,
                damage=_series(row.get("damage")),
                healing=_series(row.get("healing")),
                damage_taken=_series(row.get("damage_taken")),
                movement_units=_series(row.get("movement")),
                active_seconds=_series(row.get("activity")),
                casts=_series(row.get("casts")),
            )
        )

    return tuple(entries)


def build_avoidable_hits(
    rows: list,
    encounter_name: str = "",
    roles: dict | None = None,
    classify: bool = False,
) -> tuple[AvoidableHit, ...]:
    """
    Die vermeidbaren Einzeltreffer der Zeitleiste.

    Zwei Quellen, und der Unterschied ist wichtig. `avoidable_hits`
    aus der Antwort sind bereits als vermeidbar gemeldet und werden
    unverändert übernommen. `damage_taken_hits` sind dagegen **alle**
    Treffer mit Zeitpunkt - dort fällt das Urteil hier, über
    `analyzer/data/avoidable.py`, mit `classify=True`.

    Dass der Bot die Rohtreffer schickt und nicht sein eigenes Urteil,
    ist Absicht: ob ein Treffer vermeidbar war, hängt von
    Schwierigkeitsgrad und Taktik ab, muss für WeintTV und die Academy
    identisch sein und ohne Bot-Deploy korrigierbar bleiben. Ein
    fehlender Tabelleneintrag ergibt `unknown` und damit **keinen**
    Eintrag - lieber eine Lücke als ein Vorwurf an jemanden, der
    nichts falsch gemacht hat.
    """

    roles = roles or {}

    entries = []

    for row in rows:

        row = _mapping(row)

        name = _text(row.get("player")) or _text(row.get("actor"))

        ability = _text(row.get("ability"))

        if not name or not ability:
            continue

        if classify and not avoidable.is_avoidable(
            encounter_name,
            ability,
            role=roles.get(name, ""),
        ):
            continue

        entries.append(
            AvoidableHit(
                actor_name=name,
                ability=ability,
                at_seconds=_number(row.get("at")),
                amount=_number(row.get("amount")),
                note=_text(row.get("note")),
            )
        )

    entries.sort(key=lambda hit: hit.at_seconds)

    return tuple(entries)


def timeline_from_payload(
    payload: dict,
    source_label: str = "",
) -> FightTimeline:
    """
    Baut die Zeitleiste eines Kampfes aus der Bot-Antwort.

    `aggregate` entsteht aus dem mitgelieferten Gesamtstand, der
    exakt die Form der Einzel-Fight-Antwort hat - dadurch übersetzt
    dieselbe Funktion beide, und der Endstand der Wiedergabe stimmt
    mit dem Archivbild überein.
    """

    payload = _mapping(payload)

    fight = _mapping(payload.get("fight"))

    duration = max(0.0, _number(fight.get("duration")))

    interval = _number(payload.get("interval"), 1.0)

    if interval <= 0:
        interval = 1.0

    aggregate_payload = _mapping(payload.get("aggregate"))

    aggregate = (
        snapshot_from_payload(
            aggregate_payload,
            source_label=source_label or "Wiedergabe",
            live=False,
        )
        if aggregate_payload
        else RaidSnapshot()
    )

    encounter = encounters.lookup(
        encounter_id=_count(fight.get("encounter_id")),
        name=_text(fight.get("name")),
        difficulty_id=_count(fight.get("difficulty_id")),
        raid_size=_count(fight.get("raid_size")),
    ) if _text(fight.get("name")) else aggregate.encounter

    players = _sequence(payload.get("players"))

    heroism_windows = build_heroism_windows(
        _sequence(payload.get("heroism_windows"))
    )

    player_series = build_player_series(players)

    roles = {
        series.actor.name: series.actor.role
        for series in player_series
    }

    encounter_name = (
        encounter.name
        if encounter is not None
        else _text(fight.get("name"))
    )

    #
    # Bereits als vermeidbar gemeldete Treffer und die rohe
    # Trefferliste ergeben zusammen die Liste, aus der die Wiedergabe
    # ihre Schadensaufschlüsselung baut - die zweite Quelle läuft
    # dabei durch die eigene Bewertung (siehe build_avoidable_hits).
    #

    avoidable_hits = build_avoidable_hits(
        _sequence(payload.get("avoidable_hits"))
    ) + build_avoidable_hits(
        _sequence(payload.get("damage_taken_hits")),
        encounter_name=encounter_name,
        roles=roles,
        classify=True,
    )

    return FightTimeline(
        encounter=encounter,
        source_label=source_label or "Wiedergabe",
        pull_number=_count(fight.get("pull_number")),
        duration=duration or aggregate.pull_seconds,
        interval=interval,
        raid_size=_count(fight.get("raid_size")) or aggregate.raid_size,
        battle_res_max=(
            _count(fight.get("battle_res_max"))
            or aggregate.battle_res_max
        ),
        boss_health=_series(payload.get("boss_health")),
        players=player_series,
        deaths=build_deaths(_sequence(payload.get("deaths"))),
        resurrections=build_resurrections(
            _sequence(payload.get("resurrects"))
            or _sequence(payload.get("resurrections"))
        ),
        heroism_windows=heroism_windows,
        cooldown_usage=build_cooldown_usage(
            players,
            duration,
            heroism_windows,
        ),
        avoidable_hits=avoidable_hits,
        interrupts=build_support_events(
            _sequence(payload.get("interrupts")),
            SUPPORT_INTERRUPT,
        ),
        dispels=build_support_events(
            _sequence(payload.get("dispels")),
            SUPPORT_DISPEL,
        ),
        mechanics=(
            build_mechanics(_sequence(payload.get("mechanics")))
            or aggregate.mechanics
        ),
        events=build_events(_sequence(payload.get("events"))),
        damage_taken_totals=aggregate.damage_taken,
        dot_uptimes=(
            build_uptimes(players, "dots", "dot")
            or aggregate.dot_uptimes
        ),
        hot_uptimes=(
            build_uptimes(players, "hots", "hot")
            or aggregate.hot_uptimes
        ),
        buff_uptimes=(
            build_uptimes(players, "buffs", "buff")
            or aggregate.buff_uptimes
        ),
        aggregate=aggregate,
    )
