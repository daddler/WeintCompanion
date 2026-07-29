"""
Raid-Daten aus einem WarcraftLogs-Livelog.

Sobald jemand im Raid mit dem Live-Logging beginnt, entsteht bei
WarcraftLogs ein fortlaufend ergänzter Bericht. Diese Quelle liest
ihn - allerdings nicht direkt: sie fragt den WeintCodex-Bot, der den
Bericht kennt (er sieht den Webhook im Discord), ihn abruft und in
der Form ausliefert, die docs/warcraftlogs-bridge.md festlegt.

Der Umweg über den Bot ist eine bewusste Entscheidung. Er hält die
WarcraftLogs-Zugangsdaten an einer Stelle statt auf fünfundzwanzig
Rechnern, teilt sich ein gemeinsames Anfragekontingent und erspart
jedem Raidmitglied die Einrichtung eines eigenen API-Zugangs.

Zwei Eigenschaften, die diese Quelle vom Combat-Log unterscheiden
und die die Oberfläche kennen muss:

* **Sie hinkt hinterher.** Der Uploader überträgt in Abständen; ein
  Wert ist typischerweise einige zehn Sekunden alt. Für Bossleben im
  Sekundentakt ist das zu langsam, für Ranglisten, Verlauf und die
  Academy völlig ausreichend.
* **Sie gilt für den ganzen Raid.** Anders als das lokale Log
  braucht sie nicht, dass ausgerechnet dieser Rechner mitschreibt -
  genau der Fall der Raidleitung, die selbst nicht loggt.

Der Abruf selbst wird als Callable hereingereicht (`fetch`), nicht
importiert. Dadurch bleibt der Analyzer frei von HTTP und Bot-Wissen,
und die Quelle ist ohne Netzwerk vollständig testbar. Verdrahtet wird
beides in core/raid_data_service.py.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from analyzer.models import RaidSnapshot
from analyzer.providers.base import RaidDataProvider
from analyzer.providers.warcraftlogs_payload import (
    report_label,
    snapshot_from_payload,
)


#
# --------------------------------------------------
# Ergebnis eines Abrufs
# --------------------------------------------------
#


@dataclass(frozen=True)
class FetchResult:
    """
    Was ein Abruf zurückgibt.

    `payload` ist die Antwort des Bots, oder None. `reason` erklärt
    in einem Satz, warum nichts vorliegt - dieser Text landet
    unverändert in der Statuszeile der Einstellungen und ist damit
    die einzige Fehlermeldung, die diese Quelle braucht. Deshalb ist
    er deutsch und an den Nutzer gerichtet, nicht an den Entwickler.
    """

    payload: dict | None = None

    reason: str = ""

    @property
    def ok(self) -> bool:

        return self.payload is not None


#
# Abstand zwischen zwei Abrufen beim Bot.
#
# Deutlich langsamer als der Poll-Takt des RaidDataService (1 s): ein
# Livelog wird ohnehin nur alle paar Sekunden ergänzt, häufiger zu
# fragen erzeugt Last beim Bot und bei WarcraftLogs, ohne einen
# einzigen neuen Wert zu liefern.
#

FETCH_INTERVAL = 15.0


#
# Ab wann ein zwischengespeicherter Bericht verworfen wird. Bleiben
# Abrufe längere Zeit erfolglos (Bot neu gestartet, Raid beendet),
# soll WeintTV nicht stundenlang denselben eingefrorenen Pull zeigen,
# als liefe er noch.
#

MAX_AGE = 180.0


class WarcraftLogsProvider(RaidDataProvider):
    """
    Liest den laufenden WarcraftLogs-Bericht über den Bot.
    """

    def __init__(
        self,
        fetch,
        fetch_interval: float = FETCH_INTERVAL,
        max_age: float = MAX_AGE,
    ):
        """
        `fetch` ist ein Callable ohne Argumente, das ein FetchResult
        liefert. Es darf blockieren und es darf werfen - beides
        behandelt diese Klasse.
        """

        self._fetch = fetch

        self._fetch_interval = max(1.0, fetch_interval)

        self._max_age = max_age

        self._lock = threading.Lock()

        self._payload: dict | None = None

        self._fetched_at = 0.0

        self._reason = ""

        self._running = False

        self._thread: threading.Thread | None = None

        #
        # Das Weck-Event für die AKTUELLE Generation - siehe start().
        # Nur als Platzhalter initialisiert; stop() vor dem ersten
        # start() (siehe RaidDataProvider-Vertrag: muss folgenlos
        # sein) darf kein None antreffen.
        #

        self._wake = threading.Event()

        #
        # Zählt jeden Start durch. Folgen stop() und start() dicht
        # aufeinander, darf der alte Worker nicht neben dem neuen
        # weiterlaufen. Ein Worker arbeitet deshalb nur, so lange
        # seine eigene Nummer noch die aktuelle ist.
        #
        # Das allein reicht aber nicht: die Prüfung passiert nur VOR
        # jedem wait()-Aufruf, nicht währenddessen. Bekäme jede
        # Generation dasselbe (wiederverwendete) Event-Objekt, könnte
        # start() es per clear() zurücksetzen, während der alte
        # Worker noch in dessen wait() hängt - genau das Signal, das
        # stop() ihm gerade geschickt hat, wäre dann ausgelöscht,
        # bevor er es sieht, und er bliebe bis zu fetch_interval lang
        # als Zombie-Thread übrig. Deshalb bekommt jede Generation ihr
        # EIGENES Event (siehe start()); es wird nie wiederverwendet
        # oder zurückgesetzt, ein einmal gesetztes Event bleibt daher
        # garantiert gesetzt, unabhängig von der Ausführungsreihenfolge.
        #

        self._generation = 0

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    def start(self) -> None:

        with self._lock:

            if self._running:
                return

            self._running = True

            self._generation += 1

            generation = self._generation

            #
            # Ein frisches Event statt clear() auf dem alten - siehe
            # die Erklärung bei self._generation in __init__.
            #

            wake = threading.Event()

            self._wake = wake

            self._reason = "Verbindung zum Bot wird aufgebaut ..."

        #
        # Eigener Thread statt eines Abrufs in snapshot(): der
        # RaidDataService fragt im Sekundentakt, ein HTTP-Aufruf kann
        # aber Sekunden dauern. Würde snapshot() blockieren, stünde
        # die gesamte Auswertung so lange still. So bleibt sie
        # jederzeit sofort auskunftsfähig - mit dem zuletzt bekannten
        # Stand.
        #

        self._thread = threading.Thread(
            target=self._worker,
            args=(generation, wake),
            daemon=True,
            name="WarcraftLogsFetch",
        )

        self._thread.start()

    def stop(self) -> None:

        with self._lock:

            if not self._running:
                return

            self._running = False

            self._payload = None

            self._fetched_at = 0.0

            self._reason = ""

            #
            # Dasselbe Event-Objekt, auf das der aktuell laufende
            # Worker wartet (self._wake wird nur in start() ersetzt,
            # und das erst beim nächsten Aufruf) - unter demselben
            # Lock gelesen, mit dem start() es setzt.
            #

            wake = self._wake

        #
        # Weckt den Worker sofort aus seiner Wartezeit, statt bis zum
        # Ablauf des Intervalls zu warten.
        #

        wake.set()

        self._thread = None

    # --------------------------------------------------
    # Abruf
    # --------------------------------------------------

    def _active(self, generation: int) -> bool:

        with self._lock:

            return self._running and self._generation == generation

    def _worker(self, generation: int, wake: threading.Event) -> None:

        while self._active(generation):

            self._fetch_once(generation)

            #
            # wait() statt sleep(): stop() beendet den Thread damit
            # unmittelbar. Bewusst das als Parameter übergebene Event
            # dieser Generation, nicht self._wake - ein zwischen-
            # zeitlicher Neustart ersetzt self._wake sonst durch das
            # Event der NÄCHSTEN Generation, auf das dieser (alte)
            # Worker gar nicht warten soll.
            #

            if wake.wait(self._fetch_interval):
                return

    def _fetch_once(self, generation: int) -> None:
        """
        Ein Abruf. Fehler werden zum Statustext, nicht zur Ausnahme -
        eine geworfene Ausnahme würde den Thread beenden und die
        Quelle dauerhaft stumm schalten.
        """

        try:
            result = self._fetch()

        except Exception as exc:

            result = FetchResult(
                reason=f"Abruf beim Bot fehlgeschlagen: {exc}",
            )

        if not isinstance(result, FetchResult):

            result = FetchResult(
                reason="Unerwartete Antwort der Abrufquelle.",
            )

        with self._lock:

            #
            # Ein zwischenzeitliches stop() (oder ein Neustart) darf
            # nicht durch ein noch laufendes Abrufergebnis
            # überschrieben werden.
            #

            if not self._running or self._generation != generation:
                return

            self._reason = result.reason

            if result.ok:

                self._payload = result.payload

                self._fetched_at = time.monotonic()

    # --------------------------------------------------
    # Beschreibung
    # --------------------------------------------------

    @property
    def source_label(self) -> str:

        return "WarcraftLogs"

    @property
    def live(self) -> bool:

        return True

    @property
    def status_text(self) -> str:

        with self._lock:

            payload = self._payload

            reason = self._reason

            age = self._age(payload)

        if payload is None:

            return reason or "Kein laufender Bericht."

        label = report_label(payload)

        parts = [part for part in (label,) if part]

        parts.append(f"zuletzt aktualisiert vor {int(age)} s")

        if reason:
            parts.append(reason)

        return " · ".join(parts)

    # --------------------------------------------------
    # Snapshot
    # --------------------------------------------------

    def _age(self, payload: dict | None) -> float:
        """
        Alter des zwischengespeicherten Berichts in Sekunden. Wird
        nur unter gehaltenem Lock aufgerufen.
        """

        if payload is None or not self._fetched_at:
            return 0.0

        return max(0.0, time.monotonic() - self._fetched_at)

    def snapshot(self) -> RaidSnapshot:

        with self._lock:

            payload = self._payload

            age = self._age(payload)

            #
            # Zu alt: der Bericht wird verworfen, statt einen längst
            # beendeten Pull weiter als aktuell auszugeben.
            #

            if payload is not None and age > self._max_age:

                self._payload = None

                payload = None

                self._reason = (
                    "Seit einiger Zeit keine neuen Daten - "
                    "läuft das Live-Logging noch?"
                )

        if payload is None:

            return RaidSnapshot.empty(self.source_label)

        try:

            return snapshot_from_payload(
                payload,
                self.source_label,
                age_seconds=age,
            )

        except Exception:

            #
            # Der Mapper ist gegen unvollständige Antworten gewappnet,
            # aber der Vertrag aus base.py gilt ausnahmslos: snapshot()
            # wirft nie. Lieber ein leeres Bild als eine Ausnahme im
            # Poll-Thread.
            #

            return RaidSnapshot.empty(self.source_label)
