from __future__ import annotations

import httpx

from addon.inbox_writer import InboxWriter
from core.discord_account import DiscordAccountStore

BOT_BASE_URL = "https://weintcodex-a1d.b.jrnm.app"


class DiscordRosterSync:
    """
    Holt periodisch den Raid-Roster-Export vom Bot ab (nur möglich,
    wenn ein Discord-Account verknüpft UND per Rolle autorisiert ist)
    und übergibt ihn ans Addon. Läuft im selben Rhythmus wie der
    bestehende Material-Sync (siehe CompanionManager._run_sync_worker).
    """

    def __init__(self, manager):

        self.manager = manager
        self.account_store = DiscordAccountStore()

        #
        # Verhindert wiederholtes Schreiben/Reimportieren identischer
        # Daten bei jedem Sync-Zyklus - nur bei tatsächlicher
        # Änderung (neue/andere Anmeldungen) wird erneut zugestellt.
        #

        self._last_delivered = None

    # --------------------------------------------------

    def process(self):

        account = self.account_store.load()

        if not account or not account.get("companion_token"):
            return

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}/companion/raid-roster",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=10,
            )

        except Exception as exc:

            self.manager.logger.error(
                f"Raid-Roster-Abruf fehlgeschlagen: {exc}"
            )

            return

        #
        # Keine Berechtigung / kein aktiver Raid - kein Fehler,
        # einfach nichts zu tun in diesem Zyklus.
        #

        if response.status_code in (401, 403, 404):
            return

        if response.status_code != 200:

            self.manager.logger.error(
                f"Raid-Roster-Abruf fehlgeschlagen ({response.status_code})."
            )

            return

        data = response.json()

        wednesday = data.get("wednesday") or ""
        thursday = data.get("thursday") or ""

        fingerprint = (wednesday, thursday)

        if fingerprint == self._last_delivered:
            return

        wow_path = self.manager.state.wow_path

        if wow_path is None:
            return

        writer = InboxWriter(wow_path)

        delivered = writer.send_batch([
            {"type": "raid_import", "payload": wednesday},
            {"type": "raid_import", "payload": thursday},
        ])

        if not delivered:
            return

        self._last_delivered = fingerprint

        self.manager.logger.success(
            "Raid-Roster an das Addon übergeben."
        )
