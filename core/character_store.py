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

    def characters(self) -> list[dict]:
        """
        Alle bekannten Charaktere, zuletzt gespielter zuerst.
        """

        return sorted(
            self.data.values(),
            key=lambda sheet: sheet.get("updated", 0),
            reverse=True,
        )

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

            for sheet in self.characters():

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
        }
