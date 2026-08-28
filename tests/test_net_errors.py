"""
Warum der Bot nicht erreichbar ist - und warum das nicht als
Systemmeldung dastehen darf.

Der Fehlerbericht, der zu diesem Modul führte, war ein Bildschirmfoto
von "Einstellungen -> Discord" mit dem Satz

    Der letzte Versuch ist fehlgeschlagen: [Errno -2] Der Name oder
    der Dienst ist nicht bekannt

Die Anmeldung im Browser war tadellos durchgelaufen; gescheitert ist
erst der Austausch beim Bot, weil dessen Name im DNS nicht mehr
existierte. In dem Satz kommt nichts davon vor: nicht die Adresse,
nicht der Umstand, dass Discord unbeteiligt ist, und nicht der
Ausweg. Diese Tests halten fest, dass alle drei drinstehen.
"""

import socket

from core import net_errors


ADRESSE = "https://weintcodex-bot.example.app"


def _wie_httpx(meldung: str = "[Errno -2] Name or service not known"):
    """
    Ein Nachbau dessen, was `httpx` liefert: eine eigene Klasse, die
    den Auflösungsfehler als Ursache trägt. Bewusst ohne `httpx` -
    das Modul soll ohne Netzbibliothek prüfbar bleiben, aus
    demselben Grund, aus dem es keine importiert.
    """

    ursache = socket.gaierror(-2, "Name or service not known")

    aussen = OSError(meldung)

    aussen.__cause__ = ursache

    return aussen


# --------------------------------------------------
# Erkennung
# --------------------------------------------------

def test_der_auflösungsfehler_wird_erkannt():

    assert net_errors.is_dns_failure(_wie_httpx())


def test_auch_ohne_ursache_in_der_kette():
    """
    Nicht jede Fassung von `httpx` hängt das Original als `__cause__`
    an - dann bleibt nur der Text, und der kommt vom Betriebssystem.
    """

    assert net_errors.is_dns_failure(
        OSError("[Errno -2] Name or service not known")
    )


def test_die_deutsche_systemmeldung_zaehlt_ebenso():
    """
    Genau die Fassung aus dem Fehlerbericht. Sie kommt vom
    Betriebssystem und steht deshalb in dessen Sprache.
    """

    assert net_errors.is_dns_failure(
        OSError(
            "[Errno -2] Der Name oder der Dienst ist nicht bekannt"
        )
    )


def test_ein_verbindungsfehler_ist_kein_auflösungsfehler():
    """
    Der Unterschied trägt die ganze Aussage: ein abgewiesener
    Verbindungsversuch heisst "der Bot läuft gerade nicht", ein
    Auflösungsfehler heisst "diese Adresse gibt es nicht mehr". Der
    nächste Schritt ist ein völlig anderer.
    """

    assert not net_errors.is_dns_failure(
        ConnectionRefusedError(111, "Connection refused")
    )

    assert not net_errors.is_dns_failure(None)


def test_eine_zeitueberschreitung_wird_getrennt_beurteilt():

    assert net_errors.is_timeout(TimeoutError("read timed out"))

    assert not net_errors.is_timeout(_wie_httpx())


def test_eine_ringfoermige_kette_haengt_nicht():
    """
    Diese Funktion läuft in einem Fehlerpfad. Dort selbst
    hängenzubleiben wäre der schlechtere Fehler.
    """

    a = OSError("a")
    b = OSError("b")

    a.__cause__ = b
    b.__cause__ = a

    assert net_errors.is_dns_failure(a) is False


# --------------------------------------------------
# Der Satz
# --------------------------------------------------

def test_der_text_nennt_die_adresse():
    """
    Sie ist das einzige, woran sich ein Umzug erkennen lässt.
    """

    text = net_errors.bot_unreachable_text(_wie_httpx(), ADRESSE)

    assert ADRESSE in text


def test_der_text_entlastet_die_anmeldung():
    """
    Wer die Systemmeldung liest, sucht den Fehler bei Discord oder
    bei sich. Beide sind unbeteiligt, und das muss dastehen.
    """

    text = net_errors.bot_unreachable_text(_wie_httpx(), ADRESSE)

    assert "Discord-Anmeldung" in text


def test_der_text_nennt_den_naechsten_schritt():

    text = net_errors.bot_unreachable_text(_wie_httpx(), ADRESSE)

    assert "Adresse des Bots" in text
    assert "neu" in text


def test_die_systemmeldung_steht_nicht_mehr_allein_da():

    text = net_errors.bot_unreachable_text(_wie_httpx(), ADRESSE)

    assert "Errno" not in text


def test_ein_anderer_netzfehler_bekommt_seinen_eigenen_satz():
    """
    Ein abgewiesener Verbindungsversuch darf nicht als Umzug erklärt
    werden - dann suchte man eine neue Adresse für einen Bot, der
    schlicht gerade nicht läuft.
    """

    text = net_errors.bot_unreachable_text(
        ConnectionRefusedError(111, "Connection refused"),
        ADRESSE,
    )

    assert "nicht auflösen" not in text
    assert ADRESSE in text


def test_ohne_angabe_gilt_die_aktuelle_adresse():

    from core.backend_config import BOT_BASE_URL

    assert BOT_BASE_URL in net_errors.bot_unreachable_text(_wie_httpx())


def test_der_hinweis_nennt_beide_wege():

    hinweis = net_errors.override_hint()

    assert "WEINTCODEX_BOT_URL" in hinweis
    assert "bot_url.txt" in hinweis
