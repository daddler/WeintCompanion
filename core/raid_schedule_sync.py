"""
Den Raidtermin beim Bot abholen.

Die HTTP-Hälfte zu `core/raid_schedule.py` - getrennt aus demselben
Grund, aus dem `core/warcraftlogs_client.py` von
`analyzer/providers/warcraftlogs_payload.py` getrennt ist: die
Rechnung soll ohne Netz prüfbar bleiben.

Läuft im gewöhnlichen Sync-Takt mit, in eigenem `try/except` wie die
übrigen Absender. Vier Eigenheiten:

- **Das Ergebnis wird gespeichert** (`raid_schedule.json` unter
  `Paths.cache()`). Der Abruf braucht ein verknüpftes Konto und einen
  erreichbaren Bot; ohne Zwischenspeicher stünde die Übersicht bei
  jedem Start ein paar Sekunden lang auf "kein Termin bekannt" und
  offline dauerhaft. Der Termin ist reproduzierbar, gehört also unter
  `cache()` und nicht unter `config()`.
- **Ein Fehlschlag löscht nichts.** Ist der Bot kurz nicht erreichbar,
  bleibt der zuletzt bekannte Termin stehen - er wird dadurch nicht
  falsch. Nur eine ausdrückliche Antwort "kein Raid" räumt ihn weg.
- **Der Takt richtet sich nach dem Termin** (`refresh_interval()`).
  Der *Termin* ändert sich einmal pro Woche, der *Stand der
  Anmeldungen* ändert sich am Raidtag im Minutentakt - und genau dann
  sieht jemand hin. Ein fester Fünf-Minuten-Takt war deshalb an dem
  einen Abend, an dem die Karte zählt, zu langsam und die übrigen
  sechs Tage zu schnell.
- **`process()` meldet, ob sich etwas geändert hat.** Ohne diese
  Rückmeldung stand die frisch abgeholte Aufstellung zwar im Speicher,
  aber niemand zeichnete sie: `refresh()` der Übersicht hängt am
  Seitenwechsel und an `CompanionManager.state_changed`, und das kam
  nach dem Start nur noch auf Knopfdruck. Gemeldet wird die
  *Änderung*, nicht der Abruf - `state_changed` bei jedem Abruf hiesse,
  die sichtbare Seite ohne Anlass neu zu zeichnen.
"""

from __future__ import annotations

import json
import time

import httpx

from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore
from core.paths import Paths
from core.raid_schedule import RaidSchedule, parse_schedule


#
# Der Termin ändert sich im Minutentakt nicht - ein Abruf je Sync-Takt
# (5 s) wäre eine Anfrage alle fünf Sekunden für eine Auskunft, die
# sich einmal pro Woche ändert.
#

REFRESH_SECONDS = 300

#
# Am Raidtag ist es umgekehrt: dann ändert sich zwar nicht der Termin,
# aber der Stand der Anmeldungen - und das ist die Auskunft, wegen der
# jemand kurz vor dem Raid überhaupt auf die Übersicht sieht. Wer fünf
# Minuten alte Zahlen sieht, während in Discord gerade jemand absagt,
# hält die Karte für kaputt.
#

REFRESH_SECONDS_SOON = 60

#
# Wie lange vor dem Termin der schnellere Takt gilt. Sechs Stunden
# decken den Nachmittag vor einem Abendraid ab, ohne dass der ganze
# Vortag mitzählt.
#

SOON_MINUTES = 6 * 60

TIMEOUT = 10

CACHE_FILE = "raid_schedule.json"


def refresh_interval(schedule, now=None) -> int:
    """
    Wie viele Sekunden bis zum nächsten Abruf.

    Rein und ohne Netz, aus demselben Grund wie `parse_schedule()`
    selbst: *wann* gefragt wird, ist eine Rechnung, und eine Rechnung
    soll ohne laufende Anwendung prüfbar sein.

    Der schnellere Takt gilt vom Vorlauf (`SOON_MINUTES`) bis zum Ende
    des laufenden Raids - `is_running()` zieht die hintere Grenze, denn
    solange gespielt wird, ändern sich Ersatzbank und Absagen weiter.
    Ohne bekannten Termin bleibt es beim trägen Takt: für eine Auskunft,
    die es nicht gibt, lohnt kein Minutentakt.
    """

    day = schedule.next_day(now) if schedule is not None else None

    if day is None:
        return REFRESH_SECONDS

    if day.is_running(now):
        return REFRESH_SECONDS_SOON

    minutes = day.minutes_until(now)

    if minutes is not None and 0 < minutes <= SOON_MINUTES:
        return REFRESH_SECONDS_SOON

    return REFRESH_SECONDS


def _appointment_keys(schedule) -> tuple:
    """
    Der Termin ohne die Anmeldezahlen - Kennung und Startzeitpunkt je
    Tag. Grundlage des Logeintrags, siehe `process()`.
    """

    return tuple(
        (day.key, day.starts_at)
        for day in getattr(schedule, "days", ())
    )


class RaidScheduleSync:

    def __init__(self, manager):

        self.manager = manager

        self.account_store = DiscordAccountStore()

        self.schedule = self._load_cached()

        #
        # `None` heißt "noch nie", und das ist nicht dasselbe wie "vor
        # null Sekunden": `time.monotonic()` zählt ab dem Start des
        # Rechners. Wer die App kurz nach dem Hochfahren öffnet, hätte
        # mit einer Null als Startwert die ersten fünf Minuten keinen
        # Abruf - und die Übersicht trüge so lange "kein Termin
        # bekannt".
        #

        self._last_fetch = None

    # --------------------------------------------------

    def _cache_path(self):

        return Paths.cache() / CACHE_FILE

    def _load_cached(self) -> RaidSchedule:

        path = self._cache_path()

        if not path.exists():
            return RaidSchedule()

        try:

            return parse_schedule(
                json.loads(path.read_text(encoding="utf-8"))
            )

        except Exception:

            #
            # Eine unlesbare Datei ist kein Grund, den Start zu
            # verhindern - der nächste Abruf schreibt sie neu.
            #

            return RaidSchedule()

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
                f"Raidtermin konnte nicht gespeichert werden: {exc}"
            )

    # --------------------------------------------------

    def invalidate(self):
        """
        Den nächsten Aufruf von `process()` wirklich abrufen lassen -
        für den Knopf "Erneut prüfen" und nach einer Kontoänderung.
        """

        self._last_fetch = None

    def process(self) -> bool:
        """
        Gibt zurück, ob sich der bekannte Stand geändert hat - der
        Sync-Takt macht daraus ein `state_changed`, und erst das
        zeichnet die Aufstellung neu. Ein Abruf ohne inhaltliche
        Änderung meldet bewusst `False`.
        """

        account = self.account_store.load()

        if not account or not account.get("companion_token"):
            return False

        now = time.monotonic()

        if (
            self._last_fetch is not None
            and now - self._last_fetch < refresh_interval(self.schedule)
        ):
            return False

        self._last_fetch = now

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}/companion/raid-schedule",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=TIMEOUT,
            )

        except Exception as exc:

            #
            # Kein `logger.error`: der Bot ist regelmäßig kurz nicht
            # erreichbar, und ein roter Eintrag alle fünf Minuten für
            # eine Nebensache wäre Lärm. Der zuletzt bekannte Termin
            # bleibt stehen.
            #

            self.manager.logger.info(
                f"Raidtermin nicht abrufbar: {exc}"
            )

            return False

        if response.status_code == 404:

            #
            # Ältere Bot-Fassung: den Endpunkt gibt es dort nicht. Die
            # Übersicht sagt dann weiter "kein Termin bekannt", genau
            # wie bisher.
            #

            return False

        if response.status_code != 200:

            self.manager.logger.info(
                "Raidtermin nicht abrufbar "
                f"({response.status_code})."
            )

            return False

        try:
            data = response.json()

        except ValueError:
            return False

        schedule = parse_schedule(data)

        #
        # Verglichen wird der **ganze** Stand, nicht mehr nur
        # `known`/`days`/`title`: auf der Karte stehen auch
        # `signup_status` (geschlossene Anmeldung), `composition` (der
        # Sollbestand je Rolle), `raid_size` und die Zeile über
        # parallele Raids (`others`). Ändert sich einer davon allein,
        # war die Karte bisher stumm - und dass die Anmeldung
        # geschlossen wurde, ist genau die Auskunft, wegen der jemand
        # hinsieht. `RaidSchedule` ist eingefroren, der Vergleich also
        # ein Feldvergleich und kein Verweisvergleich.
        #

        changed = schedule != self.schedule

        #
        # Der Logeintrag hängt dagegen weiter am **Termin** und nicht
        # am Stand der Anmeldungen. Sonst stünde am Raidtag, wo alle
        # sechzig Sekunden gefragt wird, für jede einzelne Zu- oder
        # Absage eine Zeile "Raidtermin übernommen" im Protokoll.
        #

        appointment = (
            schedule.known != self.schedule.known
            or schedule.title != self.schedule.title
            or _appointment_keys(schedule) != _appointment_keys(self.schedule)
        )

        self.schedule = schedule

        self._store(data)

        if appointment and schedule.known:

            self.manager.logger.success(
                f"Raidtermin übernommen: {schedule.title}."
            )

        return changed
