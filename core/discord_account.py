from __future__ import annotations

import json
import os
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
# Discord verbinden".
#

AUTH_REJECTIONS_BEFORE_UNLINK = 3

AUTH_REJECTION_WINDOW = 300.0


#
# Und wie weit zwei Ablehnungen auseinanderliegen müssen, damit sie
# als ZWEI zählen.
#
# Das war die Lücke, die den Zähler wirkungslos gemacht hat: eine
# Nachricht, deren Zustellung fehlschlägt, bleibt in der Warteschlange
# des Addons liegen und wird im Sync-Takt - alle fünf Sekunden -
# erneut versucht (core/sync_manager.py). Ein einziger abgelehnter
# Versuch erzeugte damit drei Ablehnungen in fünfzehn Sekunden, und
# die Schwelle von drei war genauso schnell erreicht wie die Schwelle
# von eins, gegen die sie geschrieben wurde. Genau das ist der Grund,
# aus dem die Verknüpfung nach jedem Neustart wieder weg war.
#
# Mit der Sperre zählt ein Wiederholungslauf als das, was er ist: ein
# Vorfall. Erst drei Vorfälle, die mindestens eine Minute
# auseinanderliegen und zusammen in das Fenster oben passen, heissen
# zuverlässig, dass der Bot dieses Token wirklich nicht kennt. Ein
# neu startender Bot ist bis dahin längst wieder da; ein wirklich
# totes Token ist nach gut zwei Minuten erkannt statt nach fünfzehn
# Sekunden, und in dieser Zeit sagt jeder Client dem Nutzer ohnehin
# schon, dass der Bot die Verknüpfung ablehnt.
#

AUTH_REJECTION_COOLDOWN = 60.0


class DiscordAccountError(Exception):
    """
    Die Verknüpfung liess sich nicht ablegen (unbrauchbare Daten oder
    ein fehlgeschlagener Schreibvorgang). Der Aufrufer sagt es dem
    Nutzer - lautlos speichern zu wollen und dabei zu scheitern, ist
    genau der Zustand, in dem die App "verbunden" behauptet und nichts
    funktioniert.
    """


#
# Wohin die Meldung über eine aufgehobene Verknüpfung geht.
#
# Sie stand vorher in `print()` an genau einer der fünf Stellen, die
# `note_auth_rejected()` aufrufen - also nirgends, wo ein Nutzer sie
# sieht. Die übrigen vier haben den Rückgabewert nicht einmal
# ausgewertet. Dass die App die Discord-Verknüpfung von sich aus
# wegwirft, war damit ein Vorgang ohne jede Spur: aufgefallen ist er
# erst beim nächsten Start am Anmeldehinweis.
#
# Deshalb meldet es jetzt die Stelle, die es entscheidet, und nicht
# mehr der Aufrufer. `CompanionManager` hinterlegt dafür beim Start
# den Logger der App.
#

_logger = None


def set_logger(logger) -> None:

    global _logger

    _logger = logger


def _log(level: str, message: str) -> None:

    logger = _logger

    if logger is None:

        print(message)

        return

    try:

        getattr(logger, level, logger.info)(message)

    except Exception:

        pass


def is_usable(account) -> bool:
    """
    Ob mit dieser Ablage tatsächlich etwas beim Bot abgerufen werden
    kann.

    Die Frage "ist ein Konto verknüpft" wurde an vier Stellen als
    "steht da irgendetwas" beantwortet (Anmeldehinweis beim Start,
    Navigationsspalte, Einstellungsseite, Einrichtung) und an sieben
    weiteren als "steht da ein `companion_token`" - nämlich in jedem
    Client, der wirklich etwas holt. Ein Eintrag ohne Token erfüllte
    damit das erste und nicht das zweite: die Oberfläche meldete
    "Verbunden als …" und kein einziger Abruf lief. Diese Funktion ist
    die eine Antwort für beide Fragen.
    """

    return bool(
        isinstance(account, dict)
        and str(account.get("companion_token") or "").strip()
    )


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

        #
        # Die zuletzt erfolgreich abgelegte Fassung. Sie ist die
        # Antwort auf einen abgebrochenen Schreibvorgang: die Datei
        # oben ist dann leer oder halb geschrieben, und `load()` konnte
        # das bisher von "noch nie verknüpft" nicht unterscheiden.
        #

        self.backup = self.file.with_suffix(".json.bak")

    # --------------------------------------------------
    # LESEN
    # --------------------------------------------------

    @staticmethod
    def _read(path) -> dict | None:

        if not path.exists():
            return None

        try:

            with open(path, "r", encoding="utf-8") as f:

                data = json.load(f)

        except Exception:

            return None

        #
        # `null` oder eine Liste sind kein Konto. Ohne diese Prüfung
        # käme eine unbrauchbare Antwort des Bots als scheinbar
        # gültiger Stand zurück und jeder Aufrufer müsste selbst
        # nachsehen, ob er ein `dict` in der Hand hält.
        #

        if not isinstance(data, dict):
            return None

        return data

    def load(self) -> dict | None:

        data = self._read(self.file)

        if data is not None:
            return data

        #
        # Die Hauptdatei fehlt oder ist unlesbar. Gibt es eine
        # Sicherung, ist das kein "nicht verknüpft", sondern ein
        # abgebrochener Schreibvorgang - und der darf den Nutzer nicht
        # die Anmeldung kosten.
        #

        backup = self._read(self.backup)

        if backup is None:
            return None

        _log(
            "warning",
            "Die gespeicherte Discord-Verknüpfung war "
            + ("unlesbar" if self.file.exists() else "verschwunden")
            + " - die letzte gültige Fassung wurde wiederhergestellt.",
        )

        try:

            self._write_atomic(self.file, backup)

        except Exception:

            #
            # Wiederherstellen ist eine Verbesserung, keine
            # Voraussetzung: gelesen ist die Verknüpfung ohnehin
            # schon.
            #

            pass

        return backup

    def is_linked(self) -> bool:

        return is_usable(self.load())

    # --------------------------------------------------
    # SCHREIBEN
    # --------------------------------------------------
    #
    # Zwei Eigenschaften, die `open(..., "w")` nicht hat und die beide
    # als "die Anmeldung ist nach dem Neustart weg" auffallen:
    #
    # 1. `"w"` kürzt die Datei sofort auf null Byte und schreibt erst
    #    danach. Zwischen beidem liegt ein Zeitfenster, in dem ein
    #    Absturz, ein Stromausfall oder ein erzwungener Neustart eine
    #    leere Datei hinterlässt - und eine leere Datei war bisher von
    #    "noch nie verknüpft" nicht zu unterscheiden. Das ist kein
    #    Linux-Thema: unter Windows trifft es jeden Neustart, den ein
    #    Update erzwingt, genauso.
    # 2. Ohne `fsync()` steht der Inhalt nach dem Schliessen nur im
    #    Zwischenspeicher des Systems. Ein sauberes Herunterfahren
    #    schreibt ihn weg, ein hartes nicht - auf Btrfs (der Vorgabe
    #    von CachyOS) fällt die Datei dann auf den letzten festen
    #    Stand zurück, also im Zweifel auf "gibt es nicht".
    #
    # Deshalb: in eine Nebendatei schreiben, auf die Platte zwingen,
    # und erst dann an ihren Platz umbenennen. `os.replace()` ist auf
    # beiden Systemen ein Schritt - entweder die alte Fassung steht
    # da oder die neue, nie eine halbe.
    #

    @staticmethod
    def _write_atomic(path, data: dict) -> None:

        temp = path.with_suffix(path.suffix + ".tmp")

        with open(temp, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False,
            )

            f.flush()

            os.fsync(f.fileno())

        os.replace(temp, path)

        #
        # Auch der Verzeichniseintrag selbst will festgeschrieben
        # werden, sonst kann das Umbenennen einen harten Neustart
        # nicht überleben. Unter Windows lässt sich ein Verzeichnis
        # nicht öffnen - dort entfällt der Schritt.
        #

        try:

            fd = os.open(path.parent, os.O_RDONLY)

            try:
                os.fsync(fd)
            finally:
                os.close(fd)

        except Exception:

            pass

    def save(self, data: dict) -> None:
        """
        Legt die Verknüpfung ab.

        Wirft `DiscordAccountError`, wenn die Daten unbrauchbar sind
        oder sich nicht schreiben lassen. Beides lautlos hinzunehmen
        hiess bisher: die Oberfläche zeigt "Verbunden als …", und kein
        einziger Abruf funktioniert - der Zustand, der sich von aussen
        wie ein kaputter Bot anfühlt.
        """

        if not is_usable(data):

            raise DiscordAccountError(
                "Die Antwort auf die Anmeldung enthält kein "
                "Companion-Token - ohne das kann die App beim Bot "
                "nichts abrufen."
            )

        try:

            self._write_atomic(self.file, data)

        except Exception as exc:

            raise DiscordAccountError(
                f"Die Verknüpfung liess sich nicht speichern: {exc}"
            ) from exc

        #
        # Die Sicherung ist erst nach dem geglückten Schreiben dran:
        # sie soll die letzte GÜLTIGE Fassung halten, nicht die
        # jeweils letzte.
        #

        try:

            self._write_atomic(self.backup, data)

        except Exception:

            pass

    # --------------------------------------------------

    def clear(self) -> None:

        DiscordAccountStore._rejections = 0
        DiscordAccountStore._last_rejection = None

        for path in (self.file, self.backup):

            try:

                if path.exists():
                    path.unlink()

            except Exception:

                pass

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
        wurde. Gesagt wird das hier und nicht beim Aufrufer - vier der
        fünf Aufrufer haben den Rückgabewert gar nicht ausgewertet.
        """

        now = time.monotonic()

        last = DiscordAccountStore._last_rejection

        #
        # Noch innerhalb der Sperre: derselbe Vorfall, nur erneut
        # versucht. Zählt nicht.
        #

        if last is not None and now - last < AUTH_REJECTION_COOLDOWN:
            return False

        if last is None or now - last > AUTH_REJECTION_WINDOW:
            DiscordAccountStore._rejections = 0

        DiscordAccountStore._last_rejection = now
        DiscordAccountStore._rejections += 1

        if DiscordAccountStore._rejections < AUTH_REJECTIONS_BEFORE_UNLINK:

            _log(
                "warning",
                "Der Bot hat das Companion-Token abgelehnt (401) - "
                "wird erneut versucht.",
            )

            return False

        self.clear()

        _log(
            "error",
            "Der Bot hat das Companion-Token mehrfach abgelehnt (401). "
            "Die Discord-Verknüpfung wurde deshalb lokal aufgehoben - "
            "bitte unter Einstellungen → Discord erneut verbinden.",
        )

        return True
