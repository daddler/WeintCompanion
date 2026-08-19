"""
Die Charakterliste der Anwendung.

Das Addon meldet immer nur **einen** Charakter: den gerade
angemeldeten (`"character_sheet"`, siehe
`core/character_sheet_sync.py`). Die Liste über mehrere Twinks
entsteht deshalb hier - sie ist die einzige Stelle, an der die
Meldungen mehrerer Anmeldungen zusammenkommen.

Das ist kein Zwischenspeicher, sondern die Datenquelle zweier Seiten,
und sie liegt entsprechend in `Paths.config()`: Wer seit zwei Wochen
nicht auf dem Zweitcharakter war, soll ihn in "Meine Charaktere"
trotzdem sehen. In `Paths.cache()` wäre er beim ersten Aufräumen weg,
und die Seite behauptete, es gäbe ihn nicht.

Zwei Regeln, die nicht nach Geschmack sind:

* **Eine neue Meldung ersetzt den Eintrag, sie ergänzt ihn nicht.**
  Ein Feld, das die neue Meldung nicht mehr trägt, ist keine
  Erinnerung wert: es beschriebe einen Zustand, den es nicht mehr
  gibt. Wer eine Verzauberung entfernt, soll sie nicht deshalb weiter
  als vorhanden angezeigt bekommen, weil die vorige Meldung sie noch
  kannte.
* **Nur der Zeitstempel entscheidet über die Reihenfolge**, nicht die
  Reihenfolge der Verarbeitung. Sonst hinge "zuletzt gespielt" daran,
  wann die App lief.
* **Gezeigt werden nur Charaktere auf hoher Stufe**, siehe
  `MIN_LEVEL` weiter unten. Twinks bleiben gespeichert - sie werden
  nur nicht ausgegeben, und `all_characters()` liefert sie weiterhin.
  Wegwerfen wäre das Falsche: wer einen Twink hochspielt, soll ihn am
  Tag der Höchststufe mit seiner Vorgeschichte wiederfinden und nicht
  als Neuzugang.
"""

from __future__ import annotations

import json
import os
import time

from core.character_sheet_sync import (
    parse_character_sheet,
    readiness,
    sheet_key,
)
from core.paths import Paths


CHARACTERS_FILE = "characters.json"


#
# Ab welcher Stufe ein Charakter in "Meine Charaktere" und
# "Vorbereitung" auftaucht.
#
# Beide Seiten beantworten dieselbe Frage - "kann ich damit in den
# Raid" -, und die stellt sich nur für Charaktere, die mitkommen
# können. Bis 2.3.0 bekam jede Anmeldung eine Karte: wer nebenher
# vier Twinks hochspielt, fand die eine Höchststufe, um die es geht,
# zwischen vier Zeilen, die nichts mit dem nächsten Raidabend zu tun
# haben.
#
# MoP Classic endet bei 90, "hohe Stufe" heißt hier deshalb
# Höchststufe. `characters_min_level` in der Konfiguration setzt den
# Wert herunter, wer seine 85er mitzählen will - dieselbe Überlegung
# wie bei `access_role_map`: eine Zahl, die sich mit dem Spiel ändert,
# soll ohne ein Release änderbar bleiben.
#

MAX_LEVEL = 90

MIN_LEVEL = MAX_LEVEL


def is_high_level(sheet: dict, minimum: int = MIN_LEVEL) -> bool:
    """
    **Eine fehlende Stufe zählt als hohe.**

    Die 0 steht hier für "nicht gemeldet" und nicht für "Stufe 0" -
    eine ältere Addon-Version, ein abgeschnittenes Feld, ein Eintrag
    aus einer Zeit vor diesem Feld. Wer sie als Twink läse, ließe
    einen Charakter verschwinden, über den nichts bekannt ist; das ist
    dieselbe Linie wie `stars == 0` und `readiness() is None`: aus
    einer Datenlücke wird kein Befund.
    """

    try:
        level = int(sheet.get("level") or 0)

    except (TypeError, ValueError):
        return True

    if level <= 0:
        return True

    return level >= minimum


class CharacterStore:

    def __init__(self, manager):

        self.manager = manager

        self.file = Paths.config() / CHARACTERS_FILE

        #
        # Aufbau: {"<Name-Realm>": <Sheet>, ...}
        #
        # Der Schlüssel trägt den Realm, weil zwei Realms denselben
        # Namen führen dürfen - ohne ihn überschriebe der eine
        # Charakter die Ausrüstung des anderen.
        #

        self.data: dict = {}

        self.load()

    # --------------------------------------------------
    # Persistenz
    # --------------------------------------------------

    def load(self):

        if not self.file.exists():
            return

        try:

            with open(self.file, "r", encoding="utf-8") as handle:

                loaded = json.load(handle)

            if isinstance(loaded, dict):

                self.data = {
                    str(key): value
                    for key, value in loaded.items()
                    if isinstance(value, dict) and value.get("name")
                }

        except Exception as exc:

            #
            # Eine defekte Liste darf die Anwendung nicht aufhalten -
            # sie füllt sich bei der nächsten Anmeldung im Spiel von
            # selbst wieder.
            #

            self.manager.logger.warning(
                f"Charakterliste konnte nicht gelesen werden ({exc}) - "
                f"sie wird beim nächsten Anmelden im Spiel neu "
                f"aufgebaut."
            )

            self.data = {}

    def save(self):
        """
        Atomar schreiben - dasselbe Vorgehen wie in `core/config.py`
        und `core/academy_service.py`, damit ein Absturz mitten im
        Schreiben keine halbe Datei hinterlässt.
        """

        try:

            self.file.parent.mkdir(parents=True, exist_ok=True)

            tmp_path = self.file.with_suffix(self.file.suffix + ".tmp")

            with open(tmp_path, "w", encoding="utf-8") as handle:

                json.dump(
                    self.data,
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

            os.replace(tmp_path, self.file)

        except OSError as exc:

            self.manager.logger.error(
                f"Charakterliste konnte nicht gespeichert werden: {exc}"
            )

    # --------------------------------------------------
    # Aufnehmen
    # --------------------------------------------------

    def apply(self, payload: str) -> dict | None:
        """
        Eine `character_sheet`-Nutzlast aufnehmen. Gibt den zerlegten
        Eintrag zurück, damit der Aufrufer ihn protokollieren kann,
        oder `None`, wenn nichts anzuwenden war.
        """

        sheet = parse_character_sheet(payload)

        if sheet is None:
            return None

        key = sheet_key(sheet["name"], sheet["realm"])

        if not key:
            return None

        #
        # Ein Addon ohne verlässliche Uhr (oder ein Format, das das
        # Feld noch nicht trägt) bekommt den Empfangszeitpunkt. Ohne
        # Zeitstempel wäre die Sortierung "zuletzt gespielt" beliebig.
        #

        if not sheet.get("updated"):
            sheet["updated"] = int(time.time())

        self.data[key] = sheet

        self.save()

        return sheet

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def min_level(self) -> int:
        """
        Die eingestellte Mindeststufe. Ein unbrauchbarer Wert wird
        **ignoriert und nicht übernommen** - eine 0 in der
        Konfiguration hiesse sonst "alles anzeigen", und eine 200
        "nichts anzeigen"; beides sieht aus wie eine kaputte Seite.
        """

        config = getattr(self.manager, "config", None)

        value = (
            config.data.get("characters_min_level")
            if config is not None
            else None
        )

        try:
            minimum = int(value)

        except (TypeError, ValueError):
            return MIN_LEVEL

        if minimum < 1:
            return MIN_LEVEL

        return minimum

    def all_characters(self) -> list[dict]:
        """
        Alle bekannten Charaktere, zuletzt gespielter zuerst -
        einschliesslich der Twinks.
        """

        return sorted(
            self.data.values(),
            key=lambda sheet: sheet.get("updated", 0),
            reverse=True,
        )

    def characters(self) -> list[dict]:
        """
        Die Charaktere, die die Seiten zeigen: hohe Stufe, zuletzt
        gespielter zuerst.
        """

        minimum = self.min_level()

        return [
            sheet
            for sheet in self.all_characters()
            if is_high_level(sheet, minimum)
        ]

    def hidden(self) -> list[dict]:
        """
        Die ausgeblendeten Twinks.

        Sie werden gebraucht, um das Ausblenden **zu benennen**: ein
        Charakter, der aus einer Liste verschwindet, in der er gestern
        noch stand, ist sonst nicht von einem Fehler zu unterscheiden.
        """

        minimum = self.min_level()

        return [
            sheet
            for sheet in self.all_characters()
            if not is_high_level(sheet, minimum)
        ]

    def get(self, name: str, realm: str = "") -> dict | None:

        key = sheet_key(name, realm)

        if key in self.data:
            return self.data[key]

        #
        # Ohne Realm gesucht: der blanke Name darf den qualifizierten
        # Eintrag finden. Der Client kennt nur den nackten Namen -
        # dieselbe Regel wie in `analyzer/names.py`, wo ein fehlender
        # Realm ein Platzhalter ist und kein Widerspruch.
        #

        if not realm:

            bare = (name or "").strip().lower()

            #
            # Über `all_characters()`, nicht über `characters()`: die
            # Ausblendung gilt der Anzeige. Ein Twink, der gerade eine
            # Ausrüstung meldet, muss auch gefunden werden - sonst
            # legte `apply()` bei jeder Anmeldung einen zweiten
            # Eintrag an.
            #

            for sheet in self.all_characters():

                if sheet.get("name", "").strip().lower() == bare:
                    return sheet

        return None

    def remove(self, name: str, realm: str = "") -> bool:

        key = sheet_key(name, realm)

        if key not in self.data:

            found = self.get(name, realm)

            if found is None:
                return False

            key = sheet_key(found.get("name", ""), found.get("realm", ""))

        if key not in self.data:
            return False

        del self.data[key]

        self.save()

        return True

    # --------------------------------------------------
    # Zusammenfassung für die Übersicht
    # --------------------------------------------------

    def preparation_summary(self) -> dict:
        """
        Der Stand der Vorbereitung über alle gemeldeten Charaktere.

        `ratio` ist `None`, solange kein einziger Charakter geprüfte
        Verzauberungen oder Sockel gemeldet hat. Eine Null stünde dort
        für "alles offen" und wäre eine Messung, die es nicht gab -
        dieselbe Trennung wie `stars == 0` im Analyzer.

        Gezählt wird über `characters()`, also **ohne die Twinks**:
        die Kachel auf der Übersicht und die Seite "Vorbereitung"
        lesen dieselbe Zusammenfassung und dürfen sich nicht darin
        unterscheiden, wen sie meinen. Eine fehlende Verzauberung auf
        einem Charakter der Stufe 34 ist ausserdem keine offene
        Stelle, sondern der Normalfall.
        """

        sheets = self.characters()

        ratios = []

        open_count = 0

        for sheet in sheets:

            ratio = readiness(sheet)

            if ratio is None:
                continue

            ratios.append(ratio)

            for counts in (sheet.get("enchants"), sheet.get("gems")):

                if counts:
                    open_count += counts.get("missing", 0)

        return {
            "characters": len(sheets),
            "rated": len(ratios),
            "ratio": (sum(ratios) / len(ratios)) if ratios else None,
            "open": open_count,
            "hidden": len(self.hidden()),
        }
