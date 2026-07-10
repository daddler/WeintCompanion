from __future__ import annotations

import http.server
import secrets
import urllib.parse
import webbrowser

import httpx

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

CLIENT_ID = "REPLACE_WITH_DISCORD_CLIENT_ID"

REDIRECT_PORT = 53682
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"

DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"

BOT_BASE_URL = "https://weintcodex-a1d.b.jrnm.app"


class DiscordAuthError(Exception):
    pass


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

    def login(self) -> dict:
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

        server = http.server.HTTPServer(
            ("127.0.0.1", REDIRECT_PORT),
            _CallbackHandler,
        )

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

        webbrowser.open(
            f"{DISCORD_AUTHORIZE_URL}?{query}"
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

        response = httpx.post(
            f"{BOT_BASE_URL}/companion/auth/exchange",
            json={"code": code},
            timeout=15,
        )

        if response.status_code != 200:

            raise DiscordAuthError(
                f"Bot hat den Login abgelehnt: {response.text}"
            )

        return response.json()

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
