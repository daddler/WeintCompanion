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
    """

    def prepare(
        self,
        installer: Path,
        pid: int,
    ) -> Path:

        script = (
            "@echo off\r\n"
            ":wait\r\n"
            f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL\r\n'
            "if not errorlevel 1 (\r\n"
            "    timeout /t 1 /nobreak >NUL\r\n"
            "    goto wait\r\n"
            ")\r\n"
            f'start "" "{installer}"\r\n'
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
