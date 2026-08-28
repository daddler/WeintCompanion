"""
Warum der Bot nicht erreichbar ist - in einem Satz, der den nächsten
Schritt nennt.

Bis 2.4.3 reichte jede Aufrufstelle die Ausnahme durch, die `httpx`
geworfen hatte. Auf dem Bildschirm stand dann

    Der letzte Versuch ist fehlgeschlagen: [Errno -2] Der Name oder
    der Dienst ist nicht bekannt

- eine Meldung des Betriebssystems, in der nichts vorkommt, was
jemand daraufhin tun könnte: nicht die Adresse, die nicht aufgelöst
werden konnte, nicht der Umstand, dass die Anmeldung selbst völlig in
Ordnung war, und schon gar nicht der Ausweg. Wer sie liest, sucht den
Fehler bei Discord oder bei der eigenen Anmeldung, und beide sind
unbeteiligt.

Genau dieser Fall ist der wahrscheinlichste, den die Companion je
erlebt: der Bot liegt bei einem Anbieter, der den Rechner in den
Hostnamen schreibt (siehe `core/backend_config.py`). Zieht er um,
verschwindet der alte Name aus dem DNS - und ab diesem Moment
scheitert **jeder** Abruf mit `[Errno -2]`, ohne dass am Bot, an
Discord oder an der Companion irgendetwas kaputt wäre.

Rein und ohne `httpx`, aus demselben Grund wie
`access_roles.build_profile_payload()`: welcher Satz dort steht, ist
die Stelle, an der etwas falsch sein kann, und die soll ohne Netz
prüfbar bleiben. Erkannt wird deshalb über die Ausnahmekette und
`errno`, nicht über einen `isinstance`-Test auf eine
httpx-Klasse - dieselbe Funktion beurteilt einen Fehler aus
`socket`, `httpx` oder `urllib`.
"""

from __future__ import annotations

import socket

from core.backend_config import BOT_URL_ENV, bot_url_override_path


#
# Die Fehlernummern, die "der Name ist nicht auflösbar" heißen.
# `EAI_NONAME` (-2) ist der Fall aus dem Fehlerbericht; -3
# (`EAI_AGAIN`, "vorübergehend nicht auflösbar") und -5 kommen aus
# derselben Ecke und führen zu genau demselben nächsten Schritt.
#

DNS_ERRNOS = (-2, -3, -5)

#
# Der Rückfall für den Fall, dass die Ausnahmekette nichts hergibt -
# `httpx` verpackt den Auflösungsfehler zwar, aber nicht jede Fassung
# hängt das Original als `__cause__` an. Beide Sprachen, weil die
# Meldung vom Betriebssystem kommt und in dessen Sprache steht.
#

DNS_MARKERS = (
    "name or service not known",
    "name oder der dienst ist nicht bekannt",
    "nodename nor servname",
    "temporary failure in name resolution",
    "getaddrinfo failed",
    "no address associated with hostname",
)


def _chain(exc):
    """
    Die Ausnahme und alles, was sie ausgelöst hat.

    Mit Abbruch nach zehn Gliedern und einer Besuchtliste: eine Kette
    kann sich im Kreis schließen, und diese Funktion läuft in einem
    Fehlerpfad - sie darf dort nicht ihrerseits hängenbleiben.
    """

    gesehen = set()

    aktuell = exc

    while aktuell is not None and len(gesehen) < 10:

        if id(aktuell) in gesehen:
            break

        gesehen.add(id(aktuell))

        yield aktuell

        aktuell = aktuell.__cause__ or aktuell.__context__


def is_dns_failure(exc) -> bool:
    """
    Heißt diese Ausnahme "den Namen gibt es nicht"?
    """

    if exc is None:
        return False

    for glied in _chain(exc):

        if isinstance(glied, socket.gaierror):
            return True

        if getattr(glied, "errno", None) in DNS_ERRNOS:
            return True

        text = str(glied).lower()

        for marker in DNS_MARKERS:

            if marker in text:
                return True

    return False


def is_timeout(exc) -> bool:

    if exc is None:
        return False

    for glied in _chain(exc):

        if isinstance(glied, (socket.timeout, TimeoutError)):
            return True

        if "timeout" in type(glied).__name__.lower():
            return True

    return False


def bot_unreachable_text(exc, address: str = "") -> str:
    """
    Der Satz, der dem Nutzer statt der Systemmeldung angezeigt wird.

    `address` ist die Adresse, unter der es versucht wurde - sie
    gehört in den Text, weil sie das einzige ist, woran sich ein
    Umzug erkennen lässt. Ohne Angabe wird die aktuell gültige
    genommen.
    """

    if not address:

        #
        # Erst hier gelesen und nicht beim Import: eine Angabe, die
        # zur Laufzeit gesetzt wurde, soll in der Meldung stehen und
        # nicht der Wert von vorhin.
        #

        from core.backend_config import BOT_BASE_URL

        address = BOT_BASE_URL

    if is_dns_failure(exc):

        return (
            f"Die Adresse des Bots ({address}) lässt sich im Netz "
            "nicht auflösen - unter diesem Namen ist nichts (mehr) "
            "eingetragen. An deiner Discord-Anmeldung liegt es "
            "nicht.\n\n"
            "Der wahrscheinlichste Grund ist ein Umzug des Bots: "
            "sein Anbieter schreibt den Rechner in den Hostnamen, "
            "eine neue Umgebung heißt deshalb anders. Trage die "
            "aktuelle Adresse unten unter \"Adresse des Bots\" ein "
            "und starte die Companion neu.\n\n"
            "Besteht der Fehler mit der richtigen Adresse fort, ist "
            "die Internetverbindung oder der DNS-Server auf diesem "
            "Rechner die nächste Stelle zum Nachsehen."
        )

    if is_timeout(exc):

        return (
            f"Der Bot ({address}) hat nicht rechtzeitig geantwortet. "
            "Läuft er gerade erst wieder an, ist ein zweiter Versuch "
            "in ein bis zwei Minuten meist erfolgreich."
        )

    return (
        f"Der Bot ist unter {address} nicht erreichbar: {exc}\n\n"
        "Läuft er gerade nicht, hilft nur abwarten. Ist er umgezogen, "
        "trage seine neue Adresse unten unter \"Adresse des Bots\" "
        "ein und starte die Companion neu."
    )


def override_hint() -> str:
    """
    Die beiden Wege, die Adresse ohne neue Fassung zu ändern - für
    Protokoll und Beschreibung, wo kein Eingabefeld daneben steht.
    """

    return (
        f"Umgebungsvariable {BOT_URL_ENV} oder die Datei "
        f"{bot_url_override_path()}"
    )
