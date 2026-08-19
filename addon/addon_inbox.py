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

Geschrieben wird die Vereinigung seit 2.3.0 auf ZWEI Wegen, und der
zweite ist der wichtigere: die SavedVariable ist nur beim Login des
Spielers zuverlässig, weil WoW sie bei /reload und beim Abmelden aus
dem Arbeitsspeicher zurückschreibt und dabei alles vernichtet, was
wir während der Sitzung hineingeschrieben haben. Die Live-Brücke
(addon/live_bridge.py, eine Lua-Datei im Addon-Ordner) hat das
Problem nicht. Beide bekommen denselben Inhalt; welcher gilt,
entscheidet das Addon.
"""

from __future__ import annotations

import threading

from addon.inbox_writer import InboxWriter
from addon.live_bridge import LiveBridgeWriter


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

        Gibt True zurück, wenn mindestens einer der beiden Wege ins
        Addon geschrieben werden konnte. False heißt nur "weder
        SavedVariables-Datei noch Addon-Ordner gefunden" (WoW noch nie
        gestartet, Addon nicht installiert, falscher Pfad) - kein
        Fehler, für den es etwas zu melden gäbe.
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

        saved_variables = InboxWriter(wow_path).send_batch(combined)

        #
        # Die Live-Brücke ist der Weg, der eine laufende Sitzung
        # erreicht. Sie wird deshalb auch dann geschrieben, wenn die
        # SavedVariables-Datei fehlt (WoW nach der Addon-Installation
        # noch nie gestartet) - und umgekehrt.
        #

        live = LiveBridgeWriter(wow_path).write(combined)

        return saved_variables or live

    # --------------------------------------------------

    def reassert(self) -> bool:
        """
        Die aktuelle Vereinigung erneut hinausschreiben, ohne dass ein
        Absender etwas Neues zu sagen hätte.

        Läuft einmal pro Sync-Zyklus und ist fast immer ein Vergleich
        ohne Schreibvorgang. Nötig ist sie trotzdem, weil die Datei im
        Addon-Ordner uns nicht allein gehört: ein Addon-Update entpackt
        den leeren Auslieferungsstand darüber. Ohne diesen Durchlauf
        bliebe die Zustellung danach so lange verschwunden, bis sich
        beim Bot inhaltlich etwas ändert - die Absender schicken einen
        unveränderten Stand nicht noch einmal.

        Ohne belegten Kanal passiert nichts. Eine leere Vereinigung zu
        schreiben würde eine gültige Zustellung des vorherigen
        App-Starts wegnehmen, bevor die Absender ihren ersten Zyklus
        hinter sich haben.
        """

        with self._lock:

            if not self._channels:
                return False

            combined = [
                message
                for entries in self._channels.values()
                for message in entries
            ]

        wow_path = self.manager.state.wow_path

        if wow_path is None:
            return False

        return LiveBridgeWriter(wow_path).write(combined)

    # --------------------------------------------------

    def clear(self, channel: str) -> bool:
        """
        Einen Kanal leeren, ohne die übrigen anzutasten.
        """

        return self.publish(channel, [])
