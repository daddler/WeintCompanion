"""
Der zuletzt gespielte Pull - lesen, rechnen, beschriften.

**Warum es diese Datei gibt.** Die Übersicht sagte "Noch kein Pull",
auch am Tag nach einem Raidabend. Das war kein Fehler in der Anzeige,
sondern ihre Datenquelle: `LastPullCard` las
`RaidDataService.history()`, und die füllt sich ausschließlich mit
Pulls, die **in dieser Sitzung** abgeschlossen wurden, während WeintTV
oder die Academy offen waren. Wer die App am nächsten Nachmittag
startet, hat diese Liste leer - und die Karte behauptete daraufhin,
es habe keinen Kampf gegeben.

Der Raid von gestern liegt aber vor: als WarcraftLogs-Bericht, über
dieselben drei Archiv-Endpunkte, aus denen WeintTV seinen Archivmodus
speist. Diese Datei ist die reine Hälfte davon - Antwort einlesen,
Verlauf bilden, beschriften. Kein `httpx`, kein Qt, aus demselben
Grund wie bei `core/raid_schedule.py`.

Drei Regeln:

- **Die laufende Sitzung schlägt das Archiv.** Ein Pull, der gerade
  eben endete, ist der letzte - auch wenn WarcraftLogs ihn noch nicht
  kennt. Das Archiv ist der Rückfall für alles davor, nicht die
  bessere Quelle.
- **Die Fightliste genügt.** Bossname, Ausgang, Dauer und Pullnummer
  stehen schon darin; der einzelne Pull kostet den Bot Minuten
  (`FIGHT_TIMEOUT`), und die Karte zeigt nichts, was ihn bräuchte.
  Was sie ohne ihn nicht sagen kann - Bewertung und Lektion - sagt
  sie ausdrücklich nicht, statt sie zu schätzen.
- **Ein Zeitpunkt, den niemand gemeldet hat, bleibt leer.** Die
  Fightliste nennt keine Uhrzeit je Pull, nur der Bericht nennt
  seinen Beginn. Die Karte schreibt deshalb "GESTERN" und nicht
  "GESTERN 22:41" - eine Uhrzeit vom Berichtsbeginn wäre die des
  ersten Pulls, angezeigt beim letzten.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from analyzer.providers.warcraftlogs_payload import build_fight_list


#
# Wie viele Pulls die Kurve trägt. Acht sind der Ausschnitt, in dem
# "wird es besser?" noch als Richtung lesbar ist; darüber wird die
# Linie auf 132 px zum Zickzack.
#

TREND_LENGTH = 8

WEEKDAYS = (
    "MO",
    "DI",
    "MI",
    "DO",
    "FR",
    "SA",
    "SO",
)


@dataclass(frozen=True)
class LastPull:
    """
    Ein abgeschlossener Pull, so weit die Übersicht ihn braucht.

    `known` ist wie bei `RaidSchedule` die eine Frage der Oberfläche:
    gibt es überhaupt etwas zu zeigen?
    """

    known: bool = False

    boss: str = ""

    difficulty: str = ""

    kill: bool = False

    boss_percent: float = 100.0

    duration: float = 0.0

    pull_number: int = 0

    #
    # Woher der Pull stammt. `live` heißt "in dieser Sitzung
    # ausgewertet" - dann gibt es keinen Bericht und keinen Tag, wohl
    # aber eine Bewertung an anderer Stelle.
    #

    live: bool = False

    report_code: str = ""

    report_title: str = ""

    started: datetime | None = None

    fight_id: int = 0

    #
    # Der Bossanteil der letzten Pulls **desselben Bosses**, ältester
    # zuerst. Pulls verschiedener Bosse in eine Kurve zu legen ergäbe
    # eine Linie, die nichts verbindet.
    #

    trend: tuple[float, ...] = ()


def _trend_of(fights, boss: str) -> tuple[float, ...]:
    """
    Die Kurve: geschaffter Anteil je Pull, ältester zuerst.

    Gezeichnet wird `100 - Bossleben`, also der Fortschritt - eine
    steigende Linie heißt "es wird besser". Andersherum wäre sie
    richtig und läse sich falsch.
    """

    same = [
        fight
        for fight in fights
        if fight.encounter_name == boss
    ]

    return tuple(
        100.0 - float(fight.boss_percentage)
        for fight in same[-TREND_LENGTH:]
    )


def from_fights(
    fights,
    report: dict | None = None,
) -> LastPull:
    """
    Der letzte Pull einer Fightliste.

    "Letzter" ist der letzte Eintrag der Liste, nicht der mit der
    höchsten Pullnummer: die Nummer zählt je Boss, und wer am Abend
    von Boss zu Boss zieht, hätte sonst den Pull mit den meisten
    Versuchen statt den zuletzt gespielten.
    """

    fights = tuple(fights or ())

    if not fights:
        return LastPull()

    last = fights[-1]

    report = report if isinstance(report, dict) else {}

    return LastPull(
        known=True,
        boss=last.encounter_name,
        difficulty=last.difficulty,
        kill=last.kill,
        boss_percent=float(last.boss_percentage),
        duration=float(last.duration),
        pull_number=last.pull_number,
        report_code=str(report.get("code") or ""),
        report_title=str(report.get("title") or report.get("zone") or ""),
        started=_parse_moment(report.get("start")),
        fight_id=last.fight_id,
        trend=_trend_of(fights, last.encounter_name),
    )


def parse_last_pull(data) -> LastPull:
    """
    Den Zwischenspeicher einlesen, den `LastPullSync` schreibt.

    Er trägt die Fightliste in der Form des Bots
    (`{"report": …, "fights": […]}`), damit dieselbe
    `build_fight_list()` sie liest wie der Archivmodus - eine zweite
    Übersetzung derselben Antwort würde irgendwann auseinanderlaufen.

    Eine Ausnahme: der **Schwierigkeitsgrad** kommt vom Bot als Zahl
    und wird beim Einlesen in einen Namen übersetzt; zurückrechnen
    ließe er sich nicht. Er reist deshalb als `difficulty_name` mit
    und wird hier über die Fight-ID wieder zugeordnet - nicht über
    die Position, denn `build_fight_list()` wirft Trash heraus und
    die Reihen stünden dann versetzt.
    """

    if not isinstance(data, dict):
        return LastPull()

    rows = data.get("fights")

    pull = from_fights(
        build_fight_list({"fights": rows}),
        data.get("report"),
    )

    if not pull.known or not isinstance(rows, (list, tuple)):
        return pull

    for row in rows:

        if not isinstance(row, dict):
            continue

        if row.get("id") != pull.fight_id:
            continue

        name = str(row.get("difficulty_name") or "").strip()

        if name:
            pull = replace(pull, difficulty=name)

        break

    return pull


def from_history(history) -> LastPull:
    """
    Der letzte Pull der laufenden Sitzung (`PullSummary`).

    Die Felder heißen dort anders als in der Fightliste
    (`encounter_name`/`boss_health_percent`), und genau das war der
    zweite Teil des Fehlers: die Karte las `boss` und `boss_percent`
    per `getattr` mit Standardwert, fand beides nie und zeigte selbst
    mit gefüllter Historie "Kampf" ohne Kurve. Ein `getattr` mit
    Rückfall ist eine stille Zusicherung, dass das Feld optional sei -
    hier war es schlicht falsch geschrieben.
    """

    history = tuple(history or ())

    if not history:
        return LastPull()

    last = history[-1]

    same = [
        entry
        for entry in history
        if entry.encounter_name == last.encounter_name
    ]

    return LastPull(
        known=True,
        boss=last.encounter_name,
        kill=last.killed,
        boss_percent=float(last.boss_health_percent),
        duration=float(last.duration),
        pull_number=last.pull_number,
        live=True,
        trend=tuple(
            100.0 - float(entry.boss_health_percent)
            for entry in same[-TREND_LENGTH:]
        ),
    )


def _parse_moment(value) -> datetime | None:
    """
    Der Beginn des Berichts, wie WarcraftLogs ihn meldet.

    Dieselbe Haltung wie in `raid_schedule._parse_moment()`: nicht
    lesbar heißt nicht vorhanden. Ein `Z` am Ende versteht
    `fromisoformat()` erst ab Python 3.11 - die Umschrift kostet eine
    Zeile und erspart ein leeres Datum auf älteren Fassungen.
    """

    text = str(value or "").strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        moment = datetime.fromisoformat(text)

    except ValueError:
        return None

    if moment.tzinfo is not None:
        moment = moment.astimezone()

    return moment


# --------------------------------------------------
# Beschriftung
# --------------------------------------------------


def result_text(pull: LastPull | None) -> str:
    """
    "Heroisch · Kill · 06:12 · Pull 7" - die Zeile unter dem Boss.

    Ein Wipe nennt den erreichten Bossanteil, kein "Wipe" allein: der
    Unterschied zwischen 42 % und 2 % ist der ganze Abend.
    """

    if pull is None or not pull.known:
        return ""

    total = max(0, int(pull.duration))

    parts = []

    if pull.difficulty:
        parts.append(pull.difficulty)

    parts.append(
        "Kill"
        if pull.kill
        else f"Wipe bei {pull.boss_percent:.0f} %"
    )

    if total:
        parts.append(f"{total // 60:02d}:{total % 60:02d}")

    if pull.pull_number:
        parts.append(f"Pull {pull.pull_number}")

    return " · ".join(parts)


def when_text(pull: LastPull | None, now: datetime | None = None) -> str:
    """
    Die Rubrik rechts oben in der Karte: "HEUTE", "GESTERN", "MI ·
    10.08." - oder, für die laufende Sitzung, woher der Pull kommt.

    Kein Datum heißt keine Rubrik. Ein "GESTERN" auf Verdacht wäre in
    der Anzeige von einem gemeldeten nicht zu unterscheiden.
    """

    if pull is None or not pull.known:
        return ""

    if pull.live:
        return "DIESE SITZUNG"

    if pull.started is None:
        return ""

    today = (now or datetime.now()).date()

    day = pull.started.date()

    delta = (today - day).days

    if delta == 0:
        return "HEUTE"

    if delta == 1:
        return "GESTERN"

    return (
        f"{WEEKDAYS[day.weekday()]} · "
        f"{day.strftime('%d.%m.')}"
    )


def source_text(pull: LastPull | None) -> str:
    """
    Woher die Karte ihre Angaben hat.

    Steht unter der Lektionskarte und ist keine Zierde: ein Pull aus
    dem Archiv trägt **keine** Bewertung, und ohne diesen Satz sähe
    die leere Sternreihe daneben wie ein Urteil aus statt wie eine
    fehlende Auswertung.
    """

    if pull is None or not pull.known:
        return ""

    if pull.live:
        return ""

    return pull.report_title or "WarcraftLogs-Bericht"
