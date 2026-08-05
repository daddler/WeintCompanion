"""
Gemeldete Wirkungsdauern und Cooldowns gegen die Spezialisierung
halten.

Die Datenquelle sagt, **was passiert ist**. Erst
analyzer/data/class_abilities.py sagt, **was zu erwarten war** - und
zwischen beidem liegen drei Fehlerquellen, die alle drei still sind
und in der Oberfläche gleich aussehen ("Keine Angaben zu ..."):

1. **Die Sprache.** WarcraftLogs liefert Fähigkeitsnamen in der
   Sprache des Clients, der den Bericht hochgeladen hat. Ein deutscher
   Bericht meldet "Verjüngung", der Lektionskatalog fragt nach
   "Rejuvenation". Derselbe Fehler hat auf der Bot-Seite schon einmal
   sämtliche Cooldown-Listen leer ankommen lassen (siehe
   docs/warcraftlogs-bridge.md).
2. **Die Einsortierung.** Ob ein Effekt ein DoT, ein HoT oder ein
   eigener Buff ist, entscheidet bisher allein die Quelle, indem sie
   ihn in `players[].dots`, `.hots` oder `.buffs` legt. Legt sie einen
   HoT unter die Buffs, bleibt die HoT-Karte leer, obwohl die Zahl da
   ist - und niemand sieht, dass sie nur im falschen Fach liegt.
3. **Das Schweigen.** Eine Fähigkeit, die gar nicht gemeldet wird,
   fehlt in der Liste. Ein Schurke ohne Blutung sieht damit genauso
   aus wie ein Schurke, über dessen Blutung nichts bekannt ist -
   dabei ist das erste ein Befund und das zweite eine Datenlücke.

Diese Datei behebt alle drei, und zwar ohne eine einzige Zahl zu
erfinden:

* Jede gemeldete Zeile wird über Spell-ID, englischen und deutschen
  Namen gegen die Spec-Tabelle gehalten. Trifft sie, bekommt sie
  deren Art (DoT/HoT/Buff) und deren Richtwert.
* Fehlt eine Fähigkeit der Spezialisierung, wird sie mit **null
  Prozent** ergänzt - aber **nur**, wenn die Quelle diese Art
  überhaupt liefert. Eine Null ist eine Behauptung; sie darf nur
  dort stehen, wo die Quelle beweisbar hingesehen hat. Liefert sie
  gar keine HoTs, wird auch keine Null behauptet - dann sagt die
  Oberfläche über `reference_hint()`, was für diese Spec zu sehen
  wäre, und nennt es ausdrücklich eine Erwartung, keine Messung.
* Talent- und glyphenabhängiges (`optional`) wird nie ergänzt. Eine
  Zeile "Inkarnation - nie genutzt" bei jemandem, der das Talent nicht
  gewählt hat, wäre ein Vorwurf für nichts.

Die Ergänzung der möglichen Einsätze bei Cooldowns folgt derselben
Zurückhaltung: gezählt wird nur, was auf Abklingzeit gehört
(`CD_PERSONAL`). Ein ungenutzter Schildwall ist keine verschenkte
Nutzung, sondern ein Kampf, in dem er nicht gebraucht wurde - ihn
mitzuzählen hieße, Tanks und Heiler für Umsicht zu bestrafen.
"""

from __future__ import annotations

from dataclasses import replace

from analyzer.data import class_abilities, player_abilities
from analyzer.models import (
    CD_PERSONAL,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    Actor,
    CooldownUsage,
    RaidSnapshot,
    UptimeEntry,
)


UPTIME_KINDS = (UPTIME_DOT, UPTIME_HOT, UPTIME_BUFF)


def _possible_uses(duration: float, cooldown: float) -> int:
    """
    Wie oft ein Cooldown in dieser Kampfdauer hätte kommen können.

    Dieselbe Rechnung wie in providers/warcraftlogs_payload.py - der
    erste Einsatz kostet keine Abklingzeit, deshalb `+ 1`.
    """

    if cooldown <= 0 or duration <= 0:
        return 0

    return int(duration // cooldown) + 1


def _match(abilities, name: str, spell_id: int = 0, prefer: str = ""):
    """
    Eine gemeldete Fähigkeit in der Spec-Tabelle finden.

    Zwei Anläufe, und der zweite ist der Grund für diese Funktion:
    dieselbe Fähigkeit hat im Umlauf mehrere deutsche Schreibweisen
    ("Mischen" und "Beinarbeit", "Verbrennung" und "Einäschern"), und
    welche ankommt, hängt am Client, der den Bericht hochgeladen hat.
    Trifft der gemeldete Name nichts, wird er über
    analyzer/data/player_abilities.py auf seinen englischen
    Namen gebracht und damit noch einmal gesucht. Ohne diesen zweiten
    Anlauf stünde die gemeldete Zeile neben einer ergänzten
    Referenzzeile derselben Fähigkeit - beide halb richtig.
    """

    prefer = prefer or class_abilities.KIND_AURA

    found = class_abilities.match(abilities, name, spell_id, prefer)

    if found is not None:
        return found

    english = player_abilities.canonical(name)

    if english and english != name:
        return class_abilities.match(abilities, english, 0, prefer)

    return None


def _actors(snapshot: RaidSnapshot) -> dict[str, Actor]:
    """
    Alle bekannten Spieler eines Snapshots, nach Namen greifbar.

    Einmal je Snapshot gebaut statt je Zeile gesucht: hier laufen bis
    zu 150 gemeldete Zeilen durch, und die Spezialisierung steht nur
    am `Actor`.
    """

    return {actor.name: actor for actor in snapshot.actors}


def apply_spec_reference(snapshot: RaidSnapshot) -> RaidSnapshot:
    """
    Den Snapshot um das Wissen über die Spezialisierungen anreichern.

    Rein und ohne Seiteneffekt: gleicher Snapshot rein, gleicher
    Snapshot raus. Sie läuft bei einer Wiedergabe viermal je Sekunde
    über höchstens 25 Spieler, deshalb ausschließlich
    Wörterbuchzugriffe und keine Sortierung mehr als nötig.
    """

    #
    # Ohne Tiefenauswertung ist hier nichts zu tun: eine Quelle, die
    # nur Summen liefert, bekäme sonst eine Liste von Nullen
    # angehängt, die wie ein Befund aussieht. Warum die
    # Tiefenauswertung fehlt, beantwortet gui/widgets/tv/analysis_gap.py.
    #

    if not snapshot.has_analysis:
        return snapshot

    actors = _actors(snapshot)

    if not actors:
        return snapshot

    reference = {
        name: class_abilities.for_actor(actor)
        for name, actor in actors.items()
    }

    uptimes = _apply_uptimes(snapshot, reference)

    cooldowns = _apply_cooldowns(snapshot, reference)

    return replace(
        snapshot,
        dot_uptimes=uptimes[UPTIME_DOT],
        hot_uptimes=uptimes[UPTIME_HOT],
        buff_uptimes=uptimes[UPTIME_BUFF],
        cooldown_usage=cooldowns,
        #
        # Die beiden Live-Listen tragen dieselben Fähigkeiten wie die
        # Rückschau, nur als Countdown. Ohne dieselbe Umbenennung
        # stünde in WeintTV "Rallying Cry" in der einen Karte und
        # "Sammelschrei" in der anderen.
        #
        raid_cooldowns=_rename_states(snapshot.raid_cooldowns),
        heal_cooldowns=_rename_states(snapshot.heal_cooldowns),
    )


def _rename_states(states: tuple) -> tuple:

    return tuple(
        replace(state, name=class_abilities.display_name(state.name))
        for state in states
    )


#
# --------------------------------------------------
# Wirkungsdauern
# --------------------------------------------------
#


def _apply_uptimes(
    snapshot: RaidSnapshot,
    reference: dict,
) -> dict[str, tuple[UptimeEntry, ...]]:

    buckets: dict[str, list[UptimeEntry]] = {
        kind: [] for kind in UPTIME_KINDS
    }

    #
    # Welche Fähigkeit je Spieler schon gemeldet wurde - als
    # Vergleichsform, damit "Verjüngung" und "Rejuvenation" nicht
    # zweimal in der Liste landen.
    #

    seen: set[tuple[str, str]] = set()

    for entry in (
        *snapshot.dot_uptimes,
        *snapshot.hot_uptimes,
        *snapshot.buff_uptimes,
    ):

        abilities = reference.get(entry.actor_name)

        tracked = _match(abilities, entry.ability, entry.spell_id)

        #
        # Die Art kommt aus der Spec-Tabelle, wo sie bekannt ist;
        # sonst aus dem spec-unabhängigen Verzeichnis (eine Quelle
        # kann einen Spieler ohne Spezialisierung melden); sonst
        # bleibt es bei der Einordnung der Quelle.
        #

        kind = (
            tracked.kind
            if tracked is not None and hasattr(tracked, "kind")
            else class_abilities.aura_kind(entry.ability, entry.spell_id)
            or entry.kind
        )

        if kind not in buckets:
            kind = UPTIME_DOT

        expected = entry.expected_percent

        if expected <= 0 and tracked is not None:
            expected = getattr(tracked, "expected_percent", 0.0)

        buckets[kind].append(
            replace(
                entry,
                ability=_display_name(entry.ability, tracked),
                kind=kind,
                expected_percent=expected,
            )
        )

        seen.add((entry.actor_name, _seen_key(entry.ability, tracked)))

    #
    # Nur Arten ergänzen, die die Quelle nachweislich liefert. Sonst
    # entstünde aus einer Datenlücke eine Reihe von Nullen, die wie
    # ein Befund aussieht.
    #

    delivered = {
        kind: bool(rows)
        for kind, rows in buckets.items()
    }

    for name, abilities in reference.items():

        if abilities is None:
            continue

        for kind in UPTIME_KINDS:

            if not delivered[kind]:
                continue

            for aura in abilities.auras_of(kind):

                if aura.optional:
                    continue

                if (name, _seen_key(aura.english, aura)) in seen:
                    continue

                buckets[kind].append(
                    UptimeEntry(
                        actor_name=name,
                        ability=aura.german or aura.english,
                        uptime_percent=0.0,
                        kind=kind,
                        expected_percent=aura.expected_percent,
                    )
                )

    return {
        kind: tuple(
            sorted(rows, key=lambda row: row.uptime_percent, reverse=True)
        )
        for kind, rows in buckets.items()
    }


def _display_name(reported: str, tracked) -> str:
    """
    Unter welchem Namen eine erkannte Fähigkeit angezeigt wird.

    Deutsch, sobald die Spec-Tabelle sie kennt - die Oberfläche ist
    deutsch, und in welcher Sprache ein Bericht ankommt, hängt allein
    davon ab, wer ihn hochgeladen hat. Ohne diese Vereinheitlichung
    stünden in einer Karte "Rejuvenation" und "Verjüngung"
    nebeneinander, sobald eine ergänzte Referenzzeile dazukommt, und
    beides wäre dieselbe Fähigkeit.

    Unbekanntes bleibt, wie es gemeldet wurde: eine Fähigkeit, die
    diese Tabelle noch nicht kennt, darf nicht verschwinden.
    """

    if tracked is None:
        return reported

    return getattr(tracked, "german", "") or reported


def _seen_key(name: str, tracked) -> str:
    """
    Der Schlüssel, unter dem eine Fähigkeit als "schon vorhanden"
    gilt.

    Ist sie in der Spec-Tabelle bekannt, zählt deren englischer Name -
    damit gilt eine deutsch gemeldete Verjüngung als dieselbe
    Fähigkeit wie der Referenzeintrag "Rejuvenation". Ist sie
    unbekannt, zählt der gemeldete Name; sie kann dann ohnehin mit
    keinem Referenzeintrag zusammenfallen.
    """

    if tracked is not None and getattr(tracked, "english", ""):
        return class_abilities.normalize_name(tracked.english)

    return class_abilities.normalize_name(name)


#
# --------------------------------------------------
# Cooldowns
# --------------------------------------------------
#


def _apply_cooldowns(
    snapshot: RaidSnapshot,
    reference: dict,
) -> tuple[CooldownUsage, ...]:

    rows: list[CooldownUsage] = []

    seen: set[tuple[str, str]] = set()

    for entry in snapshot.cooldown_usage:

        abilities = reference.get(entry.actor_name)

        tracked = _match(
            abilities,
            entry.ability,
            entry.spell_id,
            class_abilities.KIND_COOLDOWN,
        )

        cooldown = entry.cooldown

        possible = entry.possible

        if cooldown <= 0 and tracked is not None:
            cooldown = getattr(tracked, "cooldown", 0.0)

        #
        # Die Kategorie der Quelle gewinnt nur, wenn sie eine hat:
        # `build_cooldown_usage` rät sie sonst aus dem Namen, und die
        # Spec-Tabelle weiß es sicher.
        #

        category = entry.category

        if tracked is not None and getattr(tracked, "category", ""):
            category = tracked.category

        #
        # Eine fehlende Obergrenze wird nur für Cooldowns nachgetragen,
        # die auf Abklingzeit gehören. Eine Quelle, die bei einem
        # Defensivcooldown bewusst keine angibt, sagt damit "hier gibt
        # es nichts zu verschenken" - das darf hier nicht überschrieben
        # werden.
        #

        if possible <= 0 and cooldown > 0 and category == CD_PERSONAL:
            possible = _possible_uses(snapshot.pull_seconds, cooldown)

        rows.append(
            replace(
                entry,
                ability=_display_name(entry.ability, tracked),
                cooldown=cooldown,
                possible=max(possible, entry.uses),
                category=category,
            )
        )

        seen.add((entry.actor_name, _seen_key(entry.ability, tracked)))

    if not rows:

        #
        # Liefert die Quelle zu niemandem Cooldown-Einsätze, wird auch
        # für niemanden behauptet, er habe nichts gedrückt. Was für die
        # Spezialisierung zu erwarten wäre, sagt die Oberfläche über
        # `reference_hint()`.
        #

        return snapshot.cooldown_usage

    for name, abilities in reference.items():

        if abilities is None:
            continue

        for cooldown in abilities.cooldowns:

            if cooldown.optional:
                continue

            if (name, _seen_key(cooldown.english, cooldown)) in seen:
                continue

            rows.append(
                CooldownUsage(
                    actor_name=name,
                    ability=cooldown.german or cooldown.english,
                    cast_times=(),
                    cooldown=cooldown.cooldown,
                    #
                    # Mögliche Einsätze nur für Cooldowns, die auf
                    # Abklingzeit gehören. Ein ungenutzter Schildwall
                    # ist kein verschenkter Einsatz.
                    #
                    possible=(
                        _possible_uses(
                            snapshot.pull_seconds,
                            cooldown.cooldown,
                        )
                        if cooldown.category == CD_PERSONAL
                        else 0
                    ),
                    category=cooldown.category,
                )
            )

    return tuple(rows)


#
# --------------------------------------------------
# Was zu erwarten wäre
# --------------------------------------------------
#


def reference_hint(actor: Actor | None, kind: str) -> str:
    """
    Die Fähigkeiten einer Spezialisierung als Aufzählung - der Text,
    den eine leere Karte statt "Keine Angaben" zeigen kann.

    Ohne bekannte Spezialisierung ein leerer String: dann ist auch
    diese Auskunft nicht zu geben, und ein erfundener Satz wäre
    schlechter als keiner.
    """

    abilities = class_abilities.for_actor(actor) if actor else None

    if abilities is None:
        return ""

    names = [
        aura.german or aura.english
        for aura in abilities.auras_of(kind)
        if not aura.optional
    ]

    return ", ".join(names)


def cooldown_hint(actor: Actor | None) -> str:
    """
    Dasselbe für die Cooldowns einer Spezialisierung.
    """

    abilities = class_abilities.for_actor(actor) if actor else None

    if abilities is None:
        return ""

    names = [
        cooldown.german or cooldown.english
        for cooldown in abilities.cooldowns
        if not cooldown.optional
    ]

    return ", ".join(names)
