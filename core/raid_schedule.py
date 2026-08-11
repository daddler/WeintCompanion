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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


#
# Ab wann ein Termin als "läuft gerade" gilt statt als "in ... " -
# derselbe Gedanke wie `RUNNING_HOURS` im Bot, nur von der anderen
# Seite: dort entscheidet er, welcher Termin geliefert wird, hier, wie
# er beschriftet wird.
#

RUNNING_MINUTES = 4 * 60


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

    detail: str = ""

    #
    # Wo die Anmeldung im Discord steht (Gilde, Kanal, Nachricht), so
    # wie der Bot sie meldet. Damit springt der Knopf "Aufstellung im
    # Discord" in den Anmelde-Beitrag statt auf den Standardkanal des
    # Servers. Leer, solange der Bot den Block nicht schickt - die
    # Companion hat dafür ihren eigenen Rückfall.
    #

    signup: dict = field(default_factory=dict)

    # --------------------------------------------------

    def next_day(self, now: datetime | None = None) -> RaidDay | None:
        """
        Der nächste Termin: der erste, der noch nicht vorbei ist.

        Ein laufender Raid gilt als der nächste - deshalb wird gegen
        `is_running()` und nicht gegen "liegt in der Zukunft" geprüft.
        """

        upcoming = None

        for day in self.days:

            minutes = day.minutes_until(now)

            if minutes is None:
                continue

            if minutes > 0 or day.is_running(now):

                if upcoming is None or (
                    day.starts_at < upcoming.starts_at
                ):
                    upcoming = day

        return upcoming


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
        signup=_parse_signup(data.get("discord")),
    )


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
