"""
Die Zielausrüstung auf der Platte.

`target_gear.json` in `Paths.config()` und nicht in `Paths.cache()` -
aus demselben Grund wie `stat_weights.json`: dahinter steht ein
Sim-Lauf, und ein Aufräumlauf, der die Datei löscht, wäre der Verlust
einer Nachmittagsarbeit.

**Eine Zielausrüstung je Spezialisierung.** Der Profilschlüssel ist der
Schlüssel, dieselbe Regel wie bei den Gewichten: eine zweite
Zielausrüstung für dieselbe Spec wäre eine zweite Antwort auf eine
Frage, die im Spiel nur eine hat. Ein neuer Sim **ersetzt** den
Eintrag, statt sich daneben zu legen.

**Gelöscht wird auch im Spiel.** Zugestellt wird immer die ganze Liste
(`core/target_gear_sync.py`), also verschwindet ein hier entfernter
Zielzustand dort dadurch, dass er in der nächsten Zustellung fehlt.
"""

from __future__ import annotations

import json
import time

from core.paths import Paths
from core.target_gear import TargetGear, TargetItem, TargetSet


TARGET_FILE = "target_gear.json"


PAYLOAD_VERSION = 1


class TargetGearStore:

    def __init__(self, manager, path=None):

        self.manager = manager

        self.file = path or (Paths.config() / TARGET_FILE)

        #
        # {Profilschlüssel: TargetSet}
        #

        self._sets: dict[str, TargetSet] = {}

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
            # Eine defekte Datei hält die Anwendung nicht auf, wird aber
            # auch nicht stillschweigend überschrieben - dieselbe
            # Haltung wie im Gewichte-Speicher.
            #

            self._log(
                "warning",
                "Die gespeicherte Zielausrüstung konnte nicht gelesen "
                f"werden ({exc}). Die Datei bleibt liegen; bis sie in "
                "Ordnung ist, zeigt die Seite nichts an.",
            )

            return

        if not isinstance(loaded, dict):
            return

        for raw in loaded.get("sets", []) or []:

            entry = _from_json(raw)

            if entry is not None:
                self._sets[entry.spec_key] = entry

    def save(self):

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
                f"Die Zielausrüstung konnte nicht gespeichert werden: {exc}",
            )

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def sets(self) -> list[TargetSet]:

        return sorted(
            self._sets.values(),
            key=lambda entry: (entry.created, entry.spec_key),
            reverse=True,
        )

    def get(self, spec_key: str) -> TargetSet | None:

        return self._sets.get((spec_key or "").strip().upper())

    def delivery(self) -> list[TargetSet]:

        return self.sets()

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def put(self, entry: TargetSet) -> TargetSet:

        if not entry.spec_key:
            raise ValueError(
                "Ohne Spezialisierung lässt sich eine Zielausrüstung "
                "keinem Profil zuordnen."
            )

        if not entry.created:

            entry = TargetSet(
                gear=entry.gear,
                spec_key=entry.spec_key,
                character=entry.character,
                realm=entry.realm,
                created=int(time.time()),
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


def _to_json(entry: TargetSet) -> dict:

    return {
        "spec": entry.spec_key,
        "character": entry.character,
        "realm": entry.realm,
        "source": entry.source,
        "created": int(entry.created or 0),
        "items": [
            {
                "slot": item.slot,
                "itemId": item.item_id,
                "gems": [int(gem or 0) for gem in item.gems],
                "reforge": item.reforging,
                "enchant": item.enchant,
            }
            for item in entry.items
            if not item.empty
        ],
    }


def _from_json(raw) -> TargetSet | None:

    if not isinstance(raw, dict):
        return None

    spec_key = str(raw.get("spec", "")).strip().upper()

    if not spec_key:
        return None

    items: list[TargetItem] = []

    for row in raw.get("items") or []:

        if not isinstance(row, dict):
            continue

        try:
            slot = int(row.get("slot") or 0)
            item_id = int(row.get("itemId") or 0)

        except (TypeError, ValueError):
            continue

        if not slot or not item_id:
            continue

        gems = []

        for gem in row.get("gems") or []:

            try:
                gems.append(int(gem or 0))

            except (TypeError, ValueError):
                #
                # Ein unlesbarer Stein wird zu einem leeren Sockel und
                # nicht weggelassen: die Position benennt den Sockel.
                #
                gems.append(0)

        items.append(
            TargetItem(
                slot=slot,
                item_id=item_id,
                gems=tuple(gems),
                reforging=int(row.get("reforge") or 0),
                enchant=int(row.get("enchant") or 0),
            )
        )

    if not items:
        return None

    return TargetSet(
        gear=TargetGear(
            known=True,
            source=str(raw.get("source", "")) or "wowsims",
            spec_key=spec_key,
            character=str(raw.get("character", "")),
            realm=str(raw.get("realm", "")),
            items=tuple(items),
        ),
        spec_key=spec_key,
        character=str(raw.get("character", "")),
        realm=str(raw.get("realm", "")),
        created=int(raw.get("created", 0) or 0),
    )
