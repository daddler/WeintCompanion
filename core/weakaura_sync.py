"""
Die WeakAura-Bibliothek ins Addon stellen.

Die Gegenrichtung zu `core/weakaura_catalog_sync`-artigen Meldungen:
hier geht, was auf der Seite **WeakAuras** eingetragen wurde, als
Nachricht `weakaura_library` an das Addon. Gelesen wird sie dort beim
Login bzw. nach `/reload` (`ProcessInbox` in `modules/companion.lua`),
weil WoW seine SavedVariables zur Laufzeit nicht erneut liest. Eine
gerade eingetragene Aura ist im Spiel also nach dem nächsten `/reload`
da - so steht es auch auf der Seite, damit niemand vergeblich sucht.

Drei Dinge, die nicht nach Geschmack sind:

* **Zugestellt wird immer die ganze Liste.** Eine gelöschte Aura
  verschwindet im Spiel allein dadurch, dass sie in der nächsten
  Zustellung fehlt; eine Einzelnachricht könnte "es gibt mich nicht
  mehr" nicht ausdrücken, und die Inbox wird bei jedem Login geleert.
  Das Addon ersetzt seine Ablage deshalb, statt sie zu ergänzen.
* **Eine leere Bibliothek wird zugestellt, nicht ausgelassen.** Wer
  seine letzte Aura löscht, will sie im Spiel loswerden. Ohne diese
  Zustellung bliebe genau die eine Aura für immer stehen, die
  ausdrücklich weg sollte. Der Kanal wird deshalb erst dann geleert,
  wenn nie etwas darin lag.
* **Zugestellt wird `delivery()`, nicht `auras()`.** Also eigene *und*
  Gildenauren. Mit der eigenen Liste bekäme jemand, der selbst nichts
  eingetragen hat, aus der Bibliothek der Gilde nie etwas - obwohl sie
  voll ist und genau dafür da wäre.
* **Der Fingerabdruck bleibt bei einem fehlgeschlagenen Schreiben
  unangetastet.** `publish()` gibt `False` zurück, wenn keine
  SavedVariables-Datei gefunden wurde (WoW nie gestartet, falscher
  Pfad). Würde der Merker trotzdem gesetzt, gälte die Zustellung als
  erledigt und würde nie nachgeholt - dieselbe Regel wie in
  `core/addon_analysis_sync.py`.
"""

from __future__ import annotations

import threading

from core.lua_table import to_lua


class WeakAuraSync:

    CHANNEL = "weakauras"

    def __init__(self, manager, inbox, store):

        self.manager = manager
        self.inbox = inbox
        self.store = store

        #
        # Der zuletzt zugestellte Stand. Aura-Strings sind lang; sie
        # unverändert in jedem Sync-Takt erneut in WoWs
        # SavedVariables-Datei zu schreiben wäre reine Schreiblast
        # auf einer Datei, die auch den Spielstand trägt.
        #

        self._fingerprint = None

        #
        # Vergleich und Schreiben gehören zusammen: `publish_now()`
        # läuft aus dem GUI-Thread, `process()` aus dem SyncThread.
        # `AddonInbox` sperrt nur seine Kanaltabelle, nicht den
        # Dateizugriff.
        #

        self._lock = threading.Lock()

        #
        # Ob je etwas zugestellt wurde. Entscheidet darüber, ob eine
        # leere Bibliothek eine Löschung ist (dann zustellen) oder
        # schlicht der Normalfall bei jemandem, der die Seite nie
        # benutzt hat (dann nichts belegen).
        #

        self._delivered_once = False

    # --------------------------------------------------

    def invalidate(self):

        with self._lock:
            self._fingerprint = None

    def publish_now(self):
        """
        Sofort zustellen, statt auf den Sync-Takt zu warten.

        Wird aus der Oberfläche gerufen, wenn eine Aura gespeichert
        oder gelöscht wurde. Ein Fehler darf den Aufrufer nicht
        mitreissen - er wollte nur auf "Fertig" drücken.
        """

        self.invalidate()

        try:
            self.process()

        except Exception as exc:

            self.manager.logger.error(
                f"WeakAuras: Zustellung fehlgeschlagen: {exc}"
            )

    # --------------------------------------------------

    def process(self):

        #
        # `delivery()` und nicht `auras()`: zugestellt wird, was ins
        # Addon geht - eigene UND Gildenauren. Mit der eigenen Liste
        # bekäme jemand, der selbst nichts eingetragen hat, aus der
        # Bibliothek nie etwas, obwohl sie voll ist. Und die Meldung
        # im Protokoll nennte die falsche Zahl.
        #

        auras = self.store.delivery()

        if not auras and not self._delivered_once:
            return

        payload = self.store.payload(
            updated_at=max((aura.updated_at or 0) for aura in auras)
            if auras else 0
        )

        #
        # Verglichen wird das gerenderte Lua ohne den Zeitstempel:
        # er beschreibt, wann zuletzt getippt wurde, und ist für die
        # Frage "hat sich inhaltlich etwas geändert" ohne Belang.
        #

        fingerprint = to_lua({
            key: value
            for key, value in payload.items()
            if key != "updatedAt"
        })

        with self._lock:

            if fingerprint == self._fingerprint:
                return

            messages = [
                {
                    "type": "weakaura_library",
                    "payload": payload,
                }
            ]

            if not self.inbox.publish(self.CHANNEL, messages):
                return

            self._fingerprint = fingerprint

            self._delivered_once = True

        self.manager.logger.success(
            f"WeakAuras: {len(auras)} Aura(s) an das Addon übergeben "
            f"- im Spiel nach dem nächsten /reload."
        )
