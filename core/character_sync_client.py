from __future__ import annotations

import httpx

from core.discord_account import DiscordAccountStore

BOT_BASE_URL = "https://weintcodex-a1d.b.jrnm.app"


class CharacterSyncClient:
    """
    Meldet die vom Addon bekannten Twinks (Name + Klasse) authentifiziert
    an den Bot - Gegenstück zu discord/sync_client.py:SyncClient, aber
    an den Discord-Login gebunden, da der Bot wissen muss, WESSEN
    Charaktere das sind (für den Klassen-Abgleich beim Kalender-Invite).
    """

    def __init__(self):

        self.account_store = DiscordAccountStore()

    # --------------------------------------------------

    def is_linked(self) -> bool:

        account = self.account_store.load()

        return bool(
            account
            and account.get("companion_token")
        )

    # --------------------------------------------------

    def send(self, payload: str) -> bool:

        account = self.account_store.load()

        if not account or not account.get("companion_token"):
            return False

        characters = []

        for entry in payload.split(","):

            entry = entry.strip()

            if not entry:
                continue

            parts = entry.split("|")

            name = parts[0].strip()
            cls = parts[1].strip() if len(parts) > 1 else ""

            if name:

                characters.append({
                    "name": name,
                    "class": cls,
                })

        try:

            response = httpx.post(
                f"{BOT_BASE_URL}/companion/characters",
                json={"characters": characters},
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=15,
            )

        except Exception as e:

            print(f"Charakter-Sync-Fehler: {e}")

            return False

        if response.status_code != 200:
            return False

        try:

            body = response.json()

        except ValueError:

            return False

        return body.get("status") == "ok"
