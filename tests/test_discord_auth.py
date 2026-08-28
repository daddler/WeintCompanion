"""
Tests fuer die Pruefung der Bot-Antwort auf den Code-Austausch
(core/discord_auth.py:parse_exchange_response).

`login()` selbst laesst sich nicht ohne Browser und lokalen
HTTP-Server ausfuehren - deshalb liegt die Entscheidung, ob die
Antwort brauchbar ist, in einer eigenen, reinen Funktion. Dieselbe
Aufteilung wie bei `access_roles.build_profile_payload()` und
`roster_target()`: pruefbar ist, wo etwas falsch sein kann.
"""

import pytest

httpx = pytest.importorskip("httpx")

from core.discord_auth import DiscordAuthError, parse_exchange_response


def test_eine_vollstaendige_antwort_geht_durch():

    antwort = parse_exchange_response({
        "discord_id": "1",
        "username": "Weint",
        "companion_token": "wc1.aaa.bbb",
        "authorized": True,
    })

    assert antwort["companion_token"] == "wc1.aaa.bbb"
    assert antwort["username"] == "Weint"


def test_ohne_companion_token_ist_die_anmeldung_gescheitert():
    """
    Bis 2.4.1 wurde eine solche Antwort unveraendert abgelegt. Die
    Oberflaeche meldete danach "Verbunden als …", waehrend jeder
    Client genau dieses Feld verlangt und deshalb wortlos nichts tat.
    """

    with pytest.raises(DiscordAuthError):
        parse_exchange_response({"username": "Weint"})


def test_leerraum_ist_kein_token():

    with pytest.raises(DiscordAuthError):
        parse_exchange_response({"companion_token": "   "})


def test_eine_antwort_die_kein_objekt_ist_wird_abgewiesen():

    for payload in (None, [], "ok", 7):

        with pytest.raises(DiscordAuthError):
            parse_exchange_response(payload)


# --------------------------------------------------
# Der Bot ist nicht erreichbar
# --------------------------------------------------
# Der Fehlerbericht, der zu diesem Abschnitt fuehrte: die Anmeldung
# im Browser lief tadellos durch, und danach stand in den
# Einstellungen
#
#     Der letzte Versuch ist fehlgeschlagen: [Errno -2] Der Name oder
#     der Dienst ist nicht bekannt
#
# Das ist die Meldung des Betriebssystems, unveraendert
# durchgereicht. Sie nennt weder die Adresse, die nicht aufgeloest
# werden konnte, noch dass Discord unbeteiligt war, noch den Ausweg.

import socket
import threading
import urllib.parse
import urllib.request

from core import discord_auth


class _Protokoll:

    def __init__(self):
        self.zeilen = []

    def error(self, text):
        self.zeilen.append(text)

    def info(self, text):
        self.zeilen.append(text)

    def warning(self, text):
        self.zeilen.append(text)

    def success(self, text):
        self.zeilen.append(text)


def _port_frei() -> bool:

    probe = socket.socket()

    #
    # Wie `HTTPServer` es selbst tut (`allow_reuse_address`) - sonst
    # meldet diese Probe den Port unmittelbar nach dem vorigen Test
    # als belegt, obwohl der Server ihn laengst freigegeben hat, und
    # der Test uebersprange sich selbst.
    #

    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        probe.bind(("127.0.0.1", discord_auth.REDIRECT_PORT))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def _browser_der_sofort_zurueckkommt(adresse, logger=None):
    """
    Statt eines Browsers: der Rueckruf wird selbst ausgeloest, mit
    genau dem `state` aus dem Autorisierungslink. Damit laeuft
    `login()` bis zum Austausch beim Bot durch - der Stelle, um die
    es hier geht.
    """

    state = urllib.parse.parse_qs(
        urllib.parse.urlparse(adresse).query
    )["state"][0]

    ziel = (
        f"{discord_auth.REDIRECT_URI}"
        f"?code=abc&state={urllib.parse.quote(state)}"
    )

    def rueckruf():

        try:
            urllib.request.urlopen(ziel, timeout=5).read()
        except Exception:
            pass

    threading.Thread(target=rueckruf, daemon=True).start()

    return True


def test_ein_nicht_aufloesbarer_name_wird_erklaert(monkeypatch):
    """
    Statt der Systemmeldung ein Satz, der die Adresse nennt, die
    Anmeldung entlastet und den naechsten Schritt benennt.
    """

    if not _port_frei():
        pytest.skip(
            f"Port {discord_auth.REDIRECT_PORT} ist belegt"
        )

    monkeypatch.setattr(
        discord_auth, "open_url", _browser_der_sofort_zurueckkommt
    )

    def kaputt(*args, **kwargs):

        fehler = httpx.ConnectError(
            "[Errno -2] Name or service not known"
        )

        fehler.__cause__ = socket.gaierror(
            -2, "Name or service not known"
        )

        raise fehler

    monkeypatch.setattr(discord_auth.httpx, "post", kaputt)

    logger = _Protokoll()

    with pytest.raises(DiscordAuthError) as fehler:
        discord_auth.DiscordAuth().login(logger)

    text = str(fehler.value)

    assert discord_auth.BOT_BASE_URL in text
    assert "nicht auflösen" in text
    assert "Discord-Anmeldung" in text
    assert "Errno" not in text

    #
    # Und im Protokoll steht, wo sich die Adresse aendern laesst -
    # ein Fehlschlag, der nur auf dem Bildschirm steht, ist beim
    # Nachfragen nicht mehr auffindbar.
    #

    assert any("WEINTCODEX_BOT_URL" in zeile for zeile in logger.zeilen)


def test_ein_abgewiesener_verbindungsversuch_wird_nicht_als_umzug_erklaert(monkeypatch):
    """
    Sonst suchte man eine neue Adresse fuer einen Bot, der schlicht
    gerade nicht laeuft.
    """

    if not _port_frei():
        pytest.skip(
            f"Port {discord_auth.REDIRECT_PORT} ist belegt"
        )

    monkeypatch.setattr(
        discord_auth, "open_url", _browser_der_sofort_zurueckkommt
    )

    def abgewiesen(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(discord_auth.httpx, "post", abgewiesen)

    with pytest.raises(DiscordAuthError) as fehler:
        discord_auth.DiscordAuth().login(_Protokoll())

    assert "nicht auflösen" not in str(fehler.value)
