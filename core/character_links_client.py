"""
HTTP-Hälfte der Charakterzuordnung.

Gegenstück zu core/character_links.py (rein), dasselbe Muster wie
WarcraftLogsArchiveClient: Basis-URL aus core/backend_config.py,
Authentifizierung über den gespeicherten `companion_token`, und **keine
Ausnahme verlässt diese Klasse** - jeder Fehlerfall wird zu einem
Ergebnis mit erklärendem `reason`, der unverändert in der Oberfläche
stehen kann.

Der 403-Fall ist hier kein Fehler, sondern eine Antwort: die drei
Endpunkte verlangen die Raidlead-Rolle (sie nennen Charakternamen samt
Discord-IDs des ganzen Rosters). Er kommt deshalb als eigenes Feld
zurück, damit die Seite erklären kann, wofür sie da wäre, statt eine
Störung zu melden.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from core.backend_config import BOT_BASE_URL
from core.character_links import Overview, parse_overview
from core.discord_account import DiscordAccountStore


ENDPOINT = "/companion/character-links"


#
# Die Antwort ist eine Datenbankabfrage plus ein Blick in den
# Discord-Cache - kein WarcraftLogs dahinter, also keine Minuten wie
# im Archiv. Trotzdem großzügiger als ein Klick-Timeout: der Bot läuft
# auf 0,15 vCPU und beantwortet nebenbei die Anmelde-Klicks des
# halben Raids.
#

TIMEOUT = 20.0


@dataclass(frozen=True)
class WriteResult:
    """Ergebnis eines Schreibvorgangs."""

    ok: bool = False

    #
    # Der gespeicherte Stand, wie der Bot ihn zurückmeldet - nicht das,
    # was gesendet wurde. Er zerlegt "Njiah-OokOok" in Name und Realm
    # und entfernt Zeichen, die das Importformat zerlegen würden;
    # angezeigt wird deshalb seine Fassung.
    #

    character: str = ""

    reason: str = ""


class CharacterLinksClient:

    def __init__(self, account_store: DiscordAccountStore | None = None):

        self.account_store = account_store or DiscordAccountStore()

    # --------------------------------------------------
    # Gemeinsamer HTTP-Teil
    # --------------------------------------------------

    def _request(self, method: str, payload: dict | None = None):
        """
        Liefert (status, body, reason). `status` ist -1 bei einem
        Netzwerkfehler, `body` dann None.
        """

        account = self.account_store.load()

        if not account or not account.get("companion_token"):

            return -1, None, (
                "Kein Discord-Konto verknüpft - die Zuordnung läuft "
                "über den Bot."
            )

        try:

            response = httpx.request(
                method,
                f"{BOT_BASE_URL}{ENDPOINT}",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                json=payload,
                timeout=TIMEOUT,
            )

        except httpx.TimeoutException:

            return -1, None, (
                "Der Bot hat nicht rechtzeitig geantwortet. Läuft er "
                "gerade neu an, hilft ein zweiter Versuch."
            )

        except Exception as exc:

            return -1, None, f"Bot nicht erreichbar: {exc}"

        if response.status_code == 401:

            #
            # Dieselbe Behandlung wie in den anderen Clients: ein vom
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
                "Der Bot hat die Verknüpfung abgelehnt - bitte Discord "
                "in den Einstellungen erneut verbinden."
            )

        if response.status_code == 403:

            return 403, None, (
                "Für die Charakterzuordnung ist die Raidlead-Rolle im "
                "Discord nötig."
            )

        if response.status_code == 404:

            return 404, None, (
                "Dieser Bot kennt die Charakterzuordnung noch nicht - "
                "er läuft auf einem älteren Stand."
            )

        if response.status_code != 200:

            return response.status_code, None, (
                f"Der Bot antwortete mit HTTP {response.status_code}"
                + (f": {_detail_of(response)}" if _detail_of(response) else ".")
            )

        try:
            body = response.json()

        except ValueError:

            return 200, None, "Die Antwort des Bots war kein gültiges JSON."

        if not isinstance(body, dict):

            return 200, None, "Die Antwort des Bots hatte ein unerwartetes Format."

        return 200, body, ""

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def fetch(self) -> Overview:

        status, body, reason = self._request("GET")

        if body is None:
            return Overview(reason=reason, forbidden=status == 403)

        return parse_overview(body)

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def set_link(
        self,
        discord_id: str,
        character: str,
        class_token: str | None = None,
    ) -> WriteResult:
        """
        Ordnet einem Discord-Account einen Charakter zu.

        `discord_id` reist als **Zeichenkette**, aus demselben Grund
        wie `community.id` im Zugriffsprofil: eine Discord-Snowflake
        sprengt die Zahlengenauigkeit von JSON und käme als
        `1.23e+18` an.

        `class_token` leer heißt "gilt für jede Klasse, mit der sich
        der Account anmeldet" - die Notlösung für Spieler mit genau
        einem Charakter.
        """

        character = (character or "").strip()

        if not character:
            return WriteResult(reason="Bitte einen Charakternamen eingeben.")

        status, body, reason = self._request("POST", {
            "discord_id": str(discord_id),
            "character": character,
            "class": (class_token or "").strip().upper(),
        })

        if body is None:
            return WriteResult(reason=reason)

        link = body.get("link") or {}

        from core.character_links import format_character

        return WriteResult(
            ok=True,
            character=format_character(link.get("name"), link.get("realm")),
        )

    def remove_link(
        self,
        discord_id: str,
        class_token: str | None = None,
    ) -> WriteResult:
        """
        Entfernt eine Zuordnung. Ohne `class_token` fallen **alle**
        Handeinträge dieses Accounts weg - derselbe Gedanke wie beim
        Discord-Befehl: der Anlass ist "der Spieler meldet seine
        Twinks jetzt selbst", und dann darf kein vergessener
        Klasseneintrag seine Meldung weiter überschatten.
        """

        payload = {"discord_id": str(discord_id)}

        if class_token:
            payload["class"] = class_token.strip().upper()

        status, body, reason = self._request("DELETE", payload)

        if body is None:
            return WriteResult(reason=reason)

        return WriteResult(ok=True)


def _detail_of(response) -> str:

    try:
        detail = response.json().get("detail")
    except Exception:
        return ""

    return str(detail) if detail else ""
