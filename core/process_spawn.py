"""
Einen Prozess starten, der das Beenden dieser App ueberlebt.

Der Inhalt dieser Datei stand bis 4.1 in `core/companion_updater.py`
und ist dort ueber drei Vorfaelle gewachsen (systemd-Scope, D-Bus,
Konsolen-Handle unter Windows). Er steht jetzt hier, weil es einen
**zweiten** Aufrufer gibt: der Generationswechsel startet
Companion-Forever genauso, wie das Selbstupdate seinen Updater
startet - und diese Lehren ein zweites Mal aufzuschreiben hiesse,
sie beim naechsten Mal an einer von zwei Stellen zu vergessen.

`CompanionUpdater` ruft weiterhin seine eigenen Methoden auf; sie
sind nur noch duenne Weiterleitungen hierher. Das Verhalten ist
unveraendert.
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

from core.runtime import Runtime


def running_in_systemd_scope() -> bool:
    """
    Laeuft dieser Prozess in einer transienten systemd-Scope?

    Typisch fuer Anwendungen, die ueber GNOME/KDE per Doppelklick
    oder aus dem Dateimanager gestartet wurden. Nur dann besteht das
    Risiko, dass systemd beim Beenden die komplette Cgroup mitsamt
    des gerade gestarteten Kindprozesses killt.
    """

    try:

        cgroup_file = Path("/proc/self/cgroup")

        if not cgroup_file.exists():
            return False

        return ".scope" in cgroup_file.read_text()

    except Exception:

        return False


def has_dbus_session() -> bool:
    """
    Ist eine funktionierende D-Bus-User-Session vorhanden?
    systemd-run braucht sie, um mit `systemd --user` zu sprechen.
    """

    return bool(
        os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        or os.environ.get("XDG_RUNTIME_DIR")
    )


def spawn_detached(args, log_dir=None, logger=None) -> None:
    """
    Startet `args` so, dass es das Beenden dieser App ueberlebt.

    Hintergrund:
    Auf modernen Linux-Desktops (GNOME/KDE unter Fedora, openSUSE,
    CachyOS, ...) wird eine per Doppelklick oder aus dem
    Dateimanager gestartete AppImage haeufig in einer eigenen
    transienten systemd-Scope ausgefuehrt
    ("app-...AppImage@....service"). Beendet sich der Hauptprozess,
    beendet systemd standardmaessig (KillMode=control-group) die
    GESAMTE Cgroup - inklusive aller Kindprozesse. Das betrifft auch
    ein Updater-Skript, selbst wenn es ueber start_new_session=True
    in eine eigene Sitzung gestartet wurde, denn eine neue Session
    aendert nichts an der Cgroup-Zugehoerigkeit.

    Ergebnis: der Kindprozess wird zusammen mit WeintCompanion
    abgeschossen, bevor er seine Arbeit tun kann - der Knopf
    "funktioniert" scheinbar nicht.

    Loesung: ist "systemd-run" verfuegbar, wird der Prozess in eine
    eigene, unabhaengige transiente Scope ausgelagert
    (--user --scope), die das Beenden dieser App uebersteht.

    WICHTIG: systemd-run wird NUR verwendet, wenn wir auch wirklich
    in einer solchen Scope laufen UND eine funktionierende
    D-Bus-User-Session vorhanden ist. Auf schlankeren Setups
    (i3, Sway, Hyprland) laeuft die App oft gar nicht in einer Scope
    und/oder die D-Bus-Umgebung ist unvollstaendig - systemd-run
    wuerde dann im Hintergrund lautlos fehlschlagen ("Failed to
    create bus connection"), und der Kindprozess liefe NIE, ohne
    dass unser Code einen Fehler bemerkt (der Fehler passiert
    asynchron im schon gestarteten Kindprozess).
    """

    if running_in_systemd_scope() and has_dbus_session():

        systemd_run = shutil.which("systemd-run")

        if systemd_run:

            try:

                #
                # WICHTIG fuer die Fehlersuche: systemd-run kann
                # asynchron fehlschlagen, ohne dass Popen() hier
                # etwas wirft. Deshalb wird die Ausgabe in eine
                # Protokolldatei geschrieben, statt sie mit DEVNULL
                # zu verwerfen - so laesst sich ein stiller
                # Fehlschlag im Nachhinein nachvollziehen.
                #

                debug_log = _open_debug_log(args, log_dir)

                subprocess.Popen(
                    [
                        systemd_run,
                        "--user",
                        "--scope",
                        "--collect",
                        "--",
                    ]
                    + list(args),
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=debug_log or subprocess.DEVNULL,
                    stderr=debug_log or subprocess.DEVNULL,
                    #
                    # Siehe Runtime.clean_subprocess_env(): ohne das
                    # vererbt das AppImage-Bundle sein eigenes
                    # LD_LIBRARY_PATH an das gestartete Programm
                    # (und damit an jedes darin aufgerufene
                    # System-Tool wie mv/chmod/bash selbst) -
                    # klassischer "symbol lookup error", der lautlos
                    # abbricht.
                    #
                    env=Runtime.clean_subprocess_env(),
                )

                return

            except Exception as exc:

                if logger is not None:

                    logger.warning(
                        f"systemd-run fehlgeschlagen, nutze Fallback: {exc}"
                    )

    #
    # Normaler Fallback (kein Desktop-Scope, kein systemd oder keine
    # D-Bus-Session - z. B. i3, Sway, Hyprland, oder direkter Start
    # ueber ein Terminal)
    #

    subprocess.Popen(
        list(args),
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=Runtime.clean_subprocess_env(),
    )


def _open_debug_log(args, log_dir):

    try:

        if log_dir is None:

            #
            # Wie bisher: neben der Datei, um die es geht.
            #

            reference = args[1] if len(args) > 1 else args[0]

            log_dir = Path(reference).parent

        return open(
            Path(log_dir) / "systemd-run-debug.log",
            "w",
            encoding="utf-8",
        )

    except Exception:

        return None


def spawn_windows_hidden(args) -> None:
    """
    Startet `args` unsichtbar (kein Konsolenfenster) und unabhaengig
    von dieser App.

    WICHTIG: hier NICHT zusaetzlich DETACHED_PROCESS setzen. Laut
    Win32-Doku wird CREATE_NO_WINDOW ignoriert, wenn es zusammen mit
    DETACHED_PROCESS verwendet wird. Der Kindprozess startet dann
    komplett ohne Konsole - "timeout" (aufgerufen aus einem
    Wartescript) braucht aber ein Konsolen-Handle, um auf STRG+C zu
    pruefen, und erzeugt sich in diesem Fall selbst ein neues,
    sichtbares Konsolenfenster. Genau das ist das eingefrorene
    "timeout /t 1 /nobreak"-Fenster, das Nutzer beim Update sahen.
    CREATE_NO_WINDOW allein reicht: der Kindprozess bekommt eine
    (unsichtbare) Konsole und laeuft unabhaengig weiter, da
    Windows-Kindprozesse ohnehin nicht am Elternprozess haengen.
    """

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        list(args),
        creationflags=creationflags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
