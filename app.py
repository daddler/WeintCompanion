import faulthandler
import os
import platform
import sys
from pathlib import Path


# --------------------------------------------------
# Crash-Diagnose (faulthandler)
# --------------------------------------------------
# SIGSEGV-Abstürze (z. B. in libxkbcommon/Qt) laufen an unserem
# eigenen Logger vorbei, weil der Prozess sofort hart beendet
# wird - es gibt keine Python-Exception, die wir abfangen
# könnten. faulthandler schreibt in diesem Fall trotzdem einen
# nativen Stacktrace in eine feste Log-Datei, BEVOR der Prozess
# stirbt. Damit haben wir bei zukünftigen Crash-Reports endlich
# einen echten Anhaltspunkt statt nur Vermutungen.

try:

    _crash_log_dir = (
        Path.home()
        / ".local"
        / "share"
        / "WeintCompanion"
        / "cache"
        / "logs"
        if platform.system() == "Linux"
        else Path(
            os.getenv("LOCALAPPDATA", str(Path.home()))
        )
        / "WeintCompanion"
        / "cache"
        / "logs"
    )

    _crash_log_dir.mkdir(parents=True, exist_ok=True)

    _crash_log_file = open(
        _crash_log_dir / "crash.log",
        "a",
        encoding="utf-8",
    )

    faulthandler.enable(file=_crash_log_file, all_threads=True)

except Exception:

    # Diagnose darf niemals den App-Start verhindern.
    pass


# --------------------------------------------------
# Qt-Plugin-Diagnose (QT_DEBUG_PLUGINS)
# --------------------------------------------------
# Beobachtung: Bei manchen Nutzern (auch auf echtem Wayland,
# XDG_SESSION_TYPE=wayland) wählt Qt trotzdem von sich aus die
# "xcb"-Plattform, OBWOHL wir xcb gar nicht mehr erzwingen. Das
# bedeutet: Qt versucht das native "wayland"-Plugin zu laden,
# scheitert dabei aber leise (z. B. weil eine System-Bibliothek
# wie libwayland-client/libxkbcommon-Version nicht passt) und
# fällt automatisch auf xcb zurück - ganz ohne dass wir das aus
# Python heraus sehen oder beeinflussen.
#
# QT_DEBUG_PLUGINS=1 lässt Qt genau protokollieren, welche
# Plattform-Plugins es findet, prüft und warum ein Plugin
# abgelehnt wird. Diese Ausgabe geht direkt auf stderr (C++-Ebene,
# nicht über unseren Python-Logger), daher leiten wir stderr für
# die Laufzeit der App zusätzlich in eine eigene Log-Datei um.

try:

    os.environ.setdefault("QT_DEBUG_PLUGINS", "1")

    _qt_plugin_log_path = _crash_log_dir / "qt-plugins.log"

    _qt_plugin_log_file = open(
        _qt_plugin_log_path,
        "w",
        encoding="utf-8",
    )

    _original_stderr_fd = os.dup(2)

    os.dup2(_qt_plugin_log_file.fileno(), 2)

except Exception:

    # Diagnose darf niemals den App-Start verhindern.
    pass


# --------------------------------------------------
# Linux Plattform-Wahl
# --------------------------------------------------
# ERKENNTNIS (07/2026): Unsere bisherige Logik hat
# den xcb/XI2-Absturzschutz nur aktiviert, wenn WIR SELBST anhand
# von XDG_SESSION_TYPE erkannt haben, dass eine Wayland-Sitzung
# läuft. Das ist unzuverlässig: Qt kann - unabhängig von unserer
# Erkennung - bei jedem Start selbst auf xcb zurückfallen (z. B.
# wenn WAYLAND_DISPLAY im Prozesskontext nicht sichtbar ist, was
# bei AppImages/bestimmten Startwegen vorkommt), OHNE dass unsere
# Bedingung das mitbekommt. In diesem Fall griff unser SEGV-Schutz
# (QT_XCB_NO_XI2) gar nicht - und genau das hat den
# ursprünglichen libxkbcommon/Qt6XcbQpa-Crash reproduziert, obwohl
# der Fix längst im Code stand.
#
# LÖSUNG: Statt selbst zu raten, ob xcb genutzt wird, geben wir
# Qt eine Fallback-Liste vor ("wayland;xcb") - Qt versucht dann
# selbst zuerst nativ Wayland zu laden und fällt nur bei Bedarf
# automatisch auf xcb zurück. Und der SEGV-Schutz (QT_XCB_NO_XI2)
# wird IMMER gesetzt, unabhängig davon, ob/warum xcb am Ende
# genutzt wird - er ist unter Wayland ein no-op und schützt unter
# xcb in jedem Fall, egal wie Qt dort gelandet ist.

if platform.system() == "Linux":

    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

    # --------------------------------------------------
    # Absturz-Fix: SEGV in libxkbcommon (Qt6XcbQpa)
    # --------------------------------------------------
    # Auf mehreren Distributionen (Fedora, openSUSE, CachyOS)
    # stürzt Qt sporadisch mit SIGSEGV in libxkbcommon ab,
    # aufgerufen aus dem XCB-Plugin (QXcbKeyboard). Das ist ein
    # bekanntes Problem, wenn Qt Tastatur-/Touch-Events über die
    # XInput2-Erweiterung (XI2) verarbeitet: Der XKB-Status wird
    # dabei aus einem anderen Codepfad aktualisiert als über die
    # "Core"-Events, was unter XWayland zu einer Racecondition und
    # damit zu einem Absturz in libxkbcommon führen kann.
    #
    # Deaktiviert man XI2, nutzt Qt stattdessen die klassischen
    # X11-Core-Events für Tastatur/Maus - der fehlerhafte Codepfad
    # wird dadurch komplett umgangen. Betrifft NUR xcb, ist unter
    # nativem Wayland wirkungslos.
    #
    # WEINT_FORCE_XI2=1 erlaubt betroffenen Nutzern, XI2 gezielt
    # wieder zu aktivieren, falls dieser Fix bei ihnen selbst neue
    # Probleme verursacht (Einzelbericht CachyOS/KDE, 07/2026).
    if os.environ.get("WEINT_FORCE_XI2") != "1":

        os.environ.setdefault("QT_XCB_NO_XI2", "1")


from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme.stylesheet import APP_STYLE


def main():

    app = QApplication(sys.argv)

    # Die Plattform-Wahl ist zu diesem Zeitpunkt bereits getroffen -
    # stderr wieder normal verbinden, damit spätere Laufzeitfehler
    # weiterhin im Terminal/Log sichtbar sind und nicht dauerhaft in
    # qt-plugins.log verschwinden.
    try:

        os.dup2(_original_stderr_fd, 2)

        os.close(_original_stderr_fd)

        _qt_plugin_log_file.close()

        print(
            "[WeintCompanion] Qt-Plugin-Debug-Log: "
            f"{_qt_plugin_log_path}"
        )

    except Exception:

        pass

    # Optional: Ausgabe des verwendeten Qt-Backends
    print(f"[WeintCompanion] Qt Platform: {QGuiApplication.platformName()}")

    print(
        "[WeintCompanion] QT_XCB_NO_XI2="
        f"{os.environ.get('QT_XCB_NO_XI2', '<nicht gesetzt>')}"
    )

    #
    # Globales Theme laden
    #
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()