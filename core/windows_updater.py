from pathlib import Path
import tempfile


class WindowsUpdater:
    """
    Erstellt ein kleines Wartescript, das erst startet,
    nachdem WeintCompanion.exe wirklich beendet wurde.

    Hintergrund:
    Der Windows-Installer (Inno Setup) überschreibt
    WeintCompanion.exe und die zugehörigen DLLs im
    Installationsverzeichnis. Solange der alte Prozess noch
    läuft (oder gerade erst dabei ist, sich zu beenden),
    sind diese Dateien von Windows gesperrt ("file in use").
    Ein fester, kurzer Delay (z. B. 1 Sekunde) reicht dafür
    nicht zuverlässig aus - je nach System kann das Beenden
    von Qt/Python länger dauern.

    Deshalb wird der Installer nicht direkt gestartet,
    sondern über ein Batch-Skript, das aktiv per PID prüft,
    ob der alte Prozess wirklich beendet wurde, bevor der
    Installer läuft.

    WICHTIG zum Warten zwischen den Prüfungen: Absichtlich
    "ping -n 2 127.0.0.1" statt "timeout /t 1 /nobreak".
    "timeout" braucht ein Konsolen-Handle, um auf STRG+C zu
    prüfen - läuft das Skript (z. B. wegen fehlerhafter
    Creation-Flags des aufrufenden Prozesses) ohne eigene
    Konsole, erzeugt "timeout" sich selbst ein neues,
    sichtbares und scheinbar eingefrorenes Konsolenfenster.
    "ping" braucht dafür keine Konsoleninteraktion und wartet
    zuverlässig auch dann, wenn keine (sichtbare) Konsole
    vorhanden ist.
    """

    def prepare(
        self,
        installer: Path,
        pid: int,
    ) -> Path:

        #
        # /VERYSILENT + /SUPPRESSMSGBOXES + /NORESTART: Ohne diese
        # Flags öffnet sich der volle Inno-Setup-Wizard, durch den der
        # Nutzer manuell klicken muss - startet dieses Fenster im
        # Hintergrund oder wird schlicht übersehen, sieht das Update
        # aus wie "es passiert nichts". Der Installer relauncht die App
        # danach selbst (siehe installer.iss, [Run]-Sektion).
        #

        script = (
            "@echo off\r\n"
            ":wait\r\n"
            f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL\r\n'
            "if not errorlevel 1 (\r\n"
            "    ping -n 2 127.0.0.1 >NUL\r\n"
            "    goto wait\r\n"
            ")\r\n"
            f'start "" "{installer}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART\r\n'
            'del "%~f0"\r\n'
        )

        target = (
            Path(tempfile.gettempdir())
            / "weintcompanion_update.bat"
        )

        target.write_text(
            script,
            encoding="utf-8",
        )

        return target
