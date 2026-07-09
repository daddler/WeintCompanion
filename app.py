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
# Linux Wayland Fix
# --------------------------------------------------
# Einige Wayland-Systeme (z. B. Fedora) verursachen
# Darstellungsfehler mit Qt (Transparenz/Ghosting).
# In diesem Fall wird automatisch XWayland (xcb) genutzt.
#
# WICHTIG: Dieser Workaround ist ein zweischneidiges Schwert.
# Er behebt zwar das ursprüngliche Ghosting bei transparenten
# Widgets, aber das zusätzliche QT_XCB_NO_XI2=1 (siehe unten) ist
# selbst ein inoffizieller Hack, der auf manchen Distros/Treiber-
# Kombis neue, andere Abstürze verursacht hat (Nutzerbericht,
# CachyOS/KDE, 07/2026).
#
# Deshalb ist xcb NICHT mehr der Standard. Das Ghosting-Problem
# wird stattdessen direkt an der Quelle behoben (siehe
# gui/widgets/navigation_item.py und gui/widgets/hero_banner.py:
# vollständige Repaints statt Teil-Repaints bei transparenten
# Widgets). xcb bleibt nur noch als manueller Notfall-Fallback
# erhalten, falls das Ghosting bei jemandem doch wieder auftritt:
#
#   WEINT_FORCE_XCB_WORKAROUND=1   -> xcb + XI2-Fix aktivieren
#                                       (altes Verhalten)
#   WEINT_FORCE_XI2=1               -> zusammen mit obigem: xcb
#                                       aktiv, aber XI2 NICHT
#                                       deaktivieren

if (
    platform.system() == "Linux"
    and os.environ.get("XDG_SESSION_TYPE") == "wayland"
    and os.environ.get("WEINT_FORCE_XCB_WORKAROUND") == "1"
):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

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
    # wird dadurch komplett umgangen.
    if os.environ.get("WEINT_FORCE_XI2") != "1":

        os.environ.setdefault("QT_XCB_NO_XI2", "1")


from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme.stylesheet import APP_STYLE


def main():

    app = QApplication(sys.argv)

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