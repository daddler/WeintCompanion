import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow

#
# Neues Theme
#
from gui.theme.stylesheet import APP_STYLE


def main():

    app = QApplication(sys.argv)

    #
    # Globales Theme laden
    #

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()