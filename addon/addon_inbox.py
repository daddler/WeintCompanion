"""
Die gemeinsame Zustellung Richtung Addon.

InboxWriter.send_batch() ersetzt die komplette Queue in
WeintCompanionInboxDB - das ist richtig so, weil das Addon sie beim
Login ohnehin vollständig leert. Sobald aber MEHRERE Absender
zustellen wollen, wird daraus ein Problem: der Raid-Roster-Sync und
der Auswertungs-Sync laufen nacheinander im selben Worker (siehe
CompanionManager._run_sync_worker), und der zweite würde die
Nachrichten des ersten kommentarlos wegschreiben.

Deshalb liegt zwischen den Absendern und dem Writer diese Schicht:
jeder Absender hat einen eigenen Kanal, die Inbox schreibt immer die
Vereinigung aller Kanäle. Wer nichts zu sagen hat, belegt keinen.

Die Kanalinhalte leben nur im Arbeitsspeicher. Das reicht: das Addon
kopiert alles, was es aus der Inbox liest, in seine eigenen
SavedVariables (WeintCodex_SavedData.academy/.weinttv) - es ist also
nicht darauf angewiesen, dass eine Nachricht in der Inbox liegen
bleibt.
"""

from __future__ import annotations

import threading

from addon.inbox_writer import InboxWriter


class AddonInbox:

    def __init__(self, manager):

        self.manager = manager

        self._lock = threading.Lock()

        #
        # {Kanalname: [Nachricht, ...]} - Reihenfolge der Kanäle ist
        # die Einfügereihenfolge, innerhalb eines Kanals die des
        # Absenders.
        #

        self._channels: dict[str, list[dict]] = {}

    # --------------------------------------------------

    def publish(self, channel: str, messages: list[dict]) -> bool:
        """
        Ersetzt den Inhalt eines Kanals und schreibt die Inbox neu.

        Gibt True zurück, wenn geschrieben werden konnte. False heißt
        nur "keine SavedVariables-Datei gefunden" (WoW noch nie
        gestartet, falscher Pfad) - kein Fehler, für den es etwas zu
        melden gäbe.
        """

        wow_path = self.manager.state.wow_path

        if wow_path is None:
            return False

        with self._lock:

            if messages:
                self._channels[channel] = list(messages)
            else:
                self._channels.pop(channel, None)

            combined = [
                message
                for entries in self._channels.values()
                for message in entries
            ]

        writer = InboxWriter(wow_path)

        return writer.send_batch(combined)

    # --------------------------------------------------

    def clear(self, channel: str) -> bool:
        """
        Einen Kanal leeren, ohne die übrigen anzutasten.
        """

        return self.publish(channel, [])
