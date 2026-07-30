"""
Erhaltenen Schaden einordnen und daraus Mechanikfehler ableiten.

Hier wird aus "Spieler X bekam 240.000 Schaden von Loderndes
Sonnenlicht" die Aussage "Spieler X hat einen vermeidbaren Treffer
kassiert, Kategorie Bewegung". Die Referenzdaten dafür stehen in
analyzer.data.avoidable; diese Datei enthält nur die Anwendung.

Zwei Regeln, die den Unterschied machen:

1. **Dreiwertig.** Was in den Referenzdaten fehlt, bleibt
   unklassifiziert - nicht "unvermeidbar". Sonst würde jeder Boss
   ohne Referenzdaten alle Spieler tadellos aussehen lassen.
2. **Der Bot gewinnt.** Der Bot darf eigene, handverlesene
   Mechanikregeln mitschicken. Wo eine davon denselben Fehler
   beschreibt wie eine hier abgeleitete Zeile, fliegt die abgeleitete
   raus. Ohne diese Regel stünde derselbe Fehler zweimal in der
   Liste, und die Academy würde ihn doppelt zählen.
"""

from __future__ import annotations

from analyzer.data import avoidable as avoidable_data
from analyzer.models import (
    MECHANIC_OTHER,
    MECHANIC_SOURCE_BOT,
    MECHANIC_SOURCE_LOCAL,
    AbilityDamage,
    DamageTakenEntry,
    MechanicIssue,
)


#
# Ab wie vielen Treffern derselben vermeidbaren Fähigkeit der Fehler
# von "Hinweis" auf "Fehler" hochgestuft wird. Einmal getroffen kann
# Pech sein, dreimal ist ein Muster.
#

SEVERITY_ESCALATION = 3


#
# --------------------------------------------------
# Einordnung
# --------------------------------------------------
#


def classify_abilities(
    encounter_name: str,
    rows: tuple[tuple[str, float, int, str], ...],
    role: str = "",
) -> tuple[AbilityDamage, ...]:
    """
    Reiht rohe `(ability, amount, hits, source_name)`-Zeilen zu
    eingeordneten `AbilityDamage`-Einträgen um.

    Absteigend nach Schadenssumme sortiert, damit die Oberfläche nicht
    sortieren muss.
    """

    entries: list[AbilityDamage] = []

    for ability, amount, hits, source_name in rows:

        ability = (ability or "").strip()

        if not ability:
            continue

        rule = avoidable_data.classify(encounter_name, ability, source_name)

        verdict = avoidable_data.VERDICT_UNKNOWN

        note = ""

        if rule is not None:

            verdict = rule.verdict

            note = rule.note

            #
            # Was für den Tank zum Job gehört, ist für ihn nicht
            # vermeidbar - für alle anderen schon.
            #

            if rule.tank_exempt and role == "tank":
                verdict = avoidable_data.VERDICT_UNAVOIDABLE

        entries.append(
            AbilityDamage(
                ability=ability,
                amount=max(0.0, amount),
                hits=max(0, hits),
                verdict=verdict,
                note=note,
                source_name=source_name or "",
            )
        )

    entries.sort(key=lambda entry: entry.amount, reverse=True)

    return tuple(entries)


def build_damage_taken(
    actor_name: str,
    encounter_name: str,
    rows: tuple[tuple[str, float, int, str], ...],
    role: str = "",
) -> DamageTakenEntry:
    """
    Die Schadenszeile eines Spielers samt Aufteilung in vermeidbar /
    unvermeidbar / nicht eingeordnet.
    """

    abilities = classify_abilities(encounter_name, rows, role)

    total = sum(entry.amount for entry in abilities)

    hits = sum(entry.hits for entry in abilities)

    avoidable_amount = sum(
        entry.amount
        for entry in abilities
        if entry.verdict == avoidable_data.VERDICT_AVOIDABLE
    )

    unavoidable_amount = sum(
        entry.amount
        for entry in abilities
        if entry.verdict == avoidable_data.VERDICT_UNAVOIDABLE
    )

    avoidable_hits = sum(
        entry.hits
        for entry in abilities
        if entry.verdict == avoidable_data.VERDICT_AVOIDABLE
    )

    return DamageTakenEntry(
        actor_name=actor_name,
        total=total,
        avoidable=avoidable_amount,
        unavoidable=unavoidable_amount,
        hits=hits,
        avoidable_hits=avoidable_hits,
        abilities=abilities,
    )


#
# --------------------------------------------------
# Ableitung von Mechanikfehlern
# --------------------------------------------------
#


def derive_mechanics(
    entries: tuple[DamageTakenEntry, ...],
    encounter_name: str,
) -> tuple[MechanicIssue, ...]:
    """
    Aus vermeidbaren Treffern werden Mechanikfehler.

    Das ist die Brücke, über die eine Schadenszeile in der Academy
    ankommt: die Kategorie stammt aus den Referenzdaten, und genau
    über sie ordnet der Bewerter den Fehler einem trainierbaren
    Bereich zu.
    """

    issues: list[MechanicIssue] = []

    for entry in entries:

        for ability in entry.abilities:

            if ability.verdict != avoidable_data.VERDICT_AVOIDABLE:
                continue

            rule = avoidable_data.classify(
                encounter_name,
                ability.ability,
                ability.source_name,
            )

            label = rule.label if rule and rule.label else ability.ability

            severity = rule.severity if rule else "warning"

            if ability.hits >= SEVERITY_ESCALATION:
                severity = "error"

            issues.append(
                MechanicIssue(
                    actor_name=entry.actor_name,
                    mechanic=(
                        f"{label} - {ability.note}"
                        if ability.note
                        else label
                    ),
                    count=max(1, ability.hits),
                    severity=severity,
                    category=(
                        rule.category
                        if rule
                        else MECHANIC_OTHER
                    ),
                    source=MECHANIC_SOURCE_LOCAL,
                )
            )

    return tuple(issues)


def merge_mechanics(
    bot_rows: tuple[MechanicIssue, ...],
    derived_rows: tuple[MechanicIssue, ...],
) -> tuple[MechanicIssue, ...]:
    """
    Führt die vom Bot gelieferten und die hier abgeleiteten
    Mechanikfehler zusammen, ohne denselben Fehler doppelt zu zählen.

    Der Bot gewinnt: seine Zeilen sind handverlesen und stehen zuerst.
    Eine abgeleitete Zeile fällt weg, wenn der Bot für denselben
    Spieler schon etwas zu derselben Fähigkeit gemeldet hat.

    Die Erkennung läuft über zwei Wege, weil die Texte in
    verschiedenen Sprachen entstehen: identischer Fehlertext, oder
    derselbe Spieler und eine Fähigkeit, die über
    analyzer.data.avoidable.ABILITY_ALIASES auf den deutschen
    Bot-Text abgebildet ist.
    """

    merged: list[MechanicIssue] = []

    taken_texts: set[tuple[str, str]] = set()

    taken_abilities: set[tuple[str, str]] = set()

    for issue in bot_rows:

        actor = issue.actor_name.casefold()

        merged.append(issue)

        taken_texts.add((actor, issue.mechanic.casefold()))

        #
        # Der Bot-Text nennt die Fähigkeit auf Deutsch. Über die
        # Alias-Tabelle wird daraus der englische Name, unter dem die
        # abgeleitete Zeile entstanden wäre.
        #

        for alias, ability in avoidable_data.ABILITY_ALIASES.items():

            if alias in issue.mechanic.casefold():
                taken_abilities.add((actor, ability.casefold()))

    for issue in derived_rows:

        actor = issue.actor_name.casefold()

        if (actor, issue.mechanic.casefold()) in taken_texts:
            continue

        if _mentions_taken_ability(issue, actor, taken_abilities):
            continue

        merged.append(issue)

    return tuple(merged)


def _mentions_taken_ability(
    issue: MechanicIssue,
    actor: str,
    taken_abilities: set[tuple[str, str]],
) -> bool:
    """
    Ob der Fehler eine Fähigkeit betrifft, die der Bot für denselben
    Spieler schon gemeldet hat.
    """

    text = issue.mechanic.casefold()

    for taken_actor, ability in taken_abilities:

        if taken_actor != actor:
            continue

        #
        # Die abgeleitete Zeile trägt das deutsche Label; über die
        # Alias-Tabelle wird geprüft, ob es zum englischen Namen des
        # Bot-Treffers gehört.
        #

        for alias, aliased in avoidable_data.ABILITY_ALIASES.items():

            if aliased.casefold() == ability and alias in text:
                return True

    return False


def has_usable_classification(entry: DamageTakenEntry | None) -> bool:
    """
    Ob aus dieser Zeile überhaupt eine Bewertung entstehen darf.

    Unter der Mindestquote fehlen zu viele Referenzdaten, und eine
    Bewertung würde nur die Lücken der Tabelle abbilden statt das
    Spiel des Spielers.
    """

    if entry is None or entry.total <= 0:
        return False

    return entry.classified_share >= avoidable_data.MIN_CLASSIFIED_SHARE


def bot_mechanics(rows: tuple[MechanicIssue, ...]) -> tuple[MechanicIssue, ...]:
    """
    Markiert vom Bot gelieferte Zeilen als solche - der Mapper baut
    sie ohne Herkunft, und der Standard ist bereits `bot`, aber
    explizit ist besser als implizit, wenn davon eine Vorrangregel
    abhängt.
    """

    return tuple(
        issue
        if issue.source == MECHANIC_SOURCE_BOT
        else MechanicIssue(
            actor_name=issue.actor_name,
            mechanic=issue.mechanic,
            count=issue.count,
            severity=issue.severity,
            category=issue.category,
            source=MECHANIC_SOURCE_BOT,
            at_seconds=issue.at_seconds,
        )
        for issue in rows
    )
