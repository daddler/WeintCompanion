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

from analyzer.data import encounters
from analyzer.models import (
    MECHANIC_OTHER,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
    Actor,
    ConsumableState,
    DeathEntry,
    MechanicIssue,
    MetricEntry,
    RaidSnapshot,
    TankEntry,
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


def role_name(value, damage: float = 0.0, healing: float = 0.0) -> str:
    """
    Rolle eines Spielers.

    Der Bot soll die Rolle mitliefern, weil nur er die Rangliste
    kennt, aus der sie stammt. Fehlt sie, wird sie ersatzweise aus
    den Werten abgeleitet: wer mehr geheilt als geschadet hat, ist
    ein Heiler. Tanks lassen sich so nicht erkennen - sie werden
    dann als Schadensausteiler geführt, was in der Bewertung mildere
    Folgen hat als eine falsche Tank-Einstufung.
    """

    role = ROLE_NAMES.get(_text(value).lower())

    if role is not None:
        return role

    if healing > damage:
        return ROLE_HEALER

    return ROLE_DPS


def build_actor(entry: dict) -> Actor:

    damage = _number(entry.get("damage_total"))

    healing = _number(entry.get("healing_total"))

    return Actor(
        name=_text(entry.get("name")),
        class_name=class_name(entry.get("class")),
        spec=_text(entry.get("spec")),
        role=role_name(entry.get("role"), damage, healing),
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

    `total` ist die Gesamtsumme des Spielers, `value` der Wert pro
    Sekunde - dieselbe Bedeutung wie beim Mock, damit WeintTV und die
    Academy beide Quellen ohne Fallunterscheidung darstellen können.
    """

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

    return RaidSnapshot(
        source_label=source_label,
        live=live,
        in_combat=in_combat,
        encounter=_encounter(fight),
        pull_number=_count(fight.get("pull_number")),
        pull_seconds=pull_seconds,
        boss_health_percent=_percent(fight.get("boss_percentage")),
        raid_size=raid_size,
        deaths=build_deaths(_sequence(payload.get("deaths"))),
        battle_res_charges=_count(fight.get("battle_res_charges")),
        battle_res_max=_count(fight.get("battle_res_max")),
        heroism_used=_flag(fight.get("heroism_used")),
        heroism_remaining=_number(fight.get("heroism_remaining")),
        top_damage=damage,
        top_healing=healing,
        tanks=tanks,
        consumables=build_consumables(
            _sequence(payload.get("consumables"))
        ),
        mechanics=build_mechanics(
            _sequence(payload.get("mechanics"))
        ),
        warnings=build_warnings(payload, age_seconds),
    )


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

        return " · ".join(parts) or self.code


@dataclass(frozen=True)
class FightSummary:
    """
    Ein Eintrag der Pull-Liste innerhalb eines Reports.
    """

    fight_id: int

    encounter_name: str = ""

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
    """

    entries = []

    for row in _sequence(_mapping(payload).get("fights")):

        row = _mapping(row)

        fight_id = _count(row.get("id"), -1)

        if fight_id < 0:
            continue

        entries.append(
            FightSummary(
                fight_id=fight_id,
                encounter_name=_text(row.get("name")),
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
