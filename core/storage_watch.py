"""
Nachsehen, ob sich Downloads und Backups anhäufen - ohne dass jemand
danach fragt.

Dieselbe Bauform wie `core/update_watch.py` und aus demselben Grund:
die Zahlen standen seit jeher auf *Einstellungen → Backups*, aber
dorthin geht niemand, der nichts sucht. Gemeldet wurde nie etwas, und
gelöscht wird nichts von selbst - nach einem halben Jahr Releases
liegen zwei Dutzend Dateien da, die niemand vermisst und die niemand
kennt.

Vier Dinge daran sind nicht Geschmack:

- **Gemeldet wird die Änderung, nicht die Zählung.** `process()`
  vergleicht die beiden Zahlen und antwortet nur dann mit `True`,
  wenn sich etwas bewegt hat. `state_changed` bei jedem Takt hiesse,
  die sichtbare Seite alle fünf Sekunden neu zu zeichnen.
- **Gezählt wird träge.** Ein Ordner voller Dateien ändert sich nur,
  wenn eine Aktualisierung läuft oder jemand aufräumt - beides meldet
  sich über `invalidate()` selbst. `REFRESH_SECONDS` fängt nur den
  Rest ab (jemand löscht im Dateimanager).
- **Der Merker beginnt bei `None`, nicht bei null.**
  `time.monotonic()` zählt ab dem Start des Rechners; eine Null als
  Startwert hiesse auf einem frisch hochgefahrenen Rechner "vor
  wenigen Sekunden gezählt", und die erste Zählung fiele aus.
  Dieselbe Falle wie bei `UpdateWatch` und `RaidScheduleSync`.
- **Der Bericht ist nie `None`.** Vor der ersten Zählung steht der
  leere Bericht da (`empty_report()`), sonst müsste jede lesende
  Stelle den Unterschied zwischen "noch nicht gezählt" und "nichts da"
  behandeln - und beide verlangen dasselbe, nämlich keine Meldung.
"""

from __future__ import annotations

import time

from core import storage_usage
from core.paths import Paths


#
# Fünf Minuten. Das Zählen selbst kostet nichts (ein `iterdir()` über
# eine Handvoll Dateien), aber es gibt auch nichts zu erfahren: die
# beiden Ordner ändern sich durch eine Aktualisierung oder durch das
# Aufräumen, und beide Wege rufen `invalidate()`.
#

REFRESH_SECONDS = 300


class StorageWatch:

    def __init__(self, logger=None):

        self.logger = logger

        self.report = storage_usage.empty_report()

        self._last_check = None

    # --------------------------------------------------

    def invalidate(self):
        """
        Beim nächsten Takt neu zählen.

        Gerufen, wenn sich einer der beiden Ordner nachweislich
        geändert hat: nach einer Installation (neues Backup, neues
        Archiv) und nach dem Aufräumen auf der Einstellungsseite.
        """

        self._last_check = None

    # --------------------------------------------------

    def refresh(self) -> bool:
        """
        Sofort zählen, unabhängig vom Takt. Gibt zurück, ob sich die
        Antwort geändert hat.
        """

        before = self.report.signature

        try:

            self.report = storage_usage.scan(
                Paths.downloads(),
                Paths.backups(),
            )

        except Exception as exc:

            #
            # Zählen darf nie der Grund sein, aus dem ein Sync-Takt
            # abbricht: der Bericht bleibt dann eben der von vorhin.
            #

            if self.logger is not None:

                self.logger.info(
                    f"Speicherplatz konnte nicht gezählt werden: {exc}"
                )

            return False

        self._last_check = time.monotonic()

        return self.report.signature != before

    # --------------------------------------------------

    def process(self) -> bool:

        now = time.monotonic()

        if (
            self._last_check is not None
            and now - self._last_check < REFRESH_SECONDS
        ):
            return False

        return self.refresh()
