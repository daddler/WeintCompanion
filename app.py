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