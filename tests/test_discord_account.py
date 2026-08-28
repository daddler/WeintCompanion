"""
Tests fuer die Ablage der Discord-Verknuepfung
(core/discord_account.py).

Die haeufigste Beschwerde zur App war "ich muss mich staendig neu mit
Discord verbinden", und sie hatte nacheinander drei Ursachen. Die
erste lag beim Bot (sein Pairing-Token lag in einer Datenbank, die
jeder Deploy geleert hat). Die zweite lag hier: ein einzelnes HTTP 401
hat die lokale Verknuepfung geloescht. Die dritte lag ebenfalls hier
und hat die Reparatur der zweiten unwirksam gemacht - der Zaehler von
drei Ablehnungen war in fuenfzehn Sekunden voll, weil eine nicht
zugestellte Nachricht im Sync-Takt erneut versucht wird.

Dazu kommen die beiden Faelle, in denen die Verknuepfung zwar
dastand, aber nichts konnte: eine abgebrochen geschriebene Datei und
eine Antwort des Bots ohne Companion-Token.

Alle diese Regeln sind unsichtbar, solange es funktioniert. Genau
dafuer sind diese Tests da.
"""

import json

import pytest

from core.discord_account import (
    AUTH_REJECTION_COOLDOWN,
    AUTH_REJECTION_WINDOW,
    AUTH_REJECTIONS_BEFORE_UNLINK,
    DiscordAccountError,
    DiscordAccountStore,
    is_usable,
)
from core.paths import Paths


KONTO = {
    "discord_id": "1",
    "username": "Weint",
    "companion_token": "wc1.aaa.bbb",
}


@pytest.fixture
def uhr(monkeypatch):
    """
    Die Zeit gehoert in diesen Tests zur Aussage: eine Ablehnung
    zaehlt nur, wenn sie weit genug von der vorigen entfernt ist.
    """

    stand = {"jetzt": 1000.0}

    monkeypatch.setattr(
        "core.discord_account.time.monotonic",
        lambda: stand["jetzt"],
    )

    return stand


@pytest.fixture
def store(tmp_path, monkeypatch):

    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    store = DiscordAccountStore()

    store.save(dict(KONTO))

    #
    # Der Zaehler liegt auf der Klasse (alle Clients beantworten
    # dieselbe Frage) und ueberlebt damit einen einzelnen Test.
    #

    DiscordAccountStore._rejections = 0
    DiscordAccountStore._last_rejection = None

    return store


# --------------------------------------------------
# Abgelehntes Token
# --------------------------------------------------


def test_ein_einzelnes_401_kostet_die_verknuepfung_nicht(store):

    assert store.note_auth_rejected() is False

    assert store.load() is not None


def test_ein_wiederholungslauf_ist_ein_vorfall_und_nicht_drei(store, uhr):
    """
    Das ist der eigentliche Fehler hinter "nach jedem Neustart wieder
    abgemeldet": schlaegt die Zustellung einer Nachricht fehl, bleibt
    sie in der Warteschlange des Addons und wird alle fuenf Sekunden
    erneut versucht (core/sync_manager.py). Die Schwelle von drei
    Ablehnungen war damit genauso schnell erreicht wie die Schwelle
    von eins, gegen die sie geschrieben wurde.
    """

    for _ in range(20):

        assert store.note_auth_rejected() is False

        uhr["jetzt"] += 5.0

    assert store.load() is not None


def test_drei_getrennte_vorfaelle_heben_auf(store, uhr):

    for _ in range(AUTH_REJECTIONS_BEFORE_UNLINK - 1):

        assert store.note_auth_rejected() is False

        uhr["jetzt"] += AUTH_REJECTION_COOLDOWN + 1

    assert store.note_auth_rejected() is True

    assert store.load() is None


def test_alle_clients_zaehlen_auf_denselben_stand(store, uhr):
    """
    Jeder Client (Charaktere, Roster, WeakAuras, ...) legt sich einen
    eigenen Store an. Wuerde jeder fuer sich zaehlen, braeuchte es die
    Schwelle je Client - und die Absicht waere dahin.
    """

    zweiter = DiscordAccountStore()
    dritter = DiscordAccountStore()

    assert store.note_auth_rejected() is False

    uhr["jetzt"] += AUTH_REJECTION_COOLDOWN + 1

    assert zweiter.note_auth_rejected() is False

    uhr["jetzt"] += AUTH_REJECTION_COOLDOWN + 1

    assert dritter.note_auth_rejected() is True

    assert store.load() is None


def test_vereinzelte_401_ueber_tage_summieren_sich_nicht(store, uhr):
    """
    Ein 401 heute und eines naechste Woche sind kein Muster, sondern
    zwei Zufaelle. Nur was innerhalb des Fensters zusammenfaellt,
    zaehlt zusammen.
    """

    for _ in range(AUTH_REJECTIONS_BEFORE_UNLINK * 3):

        assert store.note_auth_rejected() is False

        uhr["jetzt"] += AUTH_REJECTION_WINDOW + 1

    assert store.load() is not None


def test_ein_erfolgreicher_login_faengt_neu_an(store, uhr):
    """
    `clear()` setzt den Zaehler zurueck - sonst haette eine
    frisch hergestellte Verknuepfung die Ablehnungen der alten geerbt
    und waere beim ersten Fehlschlag sofort wieder weg.
    """

    store.note_auth_rejected()

    uhr["jetzt"] += AUTH_REJECTION_COOLDOWN + 1

    store.note_auth_rejected()

    store.clear()

    store.save({"discord_id": "1", "companion_token": "wc1.ccc.ddd"})

    uhr["jetzt"] += AUTH_REJECTION_COOLDOWN + 1

    assert store.note_auth_rejected() is False

    assert store.load() is not None


# --------------------------------------------------
# Was als "verknuepft" gilt
# --------------------------------------------------


def test_ohne_companion_token_gilt_nichts_als_verknuepft():
    """
    Jeder Client verlangt `companion_token`. Zaehlte die Oberflaeche
    stattdessen "steht da irgendetwas", meldete sie "Verbunden als …"
    zu einem Eintrag, mit dem kein einziger Abruf laeuft.
    """

    assert is_usable(KONTO) is True

    assert is_usable({"username": "Weint"}) is False
    assert is_usable({"companion_token": "  "}) is False
    assert is_usable(None) is False
    assert is_usable([]) is False


def test_eine_antwort_ohne_token_wird_nicht_abgelegt(store):

    with pytest.raises(DiscordAccountError):
        store.save({"username": "Weint"})

    #
    # Und die bestehende Verknuepfung bleibt, wo sie ist.
    #

    assert store.load()["companion_token"] == KONTO["companion_token"]


def test_is_linked_folgt_derselben_regel(store):

    assert store.is_linked() is True

    store.clear()

    assert store.is_linked() is False


# --------------------------------------------------
# Die Datei selbst
# --------------------------------------------------


def test_eine_abgebrochene_schreibung_kostet_die_anmeldung_nicht(store):
    """
    Der zweite Weg zu "nach dem Neustart wieder abgemeldet": `"w"`
    kuerzt die Datei sofort auf null Byte. Ein Absturz oder ein
    erzwungener Neustart dazwischen hinterlaesst eine leere Datei -
    und die war von "noch nie verknuepft" nicht zu unterscheiden.
    """

    store.file.write_text("", encoding="utf-8")

    assert store.load() == KONTO

    #
    # Und sie steht danach wieder richtig da, statt beim naechsten
    # Start erneut aus der Sicherung geholt zu werden.
    #

    assert json.loads(store.file.read_text(encoding="utf-8")) == KONTO


def test_eine_halb_geschriebene_datei_wird_erkannt(store):

    store.file.write_text('{"discord_id": "1", "compa', encoding="utf-8")

    assert store.load() == KONTO


def test_null_ist_kein_konto(store):

    store.file.write_text("null", encoding="utf-8")

    store.backup.unlink()

    assert store.load() is None


def test_geschrieben_wird_ohne_zwischenzustand(store, monkeypatch):
    """
    Die neue Fassung entsteht daneben und wird erst dann an ihren
    Platz gehoben. Bricht das Schreiben ab, steht weiter die alte
    Fassung da - nie eine halbe.
    """

    def platzt(*args, **kwargs):
        raise OSError("kein Platz")

    monkeypatch.setattr("core.discord_account.os.replace", platzt)

    with pytest.raises(DiscordAccountError):
        store.save({"discord_id": "2", "companion_token": "wc1.neu"})

    assert store.load()["companion_token"] == KONTO["companion_token"]


def test_trennen_raeumt_auch_die_sicherung_weg(store):
    """
    Sonst holte der naechste Start die gerade getrennte Verknuepfung
    aus der Sicherung zurueck.
    """

    assert store.backup.exists()

    store.clear()

    assert store.backup.exists() is False

    assert store.load() is None
