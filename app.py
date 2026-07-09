import os
import platform
import sys

# --------------------------------------------------
# Linux Wayland Fix
# --------------------------------------------------
# Einige Wayland-Systeme (z. B. Fedora) verursachen
# Darstellungsfehler mit Qt (Transparenz/Ghosting).
# In diesem Fall wird automatisch XWayland (xcb) genutzt.


if (
    platform.system() == "Linux"
    and os.environ.get("XDG_SESSION_TYPE") == "wayland"
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
    os.environ.setdefault("QT_XCB_NO_XI2", "1")


from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme.stylesheet import APP_STYLE


def main():

    app = QApplication(sys.argv)

    # Optional: Ausgabe des verwendeten Qt-Backends
    print(f"[WeintCompanion] Qt Platform: {QGuiApplication.platformName()}")

    #
    # Globales Theme laden
    #
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()