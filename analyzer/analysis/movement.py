"""
Laufwege: Rohkoordinaten in Meter umrechnen.

Der ganze Sinn dieser Datei ist, dass der Umrechnungsfaktor an
**einer** Stelle steht. WarcraftLogs liefert keine Distanzmetrik; die
Zahl entsteht daraus, dass der Bot die Abstände zwischen den
Positionsangaben aufeinanderfolgender Ereignisse summiert. Diese
Summe ist in Karteneinheiten, nicht in Metern, und der Faktor ist
Erfahrungswissen - er wird sich korrigieren müssen.

Zwei Ehrlichkeitshinweise, die bewusst im Code stehen und nicht nur
in der Doku:

- Zwischen zwei Ereignissen wird der Weg als Gerade angenommen. Echtes
  Ausweichen wird dadurch systematisch **unterschätzt**.
- Ohne Ereignisse gibt es keine Position. Wer währenddessen läuft,
  taucht in der Summe nicht auf.

Deshalb ist `MovementEntry.estimated` standardmäßig True, und jede
Anzeige beschriftet den Wert als Schätzung. Als Vergleich innerhalb
eines Pulls (Spieler gegen Rollenschnitt) ist er belastbar, als
absolute Zahl nicht.
"""

from __future__ import annotations

from analyzer.models import MovementEntry


#
# Karteneinheiten je Meter. WarcraftLogs' Koordinaten sind in
# Hundertstel Yard; ein Yard sind gut 0,91 Meter. 100 / 0.9144 ergibt
# den Faktor unten. Wenn sich zeigt, dass die Werte systematisch
# daneben liegen, ist das die einzige Zahl, die geändert werden muss.
#

COORD_UNITS_PER_METER = 109.36


def meters_from_units(units: float) -> float:
    """
    Karteneinheiten in Meter. Negative Eingaben ergeben 0.0 - eine
    Distanz kann nicht negativ sein, und eine kaputte Antwort soll
    keinen unsinnigen Wert erzeugen.
    """

    if units <= 0 or COORD_UNITS_PER_METER <= 0:
        return 0.0

    return units / COORD_UNITS_PER_METER


def build_movement(
    actor_name: str,
    units: float,
    seconds: float,
    avoidable_hits: int = 0,
) -> MovementEntry:
    """
    Eine Laufweg-Zeile aus der Rohsumme.
    """

    meters = meters_from_units(units)

    return MovementEntry(
        actor_name=actor_name,
        meters=meters,
        meters_per_second=(
            meters / seconds
            if seconds > 0
            else 0.0
        ),
        avoidable_hits=max(0, avoidable_hits),
        estimated=True,
    )


def format_meters(meters: float) -> str:
    """
    Deutsche Anzeige eines Laufwegs. Gehört hierher und nicht in jedes
    Widget, das ihn zeigt - dieselbe Begründung wie bei
    RaidSnapshot.pull_clock.
    """

    if meters >= 1000:
        return f"{meters / 1000:.1f} km"

    return f"{meters:.0f} m"
