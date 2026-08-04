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

        Optional darf eine Nachricht ein "community" (Discord-Guild-ID
        als Zeichenkette) tragen. Das Addon verwirft ab 1.2.0.0
        Nachrichten, deren Community nicht zu der passt, mit der es
        verknüpft ist - so vermischen sich die Daten zweier Gilden
        nicht, wenn in der Companion der verknüpfte Discord-Account
        gewechselt wird. Fehlt das Feld, gilt die Nachricht dort als
        Alt-Format und wird angenommen.
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

            community = message.get("community")

            community_line = ""

            if community not in (None, ""):

                #
                # Immer als Zeichenkette: eine Discord-Snowflake ist zu
                # groß für Luas 5.1-Zahlen und würde als Zahl
                # geschrieben zu "1.23e+18" - im Addon passt das dann
                # nie gegen die Dezimaldarstellung der Bindung.
                #

                community_line = (
                    f'["community"] = '
                    f'{quote_lua_string(str(community))},\n'
                )

            entries.append(
                "{\n"
                f'["type"] = {quote_lua_string(message["type"])},\n'
                f"{community_line}"
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
