"""
Ein Satz über den Kampf, den man gerade vor sich hat.

Bis 2.8.0 stand über der Academy-Bewertung "Horridon · Pull 12 · Ø
3,7/5". Das nennt den Boss und die Note und lässt zwei Dinge weg, die
im Snapshot längst liegen und für eine Bewertung nicht nebensächlich
sind:

    Die Schwierigkeit. Derselbe Boss heroisch und normal sind zwei
    verschiedene Ansprüche. Eine Bewertung ohne diese Angabe lässt
    sich mit keiner anderen vergleichen - auch nicht mit der eigenen
    von letzter Woche.

    Der Ausgang. Ein Wipe bei 80 % erklärt eine schwache
    Cooldown-Wertung von selbst; derselbe Wert nach einem Kill wäre
    ein Befund. Ohne den Ausgang liest man beide gleich.

Qt-frei und in `gui/widgets/tv/`, wie `analysis_gap.py` und aus
demselben Grund: *welcher Satz dasteht* ist genau die Stelle, an der
etwas falsch sein kann, und ein Fenster braucht man dafür nicht.
"""

from __future__ import annotations

from analyzer.models import RaidSnapshot

from core.raid_context import (
    OUTCOME_KILL,
    OUTCOME_OPEN,
    OUTCOME_WIPE,
    outcome_of,
)


def encounter_meta(snapshot: RaidSnapshot, profile) -> str:
    """
    Boss, Schwierigkeit, Pull, Ausgang und Durchschnittsnote - so weit
    bekannt.

    Jeder Teil fällt einzeln weg, wenn er fehlt, statt als Platzhalter
    dazustehen: "Unbekannte Schwierigkeit" ist keine Auskunft, und
    eine erfundene wäre schlimmer.
    """

    if not getattr(profile, "sample_size", 0):
        return ""

    parts = [getattr(profile, "encounter_name", "") or "Kampf"]

    encounter = snapshot.encounter

    if encounter is not None and encounter.difficulty:
        parts.append(encounter.difficulty)

    parts.append(f"Pull {profile.sample_size}")

    outcome = outcome_text(snapshot)

    if outcome:
        parts.append(outcome)

    average = getattr(profile, "average_stars", 0.0)

    #
    # Die Note nur, wenn überhaupt etwas bewertet wurde. `average_stars`
    # ist 0,0, sobald kein Bereich Daten trägt - "Ø 0,0/5" wäre dort
    # die schlechteste Note statt "keine Daten", also genau die
    # Verwechslung, gegen die `stars == 0` im Analyzer geschrieben
    # ist.
    #

    if getattr(profile, "rated", ()) and average > 0:
        parts.append(f"Ø {average:.1f}/5".replace(".", ","))

    return " · ".join(parts)


def average_text(profile) -> str:
    """
    Nur die Durchschnittsnote - "Ø 3,7/5", sonst leerer String.

    Für den Kopf der Lernansicht. Sie nennt dort **nicht** noch einmal
    Boss, Schwierigkeit, Pull und Ausgang: die vier stehen seit 4.0 im
    Kontextblock des Raid Centers, der beim Perspektivwechsel stehen
    bleibt, und ein zweites Mal darunter wären sie die Doppelung, die
    dieser Umbau beseitigt. Was `encounter_meta()` hat und der
    Kontextblock nicht, ist genau diese Note - also bleibt sie hier.

    `encounter_meta()` selbst bleibt unverändert: sie geht als
    `encounterText` ins Addon (siehe `addon/addon_payloads.py`), und
    dort steht kein Kontextblock daneben.
    """

    if not getattr(profile, "sample_size", 0):
        return ""

    average = getattr(profile, "average_stars", 0.0)

    #
    # Die Note nur, wenn überhaupt etwas bewertet wurde. `average_stars`
    # ist 0,0, sobald kein Bereich Daten trägt - "Ø 0,0/5" wäre dort
    # die schlechteste Note statt "keine Daten".
    #

    if not getattr(profile, "rated", ()) or average <= 0:
        return ""

    return f"Ø {average:.1f}/5".replace(".", ",")


def outcome_text(snapshot: RaidSnapshot) -> str:
    """
    Wie der Pull ausging.

    Drei Antworten und nicht zwei: solange gekämpft wird, ist der
    Ausgang **offen**, und ihn als Wipe bei der aktuellen Bossleiste
    auszugeben wäre eine Behauptung über einen Kampf, der noch läuft -
    in einer Wiedergabe sogar viermal je Sekunde eine andere.

    Welcher der drei Fälle vorliegt, entscheidet `outcome_of()` in
    `core/raid_context.py` - dieselbe Ableitung, aus der auch der
    Kopfblock des Raid Centers seinen Ausgang liest. Hier steht nur die
    Formulierung: zwei Ableitungen derselben drei Fälle wären zwei
    Antworten, die beim nächsten Sonderfall auseinanderlaufen.
    """

    outcome = outcome_of(
        snapshot.has_data,
        snapshot.in_combat,
        snapshot.boss_health_percent,
    )

    if outcome == OUTCOME_OPEN:
        return "läuft"

    if outcome == OUTCOME_KILL:
        return "Kill"

    if outcome == OUTCOME_WIPE:
        return f"Wipe bei {snapshot.boss_health_percent:.0f} %"

    return ""
