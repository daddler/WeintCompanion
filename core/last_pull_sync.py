"""
Den letzten Pull beim Bot abholen.

Die HTTP-Hälfte zu `core/last_pull.py`, getrennt aus demselben Grund
wie bei `raid_schedule_sync` und `warcraftlogs_client`: die Rechnung
soll ohne Netz prüfbar bleiben.

Beantwortet wird die Frage, an der die Übersicht bis 2.0.6 scheiterte:
*Was war mein letzter Pull?* - und zwar auch dann, wenn er gestern
war und die App seither neu gestartet wurde.

Vier Eigenheiten, die alle mit dem Preis des Abrufs zu tun haben:

- **Zwei Listen, kein Pull.** Berichtsliste und Fightliste sind je
  eine WarcraftLogs-Abfrage; der einzelne Pull dagegen liest die
  vollständigen Ereignisströme und kostet den Bot Minuten
  (`FIGHT_TIMEOUT` in `warcraftlogs_archive_client`). Was die Karte
  zeigt - Boss, Ausgang, Dauer, Pullnummer, die Kurve der letzten
  Versuche - steht bereits in der Fightliste. Der teure Abruf bleibt
  dem Archivmodus vorbehalten, wo ihn jemand ausdrücklich anfordert.
- **Alle zwanzig Minuten, nicht alle fünf Sekunden.** Ein
  abgeschlossener Pull ändert sich nicht mehr, und selbst während
  eines Raids ist ein Pull kein Minutentakt.
- **Ein Fehlschlag löscht nichts.** Der zuletzt bekannte Pull bleibt
  stehen; er wird durch einen nicht erreichbaren Bot nicht falsch.
  Auch eine **leere** Berichtsliste räumt ihn nicht weg - die Liste
  ist auf die letzten Wochen begrenzt, und ein Raid, der aus ihr
  herausfällt, hat trotzdem stattgefunden.
- **Ohne Berechtigung wird nicht weiter gefragt.** Das Archiv setzt
  eine Rolle im Discord voraus. Wer sie nicht hat, bekäme sonst alle
  zwanzig Minuten dieselbe abschlägige Antwort; ein Merker beendet
  die Versuche für diese Sitzung.

Der Abruf läuft im Sync-Worker mit, also **im selben Thread wie die
übrigen Absender** - und das ist eine bewusste Abwägung, keine
Nachlässigkeit: die beiden Listen haben zusammen bis zu 80 Sekunden
Zeitgrenze (`TIMEOUT` je Anfrage), und so lange ruht der Zyklus im
schlimmsten Fall. Er läuft deshalb als **letzter** Schritt, höchstens
alle zwanzig Minuten und nur mit verknüpftem Konto. Ein eigener
Thread wäre der erste im Zyklus und müsste sein Ergebnis wieder
einsammeln; was er einspart, ist eine Verzögerung an einer Zustellung,
die das Addon ohnehin erst beim nächsten Anmelden liest.
"""

from __future__ import annotations

import json
import time

from core.last_pull import LastPull, parse_last_pull
from core.paths import Paths
from core.warcraftlogs_archive_client import WarcraftLogsArchiveClient


REFRESH_SECONDS = 1200

CACHE_FILE = "last_pull.json"

#
# Wie viele Berichte höchstens durchgesehen werden, bis einer einen
# Bosskampf enthält. Der neueste ist fast immer der richtige; ein
# Bericht, der nur aus Trash besteht (die Fightliste verwirft ihn,
# siehe `build_fight_list`), darf die Karte aber nicht dauerhaft leer
# lassen. Drei ist die Grenze, ab der die Suche teurer wäre als ihr
# Ertrag.
#

MAX_REPORTS = 3


class LastPullSync:

    def __init__(self, manager, client=None):

        self.manager = manager

        self.client = client or WarcraftLogsArchiveClient()

        self.pull = self._load_cached()

        #
        # `None` heißt "noch nie", und das ist nicht dasselbe wie
        # "vor null Sekunden": `time.monotonic()` zählt ab dem Start
        # des Rechners. Wer die App kurz nach dem Hochfahren öffnet,
        # hätte mit einer Null als Startwert die ersten zwanzig
        # Minuten keinen Abruf - und die Übersicht sagte so lange, es
        # gebe keinen Pull.
        #

        self._last_fetch = None

        #
        # Gesetzt, sobald der Bot die Berechtigung verweigert hat.
        # Dieselbe Haltung wie beim 404 des Terminendpunkts: kein
        # Fehler, nur nichts zu holen.
        #

        self._denied = False

    # --------------------------------------------------

    def _cache_path(self):

        return Paths.cache() / CACHE_FILE

    def _load_cached(self) -> LastPull:

        path = self._cache_path()

        if not path.exists():
            return LastPull()

        try:

            return parse_last_pull(
                json.loads(path.read_text(encoding="utf-8"))
            )

        except Exception:

            #
            # Eine unlesbare Datei ist kein Grund, den Start zu
            # verhindern - der nächste Abruf schreibt sie neu.
            #

            return LastPull()

    def _store(self, data: dict):

        try:

            path = self._cache_path()

            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )

        except OSError as exc:

            self.manager.logger.warning(
                f"Letzter Pull konnte nicht gespeichert werden: {exc}"
            )

    # --------------------------------------------------

    def invalidate(self):
        """
        Den nächsten `process()` wirklich abrufen lassen - für den
        Knopf "Erneut prüfen" und nach einer Kontoänderung.
        """

        self._last_fetch = None

        self._denied = False

    def process(self):

        if self._denied:
            return

        if not self.client.is_linked():
            return

        now = time.monotonic()

        if (
            self._last_fetch is not None
            and now - self._last_fetch < REFRESH_SECONDS
        ):
            return

        self._last_fetch = now

        reports = self.client.fetch_reports()

        if not reports.ok:

            #
            # `logger.info` und nicht `error`: der Bot ist regelmäßig
            # kurz nicht erreichbar, und ein roter Eintrag alle zwanzig
            # Minuten für eine Nebensache wäre Lärm.
            #

            self.manager.logger.info(
                f"Letzter Pull nicht abrufbar: {reports.reason}"
            )

            self._deny_if_forbidden(reports.reason)

            return

        for report in reports.reports[:MAX_REPORTS]:

            fights = self.client.fetch_fights(report.code)

            if not fights.ok:

                self.manager.logger.info(
                    f"Pull-Liste nicht abrufbar: {fights.reason}"
                )

                self._deny_if_forbidden(fights.reason)

                return

            if not fights.fights:
                continue

            self._adopt(report, fights.fights)

            return

    # --------------------------------------------------

    def _deny_if_forbidden(self, reason: str):
        """
        Fehlende Berechtigung ist ein Dauerzustand, kein Ausfall.

        Der Client übersetzt jeden Fehler in einen deutschen Satz und
        gibt den Statuscode nicht weiter; erkannt wird der Fall
        deshalb am Text, den `WarcraftLogsArchiveClient` für 403 und
        für ein fehlendes Konto selbst setzt. Er steht an genau einer
        Stelle drüben - und ein verpasster Treffer kostet hier nur den
        nächsten vergeblichen Versuch in zwanzig Minuten, nicht die
        Anzeige.
        """

        text = (reason or "").lower()

        if "berechtigung" in text or "verknüpfung" in text:
            self._denied = True

    def _adopt(self, report, fights):

        payload = {
            "report": {
                "code": report.code,
                "title": report.title,
                "zone": report.zone,
                "start": report.start,
            },
            "fights": [
                {
                    "id": fight.fight_id,
                    "encounter_id": fight.encounter_id,
                    "name": fight.encounter_name,
                    "kill": fight.kill,
                    "boss_percentage": fight.boss_percentage,
                    "duration": fight.duration,
                    "pull_number": fight.pull_number,

                    #
                    # Als Name, nicht als `difficulty_id`: die Zahl
                    # ist beim Einlesen schon übersetzt worden und
                    # ließe sich nicht zurückrechnen (siehe
                    # `parse_last_pull`).
                    #

                    "difficulty_name": fight.difficulty,
                }
                for fight in fights
            ],
        }

        pull = parse_last_pull(payload)

        changed = (
            pull.boss != self.pull.boss
            or pull.pull_number != self.pull.pull_number
            or pull.report_code != self.pull.report_code
        )

        self.pull = pull

        self._store(payload)

        if changed and pull.known:

            self.manager.logger.success(
                f"Letzter Pull übernommen: {pull.boss}."
            )
