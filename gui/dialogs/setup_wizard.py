"""
WeintCompanion 2.0
Einrichtung

Vier geführte Schritte für den ersten Start (§6.6): WoW-Ordner, Addon
installieren, Discord verbinden, Akzent und Dichte wählen. Eine
einspaltige Folge mit Schrittanzeige `1 / 4` in `type.mono`; Schritt 4
zeigt die drei Akzentvarianten und beide Dichten als Vorschaukarten.

**Kein automatischer Erststart-Erkennung.** Der Entwurf zählt die
Einrichtung zu den nachrangigen Bildschirmen (§6.6), und das Anhängen
an den Programmstart hätte die bestehende Reihenfolge dort angefasst
(`MainWindow.__init__` → `QTimer.singleShot(0, _show_startup_popups)`
→ Was-ist-neu → Discord-Verknüpfungshinweis). Diese Kette ist bereits
sorgfältig austariert, unter anderem, damit die beiden `exec()`-Aufrufe
nie gleichzeitig laufen; ein dritter modaler Dialog dort hätte das
ohne ausführliche Prüfung riskiert. Der Assistent ist stattdessen -
genau wie die Willkommens-Tour (`show_tour()` in
`gui/pages/settings_sections/general.py`) - jederzeit von Hand über
Einstellungen → Allgemein erreichbar.

Jeder Schritt ruft dieselbe Logik auf, die es an ihrer eigentlichen
Stelle schon gibt (Ordnerprüfung, Addon-Installation, Discord-Login),
statt sie ein zweites Mal zu schreiben.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.wow_folder import resolve_classic_folder

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.appearance_picker import (
    AccentSwatch,
    DensitySwatch,
    accent_labels,
    density_labels,
)
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.status_dot import StatusDot
from gui.widgets.wrapped_label import enable_wrap


STEP_TITLES = (
    "WoW-Ordner",
    "Addon installieren",
    "Discord verbinden",
    "Aussehen wählen",
)

DIALOG_WIDTH = 520


class _DiscordLoginBridge(QObject):

    finished = Signal(object, object)


class _Step(QWidget):
    """
    Gerüst eines Schritts: Rubrik, Titel, Erklärung, Statuszeile,
    ein Hauptknopf.
    """

    def __init__(self, eyebrow: str, title: str, explanation: str, parent=None):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(tokens.SPACE[2])

        root.addWidget(eyebrow_label(eyebrow, theme().accent_light()))

        title_label = QLabel(title)

        title_label.setFont(font("section"))

        restyle(title_label, f"color:{tokens.WHITE};background:transparent;")

        root.addWidget(title_label)

        explanation_label = enable_wrap(QLabel(explanation))

        explanation_label.setFont(font("small"))

        restyle(
            explanation_label,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(explanation_label)

        root.addSpacing(tokens.SPACE[2])

        status_row = QHBoxLayout()

        status_row.setContentsMargins(0, 0, 0, 0)

        status_row.setSpacing(8)

        self.dot = StatusDot("empty")

        status_row.addWidget(self.dot)

        self.status_label = QLabel("")

        self.status_label.setFont(font("small"))

        restyle(
            self.status_label,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        status_row.addWidget(self.status_label, 1)

        root.addLayout(status_row)

        root.addSpacing(tokens.SPACE[1])

        self.action_row = QHBoxLayout()

        self.action_row.setContentsMargins(0, 0, 0, 0)

        root.addLayout(self.action_row)

        root.addStretch(1)

    def set_status(self, state: str, text: str):

        self.dot.setState(state)

        self.status_label.setText(text)

    def hide_status(self):
        """
        Für Schritte ohne "gefunden/fehlt"-Zustand (Schritt 4: Aussehen
        wählen hat keinen solchen Zustand, nur eine laufende Auswahl).
        """

        self.dot.setVisible(False)

        self.status_label.setVisible(False)


#
# Die Vorschaukarten für Akzent und Dichte standen bis 2.0 hier, privat
# in diesem Dialog - und damit an der einen Stelle, an der man sie genau
# einmal sieht. Einstellungen → Erscheinungsbild hatte deshalb gar kein
# Bedienelement für beide Wahlmöglichkeiten. Sie liegen jetzt in
# gui/widgets/appearance_picker.py, mitsamt den Beschriftungen: die
# Namen der Varianten in zwei Listen zu pflegen hiesse, dass eine
# vierte in einem Bereich erscheint und im anderen fehlt.
#


class SetupWizard(QDialog):

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.setWindowTitle("Einrichtung")

        self.setFixedWidth(DIALOG_WIDTH)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(
            f"QDialog{{background:{tokens.SURFACE['base']};}}"
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(28, 24, 28, 24)

        root.setSpacing(tokens.SPACE[3])

        self.step_label = eyebrow_label("1 / 4")

        root.addWidget(self.step_label)

        self.stack = QStackedWidget()

        root.addWidget(self.stack, 1)

        self._steps: list[_Step] = []

        self._build_wow_step()
        self._build_addon_step()
        self._build_discord_step()
        self._build_appearance_step()

        #
        # Fußzeile
        #

        footer = QHBoxLayout()

        footer.setContentsMargins(0, 0, 0, 0)

        footer.setSpacing(tokens.SPACE[1])

        self.back_button = QPushButton("Zurück")

        self.back_button.setObjectName("secondary")

        self.back_button.setCursor(Qt.PointingHandCursor)

        self.back_button.clicked.connect(self._go_back)

        footer.addWidget(self.back_button)

        footer.addStretch(1)

        self.next_button = QPushButton("Weiter")

        self.next_button.setCursor(Qt.PointingHandCursor)

        self.next_button.clicked.connect(self._go_next)

        footer.addWidget(self.next_button)

        root.addLayout(footer)

        self._index = 0

        self._apply_step()

        self._refresh_wow_step()

        self._refresh_addon_step()

        self._refresh_discord_step()

    # --------------------------------------------------

    def _apply_step(self):

        self.stack.setCurrentIndex(self._index)

        self.step_label.setText(f"{self._index + 1} / {len(STEP_TITLES)}")

        self.back_button.setEnabled(self._index > 0)

        self.next_button.setText(
            "Fertig" if self._index == len(STEP_TITLES) - 1 else "Weiter"
        )

    def _go_next(self):

        if self._index == len(STEP_TITLES) - 1:

            self.accept()

            return

        self._index += 1

        self._apply_step()

    def _go_back(self):

        self._index = max(0, self._index - 1)

        self._apply_step()

    # --------------------------------------------------
    # Schritt 1: WoW-Ordner
    # --------------------------------------------------

    def _build_wow_step(self):

        step = _Step(
            "SCHRITT 1",
            "Wo ist deine MoP-Classic-Installation?",
            "Wähle den Ordner, in dem World of Warcraft: Mists of "
            "Pandaria Classic installiert ist.",
        )

        self.wow_button = QPushButton("Ordner wählen")

        self.wow_button.setCursor(Qt.PointingHandCursor)

        self.wow_button.clicked.connect(self._choose_wow_folder)

        step.action_row.addWidget(self.wow_button)

        step.action_row.addStretch(1)

        self.stack.addWidget(step)

        self._steps.append(step)

    def _refresh_wow_step(self):

        step = self._steps[0]

        state = self.manager.state

        if state.wow_found:

            step.set_status("ok", f"Gefunden: {state.wow_path}")

        else:

            step.set_status("empty", "Noch kein Ordner gewählt.")

    def _choose_wow_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self, "MoP Classic auswählen",
        )

        if not folder:
            return

        resolved = resolve_classic_folder(folder)

        if resolved is None:

            self._steps[0].set_status(
                "error", "Das ist kein gültiger MoP-Classic-Ordner.",
            )

            return

        self.manager.config.set_classic_path(resolved)

        self.manager.refresh()

        self.manager.logger.success(f"Classic-Pfad geändert: {resolved}")

        self._refresh_wow_step()

        self._refresh_addon_step()

    # --------------------------------------------------
    # Schritt 2: Addon installieren
    # --------------------------------------------------

    def _build_addon_step(self):

        step = _Step(
            "SCHRITT 2",
            "WeintCodex installieren.",
            "Das Addon bringt WeintTV und die Academy ins Spiel und "
            "verbindet WoW mit dieser App.",
        )

        self.addon_button = QPushButton("Installieren")

        self.addon_button.setCursor(Qt.PointingHandCursor)

        self.addon_button.clicked.connect(self._install_addon)

        step.action_row.addWidget(self.addon_button)

        step.action_row.addStretch(1)

        self.stack.addWidget(step)

        self._steps.append(step)

    def _refresh_addon_step(self):

        step = self._steps[1]

        state = self.manager.state

        if state.addon_found:

            step.set_status("ok", f"Installiert: {state.addon_version}")

        elif not state.wow_found:

            step.set_status("empty", "Erst den WoW-Ordner wählen (Schritt 1).")

        else:

            step.set_status("empty", "Noch nicht installiert.")

        self.addon_button.setEnabled(state.wow_found)

    def _install_addon(self):

        try:

            self.manager.logger.info("Starte Addon-Installation...")

            self.manager.install_or_update()

            self.manager.logger.success("Addon erfolgreich installiert.")

        except Exception as exc:

            self.manager.logger.error(f"Fehler: {exc}")

        self._refresh_addon_step()

    # --------------------------------------------------
    # Schritt 3: Discord verbinden
    # --------------------------------------------------

    def _build_discord_step(self):

        step = _Step(
            "SCHRITT 3",
            "Discord verbinden.",
            "Verknüpft dein Discord-Konto für den Raid-Roster-Export "
            "und den Charakter-Abgleich mit dem Bot.",
        )

        self.discord_button = QPushButton("Mit Discord verbinden")

        self.discord_button.setCursor(Qt.PointingHandCursor)

        self.discord_button.clicked.connect(self._start_discord_login)

        step.action_row.addWidget(self.discord_button)

        step.action_row.addStretch(1)

        self.stack.addWidget(step)

        self._steps.append(step)

        self._discord_bridge = _DiscordLoginBridge(self)

        self._discord_bridge.finished.connect(self._on_discord_login_finished)

    def _refresh_discord_step(self):

        step = self._steps[2]

        account = self.manager.discord_account.load()

        if account:

            step.set_status(
                "ok", f"Verbunden als {account.get('username', '-')}.",
            )

        else:

            step.set_status("empty", "Noch nicht verbunden.")

    def _start_discord_login(self):

        self.discord_button.setEnabled(False)

        self._steps[2].set_status(
            "info", "Browser öffnet sich - Login abschließen...",
        )

        thread = threading.Thread(
            target=self._discord_login_worker,
            daemon=True,
            name="SetupWizardDiscordLoginThread",
        )

        thread.start()

    def _discord_login_worker(self):

        try:

            result = self.manager.discord_auth.login()

        except Exception as exc:

            self._discord_bridge.finished.emit(None, str(exc))

            return

        self._discord_bridge.finished.emit(result, None)

    def _on_discord_login_finished(self, result, error):

        self.discord_button.setEnabled(True)

        if error:

            self.manager.logger.error(f"Discord-Login fehlgeschlagen: {error}")

        else:

            self.manager.discord_account.save(result)

            self.manager.logger.success(
                f"Discord verbunden als {result.get('username')}."
            )

        self._refresh_discord_step()

    # --------------------------------------------------
    # Schritt 4: Akzent und Dichte
    # --------------------------------------------------

    def _build_appearance_step(self):

        step = _Step(
            "SCHRITT 4",
            "Wie soll es aussehen?",
            "Beides lässt sich später in den Einstellungen jederzeit "
            "ändern.",
        )

        step.hide_status()

        swatch_row = QHBoxLayout()

        swatch_row.setContentsMargins(0, 0, 0, 0)

        swatch_row.setSpacing(tokens.SPACE[2])

        self.accent_swatches: dict[str, AccentSwatch] = {}

        for name, label in accent_labels():

            swatch = AccentSwatch(name, label)

            swatch_row.addWidget(swatch)

            self.accent_swatches[name] = swatch

        step.action_row.addLayout(swatch_row)

        self.stack.addWidget(step)

        self._steps.append(step)

        density_row = QHBoxLayout()

        density_row.setContentsMargins(0, 0, 0, 0)

        density_row.setSpacing(tokens.SPACE[2])

        self.density_swatches: dict[str, DensitySwatch] = {}

        for name, label in density_labels():

            swatch = DensitySwatch(name, label)

            density_row.addWidget(swatch)

            self.density_swatches[name] = swatch

        wrapper = QVBoxLayout()

        wrapper.setContentsMargins(0, tokens.SPACE[2], 0, 0)

        wrapper.addLayout(density_row)

        step.layout().insertLayout(
            step.layout().count() - 1, wrapper,
        )

        theme().accent_changed.connect(self._refresh_appearance_step)

        theme().density_changed.connect(self._refresh_appearance_step)

        self._refresh_appearance_step()

    def _refresh_appearance_step(self, *_args):

        for name, swatch in self.accent_swatches.items():
            swatch.set_selected(name == theme().accent_name())

        for name, swatch in self.density_swatches.items():
            swatch.set_selected(name == theme().density_name())
