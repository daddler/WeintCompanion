"""
Die Zielausrüstung ins Addon stellen.

Dieselbe Bauform wie `core/stat_weights_sync.py`: ein eigener Kanal in
der Inbox, zugestellt wird die **ganze Liste**, geschrieben nur, wenn
sich inhaltlich etwas geändert hat.

Gelesen wird sie im Spiel beim Login bzw. nach `/reload` - WoW liest
seine SavedVariables zur Laufzeit nicht erneut. Genau deshalb gibt es
den zweiten Weg daneben: `target_gear.build_transfer()` erzeugt einen
`WCIMPORT:TG:`-String, den man ohne Neuladen ins Spiel einfügt.

Drei Dinge, die nicht nach Geschmack sind - alle drei aus demselben
Grund wie bei den Sim-Gewichten:

* **Eine leer gewordene Liste wird zugestellt, nicht ausgelassen**
  (`_delivered_once`). Wer seine letzte Zielausrüstung löscht, will sie
  im Spiel loswerden.
* **Der Fingerabdruck bleibt bei einem fehlgeschlagenen Schreiben
  unangetastet**, sonst gälte die Zustellung als erledigt und käme nie
  nach.
* **Zugestellt wird ein Zielzustand, keine Einstellung.** Im Spiel
  ändert er die *Empfehlungen* auf den Seiten Sockel und Umschmieden -
  er legt nichts an und schmiedet nichts. Was der Spieler tut,
  entscheidet weiterhin der Spieler.
"""

from __future__ import annotations

import threading

from core.lua_table import to_lua
from core.target_gear import payload as build_payload


class TargetGearSync:

    CHANNEL = "targetgear"

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
        Sofort zustellen, statt auf den Sync-Takt zu warten. Ein Fehler
        darf den Aufrufer nicht mitreissen - er wollte nur auf einen
        Knopf drücken.
        """

        self.invalidate()

        try:
            self.process()

        except Exception as exc:

            self.manager.logger.error(
                f"Zielausrüstung: Zustellung fehlgeschlagen: {exc}"
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
                    "type": "target_gear",
                    "payload": payload,
                }
            ]

            if not self.inbox.publish(self.CHANNEL, messages):
                return

            self._fingerprint = fingerprint

            self._delivered_once = True

        self.manager.logger.success(
            f"Zielausrüstung: {len(entries)} Sim-Ergebnis(se) an das "
            "Addon übergeben - im Spiel nach dem nächsten /reload."
        )
