from __future__ import annotations

from addon.sync_reader import SyncReader
from core.lua_table import upsert_variable


class InboxWriter:
    """
    Gegenrichtung zu SyncReader: schreibt Nachrichten von Companion
    Richtung Addon (z. B. den automatisch abgerufenen Raid-Roster-
    Export) in eine eigene SavedVariable (WeintCompanionInboxDB)
    innerhalb derselben WeintCodex.lua. Das Addon liest und leert
    diese Queue beim Login (siehe modules/companion.lua ProcessInbox).
    """

    def __init__(self, wow_path):

        self.reader = SyncReader(wow_path)

    # --------------------------------------------------

    def send_batch(self, messages: list[dict]) -> bool:
        """
        messages: Liste von {"type": ..., "payload": ...}. Ersetzt die
        komplette Inbox-Queue - das Addon leert sie ohnehin bei jedem
        Login vollständig, es gibt also nichts zu erhalten.
        """

        file = self.reader.get_file()

        if file is None:
            return False

        entries = []

        for message in messages:

            payload = message.get("payload") or ""

            if not payload:
                continue

            escaped = (
                payload
                .replace("\\", "\\\\")
                .replace('"', '\\"')
            )

            entries.append(
                "{\n"
                f'["type"] = "{message["type"]}",\n'
                f'["payload"] = "{escaped}",\n'
                "},\n"
            )

        body = (
            '["queue"] = {\n'
            + "".join(entries)
            + "},\n"
        )

        upsert_variable(file, "WeintCompanionInboxDB", body)

        return True
