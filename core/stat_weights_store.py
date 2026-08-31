"""
Die Sim-Gewichte auf der Platte.

`stat_weights.json` in `Paths.config()` und nicht in `Paths.cache()`:
dahinter steht ein Sim-Lauf. Wer den wiederherstellen will, muss ihn
neu rechnen lassen - dieselbe Überlegung wie bei `weakauras.json`,
`characters.json` und `academy_progress.json`. Ein Aufräumlauf, der
die Datei löscht, wäre der Verlust einer Nachmittagsarbeit.

**Eine Gewichtung je Spezialisierung.** Der Profilschlüssel ist der
Schlüssel: eine zweite Gewichtung für dieselbe Spec wäre eine zweite
Antwort auf eine Frage, die im Spiel nur eine hat (dort steht
`customWeights[<Profilschlüssel>]`). Ein neuer Sim **ersetzt** den
Eintrag deshalb, statt sich daneben zu legen.

**Gelöscht wird auch im Spiel.** Die Zustellung ist immer die ganze
Liste (`core/stat_weights_sync.py`), also verschwindet ein hier
entfernter Vorschlag dort dadurch, dass er in der nächsten Zustellung
fehlt. Eine Einzelnachricht könnte "es gibt mich nicht mehr" gar nicht
ausdrücken, weil das Addon seine Inbox bei jedem Login leert.
"""

from __future__ import annotations

import json
import time

from core.paths import Paths
from core.stat_weights import STAT_ORDER, WeightSet


WEIGHTS_FILE = "stat_weights.json"


PAYLOAD_VERSION = 1


class StatWeightsStore:

    def __init__(self, manager, path=None):

        self.manager = manager

        self.file = path or (Paths.config() / WEIGHTS_FILE)

        #
        # {Profilschlüssel: WeightSet}
        #

        self._sets: dict[str, WeightSet] = {}

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

        except Exception as exc:

            #
            # Eine defekte Datei darf die Anwendung nicht aufhalten -
            # aber auch nicht stillschweigend überschrieben werden.
            # Deshalb eine Warnung im Protokoll statt eines stummen
            # Neuanfangs.
            #

            self._log(
                "warning",
                f"Die gespeicherten Sim-Gewichte konnten nicht gelesen "
                f"werden ({exc}). Die Datei bleibt liegen; bis sie in "
                f"Ordnung ist, zeigt die Seite nichts an.",
            )

            return

        if not isinstance(loaded, dict):
            return

        for raw in loaded.get("sets", []) or []:

            entry = _from_json(raw)

            if entry is not None:
                self._sets[entry.spec_key] = entry

    def save(self):
        """
        Atomar schreiben - wie `core/config.py` und
        `core/character_store.py`.
        """

        try:

            self.file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": PAYLOAD_VERSION,
                "sets": [_to_json(entry) for entry in self.sets()],
            }

            tmp_path = self.file.with_suffix(self.file.suffix + ".tmp")

            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)

            tmp_path.replace(self.file)

        except Exception as exc:

            self._log(
                "error",
                f"Die Sim-Gewichte konnten nicht gespeichert werden: {exc}",
            )

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def sets(self) -> list[WeightSet]:
        """
        Alle Gewichtungen, die zuletzt eingelesene zuerst.
        """

        return sorted(
            self._sets.values(),
            key=lambda entry: (entry.created, entry.spec_key),
            reverse=True,
        )

    def get(self, spec_key: str) -> WeightSet | None:

        return self._sets.get((spec_key or "").strip().upper())

    def delivery(self) -> list[WeightSet]:
        """
        Was ins Addon geht. Heute alles - der Unterschied zu `sets()`
        steht hier trotzdem als eigene Frage, damit ein späterer Filter
        (etwa "nur die Spezialisierungen, die dieser Rechner spielt")
        nicht in der Zustellung selbst landet.
        """

        return self.sets()

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def put(self, entry: WeightSet) -> WeightSet:
        """
        Eine Gewichtung ablegen. Ohne Zeitstempel bekommt sie den
        jetzigen - er entscheidet über die Reihenfolge und darüber, was
        die Seite als "vom 31.08." nennt.
        """

        if not entry.spec_key:
            raise ValueError("Ohne Spezialisierung lässt sich eine "
                             "Gewichtung keinem Profil zuordnen.")

        if not entry.created:

            entry = WeightSet(
                spec_key=entry.spec_key,
                weights=dict(entry.weights),
                character=entry.character,
                realm=entry.realm,
                source=entry.source,
                created=int(time.time()),
                note=entry.note,
            )

        self._sets[entry.spec_key] = entry

        self.save()

        return entry

    def remove(self, spec_key: str) -> bool:

        key = (spec_key or "").strip().upper()

        if key not in self._sets:
            return False

        del self._sets[key]

        self.save()

        return True

    # --------------------------------------------------

    def _log(self, level: str, message: str):

        logger = getattr(self.manager, "logger", None)

        if logger is None:
            return

        getattr(logger, level, logger.info)(message)


def _to_json(entry: WeightSet) -> dict:

    return {
        "spec": entry.spec_key,
        "weights": {
            key: entry.weights[key]
            for key in STAT_ORDER
            if entry.weights.get(key)
        },
        "character": entry.character,
        "realm": entry.realm,
        "source": entry.source,
        "created": int(entry.created or 0),
        "note": entry.note,
    }


def _from_json(raw) -> WeightSet | None:

    if not isinstance(raw, dict):
        return None

    spec_key = str(raw.get("spec", "")).strip().upper()

    if not spec_key:
        return None

    weights: dict[str, int] = {}

    for key, value in (raw.get("weights") or {}).items():

        try:
            number = int(value)

        except (TypeError, ValueError):
            continue

        if number > 0:
            weights[str(key)] = number

    if not weights:
        return None

    return WeightSet(
        spec_key=spec_key,
        weights=weights,
        character=str(raw.get("character", "")),
        realm=str(raw.get("realm", "")),
        source=str(raw.get("source", "sim")) or "sim",
        created=int(raw.get("created", 0) or 0),
        note=str(raw.get("note", "")),
    )
