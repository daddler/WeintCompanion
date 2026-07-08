from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class DiscordAccount:

    discord_id: int

    username: str

    avatar: str | None = None

    access_token: str = ""

    refresh_token: str = ""

    expires_at: datetime | None = None


@dataclass(slots=True)
class AuthState:

    authenticated: bool = False

    account: DiscordAccount | None = None