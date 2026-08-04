"""
Stellt dem Addon das Zugriffsprofil zu (WeintCodex ab 1.2.0.0).

Der Bot kennt die Discord-Rollen, die Companion nicht: sie haelt nur
die Identitaet und ein undurchsichtiges companion_token. Deshalb holt
dieser Sender die Rollennamen bei GET /companion/access-profile ab und
bildet sie hier auf Rang und Freigaben ab (core/access_roles.py).

Der Endpunkt existiert im Bot noch nicht zwangslaeufig. Genau wie bei
den WarcraftLogs-Bruecken gilt: fehlt er, wird nichts zugestellt und
nichts gemeldet - das Addon verhaelt sich dann wie vor 1.2.0.0, also
vollstaendig offen. Der Vertrag steht in docs/access-profile-bridge.md.
"""

from __future__ import annotations

import time

import httpx

from core.access_roles import DEFAULT_ROLE_MAP, build_profile_payload
from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore
from core.version import VERSION


ENDPOINT = "/companion/access-profile"


class AccessProfileSync:

    def __init__(self, manager, inbox):

        self.manager = manager
        self.inbox = inbox
        self.account_store = DiscordAccountStore()

        #
        # Verhindert, dass bei jedem Sync-Zyklus dasselbe Profil neu
        # geschrieben wird. Das Addon nimmt ein Profil mit gleichem
        # issuedAt zwar an, aber die Inbox-Datei liegt in WoWs
        # SavedVariables - jeder Schreibvorgang ist ein
        # Datei-Ersetzen, das nichts bringt, wenn sich nichts geaendert
        # hat.
        #

        self._last_fingerprint = None

        #
        # Der Endpunkt fehlt im Bot moeglicherweise noch. Dann soll
        # genau einmal etwas im Log stehen und danach Ruhe sein, nicht
        # alle fuenf Sekunden dieselbe Zeile.
        #

        self._missing_logged = False

    # --------------------------------------------------

    def _role_map(self):

        configured = self.manager.config.data.get("access_role_map")

        if isinstance(configured, dict) and configured:
            return configured

        return DEFAULT_ROLE_MAP

    # --------------------------------------------------

    def _fetch(self, token):

        try:

            response = httpx.get(
                f"{BOT_BASE_URL}{ENDPOINT}",
                headers={
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
            )

        except Exception as exc:

            self.manager.logger.error(
                f"Zugriffsprofil-Abruf fehlgeschlagen: {exc}"
            )

            return None

        #
        # 404: Endpunkt im Bot (noch) nicht vorhanden.
        # 401/403: kein verknuepfter Account bzw. keine Berechtigung.
        # Beides ist kein Fehler, fuer den es etwas zu melden gaebe -
        # ohne Profil bleibt im Addon alles offen wie bisher.
        #

        if response.status_code == 404:

            if not self._missing_logged:

                self._missing_logged = True

                self.manager.logger.info(
                    "Zugriffsprofil: Der Bot stellt noch keine "
                    "Rolleninformationen bereit - im Addon bleiben alle "
                    "Bereiche offen."
                )

            return None

        if response.status_code in (401, 403):
            return None

        if response.status_code != 200:

            self.manager.logger.error(
                f"Zugriffsprofil-Abruf fehlgeschlagen "
                f"({response.status_code})."
            )

            return None

        try:

            return response.json()

        except Exception as exc:

            self.manager.logger.error(
                f"Zugriffsprofil konnte nicht gelesen werden: {exc}"
            )

            return None

    # --------------------------------------------------

    def build_payload(self, data):
        """
        Duenner Mantel um core.access_roles.build_profile_payload():
        holt Zuordnung, Version und Uhrzeit dazu und schreibt einen
        Fehlgrund ins Log. Die Abbildung selbst ist dort, weil sie ohne
        Netzzugriff testbar bleiben soll.

        Gibt (payload, matched_roles) zurueck; payload ist None, wenn
        nichts zugestellt werden soll.
        """

        payload, matched, error = build_profile_payload(
            data,
            role_map=self._role_map(),
            version=VERSION,
            now=time.time(),
        )

        if error:

            self.manager.logger.error(
                f"Zugriffsprofil: {error} Es wird kein Profil zugestellt - "
                f"im Addon bleiben alle Bereiche offen."
            )

        return payload, matched

    # --------------------------------------------------

    def process(self):

        account = self.account_store.load()

        if not account or not account.get("companion_token"):
            return

        data = self._fetch(account["companion_token"])

        if data is None:
            return

        payload, matched = self.build_payload(data)

        if payload is None:
            return

        #
        # Alles ausser issuedAt: der Zeitstempel aendert sich bei jedem
        # Abruf und wuerde die Erkennung "hat sich nichts geaendert"
        # sonst wirkungslos machen.
        #

        fingerprint = (
            payload["community"]["id"],
            payload["tier"],
            tuple(sorted(payload["features"].items())),
            payload["expiresAt"],
            payload.get("notice", ""),
        )

        if fingerprint == self._last_fingerprint:
            return

        #
        # Ueber die gemeinsame Inbox, nicht direkt ueber den Writer:
        # Roster- und Auswertungs-Sync stellen im selben Durchlauf
        # ebenfalls zu, und ein direktes send_batch() wuerde deren
        # Nachrichten mitloeschen (siehe addon/addon_inbox.py).
        #

        delivered = self.inbox.publish("access", [
            {
                "type": "access_profile",
                "payload": payload,
                "community": payload["community"]["id"],
            },
        ])

        if not delivered:
            return

        self._last_fingerprint = fingerprint

        self.manager.logger.success(
            f"Zugriffsprofil an das Addon uebergeben: "
            f"{payload['tierLabel']}"
            + (f" (Rollen: {', '.join(matched)})" if matched else "")
        )
