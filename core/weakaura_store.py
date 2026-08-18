"""
Die WeakAura-Bibliothek auf der Platte.

Was hier liegt, hat jemand von Hand eingetippt: Name, Beschreibung
und ein Importstring, den er sich aus dem Spiel geholt hat. Das ist
Nutzerarbeit und kein Zwischenspeicher, deshalb `Paths.config()` und
nicht `Paths.cache()` - dieselbe Überlegung wie bei
`core/character_store.py` und `academy_progress.json`. Ein
Aufräumlauf, der die Liste löscht, wäre der Verlust einer
Nachmittagsarbeit.

Zwei Dinge liegen in derselben Datei:

* **`auras`** - was diese Seite selbst angelegt hat. Sie geht als
  Ganzes ans Addon (`core/weakaura_sync.py`).
* **`catalog`** - was das Addon zuletzt gemeldet hat, welche Auren es
  also kennt (`weakaura_catalog`, siehe
  `core/weakaura_catalog_sync.py`). Streng genommen ein
  Zwischenspeicher; er liegt trotzdem hier, weil er sonst bei jedem
  Start leer wäre und die Seite bis zur nächsten Anmeldung im Spiel
  nicht sagen könnte, welche Auren es überhaupt zu aktualisieren
  gibt.

Die Liste **ersetzt** im Addon die dortige vollständig. Deshalb muss
sie hier vollständig sein: eine gelöschte Aura verschwindet im Spiel
dadurch, dass sie in der nächsten Zustellung nicht mehr vorkommt -
eine Einzelnachricht könnte "es gibt mich nicht mehr" gar nicht
ausdrücken.
"""

from __future__ import annotations

import json

from core.paths import Paths
from core.weakaura_library import (
    CatalogEntry,
    WeakAura,
    normalize_category,
    parse_catalog,
)


LIBRARY_FILE = "weakauras.json"


#
# Version der Nutzlast, die ans Addon geht. Sie steht dort im
# Kopf der Tabelle; das Addon liest sie bisher nicht, aber eine
# Nutzlast ohne Formatangabe lässt sich später nicht mehr
# unterscheiden.
#

PAYLOAD_VERSION = 1


class WeakAuraStore:

    def __init__(self, manager, path=None):

        self.manager = manager

        self.file = path or (Paths.config() / LIBRARY_FILE)

        self._auras: dict[str, WeakAura] = {}

        self._catalog: list[CatalogEntry] = []

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
            # aber sie darf auch nicht stillschweigend überschrieben
            # werden: dahinter steht Tipparbeit. Deshalb eine
            # Warnung im Protokoll statt eines stummen Neuanfangs.
            #

            self._log(
                "warning",
                f"Die WeakAura-Bibliothek konnte nicht gelesen werden "
                f"({exc}). Die Datei bleibt liegen; bis sie in Ordnung "
                f"ist, zeigt die Seite nichts an.",
            )

            return

        if not isinstance(loaded, dict):
            return

        for raw in loaded.get("auras", []) or []:

            aura = _aura_from_json(raw)

            if aura is not None:
                self._auras[aura.id] = aura

        self._catalog = [
            CatalogEntry(
                id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                category=normalize_category(raw.get("category", "")),
                version=str(raw.get("version", "")),
                origin=str(raw.get("origin", "addon")),
            )
            for raw in loaded.get("catalog", []) or []
            if isinstance(raw, dict) and raw.get("id")
        ]

    def save(self):
        """
        Atomar schreiben - wie `core/config.py` und
        `core/character_store.py`. Ein Absturz mitten im Schreiben
        darf keine halbe Bibliothek hinterlassen.
        """

        try:

            self.file.parent.mkdir(parents=True, exist_ok=True)

            payload = {
                "version": PAYLOAD_VERSION,
                "auras": [_aura_to_json(aura) for aura in self.auras()],
                "catalog": [
                    {
                        "id": entry.id,
                        "name": entry.name,
                        "category": entry.category,
                        "version": entry.version,
                        "origin": entry.origin,
                    }
                    for entry in self._catalog
                ],
            }

            tmp_path = self.file.with_suffix(self.file.suffix + ".tmp")

            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)

            tmp_path.replace(self.file)

        except Exception as exc:

            self._log(
                "error",
                f"Die WeakAura-Bibliothek konnte nicht gespeichert "
                f"werden: {exc}",
            )

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def auras(self) -> list[WeakAura]:
        """
        Alle selbst angelegten Auren, nach Rubrik und Name sortiert -
        dieselbe Ordnung wie im Spiel.
        """

        return sorted(
            self._auras.values(),
            key=lambda aura: (aura.category, aura.name.lower()),
        )

    def get(self, aura_id: str) -> WeakAura | None:

        return self._auras.get(aura_id)

    def catalog(self) -> list[CatalogEntry]:
        """
        Was das Addon zuletzt gemeldet hat, mitgelieferte Auren
        zuerst - das sind die, die man hier nicht schon vor sich hat.
        """

        return sorted(
            self._catalog,
            key=lambda entry: (not entry.from_addon, entry.name.lower()),
        )

    def addon_entries(self) -> list[CatalogEntry]:
        """
        Nur die mitgelieferten, die hier noch keine eigene Fassung
        haben.

        Der zweite Teil ist nicht kosmetisch: wer eine mitgelieferte
        Aura aktualisiert, legt hier einen Eintrag unter **derselben**
        Kennung an. Ohne diesen Filter stünde sie danach zweimal in
        der Liste - einmal als eigene und einmal als mitgelieferte -
        und es wäre nicht zu erkennen, welche der beiden im Spiel
        gewinnt. Beim nächsten Anmelden meldet das Addon sie ohnehin
        als "companion"; bis dahin sagt der Filter dasselbe.
        """

        return [
            entry
            for entry in self.catalog()
            if entry.from_addon and entry.id not in self._auras
        ]

    def taken_ids(self) -> set[str]:
        """
        Jede Kennung, die im Spiel schon belegt ist - eigene wie
        gemeldete. Eine neue Aura darf keine davon bekommen, sonst
        ersetzte sie unabsichtlich etwas.
        """

        return set(self._auras) | {entry.id for entry in self._catalog}

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def put(self, aura: WeakAura):
        """
        Anlegen oder ersetzen - die ID entscheidet, welches von
        beidem es ist. Genau wie im Addon.
        """

        if not aura.id:
            return

        aura.category = normalize_category(aura.category)

        self._auras[aura.id] = aura

        self.save()

    def remove(self, aura_id: str) -> bool:

        if aura_id not in self._auras:
            return False

        del self._auras[aura_id]

        self.save()

        return True

    def apply_catalog(self, payload: str) -> bool:
        """
        Die Meldung des Addons übernehmen.

        Gibt zurück, ob sich etwas geändert hat - der Aufrufer
        protokolliert nur dann, sonst stünde bei jeder Anmeldung
        dieselbe Zeile im Protokoll.
        """

        entries = parse_catalog(payload)

        if not entries:
            return False

        def signature(items):
            return [
                (item.id, item.name, item.category, item.version, item.origin)
                for item in items
            ]

        if signature(entries) == signature(self._catalog):
            return False

        self._catalog = entries

        self.save()

        return True

    # --------------------------------------------------
    # Zustellung
    # --------------------------------------------------

    def payload(self, updated_at: int = 0) -> dict:
        """
        Die vollständige Bibliothek in der Form, in der das Addon sie
        erwartet (siehe `docs/weakaura-bridge.md`).
        """

        return {
            "version": PAYLOAD_VERSION,
            "updatedAt": int(updated_at or 0),
            "auras": [aura.payload() for aura in self.auras()],
        }

    # --------------------------------------------------

    def _log(self, level: str, message: str):

        logger = getattr(self.manager, "logger", None)

        if logger is None:
            return

        getattr(logger, level, logger.info)(message)


def _aura_to_json(aura: WeakAura) -> dict:

    return {
        "id": aura.id,
        "name": aura.name,
        "category": aura.category,
        "description": aura.description,
        "version": aura.version,
        "author": aura.author,
        "icon": aura.icon,
        "string": aura.string,
        "updated_at": int(aura.updated_at or 0),
        "replaces_addon": bool(aura.replaces_addon),
    }


def _aura_from_json(raw) -> WeakAura | None:

    if not isinstance(raw, dict):
        return None

    identifier = str(raw.get("id") or "").strip()

    if not identifier:
        return None

    return WeakAura(
        id=identifier,
        name=str(raw.get("name") or ""),
        category=normalize_category(raw.get("category", "")),
        description=str(raw.get("description") or ""),
        version=str(raw.get("version") or "1.0"),
        author=str(raw.get("author") or ""),
        icon=str(raw.get("icon") or ""),
        string=str(raw.get("string") or ""),
        updated_at=int(raw.get("updated_at") or 0),
        replaces_addon=bool(raw.get("replaces_addon")),
    )
