from __future__ import annotations

from addon.sync_reader import SyncReader
from core.lua_table import quote_lua_string, to_lua, upsert_variable


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

        payload darf eine Zeichenkette sein (so kommen die
        WCIMPORT-Strings des Bots herüber) oder eine verschachtelte
        Struktur aus Dictionaries, Listen, Zahlen und Wahrheitswerten.
        Letztere wird als echtes Lua geschrieben und landet im Addon
        direkt als Tabelle - siehe INBOX_HANDLERS in
        modules/companion.lua. Ein Trennzeichen-Format wäre für die
        Auswertungs- und Lektionstexte nicht eindeutig genug.
        """

        file = self.reader.get_file()

        if file is None:
            return False

        entries = []

        for message in messages:

            payload = message.get("payload")

            if not payload:
                continue

            if isinstance(payload, str):
                rendered = quote_lua_string(payload)
            else:
                rendered = to_lua(payload, indent=0)

            entries.append(
                "{\n"
                f'["type"] = {quote_lua_string(message["type"])},\n'
                f'["payload"] = {rendered},\n'
                "},\n"
            )

        body = (
            '["queue"] = {\n'
            + "".join(entries)
            + "},\n"
        )

        upsert_variable(file, "WeintCompanionInboxDB", body)

        return True
