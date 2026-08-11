"""
Den Raidtermin beim Bot abholen.

Die HTTP-Hälfte zu `core/raid_schedule.py` - getrennt aus demselben
Grund, aus dem `core/warcraftlogs_client.py` von
`analyzer/providers/warcraftlogs_payload.py` getrennt ist: die
Rechnung soll ohne Netz prüfbar bleiben.

Läuft im gewöhnlichen Sync-Takt mit, in eigenem `try/except` wie die
übrigen Absender. Zwei Eigenheiten:

- **Das Ergebnis wird gespeichert** (`raid_schedule.json` unter
  `Paths.cache()`). Der Abruf braucht ein verknüpftes Konto und einen
  erreichbaren Bot; ohne Zwischenspeicher stünde die Übersicht bei
  jedem Start ein paar Sekunden lang auf "kein Termin bekannt" und
  offline dauerhaft. Der Termin ist reproduzierbar, gehört also unter
  `cache()` und nicht unter `config()`.
- **Ein Fehlschlag löscht nichts.** Ist der Bot kurz nicht erreichbar,
  bleibt der zuletzt bekannte Termin stehen - er wird dadurch nicht
  falsch. Nur eine ausdrückliche Antwort "kein Raid" räumt ihn weg.
"""

from __future__ import annotations

import json
import time

import httpx

from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore
from core.paths import Paths
from core.raid_schedule import RaidSchedule, parse_schedule


#
# Der Termin ändert sich im Minutentakt nicht - ein Abruf je Sync-Takt
# (5 s) wäre eine Anfrage alle fünf Sekunden für eine Auskunft, die
# sich einmal pro Woche ändert.
#

REFRESH_SECONDS = 300

TIMEOUT = 10

CACHE_FILE = "raid_schedule.json"


class RaidScheduleSync:

    def __init__(self, manager):

        self.manager = manager

        self.account_store = DiscordAccountStore()

        self.schedule = self._load_cached()

        self._last_fetch = 0.0

    # --------------------------------------------------

    def _cache_path(self):

        return Paths.cache() / CACHE_FILE

    def _load_cached(self) -> RaidSchedule:

        path = self._cache_path()

        if not path.exists():
            return RaidSchedule()

        try:

            return parse_schedule(
                json.loads(path.read_text(encoding="utf-8"))
            )

        except Exception:

            #
            # Eine unlesbare Datei ist kein Grund, den Start zu
            # verhindern - der nächste Abruf schreibt sie neu.
            #

            return RaidSchedule()

    def _store(self, data: dict):

        try:

            path = self._cache_path()

            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )

        except OSError as exc:

            self.manager.logger.warning(
                f"Raidtermin konnte nicht gespeichert werden: {exc}"
            )

    # --------------------------------------------------

    def invalidate(self):
        """
        Den nächsten Aufruf von `process()` wirklich abrufen lassen -
        für den Knopf "Erneut prüfen" und nach einer Kontoänderung.
        """

        self._last_fetch = 0.0

    def process(self):

        account = self.account_store.load()

        if not account or not account.get("companion_token"):
            return

        now = time.monotonic()

        if now - self._last_fetch < REFRESH_SECONDS:
            return

        self._last_fetch = now

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}/companion/raid-schedule",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=TIMEOUT,
            )

        except Exception as exc:

            #
            # Kein `logger.error`: der Bot ist regelmäßig kurz nicht
            # erreichbar, und ein roter Eintrag alle fünf Minuten für
            # eine Nebensache wäre Lärm. Der zuletzt bekannte Termin
            # bleibt stehen.
            #

            self.manager.logger.info(
                f"Raidtermin nicht abrufbar: {exc}"
            )

            return

        if response.status_code == 404:

            #
            # Ältere Bot-Fassung: den Endpunkt gibt es dort nicht. Die
            # Übersicht sagt dann weiter "kein Termin bekannt", genau
            # wie bisher.
            #

            return

        if response.status_code != 200:

            self.manager.logger.info(
                "Raidtermin nicht abrufbar "
                f"({response.status_code})."
            )

            return

        try:
            data = response.json()

        except ValueError:
            return

        schedule = parse_schedule(data)

        changed = (
            schedule.known != self.schedule.known
            or schedule.days != self.schedule.days
            or schedule.title != self.schedule.title
        )

        self.schedule = schedule

        self._store(data)

        if changed and schedule.known:

            self.manager.logger.success(
                f"Raidtermin übernommen: {schedule.title}."
            )
