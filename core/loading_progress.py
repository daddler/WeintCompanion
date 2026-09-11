"""
Wie lange ein Abruf noch dauert - und wie man das sagt, ohne etwas
zu behaupten.

Gemeldet wurde: *"Wenn ein Log ausgewertet wird, steht nirgendwo,
dass man erstmal kurz warten muss. Es steht nur, dass es bei längeren
Kämpfen etwas dauert. Der Nutzer sieht nicht, wie lange es dauert und
ab wann man daran arbeiten kann."*

Genau das ist der Unterschied zwischen einer Meldung und einem
Fortschritt. "Bei großen Pulls dauert das etwas" ist keine Auskunft:
es sagt nicht, ob zehn Sekunden oder zwei Minuten gemeint sind, ob
überhaupt noch etwas passiert, und was nachher zu tun ist.

Was hier steht, ist die rechnende Hälfte davon - Qt-frei und ohne
jeden Netzzugriff, damit sie prüfbar bleibt:

* **Die Schätzung hängt an der Kampflänge.** Der Bot liest für einen
  Pull den ganzen Ereignisstrom bei WarcraftLogs; ein
  Zwölf-Minuten-Garrosh kostet ihn ein Vielfaches eines
  Zwei-Minuten-Wipes. Eine feste Zahl wäre für den einen Fall
  Panikmache und für den anderen eine Lüge.
* **Sie lernt mit.** Jeder fertige Abruf wird gemessen und geht in
  den Schnitt ein (`blend()`). Die Erfahrung des eigenen Rechners mit
  dem eigenen Bot schlägt jede geratene Konstante - und der Bot läuft
  auf 0,15 vCPU, da entscheidet die Tageszeit mit.
* **Der Balken erreicht nie 100 %.** Er *nähert* sich an. Ein Balken,
  der bei 100 % stehen bleibt, während noch etwas läuft, ist die
  häufigste Lüge in Benutzeroberflächen überhaupt; hier läuft er
  stattdessen sichtbar langsamer weiter, und der Text sagt ab der
  Schätzung ausdrücklich, dass es länger dauert als üblich.
* **Null heisst unbekannt.** Ohne bekannte Kampflänge gibt es keine
  Schätzung, und dann sagt die Oberfläche das - dieselbe Regel wie
  `stars == 0` und `at == -1`.
"""

from __future__ import annotations

import math


#
# Grundlast eines Abrufs: Anfrage, Antwortweg, Auspacken. Sie fällt
# auch für den kürzesten Pull an.
#

BASE_SECONDS = 8.0


#
# Was jede Minute Kampf zusätzlich kostet. Erfahrungswert aus dem
# Bot-Log; er wird von `blend()` ohnehin überschrieben, sobald echte
# Messungen vorliegen.
#

SECONDS_PER_FIGHT_MINUTE = 6.0


#
# Grenzen der Schätzung. Nach unten, damit die Anzeige nicht sofort
# "dauert länger als üblich" sagt; nach oben, damit ein Ausreisser
# (ein Abruf, der in einen Bot-Neustart lief) nicht dazu führt, dass
# der nächste Balken minutenlang stillzustehen scheint.
#

MIN_ESTIMATE = 12.0

MAX_ESTIMATE = 300.0


#
# Wie viele Messungen in den Schnitt eingehen. Wenige: der Bot ist
# mal schnell und mal langsam, aber die letzten Abrufe sagen mehr
# über den aktuellen Zustand als die von gestern.
#

MEMORY = 5


def estimate(fight_seconds: float, measured: tuple[float, ...] = ()) -> float:
    """
    Wie lange dieser Abruf voraussichtlich dauert, in Sekunden.

    `measured` sind die zuletzt gemessenen Abrufdauern dieser Sitzung
    (jüngste zuletzt). Sind welche da, verschieben sie die Schätzung;
    sind keine da, bleibt es beim Modell aus Grundlast und Kampflänge.
    """

    fight_seconds = max(0.0, float(fight_seconds or 0.0))

    modell = BASE_SECONDS + (fight_seconds / 60.0) * SECONDS_PER_FIGHT_MINUTE

    if measured:

        letzte = tuple(measured)[-MEMORY:]

        schnitt = sum(letzte) / len(letzte)

        #
        # Die Messung gewinnt, aber nicht allein: sie kennt die Länge
        # des gerade gewählten Pulls nicht. Der Anteil wächst mit der
        # Zahl der Messungen - eine einzelne kann ein Ausreisser sein.
        #

        gewicht = min(0.75, 0.25 * len(letzte))

        modell = modell * (1.0 - gewicht) + schnitt * gewicht

    return max(MIN_ESTIMATE, min(MAX_ESTIMATE, modell))


def blend(measured: tuple[float, ...], seconds: float) -> tuple[float, ...]:
    """
    Eine frische Messung anhängen und die Liste kurz halten.

    Unsinnige Werte (negativ, oder länger als die Obergrenze) fliegen
    raus, statt die nächste Schätzung zu verderben.
    """

    if seconds <= 0 or seconds > MAX_ESTIMATE * 2:
        return tuple(measured)[-MEMORY:]

    return (*tuple(measured), float(seconds))[-MEMORY:]


def share(elapsed: float, expected: float) -> float:
    """
    Wie voll der Balken steht, 0.0 - 1.0 (ausschliesslich).

    Bis zur Schätzung läuft er gleichmässig auf 0,9; danach nähert er
    sich asymptotisch der 1 an, ohne sie je zu erreichen. Damit ist
    "läuft noch" und "dauert länger als gedacht" am Balken selbst
    ablesbar, und es wird nie behauptet, etwas sei fertig.
    """

    elapsed = max(0.0, float(elapsed or 0.0))

    if expected <= 0:
        return 0.0

    if elapsed <= expected:
        return min(0.9, elapsed / expected * 0.9)

    ueberzug = (elapsed - expected) / expected

    return 0.9 + 0.099 * (1.0 - math.exp(-ueberzug))


def overdue(elapsed: float, expected: float) -> bool:
    """
    Ob der Abruf länger dauert als geschätzt.
    """

    return expected > 0 and elapsed > expected


def _clock(seconds: float) -> str:

    seconds = max(0, int(seconds))

    if seconds < 60:
        return f"{seconds} s"

    return f"{seconds // 60}:{seconds % 60:02d} min"


def progress_text(
    elapsed: float,
    expected: float,
    what: str = "Der Pull",
) -> str:
    """
    Die eine Zeile, die während des Wartens dasteht.

    Drei Fälle, drei Sätze - und alle drei nennen eine Zahl, die sich
    weiterbewegt. Ohne eine solche Zahl ist von aussen nicht zu
    unterscheiden, ob noch etwas läuft oder ob etwas hängt.
    """

    elapsed = max(0.0, float(elapsed or 0.0))

    if expected <= 0:

        return (
            f"{what} wird gelesen … {_clock(elapsed)}. Wie lange es "
            "dauert, lässt sich für diesen Kampf nicht abschätzen."
        )

    if elapsed > expected:

        return (
            f"{what} wird gelesen … {_clock(elapsed)}, und damit "
            f"länger als die üblichen {_clock(expected)}. Der Bot "
            "liest weiter; abbrechen musst du nichts."
        )

    return (
        f"{what} wird gelesen … {_clock(elapsed)} von etwa "
        f"{_clock(expected)}."
    )


#
# Was nach dem Warten passiert. Der Satz, der bisher nirgends stand -
# und der eigentliche Grund für die Rückfrage: dass sich beide Seiten
# von selbst füllen, weiss nur, wer es einmal erlebt hat.
#

READY_NOTE = (
    "Sobald er da ist, füllen sich WeintTV und die Academy von "
    "selbst - du musst nichts erneut anklicken."
)


#
# Warum es überhaupt dauert. Einmal formuliert, weil er auf drei
# Seiten steht.
#

WHY_NOTE = (
    "Der Bot liest dafür den vollständigen Ereignisstrom des Kampfes "
    "bei WarcraftLogs - jeden Zauber, jeden Treffer, jeden Tod. Das "
    "ist die Arbeit, die danach alle Auswertungen trägt."
)
