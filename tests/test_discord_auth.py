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
