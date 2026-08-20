"""
Tests fuer die Toleranz gegenueber einem abgelehnten Companion-Token
(core/discord_account.py).

Die haeufigste Beschwerde zur App war "ich muss mich staendig neu mit
Discord verbinden". Die Ursache lag beim Bot (sein Pairing-Token lag
in einer Datenbank, die jeder Deploy geleert hat, siehe
services/companion_token.py drueben), aber die Wirkung entstand hier:
ein einzelnes HTTP 401 hat die lokale Verknuepfung geloescht.

Diese Regel ist deshalb weder Vorsicht noch Geschmack, sondern die
zweite Haelfte derselben Reparatur - und sie ist unsichtbar, solange
alles funktioniert. Genau dafuer sind diese Tests da.
"""

import pytest

from core.discord_account import (
    AUTH_REJECTIONS_BEFORE_UNLINK,
    AUTH_REJECTION_WINDOW,
    DiscordAccountStore,
)
from core.paths import Paths


@pytest.fixture
def store(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    store = DiscordAccountStore()

    store.save({
        "discord_id": "1",
        "username": "Weint",
        "companion_token": "wc1.aaa.bbb",
    })

    #
    # Der Zaehler liegt auf der Klasse (alle Clients beantworten
    # dieselbe Frage) und ueberlebt damit einen einzelnen Test.
    #

    DiscordAccountStore._rejections = 0
    DiscordAccountStore._last_rejection = None

    return store


def test_ein_einzelnes_401_kostet_die_verknuepfung_nicht(store):

    assert store.note_auth_rejected() is False

    assert store.load() is not None


def test_mehrere_401_kurz_hintereinander_heben_auf(store):

    for _ in range(AUTH_REJECTIONS_BEFORE_UNLINK - 1):
        assert store.note_auth_rejected() is False

    assert store.note_auth_rejected() is True

    assert store.load() is None


def test_alle_clients_zaehlen_auf_denselben_stand(tmp_path, monkeypatch, store):
    """
    Jeder Client (Charaktere, Roster, WeakAuras, ...) legt sich einen
    eigenen Store an. Wuerde jeder fuer sich zaehlen, braeuchte es die
    Schwelle je Client - und die Absicht waere dahin.
    """

    zweiter = DiscordAccountStore()
    dritter = DiscordAccountStore()

    assert store.note_auth_rejected() is False
    assert zweiter.note_auth_rejected() is False
    assert dritter.note_auth_rejected() is True

    assert store.load() is None


def test_vereinzelte_401_ueber_tage_summieren_sich_nicht(store, monkeypatch):
    """
    Ein 401 heute und eines naechste Woche sind kein Muster, sondern
    zwei Zufaelle. Nur was innerhalb des Fensters zusammenfaellt,
    zaehlt zusammen.
    """

    uhr = {"jetzt": 1000.0}

    monkeypatch.setattr(
        "core.discord_account.time.monotonic",
        lambda: uhr["jetzt"],
    )

    for _ in range(AUTH_REJECTIONS_BEFORE_UNLINK * 3):

        assert store.note_auth_rejected() is False

        uhr["jetzt"] += AUTH_REJECTION_WINDOW + 1

    assert store.load() is not None


def test_ein_erfolgreicher_login_faengt_neu_an(store):
    """
    `clear()` setzt den Zaehler zurueck - sonst haette eine
    frisch hergestellte Verknuepfung die Ablehnungen der alten geerbt
    und waere beim ersten Fehlschlag sofort wieder weg.
    """

    store.note_auth_rejected()
    store.note_auth_rejected()

    store.clear()

    store.save({"discord_id": "1", "companion_token": "wc1.ccc.ddd"})

    assert store.note_auth_rejected() is False

    assert store.load() is not None
