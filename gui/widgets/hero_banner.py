from __future__ import annotations

from PySide6.QtCore import (
    Qt,
    QSize,
    QRectF,
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Signal,
)

from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)

from core.resources import Resources
from gui.theme.metrics import Metrics
from PySide6.QtGui import QRadialGradient
from core.version import VERSION


# ---------------------------------------------------------
# Farben
# ---------------------------------------------------------

BACKGROUND_TOP = QColor("#1b1d23")
BACKGROUND_BOTTOM = QColor("#111318")

BORDER = QColor("#6e5a2b")

ACCENT = QColor("#d4af37")
ACCENT_DARK = QColor("#b98d18")

TEXT = QColor("#ffffff")
TEXT_SECONDARY = QColor("#a8adb7")

BUTTON = QColor("#d6b04d")
BUTTON_HOVER = QColor("#e5c45f")

CARD_RADIUS = 22


# ---------------------------------------------------------
# Hero Button
# ---------------------------------------------------------


class HeroButton(QPushButton):

    def __init__(self, text: str, primary=True):
        super().__init__(text)

        self.primary = primary

        self.setCursor(Qt.PointingHandCursor)

        self.setMinimumHeight(46)
        self.setMaximumHeight(46)

        self.setMinimumWidth(170)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(30)
        self._shadow.setOffset(0, 10)

        if primary:
            self._shadow.setColor(QColor(212, 175, 55, 90))
        else:
            self._shadow.setColor(QColor(255, 255, 255, 25))

        self.setGraphicsEffect(self._shadow)

        self.setStyleSheet(self._stylesheet(False))

        self._pulse = QPropertyAnimation(
            self._shadow,
            b"blurRadius",
        )

        self._pulse.setStartValue(22)
        self._pulse.setEndValue(42)
        self._pulse.setDuration(900)
        self._pulse.setLoopCount(-1)
        self._pulse.setEasingCurve(
            QEasingCurve.InOutSine
        )

    def enterEvent(self, event):

        self.setStyleSheet(self._stylesheet(True))

        super().enterEvent(event)

    def leaveEvent(self, event):

        self.setStyleSheet(self._stylesheet(False))

        super().leaveEvent(event)

    def _stylesheet(self, hover):

        if self.primary:

            bg = BUTTON_HOVER.name() if hover else BUTTON.name()

            return f"""
            QPushButton {{

                background:{bg};

                color:#171717;

                border:none;

                border-radius:14px;

                padding-left:26px;
                padding-right:26px;

                font-size:14px;
                font-weight:700;
            }}

            QPushButton:pressed{{
                background:{ACCENT_DARK.name()};
            }}
            """

        return f"""
        QPushButton {{

            background:rgba(255,255,255,18);

            color:white;

            border:1px solid rgba(255,255,255,45);

            border-radius:14px;

            padding-left:26px;
            padding-right:26px;

            font-size:14px;
            font-weight:600;
        }}

        QPushButton:hover{{
            background:rgba(255,255,255,35);
        }}

        QPushButton:pressed{{
            background:rgba(255,255,255,20);
        }}
        """
    
    def startPulse(self):

        if self.primary:
            self._pulse.start()


    def stopPulse(self):

        self._pulse.stop()

        self._shadow.setBlurRadius(30)


# ---------------------------------------------------------
# Badge
# ---------------------------------------------------------


class HeroBadge(QLabel):

    def __init__(self):

        super().__init__("WEINTCODEX")

        self.setAlignment(Qt.AlignCenter)

        self.setFixedHeight(28)

        self.setMinimumWidth(104)

        self.setStyleSheet("""
        QLabel{

            background:rgba(212,175,55,35);

            border:1px solid rgba(212,175,55,90);

            color:#E8C96D;

            border-radius:14px;

            padding-left:14px;
            padding-right:14px;

            font-size:11px;
            font-weight:700;

            letter-spacing:1px;
        }
        """)


# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------


class HeroBanner(QWidget):

    primaryClicked = Signal()
    secondaryClicked = Signal()

    def __init__(self):

        super().__init__()

        self.setFixedHeight(Metrics.HERO_HEIGHT)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.mode = "idle"

        self.banner = QPixmap(Resources.banner())

        self.banner_opacity = 1.0

        

        shadow = QGraphicsDropShadowEffect(self)

        shadow.setBlurRadius(42)

        shadow.setOffset(0, 18)

        shadow.setColor(QColor(0, 0, 0, 120))

        self.setGraphicsEffect(shadow)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.content = QWidget()
        self.content.setAttribute(Qt.WA_TranslucentBackground)

        self.root.addWidget(self.content)

        #
        # Gesamtes Hero-Layout
        #

        self.main_layout = QVBoxLayout(self.content)

        self.main_layout.setContentsMargins(
            32,
            24,
            32,
            24,
        )

        self.main_layout.setSpacing(26)

        #
        # Oberer Bereich
        #

        self.top_layout = QHBoxLayout()

        self.top_layout.setSpacing(32)

        self.main_layout.addLayout(self.top_layout)

        #
        # Linke Spalte
        #

        self.left = QVBoxLayout()

        self.left.setSpacing(6)

        self.top_layout.addLayout(
            self.left,
            3,
        )

        #
        # Rechte Seite bleibt frei.
        # Das Banner wird weiterhin im paintEvent gezeichnet.
        #

        self.top_layout.addStretch(2)

        self.badge = HeroBadge()

        self.left.addWidget(
            self.badge,
            alignment=Qt.AlignLeft,
        )

        self.left.addSpacing(6)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        self.title = QLabel("WeintCompanion")

        self.title.setStyleSheet("""
        QLabel{
            color:white;
            font-size:30px;
            font-weight:800;
            background:transparent;
        }
        """)

        self.left.addWidget(self.title)

        #
        # Untertitel
        #

        self.subtitle = QLabel(
            "Der offizielle Companion für WeintCodex.\n"
            "Installiere, aktualisiere und verwalte dein Addon "
            "komfortabel über eine moderne Oberfläche."
        )

        self.subtitle.setWordWrap(True)

        self.subtitle.setMaximumWidth(700)

        self.subtitle.setStyleSheet("""
        QLabel{
            color:#b6bcc8;
            font-size:14px;
            line-height:22px;
            background:transparent;
        }
        """)

        self.left.addWidget(self.subtitle)

        self.left.addSpacing(8)

        #
        # Status Chip
        #

        self.status = QLabel("● Alles aktuell")

        self.status.setStyleSheet("""
        QLabel{

            background:rgba(67,192,122,22);

            color:#7DDB9E;

            border:1px solid rgba(67,192,122,65);

            border-radius:12px;

            padding:7px 14px;

            font-size:12px;

            font-weight:700;
        }
        """)

        self.left.addWidget(
            self.status,
            alignment=Qt.AlignLeft,
        )

        #
        # Version
        #

        self.version = QLabel(f"Version {VERSION}")

        self.version.setStyleSheet("""
        QLabel{
            color:#939AA8;
            font-size:13px;
            background:transparent;
        }
        """)

        self.left.addWidget(self.version)

        #
        # Buttons
        #
        self.left.addSpacing(10)

        button_row = QHBoxLayout()

        button_row.setSpacing(14)

        self.install_button = HeroButton(
            "Jetzt aktualisieren",
            primary=True,
        )

        self.secondary_button = HeroButton(
            "Addon öffnen",
            primary=False,
        )

        self.install_button.clicked.connect(
            self.primaryClicked.emit
        )

        self.secondary_button.clicked.connect(
            self.secondaryClicked.emit
        )

        button_row.addWidget(self.install_button)

        button_row.addWidget(self.secondary_button)

        button_row.addStretch()

        self.left.addLayout(button_row)
        #
        # Unterer Abstand
        #

        self.left.addStretch()

        #
        # --------------------------------------------------
        # Dashboard Cards
        # --------------------------------------------------
        #

        self.cards_container = QWidget()

        self.cards_container.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.cards_layout = QHBoxLayout(
            self.cards_container
        )

        self.cards_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.cards_layout.setSpacing(18)

        self.main_layout.addWidget(
            self.cards_container
        )


    # --------------------------------------------------
    # Größe
    # --------------------------------------------------

    def sizeHint(self):

        return QSize(
            1200,
            Metrics.HERO_HEIGHT,
        )

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        path = QPainterPath()
        path.addRoundedRect(
            QRectF(rect),
            CARD_RADIUS,
            CARD_RADIUS,
        )

        #
        # Hintergrund
        #

        background = QLinearGradient(
            rect.topLeft(),
            rect.bottomLeft(),
        )

        background.setColorAt(0.0, QColor("#23262F"))
        background.setColorAt(0.45, QColor("#1B1E26"))
        background.setColorAt(1.0, QColor("#14171D"))

        painter.fillPath(
            path,
            background,
        )

        #
        # Goldener Glow links
        #

        left_glow = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left() + 260,
            rect.top() + 180,
        )

        left_glow.setColorAt(
            0,
            QColor(212, 175, 55, 80),
        )

        left_glow.setColorAt(
            1,
            QColor(212, 175, 55, 0),
        )

        painter.fillPath(
            path,
            left_glow,
        )

        #
        # Violetter Glow rechts
        #

        right_glow = QLinearGradient(
            rect.right() - 420,
            rect.center().y(),
            rect.right(),
            rect.center().y(),
        )

        right_glow.setColorAt(
            0,
            QColor(120, 60, 255, 0),
        )

        right_glow.setColorAt(
            0.6,
            QColor(120, 60, 255, 45),
        )

        right_glow.setColorAt(
            1,
            QColor(120, 60, 255, 90),
        )

        painter.fillPath(
            path,
            right_glow,
        )

        purple = QLinearGradient(
            rect.right() - 520,
            rect.top(),
            rect.right(),
            rect.bottom(),
        )

        purple.setColorAt(
            0.0,
            QColor(120,60,255,0),
        )

        purple.setColorAt(
            0.55,
            QColor(120,60,255,28),
        )

        purple.setColorAt(
            1.0,
            QColor(120,60,255,80),
        )

        painter.fillPath(
            path,
            purple,
        )

        #
        # -------------------------------
        # Banner zeichnen
        # -------------------------------
        #

        if not self.banner.isNull():

            banner = self.banner.scaled(
                int(rect.width() * 0.68),
                rect.height() + 70,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            x = rect.right() - banner.width() + 120
            y = rect.center().y() - banner.height() // 2

            painter.save()

            #
            # Banner innerhalb des Hero clippen
            #

            painter.setClipPath(path)

            #
            # leicht transparent
            #

            painter.setOpacity(0.90)

            painter.drawPixmap(
                x,
                y,
                banner,
            )

            garrosh_glow = QRadialGradient(
                rect.right() - 120,
                rect.center().y() - 10,
                260,
            )

            garrosh_glow.setColorAt(
                0.0,
                QColor(135, 70, 255, 80),
            )

            garrosh_glow.setColorAt(
                0.45,
                QColor(120, 60, 255, 35),
            )

            garrosh_glow.setColorAt(
                1.0,
                QColor(120, 60, 255, 0),
            )

            painter.fillRect(
                rect,
                garrosh_glow,
            )

            top_overlay = QLinearGradient(
                0,
                rect.top(),
                0,
                rect.bottom(),
            )

            top_overlay.setColorAt(
                0.0,
                QColor(0, 0, 0, 90),
            )

            top_overlay.setColorAt(
                0.25,
                QColor(0, 0, 0, 35),
            )

            top_overlay.setColorAt(
                1.0,
                QColor(0, 0, 0, 0),
            )

            painter.fillRect(
                rect,
                top_overlay,
            )

            #
            # linkes Fade
            #

            fade_width = 700

            fade = QLinearGradient(
                x - 60,
                0,
                x + fade_width,
                0,
            )

            fade.setColorAt(0.00, QColor(27,30,38,255))
            fade.setColorAt(0.15, QColor(27,30,38,250))
            fade.setColorAt(0.35, QColor(27,30,38,215))
            fade.setColorAt(0.60, QColor(27,30,38,120))
            fade.setColorAt(0.82, QColor(27,30,38,35))
            fade.setColorAt(1.00, QColor(27,30,38,0))

            painter.fillRect(
                QRectF(
                    x - 60,
                    rect.top(),
                    fade_width + 60,
                    rect.height(),
                ),
                fade,
            )

            painter.restore()

        vignette = QLinearGradient(
            rect.left(),
            rect.center().y(),
            rect.right(),
            rect.center().y(),
        )

        vignette.setColorAt(
            0.0,
            QColor(0,0,0,10),
        )

        vignette.setColorAt(
            0.65,
            QColor(0,0,0,0),
        )

        vignette.setColorAt(
            1.0,
            QColor(0,0,0,65),
        )

        painter.fillPath(
            path,
            vignette,
        )

        #
        # Goldener Rahmen
        #

        border = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        border.setColorAt(
            0,
            QColor(240, 208, 109, 170),
        )

        border.setColorAt(
            0.5,
            QColor(140, 112, 40, 80),
        )

        border.setColorAt(
            1,
            QColor(240, 208, 109, 150),
        )

        painter.setPen(
            QPen(
                border,
                1.4,
            )
        )

        painter.drawRoundedRect(
            QRectF(rect),
            CARD_RADIUS,
            CARD_RADIUS,
        )

        #
        # Lichtkante oben
        #

        highlight = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.right(),
            rect.top(),
        )

        highlight.setColorAt(
            0,
            QColor(255, 255, 255, 22),
        )

        highlight.setColorAt(
            0.5,
            QColor(255, 255, 255, 6),
        )

        highlight.setColorAt(
            1,
            QColor(255, 255, 255, 0),
        )

        painter.setPen(
            QPen(
                highlight,
                1,
            )
        )

        painter.drawLine(
            rect.left() + 28,
            rect.top() + 1,
            rect.right() - 28,
            rect.top() + 1,
        )

        painter.end()
        
    # --------------------------------------------------
    # Events
    # --------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self.update()

    # --------------------------------------------------
    # Öffentliche API
    # --------------------------------------------------

    def setTitle(self, text: str):
        self.title.setText(text)

    def setSubtitle(self, text: str):
        self.subtitle.setText(text)

    def setVersion(self, version: str | None = None):

        version = version or VERSION

        if version.lower().startswith("version"):
            self.version.setText(version)
        else:
            self.version.setText(f"Version {version}")

    def setStatus(self, text: str, color: str = "green"):

        palettes = {

            "green": (
                "#7DDB9E",
                "rgba(67,192,122,22)",
                "rgba(67,192,122,65)",
            ),

            "orange": (
                "#F4C76B",
                "rgba(212,175,55,20)",
                "rgba(212,175,55,70)",
            ),

            "red": (
                "#F18C8C",
                "rgba(255,87,87,22)",
                "rgba(255,87,87,65)",
            ),

            "blue": (
                "#8DBFFF",
                "rgba(63,140,255,20)",
                "rgba(63,140,255,65)",
            ),
        }

        fg, bg, border = palettes.get(
            color.lower(),
            palettes["green"],
        )

        self.status.setText(text)

        self.status.setStyleSheet(f"""
        QLabel{{
            background:{bg};
            color:{fg};
            border:1px solid {border};
            border-radius:12px;
            padding:7px 14px;
            font-size:12px;
            font-weight:700;
        }}
        """)

    # --------------------------------------------------
    # Bannerbild
    # --------------------------------------------------

    def setBanner(self, path: str):

        pix = QPixmap(path)

        if pix.isNull():
            return

        self.banner = pix

        self.resizeEvent(None)

    # --------------------------------------------------
    # Dashboard Cards
    # --------------------------------------------------

    def addDashboardCards(self, widget):

        self.cards_layout.addWidget(widget)

    # --------------------------------------------------
    # Buttons
    # --------------------------------------------------

    def setButtonsEnabled(
        self,
        install: bool = True,
        secondary: bool = True,
    ):

        self.install_button.setEnabled(install)
        self.secondary_button.setEnabled(secondary)

    def setPrimaryButtonText(self, text: str):
        self.install_button.setText(text)

    def setSecondaryButtonText(self, text: str):
        self.secondary_button.setText(text)

    # --------------------------------------------------
    # Update Status
    # --------------------------------------------------

    def setUpdateAvailable(
        self,
        available: bool,
        version: str | None = None,
    ):

        if available:

            self.setStatus(
                "⬤ Update verfügbar",
                "orange",
            )

            self.install_button.setText(
                "Jetzt aktualisieren"
            )

            if version:
                self.version.setText(
                    f"Neue Version: {version}"
                )

        else:

            self.setStatus(
                "✔ Alles aktuell",
                "green",
            )

    def setUpdateInProgress(self):

        self.setStatus(
            "⬤ Update wird installiert ...",
            "blue",
        )

        self.install_button.setEnabled(False)

        self.install_button.setText(
            "Installation läuft..."
        )

    def setUpdateFinished(self):

        self.install_button.setEnabled(True)

        self.install_button.setText(
            "Jetzt aktualisieren"
        )

        self.setStatus(
            "✔ Alles aktuell",
            "green",
        )

    # --------------------------------------------------
    # State übernehmen
    # --------------------------------------------------

    def updateFromState(self, state):

        #
        # Versionsnummer
        #

        self.setVersion(
            state.companion_version
        )

        #
        # Companion Update
        #

        if state.companion_update_available:

            self.mode = "companion_update"

            self.setStatus(
                "⬤ Companion-Update verfügbar",
                "orange",
            )

            self.install_button.show()

            self.install_button.startPulse()

            self.setPrimaryButtonText(
                "Companion aktualisieren"
            )

            self.setSecondaryButtonText(
                "Addon öffnen"
            )

            return

        #
        # Addon Update
        #

        if state.update_available:

            self.mode = "addon_update"

            self.setStatus(
                "⬤ Addon-Update verfügbar",
                "orange",
            )

            self.install_button.show()

            self.install_button.startPulse()

            self.setPrimaryButtonText(
                "WeintCodex aktualisieren"
            )

            return

        #
        # GitHub nicht erreichbar
        #

        if (
            state.github_version == "-"
            and
            state.companion_latest_version == "-"
        ):

            self.setStatus(
                "⬤ GitHub nicht erreichbar",
                "red",
            )

            self.setPrimaryButtonText(
                "Erneut prüfen"
            )

            self.setSecondaryButtonText(
                "Addon öffnen"
            )

            return

        #
        # Addon fehlt
        #

        if not state.addon_found:

            self.mode = "install"

            self.setStatus(
                "⬤ Addon nicht installiert",
                "orange",
            )

            self.install_button.show()

            self.install_button.startPulse()

            self.setPrimaryButtonText(
                "WeintCodex installieren"
            )

            return

        #
        # WoW fehlt
        #

        if not state.wow_found:

            self.mode = "choose_folder"

            self.setStatus(
                "⬤ WoW-Verzeichnis wählen",
                "blue",
            )

            self.install_button.show()

            self.install_button.startPulse()

            self.setPrimaryButtonText(
                "Ordner auswählen"
            )

            return

        #
        # Alles aktuell
        #

        self.setStatus(
            "✔ Alles aktuell",
            "green",
        )

        self.mode = "idle"

        self.install_button.hide()

        self.install_button.stopPulse()

        self.setSecondaryButtonText(
            "Addon öffnen"
        )

    def setError(self, message: str):

        self.setStatus(
            message,
            "red",
        )

    def set_busy(self, busy: bool):

        self.install_button.setEnabled(
            not busy
        )

        self.secondary_button.setEnabled(
            not busy
        )

        if busy:

            self.install_button.setText(
                "Bitte warten..."
            )
