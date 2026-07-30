"""
Ranglisten aus Summen bauen.

Herausgezogen aus dem WarcraftLogs-Mapper, weil die Wiedergabe
(analyzer/replay) genau dieselbe Rechnung braucht: Summe pro Spieler
zu Wert pro Sekunde, absteigend sortiert, Anteile auf 1 normiert.
Zwei Umsetzungen davon wären zwei Auswertungen, die sich irgendwann
uneinig sind - dieselbe Begründung, aus der WeintTV und die Academy
sich einen Snapshot teilen.
"""

from __future__ import annotations

from analyzer.models import Actor, MetricEntry


def build_ranking(
    rows: list[tuple[Actor, float]] | tuple[tuple[Actor, float], ...],
    duration: float,
) -> tuple[MetricEntry, ...]:
    """
    Sortierte Rangliste mit Anteilen.

    `total` ist die Gesamtsumme des Spielers, `value` der Wert pro
    Sekunde. `duration` wird nach unten auf 1.0 begrenzt, damit die
    erste Sekunde eines Pulls keine Division durch (fast) null ergibt.
    """

    duration = max(1.0, duration)

    rows = [
        (actor, total)
        for actor, total in rows
        if actor is not None and actor.name
    ]

    total_sum = sum(total for _actor, total in rows)

    rows = sorted(rows, key=lambda row: row[1], reverse=True)

    return tuple(
        MetricEntry(
            actor=actor,
            value=total / duration,
            total=total,
            share=(
                total / total_sum
                if total_sum > 0
                else 0.0
            ),
        )
        for actor, total in rows
    )


def split_by_role(
    rows: list[tuple[Actor, float, float]] | tuple[tuple[Actor, float, float], ...],
    duration: float,
) -> tuple[tuple[MetricEntry, ...], tuple[MetricEntry, ...]]:
    """
    Teilt `(actor, damage_total, healing_total)`-Zeilen in Schadens-
    und Heilrangliste.

    Die Aufteilung folgt der Rolle und nicht der Frage, ob ein Wert
    ungleich null ist: ein Heiler, der auch Schaden fährt, gehört
    trotzdem nur in die Heilrangliste - andernfalls stünde er in
    beiden und die Anteile ergäben zusammen mehr als 100 %.
    """

    damage_rows: list[tuple[Actor, float]] = []

    healing_rows: list[tuple[Actor, float]] = []

    for actor, damage, healing in rows:

        if actor is None or not actor.name:
            continue

        if actor.is_healer:
            healing_rows.append((actor, healing))
        else:
            damage_rows.append((actor, damage))

    return (
        build_ranking(damage_rows, duration),
        build_ranking(healing_rows, duration),
    )
