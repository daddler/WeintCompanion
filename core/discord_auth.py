from __future__ import annotations

import http.server
import secrets
import urllib.parse

import httpx

from core.backend_config import BOT_BASE_URL
from core.browser import open_url
from core.net_errors import bot_unreachable_text, override_hint

# --------------------------------------------------
# Discord OAuth2 Konfiguration
# --------------------------------------------------
# CLIENT_ID ist öffentlich (steht ohnehin im Autorisierungs-Link, den
# der Browser aufruft) - anders als das Client-Secret, das
# ausschließlich serverseitig beim Bot liegt und den Code-Austausch
# durchführt (siehe WeintCodex-Bot: services/companion_auth.py).
#
# WICHTIG: REDIRECT_URI muss exakt der Redirect-URI entsprechen, die
# im Discord Developer Portal (Bot-Application -> OAuth2) hinterlegt
# ist UND die der Bot in der Umgebungsvariable DISCORD_REDIRECT_URI
# erwartet.

CLIENT_ID = "1501941067577298994"

REDIRECT_PORT = 53682
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"

DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"


class DiscordAuthError(Exception):
    pass


def parse_exchange_response(payload) -> dict:
    """
    Prüft die Antwort des Bots auf den Code-Austausch, bevor sie
    abgelegt wird.

    Bewusst rein und ausserhalb von `login()` - aus demselben Grund,
    aus dem `access_roles.build_profile_payload()` ohne `httpx`
    auskommt: die Entscheidung ist die Stelle, an der etwas falsch
    sein kann, und die soll ohne Netz und ohne Fenster prüfbar sein.

    Bis 2.4.1 wurde `response.json()` ungeprüft weitergereicht. Eine
    Antwort ohne `companion_token` - ein `null`, eine Fehlermeldung
    mit Status 200, eine ältere oder neuere Feldbenennung - landete
    damit unverändert in der Ablage. Die Oberfläche meldete danach
    "Verbunden als …", während jeder einzelne Client genau dieses
    Feld verlangt und deshalb wortlos nichts tat. Genau das ist der
    Zustand "ich verbinde mich, und es kommt nichts".
    """

    if not isinstance(payload, dict):

        raise DiscordAuthError(
            "Der Bot hat auf die Anmeldung keine verwertbare Antwort "
            "geschickt."
        )

    token = str(payload.get("companion_token") or "").strip()

    if not token:

        raise DiscordAuthError(
            "Der Bot hat die Anmeldung bestätigt, aber kein "
            "Companion-Token mitgeschickt - ohne das kann die App "
            "nichts abrufen. Bitte erneut versuchen."
        )

    account = dict(payload)

    account["companion_token"] = token

    return account


class _CallbackHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):

        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        self.server.result = {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
            "error": params.get("error", [None])[0],
        }

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )
        self.end_headers()

        if self.server.result.get("error"):

            body = (
                "<h2>Discord-Anmeldung abgebrochen.</h2>"
                "<p>Dieses Fenster kann geschlossen werden.</p>"
            )

        else:

            body = (
                "<h2>Erfolgreich mit Discord verbunden.</h2>"
                "<p>Dieses Fenster kann geschlossen werden.</p>"
            )

        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):

        #
        # Kein Zugriffslog auf der Konsole
        #

        pass


class DiscordAuth:

    def login(self, logger=None) -> dict:
        """
        Führt den kompletten OAuth-Login aus: startet einen
        temporären lokalen HTTP-Server, öffnet den System-Browser zur
        echten Discord-Autorisierungsseite, wartet auf GENAU einen
        Redirect-Aufruf und tauscht den Code danach serverseitig beim
        Bot gegen die Discord-Identität + ein Companion-Pairing-Token.

        Blockierend - vom Aufrufer bereits in einem Hintergrund-Thread
        auszuführen (siehe gui/pages/settings.py), damit die UI
        währenddessen nicht einfriert.
        """

        state = secrets.token_urlsafe(16)

        try:

            server = http.server.HTTPServer(
                ("127.0.0.1", REDIRECT_PORT),
                _CallbackHandler,
            )

        except OSError as exc:

            #
            # Der übliche Fall ist ein noch laufender Versuch: der
            # wartende Server hält den Port bis zu zwei Minuten. Als
            # englische Systemmeldung ("Address already in use") war
            # das an dieser Stelle nicht zu deuten.
            #

            raise DiscordAuthError(
                f"Die Anmeldung läuft bereits (Port {REDIRECT_PORT} ist "
                "belegt). Bitte den offenen Browser-Tab abschliessen "
                "oder kurz warten und es erneut versuchen."
            ) from exc

        server.result = None
        server.timeout = 120

        query = urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "prompt": "consent",
        })

        #
        # Über core.browser.open_url(): ohne dessen bereinigte
        # Umgebung vererbt das AppImage/PyInstaller-Bündel sein
        # eigenes LD_LIBRARY_PATH an den vom Browser-Öffnen intern
        # gestarteten Subprozess (meist über /bin/sh) - der crasht
        # dann sofort mit einem "symbol lookup error", der Browser
        # öffnet nie, und der Login läuft stattdessen in den Timeout
        # unten.
        #

        address = f"{DISCORD_AUTHORIZE_URL}?{query}"

        #
        # Und der Rückgabewert wird ausgewertet. Ohne Browser (auf
        # einem frisch aufgesetzten System ist schlicht keiner als
        # Standard hinterlegt) hat der Knopf sonst zwei Minuten lang
        # nichts getan und danach mit "Zeitüberschreitung" geantwortet
        # - der Grund stand nirgends, und die Adresse, die man von
        # Hand hätte öffnen können, auch nicht.
        #

        if not open_url(address, logger):

            server.server_close()

            raise DiscordAuthError(
                "Es liess sich kein Browser öffnen. Bitte diese "
                f"Adresse von Hand aufrufen: {address}"
            )

        try:

            #
            # Blockiert bis genau eine Anfrage eingeht oder der
            # Timeout (120s) erreicht ist.
            #

            server.handle_request()

        finally:

            server.server_close()

        result = server.result

        if result is None:

            raise DiscordAuthError(
                "Zeitüberschreitung beim Discord-Login."
            )

        if result.get("error"):

            raise DiscordAuthError(
                f"Discord-Login abgebrochen ({result['error']})."
            )

        if result.get("state") != state:

            raise DiscordAuthError(
                "Ungültige Login-Antwort (state stimmt nicht überein)."
            )

        code = result.get("code")

        if not code:

            raise DiscordAuthError(
                "Kein Autorisierungscode erhalten."
            )

        #
        # Der Netzfehler wird hier abgefangen und übersetzt, statt
        # ihn durchzureichen. Bis 2.4.3 stand nach einer im Browser
        # tadellos abgeschlossenen Anmeldung
        #
        #     Der letzte Versuch ist fehlgeschlagen: [Errno -2] Der
        #     Name oder der Dienst ist nicht bekannt
        #
        # auf dem Bildschirm - eine Meldung des Betriebssystems, in
        # der weder die Adresse vorkommt, die nicht aufgelöst werden
        # konnte, noch der Umstand, dass Discord und die Anmeldung
        # selbst völlig in Ordnung waren. Wer sie liest, sucht den
        # Fehler bei sich.
        #
        # Und genau dieser Fall ist der wahrscheinlichste, den die
        # Companion je erlebt: verschwindet der Name des Bots aus dem
        # DNS - der Anbieter schreibt den Rechner in den Hostnamen,
        # siehe core/backend_config.py -, scheitert ab diesem Moment
        # jeder einzelne Abruf so.
        #

        try:

            response = httpx.post(
                f"{BOT_BASE_URL}/companion/auth/exchange",
                json={"code": code},
                timeout=15,
            )

        except Exception as exc:

            if logger is not None:

                logger.error(
                    "Discord-Login: der Bot ist unter "
                    f"{BOT_BASE_URL} nicht erreichbar ({exc}). "
                    f"Abweichende Adresse: {override_hint()}."
                )

            raise DiscordAuthError(
                bot_unreachable_text(exc, BOT_BASE_URL)
            ) from exc

        if response.status_code != 200:

            raise DiscordAuthError(
                f"Bot hat den Login abgelehnt: {response.text}"
            )

        try:

            payload = response.json()

        except ValueError as exc:

            raise DiscordAuthError(
                "Die Antwort des Bots auf die Anmeldung war kein "
                "gültiges JSON."
            ) from exc

        return parse_exchange_response(payload)

    # --------------------------------------------------

    def unlink(self, companion_token: str) -> None:

        try:

            httpx.post(
                f"{BOT_BASE_URL}/companion/auth/unlink",
                headers={
                    "Authorization": f"Bearer {companion_token}",
                },
                timeout=10,
            )

        except Exception:

            #
            # Lokale Trennung soll auch klappen, wenn der Bot gerade
            # nicht erreichbar ist - das Token verwaist dann serverseitig,
            # ist aber harmlos.
            #

            pass
