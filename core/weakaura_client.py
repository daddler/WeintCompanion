"""
HTTP-Hälfte der gemeinsamen WeakAura-Bibliothek.

Gegenstück zu `core/weakaura_library.py` (rein) und `weakaura_store.py`
(Platte), dasselbe Muster wie `CharacterLinksClient`: Basis-URL aus
`core/backend_config.py`, Authentifizierung über den gespeicherten
`companion_token`, und **keine Ausnahme verlässt diese Klasse** - jeder
Fehlerfall wird zu einem Ergebnis mit erklärendem `reason`, der
unverändert in der Oberfläche stehen kann.

Zwei Antworten des Bots sind hier keine Störung, sondern Auskunft, und
reisen deshalb als eigene Felder:

* **409** heißt: die Kennung gehört einer Aura von jemand anderem. Die
  Seite bietet daraufhin an, unter einer neuen Kennung freizugeben -
  aus einem 400 ("dein String ist kaputt") wäre das nicht zu
  unterscheiden, und der Bot benennt von sich aus nichts um, weil dann
  eine zweite Aura entstünde, die aussieht wie die erste.
* **403** heißt: das ist die Aura eines anderen, dafür braucht es die
  Raidleitung. Auch das ist eine Antwort und keine Fehlfunktion.

**404 heißt "der Bot ist älter als diese Funktion"** und ist der
freundliche Fall: die Bibliothek gibt es dann eben nicht, alles
Lokale läuft unverändert weiter. Dieselbe "gracefully unavailable"-
Linie wie beim Zugriffsprofil und der WarcraftLogs-Brücke.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from core.backend_config import BOT_BASE_URL
from core.discord_account import DiscordAccountStore
from core.weakaura_library import WeakAura, SCOPE_GUILD, normalize_category


ENDPOINT = "/companion/weakauras"


#
# Die Antwort ist eine Datenbankabfrage - kein WarcraftLogs dahinter,
# also keine Minuten wie im Archiv. Trotzdem großzügiger als ein
# Klick-Timeout: der Bot läuft auf 0,15 vCPU und beantwortet nebenbei
# die Anmelde-Klicks des halben Raids. Beim Schreiben kommt die
# Sicherung nach Discord dazu (eine Nachricht mit Anhang), deshalb
# dort mehr.
#

TIMEOUT = 20.0

WRITE_TIMEOUT = 45.0


@dataclass(frozen=True)
class LibraryResult:
    """
    Was der Bot über die Bibliothek weiß.

    `ok = False` mit leerem `reason` gibt es nicht: wenn nichts
    geholt werden konnte, steht hier immer, warum - sonst ließe sich
    eine leere Bibliothek nicht von einer nicht erreichbaren
    unterscheiden.
    """

    ok: bool = False

    auras: tuple[WeakAura, ...] = ()

    reason: str = ""

    #
    # Der Bot kennt die Bibliothek nicht (404). Kein Fehler, nur ein
    # älterer Stand - die Oberfläche sagt das in eigenen Worten.
    #

    unsupported: bool = False


@dataclass(frozen=True)
class WriteResult:

    ok: bool = False

    #
    # Der gespeicherte Stand, wie der Bot ihn zurückmeldet - nicht
    # das, was gesendet wurde. Er vergibt bei `rename` eine neue
    # Kennung, und angezeigt wird seine Fassung.
    #

    aura: WeakAura | None = None

    reason: str = ""

    #
    # Die Kennung gehört jemand anderem (409). Die Seite bietet dann
    # "unter neuer Kennung freigeben" an.
    #

    conflict: bool = False

    forbidden: bool = False

    unsupported: bool = False


def _detail_of(response) -> str:

    try:
        body = response.json()

    except ValueError:
        return ""

    if isinstance(body, dict):
        return str(body.get("detail") or "")

    return ""


def aura_from_bot(raw: dict, own_id: str = "") -> WeakAura | None:
    """
    Eine Zeile der Bibliothek in die Form dieser Anwendung bringen.

    `own_id` ist die eigene Discord-ID: daran entscheidet sich, ob der
    Eintrag hier bearbeitet werden darf oder ob er jemand anderem
    gehört (`foreign`).
    """

    if not isinstance(raw, dict):
        return None

    identifier = str(raw.get("id") or "").strip()

    body = str(raw.get("string") or "")

    if not identifier or not body:
        return None

    author_id = str(raw.get("author_id") or "")

    return WeakAura(
        id=identifier,
        name=str(raw.get("name") or identifier),
        category=normalize_category(raw.get("category")),
        description=str(raw.get("description") or ""),
        version=str(raw.get("version") or "1.0"),
        author=str(raw.get("author") or ""),
        icon=str(raw.get("icon") or ""),
        string=body,
        updated_at=int(raw.get("updated_at") or 0),
        scope=SCOPE_GUILD,
        author_id=author_id,
        foreign=bool(own_id) and author_id != own_id,
    )


class WeakAuraClient:

    def __init__(self, account_store: DiscordAccountStore | None = None):

        self.account_store = account_store or DiscordAccountStore()

    # --------------------------------------------------

    def own_discord_id(self) -> str:
        """
        Die eigene Discord-ID, oder "" ohne Verknüpfung.

        Sie entscheidet, welche Einträge der Bibliothek hier
        bearbeitbar sind. Ohne sie gilt alles als fremd - das ist die
        vorsichtige Richtung: ein Knopf, der beim Drücken 403 sagt,
        ist schlechter als keiner.
        """

        #
        # `discord_id` ist das Feld, das der Bot bei
        # /companion/auth/exchange zurueckgibt und das in
        # discord_account.json landet; `id` steht daneben nur als
        # Rueckfall fuer eine aeltere Datei.
        #

        account = self.account_store.load() or {}

        return str(account.get("discord_id") or account.get("id") or "")

    # --------------------------------------------------

    def _request(self, method: str, path: str = "", payload: dict | None = None):
        """
        Liefert (status, body, reason). `status` ist -1 bei einem
        Netzwerkfehler, `body` dann None.
        """

        account = self.account_store.load()

        if not account or not account.get("companion_token"):

            return -1, None, (
                "Kein Discord-Konto verknüpft - die gemeinsame "
                "Bibliothek läuft über den Bot."
            )

        try:

            response = httpx.request(
                method,
                f"{BOT_BASE_URL}{ENDPOINT}{path}",
                headers={
                    "Authorization": f"Bearer {account['companion_token']}",
                },
                json=payload,
                timeout=TIMEOUT if method == "GET" else WRITE_TIMEOUT,
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
            # Bot wiederholt abgelehntes Token wird lokal aufgehoben.
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
                _detail_of(response)
                or "Diese Aura gehört jemand anderem - dafür braucht es "
                   "die Raidleitung."
            )

        if response.status_code == 404:

            return 404, None, (
                "Dieser Bot kennt die gemeinsame Bibliothek noch nicht - "
                "er läuft auf einem älteren Stand."
            )

        if response.status_code == 409:

            return 409, None, (
                _detail_of(response)
                or "Diese Kennung ist in der Bibliothek schon vergeben."
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

    def fetch(self) -> LibraryResult:

        status, body, reason = self._request("GET")

        if body is None:
            return LibraryResult(reason=reason, unsupported=status == 404)

        own = self.own_discord_id()

        auras = tuple(
            aura
            for aura in (
                aura_from_bot(raw, own) for raw in body.get("auras") or []
            )
            if aura is not None
        )

        return LibraryResult(ok=True, auras=auras)

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def publish(self, aura: WeakAura, rename: bool = False) -> WriteResult:
        """
        Eine Aura freigeben oder die eigene ersetzen.

        `rename` ist die Antwort auf einen 409 und wird nur gesetzt,
        wenn der Nutzer sie ausdrücklich gewählt hat.
        """

        payload = {
            "id": aura.id,
            "name": aura.name,
            "category": aura.category,
            "string": aura.string,
            "description": aura.description,
            "version": aura.version,
            "icon": aura.icon,
        }

        if rename:
            payload["rename"] = True

        status, body, reason = self._request("POST", payload=payload)

        if body is None:

            return WriteResult(
                reason=reason,
                conflict=status == 409,
                forbidden=status == 403,
                unsupported=status == 404,
            )

        return WriteResult(
            ok=True,
            aura=aura_from_bot(body.get("aura") or {}, self.own_discord_id()),
        )

    def moderate(self, aura_id: str, **fields) -> WriteResult:
        """
        Rubrik, Name, Beschreibung, Version oder Sperre einer
        vorhandenen Aura ändern.

        Der Importstring ist bewusst nicht dabei - wer ihn ersetzen
        will, gibt die Aura neu frei und ist damit als Urheber der
        neuen Fassung sichtbar. Dieselbe Regel gilt am Bot.
        """

        payload = {key: value for key, value in fields.items() if value is not None}

        status, body, reason = self._request(
            "PATCH",
            path=f"/{aura_id}",
            payload=payload,
        )

        if body is None:

            return WriteResult(
                reason=reason,
                forbidden=status == 403,
                unsupported=status == 404,
            )

        return WriteResult(
            ok=True,
            aura=aura_from_bot(body.get("aura") or {}, self.own_discord_id()),
        )

    def withdraw(self, aura_id: str) -> WriteResult:
        """
        Aus der Bibliothek entfernen. Beim Autor die eigene, bei der
        Raidleitung jede.
        """

        status, body, reason = self._request("DELETE", path=f"/{aura_id}")

        if body is None:

            return WriteResult(
                reason=reason,
                forbidden=status == 403,
                unsupported=status == 404,
            )

        return WriteResult(ok=True)
