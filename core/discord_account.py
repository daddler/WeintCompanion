from __future__ import annotations

import json
import time

from core.paths import Paths


#
# Wie viele abgelehnte Anfragen (HTTP 401) es braucht, bis die
# Verknüpfung lokal aufgehoben wird - und innerhalb welcher Zeit sie
# dafür zusammengehören müssen.
#
# Die Zahl ist nicht Vorsicht um ihrer selbst willen. Ein einzelnes
# 401 kann ein Bot sein, der gerade neu startet, ein Proxy dazwischen
# oder ein serverseitiger Fehler, der als "Token ungültig" verkleidet
# ankommt - und der Preis dafür, es beim Wort zu nehmen, ist genau die
# Beschwerde, die am häufigsten kam: "ich muss mich dauernd neu mit
# Discord verbinden". Drei Ablehnungen innerhalb von fünf Minuten
# heissen dagegen zuverlässig, dass der Bot dieses Token wirklich
# nicht kennt; bei einem Sync-Takt von fünf Sekunden ist das eine
# Frage von Sekunden und verzögert die richtige Antwort nicht spürbar.
#

AUTH_REJECTIONS_BEFORE_UNLINK = 3

AUTH_REJECTION_WINDOW = 300.0


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

        DiscordAccountStore._rejections = 0
        DiscordAccountStore._last_rejection = None

        if self.file.exists():
            self.file.unlink()

    # --------------------------------------------------
    # ABGELEHNTE ANMELDUNG (HTTP 401)
    # --------------------------------------------------
    #
    # Bewusst auf der Klasse und nicht auf der Instanz: jeder Client
    # (Charaktere, Roster, WeakAuras, WarcraftLogs, Zuordnung) legt
    # sich einen eigenen Store an, aber sie beantworten alle dieselbe
    # eine Frage - kennt der Bot dieses Token noch? Ein Zähler je
    # Client würde jeden einzeln bis zur Schwelle zählen lassen und die
    # Absicht damit unterlaufen.
    #

    _rejections: int = 0

    _last_rejection: float | None = None

    def note_auth_rejected(self) -> bool:
        """
        Meldet, dass der Bot das Companion-Token abgelehnt hat.

        Gibt `True` zurück, wenn die Verknüpfung daraufhin aufgehoben
        wurde - der Aufrufer sagt das dann im Log, denn danach steht
        der Nutzer wieder vor dem Anmeldeknopf und soll wissen, warum.
        """

        now = time.monotonic()

        last = DiscordAccountStore._last_rejection

        if last is None or now - last > AUTH_REJECTION_WINDOW:
            DiscordAccountStore._rejections = 0

        DiscordAccountStore._last_rejection = now
        DiscordAccountStore._rejections += 1

        if DiscordAccountStore._rejections < AUTH_REJECTIONS_BEFORE_UNLINK:
            return False

        self.clear()

        return True
