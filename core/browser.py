"""
Eine Adresse im System-Browser öffnen - an genau einer Stelle.

**Warum eine eigene Datei für zwei Zeilen.** Es gab drei Aufrufer von
`webbrowser.open()` (der Discord-Login, der Feedback-Link unter
Einstellungen → Über und der Knopf "Aufstellung im Discord" der
Übersicht), und zwei davon haben `Runtime.clean_environ()` benutzt.
Der dritte nicht - und genau der war der stille Ausfall: im
AppImage/PyInstaller-Bündel erbt der Browser sonst unser eigenes
`LD_LIBRARY_PATH` und stirbt sofort mit einem "symbol lookup error".
`webbrowser.open()` bemerkt das nicht, wirft nichts und liefert
trotzdem `True`, weil es nur das Starten des Hilfsprogramms sieht.
Für den Nutzer war der Knopf schlicht tot: kein Fenster, keine
Meldung, kein Protokolleintrag.

Eine Regel, die in zwei von drei Aufrufen befolgt wird, ist keine
Regel, sondern eine Erinnerung. Deshalb steht sie hier als Funktion.

Der zweite Teil ist die Rückmeldung: `open_url()` liefert `False`,
wenn kein Browser gestartet werden konnte, und schreibt die Adresse
ins Protokoll. Ein Knopf, der nichts tut, muss wenigstens sagen,
wohin er wollte - dann lässt sich der Link von Hand öffnen.
"""

from __future__ import annotations

import webbrowser

from core.runtime import Runtime


def open_url(url: str, logger=None) -> bool:
    """
    Öffnet `url` im System-Browser.

    `logger` ist der `Logger` der App (oder `None` in Aufrufen, die
    keinen haben - etwa dem Login-Fluss, der seinen eigenen Ablauf
    protokolliert).
    """

    address = (url or "").strip()

    if not address:
        return False

    opened = False

    try:

        with Runtime.clean_environ():

            opened = bool(webbrowser.open(address))

    except Exception as exc:

        if logger is not None:

            logger.error(
                f"Browser konnte nicht geöffnet werden: {exc} "
                f"- Adresse: {address}"
            )

        return False

    if not opened and logger is not None:

        #
        # Kein Fehler, aber auch kein Erfolg: unter Linux ohne
        # `xdg-open`/`BROWSER` findet `webbrowser` schlicht kein
        # Programm. Die Adresse gehört dann ins Protokoll, sonst
        # bleibt es beim wirkungslosen Knopf.
        #

        logger.warning(
            "Kein Browser gefunden - bitte von Hand öffnen: "
            f"{address}"
        )

    return opened
