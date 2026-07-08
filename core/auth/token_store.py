from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from core.auth.models import DiscordAccount


class TokenStore:
    """
    Speichert und lädt die Discord-Anmeldedaten lokal.

    Aktuell werden die Daten als JSON gespeichert.
    Später kann diese Klasse problemlos auf den
    Windows Credential Manager, GNOME Keyring oder
    den macOS Keychain umgestellt werden, ohne dass
    sich der übrige Code ändert.
    """

    def __init__(self, path: Path):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------

    def exists(self) -> bool:

        return self.path.exists()

    # --------------------------------------------------

    def save(self, account: DiscordAccount) -> None:

        data = asdict(account)

        #
        # datetime -> ISO String
        #

        if account.expires_at is not None:

            data["expires_at"] = (
                account.expires_at.isoformat()
            )

        with self.path.open(
            "w",
            encoding="utf-8",
        ) as fp:

            json.dump(
                data,
                fp,
                indent=4,
                ensure_ascii=False,
            )

    # --------------------------------------------------

    def load(self) -> DiscordAccount | None:

        if not self.exists():

            return None

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as fp:

            data = json.load(fp)

        expires = data.get("expires_at")

        if expires:

            data["expires_at"] = (
                datetime.fromisoformat(expires)
            )

        return DiscordAccount(**data)

    # --------------------------------------------------

    def clear(self) -> None:

        if self.exists():

            self.path.unlink()