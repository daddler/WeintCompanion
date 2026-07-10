from __future__ import annotations

import json

from core.paths import Paths


class DiscordAccountStore:
    """
    Speichert die verknüpfte Discord-Identität rein lokal auf dem
    Rechner des Nutzers (Datenschutz: keine zentrale Speicherung).
    Enthält NIE das eigentliche Discord-OAuth-Token, nur die
    Identität (id/username/avatar) und das vom Bot ausgestellte
    Companion-Pairing-Token.
    """

    def __init__(self):

        self.file = (
            Paths.config()
            / "discord_account.json"
        )

    # --------------------------------------------------

    def load(self) -> dict | None:

        if not self.file.exists():
            return None

        try:

            with open(
                self.file,
                "r",
                encoding="utf-8",
            ) as f:

                return json.load(f)

        except Exception:

            return None

    # --------------------------------------------------

    def save(self, data: dict) -> None:

        with open(
            self.file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False,
            )

    # --------------------------------------------------

    def clear(self) -> None:

        if self.file.exists():
            self.file.unlink()
