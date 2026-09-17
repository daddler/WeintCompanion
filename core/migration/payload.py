"""
Was der Nutzer mitnimmt - und was ausdruecklich nicht.

Die Versuchung ist gross, hier einfach `config.json` zu kopieren.
Das waere aus zwei Gruenden falsch. Erstens zwingt es der neuen App
die Datenstruktur der alten auf: Companion-Forever soll seine
Einstellungen selbst ordnen duerfen und nicht auf ewig die
Schluesselnamen von 4.x erben. Zweitens enthaelt der Bestand Dinge,
die niemand weiterreichen sollte.

DESHALB EINE UEBERGABE UND KEINE KOPIE
--------------------------------------

    V4-Daten  ->  dieser Adapter  ->  Payload (versioniert)  ->  V5

Der Payload ist ein *Vertrag*, kein Abzug: `schema_version` steht
oben, jedes Feld hat eine benannte Bedeutung, und Companion-Forever
liest ihn mit seiner eigenen Vorstellung davon, wo so etwas bei ihm
hingehoert. Was V5 daraus macht, entscheidet V5.

KEINE GEHEIMNISSE
-----------------

Weitergegeben wird nur, was aus einer **Positivliste** stammt
(`SETTINGS`). Alles andere faellt heraus - auch Neues, das jemand
spaeter der Konfiguration hinzufuegt, ohne an diese Datei zu denken.
Eine Sperrliste waere die falsche Richtung: sie muss jeden Namen
kennen, den es je geben wird.

Zusaetzlich laeuft jeder Wert durch `_looks_secret()`, und das ist
kein doppelter Boden aus Uebervorsicht, sondern die Antwort auf den
naheliegendsten Fehler: jemand nimmt einen Schluessel in die
Positivliste auf, unter dem spaeter ein Token landet.

Das verknuepfte Discord-Konto (`discord_account.json`) enthaelt das
Companion-Token und wird **nie** uebergeben - es steht im Payload
nur als Datei, die V5 ausdruecklich *nicht* einlesen soll
(`migrate: false`). Dass die Verknuepfung besteht, ist dagegen
harmlos und erspart dem Nutzer in V5 die Suche nach dem Grund,
warum er sich erneut verbinden soll.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os
import platform

from core.migration.target import MigrationTarget
from core.paths import Paths
from core.version import VERSION


SCHEMA_VERSION = 1

SOURCE_PRODUCT = "WeintCompanion"

PAYLOAD_FILE = "migration.json"


#
# Die Positivliste. Jeder Eintrag ist eine Entscheidung: "das ist in
# der neuen Generation genauso noch wahr". Was daran haengt, dass
# diese App so gebaut ist, wie sie gebaut ist (Fensterzustand,
# Merker fuer gesehene Popups, einmalige Umstellungen), gehoert
# nicht dazu - V5 hat seine eigene Einfuehrung.
#

SETTINGS = (
    #
    # Das Wichtigste ueberhaupt: wo das Spiel liegt. Wer das nicht
    # mitnimmt, laesst jeden Nutzer die Ordnersuche erneut machen.
    #
    "wow_client",
    "wow_paths",
    "combatlog_path",
    #
    # Arbeitsweise
    #
    "check_updates",
    "auto_sync",
    "sync_interval",
    "start_on_boot",
    "minimize_to_tray",
    "linux_launcher_type",
    "linux_launcher_value",
    #
    # Fachliche Vorgaben
    #
    "characters_min_level",
    "raid_data_source",
    "roster_sync_enabled",
    "character_roster_sync_enabled",
    "access_profile_sync_enabled",
    "addon_analysis_sync_enabled",
    "weinttv_enabled",
    "academy_enabled",
    "sim_clipboard",
    #
    # "Wer bin ich" - eine Antwort, die der Nutzer einmal gegeben
    # hat und nicht zweimal geben soll.
    #
    "academy_player_name",
    "academy_follow_game",
    "academy_manual_for",
    #
    # Gemeinschaft (keine Zugangsdaten, nur die Zuordnung)
    #
    "discord_community_id",
    "discord_community_name",
    "access_role_map",
    #
    # Darstellung
    #
    "accent",
    "density",
    "motion_reduced",
    "nav_collapsed",
)


#
# Lokale Datenbestaende. Der Payload traegt **Pfade, keine Inhalte**:
# die Dateien sind teils gross (Academy-Verlauf, WeakAura-
# Bibliothek), und sie doppelt auf der Platte zu halten waere weder
# noetig noch ehrlich - sie liegen ohnehin da, V5 laeuft auf
# demselben Rechner.
#

DATA_FILES = (
    ("characters", "characters.json", True),
    ("academy_progress", "academy_progress.json", True),
    ("academy_history", "academy_history.json", True),
    ("weakauras", "weakauras.json", True),
    ("stat_weights", "stat_weights.json", True),
    ("target_gear", "target_gear.json", True),
    #
    # Enthaelt das Companion-Token. Steht hier nur, damit V5 weiss,
    # dass es diese Datei kennt und **nicht** anfasst.
    #
    ("discord_account", "discord_account.json", False),
)


_SECRET_HINTS = (
    "token",
    "secret",
    "password",
    "passwort",
    "api_key",
    "apikey",
    "credential",
    "refresh",
    "access_token",
    "client_secret",
)


def _looks_secret(key: str) -> bool:

    lowered = (key or "").lower()

    return any(hint in lowered for hint in _SECRET_HINTS)


def _clean(value):
    """
    Nur Dinge, die JSON traegt - und Woerterbuecher rekursiv um
    verdaechtige Schluessel erleichtert.
    """

    if isinstance(value, dict):

        return {
            str(key): _clean(item)
            for key, item in value.items()
            if not _looks_secret(str(key))
        }

    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def payload_path() -> Path:
    """
    Wo die Uebergabe liegt.

    Unter `Paths.base()/handover/` und nicht im Konfigurationsordner:
    sie gehoert weder zu den Einstellungen dieser App noch in ihren
    Zwischenspeicher, sondern **zwischen** die beiden Anwendungen.
    Companion-Forever findet sie an dieser Stelle, ohne sonst
    irgendetwas ueber 4.x wissen zu muessen - der Pfad steht im
    Release-Vertrag.
    """

    path = Paths.base() / "handover"

    path.mkdir(parents=True, exist_ok=True)

    return path / PAYLOAD_FILE


def build_payload(
    config,
    target: MigrationTarget,
    target_version: str = "",
    config_dir: Path | None = None,
) -> dict:

    data = getattr(config, "data", {}) or {}

    settings = {}

    for key in SETTINGS:

        if key not in data or _looks_secret(key):
            continue

        settings[key] = _clean(data[key])

    config_dir = Path(config_dir) if config_dir else Paths.config()

    files = []

    for role, name, migrate in DATA_FILES:

        path = config_dir / name

        files.append(
            {
                "role": role,
                "path": str(path),
                "exists": path.exists(),
                "migrate": migrate,
                "note": (
                    ""
                    if migrate
                    else "enthaelt Zugangsdaten - nicht uebernehmen"
                ),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "product": SOURCE_PRODUCT,
            "version": VERSION,
            "platform": platform.system(),
            "config_dir": str(config_dir),
            "data_dir": str(Paths.base()),
        },
        "target": {
            "product": target.product_name,
            "repository": target.slug,
            "major": target.major,
            "channel": target.channel,
            "version": target_version,
        },
        "settings": settings,
        "data_files": files,
        "discord": {
            #
            # Nur die Tatsache, nie das Token.
            #
            "linked": bool(data.get("discord_community_id"))
            or (config_dir / "discord_account.json").exists(),
            "relink_required": True,
        },
    }


def write_payload(payload: dict, path: Path | None = None) -> Path:
    """
    Schreibt die Uebergabe atomar (dieselbe Regel wie
    `Config.save()`): erst daneben, dann `os.replace()`. Eine halb
    geschriebene Uebergabe waere fuer V5 von einer vollstaendigen
    nicht zu unterscheiden.
    """

    path = Path(path) if path else payload_path()

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    with open(temporary, "w", encoding="utf-8") as file:

        json.dump(payload, file, indent=4, ensure_ascii=False)

    os.replace(temporary, path)

    return path
