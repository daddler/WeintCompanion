from __future__ import annotations

from pathlib import Path

# ==========================================================
# Discord OAuth2
# ==========================================================

#
# Discord Developer Portal
# https://discord.com/developers/applications
#

CLIENT_ID = ""

# Desktop-Anwendung:
# Kein CLIENT_SECRET nötig (OAuth2 mit PKCE)
CLIENT_SECRET = None

# ==========================================================
# OAuth
# ==========================================================

REDIRECT_HOST = "127.0.0.1"

REDIRECT_PORT = 48731

REDIRECT_URI = (
    f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"
)

# Discord OAuth2 Scopes
SCOPES = [
    "identify",
]

# ==========================================================
# Lokale Speicherung
# ==========================================================

CONFIG_DIR = Path("config")

TOKEN_FILE = CONFIG_DIR / "discord_account.json"

# ==========================================================
# Bot API
# ==========================================================

#
# Wird später verwendet.
# Beispiel:
#
# https://bot.weintcodex.de/api
#

API_BASE_URL = ""

# ==========================================================
# Timeouts
# ==========================================================

HTTP_TIMEOUT = 15

TOKEN_REFRESH_MARGIN = 300  # Sekunden

# ==========================================================
# Version
# ==========================================================

AUTH_VERSION = 1