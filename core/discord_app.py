"""
Die Discord-Anwendung auf diesem Rechner finden und einen Deep-Link
an sie übergeben.

**Warum eine eigene Datei.** `core/browser.py` hat unter Linux
`xdg-open discord://-/channels/…` aufgerufen und dessen Rückgabewert
als Antwort auf die Frage gelesen, ob es für dieses Schema überhaupt
ein Programm gibt. Das ist er nicht. Ist für
`x-scheme-handler/discord` nichts eingetragen, reicht xdg-open die
Adresse an den Standard-Browser weiter und meldet 0 - erfolgreich
gestartet, nur eben das Falsche. Der Browser wiederum kennt das
Schema nicht und macht daraus `http://discord//-/channels/…`, eine
Adresse, die es nirgends gibt. Genau das war zu sehen: ein
Browserfenster mit einem kaputten Link, während Discord daneben lief.

Derselbe Fehlschluss noch einmal in klein: Firefox legt für ein
einmal bestätigtes "Anwendung wählen" eine eigene
`userapp-Discord-XXXX.desktop` an, deren `Exec` auf **Firefox**
zeigt. Ein Blick auf den Namen des Eintrags hätte also "Discord"
gesagt und wieder den Browser gestartet.

Deshalb wird hier nicht mehr gefragt, ob ein Start geklappt hat,
sondern **vorher**, wohin er ginge:

1. Ist für das Schema ein Programm eingetragen und zeigt dessen
   `Exec`-Zeile auf einen Discord-Client? Dann gilt der Weg des
   Systems - er berücksichtigt auch, dass jemand Vesktop oder WebCord
   statt des offiziellen Clients benutzt. Ein eingetragener Browser
   wird ausdrücklich verworfen; das ist der Fall oben.
2. Sonst wird die Anwendung selbst gesucht: ein Programm im PATH,
   Flatpak, ein `.desktop`-Eintrag, eine AppImage in den üblichen
   Ordnern (auch in dem, aus dem WeintCompanion selbst gestartet
   wurde - AppImages liegen meist beieinander).
3. Findet sich nichts, wird `False` gemeldet, und der Aufrufer bleibt
   beim Browser - dann aber mit der **https**-Adresse, die dort auch
   wirklich funktioniert.

Der Start läuft über `Popen` und nicht über `run()`: Discord ist ein
Fenster, kein Befehl - `run()` würde warten, bis der Nutzer es wieder
schließt, und das im Hauptthread. Läuft bereits eine Instanz,
übernimmt deren Einzelinstanz-Sperre die Adresse und wechselt in den
Kanal; sonst startet sie und öffnet ihn nach der Anmeldung.

Windows und macOS behalten den Öffner des Systems als ersten Weg:
dort meldet er einen fehlenden Eintrag auch wirklich
(`os.startfile` wirft, `open` antwortet ungleich 0). Erst danach wird
auch dort die Anwendung selbst gesucht, damit eine vorhandene
Installation ohne Schema-Eintrag nicht im Browser endet.
"""

from __future__ import annotations

from pathlib import Path
import os
import shlex
import shutil
import subprocess

from core.runtime import Runtime


SCHEME = "discord"


#
# Eine Abfrage ans System antwortet in Sekundenbruchteilen; hängt sie
# doch, darf sie nicht die Oberfläche mitnehmen (der Aufruf läuft im
# Hauptthread).
#

QUERY_TIMEOUT = 5


#
# Woran ein Discord-Client zu erkennen ist. Geprüft wird damit die
# `Exec`-Zeile eines Eintrags, nicht sein Name - siehe der
# Firefox-Fall im Kopf dieser Datei.
#
# Die inoffiziellen Clients stehen bewusst mit drin: wer Vesktop
# benutzt, hat für `discord://` genau diesen eingetragen, und ihn zu
# verwerfen hieße, ihn zugunsten des Browsers zu übergehen.
#

CLIENT_NAMES = (
    "discord",
    "vesktop",
    "webcord",
    "armcord",
    "legcord",
    "goofcord",
    "dorion",
)


#
# Programme im PATH, in dieser Reihenfolge. Der offizielle Client
# zuerst; `Discord` mit großem D kommt bei entpackten tar.gz-Ablagen
# vor.
#

BINARIES = (
    "discord",
    "Discord",
    "discord-canary",
    "discord-ptb",
    "vesktop",
    "webcord",
    "armcord",
    "legcord",
)


#
# Feste Orte, die nicht im PATH stehen müssen: Snap exportiert nach
# /snap/bin (dort meist doch im PATH), Flatpak nach exports/bin, und
# die offiziellen tar.gz-Pakete landen üblicherweise unter /opt.
#

BINARY_PATHS = (
    "/snap/bin/discord",
    "/var/lib/flatpak/exports/bin/com.discordapp.Discord",
    "~/.local/share/flatpak/exports/bin/com.discordapp.Discord",
    "/opt/discord/Discord",
    "/opt/Discord/Discord",
    "/usr/share/discord/Discord",
)


FLATPAK_IDS = (
    "com.discordapp.Discord",
    "com.discordapp.DiscordCanary",
    "dev.vencord.Vesktop",
    "io.github.spacingbat3.webcord",
)


DESKTOP_IDS = (
    "discord.desktop",
    "com.discordapp.Discord.desktop",
    "discord-canary.desktop",
    "discord-ptb.desktop",
    "vesktop.desktop",
    "dev.vencord.Vesktop.desktop",
    "webcord.desktop",
    "io.github.spacingbat3.webcord.desktop",
)


#
# Wo eine AppImage liegen kann. Der Ordner der eigenen AppImage kommt
# in `_appimage_dirs()` dazu - wer WeintCompanion so benutzt, hat
# Discord mit einiger Wahrscheinlichkeit daneben liegen.
#

APPIMAGE_DIRS = (
    "~/Applications",
    "~/.local/bin",
    "~/bin",
    "~/Downloads",
    "~/Desktop",
    "/opt",
    "/usr/local/bin",
)


# --------------------------------------------------
# Kleine Helfer
# --------------------------------------------------


def _query(command: list[str]):
    """
    Eine kurze Abfrage ans System. `None`, wenn sie nicht beantwortet
    werden konnte - ein fehlendes Werkzeug ist hier kein Fehler,
    sondern eine Auskunft weniger.
    """

    try:

        return subprocess.run(
            command,
            env=Runtime.clean_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=QUERY_TIMEOUT,
        )

    except Exception:

        return None


def _is_client(exec_line: str) -> bool:

    lowered = str(exec_line or "").lower()

    return any(name in lowered for name in CLIENT_NAMES)


def _executable(path: Path) -> bool:

    try:
        return path.is_file() and os.access(path, os.X_OK)

    except OSError:
        return False


def _data_dirs() -> list[Path]:
    """
    Die Verzeichnisse, in denen `.desktop`-Einträge liegen - nach der
    XDG-Reihenfolge, die auch das System benutzt.
    """

    raw = [
        os.environ.get("XDG_DATA_HOME", "~/.local/share"),
        *os.environ.get(
            "XDG_DATA_DIRS",
            "/usr/local/share:/usr/share",
        ).split(":"),
        #
        # Flatpak exportiert hierhin. Beide Pfade stehen normalerweise
        # in XDG_DATA_DIRS, aber eben nicht in jeder Sitzung - und ein
        # fehlender Ordner kostet hier nichts.
        #
        "~/.local/share/flatpak/exports/share",
        "/var/lib/flatpak/exports/share",
    ]

    folders: list[Path] = []

    for entry in raw:

        entry = str(entry).strip()

        if not entry:
            continue

        folder = Path(entry).expanduser() / "applications"

        if folder not in folders:
            folders.append(folder)

    return folders


def desktop_file(name: str) -> Path | None:
    """
    Der `.desktop`-Eintrag zu einem Namen, oder `None`.
    """

    entry = str(name or "").strip()

    if not entry:
        return None

    for folder in _data_dirs():

        candidate = folder / entry

        try:

            if candidate.is_file():
                return candidate

        except OSError:
            continue

    return None


def exec_line(path: Path) -> str:
    """
    Die `Exec`-Zeile aus `[Desktop Entry]`.

    Bewusst nur aus diesem Abschnitt: die `[Desktop Action …]`-Blöcke
    darunter haben eigene `Exec`-Zeilen ("Neues Fenster"), die eine
    übergebene Adresse nicht annehmen.
    """

    try:
        text = path.read_text(encoding="utf-8", errors="replace")

    except OSError:
        return ""

    inside = False

    for line in text.splitlines():

        stripped = line.strip()

        if stripped.startswith("["):

            inside = stripped == "[Desktop Entry]"

            continue

        if inside and stripped.startswith("Exec="):

            return stripped[len("Exec="):].strip()

    return ""


def _expand(line: str, url: str) -> list[str]:
    """
    Aus einer `Exec`-Zeile den Aufruf mit der Adresse machen.

    Die Platzhalter der Desktop-Entry-Spezifikation werden ersetzt
    (`%u`/`%U`/`%f`/`%F`) oder verworfen; die
    `@@`-Markierungen des Flatpak-Dateiweiterreichens ebenso. Kommt
    kein Platzhalter vor, hängt die Adresse hinten an - ein Client,
    der sie nicht erwartet, ignoriert sie, während sie ohne diesen
    Zusatz sicher verloren wäre.
    """

    try:
        parts = shlex.split(str(line or ""))

    except ValueError:
        return []

    argv: list[str] = []

    carried = False

    for part in parts:

        if part in ("%u", "%U", "%f", "%F"):

            argv.append(url)

            carried = True

            continue

        if part in ("@@", "@@u"):
            continue

        if part.startswith("%"):
            continue

        argv.append(part)

    if not argv:
        return []

    if not carried:
        argv.append(url)

    return argv


# --------------------------------------------------
# Die einzelnen Fundstellen
# --------------------------------------------------


def scheme_handler() -> str:
    """
    Der für `discord://` eingetragene Programm-Eintrag, oder "".
    """

    if not shutil.which("xdg-mime"):
        return ""

    result = _query(
        ["xdg-mime", "query", "default", f"x-scheme-handler/{SCHEME}"]
    )

    if result is None or result.returncode != 0:
        return ""

    for line in (result.stdout or "").splitlines():

        entry = line.strip()

        if entry:
            return entry

    return ""


def _from_scheme_handler(url: str) -> list[str]:

    path = desktop_file(scheme_handler())

    if path is None:
        return []

    line = exec_line(path)

    #
    # Der Kern der Sache: eingetragen heißt nicht "ist Discord". Ein
    # Browser (oder Firefox' eigener userapp-Eintrag) wird hier
    # verworfen, statt gestartet zu werden.
    #

    if not _is_client(line):
        return []

    return _expand(line, url)


def _from_path(url: str) -> list[str]:

    for name in BINARIES:

        found = shutil.which(name)

        if found:
            return [found, url]

    for name in BINARY_PATHS:

        path = Path(name).expanduser()

        if _executable(path):
            return [str(path), url]

    return []


def _from_flatpak(url: str) -> list[str]:

    if not shutil.which("flatpak"):
        return []

    result = _query(
        ["flatpak", "list", "--app", "--columns=application"]
    )

    if result is None or result.returncode != 0:
        return []

    installed = {
        line.strip()
        for line in (result.stdout or "").splitlines()
        if line.strip()
    }

    for app in FLATPAK_IDS:

        if app in installed:
            return ["flatpak", "run", app, url]

    return []


def _from_desktop_entries(url: str) -> list[str]:

    for name in DESKTOP_IDS:

        path = desktop_file(name)

        if path is None:
            continue

        argv = _expand(exec_line(path), url)

        if argv:
            return argv

    return []


def _appimage_dirs() -> list[Path]:

    folders = [Path(entry).expanduser() for entry in APPIMAGE_DIRS]

    try:

        own = Runtime.current_executable().parent

        if own not in folders:
            folders.insert(0, own)

    except Exception:
        pass

    return folders


def _from_appimage(url: str) -> list[str]:
    """
    Eine Discord-AppImage in den üblichen Ordnern.

    Absichtlich zuletzt: liegt eine richtige Installation vor, ist
    die der bessere Weg. Eine bloß heruntergeladene Datei ist der
    Fall, den sonst niemand abdeckt - und der, nach dem hier gefragt
    wurde.
    """

    for folder in _appimage_dirs():

        try:
            entries = sorted(folder.iterdir())

        except OSError:
            continue

        for entry in entries:

            if entry.suffix.lower() != ".appimage":
                continue

            if not _is_client(entry.stem):
                continue

            if _executable(entry):
                return [str(entry), url]

    return []


# --------------------------------------------------
# Windows und macOS
# --------------------------------------------------


def _windows_launcher(url: str) -> list[str]:
    """
    Discord installiert sich nach `%LOCALAPPDATA%\\Discord\\app-<ver>`
    und legt neben der neuen die alte Fassung ab. Gefragt ist die
    neueste, also die letzte in der Sortierung nach Versionsnummer.
    """

    local = os.environ.get("LOCALAPPDATA", "")

    if not local:
        return []

    from core.version import parse_version

    for folder in ("Discord", "DiscordCanary", "DiscordPTB"):

        base = Path(local) / folder

        try:
            versions = sorted(
                (
                    entry
                    for entry in base.glob("app-*")
                    if entry.is_dir()
                ),
                key=lambda entry: parse_version(entry.name[4:]),
            )

        except OSError:
            continue

        for entry in reversed(versions):

            exe = entry / "Discord.exe"

            if exe.is_file():
                return [str(exe), url]

    return []


def _macos_launcher(url: str) -> list[str]:

    for name in ("Discord", "Discord Canary", "Discord PTB"):

        for base in ("/Applications", "~/Applications"):

            app = Path(base).expanduser() / f"{name}.app"

            try:

                if app.is_dir():
                    return ["open", "-a", str(app), url]

            except OSError:
                continue

    return []


def _system_open(url: str) -> bool:
    """
    Der Öffner des Systems - nur dort, wo er einen fehlenden Eintrag
    auch meldet: `os.startfile` wirft unter Windows, `open` antwortet
    unter macOS mit einem Rückgabewert ungleich 0.

    Unter Linux ist das ausdrücklich **nicht** der Fall, weshalb
    xdg-open hier gar nicht erst vorkommt.
    """

    try:

        if Runtime.is_windows():

            with Runtime.clean_environ():

                os.startfile(url)  # noqa: S606 - Schema, kein Pfad

            return True

        if Runtime.is_macos():

            result = subprocess.run(
                ["open", url],
                env=Runtime.clean_subprocess_env(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=QUERY_TIMEOUT,
            )

            return result.returncode == 0

    except Exception:
        return False

    return False


# --------------------------------------------------
# Suchen und starten
# --------------------------------------------------


def find_launcher(url: str) -> list[str]:
    """
    Der vollständige Aufruf, mit dem die Discord-Anwendung diese
    Adresse öffnet - oder eine leere Liste, wenn es auf diesem
    Rechner keine gibt.
    """

    address = str(url or "").strip()

    if not address:
        return []

    if Runtime.is_windows():
        return _windows_launcher(address)

    if Runtime.is_macos():
        return _macos_launcher(address)

    for source in (
        _from_scheme_handler,
        _from_path,
        _from_flatpak,
        _from_desktop_entries,
        _from_appimage,
    ):

        try:
            argv = source(address)

        except Exception:

            #
            # Eine einzelne Fundstelle darf die Suche nicht beenden -
            # die nächste kennt die Anwendung vielleicht.
            #

            continue

        if argv:
            return argv

    return []


def _launch(argv: list[str], logger=None) -> bool:
    """
    Starten und nicht warten.

    `start_new_session=True`, damit Discord nicht mitstirbt, wenn
    WeintCompanion beendet wird oder ein Signal bekommt.
    """

    try:

        subprocess.Popen(
            argv,
            env=Runtime.clean_subprocess_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    except Exception as exc:

        if logger is not None:

            logger.info(
                f"Discord-Anwendung ließ sich nicht starten ({exc}) - "
                "es geht im Browser weiter."
            )

        return False

    if logger is not None:
        logger.info(f"Discord-Anwendung geöffnet: {argv[0]}")

    return True


def open_link(url: str, logger=None) -> bool:
    """
    Öffnet einen `discord://`-Link in der Anwendung auf diesem
    Rechner. `False`, wenn es keine gibt - dann übernimmt der
    Browser.
    """

    address = str(url or "").strip()

    if not address:
        return False

    #
    # Windows und macOS zuerst über das System: dort ist der
    # eingetragene Weg verlässlich und respektiert eine Installation
    # an einem ungewöhnlichen Ort.
    #

    if (Runtime.is_windows() or Runtime.is_macos()) and _system_open(
        address
    ):
        return True

    argv = find_launcher(address)

    if not argv:

        if logger is not None:

            logger.info(
                "Keine Discord-Anwendung gefunden - der Link geht an "
                "den Browser."
            )

        return False

    return _launch(argv, logger)
