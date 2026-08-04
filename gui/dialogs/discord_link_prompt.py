from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.hero_banner import HeroButton


class DiscordLinkPromptDialog(QDialog):
    """
    Start-Hinweis, solange kein Discord-Account verknüpft ist.
    Schließbar wie jeder andere Dialog (X, Escape, "Später") - die
    Verknüpfung wird nur empfohlen, nie erzwungen.

    Titel und Fließtext stecken in einer QScrollArea statt direkt im
    Root-Layout (dasselbe Muster wie WhatsNewDialog): eine feste
    Dialoggröße plus wortumbrechendes QLabel allein hat den zweiten
    Absatz abgeschnitten, weil das Layout die Label-Höhe nicht
    zuverlässig an den vollen Text angepasst hat. Mit Scroll-Bereich
    bleibt der Text immer vollständig lesbar, unabhängig von
    Schriftgröße oder Zeilenzahl.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._link_requested = False

        self.setWindowTitle("WeintCompanion")

        self.setModal(True)

        self.setFixedSize(480, 360)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(f"""
        QDialog{{
            background:{Colors.SURFACE};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:{Metrics.RADIUS_LARGE}px;
        }}
        """)

        root = QVBoxLayout(self)

        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        title = QLabel("Discord noch nicht verknüpft")

        title.setWordWrap(True)

        title.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{Colors.WHITE};"
        )

        content_layout.addWidget(title)

        body = QLabel(
            "Der volle Funktionsumfang von WeintCompanion - unter anderem "
            "Gilden-Kalender, Charakter-Roster und die Discord-basierten "
            "Zugriffsrechte - steht erst zur Verfügung, wenn dein "
            "Discord-Account verknüpft ist.\n\n"
            "Die Anmeldedaten werden dabei ausschließlich lokal und "
            "temporär auf deinem eigenen Rechner gespeichert. Dritte "
            "haben keine Möglichkeit, sie einzusehen."
        )

        body.setWordWrap(True)

        body.setStyleSheet(
            f"font-size:14px;color:{Colors.TEXT_SECONDARY};"
        )

        content_layout.addWidget(body)

        content_layout.addStretch()

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )

        scroll.setWidget(content)

        root.addWidget(scroll, 1)

        footer = QHBoxLayout()

        footer.setSpacing(12)

        footer.addStretch()

        self.later_button = HeroButton("Später", primary=False)

        self.later_button.clicked.connect(self.reject)

        footer.addWidget(self.later_button)

        self.link_button = HeroButton("Jetzt verknüpfen", primary=True)

        self.link_button.clicked.connect(self._request_link)

        footer.addWidget(self.link_button)

        root.addLayout(footer)

    # --------------------------------------------------

    @property
    def link_requested(self) -> bool:
        return self._link_requested

    def _request_link(self):

        self._link_requested = True

        self.accept()


def show_discord_link_prompt_if_needed(manager, parent=None) -> None:
    """
    Wird einmal beim Start aufgerufen (siehe gui/main_window.py), nach
    dem "Was ist neu"-Popup. Erscheint bei jedem Start, solange kein
    Discord-Account verknüpft ist - bewusst ohne "nicht mehr
    anzeigen"-Option: anders als beim Changelog geht es hier nicht um
    eine einmalige Information, sondern um einen fehlenden
    Funktionsumfang, der sonst dauerhaft unbemerkt bliebe.
    """

    if manager.discord_account.load():
        return

    dialog = DiscordLinkPromptDialog(parent)

    dialog.exec()

    if (
        dialog.link_requested
        and parent is not None
        and hasattr(parent, "open_settings_section")
    ):

        parent.open_settings_section("discord")
