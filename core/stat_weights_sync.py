"""
Die Sim-Gewichte ins Addon stellen.

Dieselbe Bauform wie `core/weakaura_sync.py`: ein eigener Kanal in der
Inbox, zugestellt wird die **ganze Liste**, geschrieben nur, wenn sich
inhaltlich etwas geändert hat.

Gelesen wird sie im Spiel beim Login bzw. nach `/reload` - WoW liest
seine SavedVariables zur Laufzeit nicht erneut. Genau deshalb gibt es
den zweiten Weg daneben: `stat_weights.build_transfer()` erzeugt einen
`WCIMPORT:SW:`-String, den man ohne Neuladen ins Spiel einfügt. Die
Seite sagt beides, damit niemand vergeblich sucht.

Drei Dinge, die nicht nach Geschmack sind:

* **Eine leer gewordene Liste wird zugestellt, nicht ausgelassen**
  (`_delivered_once`). Wer seine letzte Gewichtung löscht, will sie im
  Spiel loswerden; ohne diese Zustellung bliebe genau die eine stehen,
  die weg sollte. Wer die Seite nie benutzt hat, belegt dagegen keinen
  Kanal.
* **Der Fingerabdruck bleibt bei einem fehlgeschlagenen Schreiben
  unangetastet.** `publish()` meldet `False`, wenn keine
  SavedVariables-Datei gefunden wurde (WoW nie gestartet, falscher
  Pfad). Würde der Merker trotzdem gesetzt, gälte die Zustellung als
  erledigt und käme nie nach - dieselbe Regel wie in
  `core/addon_analysis_sync.py`.
* **Zugestellt wird ein Vorschlag, keine Einstellung.** Im Spiel füllt
  er die Felder auf *Priorisierung* und wird erst auf Klick wirksam.
  Das ist keine Vorsicht um ihrer selbst willen: dieselbe Regel gilt
  dort für einen von Hand eingefügten Text, und eine Gewichtung, die
  sich nach einem Login von selbst geändert hat, wäre von einem Fehler
  nicht zu unterscheiden.
"""

from __future__ import annotations

import threading

from core.lua_table import to_lua
from core.stat_weights import payload as build_payload


class StatWeightsSync:

    CHANNEL = "statweights"

    def __init__(self, manager, inbox, store):

        self.manager = manager

        self.inbox = inbox

        self.store = store

        self._fingerprint = None

        #
        # Vergleich und Schreiben gehören zusammen: `publish_now()`
        # läuft aus dem GUI-Thread, `process()` aus dem SyncThread.
        #

        self._lock = threading.Lock()

        self._delivered_once = False

    # --------------------------------------------------

    def invalidate(self):

        with self._lock:
            self._fingerprint = None

    def publish_now(self):
        """
        Sofort zustellen, statt auf den Sync-Takt zu warten.

        Wird aus der Oberfläche gerufen, wenn eine Gewichtung
        übernommen oder gelöscht wurde. Ein Fehler darf den Aufrufer
        nicht mitreissen - er wollte nur auf einen Knopf drücken.
        """

        self.invalidate()

        try:
            self.process()

        except Exception as exc:

            self.manager.logger.error(
                f"Sim-Gewichte: Zustellung fehlgeschlagen: {exc}"
            )

    # --------------------------------------------------

    def process(self):

        entries = self.store.delivery()

        if not entries and not self._delivered_once:
            return

        payload = build_payload(entries)

        fingerprint = to_lua(payload)

        with self._lock:

            if fingerprint == self._fingerprint:
                return

            messages = [
                {
                    "type": "stat_weights",
                    "payload": payload,
                }
            ]

            if not self.inbox.publish(self.CHANNEL, messages):
                return

            self._fingerprint = fingerprint

            self._delivered_once = True

        self.manager.logger.success(
            f"Sim-Gewichte: {len(entries)} Gewichtung(en) an das Addon "
            f"übergeben - im Spiel nach dem nächsten /reload."
        )
