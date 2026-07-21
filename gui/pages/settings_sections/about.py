import platform
import sys
import webbrowser

import PySide6
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.resources import Resources
from core.runtime import Runtime
from core.version import VERSION
from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton

REPO_URL = "https://github.com/daddler/WeintCodex"

# Feedback-Channel auf dem WeintCodex-Discord - Deep-Link statt der
# reinen Invite-URL, damit Mitglieder direkt im richtigen Channel
# landen statt auf dem Server-Standardkanal.
DISCORD_FEEDBACK_URL = (
    "https://discord.com/channels/"
    "1311060525555257364/1519466082362982410"
)


class _ArtworkHeader(QWidget):
    """
    Artwork-Streifen oben im "Über"-Tab (~200px, Fade zum
    App-Hintergrund) - der einzige Ort, an dem das Artwork
    als Header auftritt, siehe Design-Notiz zu Screen 07.
    """

    HEIGHT = 180

    def __init__(self):

        super().__init__()

        self.setFixedHeight(self.HEIGHT)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self._pixmap = QPixmap(Resources.banner())

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        painter.fillRect(rect, QColor(Colors.BACKGROUND))

        if not self._pixmap.isNull():

            scaled = self._pixmap.scaled(
                self.width(),
                self.height(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            painter.save()

            painter.setOpacity(0.6)

            painter.drawPixmap(
                (self.width() - scaled.width()) // 2,
                (self.height() - scaled.height()) // 2,
                scaled,
            )

            painter.restore()

        fade = QLinearGradient(0, rect.top(), 0, rect.bottom())

        fade.setColorAt(0.35, QColor(0, 0, 0, 0))
        fade.setColorAt(1.0, QColor(*_hex_to_rgb(Colors.SURFACE), 255))

        painter.fillRect(rect, fade)

        painter.end()


def _open_external(url: str):
    """
    Öffnet eine URL im System-Browser. Siehe Runtime.clean_environ():
    ohne das vererbt der AppImage/PyInstaller-Bundle sein eigenes
    LD_LIBRARY_PATH an den intern gestarteten Browser-Subprozess, der
    dann lautlos abstürzt - der Browser öffnet nie, ohne Fehler.
    """

    with Runtime.clean_environ():
        webbrowser.open(url)


def _hex_to_rgb(value: str):

    value = value.lstrip("#")

    return tuple(
        int(value[i:i + 2], 16) for i in (0, 2, 4)
    )


def _info_row(label_text: str, value_text: str):

    row = QHBoxLayout()

    label = QLabel(label_text)

    label.setStyleSheet(f"font-size:13px;color:{Colors.TEXT_SECONDARY};")

    row.addWidget(label)

    row.addStretch()

    value = QLabel(value_text)

    value.setStyleSheet(
        'font-family:"JetBrains Mono";'
        f"font-size:13px;color:{Colors.TEXT};"
    )

    row.addWidget(value)

    return row


class AboutSection(QWidget):

    def __init__(self, manager):

        super().__init__()

        self.manager = manager

        #
        # Siehe Kommentar in _common.SectionContent: QStackedWidget
        # poliert "background:transparent" bei nie zuvor sichtbaren
        # Kindern nicht zuverlässig neu - expliziter Hintergrund +
        # WA_StyledBackground umgeht das zuverlässig.
        #

        self.setObjectName("aboutSection")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(
            f"QWidget#aboutSection{{background:{Colors.SURFACE};}}"
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(0)

        root.addWidget(_ArtworkHeader())

        body = QVBoxLayout()

        body.setContentsMargins(40, 8, 40, 32)

        body.setSpacing(20)

        root.addLayout(body)

        #
        # Kopf
        #

        head = QHBoxLayout()

        head.setSpacing(16)

        mark = QLabel("W")

        mark.setFixedSize(56, 56)

        mark.setAlignment(Qt.AlignCenter)

        mark.setStyleSheet(f"""
        QLabel{{
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,
                stop:0 {Colors.PRIMARY},
                stop:1 {Colors.PRIMARY_2}
            );
            color:white;
            font-size:24px;
            font-weight:800;
            border-radius:14px;
        }}
        """)

        head.addWidget(mark)

        text_col = QVBoxLayout()

        text_col.setSpacing(2)

        name = QLabel("WeintCompanion")

        name.setStyleSheet(
            f"font-size:20px;font-weight:700;color:{Colors.WHITE};"
        )

        text_col.addWidget(name)

        version = QLabel(f"v{VERSION} · MoP Classic")

        version.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:12px;color:{Colors.TEXT_MUTED};"
        )

        text_col.addWidget(version)

        head.addLayout(text_col)

        head.addStretch()

        body.addLayout(head)

        description = QLabel(
            "Der offizielle Companion für WeintCodex. Aktualisierung des "
            "Addons und Live-Sync zwischen Spiel und Discord - gebaut mit "
            "Python und PySide6."
        )

        description.setWordWrap(True)

        description.setStyleSheet(
            f"font-size:13px;color:{Colors.TEXT_SECONDARY};line-height:1.6;"
        )

        body.addWidget(description)

        #
        # Info-Zeilen
        #

        python_version = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )

        info_col = QVBoxLayout()

        info_col.setSpacing(10)

        info_col.addLayout(
            _info_row(
                "Runtime",
                f"Python {python_version} · PySide6 {PySide6.__version__}",
            )
        )

        info_col.addLayout(
            _info_row(
                "Plattform",
                f"{platform.system()} · {platform.machine()}",
            )
        )

        info_col.addLayout(
            _info_row("Entwickler", "daddler2419")
        )

        info_col.addLayout(
            _info_row("Lizenz", "MIT")
        )

        body.addLayout(info_col)

        #
        # Buttons
        #

        button_row = QHBoxLayout()

        button_row.setSpacing(8)

        github_button = HeroButton("GitHub öffnen", primary=False)

        github_button.clicked.connect(
            lambda: _open_external(REPO_URL)
        )

        button_row.addWidget(github_button)

        changelog_button = HeroButton("Changelog", primary=False)

        changelog_button.clicked.connect(
            lambda: _open_external(f"{REPO_URL}/releases")
        )

        button_row.addWidget(changelog_button)

        support_button = HeroButton("Support", primary=False)

        support_button.clicked.connect(
            lambda: _open_external(DISCORD_FEEDBACK_URL)
        )

        button_row.addWidget(support_button)

        button_row.addStretch()

        body.addLayout(button_row)

        body.addStretch()

    def refresh(self):
        pass
