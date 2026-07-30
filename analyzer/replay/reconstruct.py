"""
Aus einer Zeitleiste den Snapshot einer Sekunde bauen.

Das ist die Stelle, an der die Wiedergabe entsteht. `snapshot_at()`
ist eine reine Funktion: dieselbe Zeitleiste und derselbe Zeitpunkt
ergeben immer denselben Snapshot, egal wie oft und aus welcher
Richtung angesprungen. Nur so ist Scrubbing genauso billig wie
Abspielen.

Sie wird viermal pro Sekunde aufgerufen und darf deshalb weder
blockieren noch werfen - dieselbe Zusicherung wie bei
`RaidDataProvider.snapshot()`.

Eine bewusste Selbstbeschränkung: was sich pro Sekunde **nicht**
ehrlich rekonstruieren lässt, bleibt leer, statt geschätzt zu werden.
Konkret sind das die Verbrauchsgüter und die vollständige
Fähigkeitsaufschlüsselung des erhaltenen Schadens - dafür bräuchte es
je Spieler und Fähigkeit eine eigene Zeitreihe, also Megabyte pro
Kampf. Erst am Ende der Wiedergabe kommen sie aus dem
Gesamtschnappschuss. Interpolierte Uptimes oder erfundene
Fähigkeitsanteile wären genau die Sorte Zahl, die eine tiefgründige
Analyse unglaubwürdig macht.
"""

from __future__ import annotations

from analyzer.analysis.ranking import split_by_role
from analyzer.models import (
    AbilityDamage,
    ActivityEntry,
    CooldownState,
    CooldownUsage,
    DamageTakenEntry,
    MovementEntry,
    RaidSnapshot,
    TankEntry,
    UptimeEntry,
)
from analyzer.replay.models import FightTimeline


#
# Hinweis, der jeden wiedergegebenen Snapshot begleitet. Ohne ihn
# könnte eine Raidleitung eine Wiedergabe für den Live-Stand halten.
#

REPLAY_NOTICE = "Wiedergabe - rekonstruiert aus der Zeitleiste."


def snapshot_at(
    timeline: FightTimeline,
    seconds: float,
    source_label: str = "",
) -> RaidSnapshot:
    """
    Der Stand des Kampfes zur Sekunde `seconds`.

    `seconds` wird auf `[0, duration]` begrenzt - ein Schieberegler
    darf nicht aus dem Kampf herauslaufen können.
    """

    label = source_label or timeline.source_label or "Wiedergabe"

    if not timeline.has_data:
        return RaidSnapshot.empty(label)

    at = max(0.0, min(timeline.duration, seconds))

    #
    # Ranglisten aus den kumulativen Summen bis hierher. Dieselbe
    # Funktion, die auch der WarcraftLogs-Mapper benutzt - zwei
    # Umsetzungen wären zwei Auswertungen, die auseinanderdriften.
    #

    rows = [
        (
            series.actor,
            _value_at(series.damage, at, timeline.interval),
            _value_at(series.healing, at, timeline.interval),
        )
        for series in timeline.players
    ]

    damage, healing = split_by_role(rows, at)

    deaths = tuple(
        death
        for death in timeline.deaths
        if death.at_seconds <= at
    )

    resurrections = tuple(
        event
        for event in timeline.resurrections
        if event.at_seconds <= at
    )

    windows = tuple(
        window
        for window in timeline.heroism_windows
        if window.start <= at
    )

    active_window = next(
        (window for window in windows if window.contains(at)),
        None,
    )

    cooldown_usage = _cooldowns_until(timeline.cooldown_usage, at, windows)

    finished = at >= timeline.duration

    return RaidSnapshot(
        source_label=label,
        live=False,
        in_combat=not finished,
        encounter=timeline.encounter,
        pull_number=timeline.pull_number,
        pull_seconds=at,
        boss_health_percent=_percent_at(
            timeline.boss_health,
            at,
            timeline.interval,
        ),
        raid_size=timeline.raid_size or len(timeline.players),
        deaths=deaths,
        battle_res_charges=max(
            0,
            timeline.battle_res_max - len(resurrections),
        ),
        battle_res_max=timeline.battle_res_max,
        heroism_used=bool(windows),
        heroism_remaining=(
            max(0.0, active_window.end - at)
            if active_window is not None
            else 0.0
        ),
        top_damage=damage,
        top_healing=healing,
        tanks=_tanks_at(timeline, at),
        #
        # Die Live-Cooldownlisten werden aus den Einsatzzeitpunkten
        # abgeleitet. Dadurch funktionieren WeintTVs bestehende
        # Cooldown-Karten während der Wiedergabe unverändert weiter,
        # ohne dass sie etwas von einer Zeitleiste wissen müssten.
        #
        raid_cooldowns=_states_from_usage(cooldown_usage, at, "raid"),
        heal_cooldowns=_states_from_usage(cooldown_usage, at, "heal"),
        #
        # Verbrauchsgüter gelten für den ganzen Kampf und lassen sich
        # nicht sinnvoll auf eine Sekunde herunterbrechen - am Ende
        # kommen sie aus dem Gesamtstand.
        #
        consumables=(
            timeline.aggregate.consumables
            if finished
            else ()
        ),
        mechanics=tuple(
            issue
            for issue in timeline.mechanics
            if issue.at_seconds < 0 or issue.at_seconds <= at
        ),
        warnings=(REPLAY_NOTICE,),
        activity=_activity_at(timeline, at),
        dot_uptimes=_uptimes_at(timeline.dot_uptimes, timeline, at),
        hot_uptimes=_uptimes_at(timeline.hot_uptimes, timeline, at),
        movement=_movement_at(timeline, at),
        damage_taken=_damage_taken_at(timeline, at, finished),
        cooldown_usage=cooldown_usage,
        heroism_windows=windows,
        resurrections=resurrections,
        interrupts=tuple(
            event
            for event in timeline.interrupts
            if event.at_seconds <= at
        ),
        dispels=tuple(
            event
            for event in timeline.dispels
            if event.at_seconds <= at
        ),
    )


#
# --------------------------------------------------
# Reihen lesen
# --------------------------------------------------
#


def _value_at(
    values: tuple[float, ...],
    seconds: float,
    interval: float,
) -> float:
    """
    Der Wert einer kumulativen Reihe zum Zeitpunkt `seconds`, zwischen
    zwei Stützpunkten linear interpoliert.

    Ohne die Interpolation würde jede Anzeige im Takt der Abtastung
    springen - bei achtfacher Geschwindigkeit deutlich sichtbar.
    """

    if not values:
        return 0.0

    if interval <= 0:
        return values[-1]

    position = seconds / interval

    if position <= 0:
        return values[0]

    if position >= len(values) - 1:
        return values[-1]

    lower = int(position)

    fraction = position - lower

    return values[lower] + (values[lower + 1] - values[lower]) * fraction


def _percent_at(
    values: tuple[float, ...],
    seconds: float,
    interval: float,
) -> float:
    """
    Wie `_value_at`, aber auf 0-100 begrenzt und mit 100 als
    Rückfallwert - ein Bossleben ohne Daten ist "noch voll", nicht
    "tot".
    """

    if not values:
        return 100.0

    return max(0.0, min(100.0, _value_at(values, seconds, interval)))


#
# --------------------------------------------------
# Abgeleitete Felder
# --------------------------------------------------
#


def _activity_at(
    timeline: FightTimeline,
    seconds: float,
) -> tuple[ActivityEntry, ...]:

    if seconds <= 0:
        return ()

    entries = []

    for series in timeline.players:

        active = _value_at(series.active_seconds, seconds, timeline.interval)

        casts = _value_at(series.casts, seconds, timeline.interval)

        if active <= 0 and casts <= 0:
            continue

        entries.append(
            ActivityEntry(
                actor_name=series.actor.name,
                active_percent=max(0.0, min(100.0, active / seconds * 100.0)),
                casts=int(casts),
                apm=casts / seconds * 60.0,
            )
        )

    entries.sort(key=lambda entry: entry.active_percent, reverse=True)

    return tuple(entries)


def _movement_at(
    timeline: FightTimeline,
    seconds: float,
) -> tuple[MovementEntry, ...]:

    if seconds <= 0:
        return ()

    from analyzer.analysis.movement import build_movement

    hits_by_name: dict[str, int] = {}

    for hit in timeline.avoidable_hits:

        if hit.at_seconds <= seconds:

            hits_by_name[hit.actor_name] = (
                hits_by_name.get(hit.actor_name, 0) + 1
            )

    entries = []

    for series in timeline.players:

        units = _value_at(
            series.movement_units,
            seconds,
            timeline.interval,
        )

        if units <= 0:
            continue

        entries.append(
            build_movement(
                actor_name=series.actor.name,
                units=units,
                seconds=seconds,
                avoidable_hits=hits_by_name.get(series.actor.name, 0),
            )
        )

    entries.sort(key=lambda entry: entry.meters, reverse=True)

    return tuple(entries)


def _damage_taken_at(
    timeline: FightTimeline,
    seconds: float,
    finished: bool,
) -> tuple[DamageTakenEntry, ...]:
    """
    Erhaltener Schaden zum Zeitpunkt X.

    Die Gesamtsumme kommt aus der Zeitreihe und ist damit exakt. Die
    Aufschlüsselung nach Fähigkeit umfasst während der Wiedergabe
    bewusst nur die vermeidbaren Treffer - die sind einzeln mit
    Zeitpunkt bekannt. Alles Übrige nach Fähigkeit aufzuteilen ginge
    nur durch Raten; die vollständige Aufschlüsselung erscheint am
    Ende aus dem Gesamtstand.
    """

    if finished and timeline.damage_taken_totals:
        return timeline.damage_taken_totals

    if seconds <= 0:
        return ()

    hits_by_name: dict[str, list] = {}

    for hit in timeline.avoidable_hits:

        if hit.at_seconds > seconds:
            continue

        hits_by_name.setdefault(hit.actor_name, []).append(hit)

    entries = []

    for series in timeline.players:

        total = _value_at(
            series.damage_taken,
            seconds,
            timeline.interval,
        )

        hits = hits_by_name.get(series.actor.name, [])

        if total <= 0 and not hits:
            continue

        abilities: dict[str, list] = {}

        for hit in hits:

            abilities.setdefault(hit.ability, []).append(hit)

        breakdown = tuple(
            AbilityDamage(
                ability=ability,
                amount=sum(hit.amount for hit in rows),
                hits=len(rows),
                verdict="avoidable",
                note=rows[0].note,
            )
            for ability, rows in abilities.items()
        )

        avoidable = sum(entry.amount for entry in breakdown)

        entries.append(
            DamageTakenEntry(
                actor_name=series.actor.name,
                total=max(total, avoidable),
                avoidable=avoidable,
                unavoidable=0.0,
                hits=len(hits),
                avoidable_hits=len(hits),
                abilities=breakdown,
            )
        )

    entries.sort(key=lambda entry: entry.total, reverse=True)

    return tuple(entries)


def _uptimes_at(
    rows: tuple[UptimeEntry, ...],
    timeline: FightTimeline,
    seconds: float,
) -> tuple[UptimeEntry, ...]:
    """
    Wirkungsdauern gelten für den ganzen Kampf.

    Sie erst am Ende der Wiedergabe zu zeigen wäre ehrlich, aber
    unbrauchbar - deshalb der Mittelweg: der Gesamtwert wird gezeigt,
    sobald genug Kampf vergangen ist, dass er nicht mehr vom
    Aufbau der ersten Sekunden verzerrt wird. Vorher bleibt die Liste
    leer statt eine hochgerechnete Zahl zu behaupten.
    """

    if timeline.duration <= 0 or seconds < min(20.0, timeline.duration):
        return ()

    return rows


def _tanks_at(
    timeline: FightTimeline,
    seconds: float,
) -> tuple[TankEntry, ...]:
    """
    Die Tank-Übersicht während der Wiedergabe.

    Der Lebensbalken bleibt leer: die Zeitleiste führt keine
    Lebensreihe je Spieler, und einen Wert zu erfinden wäre schlimmer
    als keinen zu zeigen. Erhaltener Schaden dagegen ist exakt
    bekannt.
    """

    entries = []

    for series in timeline.players:

        if not series.actor.is_tank:
            continue

        entries.append(
            TankEntry(
                actor=series.actor,
                health_percent=0.0,
                damage_taken=_value_at(
                    series.damage_taken,
                    seconds,
                    timeline.interval,
                ),
                active_mitigation=False,
            )
        )

    return tuple(entries)


def _cooldowns_until(
    rows: tuple[CooldownUsage, ...],
    seconds: float,
    windows: tuple,
) -> tuple[CooldownUsage, ...]:
    """
    Cooldown-Einsätze bis zum Zeitpunkt X.

    `possible` wird gegen die **bisher** vergangene Zeit gerechnet,
    nicht gegen die Kampfdauer - sonst sähe nach zehn Sekunden jeder
    Spieler so aus, als hätte er fünf Einsätze verschenkt.
    """

    entries = []

    for usage in rows:

        used = tuple(at for at in usage.cast_times if at <= seconds)

        entries.append(
            CooldownUsage(
                actor_name=usage.actor_name,
                ability=usage.ability,
                cast_times=used,
                cooldown=usage.cooldown,
                possible=(
                    int(seconds // usage.cooldown) + 1
                    if usage.cooldown > 0
                    else 0
                ),
                in_burst=sum(
                    1
                    for at in used
                    if any(window.contains(at) for window in windows)
                ),
                category=usage.category,
            )
        )

    return tuple(entries)


def _states_from_usage(
    rows: tuple[CooldownUsage, ...],
    seconds: float,
    category: str,
) -> tuple[CooldownState, ...]:
    """
    Baut aus den Einsatzzeitpunkten die Live-Cooldownzustände.

    Das ist der Kniff, der WeintTVs bestehende Cooldown-Karten
    während der Wiedergabe ohne jede Änderung weiterarbeiten lässt:
    sie bekommen genau die Struktur, die sie aus dem Live-Betrieb
    kennen.
    """

    states = []

    for usage in rows:

        if usage.category != category:
            continue

        if not usage.cast_times:

            states.append(
                CooldownState(
                    name=usage.ability,
                    actor_name=usage.actor_name,
                    ready=True,
                    remaining=0.0,
                    duration=usage.cooldown,
                )
            )

            continue

        remaining = usage.cooldown - (seconds - usage.cast_times[-1])

        states.append(
            CooldownState(
                name=usage.ability,
                actor_name=usage.actor_name,
                ready=remaining <= 0.0,
                remaining=max(0.0, remaining),
                duration=usage.cooldown,
            )
        )

    return tuple(states)
