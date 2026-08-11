from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.changelog_reader import format_changelog_body, read_changelog_sections
from core.resources import Resources
from core.version import VERSION, versions_equal

from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.hero_banner import HeroButton

#
# Statischer Inhalt der Erstinstallations-/1.0-Tour. Wird nur
# gezeigt, solange config["onboarding_seen_version"] noch leer ist -
# also beim allerersten Start dieser Funktion, egal ob Neuinstallation
# oder Update von einer Vor-1.0-Version.
#

TOUR_PAGES = [

    (
        Resources.companion,
        "Willkommen bei WeintCompanion 1.0!",
        "WeintCompanion verbindet drei Teile zu einem Ökosystem: das "
        "WoW-Addon WeintCodex, diese Desktop-App und den WeintCodex-Bot "
        "auf Discord. Ein kurzer Rundgang, bevor es losgeht.",
    ),

    (
        Resources.dashboard,
        "Dashboard",
        "Alles auf einen Blick: erkannte WoW-Installation, installierte "
        "Addon-Version und verfügbare Updates - ein Klick genügt, um zu "
        "installieren oder zu aktualisieren.",
    ),

    (
        Resources.software,
        "Addon-Verwaltung",
        "WeintCodex installieren oder aktualisieren und den Addon-Ordner "
        "direkt öffnen. Vor jedem Update wird automatisch ein Backup der "
        "bisherigen Version angelegt.",
    ),

    (
        Resources.discord,
        "Synchronisation & Discord",
        "Verknüpfe dein Discord-Konto in den Einstellungen. Danach laufen "
        "Gilden-Kalender, Charakter-Roster und optional die "
        "Loot-Verteilung automatisch zwischen Addon und Bot.",
    ),

    (
        Resources.settings,
        "Einstellungen",
        "WoW-Pfad, Backups, Sync-Verhalten - alles einstellbar. Diesen "
        "Rundgang findest du übrigens jederzeit unter Einstellungen → "
        "Allgemein erneut.",
    ),

]


class _DialogPage(QWidget):
    """Eine einzelne Seite: Icon + Titel + Fließtext, zentriert."""

    def __init__(self, icon_path: str, title: str, body: str):
        super().__init__()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        layout.addStretch()

        if icon_path:

            icon_label = QLabel()

            icon_label.setPixmap(
                QIcon(icon_path).pixmap(40, 40)
            )

            icon_label.setAlignment(Qt.AlignHCenter)

            layout.addWidget(icon_label)

        title_label = QLabel(title)

        title_label.setAlignment(Qt.AlignHCenter)

        title_label.setWordWrap(True)

        title_label.setStyleSheet(
            f"font-size:20px;font-weight:700;color:{Colors.WHITE};"
        )

        layout.addWidget(title_label)

        body_label = QLabel(body)

        body_label.setAlignment(Qt.AlignHCenter)

        body_label.setWordWrap(True)

        body_label.setStyleSheet(
            f"font-size:14px;color:{Colors.TEXT_SECONDARY};"
        )

        layout.addWidget(body_label)

        layout.addStretch()


class WhatsNewDialog(QDialog):
    """
    "Was ist neu"-/Onboarding-Dialog. Läuft mit denselben Bausteinen
    in zwei Modi:

    - Tour-Modus (mehrere Seiten, TOUR_PAGES): erstmaliges Erscheinen
      nach 1.0, mit Zurück/Weiter-Navigation und Fortschritts-Punkten.
    - Changelog-Modus (eine oder mehrere Seiten aus
      core/changelog_reader.py): nach künftigen Updates, zeigt genau
      das, was sich seit der zuletzt gesehenen Version geändert hat.

    Mit nur einer Seite blendet sich die Zurück/Weiter-Navigation
    automatisch auf einen einzelnen Schließen-Knopf herunter.
    """

    def __init__(
        self,
        pages: list[tuple[str, str, str]],
        finish_label: str = "Fertig",
        parent=None,
    ):
        super().__init__(parent)

        self._dont_show_again = False

        self.setWindowTitle("WeintCompanion")

        self.setModal(True)

        self.setFixedSize(560, 480)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(f"""
        QDialog{{
            background:{Colors.SURFACE};
            border:1px solid {Colors.BORDER_LIGHT};
            border-radius:{Metrics.RADIUS_LARGE}px;
        }}
        """)

        root = QVBoxLayout(self)

        root.setContentsMargins(32, 32, 32, 24)
        root.setSpacing(20)

        self.stack = QStackedWidget()

        for icon_path, title, body in pages:
            self.stack.addWidget(_DialogPage(icon_path, title, body))

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )

        scroll.setWidget(self.stack)

        root.addWidget(scroll, 1)

        #
        # Fortschritts-Punkte - nur bei mehreren Seiten sichtbar
        # (Changelog-Modus ist meist nur eine Seite).
        #

        self._dots: list[QLabel] = []

        if len(pages) > 1:

            dots_row = QHBoxLayout()

            dots_row.setAlignment(Qt.AlignHCenter)
            dots_row.setSpacing(6)

            for _ in pages:

                dot = QLabel()

                dot.setFixedSize(6, 6)

                self._dots.append(dot)

                dots_row.addWidget(dot)

            root.addLayout(dots_row)

        footer = QHBoxLayout()

        footer.setSpacing(12)

        self.checkbox = QCheckBox("Nicht mehr automatisch anzeigen")

        self.checkbox.toggled.connect(self._set_dont_show_again)

        footer.addWidget(self.checkbox)

        footer.addStretch()

        self._finish_label = finish_label

        self.back_button = HeroButton("Zurück", primary=False)

        self.back_button.clicked.connect(self._go_back)

        self.next_button = HeroButton(finish_label, primary=True)

        self.next_button.clicked.connect(self._go_next)

        footer.addWidget(self.back_button)
        footer.addWidget(self.next_button)

        root.addLayout(footer)

        self.stack.currentChanged.connect(self._update_nav)

        self._update_nav()

    # --------------------------------------------------

    def showEvent(self, event):
        """
        Nach vorn holen.

        Ein modaler Dialog, den man nicht sieht, ist kein Dialog
        mehr, sondern ein hängendes Programm: `exec()` wartet in
        einer eigenen Ereignisschleife, und der Nutzer sieht nur ein
        Fenster, das nicht weitergeht. Genau so lief der 2.0.3-Start
        unter Windows. Die Ursache ist inzwischen beseitigt (siehe
        `MainWindow.showEvent`), aber dieser Dialog erscheint bei
        jedem Update genau einmal - und wenn er dann einmal hinter
        etwas liegt, ist die App für den Nutzer kaputt. Zwei Zeilen
        Versicherung sind das wert.
        """

        super().showEvent(event)

        self.raise_()

        self.activateWindow()

    @property
    def dont_show_again(self) -> bool:
        return self._dont_show_again

    def _set_dont_show_again(self, checked: bool):
        self._dont_show_again = checked

    # --------------------------------------------------

    def _update_nav(self):

        index = self.stack.currentIndex()
        last = self.stack.count() - 1

        self.back_button.setVisible(index > 0)

        self.next_button.setText(
            self._finish_label if index == last else "Weiter"
        )

        for i, dot in enumerate(self._dots):

            color = (
                Colors.PRIMARY
                if i == index
                else Colors.BORDER_LIGHT
            )

            dot.setStyleSheet(
                f"background:{color};border-radius:3px;"
            )

    def _go_back(self):

        self.stack.setCurrentIndex(
            self.stack.currentIndex() - 1
        )

    def _go_next(self):

        index = self.stack.currentIndex()

        if index >= self.stack.count() - 1:

            self.accept()
            return

        self.stack.setCurrentIndex(index + 1)


# --------------------------------------------------
# Orchestrierung
# --------------------------------------------------


def _build_tour_pages() -> list[tuple[str, str, str]]:

    return [
        (icon_fn(), title, body)
        for icon_fn, title, body in TOUR_PAGES
    ]


def _build_changelog_pages(since_version: str) -> list[tuple[str, str, str]]:

    sections = read_changelog_sections(VERSION, since_version=since_version)

    if not sections:

        return [(
            Resources.changelog(),
            f"Was ist neu in {VERSION}",
            "Diese Version enthält allgemeine Verbesserungen.",
        )]

    return [
        (
            Resources.changelog(),
            f"Was ist neu in {version}",
            format_changelog_body(body),
        )
        for version, body in sections
    ]


def show_tour(manager, parent=None) -> None:
    """
    Zeigt die 1.0-Feature-Tour unabhängig vom gespeicherten Zustand -
    für den "Tour erneut anzeigen"-Knopf in den Einstellungen.
    """

    dialog = WhatsNewDialog(
        _build_tour_pages(),
        finish_label="Los geht's",
        parent=parent,
    )

    dialog.exec()

    if dialog.dont_show_again:

        manager.config.data["whats_new_enabled"] = False
        manager.config.save()


def show_whats_new_if_needed(manager, parent=None) -> None:
    """
    Wird einmal beim Start aufgerufen (siehe gui/main_window.py).
    Zeigt je nach gespeichertem Zustand entweder die 1.0-Tour (noch
    nie gesehen) oder die Changelog-Ansicht seit der zuletzt
    gesehenen Version - oder gar nichts, wenn die aktuelle Version
    bereits bestätigt wurde oder der Nutzer das Popup abgeschaltet hat.
    """

    config = manager.config

    if not config.data.get("whats_new_enabled", True):
        return

    seen_version = config.data.get("onboarding_seen_version", "")

    if seen_version and versions_equal(seen_version, VERSION):
        return

    if seen_version:

        pages = _build_changelog_pages(seen_version)
        finish_label = "Schließen"

    else:

        pages = _build_tour_pages()
        finish_label = "Los geht's"

    dialog = WhatsNewDialog(
        pages,
        finish_label=finish_label,
        parent=parent,
    )

    dialog.exec()

    config.data["onboarding_seen_version"] = VERSION

    if dialog.dont_show_again:
        config.data["whats_new_enabled"] = False

    config.save()
