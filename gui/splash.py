from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from core.resources import Resources
from core.version import VERSION
from gui.theme.colors import Colors


class SplashScreen(QWidget):
    """
    Ephemerer Startbildschirm (~1.5s, während Python/PySide6 hochfährt).
    Das Artwork darf hier kurz Bühne bekommen, siehe Design-Notiz zu
    Screen 06 · Splash.
    """

    WIDTH = 560
    HEIGHT = 360

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SplashScreen
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._backdrop = QPixmap(Resources.banner())

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

        self.mark = QLabel("W")

        self.mark.setFixedSize(72, 72)

        self.mark.setAlignment(Qt.AlignCenter)

        self.mark.setStyleSheet(f"""
        QLabel{{
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 {Colors.PRIMARY},
                stop:1 {Colors.PRIMARY_2}
            );
            color:white;
            font-size:32px;
            font-weight:800;
            border-radius:18px;
        }}
        """)

        layout.addWidget(self.mark, alignment=Qt.AlignCenter)

        layout.addSpacing(24)

        title = QLabel("WeintCompanion")

        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet(
            f"color:{Colors.WHITE};font-size:26px;font-weight:700;"
        )

        layout.addWidget(title)

        subtitle = QLabel(
            f"MISTS OF PANDARIA CLASSIC · v{VERSION}"
        )

        subtitle.setAlignment(Qt.AlignCenter)

        subtitle.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_SECONDARY};"
            "letter-spacing:0.1em;"
        )

        layout.addWidget(subtitle)

        layout.addSpacing(28)

        self.progress = QProgressBar()

        self.progress.setFixedWidth(280)
        self.progress.setFixedHeight(3)

        self.progress.setTextVisible(False)

        self.progress.setRange(0, 0)

        self.progress.setStyleSheet(f"""
        QProgressBar{{
            background:{Colors.SURFACE_LIGHT};
            border:none;
            border-radius:1px;
        }}
        QProgressBar::chunk{{
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:0,
                stop:0 {Colors.PRIMARY},
                stop:1 {Colors.PRIMARY_2}
            );
            border-radius:1px;
        }}
        """)

        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        layout.addSpacing(10)

        self.status = QLabel("Wird gestartet …")

        self.status.setAlignment(Qt.AlignCenter)

        self.status.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(self.status)

        layout.addStretch()

        #
        # Bildschirmmitte
        #

        screen = self.screen()

        if screen is not None:

            geometry = screen.availableGeometry()

            self.move(
                geometry.center().x() - self.width() // 2,
                geometry.center().y() - self.height() // 2,
            )

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())

        base = QRadialGradient(
            rect.center(),
            rect.width() * 0.6,
        )

        base.setColorAt(0, QColor("#12101a"))
        base.setColorAt(1, QColor(Colors.BACKGROUND))

        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawRoundedRect(rect, 14, 14)

        if not self._backdrop.isNull():

            painter.save()

            painter.setClipRect(rect)

            painter.setOpacity(0.28)

            scaled = self._backdrop.scaled(
                self.width(),
                self.height(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            painter.drawPixmap(0, 0, scaled)

            painter.restore()

        vignette = QRadialGradient(
            rect.center(),
            rect.width() * 0.7,
        )

        vignette.setColorAt(0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.7, QColor(10, 10, 12, 110))
        vignette.setColorAt(1, QColor(10, 10, 12, 235))

        painter.setBrush(vignette)
        painter.drawRoundedRect(rect, 14, 14)

        brand = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        brand.setColorAt(0, QColor(168, 85, 247, 30))
        brand.setColorAt(1, QColor(99, 102, 241, 20))

        painter.setBrush(brand)
        painter.drawRoundedRect(rect, 14, 14)

        painter.end()

    def setStatusText(self, text: str):
        self.status.setText(text)
