from __future__ import annotations

from pathlib import Path

from core.auth.models import (
    AuthState,
    DiscordAccount,
)
from core.auth.token_store import TokenStore


class AuthManager:
    """
    Zentrale Authentifizierung für WeintCompanion.

    Diese Klasse verwaltet:

    - aktuellen Loginstatus
    - gespeicherte Discord-Anmeldung
    - Laden/Speichern der Tokens
    - später OAuth2
    """

    # --------------------------------------------------

    def __init__(self, token_file: Path):

        self.store = TokenStore(token_file)

        self.state = AuthState()

        self.load()

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    @property
    def authenticated(self) -> bool:

        return self.state.authenticated

    # --------------------------------------------------

    @property
    def account(self) -> DiscordAccount | None:

        return self.state.account

    # --------------------------------------------------
    # Laden
    # --------------------------------------------------

    def load(self) -> None:

        account = self.store.load()

        if account is None:

            self.state.authenticated = False
            self.state.account = None

            return

        self.state.authenticated = True
        self.state.account = account

    # --------------------------------------------------
    # Speichern
    # --------------------------------------------------

    def save(self, account: DiscordAccount) -> None:

        self.store.save(account)

        self.state.account = account
        self.state.authenticated = True

    # --------------------------------------------------
    # Login
    # --------------------------------------------------

    def login(self) -> None:
        """
        Startet später den OAuth2-Login.

        Wird in der nächsten Ausbaustufe implementiert.
        """

        print("OAuth2 Login folgt...")

    # --------------------------------------------------
    # Logout
    # --------------------------------------------------

    def logout(self) -> None:

        self.store.clear()

        self.state.account = None
        self.state.authenticated = False

    # --------------------------------------------------
    # Refresh
    # --------------------------------------------------

    def refresh(self) -> None:
        """
        Wird später den Access Token
        automatisch erneuern.
        """

        pass

    # --------------------------------------------------
    # Benutzerinformationen
    # --------------------------------------------------

    def username(self) -> str:

        if self.state.account is None:

            return ""

        return self.state.account.username

    # --------------------------------------------------

    def discord_id(self) -> int | None:

        if self.state.account is None:

            return None

        return self.state.account.discord_id