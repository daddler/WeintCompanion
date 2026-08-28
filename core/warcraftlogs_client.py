"""
Abruf des laufenden WarcraftLogs-Berichts beim WeintCodex-Bot.

Die Companion-App spricht bewusst NICHT selbst mit WarcraftLogs. Der
Bot sieht den Webhook, mit dem der Livelog-Uploader den Bericht ins
Discord meldet, hält die API-Zugangsdaten und liefert das Ergebnis
bereits aufbereitet aus. Diese Klasse ist deshalb nur die dünne
HTTP-Schicht dazu - die Übersetzung in einen Snapshot passiert im
Analyzer (analyzer/providers/warcraftlogs_payload.py).

Aufbau und Statuscodes des Endpunkts stehen in
docs/warcraftlogs-bridge.md; das ist zugleich die Vorlage für die
Bot-Seite.

Das Muster folgt core/discord_roster_sync.py und
core/character_sync_client.py: Basis-URL aus core/backend_config.py,
Authentifizierung über den gespeicherten `companion_token`.
"""

from __future__ import annotations

import httpx

from analyzer.providers.warcraftlogs import FetchResult
from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore


ENDPOINT = "/companion/warcraftlogs/live"


#
# Der Bot fragt seinerseits WarcraftLogs an; etwas mehr Geduld als
# beim reinen Roster-Abruf ist deshalb angemessen. Der Abruf läuft im
# eigenen Thread des Providers, blockiert also keine Oberfläche.
#

TIMEOUT = 15.0


class WarcraftLogsClient:
    """
    Holt den aktuellen Bericht beim Bot ab.
    """

    def __init__(self, account_store=None):

        self.account_store = account_store or DiscordAccountStore()

    # --------------------------------------------------

    def is_linked(self) -> bool:

        account = self.account_store.load()

        return bool(
            account
            and account.get("companion_token")
        )

    # --------------------------------------------------

    def fetch(self) -> FetchResult:
        """
        Ein Abruf.

        Wirft nie: jeder Fehlerfall wird zu einem FetchResult mit
        erklärendem `reason`. Dieser Text erscheint unverändert in
        den Einstellungen, ist deshalb an den Nutzer gerichtet und
        nennt möglichst den nächsten Schritt.
        """

        account = self.account_store.load()

        if not account or not account.get("companion_token"):

            return FetchResult(
                reason=(
                    "Kein Discord-Konto verknüpft - die Verbindung "
                    "läuft über den Bot."
                ),
            )

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}{ENDPOINT}",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=TIMEOUT,
            )

        except Exception as exc:

            return FetchResult(
                reason=f"Bot nicht erreichbar: {exc}",
            )

        return self._interpret(response)

    # --------------------------------------------------

    def _interpret(self, response) -> FetchResult:

        status = response.status_code

        if status == 401:

            #
            # Der Bot kennt dieses Token nicht mehr. Dieselbe
            # Behandlung wie im CharacterSyncClient: die lokale
            # Verknüpfung aufheben, damit die Oberfläche nicht weiter
            # "verbunden" behauptet und der Nutzer den richtigen
            # nächsten Schritt sieht.
            #
            #
            # Nicht beim ersten Mal aufheben: siehe
            # AUTH_REJECTIONS_BEFORE_UNLINK und
            # AUTH_REJECTION_COOLDOWN in core/discord_account.py.
            # Ein einzelnes 401 kann ein gerade neu startender Bot
            # sein; erst mehrere, die weit genug auseinanderliegen,
            # heissen, dass er dieses Token wirklich nicht mehr kennt
            # - ein Abruf, der im Takt wiederholt wird, ist ein
            # Vorfall und nicht drei.
            #

            self.account_store.note_auth_rejected()

            return FetchResult(
                reason=(
                    "Der Bot hat die Verknüpfung abgelehnt - bitte "
                    "Discord in den Einstellungen erneut verbinden."
                ),
            )

        if status == 403:

            return FetchResult(
                reason=(
                    "Keine Berechtigung für die Raid-Auswertung - "
                    "dafür ist eine Rolle im Discord nötig."
                ),
            )

        #
        # 204/404 sind der Normalfall außerhalb des Raids: es läuft
        # schlicht kein Livelog. Das ist kein Fehler und wird deshalb
        # ruhig formuliert.
        #

        if status in (204, 404):

            return FetchResult(
                reason="Zurzeit läuft kein Livelog.",
            )

        if status != 200:

            return FetchResult(
                reason=f"Der Bot antwortete mit HTTP {status}.",
            )

        try:
            body = response.json()

        except ValueError:

            return FetchResult(
                reason="Die Antwort des Bots war kein gültiges JSON.",
            )

        if not isinstance(body, dict):

            return FetchResult(
                reason="Die Antwort des Bots hatte ein unerwartetes Format.",
            )

        #
        # Der Bot meldet über `status`, ob gerade ein Bericht läuft.
        # "idle" ist wie 204 der ruhige Normalfall.
        #

        state = str(body.get("status", "ok")).lower()

        if state == "idle":

            return FetchResult(
                reason=(
                    str(body.get("detail") or "").strip()
                    or "Zurzeit läuft kein Livelog."
                ),
            )

        if state != "ok":

            return FetchResult(
                reason=(
                    str(body.get("detail") or "").strip()
                    or f"Der Bot meldet Status '{state}'."
                ),
            )

        return FetchResult(payload=body)
