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

**Der dritte Teil ist die Anwendung statt des Browsers.** Ein
Discord-Link im Browser führt in eine zweite, meist abgemeldete
Ansicht desselben Servers - während die Anwendung daneben offen
steht. `open_url()` nimmt deshalb ein optionales `app_url`
(`discord://…`) entgegen und versucht es zuerst. Das darf nicht
blind geschehen: wer Discord nur im Browser nutzt, hat für dieses
Schema kein Programm, und ein stillschweigend verpuffter Aufruf wäre
genau der tote Knopf, gegen den diese Datei geschrieben wurde.
Deshalb wird das Schema nicht über `webbrowser` geöffnet (das meldet
den Fehlschlag nicht), sondern über den Öffner des Systems, dessen
Rückgabewert wir lesen können - und bei Misserfolg geht es im
Browser weiter.
"""

from __future__ import annotations

import os
import subprocess
import webbrowser

from core.runtime import Runtime


#
# Der Systemöffner antwortet in Sekundenbruchteilen; hängt er doch,
# darf er nicht die Oberfläche mitnehmen (der Aufruf läuft im
# Hauptthread).
#

APP_LINK_TIMEOUT = 5


def open_app_link(url: str, logger=None) -> bool:
    """
    Öffnet eine Adresse mit eigenem Schema (`discord://…`) in der
    zuständigen Anwendung. `False`, wenn es keine gibt.

    Je Plattform der Öffner, der einen Fehlschlag auch meldet:
    `os.startfile` wirft unter Windows, wenn kein Programm zugeordnet
    ist, `open` und `xdg-open` antworten mit einem Rückgabewert
    ungleich 0. `webbrowser.open()` sieht dagegen nur, dass es ein
    Hilfsprogramm gestartet hat.
    """

    address = (url or "").strip()

    if not address:
        return False

    try:

        if Runtime.is_windows():

            with Runtime.clean_environ():

                os.startfile(address)  # noqa: S606 - Schema, kein Pfad

            return True

        command = (
            ["open", address]
            if Runtime.is_macos()
            else ["xdg-open", address]
        )

        result = subprocess.run(
            command,
            env=Runtime.clean_subprocess_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=APP_LINK_TIMEOUT,
        )

        return result.returncode == 0

    except Exception as exc:

        if logger is not None:

            #
            # Kein Fehler für den Nutzer: der Browser übernimmt gleich.
            #

            logger.info(
                f"Discord-Anwendung nicht erreichbar ({exc}) - "
                "es geht im Browser weiter."
            )

        return False


def open_url(url: str, logger=None, app_url: str = "") -> bool:
    """
    Öffnet `url` im System-Browser.

    `logger` ist der `Logger` der App (oder `None` in Aufrufen, die
    keinen haben - etwa dem Login-Fluss, der seinen eigenen Ablauf
    protokolliert).

    `app_url` ist dieselbe Adresse für die zuständige Anwendung. Sie
    wird zuerst versucht und der Browser nur dann bemüht, wenn dafür
    kein Programm bereitsteht.
    """

    address = (url or "").strip()

    if not address:
        return False

    if app_url and open_app_link(app_url, logger):
        return True

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
