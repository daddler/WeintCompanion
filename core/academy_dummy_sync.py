"""
Rotationstrainer-Sitzungen, wie sie das Addon zurückmeldet.

Bewusst ein eigenes Modul und nicht Teil von core/sync_manager.py: das
ist reines Parsen ohne Netzwerk, und der Test-Job der CI installiert
nur pytest, keine Projektabhängigkeiten. Läge die Funktion im
SyncManager, zöge schon der Import des Testmoduls über
discord/sync_client.py `requests` herein - und der komplette Testlauf
bräche beim Einsammeln ab (gleicher Grund wie bei
core/academy_progress_sync.py).

Format (siehe SendDummyPracticeSession in modules/companion.lua des
Addons), EIN Ereignis pro abgeschlossener Sitzung, kein Gesamtstand:

    <Charakter>|<specKey>|<Datum YYYYMMDD>|<durationSec>|<hits>|
    <compliantHits>|<compliancePercent>

specKey ist der interne Profilschlüssel des Addons aus
data/spec_profiles.lua (z.B. "WARRIOR_ARMS"), keine Lokalisierung -
SPEC_KEY_TO_LESSON_SLUG übersetzt ihn in das Lektions-ID-Präfix des
hiesigen Katalogs (z.B. "warrior-arms"). Ein nicht gefundener Key wird
geloggt und die Sitzung verworfen, statt den ganzen Sync-Lauf zu
gefährden - gleiche Philosophie wie in addon/sync_reader.py.

Eine Sitzung zählt nur als "gültiger Übungstag", wenn sie
MIN_SESSION_SECONDS Kampfzeit erreicht und ihre Note bei
MIN_COMPLIANCE_PERCENT liegt. Drei solche Tage IN FOLGE (Kalendertag
auf Kalendertag, keine Lücke) hakt die zugehörige Lektion automatisch
über AcademyService.set_completed() ab - dieselbe Persistenz wie beim
manuell gesetzten Häkchen, nur ein neuer Aufrufer.

Die Mindestdauer steht bewusst auf beiden Seiten: das Addon meldet
seit 1.3.2.0 gar nichts Kürzeres mehr (MIN_SESSION_SECONDS in
modules/rotationtrainer.lua), aber welche Addon-Version installiert
ist, entscheidet der Spieler - eine ältere schickt weiterhin
Dreißig-Sekunden-Sitzungen, und die dürfen die Tage-Serie nicht
tragen. Beide Zahlen müssen deshalb gleich bleiben.
"""

from __future__ import annotations

from datetime import datetime

MIN_SESSION_SECONDS = 180
MIN_COMPLIANCE_PERCENT = 80.0
STREAK_TARGET = 3

# WeintCodex-interner Spec-Schlüssel -> Lektions-ID-Präfix im hiesigen
# Katalog (analyzer/academy/lessons/classes/<klasse>.py). Absichtlich
# eine explizite Tabelle statt einer Normalisierung über Klassenname/
# Spec-Anzeigetext: vermeidet jede Lokalisierungs- oder Groß-/
# Kleinschreibungsfrage zwischen Client-Sprache und Katalog.
SPEC_KEY_TO_LESSON_SLUG = {
    "WARRIOR_ARMS": "warrior-arms",
    "WARRIOR_FURY": "warrior-fury",
    "PALADIN_RETRIBUTION": "paladin-retribution",
    "HUNTER_BEASTMASTERY": "hunter-beastmastery",
    "HUNTER_MARKSMANSHIP": "hunter-marksmanship",
    "HUNTER_SURVIVAL": "hunter-survival",
    "ROGUE_ASSASSINATION": "rogue-assassination",
    "ROGUE_COMBAT": "rogue-combat",
    "ROGUE_SUBTLETY": "rogue-subtlety",
    "PRIEST_SHADOW": "priest-shadow",
    "DEATHKNIGHT_FROST": "deathknight-frost",
    "DEATHKNIGHT_UNHOLY": "deathknight-unholy",
    "SHAMAN_ELEMENTAL": "shaman-elemental",
    "SHAMAN_ENHANCEMENT": "shaman-enhancement",
    "MAGE_ARCANE": "mage-arcane",
    "MAGE_FIRE": "mage-fire",
    "MAGE_FROST": "mage-frost",
    "WARLOCK_AFFLICTION": "warlock-affliction",
    "WARLOCK_DEMONOLOGY": "warlock-demonology",
    "WARLOCK_DESTRUCTION": "warlock-destruction",
    "MONK_WINDWALKER": "monk-windwalker",
    "DRUID_BALANCE": "druid-balance",
    "DRUID_FERAL": "druid-feral",
}


def _parse_date(date_str: str):

    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def parse_dummy_practice_session(payload: str) -> dict | None:
    """
    Eine einzelne Sitzung aus der Pipe-Zeichenkette, oder None bei
    einem unvollständigen/kaputten Eintrag (z. B. durch einen Lese-
    Zugriff mitten in einem Schreibvorgang von WoWs Lua-VM).
    """

    parts = (payload or "").split("|")

    if len(parts) != 7:
        return None

    character, spec_key, date_str, duration, hits, compliant, compliance = (
        part.strip() for part in parts
    )

    if not character or not spec_key:
        return None

    try:

        return {
            "character": character,
            "spec_key": spec_key,
            "date": date_str,
            "duration": int(duration),
            "hits": int(hits),
            "compliant": int(compliant),
            "compliance": float(compliance),
        }

    except ValueError:
        return None


def apply_dummy_practice_session(academy, payload: str) -> bool:
    """
    Übernimmt eine gemeldete Sitzung in den AcademyService und
    speichert, wenn sich etwas geändert hat. Gibt zurück, ob
    gespeichert wurde.
    """

    if academy is None:
        return False

    session = parse_dummy_practice_session(payload)

    if session is None:
        return False

    #
    # Zu kurz ist kein Übungstag: unter drei Minuten am Stück sagt eine
    # Sitzung nichts über die Rotation aus. Neuere Addon-Versionen
    # melden solche Sitzungen gar nicht erst, ältere schon.
    #

    if session["duration"] < MIN_SESSION_SECONDS:
        return False

    if session["compliance"] < MIN_COMPLIANCE_PERCENT:
        return False

    day = _parse_date(session["date"])

    if day is None:
        return False

    spec_key = session["spec_key"]
    lesson_slug = SPEC_KEY_TO_LESSON_SLUG.get(spec_key)

    if lesson_slug is None:

        academy.manager.logger.warning(
            f"Rotationstrainer: unbekannter Spec-Schlüssel "
            f"'{spec_key}' - Sitzung wird ignoriert."
        )

        return False

    character = session["character"]

    #
    # Über den Service: welcher Charakter gemeint ist, entscheidet
    # dort `_key_for()`. Der Trainer meldet den nackten Clientnamen
    # ("Aldrin"), die Auswertung läuft unter der Schreibweise des
    # Berichts ("Aldrin-DieAldor") - roh weggeschrieben landete die
    # Serie unter einem Namen, unter dem später niemand mehr sucht,
    # und das Abhaken nach drei Tagen war lautlos verloren.
    #

    per_character = academy.practice_store(character)

    record = dict(per_character.get(spec_key) or {"lastDate": "", "streak": 0})
    last_day = _parse_date(record.get("lastDate", ""))

    #
    # Bereits für heute gezählt, oder eine verspätet zugestellte,
    # ältere Sitzung - beides verändert die Serie nicht.
    #

    if last_day is not None and day <= last_day:
        return False

    if last_day is not None and (day - last_day).days == 1:
        record["streak"] = int(record.get("streak", 0)) + 1
    else:
        record["streak"] = 1

    record["lastDate"] = session["date"]
    per_character[spec_key] = record

    academy.save()

    if record["streak"] >= STREAK_TARGET:

        lesson_id = f"{lesson_slug}.rotation.dummy_practice"

        academy.set_completed(character, lesson_id, True)

    return True


# --------------------------------------------------
# Was die Serie heute wert ist
# --------------------------------------------------
#
# **Die Serie wurde gespeichert und nirgends gezeigt.** Wer zwei Tage
# hintereinander an der Puppe stand, sah davon weder im Spiel noch auf
# dem Desktop etwas - erst am dritten Tag erschien wortlos ein Haken im
# Trainingsplan. Genau der Kreis, für den es den Rotationshelfer gibt
# (die Academy nennt die Schwäche, der Helfer übt sie, die Lektion hakt
# ab), war an seiner sichtbarsten Stelle unsichtbar.
#
# Beantwortet wird das hier und nur hier, weil hier auch entschieden
# wird, was eine Serie fortsetzt: eine zweite Rechnung in der
# Oberfläche oder im Addon liefe irgendwann anders aus als die, die
# tatsächlich abhakt.
#


def streak_state(record, day: str = "") -> dict:
    """
    Der heutige Stand einer gespeicherten Serie.

    `record` ist ein Eintrag aus `AcademyService.practice_for()`,
    `day` der Kalendertag als "YYYYMMDD" (leer = heute).

    **Eine gespeicherte Zahl ist noch keine laufende Serie.** Zählt
    wird nur weiter, wenn die letzte Sitzung von heute oder gestern
    ist - dieselbe Regel, nach der `apply_dummy_practice_session()`
    fortschreibt bzw. zurücksetzt. Eine drei Wochen alte Zwei als
    "Tag 2 von 3" auszugeben, wäre ein Versprechen, das die nächste
    Sitzung bricht.

    `done` sagt, dass die Serie ihr Ziel erreicht hat - nicht, dass die
    Lektion abgehakt ist. Der Haken liegt in `completed` und bleibt
    dort auch dann, wenn die Serie später abreißt.
    """

    today_day = _parse_date(day) if day else datetime.now().date()

    last = _parse_date(str((record or {}).get("lastDate", "")))

    streak = int((record or {}).get("streak", 0) or 0)

    if last is None or streak <= 0 or today_day is None:

        return {
            "streak": 0,
            "target": STREAK_TARGET,
            "missing": STREAK_TARGET,
            "alive": False,
            "practicedToday": False,
            "done": False,
            "lastDate": "",
        }

    abstand = (today_day - last).days

    alive = abstand in (0, 1)

    laufend = streak if alive else 0

    return {
        "streak": laufend,
        "target": STREAK_TARGET,
        "missing": max(STREAK_TARGET - laufend, 0),
        "alive": alive,
        "practicedToday": abstand == 0,
        "done": laufend >= STREAK_TARGET,
        "lastDate": str(record.get("lastDate", "")),
    }


def practice_text(state) -> str:
    """
    Der Satz zur Serie - leer, wenn noch nie geübt wurde.

    Vier Lagen, vier Sätze: sie verlangen Verschiedenes, und ein
    gemeinsamer wäre für drei davon falsch.
    """

    if not state or not state.get("lastDate"):
        return ""

    ziel = int(state.get("target", STREAK_TARGET))

    if state.get("done"):

        return (
            f"{ziel} Übungstage in Folge geschafft - "
            f"die Lektion ist abgehakt."
        )

    if not state.get("alive"):

        return (
            "Die Übungsserie ist abgerissen. Die nächste Sitzung an "
            "der Puppe beginnt wieder bei Tag 1."
        )

    tag = int(state.get("streak", 0))

    if state.get("practicedToday"):

        fehlt = int(state.get("missing", 0))

        return (
            f"Heute geübt - Tag {tag} von {ziel}. Noch "
            + (f"{fehlt} Tage" if fehlt != 1 else "ein Tag")
            + " in Folge."
        )

    return (
        f"Tag {tag} von {ziel} geschafft. Heute noch eine Sitzung, "
        f"sonst beginnt die Serie morgen von vorn."
    )


def practice_payload(academy, character: str) -> list[dict]:
    """
    Die Übungsserien eines Charakters, so wie das Addon sie liest.

    Geschickt wird der **Spec-Schlüssel des Addons** und nicht unser
    Lektions-Slug als Ordnung: welche Spezialisierung gerade gespielt
    wird, weiss nur das Addon - und es weiss es genauer als jede
    Zustellung, die beim letzten Login entstanden ist. Die Lektions-ID
    steht daneben, damit die Zeile im Trainingsplan an der richtigen
    Karte landet.

    Der Satz kommt fertig mit: `practice_text()` ist die eine Stelle,
    an der die Serie in Worte gefasst wird, und Desktop wie Spiel
    lesen daraus - sonst stünde im Spiel "Tag 2 von 3", während der
    Desktop die Serie längst für abgerissen hält.
    """

    if academy is None or not character:
        return []

    entries = []

    for spec_key, record in sorted(
        (academy.practice_for(character) or {}).items()
    ):

        state = streak_state(record)

        slug = SPEC_KEY_TO_LESSON_SLUG.get(spec_key)

        entries.append({
            "specKey": spec_key,
            "lessonId": (
                f"{slug}.rotation.dummy_practice" if slug else ""
            ),
            "streak": state["streak"],
            "target": state["target"],
            "missing": state["missing"],
            "alive": state["alive"],
            "practicedToday": state["practicedToday"],
            "done": state["done"],
            "lastDate": state["lastDate"],
            "text": practice_text(state),
        })

    return entries


def practice_for_lessons(entries, lesson_ids) -> dict | None:
    """
    Die Serie, die zu einem Lektionskatalog gehört - oder None.

    Zugeordnet wird über die **Lektions-ID** und nicht über die
    Spezialisierung: der Katalog eines Charakters ist ohnehin
    spec-genau, und eine zweite Übersetzung Spec -> Slug wäre eine
    zweite Tabelle, die von der bestehenden abweichen kann.
    """

    ids = {entry for entry in (lesson_ids or ()) if entry}

    for entry in entries or ():

        if entry.get("lessonId") and entry["lessonId"] in ids:
            return entry

    return None
