from __future__ import annotations

from addon.sync_reader import SyncReader
from core.lua_table import quote_lua_string, to_lua, upsert_variable
from core.version import VERSION


def render_entries(messages: list[dict]) -> str:
    """
    Die Nachrichten einer Zustellung als Lua-Tabelleneinträge.

    Steht hier und nicht in InboxWriter, weil es zwei Wege ins Addon
    gibt und beide exakt dieselbe Warteschlange tragen müssen: die
    SavedVariable WeintCompanionInboxDB (dieser Writer) und die
    Live-Brücke im Addon-Ordner (addon/live_bridge.py). Zwei
    Renderer wären zwei Formate, sobald einer von beiden erweitert
    wird - und der Unterschied fiele erst im Spiel auf.
    """

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

    return "".join(entries)


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

        #
        # Die eigene Version mitschreiben - bei JEDEM Schreibvorgang,
        # auch bei leerer Queue.
        #
        # Grund: das Addon schickt seit WeintCodex 1.3.3.0 eine
        # Nachricht "character_report" (wer ist gerade angemeldet).
        # Eine Companion, die diesen Typ nicht kennt, würde ihn in
        # ihren generischen Zweig fallen lassen und an den Bot
        # schicken; der antwortet nicht mit Erfolg, die Nachricht
        # bleibt liegen, und der Nutzer bekäme alle fünf Sekunden
        # "Nachricht #N konnte nicht gesendet werden". Das Addon liest
        # diese Marke deshalb und sendet erst, wenn die Companion neu
        # genug ist.
        #
        # Eine reine Empfehlung zur Update-Reihenfolge hätte das nicht
        # verhindert - Addon und App werden unabhängig aktualisiert.
        #

        body = (
            f'["companionVersion"] = {quote_lua_string(VERSION)},\n'
            '["queue"] = {\n'
            + render_entries(messages)
            + "},\n"
        )

        #
        # Der Rückgabewert wird durchgereicht: upsert_variable()
        # schreibt nicht, wenn WoW die Datei zwischen unserem Lesen
        # und unserem Ersetzen selbst geschrieben hat (siehe dort).
        # "Diesmal nicht" ist kein Fehler - der nächste Takt schreibt
        # erneut, und die Live-Brücke trägt denselben Inhalt ohnehin.
        #

        return upsert_variable(file, "WeintCompanionInboxDB", body)
