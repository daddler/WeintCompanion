"""
Übersetzung der Bot-Antwort in einen RaidSnapshot.

Dieses Modul ist bewusst frei von Netzwerk, Threads und Qt: es
bekommt ein bereits geladenes Wörterbuch und gibt einen Snapshot
zurück. Dadurch ist die gesamte Auswertungslogik testbar, ohne dass
ein Bot, ein Token oder eine Internetverbindung nötig wäre - und der
Analyzer bleibt, wie der Rest des Pakets, ohne Fremdabhängigkeit.

Grundregel für alles hier: **eine unvollständige Antwort ist kein
Fehlerfall.** Der Bot kann jederzeit ein Feld weglassen, weil
WarcraftLogs es für diesen Kampf nicht liefert. Jede Funktion liest
deshalb defensiv und fällt auf den neutralen Wert zurück, statt eine
Ausnahme zu werfen. Der Vertrag aus providers/base.py - snapshot()
wirft nie - beginnt genau hier.

Der Aufbau der Antwort ist in docs/warcraftlogs-bridge.md
festgeschrieben; das ist zugleich die Vorlage für die Bot-Seite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analyzer.analysis import damage as damage_analysis
from analyzer.analysis.movement import build_movement
from analyzer.analysis.ranking import build_ranking
from analyzer.analysis.spec_reference import apply_spec_reference
from analyzer.data import encounters, specs
from analyzer.models import (
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    MECHANIC_OTHER,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    SUPPORT_DISPEL,
    SUPPORT_INTERRUPT,
    UPTIME_BUFF,
    UPTIME_DOT,
    UPTIME_HOT,
    ActivityEntry,
    Actor,
    CombatEvent,
    ConsumableState,
    CooldownState,
    CooldownUsage,
    DeathEntry,
    HeroismWindow,
    MechanicIssue,
    MetricEntry,
    RaidSnapshot,
    ResurrectionEvent,
    SupportEvent,
    TankEntry,
    UptimeEntry,
)


#
# --------------------------------------------------
# Schreibweisen
# --------------------------------------------------
#
# WarcraftLogs liefert Klassennamen ohne Leerzeichen ("DeathKnight"),
# der Rest der Anwendung benutzt die Schreibweise des Combat-Logs
# ("Death Knight") - siehe gui/theme/wow_colors.py. Ohne diese
# Umschreibung fänden Klassenfarbe und deutsche Bezeichnung ihren
# Eintrag nicht und Todesritter würden farblos dargestellt.
#

CLASS_NAMES: dict[str, str] = {

    "deathknight": "Death Knight",
    "death knight": "Death Knight",
    "demonhunter": "Demon Hunter",
    "druid": "Druid",
    "hunter": "Hunter",
    "mage": "Mage",
    "monk": "Monk",
    "paladin": "Paladin",
    "priest": "Priest",
    "rogue": "Rogue",
    "shaman": "Shaman",
    "warlock": "Warlock",
    "warrior": "Warrior",

}


#
# Rollenbezeichnungen, wie WarcraftLogs sie kennt, auf die drei
# Rollen des Analyzers abgebildet.
#

ROLE_NAMES: dict[str, str] = {

    "tank": ROLE_TANK,
    "tanks": ROLE_TANK,
    "healer": ROLE_HEALER,
    "healers": ROLE_HEALER,
    "healing": ROLE_HEALER,
    "dps": ROLE_DPS,
    "damage": ROLE_DPS,
    "damager": ROLE_DPS,

}


#
# --------------------------------------------------
# Sichere Zugriffe
# --------------------------------------------------
#


def _mapping(value) -> dict:
    """
    Gibt `value` zurück, wenn es ein Wörterbuch ist, sonst ein
    leeres. Erspart jeder Aufrufstelle eine eigene Prüfung.
    """

    return value if isinstance(value, dict) else {}


def _sequence(value) -> list:

    if isinstance(value, (list, tuple)):
        return list(value)

    return []


def _text(value) -> str:

    if value is None:
        return ""

    return str(value).strip()


def _format_report_date(iso_timestamp: str) -> str:
    """
    ISO-Zeitstempel (UTC, vom Bot geliefert) in die lokale Zeitzone
    dieses Rechners umgerechnet und kurz formatiert - fürs Report-
    Dropdown im Archiv-Modus, wo sonst mehrere gleichnamige Berichte
    (z.B. "Siege of Orgrimmar · Siege of Orgrimmar") nicht
    unterscheidbar wären. Leerer String bei fehlendem/ungültigem Wert,
    statt eine Ausnahme zu werfen - siehe Grundregel oben im Modul.
    """

    if not iso_timestamp:
        return ""

    try:
        published = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))

    except ValueError:
        return ""

    return published.astimezone().strftime("%d.%m.%Y %H:%M")


def _number(value, default: float = 0.0) -> float:
    """
    Zahlenwert aus der Antwort. JSON kann hier eine Zahl, eine
    Zeichenkette oder `null` liefern - alles, was sich nicht in eine
    endliche Zahl übersetzen lässt, ergibt den Standardwert.
    """

    if isinstance(value, bool):
        return default

    try:
        number = float(value)

    except (TypeError, ValueError):
        return default

    #
    # NaN und Unendlich würden sich durch die gesamte Auswertung
    # ziehen (Sortierung, Anteile, Balkenbreiten) und die Oberfläche
    # unbrauchbar machen.
    #

    if number != number or number in (float("inf"), float("-inf")):
        return default

    return number


def _count(value, default: int = 0) -> int:

    return int(_number(value, default))


def _percent(value, default: float = 100.0) -> float:
    """
    Prozentwert auf 0 - 100 begrenzen.
    """

    return max(0.0, min(100.0, _number(value, default)))


def _spell_id(row: dict) -> int:
    """
    Die Spell-ID einer gemeldeten Fähigkeit.

    Vier Feldnamen, weil WarcraftLogs je nach Tabelle `guid`,
    `abilityGameID` oder `id` schreibt und der Bot sie mal
    durchreicht, mal umbenennt. Die ID ist die einzige Angabe an einer
    Fähigkeit ohne Sprache, und genau daran ist die Erkennung schon
    einmal gescheitert (siehe docs/warcraftlogs-bridge.md) - deshalb
    wird sie großzügig gelesen und nirgends erzwungen.
    """

    for key in ("spell_id", "guid", "ability_id", "abilityGameID"):

        value = _count(row.get(key))

        if value > 0:
            return value

    return 0


def _flag(value, default: bool = False) -> bool:

    if isinstance(value, bool):
        return value

    if value is None:
        return default

    return bool(value)


#
# --------------------------------------------------
# Einzelteile
# --------------------------------------------------
#


def class_name(value) -> str:
    """
    Klassenname in der Schreibweise des Combat-Logs.

    Unbekannte Klassen werden unverändert durchgereicht statt
    verworfen: ein künftiger Patch soll den Spieler nicht aus der
    Auswertung entfernen, nur weil die Tabelle ihn noch nicht kennt.
    """

    text = _text(value)

    return CLASS_NAMES.get(text.lower(), text)


def spec_name(class_value, spec_value) -> str:
    """
    Spezialisierung in der Schreibweise, die der Rest der Anwendung
    benutzt (deutsch).

    WarcraftLogs liefert sie englisch ("Retribution"), der
    Lektionskatalog und die Simulation führen sie deutsch
    ("Vergeltung"). Ohne diese Übersetzung traf im Echtbetrieb kein
    einziger Katalogschlüssel zu, und zwar lautlos: jeder Spieler
    bekam nur Rollen- und Allgemeinlektionen, ohne dass irgendwo etwas
    fehlgeschlagen wäre.
    """

    return specs.normalize_spec(class_name(class_value), _text(spec_value))


def role_name(
    value,
    damage: float = 0.0,
    healing: float = 0.0,
    *,
    actor_class: str = "",
    spec: str = "",
) -> str:
    """
    Rolle eines Spielers.

    Drei Wege, in dieser Reihenfolge:

    1. **Die Angabe des Bots.** Nur er kennt die Rangliste, aus der
       sie stammt.
    2. **Die Spezialisierung.** "Protection", "Blood", "Guardian" und
       "Brewmaster" sind eine sichere Aussage - dafür gibt es
       analyzer.data.specs.
    3. **Schaden gegen Heilung.** Der alte Notweg, der Tanks
       grundsätzlich nicht erkennen konnte und sie als
       Schadensausteiler führte. Genau das ist der Fall, den Schritt 2
       jetzt abfängt: ein als Schadensausteiler geführter Tank wird
       gegen die Schadensrangliste gemessen und bekommt dauerhaft
       einen Stern, obwohl er seine Aufgabe erfüllt.
    """

    role = ROLE_NAMES.get(_text(value).lower())

    if role is not None:
        return role

    from_spec = specs.role_for_spec(actor_class, spec)

    if from_spec:
        return from_spec

    if healing > damage:
        return ROLE_HEALER

    return ROLE_DPS


def build_actor(entry: dict) -> Actor:

    damage = _number(entry.get("damage_total"))

    healing = _number(entry.get("healing_total"))

    actor_class = class_name(entry.get("class"))

    spec = spec_name(entry.get("class"), entry.get("spec"))

    return Actor(
        name=_text(entry.get("name")),
        class_name=actor_class,
        spec=spec,
        role=role_name(
            entry.get("role"),
            damage,
            healing,
            actor_class=actor_class,
            spec=spec,
        ),
    )


def _encounter(fight: dict) -> object:

    name = _text(fight.get("name"))

    if not name:
        return None

    return encounters.lookup(
        encounter_id=_count(fight.get("encounter_id")),
        name=name,
        difficulty_id=_count(fight.get("difficulty_id")),
        raid_size=_count(fight.get("raid_size")),
    )


def _duration(fight: dict) -> float:
    """
    Kampfdauer in Sekunden. Sie ist der Nenner jeder Kennzahl - ist
    sie unbekannt oder null, wird auf eine Sekunde begrenzt, damit
    aus einer Division nie eine Ausnahme oder ein absurder Wert
    entsteht.
    """

    return max(1.0, _number(fight.get("duration"), 1.0))


#
# --------------------------------------------------
# Ranglisten
# --------------------------------------------------
#


def _entries(
    rows: list[tuple[Actor, float]],
    duration: float,
) -> tuple[MetricEntry, ...]:
    """
    Baut eine sortierte Rangliste mit Anteilen.

    Nur noch eine Weiterleitung: die Rechnung steht in
    analyzer.analysis.ranking, weil die Wiedergabe sie genauso
    braucht. Zwei Umsetzungen wären zwei Auswertungen, die sich
    irgendwann uneinig sind.
    """

    return build_ranking(rows, duration)


def build_metrics(
    players: list,
    duration: float,
) -> tuple[tuple[MetricEntry, ...], tuple[MetricEntry, ...]]:
    """
    Teilt das Roster in Schadens- und Heilrangliste.

    Die Aufteilung folgt der Rolle und nicht der Frage, ob ein Wert
    ungleich null ist: ein Heiler, der auch Schaden fährt, gehört
    trotzdem in die Heilrangliste - andernfalls stünde er in beiden
    und die Anteile ergäben zusammen mehr als 100 %.
    """

    damage_rows: list[tuple[Actor, float]] = []

    healing_rows: list[tuple[Actor, float]] = []

    for entry in players:

        entry = _mapping(entry)

        actor = build_actor(entry)

        if not actor.name:
            continue

        if actor.is_healer:

            healing_rows.append(
                (actor, _number(entry.get("healing_total")))
            )

        else:

            damage_rows.append(
                (actor, _number(entry.get("damage_total")))
            )

    return (
        _entries(damage_rows, duration),
        _entries(healing_rows, duration),
    )


def build_tanks(players: list) -> tuple[TankEntry, ...]:

    entries = []

    for entry in players:

        entry = _mapping(entry)

        actor = build_actor(entry)

        if not actor.name or not actor.is_tank:
            continue

        entries.append(
            TankEntry(
                actor=actor,
                health_percent=_percent(entry.get("health_percent")),
                damage_taken=_number(entry.get("damage_taken")),
                active_mitigation=_flag(entry.get("active_mitigation")),
            )
        )

    return tuple(entries)


#
# --------------------------------------------------
# Ereignisse
# --------------------------------------------------
#


def build_deaths(rows: list) -> tuple[DeathEntry, ...]:

    entries = []

    for row in rows:

        row = _mapping(row)

        name = _text(row.get("name"))

        if not name:
            continue

        entries.append(
            DeathEntry(
                actor_name=name,
                at_seconds=_number(row.get("at")),
                cause=_text(row.get("ability")),
            )
        )

    return tuple(entries)


def build_mechanics(rows: list) -> tuple[MechanicIssue, ...]:
    """
    Mechanikfehler.

    Der Bot darf diese Liste leer lassen - WarcraftLogs liefert sie
    nicht von selbst, sie muss dort aus Ereignissen abgeleitet
    werden. Die Academy kommt mit einer leeren Liste zurecht und
    bewertet die betroffenen Bereiche dann fehlerfrei; das Feld ist
    hier bereits vorgesehen, damit die Bot-Seite es später ohne
    Änderung an der Companion-App nachliefern kann.
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        name = _text(row.get("name"))

        mechanic = _text(row.get("mechanic"))

        if not name or not mechanic:
            continue

        entries.append(
            MechanicIssue(
                actor_name=name,
                mechanic=mechanic,
                count=max(1, _count(row.get("count"), 1)),
                severity=_text(row.get("severity")) or "warning",
                category=_text(row.get("category")) or MECHANIC_OTHER,
            )
        )

    return tuple(entries)


def build_consumables(rows: list) -> tuple[ConsumableState, ...]:

    entries = []

    for row in rows:

        row = _mapping(row)

        label = _text(row.get("label"))

        if not label:
            continue

        entries.append(
            ConsumableState(
                label=label,
                used=_count(row.get("used")),
                total=_count(row.get("total")),
                missing=tuple(
                    _text(name)
                    for name in _sequence(row.get("missing"))
                    if _text(name)
                ),
            )
        )

    return tuple(entries)


def build_cooldowns(rows: list) -> tuple[CooldownState, ...]:
    """
    Raid-/Heil-Cooldowns (siehe raid_cooldowns/heal_cooldowns in
    docs/warcraftlogs-bridge.md). Der Bot liefert hier keinen echten
    Live-Countdown (fuer einen bereits beendeten WarcraftLogs-Pull
    ergibt "noch X Sekunden" keinen Sinn) - "ready" ist deshalb immer
    wahr und eine etwaige Mehrfachnutzung steckt bereits lesbar im
    Namen (z.B. "Kaldrun (2×)").
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        name = _text(row.get("name"))

        actor_name = _text(row.get("actor_name"))

        if not name or not actor_name:
            continue

        entries.append(
            CooldownState(
                name=name,
                actor_name=actor_name,
                ready=_flag(row.get("ready"), default=True),
                remaining=_number(row.get("remaining")),
                duration=_number(row.get("duration")),
            )
        )

    return tuple(entries)


#
# --------------------------------------------------
# Tiefenauswertung
# --------------------------------------------------
#
# Alles hier ist optional (siehe docs/warcraftlogs-bridge.md, v2).
# Liefert der Bot einen Block nicht, entsteht ein leeres Tupel und
# die Oberfläche zeigt ihren Platzhaltertext - kein Fehler, kein
# Sonderfall. Genau deshalb kann der Bot die neuen Felder einzeln und
# in beliebiger Reihenfolge nachliefern.
#


def build_activity(
    players: list,
    duration: float,
) -> tuple[ActivityEntry, ...]:
    """
    Aktivzeit und Aktionen pro Minute je Spieler.

    Das ist die eigentliche Rotationsmetrik: `active_time` kommt aus
    WarcraftLogs' `activeTime` und sagt, wie durchgehend jemand
    Knöpfe gedrückt hat - unabhängig davon, wie viel Schaden dabei
    herauskam.
    """

    entries = []

    for row in players:

        row = _mapping(row)

        name = _text(row.get("name"))

        if not name:
            continue

        active = _number(row.get("active_time"))

        casts = _count(row.get("casts"))

        if active <= 0 and casts <= 0:
            continue

        entries.append(
            ActivityEntry(
                actor_name=name,
                active_percent=(
                    max(0.0, min(100.0, active / duration * 100.0))
                    if duration > 0
                    else 0.0
                ),
                casts=casts,
                apm=(
                    casts / duration * 60.0
                    if duration > 0
                    else 0.0
                ),
                longest_gap=_number(row.get("longest_gap")),
            )
        )

    entries.sort(key=lambda entry: entry.active_percent, reverse=True)

    return tuple(entries)


def build_uptimes(
    players: list,
    key: str,
    kind: str,
) -> tuple[UptimeEntry, ...]:
    """
    Wirkungsdauern aus `players[].dots`, `players[].hots` bzw.
    `players[].buffs`.

    Absteigend nach Uptime sortiert, damit die Oberfläche nicht
    sortieren muss.
    """

    entries = []

    for row in players:

        row = _mapping(row)

        actor_name = _text(row.get("name"))

        if not actor_name:
            continue

        for aura in _sequence(row.get(key)):

            aura = _mapping(aura)

            ability = _text(aura.get("aura")) or _text(aura.get("name"))

            spell_id = _spell_id(aura)

            #
            # Ohne Namen, aber mit Spell-ID ist die Zeile trotzdem
            # brauchbar: die Spec-Tabelle kennt den Namen dann. Sie
            # ganz zu verwerfen hieße, eine gemeldete Wirkungsdauer
            # wegen einer fehlenden Beschriftung zu verlieren.
            #

            if not ability and not spell_id:
                continue

            entries.append(
                UptimeEntry(
                    actor_name=actor_name,
                    ability=ability,
                    uptime_percent=_percent(
                        aura.get("uptime_percent"),
                        default=0.0,
                    ),
                    kind=kind,
                    applications=_count(aura.get("applications")),
                    target=_text(aura.get("target")),
                    expected_percent=_percent(
                        aura.get("expected_percent"),
                        default=0.0,
                    ),
                    spell_id=spell_id,
                )
            )

    entries.sort(key=lambda entry: entry.uptime_percent, reverse=True)

    return tuple(entries)


def build_movement_rows(
    players: list,
    duration: float,
    damage_taken: tuple = (),
) -> tuple:
    """
    Laufwege aus den Rohsummen der Positionsdaten.

    Der Bot schickt bewusst **Karteneinheiten** (`movement_units`) und
    keine Meter - die Umrechnung steht in analyzer.analysis.movement,
    damit der Faktor an einer Stelle korrigierbar ist. Siehe dort
    auch, warum der Wert eine Schätzung ist.
    """

    hits_by_name = {
        entry.actor_name: entry.avoidable_hits
        for entry in damage_taken
    }

    entries = []

    for row in players:

        row = _mapping(row)

        name = _text(row.get("name"))

        if not name:
            continue

        units = _number(row.get("movement_units"))

        if units <= 0:
            continue

        entries.append(
            build_movement(
                actor_name=name,
                units=units,
                seconds=duration,
                avoidable_hits=hits_by_name.get(name, 0),
            )
        )

    entries.sort(key=lambda entry: entry.meters, reverse=True)

    return tuple(entries)


def build_damage_taken(
    players: list,
    encounter_name: str,
) -> tuple:
    """
    Erhaltener Schaden je Spieler, aufgeschlüsselt nach Fähigkeit und
    eingeordnet nach Vermeidbarkeit.

    Die Einordnung macht bewusst der Companion
    (analyzer.data.avoidable), nicht der Bot: sie ist eine Wertung,
    die für WeintTV und die Academy identisch sein muss und ohne
    Bot-Deploy korrigierbar bleiben soll.
    """

    entries = []

    for row in players:

        row = _mapping(row)

        name = _text(row.get("name"))

        if not name:
            continue

        rows = []

        for ability in _sequence(row.get("damage_taken_abilities")):

            ability = _mapping(ability)

            ability_name = _text(ability.get("ability")) or _text(ability.get("name"))

            if not ability_name:
                continue

            rows.append(
                (
                    ability_name,
                    _number(ability.get("amount")),
                    _count(ability.get("hits")),
                    _text(ability.get("source")),
                )
            )

        if not rows:
            continue

        entries.append(
            damage_analysis.build_damage_taken(
                actor_name=name,
                encounter_name=encounter_name,
                rows=tuple(rows),
                role=role_name(_text(row.get("role"))),
            )
        )

    entries.sort(key=lambda entry: entry.total, reverse=True)

    return tuple(entries)


#
# Wie ein Cooldown-Name auf eine Kategorie abgebildet wird, wenn der
# Bot keine mitschickt. Die Listen sind bewusst dieselben, die der
# Bot für raid_cooldowns/heal_cooldowns benutzt - so landet ein
# Cooldown in beiden Ansichten in derselben Schublade.
#

_RAID_COOLDOWN_NAMES = {
    "rallying cry",
    "anti-magic zone",
    "spirit link totem",
    "power word: barrier",
    "smoke bomb",
    "stampeding roar",
    "devotion aura",
}

_HEAL_COOLDOWN_NAMES = {
    "tranquility",
    "divine hymn",
    "healing tide totem",
    "revival",
    "aura mastery",
}


def _cooldown_category(name: str, given: str) -> str:

    if given in (CD_RAID, CD_HEAL, CD_PERSONAL, "defensive"):
        return given

    lowered = name.lower()

    if lowered in _RAID_COOLDOWN_NAMES:
        return CD_RAID

    if lowered in _HEAL_COOLDOWN_NAMES:
        return CD_HEAL

    return CD_PERSONAL


def build_cooldown_usage(
    players: list,
    duration: float,
    windows: tuple[HeroismWindow, ...] = (),
) -> tuple[CooldownUsage, ...]:
    """
    Cooldown-Einsätze mit Zeitpunkten.

    Der Unterschied zu `build_cooldowns()`: dort geht es um den
    Live-Countdown, hier um die Rückschau. `possible` rechnet der
    Companion selbst aus Kampfdauer und Abklingzeit aus - der Bot
    liefert nur die Tatsachen (wann gewirkt, wie lang die Abklingzeit
    ist), nicht die Bewertung.

    `in_burst` zählt die Einsätze innerhalb eines Heldentum-Fensters.
    Genau das ist die Frage, die "genutzt oder nicht" nicht
    beantwortet: ein Cooldown zur falschen Zeit ist halb verschenkt.
    """

    entries = []

    for row in players:

        row = _mapping(row)

        actor_name = _text(row.get("name"))

        if not actor_name:
            continue

        for cooldown in _sequence(row.get("cooldowns")):

            cooldown = _mapping(cooldown)

            ability = _text(cooldown.get("name"))

            spell_id = _spell_id(cooldown)

            if not ability and not spell_id:
                continue

            cast_times = tuple(
                sorted(
                    _number(value)
                    for value in _sequence(cooldown.get("casts"))
                )
            )

            recharge = _number(cooldown.get("cooldown"))

            entries.append(
                CooldownUsage(
                    actor_name=actor_name,
                    ability=ability,
                    cast_times=cast_times,
                    cooldown=recharge,
                    possible=_possible_uses(duration, recharge),
                    in_burst=sum(
                        1
                        for at in cast_times
                        if any(window.contains(at) for window in windows)
                    ),
                    category=_cooldown_category(
                        ability,
                        _text(cooldown.get("category")),
                    ),
                    spell_id=spell_id,
                )
            )

    return tuple(entries)


def _possible_uses(duration: float, cooldown: float) -> int:
    """
    Wie oft ein Cooldown im Kampf hätte genutzt werden können.

    Der erste Einsatz zählt immer mit (Kampfbeginn), danach je
    vollständig abgelaufener Abklingzeit einer mehr. Ohne bekannte
    Abklingzeit gibt es keine Obergrenze - dann 0, damit daraus keine
    erfundene Quote entsteht.
    """

    if cooldown <= 0 or duration <= 0:
        return 0

    return int(duration // cooldown) + 1


def build_heroism_windows(rows: list) -> tuple[HeroismWindow, ...]:
    """
    Heldentum-Fenster mit Anfang und Ende.

    Bisher wusste die Anwendung nur *ob* Heldentum lief. Der Zeitpunkt
    ist die Voraussetzung dafür, Cooldown-Einsätze überhaupt bewerten
    zu können.
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        start = _number(row.get("start"), -1.0)

        end = _number(row.get("end"), -1.0)

        if start < 0 or end < start:
            continue

        entries.append(
            HeroismWindow(
                start=start,
                end=end,
                source=_text(row.get("source")),
                label=_text(row.get("label")) or "Heldentum",
            )
        )

    entries.sort(key=lambda window: window.start)

    return tuple(entries)


def build_resurrections(rows: list) -> tuple[ResurrectionEvent, ...]:
    """
    Im Kampf gewirkte Wiederbelebungen - auf wen, von wem, wann.

    Ohne Ziel ist der Eintrag wertlos und wird verworfen; ohne Wirker
    ist er noch brauchbar.
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        target = _text(row.get("target"))

        if not target:
            continue

        entries.append(
            ResurrectionEvent(
                target=target,
                caster=_text(row.get("caster")),
                at_seconds=_number(row.get("at")),
                ability=_text(row.get("ability")),
            )
        )

    entries.sort(key=lambda event: event.at_seconds)

    return tuple(entries)


def build_support_events(rows: list, kind: str) -> tuple[SupportEvent, ...]:
    """
    Unterbrechungen bzw. entfernte Effekte als Einzelereignisse.
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        actor_name = _text(row.get("actor")) or _text(row.get("name"))

        if not actor_name:
            continue

        entries.append(
            SupportEvent(
                actor_name=actor_name,
                kind=kind,
                at_seconds=_number(row.get("at")),
                target=_text(row.get("target")),
                ability=_text(row.get("ability")),
            )
        )

    entries.sort(key=lambda event: event.at_seconds)

    return tuple(entries)


def build_events(rows: list) -> tuple[CombatEvent, ...]:
    """
    Sonstige Kampfereignisse (Phasenwechsel, angesagte
    Bossfähigkeiten, Adds).

    `kind` ist die einzige Pflichtangabe - alles Weitere darf fehlen.
    Die Art wird bewusst NICHT gegen eine Liste geprüft: eine neue
    Ereignisart soll ohne Companion-Update in der Ereignisliste
    erscheinen können.

    Steht hier bei den übrigen `build_*` und nicht bei der
    Wiedergabe, weil beide Antworten (Einzel-Fight und Zeitleiste)
    denselben Block liefern dürfen - analyzer/replay/payload.py holt
    sich diese Funktion von hier.
    """

    entries = []

    for row in rows:

        row = _mapping(row)

        kind = _text(row.get("kind"))

        if not kind:
            continue

        entries.append(
            CombatEvent(
                at_seconds=_number(row.get("at")),
                kind=kind,
                actor_name=_text(row.get("actor")) or _text(row.get("name")),
                target=_text(row.get("target")),
                ability=_text(row.get("ability")),
                detail=_text(row.get("detail")),
                severity=_text(row.get("severity")) or "info",
            )
        )

    entries.sort(key=lambda event: event.at_seconds)

    return tuple(entries)


#
# --------------------------------------------------
# Hinweise
# --------------------------------------------------
#
# Ab wann ein Snapshot ausdrücklich als veraltet gekennzeichnet wird.
# Ein Livelog-Upload alle 30 Sekunden ist üblich; erst deutlich
# darüber ist der Verzug eine Erwähnung wert.
#

STALE_AFTER = 45.0


def build_warnings(payload: dict, age_seconds: float) -> tuple[str, ...]:
    """
    Hinweise für die Raidleitung.

    Der wichtigste ist der Verzug: WarcraftLogs-Livelogs werden in
    Abständen hochgeladen, ein Snapshot ist deshalb nie ganz aktuell.
    Diesen Umstand zu verschweigen wäre die gefährlichste Variante -
    eine Raidleitung, die eine Zahl für taggenau hält, trifft
    Entscheidungen auf veralteter Grundlage.
    """

    warnings = [
        _text(entry)
        for entry in _sequence(payload.get("warnings"))
        if _text(entry)
    ]

    if age_seconds >= STALE_AFTER:

        warnings.insert(
            0,
            f"Daten sind {int(age_seconds)} Sekunden alt - "
            f"WarcraftLogs überträgt in Abständen.",
        )

    return tuple(warnings)


#
# --------------------------------------------------
# Snapshot
# --------------------------------------------------
#


def snapshot_from_payload(
    payload: dict,
    source_label: str,
    age_seconds: float = 0.0,
    live: bool = True,
) -> RaidSnapshot:
    """
    Baut aus der Bot-Antwort das vollständige Bild eines Zeitpunkts.

    `age_seconds` ist die Zeit, die seit dem Abruf vergangen ist. Sie
    wird bei einem laufenden Kampf auf die Pull-Zeit addiert, damit
    die Uhr in WeintTV weiterläuft, statt zwischen zwei Abrufen
    stehen zu bleiben. Alle übrigen Werte bleiben unangetastet - sie
    zu extrapolieren hieße, Zahlen zu erfinden.

    `live` unterscheidet den Live-Provider (WarcraftLogsProvider) von
    einem einzeln aus dem Archiv abgerufenen, längst beendeten Fight
    (siehe build_report_list()/build_fight_list() unten) - beide
    liefern exakt dieselbe JSON-Form, nur die Herkunft ist eine
    andere. Ein archivierter Fight ist nie "live", auch wenn sein
    `in_progress`-Feld aus historischen Gründen zufällig true wäre.
    """

    payload = _mapping(payload)

    fight = _mapping(payload.get("fight"))

    players = _sequence(payload.get("players"))

    duration = _duration(fight)

    in_combat = _flag(fight.get("in_progress"))

    damage, healing = build_metrics(players, duration)

    tanks = build_tanks(players)

    #
    # Die Raidgröße aus dem Kampf hat Vorrang; fehlt sie, ist die
    # Anzahl der gemeldeten Spieler die ehrlichere Angabe als eine
    # feste Zahl.
    #

    raid_size = _count(fight.get("raid_size")) or len(damage) + len(healing)

    pull_seconds = duration + (age_seconds if in_combat else 0.0)

    #
    # Tiefenauswertung. Reihenfolge ist hier wichtig: die
    # Heldentum-Fenster braucht die Cooldown-Auswertung (um Einsätze
    # im Burst zu zählen), und der erhaltene Schaden braucht die
    # Laufweg-Auswertung (für die Zahl vermeidbarer Treffer).
    #

    encounter = _encounter(fight)

    encounter_name = encounter.name if encounter is not None else ""

    heroism_windows = build_heroism_windows(
        _sequence(payload.get("heroism_windows"))
        or _sequence(_mapping(fight).get("heroism_windows"))
    )

    damage_taken = build_damage_taken(players, encounter_name)

    #
    # Der Bot darf eigene, handverlesene Mechanikregeln mitschicken;
    # zusätzlich leitet der Analyzer sie aus vermeidbaren Treffern ab.
    # Beim Zusammenführen gewinnt der Bot, damit derselbe Fehler nicht
    # doppelt gezählt wird - siehe analyzer.analysis.damage.
    #

    mechanics = damage_analysis.merge_mechanics(
        damage_analysis.bot_mechanics(
            build_mechanics(_sequence(payload.get("mechanics")))
        ),
        damage_analysis.derive_mechanics(damage_taken, encounter_name),
    )

    resurrections = build_resurrections(
        _sequence(payload.get("resurrects"))
        or _sequence(payload.get("resurrections"))
    )

    #
    # Zum Schluss gegen die Spezialisierungen halten: Namen erkennen,
    # DoT/HoT/Buff richtig einsortieren, Richtwerte anhängen und
    # fehlende Fähigkeiten der Spec als Null ergänzen, wo die Quelle
    # diese Art überhaupt liefert. Das passiert hier und nicht in der
    # Oberfläche, damit WeintTV, die Academy, das Addon-Payload und
    # die Wiedergabe dasselbe sehen - siehe
    # analyzer/analysis/spec_reference.py.
    #

    return apply_spec_reference(RaidSnapshot(
        source_label=source_label,
        live=live,
        in_combat=in_combat,
        encounter=encounter,
        pull_number=_count(fight.get("pull_number")),
        pull_seconds=pull_seconds,
        boss_health_percent=_percent(fight.get("boss_percentage")),
        raid_size=raid_size,
        deaths=build_deaths(_sequence(payload.get("deaths"))),
        battle_res_charges=_battle_res_charges(fight, resurrections),
        battle_res_max=_count(fight.get("battle_res_max")),
        heroism_used=_heroism_used(fight, heroism_windows),
        heroism_remaining=_number(fight.get("heroism_remaining")),
        top_damage=damage,
        top_healing=healing,
        tanks=tanks,
        consumables=build_consumables(
            _sequence(payload.get("consumables"))
        ),
        mechanics=mechanics,
        raid_cooldowns=build_cooldowns(
            _sequence(payload.get("raid_cooldowns"))
        ),
        heal_cooldowns=build_cooldowns(
            _sequence(payload.get("heal_cooldowns"))
        ),
        warnings=build_warnings(payload, age_seconds),
        activity=build_activity(players, duration),
        dot_uptimes=build_uptimes(players, "dots", UPTIME_DOT),
        hot_uptimes=build_uptimes(players, "hots", UPTIME_HOT),
        buff_uptimes=build_uptimes(players, "buffs", UPTIME_BUFF),
        movement=build_movement_rows(players, duration, damage_taken),
        damage_taken=damage_taken,
        cooldown_usage=build_cooldown_usage(
            players,
            duration,
            heroism_windows,
        ),
        heroism_windows=heroism_windows,
        resurrections=resurrections,
        interrupts=build_support_events(
            _sequence(payload.get("interrupts")),
            SUPPORT_INTERRUPT,
        ),
        dispels=build_support_events(
            _sequence(payload.get("dispels")),
            SUPPORT_DISPEL,
        ),
        events=build_events(_sequence(payload.get("events"))),
    ))


def _heroism_used(
    fight: dict,
    windows: tuple[HeroismWindow, ...],
) -> bool:
    """
    Ein ausdrückliches `heroism_used` des Bots hat Vorrang; sonst
    verrät schon die Existenz eines Fensters die Antwort. So
    funktioniert die Anzeige auch für einen Bot, der nur noch die
    Fenster schickt.
    """

    if _flag(fight.get("heroism_used")):
        return True

    return bool(windows)


def _battle_res_charges(
    fight: dict,
    resurrections: tuple[ResurrectionEvent, ...],
) -> int:
    """
    Verbleibende Kampf-Wiederbelebungen.

    Ein ausdrücklicher Wert des Bots hat Vorrang. Fehlt er, aber die
    Obergrenze und die Ereignisse sind bekannt, ist die Differenz die
    ehrlichere Angabe als eine Null - die würde aussehen, als wären
    alle Ladungen verbraucht.
    """

    charges = _count(fight.get("battle_res_charges"), -1)

    if charges >= 0:
        return charges

    maximum = _count(fight.get("battle_res_max"))

    if maximum <= 0:
        return 0

    return max(0, maximum - len(resurrections))


#
# --------------------------------------------------
# Herkunft
# --------------------------------------------------
#


def report_label(payload: dict) -> str:
    """
    Kurze Beschreibung des Berichts für die Statuszeile, z. B.
    "Thron des Donners · Bericht aBcDeF12".
    """

    report = _mapping(_mapping(payload).get("report"))

    parts = [
        _text(report.get("zone")) or _text(report.get("title")),
    ]

    code = _text(report.get("code"))

    if code:
        parts.append(f"Bericht {code}")

    return " · ".join(part for part in parts if part)


#
# --------------------------------------------------
# Archiv: Report- und Fight-Listen
# --------------------------------------------------
#
# Zwei zusätzliche, reine Mapping-Funktionen für den Archiv-Modus
# (vergangene Logs auswählen statt live zuzusehen). Sie übersetzen
# die Antworten von GET /companion/warcraftlogs/reports und
# GET /companion/warcraftlogs/reports/{code}/fights - siehe
# docs/warcraftlogs-bridge.md. Der eigentliche Fight selbst braucht
# keine eigene Übersetzung: GET .../fights/{fight_id} liefert
# bewusst dieselbe JSON-Form wie der Live-Endpunkt, damit
# snapshot_from_payload() unverändert wiederverwendet werden kann
# (nur mit live=False).
#


@dataclass(frozen=True)
class ReportSummary:
    """
    Ein Eintrag der Report-Liste - genug, um ihn in einem Dropdown
    anzuzeigen, ohne den ganzen Bericht zu laden.
    """

    code: str

    title: str = ""

    zone: str = ""

    start: str = ""

    @property
    def label(self) -> str:

        parts = [
            part
            for part in (self.title or self.zone, self.zone if self.title else "")
            if part
        ]

        text = " · ".join(parts) or self.code

        date = _format_report_date(self.start)

        return f"{date} · {text}" if date else text


@dataclass(frozen=True)
class FightSummary:
    """
    Ein Eintrag der Pull-Liste innerhalb eines Reports.
    """

    fight_id: int

    encounter_name: str = ""

    #
    # WarcraftLogs' Encounter-ID. 0 bedeutet **Trash** - das ist das
    # einzige verlässliche Merkmal dafür, denn `encounter_name` trägt
    # bei Trash den Namen irgendeines Mobs und `difficulty` fehlt dort
    # zwar meist, aber nicht immer nur dort.
    #

    encounter_id: int = 0

    difficulty: str = ""

    kill: bool = False

    boss_percentage: float = 100.0

    duration: float = 0.0

    pull_number: int = 0

    @property
    def label(self) -> str:

        total = max(0, int(self.duration))

        clock = f"{total // 60:02d}:{total % 60:02d}"

        outcome = "Kill" if self.kill else f"{self.boss_percentage:.0f} %"

        pull = f"Pull {self.pull_number} · " if self.pull_number else ""

        return f"{pull}{self.encounter_name} · {outcome} · {clock}"


def build_report_list(payload: dict) -> tuple[ReportSummary, ...]:
    """
    Übersetzt die Antwort von GET /companion/warcraftlogs/reports.

    Einträge ohne Code werden verworfen - ohne ihn lässt sich der
    Report später nicht abrufen, ein Eintrag wäre also nur ein
    nutzloser Listenplatz.
    """

    entries = []

    for row in _sequence(_mapping(payload).get("reports")):

        row = _mapping(row)

        code = _text(row.get("code"))

        if not code:
            continue

        entries.append(
            ReportSummary(
                code=code,
                title=_text(row.get("title")),
                zone=_text(row.get("zone")),
                start=_text(row.get("start")),
            )
        )

    return tuple(entries)


def build_fight_list(payload: dict) -> tuple[FightSummary, ...]:
    """
    Übersetzt die Antwort von
    GET /companion/warcraftlogs/reports/{code}/fights.

    Einträge ohne verwendbare Fight-ID werden verworfen - dieselbe
    Regel wie bei fehlendem Report-Code: ohne ID lässt sich der Fight
    nicht einzeln nachladen.

    **Trash wird ebenfalls verworfen** (`encounter_id == 0`). Eine
    Trashgruppe ist kein Pull: kein Bossanteil, keine Pull-Nummer, die
    etwas bedeutet, keine Taktik, gegen die sich etwas bewerten ließe -
    in der Auswahlliste standen davon aber Dutzende zwischen den paar
    Bosskämpfen, die man tatsächlich ansehen will.

    Der Bot filtert seit derselben Runde ebenfalls, und trotzdem steht
    es hier: die Liste kommt von einem Server, der nicht mit der App
    zusammen aktualisiert wird. Ohne diese Zeile hinge die Auswahl
    davon ab, wann jemand den Bot neu ausrollt.
    """

    entries = []

    for row in _sequence(_mapping(payload).get("fights")):

        row = _mapping(row)

        fight_id = _count(row.get("id"), -1)

        if fight_id < 0:
            continue

        encounter_id = _count(row.get("encounter_id"))

        if encounter_id <= 0:
            continue

        entries.append(
            FightSummary(
                fight_id=fight_id,
                encounter_name=_text(row.get("name")),
                encounter_id=encounter_id,
                difficulty=(
                    encounters.difficulty_name(_count(row.get("difficulty_id")))
                    if row.get("difficulty_id")
                    else ""
                ),
                kill=_flag(row.get("kill")),
                boss_percentage=_percent(row.get("boss_percentage")),
                duration=_number(row.get("duration")),
                pull_number=_count(row.get("pull_number")),
            )
        )

    return tuple(entries)
