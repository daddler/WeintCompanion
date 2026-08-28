"""
Abruf vergangener WarcraftLogs-Berichte beim WeintCodex-Bot.

Gegenstück zu core/warcraftlogs_client.py, das nur den gerade
laufenden Livelog kennt. Diese Klasse bedient den "Archiv"-Modus von
WeintTV/WeintAcademy: Report auswählen, Pull darin auswählen, dessen
Fight-Daten abrufen. Der letzte Schritt liefert bewusst dieselbe
JSON-Form wie der Live-Endpunkt (siehe docs/warcraftlogs-bridge.md),
damit analyzer/providers/warcraftlogs_payload.py's
snapshot_from_payload() unverändert wiederverwendet werden kann -
nur mit live=False.

Dasselbe Muster wie WarcraftLogsClient: Basis-URL aus
core/backend_config.py, Authentifizierung über den gespeicherten
`companion_token`, keine Ausnahme verlässt diese Klasse - jeder
Fehlerfall wird zu einem Ergebnis mit erklärendem `reason`-Text, der
unverändert in der Oberfläche erscheinen kann.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from analyzer.providers.warcraftlogs import FetchResult
from analyzer.providers.warcraftlogs_payload import (
    FightSummary,
    ReportSummary,
    build_fight_list,
    build_report_list,
)
from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore


REPORTS_ENDPOINT = "/companion/warcraftlogs/reports"

#
# Die drei Zeitgrenzen sind nach dem bemessen, was der Bot für die
# jeweilige Antwort tatsächlich tun muss - nicht nach einem
# einheitlichen "das reicht schon".
#
# Report- und Fightliste sind je eine einzige WarcraftLogs-Abfrage.
# Dass sie trotzdem mehr als 15 Sekunden bekommen, liegt an der
# Zeitgrenze auf der anderen Seite: der Bot wartet selbst bis zu 30
# Sekunden auf WarcraftLogs. Wer früher aufgibt, bekommt nie die
# Erklärung des Bots zu sehen ("WarcraftLogs hat nicht rechtzeitig
# geantwortet"), sondern immer nur die eigene Zeitüberschreitung -
# also ausgerechnet in dem Fall, in dem die Ursache woanders liegt,
# die unbrauchbarste Meldung.
#

TIMEOUT = 40.0

#
# Ein einzelner Pull ist keine Liste, sondern das Gesamtbild eines
# Kampfes: der Bot liest dafür die vollständigen Ereignisströme
# (Zauber, Auren, erlittener Schaden) - in einem beobachteten Fall
# über 30.000 Ereignisse, seitenweise geholt und auf 0,15 vCPU
# ausgewertet. Das dauert Minuten, nicht Sekunden.
#
# Mit den früheren 15 Sekunden war der Ausgang damit vorherbestimmt:
# die App gab auf, während der Bot noch arbeitete, und meldete "Bot
# nicht erreichbar: The read operation timed out" neben dem
# Wiedergabe-Knopf. Schlimmer noch, jeder Versuch begann von vorn.
#

FIGHT_TIMEOUT = 180.0

#
# Die Zeitleiste bekommt am meisten Zeit.
#
# Sie enthält für jeden der 25 Spieler mehrere Reihen mit einem Wert
# je Sekunde, und der Bot setzt sie aus denselben Ereignisströmen wie
# den Pull zusammen, zuzüglich Schaden und Heilung - der mit Abstand
# teuerste Abruf der ganzen Brücke.
#

TIMELINE_TIMEOUT = 240.0


#
# --------------------------------------------------
# Ergebnisse
# --------------------------------------------------
#


def _detail_of(response) -> str:
    """
    Der `detail`-Text einer Fehlerantwort des Bots, sofern vorhanden.

    Wirft nie: eine Fehlerantwort muss kein JSON sein (ein Proxy oder
    uvicorn selbst antwortet mit HTML), und dann bleibt es eben bei
    der Statuszeile.
    """

    try:
        body = response.json()

    except Exception:
        return ""

    if not isinstance(body, dict):
        return ""

    return str(body.get("detail") or "").strip()


@dataclass(frozen=True)
class ReportsFetchResult:

    reports: tuple[ReportSummary, ...] = ()

    reason: str = ""

    @property
    def ok(self) -> bool:

        return not self.reason


@dataclass(frozen=True)
class FightsFetchResult:

    fights: tuple[FightSummary, ...] = ()

    reason: str = ""

    @property
    def ok(self) -> bool:

        return not self.reason


class WarcraftLogsArchiveClient:
    """
    Liest Report- und Fight-Listen sowie einzelne vergangene Fights
    beim Bot.
    """

    def __init__(self, account_store=None):

        self.account_store = account_store or DiscordAccountStore()

    # --------------------------------------------------

    def is_linked(self) -> bool:

        account = self.account_store.load()

        return bool(
            account
            and account.get("companion_token")
        )

    # --------------------------------------------------
    # Roher Abruf
    # --------------------------------------------------

    def _get(self, path: str, timeout: float = TIMEOUT):
        """
        Gemeinsamer HTTP-Teil aller Endpunkte.

        Liefert (status_code, body, reason). `status_code` ist -1
        bei einem Netzwerkfehler; `body` ist dann None. Ein
        fehlendes/ungültiges Token liefert das gemeinsame
        401-Verhalten bereits hier, da es für alle drei Endpunkte
        identisch ist.
        """

        account = self.account_store.load()

        if not account or not account.get("companion_token"):

            return -1, None, (
                "Kein Discord-Konto verknüpft - die Verbindung "
                "läuft über den Bot."
            )

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}{path}",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                timeout=timeout,
            )

        except httpx.TimeoutException:

            #
            # Nicht die Ausnahme durchreichen: httpx meldet hier "The
            # read operation timed out" - englisch, technisch, und vor
            # allem ohne den einen Hinweis, der weiterhilft, nämlich
            # dass ein zweiter Versuch schneller ist (der Bot hält das
            # Ergebnis eines fertig gerechneten Pulls einige Minuten
            # vor).
            #

            return -1, None, (
                "Der Bot hat nicht rechtzeitig geantwortet. Bei einem "
                "großen Pull kann die Auswertung beim Bot länger "
                "dauern - ein erneuter Versuch ist meist deutlich "
                "schneller."
            )

        except Exception as exc:

            return -1, None, f"Bot nicht erreichbar: {exc}"

        if response.status_code == 401:

            #
            # Dieselbe Behandlung wie in WarcraftLogsClient: ein vom
            # Bot wiederholt abgelehntes Token wird lokal aufgehoben,
            # statt bei jedem weiteren Versuch erneut zu scheitern.
            #
            #
            # Nicht beim ersten Mal aufheben: siehe
            # AUTH_REJECTIONS_BEFORE_UNLINK und
            # AUTH_REJECTION_COOLDOWN in core/discord_account.py.
            # Ein einzelnes 401 kann ein gerade neu startender Bot
            # sein; erst mehrere, die weit genug auseinanderliegen,
            # heissen, dass er dieses Token wirklich nicht mehr kennt
            # - ein Abruf, der im Takt wiederholt wird, ist ein
            # Vorfall und nicht drei.
            #

            self.account_store.note_auth_rejected()

            return 401, None, (
                "Der Bot hat die Verknüpfung abgelehnt - bitte "
                "Discord in den Einstellungen erneut verbinden."
            )

        if response.status_code == 403:

            return 403, None, (
                "Keine Berechtigung für das Log-Archiv - dafür ist "
                "eine Rolle im Discord nötig."
            )

        if response.status_code != 200:

            #
            # Den Grund des Bots mitnehmen, wenn er einen nennt: die
            # Archiv-Endpunkte antworten bei einem Problem mit
            # WarcraftLogs mit 502 und einem `detail`, das die
            # eigentliche Ursache benennt ("WarcraftLogs hat nicht
            # rechtzeitig geantwortet"). Ohne das stand in der
            # Oberfläche nur die nackte Zahl, und die Ursache blieb
            # allein im Bot-Terminal sichtbar.
            #

            return response.status_code, None, (
                f"Der Bot antwortete mit HTTP {response.status_code}"
                + (f": {_detail_of(response)}" if _detail_of(response) else ".")
            )

        try:
            body = response.json()

        except ValueError:

            return 200, None, "Die Antwort des Bots war kein gültiges JSON."

        if not isinstance(body, dict):

            return 200, None, (
                "Die Antwort des Bots hatte ein unerwartetes Format."
            )

        return 200, body, ""

    # --------------------------------------------------
    # Report-Liste
    # --------------------------------------------------

    def fetch_reports(self) -> ReportsFetchResult:

        status, body, reason = self._get(REPORTS_ENDPOINT)

        if body is None:
            return ReportsFetchResult(reason=reason)

        return ReportsFetchResult(reports=build_report_list(body))

    # --------------------------------------------------
    # Fight-Liste eines Reports
    # --------------------------------------------------

    def fetch_fights(self, report_code: str) -> FightsFetchResult:

        if not report_code:

            return FightsFetchResult(
                reason="Kein Bericht ausgewählt.",
            )

        status, body, reason = self._get(
            f"{REPORTS_ENDPOINT}/{report_code}/fights"
        )

        if status == 404:

            return FightsFetchResult(
                reason="Dieser Bericht wurde nicht gefunden.",
            )

        if body is None:
            return FightsFetchResult(reason=reason)

        return FightsFetchResult(fights=build_fight_list(body))

    # --------------------------------------------------
    # Einzelner Fight
    # --------------------------------------------------

    def fetch_fight(self, report_code: str, fight_id: int) -> FetchResult:
        """
        Liefert dieselbe Ergebnisform wie WarcraftLogsClient.fetch() -
        ein FetchResult mit der rohen Bot-Antwort als `payload`, damit
        beide Wege (live und Archiv) durch dieselbe
        snapshot_from_payload()-Funktion laufen.
        """

        if not report_code:

            return FetchResult(
                reason="Kein Bericht ausgewählt.",
            )

        status, body, reason = self._get(
            f"{REPORTS_ENDPOINT}/{report_code}/fights/{fight_id}",
            timeout=FIGHT_TIMEOUT,
        )

        if status == 404:

            return FetchResult(
                reason="Dieser Pull wurde nicht gefunden.",
            )

        if body is None:
            return FetchResult(reason=reason)

        return FetchResult(payload=body)

    # --------------------------------------------------
    # Zeitleiste eines Fights (Wiedergabe)
    # --------------------------------------------------

    def fetch_timeline(self, report_code: str, fight_id: int) -> FetchResult:
        """
        Die Zeitleiste eines Pulls für die Wiedergabe.

        Bewusst ein eigener Endpunkt statt eines Zusatzfeldes am
        Einzel-Fight: die Antwort enthält Zeitreihen für jeden Spieler
        und ist damit deutlich größer als das Gesamtbild - sie wird
        nur beim Druck auf Wiedergabe gebraucht und soll nicht jeden
        Archiv-Klick verteuern.

        Ergebnisform wie bei fetch_fight(): ein FetchResult mit der
        rohen Antwort, das analyzer.replay.payload übersetzt.
        """

        if not report_code:

            return FetchResult(
                reason="Kein Bericht ausgewählt.",
            )

        status, body, reason = self._get(
            f"{REPORTS_ENDPOINT}/{report_code}/fights/{fight_id}/timeline",
            timeout=TIMELINE_TIMEOUT,
        )

        if status == 404:

            return FetchResult(
                reason="Für diesen Pull liefert der Bot keine Zeitleiste.",
            )

        if body is None:
            return FetchResult(reason=reason)

        return FetchResult(payload=body)
