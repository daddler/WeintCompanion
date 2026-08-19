"""
Die gemeinsame WeakAura-Bibliothek beim Bot abholen.

Bis 2.1.0 half eine eingetragene Aura genau einer Person: der, die sie
getippt hat. Wer sie im Raid brauchte, bekam sie weiterhin als
Zeichenkette in den Chat kopiert. Seit dem Bot die Bibliothek führt
(`services/weakaura_library.py` drüben), holt sie sich hier jede
verknüpfte Companion ab und stellt sie zusammen mit den eigenen Auren
ihrem WeintCodex zu.

Läuft im gewöhnlichen Sync-Takt mit, in eigenem `try/except` wie die
übrigen Absender. Vier Regeln, die nicht nach Geschmack sind:

- **Ein Fehlschlag löscht nichts.** `set_guild_auras()` wird nur mit
  einer *erfolgreichen* Antwort gerufen. Andernfalls verschwänden bei
  jeder Netzstörung sämtliche Gildenauren aus dem Spiel - und zwar
  ohne dass irgendwo etwas kaputt wäre.
- **Eine leere Antwort ist etwas anderes als keine Antwort.** Der Bot
  sagt mit HTTP 200 und `auras: []`, dass die Bibliothek leer ist,
  und dann *soll* geräumt werden: so verschwindet eine gelöschte oder
  gesperrte Aura. Nur `ok = False` lässt den Stand stehen.
- **Ohne verknüpftes Discord-Konto passiert nichts**, ohne eine
  einzige Fehlermeldung. Das ist der Normalzustand für jeden, der die
  Companion ohne Discord benutzt, und kein Fehler.
- **Nach einer Änderung wird sofort zugestellt.** Zwischen "der Bot
  hat eine neue Aura" und dem Addon liegt sonst bis zu ein
  Sync-Intervall plus ein `/reload` - und wer in dieser Zeit
  nachschaut, hält es für kaputt.

Der Abruf ist **träge**: alle `REFRESH_SECONDS`. Die Bibliothek ändert
sich ein paarmal im Monat; sie alle fünf Sekunden zu erfragen wäre
eine Anfrage je Sync-Takt für eine Auskunft, die tagelang dieselbe
bleibt - auf einem Bot mit 0,15 vCPU, der nebenbei die Anmelde-Klicks
des halben Raids beantwortet.
"""

from __future__ import annotations

import time

from core.weakaura_client import WeakAuraClient


REFRESH_SECONDS = 600


class WeakAuraGuildSync:

    def __init__(self, manager, store, client: WeakAuraClient | None = None):

        self.manager = manager

        self.store = store

        self.client = client or WeakAuraClient()

        #
        # `None` heißt "noch nie", und das ist nicht dasselbe wie "vor
        # null Sekunden": `time.monotonic()` zählt ab dem Start des
        # Rechners. Mit einer Null als Startwert bliebe auf einer
        # gerade hochgefahrenen Maschine der erste Abruf zehn Minuten
        # lang aus - dieselbe Falle wie bei `RaidScheduleSync`.
        #

        self._last_fetch = None

        #
        # Der Grund, warum zuletzt nichts geholt werden konnte. Die
        # Seite zeigt ihn; ohne ihn wäre eine leere Bibliothek nicht
        # von einem nicht erreichbaren Bot zu unterscheiden.
        #

        self.reason = ""

        self.unsupported = False

    # --------------------------------------------------

    def invalidate(self):
        """
        Den nächsten Sync-Takt sofort abholen lassen.

        Nach einer eigenen Freigabe: der Bot hat den Eintrag dann
        gerade angenommen, und die Bibliothek soll ihn zeigen, ohne
        dass jemand zehn Minuten wartet.
        """

        self._last_fetch = None

    # --------------------------------------------------

    def process(self, force: bool = False):

        if not self.client.own_discord_id():

            #
            # Kein verknüpftes Konto. Kein Fehler, keine Meldung - und
            # ausdrücklich auch kein Räumen: wer sein Konto trennt,
            # räumt über `clear_guild()` auf (siehe
            # CompanionManager), nicht über einen ausbleibenden
            # Abruf.
            #

            return False

        now = time.monotonic()

        if (
            not force
            and self._last_fetch is not None
            and now - self._last_fetch < REFRESH_SECONDS
        ):
            return False

        self._last_fetch = now

        result = self.client.fetch()

        self.reason = result.reason

        self.unsupported = result.unsupported

        if not result.ok:

            #
            # Stehen lassen, was da ist. Ein nicht erreichbarer Bot
            # ist keine Aussage darüber, was in der Bibliothek liegt.
            #

            return False

        if not self.store.set_guild_auras(result.auras):
            return False

        self.manager.logger.info(
            f"WeakAuras der Gilde: {len(result.auras)} Aura(s) übernommen."
        )

        #
        # Sofort weiterreichen ans Addon. Der Zusteller vergleicht
        # selbst und schreibt nur bei einer echten Änderung.
        #

        sync = getattr(self.manager, "weakaura_sync", None)

        if sync is not None:
            sync.publish_now()

        return True
