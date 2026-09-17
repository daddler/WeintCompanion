"""
Die Uebergabe: neue Anwendung bereitstellen und starten.

GRUNDSATZ
---------

**Erst V5 bereitstellen, dann V4 ablösen - und "ablösen" heisst hier
nie "löschen".** Diese Datei fasst die laufende Installation von
WeintCompanion an keiner Stelle an: sie schreibt nichts in deren
Ordner, benennt nichts um, deinstalliert nichts. Companion-Forever
ist ein anderes Produkt mit einem anderen Namen; die beiden koennen
nebeneinander liegen, und genau das ist der Rueckfallweg. Schlaegt
irgendetwas fehl, startet der Nutzer weiter seine 4.x, als waere
nichts gewesen.

Das ist der Unterschied zum Selbstupdate (`core/linux_updater.py`,
`core/windows_updater.py`): dort **muss** die laufende Datei ersetzt
werden, und der ganze Aufwand mit Wartescript und Prozess-PID
entsteht nur deswegen. Hier entfaellt er - niemand muss warten, bis
sich WeintCompanion beendet hat, weil nichts gesperrt ist.

ZWEI PLATTFORMEN, EIN ABLAUF
----------------------------

    Linux    AppImage neben die laufende legen, ausfuehrbar machen, starten
    Windows  Installer still ausfuehren, er startet die neue App selbst

Der Ablauf ist derselbe (`prepare` -> `install` -> `launch`), der
Inhalt der drei Schritte steht je einmal pro Plattform in dieser
Datei. Kein `if sys.platform` ausserhalb davon.

WAS DER RELEASE-VERTRAG DAFUER VERLANGT
---------------------------------------

Der Windows-Installer muss `/VERYSILENT /SUPPRESSMSGBOXES
/NORESTART` verstehen und die Anwendung danach **selbst** starten
(also `[Run]` ohne `skipifsilent`, genau wie
`packaging/installer.iss` dieser App). Steht in
`docs/companion-forever-release-contract.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import stat
import subprocess

from core.migration.assets import LINUX, WINDOWS, PlatformProfile
from core.paths import Paths
from core.process_spawn import spawn_detached
from core.runtime import Runtime


#
# Wie lange der Windows-Installer hoechstens laufen darf, bevor der
# Wechsel als fehlgeschlagen gilt. Grosszuegig - ein
# Virenscanner-Durchlauf mitten in der Installation ist keine
# Seltenheit.
#

INSTALL_TIMEOUT = 600


class HandoverError(Exception):

    def __init__(self, code: str, message: str):

        super().__init__(message)

        self.code = code
        self.message = message


@dataclass
class HandoverResult:

    installed_path: Path | None = None
    launched: bool = False
    detail: str = ""


def install_root() -> Path:
    """
    Wohin die neue Generation unter Linux gelegt wird.

    Neben die laufende AppImage, wenn wir als AppImage laufen - dort
    sucht der Nutzer sie, dort liegt seine bisherige. Sonst (aus dem
    Quelltext gestartet) in den Datenordner dieser App, damit ein
    Probelauf auf einem Entwicklerrechner nichts in fremden Ordnern
    ablegt.
    """

    if Runtime.is_linux() and Runtime.is_appimage():
        return Runtime.current_executable().parent

    path = Paths.base() / "forever"

    path.mkdir(parents=True, exist_ok=True)

    return path


class Handover:
    """
    Der Uebergabeschritt, plattformabhaengig - aber von aussen
    ueberall gleich.

    `dry_run` fuehrt alles bis zur letzten Zeile aus (Datei an ihren
    Platz legen, Rechte setzen), nur Installation und Start
    unterbleiben. So laesst sich der ganze Weg pruefen, ohne eine
    zweite Anwendung auf dem Rechner zu haben.
    """

    def __init__(self, profile: PlatformProfile, logger=None, dry_run: bool = False):

        self.profile = profile
        self.logger = logger
        self.dry_run = dry_run

    # --------------------------------------------------

    def _log(self, level: str, message: str) -> None:

        if self.logger is None:
            return

        getattr(self.logger, level, self.logger.info)(message)

    # --------------------------------------------------

    def run(self, downloaded: Path) -> HandoverResult:

        downloaded = Path(downloaded)

        if not downloaded.exists() or downloaded.stat().st_size == 0:

            raise HandoverError(
                "EMPTY_DOWNLOAD",
                "Die heruntergeladene Datei fehlt oder ist leer.",
            )

        if self.profile is LINUX:
            return self._run_linux(downloaded)

        if self.profile is WINDOWS:
            return self._run_windows(downloaded)

        raise HandoverError(
            "UNSUPPORTED_PLATFORM",
            "Fuer diese Plattform gibt es keinen Uebergabeweg.",
        )

    # --------------------------------------------------
    # Linux
    # --------------------------------------------------

    def _run_linux(self, downloaded: Path) -> HandoverResult:

        target = install_root() / downloaded.name

        #
        # Erst daneben, dann an den Platz: bricht das Kopieren ab,
        # liegt kein halbes Programm unter dem endgueltigen Namen -
        # dieselbe Regel wie bei jedem anderen Schreibvorgang dieser
        # App.
        #

        staging = target.with_name(target.name + ".part")

        try:

            if staging.exists():
                staging.unlink()

            shutil.copy2(downloaded, staging)

            staging.chmod(
                staging.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

            staging.replace(target)

        except OSError as exc:

            raise HandoverError(
                "INSTALL_FAILED",
                f"Die neue Anwendung konnte nicht abgelegt werden: {exc}",
            ) from exc

        self._log("info", f"Neue Anwendung liegt unter {target}.")

        if self.dry_run:

            return HandoverResult(
                installed_path=target,
                launched=False,
                detail="Probelauf: die neue Anwendung wurde nicht gestartet.",
            )

        try:

            spawn_detached([str(target)], log_dir=target.parent, logger=self.logger)

        except Exception as exc:

            raise HandoverError(
                "LAUNCH_FAILED",
                f"Die neue Anwendung konnte nicht gestartet werden: {exc}",
            ) from exc

        return HandoverResult(
            installed_path=target,
            launched=True,
            detail="Die neue Anwendung wurde gestartet.",
        )

    # --------------------------------------------------
    # Windows
    # --------------------------------------------------

    def _run_windows(self, downloaded: Path) -> HandoverResult:

        if self.dry_run:

            return HandoverResult(
                installed_path=downloaded,
                launched=False,
                detail="Probelauf: der Installer wurde nicht ausgefuehrt.",
            )

        #
        # Der Installer laeuft hier **synchron** - anders als beim
        # Selbstupdate, wo ein Wartescript noetig ist, weil die
        # eigene EXE gesperrt waere. Nichts ist gesperrt, also kann
        # auf das Ergebnis gewartet werden, und das ist der ganze
        # Unterschied zwischen "installiert" und "gestartet, Ausgang
        # unbekannt".
        #

        command = [
            str(downloaded),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
        ]

        try:

            completed = subprocess.run(
                command,
                timeout=INSTALL_TIMEOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

        except subprocess.TimeoutExpired as exc:

            raise HandoverError(
                "INSTALL_TIMEOUT",
                "Die Installation hat zu lange gedauert und wurde "
                "abgebrochen. Die bisherige Fassung bleibt unveraendert.",
            ) from exc

        except OSError as exc:

            raise HandoverError(
                "INSTALL_FAILED",
                f"Der Installer konnte nicht ausgefuehrt werden: {exc}",
            ) from exc

        if completed.returncode != 0:

            raise HandoverError(
                "INSTALL_FAILED",
                "Die Installation wurde mit dem Fehlercode "
                f"{completed.returncode} beendet. Die bisherige Fassung "
                "bleibt unveraendert.",
            )

        #
        # Den Start uebernimmt der Installer selbst (Release-Vertrag,
        # siehe Modulkommentar). Wir wissen hier nicht, wohin er
        # installiert hat - und zu raten waere schlechter, als es
        # ihn tun zu lassen.
        #

        return HandoverResult(
            installed_path=downloaded,
            launched=True,
            detail="Die Installation ist abgeschlossen.",
        )
