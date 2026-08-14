"""
Die Begrüßung auf der Übersicht - Tageszeit, Name, nächster Raid.

**Warum es diese Datei gibt.** Der Kopf der Übersicht trug bis 2.0.7
zwei feste Zeichenketten: die Rubrik "HEUTE" und darunter einen von
drei Sätzen, die allesamt den Zustand der *Installation* meldeten
("Alles bereit für den nächsten Raid.", "Für das Addon liegt eine neue
Version bereit.", "World of Warcraft wurde noch nicht gefunden.").
Das ist genau der Fehler, den die Übersicht 2.0 beim alten Dashboard
behoben hat, nur eine Etage höher: die Stelle, die man bei jedem Start
zuerst liest, sagt etwas, das man schon weiß - und sie sagt es jedem
Nutzer zu jeder Tageszeit gleich.

Hier wird daraus eine Anrede und eine Auskunft: **Tageszeit und Name**
in der Rubrik, **der nächste Raid** im Satz darunter. Der Countdown-Chip
rechts nennt die Restzeit auf die Minute genau; was er nicht sagt, ist,
ob das "in 2 T 5 STD" nun ein Grund ist, heute noch etwas vorzubereiten.
"Übermorgen um 20:00 Uhr ist Raid." sagt es.

Ohne Qt und ohne `httpx`, aus demselben Grund wie
`core/raid_schedule.py`, `access_roles.build_profile_payload()` und
`backend_config.roster_target()`: die Entscheidung, *welcher* Satz
dasteht, ist die Stelle, an der etwas falsch sein kann, und sie soll
ohne Fenster prüfbar bleiben.

Drei Regeln, dieselben wie überall in diesem Projekt:

- **Ohne Termin kein Termin.** Kennt die App keinen Raid, bleibt es
  bei dem Satz, der schon immer dastand. Ein "Bald ist wieder Raid"
  ohne Datum wäre eine Behauptung über den Kalender.
- **Gezählt werden Kalendertage, nicht 24-Stunden-Blöcke.** "Morgen"
  heißt der nächste Tag im Kalender. Um 23:00 Uhr ist ein Raid am
  Folgetag um 20:00 Uhr *morgen* - er liegt aber nur 21 Stunden
  entfernt, und eine Rechnung in Blöcken hätte daraus "heute" gemacht.
- **Ein Name wird nicht geraten.** Ist keiner bekannt, grüßt die App
  ohne Namen. Die Anrede mit dem erstbesten Raider aus einem
  Bericht wäre dieselbe Sorte Fehler wie das geratene "ich" in der
  Academy (siehe `analyzer/names.py`).
"""

from __future__ import annotations

from datetime import datetime

from core.raid_schedule import number_word


#
# --------------------------------------------------
# Tageszeiten
# --------------------------------------------------
#
# Die Grenzen sind die des deutschen Sprachgebrauchs und nicht die der
# Uhr: der Morgen endet, wenn man niemanden mehr mit "Guten Morgen"
# grüßen würde, und die Nacht beginnt, wenn "Guten Abend" befremdlich
# klänge. Wer um 2 Uhr nachts noch am Rechner sitzt, bekommt "Gute
# Nacht" - das ist die einzige Tageszeit, die auch etwas über den
# Nutzer sagt.
#

MORNING_HOUR = 5

DAY_HOUR = 11

EVENING_HOUR = 18

NIGHT_HOUR = 23

DAYPARTS = (
    (MORNING_HOUR, "Guten Morgen"),
    (DAY_HOUR, "Guten Tag"),
    (EVENING_HOUR, "Guten Abend"),
    (NIGHT_HOUR, "Gute Nacht"),
)

#
# Wie ein Tag heißt, der 0, 1 oder 2 Kalendertage entfernt ist. Weiter
# reicht das Deutsche nicht - ab drei Tagen wird gezählt.
#

DAY_WORDS = {
    0: "Heute",
    1: "Morgen",
    2: "Übermorgen",
}

#
# Ab wann ein Termin zu weit weg ist, um im Kopf der Übersicht
# erwähnt zu werden. Eine Woche vorher ist "noch sieben Tage" keine
# Auskunft mehr, sondern ein Hinweis darauf, dass gerade kein Raid
# ansteht - und den gibt der Satz "Alles bereit für den nächsten Raid."
# freundlicher.
#

MENTION_DAYS = 6


def _local(moment: datetime | None) -> datetime | None:
    """
    Ein Zeitpunkt in der Zeitzone dieses Rechners.

    Ein naiver Zeitpunkt gilt als lokale Zeit - das ist dieselbe
    Annahme wie in `raid_schedule._parse_moment()` und die einzige,
    die nicht schlechter ist als der Verzicht auf die Angabe.
    """

    if moment is None:
        return None

    return moment.astimezone()


def _now(now: datetime | None = None) -> datetime:

    return _local(now) or datetime.now().astimezone()


def daypart(now: datetime | None = None) -> str:
    """
    "Guten Morgen", "Guten Tag", "Guten Abend" oder "Gute Nacht".
    """

    hour = _now(now).hour

    if hour < MORNING_HOUR or hour >= NIGHT_HOUR:
        return "Gute Nacht"

    text = "Guten Morgen"

    for start, word in DAYPARTS:

        if hour >= start:
            text = word

    return text


def greeting(name: str = "", now: datetime | None = None) -> str:
    """
    Die Rubrik über dem Titel: "Guten Abend, Krallenwut".

    Ohne bekannten Namen nur die Tageszeit. Ein Komma ohne Anrede
    dahinter sähe aus wie ein abgeschnittener Text.
    """

    text = daypart(now)

    name = str(name or "").strip()

    return f"{text}, {name}" if name else text


# --------------------------------------------------
# Der nächste Raid
# --------------------------------------------------


def days_until(day, now: datetime | None = None) -> int | None:
    """
    Kalendertage bis zum Termin - 0 heißt "heute".

    Bewusst über die Datumsgrenze und nicht über die Restzeit: um
    23:00 Uhr ist ein Raid am Folgetag um 20:00 Uhr *morgen*, obwohl
    nur 21 Stunden dazwischen liegen. Genau so steht es auch im
    Kalender, in den der Nutzer sonst sehen würde.
    """

    starts_at = _local(getattr(day, "starts_at", None))

    if starts_at is None:
        return None

    return (starts_at.date() - _now(now).date()).days


def time_text(day) -> str:
    """
    "20:00" - die Uhrzeit des Termins, in lokaler Zeit.
    """

    starts_at = _local(getattr(day, "starts_at", None))

    if starts_at is None:
        return ""

    return starts_at.strftime("%H:%M")


def raid_phrase(day, now: datetime | None = None, clock: bool = True) -> str:
    """
    Der halbe Satz über den nächsten Raid - **ohne Punkt**, damit der
    Aufrufer ihn fortsetzen kann.

    Leer heißt "dazu ist nichts zu sagen": kein Termin bekannt, der
    Termin liegt hinter uns, oder er ist mehr als eine Woche entfernt.
    Leer ist hier kein Fehlerfall, sondern die Voreinstellung - der
    Aufrufer setzt dann seinen eigenen Satz.

    `clock=False` lässt die Uhrzeit weg. Das ist keine Verschönerung,
    sondern eine Platzfrage: der Titel im Kopf ist 28 px groß, steht
    auf **einer** Zeile und wird bei 960 px Fensterbreite abgeschnitten
    statt umgebrochen. Hängt hinter dem Termin noch ein Halbsatz über
    ein wartendes Update, muss vorne etwas weichen - und die Uhrzeit
    steht ohnehin einen Blick tiefer auf der Aufstellungskarte.
    """

    if day is None:
        return ""

    is_running = getattr(day, "is_running", None)

    if callable(is_running) and is_running(now):
        return "Der Raid läuft gerade"

    minutes = getattr(day, "minutes_until", None)

    if callable(minutes) and (minutes(now) or 0) <= 0:

        #
        # Vorbei und nicht laufend: dazu sagt der Kopf nichts. Der
        # Termin ist Geschichte, und der nächste ist unbekannt -
        # sonst stünde er hier statt dieses einen.
        #

        return ""

    days = days_until(day, now)

    if days is None or days < 0:
        return ""

    if days <= 2:

        word = DAY_WORDS[days]

        moment = time_text(day) if clock else ""

        if moment:
            return f"{word} um {moment} Uhr ist Raid"

        return f"{word} ist Raid"

    if days <= MENTION_DAYS:

        return f"Noch {number_word(days).lower()} Tage bis zum nächsten Raid"

    return ""


# --------------------------------------------------
# Der Satz im Kopf
# --------------------------------------------------


def update_sentence(addon_update: bool, app_update: bool) -> str:
    """
    Welche Fassung wartet - Addon, App oder beide.

    Beim Namen der Komponente und nicht bei "ein Update": die beiden
    Kanäle sind voneinander unabhängig (siehe die Notiz zum Abzeichen
    in der Navigation), und "es gibt ein Update" ließe offen, welches
    der beiden gemeint ist.
    """

    if addon_update and app_update:
        return "Für Addon und App gibt es neue Versionen."

    if addon_update:
        return "Für das Addon liegt eine neue Version bereit."

    if app_update:
        return "Für die App liegt eine neue Version bereit."

    return ""


def headline(
    day=None,
    *,
    addon_update: bool = False,
    app_update: bool = False,
    wow_found: bool = True,
    now: datetime | None = None,
) -> str:
    """
    Der Titel im Kopf der Übersicht.

    Die Reihenfolge ist eine Aussage darüber, was den Abend
    entscheidet:

    1. **Kein WoW gefunden.** Solange das so ist, kann die App gar
       nichts - das steht vor allem anderen.
    2. **Der Raid.** Er ist der Grund, warum diese Anwendung offen
       ist. Wartet nebenbei ein Update **und ist der Termin höchstens
       übermorgen**, hängt es als Halbsatz hinten dran, statt den
       Termin zu verdrängen - dann weicht dafür die Uhrzeit, damit die
       Zeile auf dem schmalsten Fenster nicht abgeschnitten wird. Bei
       einem Termin in fünf Tagen bleibt das Update draußen: die
       Update-Karte steht unmittelbar darunter, nennt beide Kanäle
       beim Namen und trägt den Knopf dazu.
    3. **Ein wartendes Update**, wenn vom Raid nichts zu sagen ist.
    4. Sonst der Satz, der schon immer dastand.
    """

    if not wow_found:
        return "World of Warcraft wurde noch nicht gefunden."

    count = int(bool(addon_update)) + int(bool(app_update))

    days = days_until(day, now)

    near = days is not None and 0 <= days <= 2

    phrase = raid_phrase(day, now, clock=not (count and near))

    if phrase:

        if count and near:

            return (
                f"{phrase} - "
                f"{'zwei Updates warten' if count == 2 else 'ein Update wartet'}."
            )

        return f"{phrase}."

    return (
        update_sentence(addon_update, app_update)
        or "Alles bereit für den nächsten Raid."
    )
