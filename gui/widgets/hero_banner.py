from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
)

from core.resources import Resources
from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme


# ---------------------------------------------------------
# Hero Button
# ---------------------------------------------------------
# Flache Gradient-/Outline-Pille, siehe Buttons im Design
# ("Jetzt aktualisieren" / "Changelog" / "Addon-Ordner öffnen" ...).


class HeroButton(QPushButton):

    def __init__(self, text: str, primary=True):
        super().__init__(text)

        self.primary = primary

        self.setCursor(Qt.PointingHandCursor)

        self.setMinimumHeight(40)
        self.setMaximumHeight(40)

        self.setMinimumWidth(0)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(0, 0, 0, 0))

        self.setGraphicsEffect(self._shadow)

        self._apply_stylesheet()

        #
        # Der Hauptknopf trägt die Akzentfarbe, und zwar in einer
        # Stylesheet statt in einem paintEvent - er muss deshalb aktiv
        # benachrichtigt werden. Ohne diese Verbindung blieb jeder
        # "Speichern"-, "Trennen"- oder "Wiedergabe"-Knopf in der
        # ganzen Anwendung bernsteinfarben, auch wenn der Nutzer in
        # Einstellungen -> Erscheinungsbild Jade oder Arkan gewählt
        # hatte. Im Konstruktor verbinden, nicht im Handler (sonst
        # verdoppelt sich die Verbindung bei jedem Wechsel).
        #

        theme().accent_changed.connect(self._on_accent)

        self._pulse = QPropertyAnimation(
            self._shadow,
            b"blurRadius",
        )

        self._pulse.setStartValue(8)
        self._pulse.setEndValue(26)
        self._pulse.setDuration(900)
        self._pulse.setLoopCount(-1)
        self._pulse.setEasingCurve(
            QEasingCurve.InOutSine
        )

    # --------------------------------------------------

    def _on_accent(self, _name: str = ""):

        self._apply_stylesheet()

    def _apply_stylesheet(self):

        #
        # restyle() vergleicht zuerst: setStyleSheet() ist kein Setter,
        # sondern verwirft die zwischengespeicherte Stilrechnung des
        # Widgets und erzwingt ein Neuzeichnen - auch bei
        # unveränderter Zeichenkette (siehe CLAUDE.md).
        #

        restyle(self, self._stylesheet())

    def _stylesheet(self):

        if self.primary:

            #
            # Aus theme() und nicht aus Colors.*: das Übergangsmodul
            # gui/theme/colors.py hält seine Werte statisch und folgt
            # damit keinem Akzentwechsel zur Laufzeit.
            #

            base = theme().accent_base()

            light = theme().accent_light()

            #
            # "onBase" statt hart "white": Jade ist heller als
            # Bernstein und verlangt eine dunkle Schrift, sonst steht
            # weißer Text auf einer hellen Fläche.
            #

            on_base = theme().accent_on_base()

            return f"""
            QPushButton {{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 {base},
                    stop:1 {light}
                );
                color:{on_base};
                border:none;
                border-radius:8px;
                padding-left:20px;
                padding-right:20px;
                font-size:13px;
                font-weight:600;
            }}
            QPushButton:hover {{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 {theme().accent_hover()[0]},
                    stop:1 {theme().accent_hover()[1]}
                );
            }}
            QPushButton:pressed {{
                background:{theme().accent_pressed()};
            }}
            QPushButton:disabled {{
                background:{Colors.SURFACE_LIGHT};
                color:{Colors.TEXT_MUTED};
            }}
            """

        return f"""
        QPushButton {{
            background:{Colors.SURFACE_LIGHT};
            color:{Colors.TEXT};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:8px;
            padding-left:18px;
            padding-right:18px;
            font-size:13px;
            font-weight:500;
        }}
        QPushButton:hover {{
            background:{Colors.BORDER_LIGHT};
        }}
        QPushButton:disabled {{
            color:{Colors.TEXT_MUTED};
        }}
        """

    def startPulse(self):

        if self.primary:

            self._shadow.setColor(
                QColor(168, 85, 247, 140)
            )

            self._pulse.start()

    def stopPulse(self):

        self._pulse.stop()

        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 0, 0, 0))


# ---------------------------------------------------------
# Badge
# ---------------------------------------------------------


class HeroBadge(QLabel):

    def __init__(self):

        super().__init__("WEINTCODEX")

        self.setAlignment(Qt.AlignCenter)

        self.setFixedHeight(24)

        self.setMinimumWidth(96)

        self.setStyleSheet(f"""
        QLabel{{
            background:rgba(212,162,74,18);
            border:1px solid rgba(212,162,74,60);
            color:{Colors.GOLD_LIGHT};
            border-radius:12px;
            padding-left:12px;
            padding-right:12px;
            font-size:10px;
            font-weight:700;
            letter-spacing:1px;
        }}
        """)


# ---------------------------------------------------------
# Refresh-Button
# ---------------------------------------------------------
# Löst eine erneute Prüfung gegen GitHub aus (Addon + Companion),
# ohne dass die App neu gestartet werden muss.


class RefreshIconButton(QPushButton):

    def __init__(self):

        super().__init__()

        self.setIcon(
            QIcon(Resources.sync())
        )

        self.setIconSize(QSize(14, 14))

        self.setFixedSize(40, 40)

        self.setCursor(Qt.PointingHandCursor)

        self.setToolTip(
            "Erneut nach Updates suchen"
        )

        self.setStyleSheet(f"""
        QPushButton{{
            background:{Colors.SURFACE_LIGHT};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:8px;
        }}
        QPushButton:hover{{
            background:{Colors.BORDER_LIGHT};
        }}
        QPushButton:disabled{{
            background:{Colors.SURFACE};
        }}
        """)
