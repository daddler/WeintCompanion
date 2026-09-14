"""
Der Raid-Kontext: welchen Pull habe ich gerade vor mir?

**Warum es diese Datei gibt.** Bis 3.6.0 gab es drei Bereiche in der
Navigation - WeintTV, Academy, Archiv -, die sich unsichtbar eine
Datenquelle, einen Snapshot und eine Archivauswahl teilten. Der Nutzer
musste selbst wissen, wann er welchen öffnen muss, und die Antwort auf
die Frage "welcher Kampf ist das hier eigentlich" stand auf jeder der
drei Seiten anders (WeintTV: Bossname im Kopfblock; Academy:
`encounter_meta()`; Archiv: `selection_text()`). Drei Formulierungen
desselben Sachverhalts laufen auseinander, und genau das ist passiert.

Seit 4.0 ist ein **Raid/Pull der zentrale Gegenstand** der Oberfläche
und *Live*, *Analyse*, *Lernen* und *Quelle* sind vier Perspektiven
darauf. Diese Datei ist die eine Beschreibung dieses Gegenstands.

**Sie hält keinen Zustand.** Das ist die wichtigste Eigenschaft:
`RaidDataService` ist und bleibt die einzige Wahrheit über Modus,
Archivauswahl, Wiedergabe und Snapshot. `context_from()` ist eine
reine Projektion darüber - ein Leseformat, keine zweite Verwaltung.
Ein zweiter Archiv- oder Wiedergabezustand daneben wäre genau der
Fehler, den die Architektur seit 2.8.0 vermeidet.

Qt-frei und ohne Netz, aus demselben Grund wie
`core/archive_index.py` und `gui/widgets/tv/analysis_gap.py`: *welcher
Satz über dem Bildschirm steht* ist die Stelle, an der etwas falsch
sein kann, und ein Fenster braucht man dafür nicht.

Drei Regeln, die nicht Geschmack sind:

- **Der Snapshot sagt, was läuft; die Fightliste sagt, wann es war.**
  Ein `RaidSnapshot` trägt keinen Zeitstempel des Pulls (er beschreibt
  einen Moment, nicht einen Kalendereintrag), die `FightSummary` des
  Archivs dagegen schon. Der Kontext liest beides und nimmt je Feld
  die Quelle, die es kennt - statt ein Datum zu erfinden.
- **Unbekannt bleibt unbekannt.** `pull_number == 0`, `started is
  None`, `duration == 0.0` heissen "nicht gemeldet" und nie "Pull 0",
  "Mitternacht", "sofort vorbei" - dieselbe Linie, an der `stars == 0`
  und `at == -1` entlanglaufen.
- **Der Ausgang ist dreiwertig.** Solange gekämpft wird, ist er
  *offen*. Ihn am aktuellen Bossbalken als Wipe auszugeben wäre eine
  Behauptung über einen Kampf, der noch läuft - in einer Wiedergabe
  viermal je Sekunde eine andere.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.raid_state import (
    MODE_ARCHIVE,
    MODE_LIVE,
    MODE_REPLAY,
)


#
# --------------------------------------------------
# Ausgang eines Pulls
# --------------------------------------------------
#
# Drei Werte, nicht zwei. `OUTCOME_UNKNOWN` ist der vierte Fall und
# heisst "es liegt gar kein Kampf vor" - er ist von "läuft noch"
# verschieden, weil der eine eine Auskunft über den Kampf ist und der
# andere über das Fehlen eines Kampfes.
#

OUTCOME_UNKNOWN = ""

OUTCOME_OPEN = "open"

OUTCOME_KILL = "kill"

OUTCOME_WIPE = "wipe"


def outcome_of(
    has_data: bool,
    in_combat: bool,
    boss_percent: float,
) -> str:
    """
    Wie ein Pull ausging - die **eine** Stelle, an der diese Frage
    beantwortet wird.

    `gui/widgets/tv/encounter_meta.outcome_text()` formuliert daraus
    den Satz für die Bewertungszeile; zwei getrennte Ableitungen
    derselben drei Fälle wären zwei Antworten, die beim nächsten
    Sonderfall auseinanderlaufen.
    """

    if not has_data:
        return OUTCOME_UNKNOWN

    if in_combat:
        return OUTCOME_OPEN

    return OUTCOME_KILL if boss_percent <= 0 else OUTCOME_WIPE


WEEKDAYS = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)


@dataclass(frozen=True)
class RaidContext:
    """
    Der Kampf, den der Nutzer gerade vor sich hat - so weit bekannt.

    `known` ist wie bei `RaidSchedule` und `LastPull` die eine Frage
    der Oberfläche: gibt es überhaupt etwas zu zeigen? Ein Kontext
    ohne Kampf ist kein Fehler - er ist der Normalfall zwischen zwei
    Raidabenden, und die Oberfläche sagt dann, was fehlt.
    """

    known: bool = False

    #
    # Woher die Zahlen kommen (Schlüssel aus `SOURCE_LABELS`), und in
    # welcher Betriebsart sie gelesen werden: live, ein archivierter
    # Pull, oder eine laufende Wiedergabe.
    #

    source: str = ""

    mode: str = MODE_LIVE

    #
    # Welcher Pull. `report_code`/`fight_id` sind die Kennung, unter
    # der ein Pull erneut geladen werden kann - sie sind das, was ein
    # Tiefenverweis (Übersicht -> Raid Center) weitergibt.
    #

    report_code: str = ""

    fight_id: int | None = None

    encounter_id: int = 0

    #
    # Wie er heisst. `instance` ist die Zone ("Belagerung von
    # Orgrimmar"), `boss` der Kampf darin.
    #

    instance: str = ""

    boss: str = ""

    difficulty: str = ""

    raid_size: int = 0

    pull_number: int = 0

    #
    # Wie er ausging, und wie weit er kam.
    #

    outcome: str = OUTCOME_UNKNOWN

    boss_percent: float = 100.0

    duration: float = 0.0

    #
    # Wann er war. `None` heisst "niemand hat es gemeldet" - die
    # Fightliste des Bots kennt die Uhrzeit erst seit der Runde zu
    # 3.0.0, und der Live-Feed kennt sie gar nicht.
    #

    started: datetime | None = None

    #
    # Auf wen sich Bewertung und Analyse beziehen. Leer heisst "noch
    # niemand gewählt" - geraten wird hier nichts (siehe
    # analyzer/names.py).
    #

    character: str = ""

    #
    # Ob der Stand aus einem laufenden Log kommt. Bewusst getrennt von
    # `mode`: eine Wiedergabe ist nicht live, obwohl sie sich bewegt.
    #

    live: bool = False

    #
    # Läuft gerade ein Abruf? Dann ist "kein Kampf" keine Auskunft,
    # sondern nur noch nicht eingetroffen.
    #

    loading: bool = False

    #
    # Warum kein Kampf dasteht, wenn einer dastehen sollte. Leer heisst
    # "kein Fehler".
    #
    # Er gehört in den Kontext und nicht nur in die Quellenansicht: ein
    # fehlgeschlagener Abruf liess den Kopfblock bis dahin "Kein Pull
    # gewählt" sagen, obwohl einer gewählt war - und den Grund fand man
    # nur, wenn man von sich aus in die Quellenansicht wechselte. Ein
    # Leerzustand, der einen Fehler als Absicht ausgibt, ist die
    # schlechteste Sorte Leerzustand.
    #

    error: str = ""

    # --------------------------------------------------

    @property
    def replaying(self) -> bool:

        return self.mode == MODE_REPLAY

    @property
    def browsing(self) -> bool:
        """
        Ob etwas anderes als der Live-Feed gezeigt wird - dieselbe
        Frage wie `ArchiveState.browsing`, und absichtlich aus
        demselben Feld abgeleitet.
        """

        return self.mode != MODE_LIVE

    @property
    def archived(self) -> bool:
        """
        Ob dieser Pull eine Archivkennung trägt und damit erneut
        geladen werden kann. Das ist die Bedingung für jeden
        Tiefenverweis auf ihn.
        """

        return bool(self.report_code) and self.fight_id is not None

    @property
    def clock(self) -> str:
        """
        Kampfdauer als mm:ss, leer wenn sie niemand gemeldet hat.
        """

        if self.duration <= 0:
            return ""

        total = int(self.duration)

        return f"{total // 60:02d}:{total % 60:02d}"


#
# --------------------------------------------------
# Die Projektion
# --------------------------------------------------
#


def context_from(service, character: str = "") -> RaidContext:
    """
    Der Kontext, wie er sich aus dem Dienst ergibt.

    Gelesen wird ausschliesslich über die vorhandenen Zugänge
    (`archive_state()`, `replay_state()`, `current()`,
    `active_source()`), damit hier keine zweite Wahrheit entsteht.
    `getattr` durchgehend, weil diese Funktion auch gegen die
    Testdoppel der Archivtests läuft, die nur einen Teil des Dienstes
    nachbilden.
    """

    state = getattr(service, "archive_state", lambda: None)()

    snapshot = getattr(service, "current", lambda: None)()

    source = getattr(service, "active_source", lambda: "")() or ""

    mode = getattr(state, "mode", MODE_LIVE) if state is not None else MODE_LIVE

    fight = _selected_fight(state)

    report = _selected_report(state)

    #
    # Der Snapshot ist die Auskunft über den Kampf selbst. Im
    # Archivmodus ist er der geladene Pull, in der Wiedergabe die
    # gerade gezeigte Sekunde - in beiden Fällen derselbe Gegenstand
    # wie die gewählte `FightSummary`, nur feiner aufgelöst.
    #

    has_data = bool(getattr(snapshot, "has_data", False))

    encounter = getattr(snapshot, "encounter", None)

    #
    # **Nicht** über `snapshot.encounter_name`: die Eigenschaft
    # antwortet ohne Kampf mit dem Platzhalter "Kein Kampf", und der
    # stünde hier als Bossname da - dann könnte `boss_line()` nicht
    # mehr unterscheiden, ob ein Kampf vorliegt, und der Kopfblock
    # verlöre seinen Leerzustand samt nächstem Schritt.
    #

    boss = (
        (getattr(encounter, "name", "") if encounter is not None else "")
        or getattr(fight, "encounter_name", "")
    )

    instance = getattr(encounter, "instance", "") if encounter is not None else ""

    if not instance and report is not None:
        instance = getattr(report, "zone", "") or ""

    difficulty = (
        (getattr(encounter, "difficulty", "") if encounter is not None else "")
        or getattr(fight, "difficulty", "")
    )

    raid_size = int(
        (getattr(encounter, "raid_size", 0) if encounter is not None else 0)
        or getattr(fight, "size", 0)
        or 0
    )

    #
    # Pullnummer, Dauer und Bossanteil: der Snapshot zuerst, weil er
    # den laufenden Stand kennt; die Fightliste als Rückfall, weil sie
    # den Pull auch dann beschreibt, wenn er noch nicht geladen ist.
    #

    pull_number = int(
        getattr(snapshot, "pull_number", 0)
        or getattr(fight, "pull_number", 0)
        or 0
    )

    duration = float(
        getattr(snapshot, "pull_seconds", 0.0)
        or getattr(fight, "duration", 0.0)
        or 0.0
    )

    if has_data:

        boss_percent = float(getattr(snapshot, "boss_health_percent", 100.0))

        outcome = outcome_of(
            True,
            bool(getattr(snapshot, "in_combat", False)),
            boss_percent,
        )

    elif fight is not None:

        boss_percent = float(getattr(fight, "boss_percentage", 100.0))

        outcome = (
            OUTCOME_KILL
            if getattr(fight, "kill", False)
            else OUTCOME_WIPE
        )

    else:

        boss_percent = 100.0

        outcome = OUTCOME_UNKNOWN

    started = _moment_of(fight, report)

    return RaidContext(
        known=bool(has_data or fight is not None),
        source=source,
        mode=mode,
        report_code=getattr(state, "selected_report", "") or "",
        fight_id=getattr(state, "selected_fight", None),
        encounter_id=int(getattr(fight, "encounter_id", 0) or 0),
        instance=instance,
        boss=boss,
        difficulty=difficulty,
        raid_size=raid_size,
        pull_number=pull_number,
        outcome=outcome,
        boss_percent=boss_percent,
        duration=duration,
        started=started,
        character=character or "",
        error=_error_of(state),
        live=bool(getattr(snapshot, "live", False)) and has_data,
        loading=bool(getattr(state, "fight_loading", False)),
    )


def _error_of(state) -> str:
    """
    Der erste Fehler, der einen Kampf verhindert - in der Reihenfolge
    der Schritte.

    Nur beim Blättern: im Live-Modus beschreiben die Archivfehler einen
    Weg, den gerade niemand geht, und ein alter Fehler von vorhin über
    dem laufenden Raid wäre schlicht falsch.
    """

    if state is None or getattr(state, "mode", MODE_LIVE) == MODE_LIVE:
        return ""

    return (
        getattr(state, "fight_error", "")
        or getattr(state, "fights_error", "")
        or getattr(state, "reports_error", "")
    )


def _selected_report(state):

    code = getattr(state, "selected_report", "")

    if not code:
        return None

    for report in getattr(state, "reports", ()) or ():

        if getattr(report, "code", "") == code:
            return report

    return None


def _selected_fight(state):

    fight_id = getattr(state, "selected_fight", None)

    if fight_id is None:
        return None

    for fight in getattr(state, "fights", ()) or ():

        if getattr(fight, "fight_id", None) == fight_id:
            return fight

    return None


def _parse(value) -> datetime | None:

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).astimezone()

    except (ValueError, TypeError):
        return None


def _moment_of(fight, report) -> datetime | None:
    """
    Wann der Pull war.

    Die Uhrzeit des **Pulls** zuerst; kennt der Bot sie nicht, bleibt
    der Beginn des Berichts - das ist der richtige *Abend*, und mehr
    behauptet die Anzeige dann auch nicht (siehe `when_line()`).
    """

    moment = _parse(getattr(fight, "start", "")) if fight is not None else None

    if moment is not None:
        return moment

    return _parse(getattr(report, "start", "")) if report is not None else None


#
# --------------------------------------------------
# Beschriftung
# --------------------------------------------------
#
# Vier Zeilen, und jede beantwortet genau eine Frage. Sie stehen hier
# und nicht im Kopfwidget, damit ein Test sie ohne Fenster prüfen kann
# - und damit es sie nur einmal gibt.
#


def instance_line(context: RaidContext) -> str:
    """
    Die Rubrik über dem Bossnamen: wo das war.
    """

    parts = [context.instance]

    if context.difficulty:
        parts.append(context.difficulty)

    elif context.raid_size:
        parts.append(f"{context.raid_size}er")

    return " · ".join(part for part in parts if part).upper()


def boss_line(context: RaidContext) -> str:
    """
    Der Titel: welcher Kampf.
    """

    return context.boss or ""


def outcome_label(context: RaidContext) -> str:
    """
    Ein Wort zum Ausgang - leer, wenn es keinen Kampf gibt.
    """

    if context.outcome == OUTCOME_OPEN:
        return "läuft"

    if context.outcome == OUTCOME_KILL:
        return "Kill"

    if context.outcome == OUTCOME_WIPE:
        return "Wipe"

    return ""


def facts_line(context: RaidContext) -> str:
    """
    "Pull 17 · Wipe · 42 % · 06:31" - jeder Teil fällt einzeln weg,
    wenn er fehlt.

    Der Bossanteil steht **nicht** neben einem Kill: "Kill · 0 %" ist
    dieselbe Auskunft zweimal, und die zweite liest sich wie ein
    Mangel.
    """

    parts: list[str] = []

    if context.pull_number:
        parts.append(f"Pull {context.pull_number}")

    outcome = outcome_label(context)

    if outcome:
        parts.append(outcome)

    if context.outcome in (OUTCOME_WIPE, OUTCOME_OPEN):
        parts.append(f"{context.boss_percent:.0f} %")

    if context.clock:
        parts.append(context.clock)

    return " · ".join(parts)


def when_line(context: RaidContext) -> str:
    """
    "Mittwoch · 10.09. · 21:43" - der Wochentag zuerst, weil die Raids
    dieser Gilde Wochentage sind und niemand ein Datum im Kopf hat.

    Leer, wenn niemand einen Zeitpunkt gemeldet hat. Eine erfundene
    Uhrzeit wäre von einer echten nicht zu unterscheiden.
    """

    moment = context.started

    if moment is None:
        return ""

    return " · ".join((
        WEEKDAYS[moment.weekday()],
        moment.strftime("%d.%m."),
        moment.strftime("%H:%M"),
    ))


def empty_line(context: RaidContext) -> str:
    """
    Was statt des Bossnamens dasteht, wenn es keinen Kampf gibt.

    Vier verschiedene Lagen, vier verschiedene Sätze: der Abruf ist
    fehlgeschlagen, es wird geladen, es läuft der Live-Feed und gerade
    kämpft niemand, oder es ist einfach nichts gewählt. Ein gemeinsames
    "Keine Daten" für alle vier wäre der Zustand, aus dem man nicht
    weiterkommt - und der erste Fall als "nichts gewählt" ausgegeben
    wäre eine falsche Auskunft, nicht bloss eine dürftige.
    """

    if context.error:
        return "Pull nicht geladen"

    #
    # Gewählt, aber (noch) nicht beschrieben: die Pullliste dieses
    # Berichts ist unterwegs. "Kein Pull gewählt" wäre hier das
    # Gegenteil der Wahrheit.
    #

    if context.loading or (context.archived and not context.known):
        return "Pull wird geladen …"

    if context.mode == MODE_LIVE:
        return "Kein laufender Kampf"

    return "Kein Pull gewählt"


def empty_hint(context: RaidContext) -> str:
    """
    Der Satz darunter - er nennt den nächsten Schritt, nicht den
    Mangel. Beim Fehlschlag ist der Grund der nächste Schritt.
    """

    if context.error:
        return context.error

    if context.loading or (context.archived and not context.known):
        return (
            "Der Bot liest den ganzen Kampf. Die Ansichten füllen "
            "sich, sobald er antwortet."
        )

    if context.mode == MODE_LIVE:
        return (
            "Sobald euer Raid pullt, steht der Kampf hier. Einen "
            "vergangenen Pull findest du unter „Quelle“."
        )

    return "Unter „Quelle“ wählst du Raidabend, Boss und Pull."


def mode_label(context: RaidContext) -> str:
    """
    Wie der Kampf gerade gelesen wird - als Chip neben dem Bossnamen.

    Er beantwortet **zwei** Fragen in einem Wort, und bis 3.6.0 taten
    das zwei Chips auf verschiedenen Seiten: in welcher Betriebsart
    gelesen wird (WeintTVs Kopf sagte das nicht, der `ArchivePicker`
    schon) und ob überhaupt Daten fliessen (WeintTVs `feed_chip`).
    Getrennt gingen sie auseinander - ein "LIVE" neben einem
    archivierten Pull war möglich.

    Im Archiv und in der Wiedergabe ist die Betriebsart die Antwort;
    im Live-Modus ist sie bekannt, und dann zählt der Fluss.
    """

    if context.mode == MODE_REPLAY:
        return "WIEDERGABE"

    if context.mode == MODE_ARCHIVE:
        return "ARCHIV"

    if context.live:
        return "LIVE"

    return "DATEN AKTIV" if context.known else "KEINE DATEN"


def same_pull(left: RaidContext, right: RaidContext) -> bool:
    """
    Ob zwei Kontexte denselben Pull meinen.

    Gefragt wird über die Archivkennung, nicht über die Beschriftung:
    während einer Wiedergabe ändern sich Bossanteil, Dauer und Ausgang
    viermal je Sekunde, der Pull dabei nie. Genau diese Unterscheidung
    braucht die Oberfläche, um einen Perspektivwechsel von einem
    Pullwechsel zu unterscheiden.
    """

    if left.archived or right.archived:

        return (
            left.report_code == right.report_code
            and left.fight_id == right.fight_id
        )

    return (
        left.boss == right.boss
        and left.pull_number == right.pull_number
        and left.mode == right.mode
    )
