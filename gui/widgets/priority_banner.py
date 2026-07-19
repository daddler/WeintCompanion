from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.theme.colors import Colors
from gui.widgets.hero_banner import HeroButton, RefreshIconButton


PALETTES = {

    "amber": (Colors.WARNING, "rgba(212,162,74,18)"),
    "green": (Colors.SUCCESS, "rgba(124,192,110,18)"),
    "red": (Colors.ERROR, "rgba(229,107,107,18)"),
    "blue": (Colors.DISCORD, "rgba(139,149,245,18)"),
}


def _relative_time(iso_timestamp: str) -> str:

    if not iso_timestamp:
        return ""

    try:

        published = datetime.fromisoformat(
            iso_timestamp.replace("Z", "+00:00")
        )

        delta = datetime.now(timezone.utc) - published

        hours = int(delta.total_seconds() // 3600)

        if hours < 1:
            return "vor wenigen Minuten"

        if hours < 24:
            return f"vor {hours}h"

        return f"vor {hours // 24}d"

    except ValueError:

        return ""


class PriorityBanner(QWidget):
    """
    Gradient-Karte fürs Dashboard - ersetzt den fotografischen
    HeroBanner. Bietet dieselbe öffentliche Schnittstelle
    (Signale/Methoden), die DashboardPage bereits erwartet.
    """

    primaryClicked = Signal()
    secondaryClicked = Signal()
    refreshClicked = Signal()

    def __init__(self):

        super().__init__()

        self.mode = "idle"

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(12)

        #
        # Eyebrow
        #

        eyebrow_row = QHBoxLayout()
        eyebrow_row.setSpacing(8)

        self.dot = QLabel("●")

        eyebrow_row.addWidget(self.dot)

        self.eyebrow = QLabel("ALLES AKTUELL")

        self.eyebrow.setStyleSheet(
            'font-family:"JetBrains Mono";'
            "font-size:11px;"
            "letter-spacing:0.1em;"
        )

        eyebrow_row.addWidget(self.eyebrow)

        eyebrow_row.addStretch()

        root.addLayout(eyebrow_row)

        #
        # Titel + Meta + Buttons
        #

        content_row = QHBoxLayout()
        content_row.setSpacing(24)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        self.title = QLabel("Alles aktuell")

        self.title.setStyleSheet(
            "font-size:22px;"
            "font-weight:600;"
            f"color:{Colors.WHITE};"
            "letter-spacing:-0.01em;"
        )

        text_col.addWidget(self.title)

        self.meta = QLabel("")

        self.meta.setWordWrap(True)

        self.meta.setStyleSheet(
            f"color:{Colors.TEXT_SECONDARY};"
            "font-size:13px;"
        )

        text_col.addWidget(self.meta)

        content_row.addLayout(text_col, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.secondary_button = HeroButton(
            "Addon öffnen",
            primary=False,
        )

        self.install_button = HeroButton(
            "Jetzt aktualisieren",
            primary=True,
        )

        self.refresh_button = RefreshIconButton()

        self.secondary_button.clicked.connect(
            self.secondaryClicked.emit
        )

        self.install_button.clicked.connect(
            self.primaryClicked.emit
        )

        self.refresh_button.clicked.connect(
            self.refreshClicked.emit
        )

        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.secondary_button)
        button_row.addWidget(self.install_button)

        content_row.addLayout(button_row)

        root.addLayout(content_row)

        self._palette = PALETTES["green"]

    # --------------------------------------------------
    # Paint (flache Gradient-Karte, Top-Akzentlinie)
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)

        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        background = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        background.setColorAt(0, QColor(168, 85, 247, 26))
        background.setColorAt(1, QColor(99, 102, 241, 12))

        painter.fillPath(path, background)

        painter.setPen(QColor(Colors.BORDER_ACCENT))
        painter.drawRoundedRect(rect, 14, 14)

        top_line = QLinearGradient(
            rect.left(),
            0,
            rect.right(),
            0,
        )

        top_line.setColorAt(0, QColor(Colors.PRIMARY))
        top_line.setColorAt(1, QColor(Colors.PRIMARY_2))

        painter.fillRect(
            rect.left() + 14,
            rect.top(),
            rect.width() - 28,
            2,
            top_line,
        )

        painter.end()

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def setStatus(self, text: str, color: str = "green"):

        fg, dot_bg = PALETTES.get(color, PALETTES["green"])

        self._palette = (fg, dot_bg)

        self.eyebrow.setText(text)

        self.eyebrow.setStyleSheet(
            'font-family:"JetBrains Mono";'
            "font-size:11px;"
            "letter-spacing:0.1em;"
            f"color:{fg};"
        )

        self.dot.setStyleSheet(f"color:{fg};font-size:10px;")

    def setTitle(self, text: str):
        self.title.setText(text)

    def setMeta(self, text: str):
        self.meta.setText(text)

    def setPrimaryButtonText(self, text: str):
        self.install_button.setText(text)

    def setSecondaryButtonText(self, text: str):
        self.secondary_button.setText(text)

    def setVersion(self, version: str | None = None):
        # Kompatibilität zur bisherigen HeroBanner-API - Version
        # steht im "meta"-Text, kein separates Label nötig.
        pass

    def setUpdateInProgress(self):

        self.setStatus("UPDATE WIRD INSTALLIERT...", "blue")

        self.install_button.setEnabled(False)
        self.install_button.setText("Installation läuft...")

    # --------------------------------------------------
    # State übernehmen
    # --------------------------------------------------

    def updateFromState(self, state):

        if state.companion_update_available:

            self.mode = "companion_update"

            self.setStatus("1 UPDATE VERFÜGBAR", "amber")

            self.setTitle(
                f"WeintCompanion {state.companion_version} → "
                f"{state.companion_latest_version}"
            )

            self.setMeta(
                "Neue Version des Companions verfügbar."
            )

            self.install_button.show()
            self.install_button.setEnabled(True)
            self.install_button.startPulse()

            self.setPrimaryButtonText("Companion aktualisieren")
            self.setSecondaryButtonText("Addon öffnen")

            return

        if state.update_available:

            self.mode = "addon_update"

            self.setStatus("1 UPDATE VERFÜGBAR", "amber")

            self.setTitle(
                f"WeintCodex {state.addon_version} → "
                f"{state.github_version}"
            )

            published = _relative_time(state.github_published)

            meta = state.github_release_name or "Neues Update verfügbar"

            if published:
                meta = f"{meta} · veröffentlicht {published}"

            self.setMeta(meta)

            self.install_button.show()
            self.install_button.setEnabled(True)
            self.install_button.startPulse()

            self.setPrimaryButtonText("WeintCodex aktualisieren")

            return

        if (
            state.github_version == "-"
            and state.companion_latest_version == "-"
        ):

            self.setStatus("GITHUB NICHT ERREICHBAR", "red")

            self.setTitle("GitHub nicht erreichbar")

            self.setMeta(
                "Updates konnten nicht geprüft werden."
            )

            self.setPrimaryButtonText("Erneut prüfen")
            self.setSecondaryButtonText("Addon öffnen")

            return

        if not state.addon_found:

            self.mode = "install"

            self.setStatus("ADDON NICHT INSTALLIERT", "amber")

            self.setTitle("WeintCodex ist noch nicht installiert")

            self.setMeta(
                "Installiere das Addon, um loszulegen."
            )

            self.install_button.show()
            self.install_button.setEnabled(True)
            self.install_button.startPulse()

            self.setPrimaryButtonText("WeintCodex installieren")

            return

        if not state.wow_found:

            self.mode = "choose_folder"

            self.setStatus("WOW-VERZEICHNIS WÄHLEN", "blue")

            self.setTitle("World of Warcraft nicht gefunden")

            self.setMeta(
                "Bitte wähle deinen MoP-Classic-Ordner aus."
            )

            self.install_button.show()
            self.install_button.setEnabled(True)
            self.install_button.startPulse()

            self.setPrimaryButtonText("Ordner auswählen")

            return

        self.mode = "idle"

        self.setStatus("ALLES AKTUELL", "green")

        self.setTitle("Alles aktuell")

        self.setMeta(
            f"WeintCodex {state.addon_version} · "
            f"Companion {state.companion_version}"
        )

        self.install_button.hide()
        self.install_button.stopPulse()

        self.setSecondaryButtonText("Addon öffnen")

    def setError(self, message: str):

        self.setStatus(message, "red")

    def set_busy(self, busy: bool):

        self.install_button.setEnabled(not busy)
        self.secondary_button.setEnabled(not busy)

        if busy:
            self.install_button.setText("Bitte warten...")

    def set_refresh_busy(self, busy: bool):

        self.refresh_button.setEnabled(not busy)

        self.refresh_button.setToolTip(
            "Suche läuft..."
            if busy
            else "Erneut nach Updates suchen"
        )
