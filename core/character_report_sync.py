"""
Wer spielt gerade? - die Meldung des Addons.

Bis WeintCodex 1.3.2.3 erfuhr die Companion **nie**, welcher Charakter
im Spiel angemeldet ist. Die einzige Charakter-Meldung war die
komplette Twinkliste (`"character"`), die an den Discord-Bot
weitergereicht wird und keinerlei Kennzeichnung trägt, wer davon
gerade spielt. Die Frage "wer bin ich" musste die App deshalb aus
einer WarcraftLogs-Namensliste raten - im Zweifel wurde der
alphabetisch erste Raider genommen. Daher stammte der Fehler, dass in
Academy und WeintTV ein völlig fremder Charakter stand.

Seit WeintCodex 1.3.3.0 gibt es dafür `"character_report"`. Die
Nachricht wird hier lokal verarbeitet und **nie an den Bot
geschickt** - genau wie `"academy"` und `"dummy_practice_session"`.
Das Modul importiert deshalb kein `httpx`: es soll ohne die
Netzwerkschicht testbar bleiben.

Format (die Ausgangsrichtung kann `addon/sync_reader.py` nur als
Zeichenkette lesen, deshalb flach und positionsbasiert):

    <Name>|<Realm>|<classFile>|<Level>|<specKey>

**Zwei bis fünf Felder werden angenommen, weitere ignoriert.** Das
Addon darf das Format also erweitern, ohne eine ältere Companion zu
brechen - und eine ältere Addon-Version, die nur Name und Realm
schickt, funktioniert hier weiter. Für die Charakterauswahl zählen
ohnehin nur die ersten beiden Felder.
"""

from __future__ import annotations


def parse_character_report(payload: str) -> dict | None:
    """
    Zerlegt die Nutzlast. `None` heißt "unbrauchbar" - ohne Namen ist
    die Meldung wertlos.
    """

    if not isinstance(payload, str):
        return None

    fields = payload.split("|")

    name = fields[0].strip() if fields else ""

    if not name:
        return None

    def field(index: int) -> str:

        if index >= len(fields):
            return ""

        return fields[index].strip()

    level = 0

    try:
        level = int(field(3) or 0)

    except ValueError:
        #
        # Ein unlesbares Level darf die ganze Meldung nicht
        # verwerfen: der Name ist das Einzige, worauf es ankommt.
        #
        level = 0

    return {
        "name": name,
        "realm": field(1),
        "class": field(2),
        "level": level,
        "spec": field(4),
    }


def apply_character_report(academy, payload: str) -> dict | None:
    """
    Die Meldung an den `AcademyService` weiterreichen.

    Gibt die zerlegte Meldung zurück, damit der Aufrufer sie
    protokollieren kann, oder `None`, wenn nichts anzuwenden war.
    """

    report = parse_character_report(payload)

    if report is None or academy is None:
        return None

    academy.note_ingame_character(
        report["name"],
        report["realm"],
    )

    return report
