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
            realm = parts[2].strip() if len(parts) > 2 else ""

            if name:

                characters.append({
                    "name": name,
                    "class": cls,
                    "realm": realm,
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

        if response.status_code == 401:

            #
            # Der Bot kennt dieses Token nicht (mehr) - z. B. weil seine
            # Datenbank bei einem Redeploy zurückgesetzt wurde. Ohne
            # diesen Reset würde is_linked() lokal weiter "verknüpft"
            # melden und dieselbe Nachricht endlos alle paar Sekunden
            # erfolglos erneut versucht werden.
            #

            print(
                "Charakter-Sync-Fehler: Companion-Token vom Bot abgelehnt "
                "(401) - Verknüpfung wird lokal aufgehoben, bitte Discord "
                "in den Einstellungen erneut verbinden."
            )

            self.account_store.clear()

            return False

        if response.status_code != 200:

            print(
                f"Charakter-Sync-Fehler: HTTP {response.status_code} "
                f"- {response.text[:200]}"
            )

            return False

        try:

            body = response.json()

        except ValueError:

            print(
                f"Charakter-Sync-Fehler: Antwort war kein gültiges JSON "
                f"- {response.text[:200]}"
            )

            return False

        if body.get("status") != "ok":

            print(
                f"Charakter-Sync-Fehler: Bot meldet Status "
                f"'{body.get('status')}' ({body.get('detail', '-')})"
            )

            return False

        return True
