"""
Nach einer neuen Fassung sehen, ohne dass jemand danach fragt.

Bis 2.3.2 wurde genau zweimal geprüft: einmal beim Start
(`full_refresh()` im InitThread) und danach nur noch auf Knopfdruck
("Erneut prüfen"). Wer die Anwendung morgens öffnet und abends damit
raidet, erfuhr von einer mittags veröffentlichten Fassung nichts -
und zwar nicht, weil die Anzeige fehlte, sondern weil niemand mehr
nachgefragt hat. Alle drei Stellen, die ein wartendes Update ansagen
(die Systemzeile der Übersicht, das Abzeichen in der
Navigationsspalte, die Meldung unten rechts), hängen an
`CompanionManager.state_changed` - und das kam nach dem Start nur noch,
wenn der Nutzer den Knopf drückte, den er dafür erst einmal suchen
musste.

Diese Klasse ist der fehlende dritte Auslöser. Sie läuft im
gewöhnlichen Sync-Takt mit (eigener `try/except` wie jeder andere
Schritt), prüft aber nur alle `REFRESH_SECONDS`, und ihr Rückgabewert
sagt, ob die Oberfläche etwas nachzuziehen hat.

Vier Dinge daran sind nicht Geschmack:

- **Gemeldet wird die Änderung, nicht die Prüfung.** `state_changed`
  bei jedem Takt hiesse, die sichtbare Seite alle fünf Sekunden neu zu
  zeichnen - und `MainWindow._announce_updates()` bei jeder Prüfung
  erneut zu durchlaufen. Verglichen wird deshalb die *Antwort*
  (Fassungen und beide "steht bereit"-Marken), nicht der Zeitpunkt.
- **Die Zwischenspeicher werden vorher verworfen.** `GitHubUpdater`
  hält seine Antwort 15 Minuten; ohne das Verwerfen käme bei einem
  gleich langen Takt regelmässig die gespeicherte Antwort zurück, und
  die Prüfung wäre eine, die nie etwas Neues erfahren kann. Dieselbe
  Überlegung wie bei `refresh_update_status()`, nur ohne Nutzer davor.
- **Der Merker beginnt bei `None`, nicht bei null.**
  `time.monotonic()` zählt ab dem Start des Rechners, eine Null als
  Startwert hiesse also auf einem frisch hochgefahrenen Rechner "vor
  wenigen Sekunden geprüft". Gesetzt wird er hier über
  `note_checked()`, das `full_refresh()` und `refresh_update_status()`
  nach ihrer eigenen Prüfung aufrufen - sonst liefe fünf Sekunden nach
  dem Start sofort eine zweite Runde gegen GitHub.
- **Geprüft wird laut, berichtet wird leise.** Der Fund einer neuen
  Fassung steht im Protokoll, der Vollzug einer Prüfung nicht - sonst
  stünde dort alle fünfzehn Minuten viermal, dass alles beim Alten
  ist. Dafür nehmen `check_github()` und `check_for_update()` ein
  `quiet`.
- **Die installierte Fassung wird mitgelesen.** Ein Update kann auch
  dadurch verschwinden, dass das Addon von aussen aktualisiert wurde
  (ein zweiter Rechner, ein Addon-Manager). `detect_addon()` gehört
  deshalb in dieselbe Runde - sonst stünde "Update verfügbar", bis die
  Anwendung neu gestartet wird.
"""

from __future__ import annotations

import time


#
# Eine Viertelstunde. Dasselbe Mass, mit dem `GitHubUpdater` seine
# Antwort zwischenspeichert: häufiger zu fragen hiesse, GitHub für
# eine Auskunft zu belasten, die sich dort selten am Tag ändert - und
# seltener zu fragen hiesse, dass eine Fassung stundenlang bereitliegt,
# ohne dass es jemand erfährt. Zwei Anfragen je Viertelstunde (Addon
# und Companion) liegen weit unter dem, was GitHub ohne Anmeldung
# zulässt.
#

REFRESH_SECONDS = 900


class UpdateWatch:

    def __init__(self, manager):

        self.manager = manager

        self._last_check = None

    # --------------------------------------------------

    def note_checked(self):
        """
        Eine Prüfung, die woanders gelaufen ist, mitzählen.

        `full_refresh()` und `refresh_update_status()` fragen dieselben
        beiden Endpunkte ab; ohne diesen Vermerk würde der Sync-Takt
        gleich danach ein zweites Mal losziehen.
        """

        self._last_check = time.monotonic()

    def invalidate(self):
        """
        Die nächste Runde wirklich prüfen lassen.
        """

        self._last_check = None

    # --------------------------------------------------

    def _signature(self):
        """
        Was die Oberfläche über wartende Updates anzeigt.

        Bewusst auch die *Fassungen* und nicht nur die beiden Marken:
        erscheint bei liegengebliebenem Update eine noch neuere
        Version, soll die Meldung erneut kommen - genau danach
        entscheidet `MainWindow._announce_updates()`.
        """

        state = self.manager.state

        return (
            state.addon_version,
            state.github_version,
            state.update_available,
            state.companion_latest_version,
            state.companion_update_available,
        )

    # --------------------------------------------------

    def process(self) -> bool:
        """
        Prüfen, wenn der Takt es hergibt. Gibt zurück, ob sich an der
        Antwort etwas geändert hat.
        """

        now = time.monotonic()

        if (
            self._last_check is not None
            and now - self._last_check < REFRESH_SECONDS
        ):
            return False

        self._last_check = now

        before = self._signature()

        #
        # Siehe Kopf: ohne dieses Verwerfen antwortet der
        # Zwischenspeicher, und die Prüfung erführe nie etwas Neues.
        #

        self.manager.github.invalidate_cache()

        self.manager.companion_updater.github.invalidate_cache()

        self.manager.detect_addon()

        #
        # `quiet`: dieselbe Prüfung, aber ohne die Zeilen, die nur den
        # Vollzug melden. Alle fünfzehn Minuten "WeintCodex ist
        # aktuell." und "Companion ist aktuell." ins Protokoll zu
        # schreiben, machte aus der Protokollseite eine Liste von
        # Nichtereignissen - und ein unerreichbares GitHub ist hier
        # keine Störung, sondern der Normalfall eines Rechners, der
        # gerade offline ist. Ein *Fund* wird auch leise gemeldet.
        #

        self.manager.check_github(quiet=True)

        self.manager.companion_updater.check_for_update(quiet=True)

        return self._signature() != before
