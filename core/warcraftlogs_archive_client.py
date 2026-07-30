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

TIMEOUT = 15.0


#
# --------------------------------------------------
# Ergebnisse
# --------------------------------------------------
#


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

    def _get(self, path: str):
        """
        Gemeinsamer HTTP-Teil aller drei Endpunkte.

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
                timeout=TIMEOUT,
            )

        except Exception as exc:

            return -1, None, f"Bot nicht erreichbar: {exc}"

        if response.status_code == 401:

            #
            # Dieselbe Behandlung wie in WarcraftLogsClient: ein vom
            # Bot abgelehntes Token wird lokal sofort aufgehoben,
            # statt bei jedem weiteren Versuch erneut zu scheitern.
            #

            self.account_store.clear()

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

            return response.status_code, None, (
                f"Der Bot antwortete mit HTTP {response.status_code}."
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
            f"{REPORTS_ENDPOINT}/{report_code}/fights/{fight_id}"
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
            f"{REPORTS_ENDPOINT}/{report_code}/fights/{fight_id}/timeline"
        )

        if status == 404:

            return FetchResult(
                reason="Für diesen Pull liefert der Bot keine Zeitleiste.",
            )

        if body is None:
            return FetchResult(reason=reason)

        return FetchResult(payload=body)
