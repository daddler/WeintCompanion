"""
Der nächste Raidtermin - lesen, rechnen, beschriften.

**Warum es diese Datei gibt.** Die Übersicht trug rechts oben
dauerhaft "KEIN TERMIN BEKANNT", und das war keine Vorsicht, sondern
schlicht der Stand: der Chip wurde einmal gebaut und danach nie wieder
angefasst. Was die App vom Gildenkalender kannte, waren zwei
undurchsichtige WCIMPORT-Zeichenketten, die `DiscordRosterSync`
ungeparst an das Addon durchreicht - und selbst die bekommt nur, wer
die Raidlead-Rolle trägt.

Der Bot beantwortet die Frage jetzt eigens (`/companion/raid-schedule`,
für **jeden** verknüpften Nutzer, siehe `services/raid_schedule.py`
drüben). Diese Datei ist die reine Hälfte davon: Antwort einlesen,
Restzeit rechnen, beschriften. Kein `httpx`, kein Qt - aus demselben
Grund wie bei `access_roles.build_profile_payload()` und
`backend_config.roster_target()`: die Rechnung ist die Stelle, an der
etwas falsch sein kann, und sie soll ohne Fenster und ohne Netz
prüfbar bleiben.

Drei Regeln, die den Unterschied zwischen "Auskunft" und "Behauptung"
ziehen:

- **Ein fehlender Termin bleibt ein fehlender Termin.** Ohne Antwort,
  ohne Raid oder ohne lesbares Datum gibt es keinen Ersatzwert. Ein
  auf gut Glück gesetzter Mittwoch wäre in der Anzeige von einem
  echten Termin nicht zu unterscheiden.
- **Die Zeitzone kommt vom Bot**, als Offset in `starts_at`. Die App
  rechnet die Restzeit gegen die eigene Uhr, nicht gegen eine geratene
  Zeitzone - sonst läge sie für jeden im Ausland spielenden Raider
  daneben.
- **Zugesagt heißt zugesagt.** Gezählt wird `active`; "vielleicht" und
  "Ersatzbank" stehen daneben, nicht mittendrin. Sie in eine Zahl zu
  werfen wäre genau die Art Vereinfachung, wegen der man dann doch
  wieder im Discord nachsieht.

**Die Aufstellung ist mehr als eine Zahl.** Der Entwurf der Übersicht
zeigte an dieser Stelle von Anfang an die *Zusammensetzung*: Tanks,
Heiler und Schaden als Reihen von Plätzen, gefüllte in Klassenfarbe,
offene als leere Kästchen, darunter ein Satz, was noch fehlt. Genau
das ist die Frage, wegen der man vor dem Raid ins Discord sieht - "21
von 25" beantwortet sie nicht, denn ob die vier fehlenden Heiler oder
Schaden sind, entscheidet, ob der Abend stattfindet.

Dafür trägt `days[].roster` je Zusage **Rolle und Klasse, niemals
einen Namen** (siehe `docs/raid-schedule-bridge.md`) - die Grenze des
Vertrags bleibt damit unverändert, denn beides steht ohnehin als
Symbol im Anmelde-Beitrag. Zwei Regeln kommen hinzu:

- **Ohne Rollen keine Rollen.** Fehlt der Block (ältere Bot-Fassung),
  gibt es einen einzigen Streifen "zugesagt" statt drei erfundener.
  Eine Aufteilung zu schätzen wäre in der Anzeige von einer gemeldeten
  nicht zu unterscheiden.
- **Was fehlt, sagt nur, wer ein Soll kennt.** `composition` ist die
  Sollstärke je Rolle. Ohne sie bleibt es bei "vier offene Plätze";
  mit ihr steht daneben, welche. Ein geratenes Soll (2 Tanks, 5
  Heiler) wäre für die halbe Gilde falsch.

**Und die kleinste Frage von allen: bin ich selbst schon drin?** Sie
liess sich aus dieser Antwort nicht beantworten, gerade *weil* sie
keine Namen nennt - aus "21 von 25 zugesagt" geht nicht hervor, wer
von den 21 man ist. Der Bot schickt sie deshalb je Tag als
`days[].me`, abgeleitet aus dem Token, mit dem gefragt wird. Die
Einzelheiten stehen beim Abschnitt "Der eigene Anmeldezustand" weiter
unten; die Grenze des Vertrags bleibt unverändert, denn eine Auskunft
über den Fragenden selbst ist keine über jemand anderen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


#
# --------------------------------------------------
# Rollen
# --------------------------------------------------
#
# Die Reihenfolge ist die der Anzeige: Tanks, Heiler, Schaden - so
# steht sie im Entwurf und so liest sie jeder Raidleiter. Sie ist
# hier festgelegt und nicht im Widget, damit Streifen und Satz
# darunter nicht in unterschiedlicher Folge auftreten.
#

ROLE_ORDER = ("tank", "healer", "dps")

ROLE_LABELS = {
    "tank": "TANKS",
    "healer": "HEILER",
    "dps": "SCHADEN",
}

#
# Für den Satz unter den Streifen ("1 Tank, 2 Schaden") - Einzahl und
# Mehrzahl fallen im Deutschen bei allen drei zusammen.
#

ROLE_NAMES = {
    "tank": "Tank",
    "healer": "Heiler",
    "dps": "Schaden",
}

#
# Wie der Bot eine Rolle nennen könnte. Additiv gedacht wie
# `player_abilities`: ein unbekannter Wert kostet die Zuordnung, er
# erfindet keine.
#

ROLE_ALIASES = {
    "tank": "tank",
    "tanks": "tank",
    "healer": "healer",
    "heal": "healer",
    "heals": "healer",
    "heiler": "healer",
    "dps": "dps",
    "damage": "dps",
    "damager": "dps",
    "dd": "dps",
    "schaden": "dps",
    "melee": "dps",
    "ranged": "dps",
}

#
# Zahlwörter für den Satz unter den Streifen. Der Entwurf schreibt
# "Vier offene Plätze", nicht "4 offene Plätze" - eine kleine Zahl
# ausgeschrieben liest sich als Satz statt als Messwert, und mehr als
# zwölf offene Plätze sind ohnehin keine Feinheit mehr.
#

NUMBER_WORDS = {
    2: "Zwei",
    3: "Drei",
    4: "Vier",
    5: "Fünf",
    6: "Sechs",
    7: "Sieben",
    8: "Acht",
    9: "Neun",
    10: "Zehn",
    11: "Elf",
    12: "Zwölf",
}


#
# --------------------------------------------------
# Der eigene Anmeldezustand
# --------------------------------------------------
#
# **Warum die Übersicht das überhaupt zeigt.** "21 von 25 zugesagt"
# ist die Auskunft über den Raid; die Frage, wegen der die meisten
# kurz ins Discord sehen, ist eine andere und viel kleinere: habe
# *ich* mich eigentlich schon eingetragen? Sie stand in der App
# nirgends, und beantworten liess sie sich hier auch nicht - die
# Antwort des Bots nennt bewusst keine Namen, aus ihr geht also nicht
# hervor, wer von den 21 man selbst ist.
#
# Der Bot beantwortet sie deshalb eigens, je Tag als `days[].me`: sie
# folgt aus dem Token, mit dem gefragt wird, und ist damit eine
# Auskunft über den Fragenden selbst. Die Grenze des Vertrags -
# niemals ein Name - bleibt, wo sie war.
#
# Je Tag, und nicht je Raid: Mittwoch und Donnerstag sind zwei
# Anmeldungen, und "du bist angemeldet" wäre über beide zusammen
# genau dann falsch, wenn es darauf ankommt.
#
# Fünf Zustände, und der Unterschied zwischen den letzten beiden ist
# der eigentliche Punkt: **eine Absage ist eine Antwort**, ein
# Schweigen nicht. Wer abgesagt hat, hat getan, was von ihm erwartet
# war; wer nichts getan hat, ist der einzige, der noch handeln muss.
# Beides "nicht dabei" zu nennen wäre die bequeme Zusammenfassung und
# genau die, die niemandem hilft.
#

OWN_ACTIVE = "active"

OWN_TENTATIVE = "tentative"

OWN_BENCH = "bench"

OWN_ABSENT = "absent"

OWN_NONE = "none"

OWN_STATES = (
    OWN_ACTIVE,
    OWN_TENTATIVE,
    OWN_BENCH,
    OWN_ABSENT,
    OWN_NONE,
)

#
# Die Beschriftung des Chips - Versalien wie bei jedem Chip in dieser
# Oberfläche. "NICHT ANGEMELDET" statt "OFFEN": der Chip steht neben
# dem Datum und den Zahlen des Raids, und "offen" liesse sich ebenso
# gut auf dessen Anmeldung beziehen wie auf die eigene.
#

OWN_LABELS = {
    OWN_ACTIVE: "ANGEMELDET",
    OWN_TENTATIVE: "VIELLEICHT",
    OWN_BENCH: "ERSATZBANK",
    OWN_ABSENT: "ABGEMELDET",
    OWN_NONE: "NICHT ANGEMELDET",
}

#
# Der ganze Satz - er hängt als Tooltip am Chip und beantwortet die
# Frage in derselben Sprache, in der man sie stellt.
#

OWN_SENTENCES = {
    OWN_ACTIVE: "Du bist für diesen Tag angemeldet.",
    OWN_TENTATIVE: "Du stehst für diesen Tag auf „vielleicht“.",
    OWN_BENCH: "Du stehst für diesen Tag auf der Ersatzbank.",
    OWN_ABSENT: "Du hast für diesen Tag abgesagt.",
    OWN_NONE: "Deine Anmeldung für diesen Tag fehlt noch.",
}

#
# Die Farbe. Nur die fehlende Anmeldung ist eine Aufforderung und
# trägt deshalb `warn`; eine Absage ist erledigt und bekommt die
# neutrale Fläche, keine rote. Rot hiesse "hier stimmt etwas nicht",
# und abgesagt zu haben ist kein Fehler - dieselbe Zurückhaltung, mit
# der `Chip` seine Variante `neutral` für "keine Daten" reserviert.
#

OWN_VARIANTS = {
    OWN_ACTIVE: "ok",
    OWN_TENTATIVE: "info",
    OWN_BENCH: "info",
    OWN_ABSENT: "neutral",
    OWN_NONE: "warn",
}


def normalize_own_state(value) -> str:
    """
    Der gemeldete Zustand - oder "", wenn keiner gemeldet wurde.

    Der leere Wert ist der wichtige: er heisst **"der Bot hat dazu
    nichts gesagt"** (eine ältere Fassung kennt das Feld nicht), und
    die Übersicht schweigt daraufhin. Ihn auf "nicht angemeldet"
    abzubilden wäre die übliche stille Lüge: ein Satz, auf den jemand
    hin handelt, aus einer Auskunft, die es gar nicht gibt - dieselbe
    Linie wie `stars == 0` und `readiness() is None`.
    """

    text = str(value or "").strip().lower()

    return text if text in OWN_STATES else ""


def normalize_role(value) -> str:
    """
    Die Rolle in einem der drei bekannten Werte - oder "".

    Ein unbekannter Wert wird nicht geraten: der Platz erscheint dann
    im Streifen "zugesagt" statt in einer falschen Rolle.
    """

    return ROLE_ALIASES.get(str(value or "").strip().lower(), "")


#
# Ab wann ein Termin als "läuft gerade" gilt statt als "in ... " -
# derselbe Gedanke wie `RUNNING_HOURS` im Bot, nur von der anderen
# Seite: dort entscheidet er, welcher Termin geliefert wird, hier, wie
# er beschriftet wird.
#

RUNNING_MINUTES = 4 * 60


#
# Wie weit zwei Termine auseinanderliegen dürfen, um noch **derselbe
# Raid** zu sein.
#
# Der Bot rechnet jeden Tag als *nächstes Vorkommen* seines
# Wochentags: am Donnerstag steht der Mittwoch derselben Antwort
# deshalb schon auf der kommenden Woche - mit den Zusagen des
# vergangenen. Solange die Übersicht nur den nächsten Termin nannte,
# fiel das nicht auf; untereinander stünde neben dem heutigen
# Donnerstag ein Mittwoch in sechs Tagen mit Zahlen, die zu ihm nicht
# gehören.
#
# Fünf Tage trennen die beiden Fälle sauber: die Tage eines Raids
# liegen dicht beieinander (Mittwoch und Donnerstag einen Tag), ein
# bereits gelaufener Tag ist immer mindestens sechs Tage voraus.
#

CYCLE_DAYS = 5


@dataclass(frozen=True)
class RosterSlot:
    """
    Ein zugesagter Platz: Rolle und Klasse, **kein Name**.

    Die Grenze des Vertrags verläuft genau hier. Rolle und Klasse
    stehen als Symbol in jedem Anmelde-Beitrag, den jeder im Kanal
    liest; die Namensliste bleibt hinter der Raidlead-Rolle. Ein
    `name`-Feld an dieser Stelle würde eine rollengeschützte Auskunft
    unbemerkt in eine ungeschützte verschieben.
    """

    role: str = ""

    class_name: str = ""


@dataclass(frozen=True)
class RaidDay:
    """Ein Termin des laufenden Raids."""

    key: str = ""

    label: str = ""

    starts_at: datetime | None = None

    active: int = 0

    tentative: int = 0

    bench: int = 0

    absent: int = 0

    #
    # Die Zusagen als Plätze. Leer, solange der Bot den Block nicht
    # schickt - dann zeigt die Übersicht einen einzigen Streifen
    # "zugesagt" statt drei geschätzter Rollen.
    #

    roster: tuple[RosterSlot, ...] = ()

    #
    # Der **eigene** Anmeldezustand an diesem Tag, so wie der Bot ihn
    # meldet (`days[].me`). Leer heisst "nicht gemeldet" - eine
    # ältere Bot-Fassung kennt das Feld nicht, und die Karte sagt dann
    # dazu nichts, statt eine fehlende Anmeldung zu behaupten.
    #

    me: str = ""

    # --------------------------------------------------

    def role_counts(self) -> dict[str, int]:
        """
        Wie viele Zusagen je Rolle - nur aus dem gemeldeten Roster.

        Ein leeres Ergebnis heißt "nicht bekannt" und nicht "keine
        Tanks": die beiden Fälle unterscheidet allein `roster`.
        """

        counts = {role: 0 for role in ROLE_ORDER}

        for slot in self.roster:

            if slot.role in counts:
                counts[slot.role] += 1

        return counts

    def has_roles(self) -> bool:
        """
        Ob die Zusammensetzung überhaupt bekannt ist.

        Ein Roster ohne eine einzige zuzuordnende Rolle zählt nicht -
        drei leere Streifen wären eine Behauptung über den Raid, wo
        in Wahrheit die Auskunft fehlt.
        """

        return any(self.role_counts().values())

    # --------------------------------------------------

    def minutes_until(self, now: datetime | None = None) -> int | None:
        """
        Restzeit in Minuten; negativ, wenn der Termin begonnen hat.

        `None` ohne Zeitpunkt - und nicht 0, das hieße "jetzt".
        """

        if self.starts_at is None:
            return None

        moment = now or datetime.now(timezone.utc)

        if moment.tzinfo is None:
            moment = moment.astimezone()

        return int(
            (self.starts_at - moment).total_seconds() // 60
        )

    def is_running(self, now: datetime | None = None) -> bool:

        minutes = self.minutes_until(now)

        if minutes is None:
            return False

        return -RUNNING_MINUTES < minutes <= 0


@dataclass(frozen=True)
class RaidSchedule:
    """
    Was der Bot über den laufenden Raid weiß.

    `known` ist die eine Frage, die die Oberfläche stellt: gibt es
    überhaupt etwas anzuzeigen? Alles andere darunter ist erst dann
    aussagekräftig.
    """

    known: bool = False

    title: str = ""

    raid_type: str = "standard"

    signup_status: str = "open"

    raid_size: int = 0

    days: tuple[RaidDay, ...] = field(default_factory=tuple)

    #
    # Die Sollstärke je Rolle, so wie der Raid geplant ist. Leer,
    # solange der Bot sie nicht meldet - dann bleibt es bei "vier
    # offene Plätze", ohne zu behaupten, welche.
    #

    composition: dict = field(default_factory=dict)

    detail: str = ""

    #
    # Wo die Anmeldung im Discord steht (Gilde, Kanal, Nachricht), so
    # wie der Bot sie meldet. Damit springt der Knopf "Aufstellung im
    # Discord" in den Anmelde-Beitrag statt auf den Standardkanal des
    # Servers. Leer, solange der Bot den Block nicht schickt - die
    # Companion hat dafür ihren eigenen Rückfall.
    #

    signup: dict = field(default_factory=dict)

    #
    # Die übrigen Raids, wenn im Discord mehrere gleichzeitig laufen.
    # Jeder als eigenes `RaidSchedule` - dieselben Felder, dieselben
    # Rechnungen (`next_day()`, `day_text()`), kein zweiter Datentyp,
    # der irgendwann anders rechnet als der erste.
    #
    # Leer, solange der Bot den Block nicht schickt. Das ist der
    # Normalfall bei einem einzigen Raid und der Zustand bei einer
    # älteren Bot-Fassung - beides sieht gleich aus und soll es auch.
    #

    others: tuple["RaidSchedule", ...] = field(default_factory=tuple)

    # --------------------------------------------------

    def all_raids(self) -> tuple["RaidSchedule", ...]:
        """
        Dieser Raid und die übrigen, in der Reihenfolge des Bots -
        der nächste zuerst.
        """

        if not self.known:
            return ()

        return (self,) + tuple(self.others)

    def upcoming_days(
        self,
        now: datetime | None = None,
    ) -> tuple[RaidDay, ...]:
        """
        Alle noch bevorstehenden Termine, der nächste zuerst.

        **Warum die Uebersicht mehr als einen zeigt.** Der Standardraid
        laeuft Mittwoch *und* Donnerstag, und die beiden Anmeldungen
        sind nicht dieselbe: wer am Mittwoch zusagt, muss am Donnerstag
        nicht koennen. Genannt wurde bisher nur der naechste - am
        Dienstag also der Mittwoch, und ob der Donnerstag ueberhaupt
        Leute hat, war in der App nicht zu sehen, obwohl der Bot beide
        Tage in derselben Antwort schickt.

        Ein laufender Termin zaehlt als bevorstehend, aus demselben
        Grund wie in `next_day()`: er ist der, um den es gerade geht.

        Ein Tag ohne lesbaren Zeitpunkt faellt heraus statt ans Ende -
        anders als beim Raid selbst (`others`) gaebe es hier nichts
        anzuzeigen ausser einer Reihe Kaestchen ohne Datum, und die
        waere von einem Termin nicht zu unterscheiden.

        **Und nur die Tage desselben Raids.** Der Bot nennt zu jedem
        Wochentag dessen naechstes Vorkommen: am Donnerstag steht der
        Mittwoch bereits auf der kommenden Woche - mit den Zusagen der
        vergangenen, denn die Anmeldung ist dieselbe. Neben dem
        heutigen Termin waere das eine Aufstellung zu einem Datum, zu
        dem sie nicht gehoert. `CYCLE_DAYS` schneidet ihn ab.
        """

        upcoming = [
            day
            for day in self.days
            if day.minutes_until(now) is not None
            and (day.minutes_until(now) > 0 or day.is_running(now))
        ]

        upcoming.sort(key=lambda day: day.starts_at)

        if not upcoming:
            return ()

        erster = upcoming[0].starts_at

        return tuple(
            day
            for day in upcoming
            if (day.starts_at - erster).days < CYCLE_DAYS
        )

    def next_day(self, now: datetime | None = None) -> RaidDay | None:
        """
        Der nächste Termin: der erste, der noch nicht vorbei ist.

        Ein laufender Raid gilt als der nächste - deshalb wird gegen
        `is_running()` und nicht gegen "liegt in der Zukunft" geprüft.

        Dieselbe Rechnung wie `upcoming_days()`, nur auf einen Termin
        verkuerzt: der Countdown im Kopf und die Begruessung haben
        genau einen Platz. Zwei Fassungen davon wuerden irgendwann
        verschiedene Tage nennen.
        """

        days = self.upcoming_days(now)

        return days[0] if days else None


def _parse_moment(value) -> datetime | None:
    """
    Ein ISO-Zeitpunkt mit Offset, wie der Bot ihn schickt.

    Ohne Offset wird die lokale Zeitzone angenommen: das ist die
    einzige Annahme, die nicht schlechter ist als der Verzicht auf den
    Termin, und ältere Bot-Fassungen könnten ihn weglassen.
    """

    text = str(value or "").strip()

    if not text:
        return None

    try:
        moment = datetime.fromisoformat(text)

    except ValueError:
        return None

    if moment.tzinfo is None:
        return moment.astimezone()

    return moment


def parse_schedule(data) -> RaidSchedule:
    """
    Die Antwort von `/companion/raid-schedule` einlesen.

    Defensiv wie `warcraftlogs_payload.snapshot_from_payload()`: eine
    unvollständige Antwort ist kein Fehler, sondern weniger Auskunft.
    Ein Feld, das der Bot nicht schickt, bleibt leer statt zu raten.
    """

    if not isinstance(data, dict):
        return RaidSchedule()

    if data.get("status") != "ok":

        return RaidSchedule(
            detail=str(data.get("detail") or ""),
        )

    days: list[RaidDay] = []

    for entry in data.get("days") or []:

        if not isinstance(entry, dict):
            continue

        counts = entry.get("signups") or {}

        if not isinstance(counts, dict):
            counts = {}

        days.append(
            RaidDay(
                key=str(entry.get("key") or ""),
                label=str(entry.get("label") or ""),
                starts_at=_parse_moment(entry.get("starts_at")),
                active=int(counts.get("active") or 0),
                tentative=int(counts.get("tentative") or 0),
                bench=int(counts.get("bench") or 0),
                absent=int(counts.get("absent") or 0),
                roster=_parse_roster(entry.get("roster"), counts.get("roles")),
                me=normalize_own_state(entry.get("me")),
            )
        )

    days.sort(
        key=lambda day: (
            day.starts_at is None,
            day.starts_at or datetime.max.replace(tzinfo=timezone.utc),
        )
    )

    return RaidSchedule(
        known=True,
        title=str(data.get("title") or "Raid"),
        raid_type=str(data.get("raid_type") or "standard"),
        signup_status=str(data.get("signup_status") or "open"),
        raid_size=int(data.get("raid_size") or 0),
        days=tuple(days),
        composition=_parse_composition(data.get("composition")),
        signup=_parse_signup(data.get("discord")),
        others=_parse_others(data.get("others")),
    )


def _parse_others(rows) -> tuple[RaidSchedule, ...]:
    """
    Die weiteren gleichzeitig laufenden Raids.

    **Warum das rekursiv über `parse_schedule()` läuft.** Ein Eintrag
    in `others` trägt dieselben Felder wie die Antwort selbst, nur
    ohne `status`. Ihn hier von Hand nachzubauen hieße, die Regeln aus
    `parse_schedule()` ein zweites Mal aufzuschreiben - und ab der
    ersten Änderung würde der zweite Raid anders gelesen als der
    erste, ohne dass es jemandem auffiele.

    Ein Eintrag ohne Termin fliegt nicht heraus: der Bot sortiert ihn
    ans Ende, weil sein Datum unlesbar ist - der Raid existiert
    trotzdem, und "es läuft noch etwas, dessen Termin ich nicht kenne"
    ist eine bessere Auskunft als Schweigen.
    """

    if not isinstance(rows, (list, tuple)):
        return ()

    weitere = []

    for row in rows:

        if not isinstance(row, dict):
            continue

        #
        # `others` wird beim verschachtelten Eintrag ausdrücklich
        # entfernt. Der Bot schickt es dort nicht, aber eine Antwort,
        # die sich selbst enthält, würde sonst so tief einlesen, wie
        # sie geschachtelt ist - eine Rekursion, deren Tiefe von
        # außen bestimmt wird.
        #

        eintrag = parse_schedule({**row, "status": "ok", "others": None})

        if eintrag.known:
            weitere.append(eintrag)

    return tuple(weitere)


def _parse_roster(rows, roles) -> tuple[RosterSlot, ...]:
    """
    Die Zusagen als Plätze - aus `days[].roster`, ersatzweise aus
    `days[].signups.roles`.

    Zwei Formen, weil der Bot die zweite deutlich billiger liefern
    kann: `roster` nennt je Zusage Rolle **und** Klasse (dann sind die
    Plätze in Klassenfarbe), `roles` nur die Zahlen je Rolle (dann
    sind sie in Akzentfarbe). Beides sagt dasselbe über die
    Zusammensetzung; nur das Bild wird ärmer.

    Ein Eintrag ohne erkennbare Rolle wird verworfen, statt unter
    "Schaden" zu landen - eine falsche Rolle ist schlechter als eine
    fehlende, weil sie sich nicht als Lücke zu erkennen gibt.
    """

    slots: list[RosterSlot] = []

    if isinstance(rows, (list, tuple)):

        for row in rows:

            if not isinstance(row, dict):
                continue

            role = normalize_role(row.get("role"))

            if not role:
                continue

            slots.append(
                RosterSlot(
                    role=role,
                    class_name=str(
                        row.get("class") or row.get("class_name") or ""
                    ).strip(),
                )
            )

    if slots:
        return tuple(slots)

    if not isinstance(roles, dict):
        return ()

    for key in ROLE_ORDER:

        count = 0

        for name, value in roles.items():

            if normalize_role(name) != key:
                continue

            try:
                count += int(value or 0)

            except (TypeError, ValueError):
                continue

        slots.extend(RosterSlot(role=key) for _ in range(max(0, count)))

    return tuple(slots)


def _parse_composition(data) -> dict:
    """
    Die Sollstärke je Rolle.

    Nur die drei bekannten Rollen und nur positive Zahlen: ein Soll
    von null ist keins, und eine unbekannte Rolle hätte im Streifen
    keinen Platz, an dem sie erscheinen könnte.
    """

    if not isinstance(data, dict):
        return {}

    target = {}

    for name, value in data.items():

        role = normalize_role(name)

        if not role:
            continue

        try:
            count = int(value or 0)

        except (TypeError, ValueError):
            continue

        if count > 0:
            target[role] = count

    return target


def _parse_signup(data) -> dict:
    """
    Der `discord`-Block: Gilde, Kanal, Nachricht der Anmeldung.

    Jede Kennung als **Zeichenkette** - eine Discord-Snowflake sprengt
    die Zahlengenauigkeit, und aus `1.23e+18` wird nie wieder ein
    Link. Ältere Bot-Fassungen schicken den Block nicht; dann bleibt er
    leer, statt aus Teilen etwas zusammenzusetzen, das wie eine Adresse
    aussieht.
    """

    if not isinstance(data, dict):
        return {}

    signup = {}

    for key in ("guild_id", "channel_id", "message_id"):

        value = str(data.get(key) or "").strip()

        if value:
            signup[key] = value

    return signup


def countdown_text(day: RaidDay | None, now: datetime | None = None) -> str:
    """
    Der Chip rechts oben in der Übersicht.

    Grobkörnig mit Absicht: Tage, dann Stunden, dann Minuten. Eine
    laufende Sekundenuhr auf einen Termin in vier Tagen wäre Bewegung
    ohne Aussage - und sie müsste jede Sekunde neu gezeichnet werden.
    """

    if day is None:
        return "KEIN TERMIN BEKANNT"

    minutes = day.minutes_until(now)

    if minutes is None:
        return "KEIN TERMIN BEKANNT"

    if minutes <= 0:

        if day.is_running(now):
            return "RAID LÄUFT"

        return "KEIN TERMIN BEKANNT"

    if minutes < 60:
        return f"IN {minutes} MIN"

    hours = minutes // 60

    if hours < 24:

        rest = minutes % 60

        if rest:
            return f"IN {hours} STD {rest} MIN"

        return f"IN {hours} STD"

    days = hours // 24

    rest_hours = hours % 24

    if rest_hours:
        return f"IN {days} T {rest_hours} STD"

    return f"IN {days} T"


def day_text(day: RaidDay | None) -> str:
    """
    "Mittwoch, 12.08. um 20:00" - die Zeile unter dem Titel.
    """

    if day is None or day.starts_at is None:
        return ""

    label = day.label or day.starts_at.strftime("%A")

    return (
        f"{label}, {day.starts_at.strftime('%d.%m.')} um "
        f"{day.starts_at.strftime('%H:%M')} Uhr"
    )


def signup_text(day: RaidDay | None, size: int = 0) -> str:
    """
    "18 von 25 zugesagt · 2 vielleicht · 1 Ersatzbank".

    Ohne Raidgröße ohne das "von 25" - der Bot kennt sie, aber eine
    ältere Fassung vielleicht nicht, und eine erfundene Obergrenze
    würde die Zusagen auf einmal knapp oder üppig aussehen lassen.
    """

    if day is None:
        return ""

    parts = [
        f"{day.active} von {size} zugesagt"
        if size
        else f"{day.active} zugesagt"
    ]

    if day.tentative:
        parts.append(f"{day.tentative} vielleicht")

    if day.bench:
        parts.append(f"{day.bench} Ersatzbank")

    return " · ".join(parts)


# --------------------------------------------------
# Die Aufstellung
# --------------------------------------------------


def count_text(day: RaidDay | None, size: int = 0) -> str:
    """
    Die Zahl rechts über den Streifen: "21 / 25 zugesagt".

    Ohne Raidgröße ohne das "/ 25", aus demselben Grund wie in
    `signup_text()`.
    """

    if day is None:
        return ""

    if size:
        return f"{day.active} / {size} zugesagt"

    return f"{day.active} zugesagt"


def open_slots(schedule: RaidSchedule | None, day: RaidDay | None):
    """
    Was noch fehlt: (offene Plätze, je Rolle offen, frei wählbar).

    Drei Zahlen, weil sie drei verschiedene Dinge wissen:

    - **offen** folgt allein aus Raidgröße minus Zusagen und ist
      deshalb schon bekannt, wenn von Rollen noch keine Rede ist.
    - **je Rolle** braucht beides, das gemeldete Soll und die
      gemeldete Zusammensetzung. Fehlt eines, bleibt die Angabe leer
      statt geschätzt.
    - **frei wählbar** ist der Rest. Er ist der ehrliche Teil der
      Auskunft: die Sollstärke sagt, wie viele Heiler gebraucht
      werden, nicht wie die letzten Plätze zu besetzen sind.

    Ohne bekannte Raidgröße ist alles davon `None`-artig, hier also
    `(0, {}, 0)` - die Oberfläche sagt dann gar nichts über offene
    Plätze, statt gegen eine erfundene Obergrenze zu rechnen.
    """

    if day is None or schedule is None:
        return 0, {}, 0

    size = int(getattr(schedule, "raid_size", 0) or 0)

    if size <= 0:
        return 0, {}, 0

    total = max(0, size - day.active)

    composition = getattr(schedule, "composition", None) or {}

    if not composition or not day.has_roles():
        return total, {}, total

    have = day.role_counts()

    missing = {}

    for role in ROLE_ORDER:

        target = int(composition.get(role) or 0)

        if target <= 0:
            continue

        gap = target - have.get(role, 0)

        if gap > 0:
            missing[role] = gap

    return total, missing, max(0, total - sum(missing.values()))


def number_word(count: int) -> str:
    """
    "Vier" statt "4" - bis zwölf, darüber die Ziffer.
    """

    return NUMBER_WORDS.get(count, str(count))


def composition_text(
    schedule: RaidSchedule | None,
    day: RaidDay | None,
) -> str:
    """
    Der Satz unter den Streifen.

    "Vier offene Plätze · 1 Tank, 1 Heiler, 2 frei wählbar" - oder,
    ohne gemeldetes Soll, nur der erste Teil. Ist der Raid voll, sagt
    er das; ohne bekannte Raidgröße sagt er nichts, weil er dann auch
    nichts weiß.
    """

    if day is None:
        return ""

    total, missing, free = open_slots(schedule, day)

    size = int(getattr(schedule, "raid_size", 0) or 0)

    if size <= 0:
        return ""

    parts = [
        f"{count} {ROLE_NAMES[role]}"
        for role, count in (
            (role, missing.get(role, 0)) for role in ROLE_ORDER
        )
        if count
    ]

    if total <= 0:

        #
        # Voll und trotzdem falsch besetzt: fünfundzwanzig Zusagen,
        # darunter kein zweiter Tank. "Vollständig" wäre hier die
        # bequeme Antwort und die einzige, die der Raidleiter nicht
        # gebrauchen kann - die Streifen daneben zeigen die Lücke ja.
        #

        if not parts:
            return "Die Aufstellung ist vollständig."

        return (
            f"Voll besetzt · {', '.join(parts)} "
            f"{'fehlt' if sum(missing.values()) == 1 else 'fehlen'} noch"
        )

    head = (
        "Ein offener Platz"
        if total == 1
        else f"{number_word(total)} offene Plätze"
    )

    if free and parts:
        parts.append(f"{free} frei wählbar")

    if not parts:
        return head

    return f"{head} · {', '.join(parts)}"


# --------------------------------------------------
# Die eigene Anmeldung
# --------------------------------------------------


def own_signup_label(day: RaidDay | None) -> str:
    """
    Die Beschriftung des Chips - "ANGEMELDET", "NICHT ANGEMELDET" …

    Leer, wenn der Bot nichts gemeldet hat. Der Aufrufer blendet den
    Chip dann aus: kein Chip heisst "dazu ist nichts bekannt", und das
    ist etwas anderes als jede der fünf Antworten.
    """

    if day is None:
        return ""

    return OWN_LABELS.get(day.me, "")


def own_signup_variant(day: RaidDay | None) -> str:
    """
    Die Farbe des Chips. `neutral`, solange nichts gemeldet ist - der
    Chip wird dann ohnehin nicht gezeigt.
    """

    if day is None:
        return "neutral"

    return OWN_VARIANTS.get(day.me, "neutral")


def own_signup_text(day: RaidDay | None) -> str:
    """
    Der ganze Satz: "Du bist für diesen Tag angemeldet." bzw. "Deine
    Anmeldung für diesen Tag fehlt noch."
    """

    if day is None:
        return ""

    return OWN_SENTENCES.get(day.me, "")


def others_text(
    schedule: RaidSchedule | None,
    now: datetime | None = None,
) -> str:
    """
    Die Zeile über die weiteren gleichzeitig laufenden Raids.

    "Außerdem offen: 25er Twinks (Donnerstag, 14.08. um 20:00 Uhr)" -
    leer, solange nur einer läuft.

    **Warum das überhaupt eine Zeile bekommt.** Die Übersicht hat
    genau einen Termin-Platz, und der bleibt beim nächsten Raid. Ohne
    diesen Hinweis wäre ein zweiter, parallel laufender Raid in der
    App schlicht unsichtbar - man sähe nicht, dass man sich noch
    woanders eintragen kann, und würde den Unterschied nie bemerken.
    Ein Raid ohne lesbaren Termin steht mit Namen da, ohne Datum: dass
    es ihn gibt, ist die Auskunft, das Datum kennt der Bot eben nicht.
    """

    if schedule is None or not getattr(schedule, "known", False):
        return ""

    teile = []

    for weiterer in schedule.others:

        tag = weiterer.next_day(now)

        beschriftung = day_text(tag)

        teile.append(
            f"{weiterer.title} ({beschriftung})"
            if beschriftung
            else weiterer.title
        )

    if not teile:
        return ""

    return "Außerdem offen: " + " · ".join(teile)
