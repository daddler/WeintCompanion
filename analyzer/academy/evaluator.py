"""
Auswertung: aus einem Kampf wird ein Lernprofil, aus dem Lernprofil
ein Trainingsplan.

Zwei bewusste Festlegungen:

* **Die Bewertung ist relativ, nicht absolut.** Ein fester
  Schadensschwellenwert wäre nach dem nächsten Ausrüstungsstand
  wertlos. Verglichen wird deshalb mit dem besten Wert der eigenen
  Rolle im selben Kampf.
* **Der Trainingsplan folgt der Schwäche.** Die Reihenfolge der
  Lektionen ergibt sich aus der schlechtesten Bewertung zuerst -
  genau die Reihenfolge, die den größten Fortschritt bringt.
"""

from __future__ import annotations

from analyzer.academy import lessons as lesson_catalog
from analyzer.academy.checks import evaluate_lesson
from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ORDER,
    CATEGORY_OUTPUT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    MAX_STARS,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNKNOWN,
    Lesson,
    LessonResult,
    PlanItem,
    PlayerProfile,
    SkillRating,
    TrainingPlan,
)
from analyzer.analysis.damage import has_usable_classification
from analyzer.models import (
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_OTHER,
    MECHANIC_POSITIONING,
    UPTIME_DOT,
    UPTIME_HOT,
    Actor,
    MetricEntry,
    RaidSnapshot,
)


#
# Wie viele Lektionen ein Trainingsplan höchstens enthält. Mehr
# überfordert; weniger führt zu einem leeren Plan, sobald zwei
# Lektionen erledigt sind.
#

PLAN_LENGTH = 6


#
# Ab welchem Vielfachen des Rollenschnitts ein Laufweg als auffällig
# gilt. Leicht über dem Schnitt zu liegen ist Streuung, kein Fehler -
# und wer viel ausweicht, läuft zwangsläufig mehr.
#

MOVEMENT_TOLERANCE = 1.25


#
# Dasselbe für den Anteil vermeidbaren Schadens. Enger gefasst als
# beim Laufweg, weil hier jeder Prozentpunkt tatsächlich Heilung
# kostet.
#

SURVIVAL_TOLERANCE = 1.1


#
# Bis zu welchem Anteil vermeidbaren Schadens es unabhängig vom Raid
# noch die volle Wertung gibt.
#
# Der Rollenvergleich allein genügt nicht: machen alle
# Schadensausteiler denselben Fehler, liegt jeder genau im Schnitt und
# alle bekämen fünf Sterne. Eine Bewertung, die Gleichförmigkeit
# belohnt, sagt niemandem, dass der ganze Raid etwas falsch macht.
#
# Zehn Prozent sind bewusst kein Ideal, sondern eine erreichbare
# Schwelle. Eine Bewertung, die nur bei nahezu perfektem Spiel volle
# Sterne gibt, verliert ihre Aussagekraft - dann steht überall
# dieselbe schlechte Note und niemand erfährt, woran er wirklich
# arbeiten sollte. Der Wert wird sich mit echten Logs nachjustieren
# lassen; er steht deshalb hier und nicht verstreut in der Rechnung.
#

ABSOLUTE_AVOIDABLE_SHARE = 0.10


#
# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
#


def _stars_from_ratio(ratio: float) -> int:
    """
    Leistungsverhältnis (eigener Wert / bester Wert der Rolle) in
    eine Sternebewertung übersetzen.
    """

    if ratio >= 0.95:
        return 5

    if ratio >= 0.87:
        return 4

    if ratio >= 0.76:
        return 3

    if ratio >= 0.62:
        return 2

    return 1


def _stars_from_mistakes(count: int) -> int:
    """
    Fehleranzahl in eine Sternebewertung übersetzen - fehlerfrei
    ergibt die volle Punktzahl.
    """

    if count <= 0:
        return MAX_STARS

    if count == 1:
        return 4

    if count == 2:
        return 3

    if count <= 4:
        return 2

    return 1


def _find_entry(
    rows: tuple[MetricEntry, ...],
    name: str,
) -> tuple[MetricEntry | None, int]:
    """
    Sucht den Eintrag eines Spielers und liefert zusätzlich seinen
    Platz im Ranking (1-basiert, 0 wenn nicht enthalten).
    """

    for position, entry in enumerate(rows, start=1):

        if entry.actor.name == name:
            return entry, position

    return None, 0


def find_actor(snapshot: RaidSnapshot, name: str) -> Actor | None:
    """
    Sucht einen Spieler in allen Listen eines Snapshots.
    """

    if not name:
        return None

    for rows in (snapshot.top_damage, snapshot.top_healing):

        entry, _position = _find_entry(rows, name)

        if entry is not None:
            return entry.actor

    for tank in snapshot.tanks:

        if tank.actor.name == name:
            return tank.actor

    return None


def roster_names(snapshot: RaidSnapshot) -> tuple[str, ...]:
    """
    Alle Spielernamen eines Snapshots, alphabetisch - die Auswahl,
    die die Academy dem Nutzer anbietet.
    """

    names = set()

    for rows in (snapshot.top_damage, snapshot.top_healing):

        for entry in rows:
            names.add(entry.actor.name)

    for tank in snapshot.tanks:
        names.add(tank.actor.name)

    return tuple(sorted(names))


def _mechanics_of(
    snapshot: RaidSnapshot,
    name: str,
    categories: tuple[str, ...],
) -> int:
    """
    Summiert die Fehler eines Spielers in den genannten Kategorien.
    """

    return sum(
        issue.count
        for issue in snapshot.mechanics
        if issue.actor_name == name and issue.category in categories
    )


def _missing_consumables(snapshot: RaidSnapshot, name: str) -> tuple[str, ...]:

    return tuple(
        state.label
        for state in snapshot.consumables
        if name in state.missing
    )


#
# --------------------------------------------------
# Einzelbewertungen
# --------------------------------------------------
#


def _comparison_group(
    snapshot: RaidSnapshot,
    actor: Actor,
) -> tuple[MetricEntry, ...]:
    """
    Die Vergleichsgruppe eines Spielers.

    Entscheidend ist, dass nach Rolle getrennt wird: ein Tank gegen
    das Schadensranking der Schadensausteiler zu messen, würde ihn
    dauerhaft mit einem Stern bewerten, obwohl er seine Aufgabe
    einwandfrei erfüllt.
    """

    if actor.is_healer:
        return snapshot.top_healing

    if actor.is_tank:

        return tuple(
            entry
            for entry in snapshot.top_damage
            if entry.actor.is_tank
        )

    return tuple(
        entry
        for entry in snapshot.top_damage
        if not entry.actor.is_tank
    )


def _role_peers(
    snapshot: RaidSnapshot,
    actor: Actor,
) -> tuple[str, ...]:
    """
    Die Namen aller Spieler derselben Rolle.

    Die Verallgemeinerung von `_comparison_group`: für Laufwege und
    erhaltenen Schaden gibt es keine Rangliste, aber der Vergleich
    muss trotzdem rollenrelativ bleiben. Bei erhaltenem Schaden ist
    das sogar wichtiger als beim Schaden selbst - ein Tank hat immer
    die höchste absolute Schadenssumme des Raids und macht dabei
    alles richtig.
    """

    names = set()

    for entry in snapshot.top_damage + snapshot.top_healing:

        if entry.actor.role == actor.role:
            names.add(entry.actor.name)

    for tank in snapshot.tanks:

        if tank.actor.role == actor.role:
            names.add(tank.actor.name)

    return tuple(sorted(names))


def _role_average(
    snapshot: RaidSnapshot,
    actor: Actor,
    values: dict[str, float],
) -> float | None:
    """
    Der Mittelwert einer Kennzahl innerhalb der eigenen Rolle.
    """

    peers = [
        values[name]
        for name in _role_peers(snapshot, actor)
        if name in values
    ]

    if not peers:
        return None

    return sum(peers) / len(peers)


def _stars_from_share(share: float) -> int:
    """
    Erfüllungsgrad (0.0 - 1.0) in Sterne übersetzen, für Kennzahlen
    mit einem absoluten Ziel: Aktivzeit, Uptime, genutzte Cooldowns.

    Anders als `_stars_from_ratio` wird hier nicht gegen den besten
    Spieler verglichen, sondern gegen das, was möglich gewesen wäre.
    """

    if share >= 0.95:
        return 5

    if share >= 0.85:
        return 4

    if share >= 0.70:
        return 3

    if share >= 0.50:
        return 2

    return 1


def _stars_from_excess(ratio: float, tolerance: float = 1.25) -> int:
    """
    Für Kennzahlen, bei denen **weniger besser** ist und der Bezug
    der Rollenschnitt ist (Laufweg, Anteil vermeidbaren Schadens).

    Bis zur Toleranzgrenze gibt es die volle Bewertung. Das ist
    Absicht: leicht über dem Schnitt zu liegen ist kein Fehler,
    sondern Streuung - und wer viel ausweicht, läuft zwangsläufig
    mehr als der Durchschnitt.
    """

    if ratio <= tolerance:
        return 5

    if ratio <= tolerance * 1.3:
        return 4

    if ratio <= tolerance * 1.7:
        return 3

    if ratio <= tolerance * 2.2:
        return 2

    return 1


def _combine(parts: tuple[tuple[int, int], ...]) -> int:
    """
    Mehrere Teilbewertungen `(Sterne, Gewicht)` zu einer verrechnen.

    Teile ohne Daten (null Sterne) fallen heraus, statt die Wertung
    nach unten zu ziehen. Bleibt nichts übrig, ist das Ergebnis
    ebenfalls null - also "keine Daten" und keine schlechte Note.
    Genau das macht die Bewertung gegenüber Lücken in der Datenquelle
    robust.
    """

    usable = [
        (stars, weight)
        for stars, weight in parts
        if stars > 0 and weight > 0
    ]

    if not usable:
        return 0

    total = sum(stars * weight for stars, weight in usable)

    weights = sum(weight for _stars, weight in usable)

    return max(1, min(MAX_STARS, round(total / weights)))


def _no_data(category: str, reason: str) -> SkillRating:
    """
    Eine Bewertung, die ausdrücklich keine ist.
    """

    return SkillRating(
        category=category,
        stars=0,
        detail=reason,
    )


#
# --------------------------------------------------
# Rotation
# --------------------------------------------------
#


def _rate_rotation(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Ob die Knöpfe richtig gedrückt wurden.

    Bewusst **ohne** jeden Bezug zum Schadensranking: hoher Schaden
    bei löchriger Aktivzeit heißt gute Ausrüstung, nicht gutes Spiel.
    Der Rang steht jetzt in der eigenen Kategorie "Leistung".

    Zwei Bestandteile: Aktivzeit (wie durchgehend gespielt wurde) und
    die mittlere Wirkungsdauer der eigenen Effekte (ob das Gespielte
    auch oben gehalten wurde). Fehlt eines, zählt das andere allein.
    """

    activity = snapshot.activity_of(actor.name)

    kind = UPTIME_HOT if actor.is_healer else UPTIME_DOT

    uptimes = snapshot.uptimes_of(actor.name, kind)

    if activity is None and not uptimes:

        return _no_data(
            CATEGORY_ROTATION,
            "Keine Angaben zu Aktivzeit oder Wirkungsdauern - die "
            "Datenquelle liefert sie für diesen Kampf nicht.",
        )

    parts = []

    details = []

    if activity is not None:

        parts.append((_stars_from_share(activity.active_percent / 100.0), 2))

        details.append(
            f"Aktivzeit {activity.active_percent:.0f} % · "
            f"{activity.apm:.0f} Aktionen/min"
        )

    if uptimes:

        reached = sum(entry.uptime_percent for entry in uptimes) / len(uptimes)

        #
        # Gegen den hinterlegten Richtwert messen, wo es einen gibt.
        # Neunzig Prozent Uptime sind für einen Effekt hervorragend
        # und für einen anderen mangelhaft.
        #

        expected = [
            entry.expected_percent
            for entry in uptimes
            if entry.expected_percent > 0
        ]

        target = (
            sum(expected) / len(expected)
            if expected
            else 95.0
        )

        parts.append((
            _stars_from_share(min(1.0, reached / target) if target else 0.0),
            1,
        ))

        label = "HoT-Uptime" if actor.is_healer else "DoT-Uptime"

        details.append(f"{label} {reached:.0f} % (Ziel {target:.0f} %)")

    return SkillRating(
        category=CATEGORY_ROTATION,
        stars=_combine(tuple(parts)),
        detail=" · ".join(details),
        metric_text=details[0] if details else "",
    )


#
# --------------------------------------------------
# Leistung
# --------------------------------------------------
#


def _rate_output(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Der Platz im Ranking der eigenen Rolle.

    Das ist wortwörtlich die frühere Rotationsbewertung - sie war nie
    falsch, nur falsch benannt. Als eigener Bereich bleibt sie
    sichtbar, ohne die Frage nach der Spielweise zu überlagern.
    """

    rows = _comparison_group(snapshot, actor)

    entry, position = _find_entry(rows, actor.name)

    metric = "Heilung" if actor.is_healer else "Schaden"

    if entry is None or not rows:

        return _no_data(
            CATEGORY_OUTPUT,
            f"Noch keine {metric}sdaten für diesen Kampf.",
        )

    best = rows[0].value

    ratio = entry.value / best if best > 0 else 0.0

    return SkillRating(
        category=CATEGORY_OUTPUT,
        stars=_stars_from_ratio(ratio),
        detail=(
            f"Platz {position} von {len(rows)} · "
            f"{entry.value / 1000:.1f}k {metric} · "
            f"{ratio * 100:.0f} % der Spitzenleistung"
        ),
        metric_text=f"Platz {position} von {len(rows)}",
    )


#
# --------------------------------------------------
# Cooldowns
# --------------------------------------------------
#


def _rate_cooldowns(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Genutzte gegen mögliche Einsätze - und ob sie zum richtigen
    Zeitpunkt kamen.

    Die frühere Fassung konnte das nicht bewerten und sagte das auch
    ehrlich: aus einem einzelnen Snapshot ging nicht hervor, ob ein
    bereiter Cooldown ungenutzt oder gerade wieder verfügbar war. Mit
    den Einsatzzeitpunkten ist die Frage beantwortbar geworden.
    """

    usage = [
        entry
        for entry in snapshot.cooldowns_of(actor.name)
        if entry.possible > 0
    ]

    missing = _missing_consumables(snapshot, actor.name)

    if not usage:

        #
        # Ohne Cooldown-Daten bleibt nur die alte Näherung über
        # Defensivfehler und Verbrauchsgüter - besser als nichts,
        # aber ausdrücklich als schwache Grundlage gekennzeichnet.
        #

        defensive = _mechanics_of(snapshot, actor.name, (MECHANIC_DEFENSIVE,))

        if not defensive and not missing:

            return _no_data(
                CATEGORY_COOLDOWNS,
                "Keine Angaben zur Cooldown-Nutzung.",
            )

        return SkillRating(
            category=CATEGORY_COOLDOWNS,
            stars=_stars_from_mistakes(defensive + len(missing)),
            detail=_join(
                f"{defensive}× Defensive ungenutzt" if defensive else "",
                "fehlt: " + ", ".join(missing) if missing else "",
            ),
        )

    used = sum(entry.uses for entry in usage)

    possible = sum(entry.possible for entry in usage)

    wasted = sum(entry.wasted for entry in usage)

    efficiency = used / possible if possible else 0.0

    parts = [(_stars_from_share(efficiency), 2)]

    details = [f"{used} von {possible} möglichen Einsätzen"]

    #
    # Ausrichtung auf Burstfenster nur bewerten, wenn es überhaupt
    # welche gab - sonst würde ein Kampf ohne Heldentum jedem eine
    # verpasste Ausrichtung anlasten.
    #

    if snapshot.heroism_windows and used:

        in_burst = sum(entry.in_burst for entry in usage)

        share = in_burst / used

        parts.append((_stars_from_share(share), 1))

        details.append(f"{in_burst} davon im Heldentum")

    if missing:

        details.append("fehlt: " + ", ".join(missing))

    stars = _combine(tuple(parts))

    #
    # Fehlende Verbrauchsgüter sind kein eigener Bereich, aber auch
    # kein Detail: je zwei fehlende kostet einen Stern.
    #

    if missing and stars > 0:

        stars = max(1, stars - len(missing) // 2)

    if wasted:

        details.append(f"{wasted} Einsätze verschenkt")

    return SkillRating(
        category=CATEGORY_COOLDOWNS,
        stars=stars,
        detail=" · ".join(details),
        metric_text=f"{efficiency * 100:.0f} % genutzt",
        at_seconds=(
            snapshot.heroism_windows[0].start
            if snapshot.heroism_windows and stars <= 3
            else -1.0
        ),
    )


#
# --------------------------------------------------
# Movement
# --------------------------------------------------
#


def _rate_movement(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Vermeidbare Treffer zuerst, Laufweg nur als Nebenbedingung.

    Der Laufweg allein taugt nicht als Bewertung: Nahkämpfer, Kiter
    und Soaker müssen mehr laufen als ein Zauberer, und wer eine
    Mechanik ignoriert und stehen bleibt, hätte den kürzesten Weg.
    Was den Raid tatsächlich Leben kostet, sind die Treffer - deshalb
    wiegen sie dreifach, und der Laufweg zählt nur, wenn er
    **deutlich** über dem Rollenschnitt liegt.
    """

    mistakes = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_MOVEMENT, MECHANIC_POSITIONING),
    )

    entry = snapshot.movement_of(actor.name)

    if entry is None and not snapshot.has_data:

        return _no_data(
            CATEGORY_MOVEMENT,
            "Noch keine Kampfdaten.",
        )

    parts = [(_stars_from_mistakes(mistakes), 3)]

    details = [
        f"{mistakes} vermeidbare Treffer durch Bewegung oder Position"
        if mistakes
        else "Keine vermeidbaren Treffer durch Positionierung."
    ]

    if entry is not None:

        average = _role_average(
            snapshot,
            actor,
            {row.actor_name: row.meters for row in snapshot.movement},
        )

        if average and average > 0:

            parts.append((
                _stars_from_excess(
                    entry.meters / average,
                    MOVEMENT_TOLERANCE,
                ),
                1,
            ))

            details.append(
                f"{entry.meters:.0f} m gelaufen (Rollenschnitt "
                f"{average:.0f} m, Schätzung)"
            )

        else:

            details.append(f"{entry.meters:.0f} m gelaufen (Schätzung)")

    return SkillRating(
        category=CATEGORY_MOVEMENT,
        stars=_combine(tuple(parts)),
        detail=" · ".join(details),
        metric_text=(
            f"{entry.meters:.0f} m"
            if entry is not None
            else ""
        ),
        at_seconds=_first_mechanic_moment(
            snapshot,
            actor,
            (MECHANIC_MOVEMENT, MECHANIC_POSITIONING),
        ),
    )


#
# --------------------------------------------------
# Mechaniken
# --------------------------------------------------
#


def _rate_mechanics(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Unterbrechungen, Dispels und bossspezifische Fehler.

    Tode sind hier ausgezogen und stehen jetzt bei "Überleben" -
    dorthin gehören sie sachlich, und sie zweimal zu zählen wäre eine
    doppelte Bestrafung für denselben Vorfall.

    Erfolgreiche Unterbrechungen stehen im Begründungstext, aber
    nicht in der Wertung: wie viele Gelegenheiten jemand hatte, hängt
    von Spezialisierung und Aufstellung ab.
    """

    missed = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_INTERRUPT,),
    )

    other = _mechanics_of(
        snapshot,
        actor.name,
        (MECHANIC_OTHER,),
    )

    if not snapshot.has_data:

        return _no_data(CATEGORY_MECHANICS, "Noch keine Kampfdaten.")

    interrupts = len(snapshot.interrupts_of(actor.name))

    dispels = len(snapshot.dispels_of(actor.name))

    details = []

    if missed:
        details.append(f"{missed} verpasste Unterbrechungen")

    if other:
        details.append(f"{other} weitere Mechanikfehler")

    if interrupts:
        details.append(f"{interrupts}× erfolgreich unterbrochen")

    if dispels:
        details.append(f"{dispels}× entzaubert")

    return SkillRating(
        category=CATEGORY_MECHANICS,
        stars=_stars_from_mistakes(missed + other),
        detail=(
            " · ".join(details)
            if details
            else "Kampfmechaniken sauber ausgeführt."
        ),
        at_seconds=_first_mechanic_moment(
            snapshot,
            actor,
            (MECHANIC_INTERRUPT, MECHANIC_OTHER),
        ),
    )


#
# --------------------------------------------------
# Überleben
# --------------------------------------------------
#


def _rate_survival(snapshot: RaidSnapshot, actor: Actor) -> SkillRating:
    """
    Erhaltener Schaden, sein vermeidbarer Anteil und Tode.

    Der Bereich, den es vorher nicht gab - und der viele Bewertungen
    realistischer macht, weil er die Frage stellt, die im Wipe zählt.

    Zwei Vorsichtsmaßnahmen stecken darin:

    Erstens wird ausschließlich der **Anteil** bewertet, nie die
    absolute Summe. Ein Tank bekommt zwangsläufig den meisten Schaden
    des Raids ab; nach Summe zu bewerten hieße, ihn für seine Aufgabe
    zu bestrafen. Verglichen wird zudem nur innerhalb der eigenen
    Rolle.

    Zweitens: liegt zu wenig eingeordneter Schaden vor - weil für
    diesen Boss noch Referenzdaten fehlen -, gibt es gar keine
    Bewertung. Sonst würde die Note nur die Lücken der Tabelle
    abbilden statt das Spiel des Spielers.
    """

    entry = snapshot.damage_taken_of(actor.name)

    deaths = len(snapshot.deaths_of(actor.name))

    defensive = _mechanics_of(snapshot, actor.name, (MECHANIC_DEFENSIVE,))

    if entry is None or not has_usable_classification(entry):

        if not snapshot.has_data:

            return _no_data(CATEGORY_SURVIVAL, "Noch keine Kampfdaten.")

        if deaths or defensive:

            return SkillRating(
                category=CATEGORY_SURVIVAL,
                stars=_stars_from_mistakes(deaths * 2 + defensive),
                detail=_join(
                    f"{deaths}× gestorben" if deaths else "",
                    (
                        f"{defensive}× Defensive ungenutzt"
                        if defensive
                        else ""
                    ),
                    "Schaden nicht eingeordnet - für diesen Boss fehlen "
                    "Referenzdaten.",
                ),
            )

        return _no_data(
            CATEGORY_SURVIVAL,
            "Erhaltener Schaden konnte nicht eingeordnet werden - für "
            "diesen Boss fehlen noch Referenzdaten.",
        )

    shares = {
        row.actor_name: row.avoidable_share
        for row in snapshot.damage_taken
        if has_usable_classification(row)
    }

    peers = [
        name
        for name in _role_peers(snapshot, actor)
        if name in shares and name != actor.name
    ]

    #
    # Der Rollenvergleich braucht mindestens einen echten Vergleich.
    # Ist man der einzige Spieler seiner Rolle mit Daten, wäre der
    # "Schnitt" der eigene Wert - man würde mit sich selbst verglichen
    # und bekäme immer die volle Wertung, egal wie schlecht der Wert
    # ist.
    #

    average = (
        _role_average(snapshot, actor, shares)
        if peers
        else None
    )

    share = entry.avoidable_share

    #
    # Absolut bewerten und, wo es eine Vergleichsgruppe gibt,
    # zusätzlich relativ - und dann die STRENGERE von beiden nehmen.
    #
    # Nur relativ zu bewerten würde Gleichförmigkeit belohnen: machen
    # alle Schadensausteiler denselben Fehler, läge jeder genau im
    # Schnitt und alle bekämen die volle Wertung. Nur absolut zu
    # bewerten würde umgekehrt Rollen bestrafen, die von der Aufstellung
    # her mehr Vermeidbares abbekommen.
    #

    stars_share = _stars_from_excess(
        share / ABSOLUTE_AVOIDABLE_SHARE if share else 0.0,
        1.0,
    )

    if average and average > 0:

        stars_share = min(
            stars_share,
            _stars_from_excess(share / average, SURVIVAL_TOLERANCE),
        )

    parts = (
        (stars_share, 2),
        (_stars_from_mistakes(deaths * 2 + defensive), 2),
    )

    details = [
        f"{share * 100:.0f} % des erhaltenen Schadens war vermeidbar"
    ]

    if average and average > 0:
        details.append(f"Rollenschnitt {average * 100:.0f} %")

    if entry.avoidable_hits:
        details.append(f"{entry.avoidable_hits} vermeidbare Treffer")

    if deaths:
        details.append(f"{deaths}× gestorben")

    if defensive:
        details.append(f"{defensive}× Defensive ungenutzt")

    own_deaths = snapshot.deaths_of(actor.name)

    return SkillRating(
        category=CATEGORY_SURVIVAL,
        stars=_combine(parts),
        detail=" · ".join(details),
        metric_text=f"{share * 100:.0f} % vermeidbar",
        at_seconds=(
            own_deaths[0].at_seconds
            if own_deaths
            else _first_mechanic_moment(
                snapshot,
                actor,
                (MECHANIC_MOVEMENT, MECHANIC_POSITIONING, MECHANIC_DEFENSIVE),
            )
        ),
    )


#
# --------------------------------------------------
# Gemeinsame Kleinigkeiten
# --------------------------------------------------
#


def _join(*parts: str) -> str:

    return " · ".join(part for part in parts if part)


def _first_mechanic_moment(
    snapshot: RaidSnapshot,
    actor: Actor,
    categories: tuple[str, ...],
) -> float:
    """
    Der Zeitpunkt des ersten passenden Mechanikfehlers - das
    Sprungziel in die Wiedergabe. -1, wenn keiner einen Zeitpunkt
    trägt.
    """

    for issue in snapshot.mechanics:

        if (
            issue.actor_name == actor.name
            and issue.category in categories
            and issue.at_seconds >= 0
        ):
            return issue.at_seconds

    return -1.0


#
# --------------------------------------------------
# Profil
# --------------------------------------------------
#


def build_profile(
    snapshot: RaidSnapshot,
    player_name: str,
) -> PlayerProfile:
    """
    Baut das Lernprofil eines Spielers aus einem Snapshot.

    Ist der Spieler nicht enthalten (z. B. weil gerade kein Kampf
    läuft), entsteht ein leeres Profil mit erklärender Notiz statt
    eines Fehlers - die Oberfläche zeigt dann einfach den Hinweis an.
    """

    actor = find_actor(snapshot, player_name)

    if actor is None:

        return PlayerProfile(
            encounter_name=snapshot.encounter_name,
            sample_size=snapshot.pull_number,
            note=(
                "Noch keine Kampfdaten für diesen Charakter. Sobald "
                "ein Pull ausgewertet wurde, entsteht hier "
                "automatisch ein Lernprofil."
            ),
        )

    ratings = (
        _rate_rotation(snapshot, actor),
        _rate_movement(snapshot, actor),
        _rate_cooldowns(snapshot, actor),
        _rate_mechanics(snapshot, actor),
        _rate_survival(snapshot, actor),
        _rate_output(snapshot, actor),
    )

    #
    # In der Reihenfolge von CATEGORY_ORDER ausgeben, damit die
    # Oberfläche die Zeilen nie umsortieren muss.
    #

    ordered = tuple(
        sorted(
            ratings,
            key=lambda entry: CATEGORY_ORDER.index(entry.category),
        )
    )

    return PlayerProfile(
        actor=actor,
        ratings=ordered,
        encounter_name=snapshot.encounter_name,
        sample_size=snapshot.pull_number,
    )


#
# --------------------------------------------------
# Trainingsplan
# --------------------------------------------------
#


def build_plan(
    profile: PlayerProfile,
    completed: frozenset[str] | set[str] | None = None,
    *,
    snapshot: RaidSnapshot | None = None,
    excluded: frozenset[str] | set[str] | None = None,
) -> TrainingPlan:
    """
    Leitet aus einem Profil die nächsten Lektionen ab und prüft sie
    gegen den gewählten Kampf.

    Vorgehen: die Bereiche werden nach Bewertung sortiert
    (schlechtester zuerst) und reihum je eine Lektion beigesteuert.
    Dadurch beginnt der Plan bei der größten Schwäche, ohne die
    übrigen Bereiche vollständig auszublenden.

    `snapshot` ist bewusst ein **Schlüsselwort**-Argument mit
    Standardwert: die bisherigen Aufrufe `build_plan(profile)` und
    `build_plan(profile, done)` bleiben damit gültig und verhalten
    sich unverändert (ohne Snapshot ist jedes Ergebnis schlicht
    "keine Daten").

    `excluded` sind die vom Spieler abgewählten Lektionen. Gespeichert
    werden Ausschlüsse und nicht Einschlüsse - dadurch ist eine neu
    hinzugefügte Lektion automatisch für alle aktiv, ohne Migration
    und ohne Nachfrage.
    """

    done = frozenset(completed or ())

    hidden = frozenset(excluded or ())

    def _evaluate(lesson: Lesson) -> LessonResult | None:

        if snapshot is None or profile.actor is None:
            return None

        return evaluate_lesson(snapshot, profile.actor, lesson)

    def _item(lesson: Lesson) -> PlanItem:

        return PlanItem(
            lesson=lesson,
            result=_evaluate(lesson),
            completed=lesson.lesson_id in done,
        )

    if not profile.has_data:

        #
        # Ohne Kampfdaten trotzdem ein sinnvoller Einstieg: die
        # allgemeinen Lektionen in fester Reihenfolge.
        #

        generic = [
            lesson
            for lesson in lesson_catalog.GENERIC_LESSONS
            if lesson.lesson_id not in hidden
        ]

        return TrainingPlan(
            items=tuple(_item(lesson) for lesson in generic[:PLAN_LENGTH]),
            completed=done,
        )

    #
    # Je Bereich die noch nicht erledigten Lektionen einsammeln,
    # Spezialisierung zuerst (dafür sorgt lessons_in_category).
    #

    buckets: list[list[Lesson]] = []

    for rating in profile.weakest:

        candidates = [
            lesson
            for lesson in lesson_catalog.lessons_in_category(
                profile.actor,
                rating.category,
                profile.encounter_name,
            )
            if lesson.lesson_id not in done
            and lesson.lesson_id not in hidden
        ]

        if candidates:
            buckets.append(candidates)

    selected: list[Lesson] = []

    seen: set[str] = set()

    #
    # Reihum aus den Bereichen ziehen: erst die jeweils erste
    # Lektion jedes Bereichs, dann die zweite und so weiter.
    #

    while buckets and len(selected) < PLAN_LENGTH:

        for bucket in list(buckets):

            if len(selected) >= PLAN_LENGTH:
                break

            lesson = bucket.pop(0)

            if lesson.lesson_id not in seen:

                selected.append(lesson)

                seen.add(lesson.lesson_id)

            if not bucket:
                buckets.remove(bucket)

    items = [_item(lesson) for lesson in selected]

    #
    # Sortierung nach Handlungsbedarf: was das Log nachweislich
    # bemängelt, steht oben; was es nachweislich bestätigt, unten.
    # Nicht messbare Lektionen liegen dazwischen - sie sind der
    # eigentliche Lernstoff, aber ein belegter Fehler ist dringender.
    #

    order = {
        STATUS_FAILED: 0,
        STATUS_UNKNOWN: 1,
        STATUS_PASSED: 2,
    }

    items.sort(key=lambda item: order.get(item.status, 1))

    #
    # Bereits erledigte Lektionen hinten anhängen, damit der
    # Fortschritt sichtbar bleibt.
    #

    finished = [
        _item(lesson)
        for lesson in lesson_catalog.lessons_for_actor(
            profile.actor,
            profile.encounter_name,
        )
        if lesson.lesson_id in done
        and lesson.lesson_id not in hidden
    ]

    return TrainingPlan(
        items=tuple(items) + tuple(finished),
        completed=done,
    )
