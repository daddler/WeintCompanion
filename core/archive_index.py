"""
Die reine Hälfte des Archivbrowsers: aus einer Liste von Berichten und
einer Liste von Pulls wird das, was man in einer Auswahl tatsächlich
sucht.

Kein Qt, kein `httpx`, keine Datei — aus demselben Grund wie
`roster_target()`, `build_profile_payload()` und
`gui/widgets/tv/analysis_gap.py`: *welche Zeilen dastehen und wie sie
beschriftet sind* ist genau die Stelle, an der etwas falsch sein kann,
und ein Fenster braucht man dafür nicht.

Warum es dieses Modul überhaupt gibt: bis 2.8.0 war das Archiv zwei
Ausklapplisten nebeneinander. Die zweite davon trägt an einem
Raidabend leicht sechzig Zeilen, alle in der Form „Pull 14 · Garrosh ·
42 % · 06:31", und die einzige Ordnung darin war die Reihenfolge des
Berichts. Wer den einen Versuch wiederfinden wollte, über den in der
Gilde gesprochen wurde, hat gescrollt und geraten. Gemeldet wurde es
als „es ist ziemlich kompliziert, archivierte Logs zu finden", und das
ist die richtige Beschreibung: die Daten waren alle da, gefunden hat
man damit trotzdem nichts.

Vier Fragen beantwortet dieses Modul, und jede davon ist eine, die man
vor der Liste wirklich hat:

    Welcher Abend?      `group_reports_by_day` — der Bericht heisst
                        „Siege of Orgrimmar", und der von letzter
                        Woche auch.
    Welcher Boss?       `group_fights` — nach Boss gebündelt, in der
                        Reihenfolge, in der er im Bericht zuerst
                        vorkam.
    Welcher Versuch?    `best_try` — der beste Wipe eines Bosses ist
                        der, den man ansehen will, wenn es keinen Kill
                        gibt.
    Wo war es noch?     `match_report` / `match_fight` — Suchtext über
                        alles, was auf der Zeile steht.

Nichts davon wertet: gruppiert und beschriftet wird, gerechnet wird
nicht. Der Snapshot bleibt die einzige Auskunft über den Kampf selbst.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


#
# --------------------------------------------------
# Suchtext
# --------------------------------------------------
#


def normalize(text: str) -> str:
    """
    Vergleichsform für die Suche: klein geschrieben, Umlaute
    aufgelöst.

    Die Auflösung ist nicht Kosmetik. Bosse und Zonen heissen in einem
    deutschen Bericht „Malkorok" und „Belagerung von Orgrimmar", und
    wer sie sucht, tippt sie schon mal ohne Umlaut — eine Suche, die
    „Sha des Zorns" nicht findet, weil jemand „sha des zorns" mit
    anderem „ß" getippt hat, ist eine, die man nach zwei Versuchen
    nicht mehr benutzt.
    """

    lowered = (text or "").lower()

    for source, target in (
        ("ä", "a"),
        ("ö", "o"),
        ("ü", "u"),
        ("ß", "ss"),
        ("é", "e"),
        ("è", "e"),
    ):
        lowered = lowered.replace(source, target)

    return lowered


def _matches(needle: str, *haystack: str) -> bool:

    query = normalize(needle).strip()

    if not query:
        return True

    #
    # Jedes Wort muss vorkommen, nicht die ganze Eingabe am Stück:
    # „garrosh kill" soll den Kill auf Garrosh finden, obwohl die
    # beiden Wörter auf der Zeile nicht nebeneinander stehen.
    #

    fields = normalize(" ".join(part for part in haystack if part))

    return all(word in fields for word in query.split())


def match_report(report, needle: str) -> bool:
    """
    Ob ein Bericht auf den Suchtext passt.
    """

    return _matches(
        needle,
        getattr(report, "title", ""),
        getattr(report, "zone", ""),
        getattr(report, "code", ""),
        day_label(getattr(report, "start", "")),
    )


def match_fight(fight, needle: str) -> bool:
    """
    Ob ein Pull auf den Suchtext passt.

    Gesucht wird über genau das, was auf der Zeile steht — Bossname,
    Schwierigkeit, Ausgang, Uhrzeit und Pull-Nummer. Ein Suchfeld, das
    über unsichtbare Felder mitsucht, liefert Treffer, die niemand
    erklären kann.
    """

    return _matches(
        needle,
        getattr(fight, "encounter_name", ""),
        getattr(fight, "difficulty", ""),
        "kill" if getattr(fight, "kill", False) else "wipe",
        getattr(fight, "time_label", ""),
        f"pull {getattr(fight, 'pull_number', 0)}",
    )


#
# --------------------------------------------------
# Berichte: welcher Abend war das?
# --------------------------------------------------
#


WEEKDAYS = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)


def _parse(iso_timestamp: str):

    if not iso_timestamp:
        return None

    try:
        return datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00")).astimezone()

    except ValueError:
        return None


def day_label(iso_timestamp: str) -> str:
    """
    „Mittwoch, 03.09.2026" — der Wochentag steht vorn, weil die Raids
    dieser Gilde Wochentage sind und niemand ein Datum im Kopf hat.

    Leerer String, wenn der Zeitstempel fehlt oder unlesbar ist. Ein
    erfundenes Datum wäre von einem echten nicht zu unterscheiden —
    dieselbe Linie, an der `stars == 0` und `readiness() is None`
    entlanglaufen.
    """

    moment = _parse(iso_timestamp)

    if moment is None:
        return ""

    return f"{WEEKDAYS[moment.weekday()]}, {moment.strftime('%d.%m.%Y')}"


def report_title(report) -> str:
    """
    Wie der Bericht heisst — Titel, sonst Zone, sonst sein Code.
    """

    return (
        getattr(report, "title", "")
        or getattr(report, "zone", "")
        or getattr(report, "code", "")
    )


def report_subtitle(report) -> str:
    """
    Die zweite Zeile eines Berichtseintrags: Zone und Code.

    Der Code gehört dazu, obwohl ihn niemand liest — er ist das, was
    in einem Discord-Link steht, und damit die einzige Möglichkeit,
    einen dort genannten Bericht hier wiederzufinden.
    """

    zone = getattr(report, "zone", "")

    code = getattr(report, "code", "")

    parts = [part for part in (zone if zone != report_title(report) else "", code) if part]

    return " · ".join(parts)


@dataclass(frozen=True)
class ReportDay:
    """
    Ein Raidabend mit den Berichten, die an ihm entstanden sind.
    """

    label: str

    reports: tuple

    @property
    def key(self) -> str:

        return self.label


def group_reports_by_day(reports, needle: str = "") -> tuple[ReportDay, ...]:
    """
    Berichte nach Tag gebündelt, in der gelieferten Reihenfolge
    (neueste zuerst).

    Berichte ohne lesbares Datum kommen **nicht** unter einen
    erfundenen Tag, sondern unter „Ohne Datum" ans Ende: sie
    existieren, nur ihr Zeitpunkt ist unbekannt, und ein geratener
    wäre schlechter als gar keiner.
    """

    days: list[ReportDay] = []

    index: dict[str, list] = {}

    for report in reports:

        if not match_report(report, needle):
            continue

        label = day_label(getattr(report, "start", "")) or "Ohne Datum"

        if label not in index:

            index[label] = []

            days.append(label)

        index[label].append(report)

    ordered = [label for label in days if label != "Ohne Datum"]

    if "Ohne Datum" in index:
        ordered.append("Ohne Datum")

    return tuple(
        ReportDay(label=label, reports=tuple(index[label]))
        for label in ordered
    )


#
# --------------------------------------------------
# Pulls: welcher Boss, welcher Versuch?
# --------------------------------------------------
#


@dataclass(frozen=True)
class BossGroup:
    """
    Alle Pulls eines Bosses innerhalb eines Berichts.
    """

    encounter_id: int

    name: str

    fights: tuple

    @property
    def killed(self) -> bool:

        return any(fight.kill for fight in self.fights)

    @property
    def summary(self) -> str:
        """
        Die Zeile über der Gruppe: wie viele Versuche, und wie es
        ausging.

        „12 Versuche · Kill" und „12 Versuche · bester Wipe 4 %" sind
        zwei verschiedene Auskünfte, und die zweite ist die, wegen der
        man einen Wipe-Abend überhaupt noch einmal aufmacht.
        """

        count = len(self.fights)

        tries = "1 Versuch" if count == 1 else f"{count} Versuche"

        if self.killed:
            return f"{tries} · Kill"

        best = best_try(self.fights)

        if best is None:
            return tries

        return f"{tries} · bester Versuch {best.boss_percentage:.0f} %"


def best_try(fights):
    """
    Der beste Versuch einer Reihe von Pulls.

    Ein Kill schlägt jeden Wipe; unter Wipes gewinnt der niedrigste
    Bossanteil, und bei gleichem Anteil der längere Kampf — er ist der,
    in dem mehr passiert ist.

    `None` bei leerer Liste statt eines Platzhalters: „kein bester
    Versuch" ist eine Antwort, ein erfundener wäre keine.
    """

    usable = [fight for fight in fights if fight is not None]

    if not usable:
        return None

    return min(
        usable,
        key=lambda fight: (
            0 if fight.kill else 1,
            fight.boss_percentage,
            -fight.duration,
        ),
    )


def group_fights(
    fights,
    needle: str = "",
    kills_only: bool = False,
) -> tuple[BossGroup, ...]:
    """
    Pulls nach Boss gebündelt, in der Reihenfolge seines ersten
    Auftretens im Bericht.

    Bewusst **nicht** alphabetisch: ein Bericht erzählt einen Abend,
    und der lief in dieser Reihenfolge. Wer den letzten Boss sucht,
    scrollt nach unten — wer alphabetisch sortiert, sucht überall.

    `kills_only` filtert die Pulls, nicht die Gruppen: ein Boss ohne
    Kill verschwindet damit ganz, statt als leere Überschrift
    stehenzubleiben.
    """

    groups: list[int] = []

    index: dict[int, list] = {}

    names: dict[int, str] = {}

    for fight in fights:

        if kills_only and not fight.kill:
            continue

        if not match_fight(fight, needle):
            continue

        key = fight.encounter_id

        if key not in index:

            index[key] = []

            groups.append(key)

            names[key] = fight.encounter_name

        index[key].append(fight)

    return tuple(
        BossGroup(
            encounter_id=key,
            name=names[key] or "Unbekannter Boss",
            fights=tuple(index[key]),
        )
        for key in groups
    )


def fight_count(groups) -> int:
    """
    Wie viele Pulls die gefilterte Ansicht insgesamt zeigt.
    """

    return sum(len(group.fights) for group in groups)


#
# --------------------------------------------------
# Was ist gerade geladen?
# --------------------------------------------------
#


def selection_text(state) -> str:
    """
    Ein Satz für die Quellenzeile: was gerade gezeigt wird.

    Er beantwortet die Frage, die die zwei Ausklapplisten nie
    beantwortet haben — sie zeigten die *Auswahl*, nicht das
    *Geladene*, und nach einem fehlgeschlagenen Abruf standen beide
    noch auf dem Pull, den man gar nicht vor sich hatte.

    Leerer String heisst „nichts gewählt"; der Aufrufer setzt dann
    seinen eigenen Hinweis, denn ob das ein Mangel ist, hängt vom
    Modus ab.
    """

    report = _selected_report(state)

    fight = _selected_fight(state)

    if report is None:
        return ""

    day = day_label(getattr(report, "start", ""))

    parts = [day or report_title(report)]

    if fight is not None:

        pull = (
            f"Pull {fight.pull_number}"
            if fight.pull_number
            else "Pull"
        )

        detail = f"{pull} · {fight.encounter_name} · {fight.outcome_label}"

        if fight.time_label:
            detail += f" · {fight.time_label}"

        parts.append(detail)

    return " · ".join(parts)


def _selected_report(state):

    code = getattr(state, "selected_report", "")

    if not code:
        return None

    for report in getattr(state, "reports", ()):

        if report.code == code:
            return report

    return None


def _selected_fight(state):

    fight_id = getattr(state, "selected_fight", None)

    if fight_id is None:
        return None

    for fight in getattr(state, "fights", ()):

        if fight.fight_id == fight_id:
            return fight

    return None
