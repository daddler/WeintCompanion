"""
Der Wechsel auf die nächste Generation - als Assistent in drei
Bildern.

WARUM EIN EIGENER DIALOG UND KEINE UPDATE-KARTE
-----------------------------------------------

Weil es kein Update ist. Die Update-Karte auf der Übersicht sagt
"es gibt eine neuere Fassung von dem, was du benutzt" - und das ist
hier falsch: es fängt eine **andere Anwendung** an. Stünde es an
derselben Stelle in derselben Sprache, wäre der erste Satz des
Nutzers nach dem Klick "warum heisst das jetzt anders".

Deshalb stehen beide Anwendungen hier immer nebeneinander, mit Namen
und Fassung:

    WeintCompanion 4.9.0   ->   Companion-Forever 5.0.0

und deshalb steht im Text, was passiert, **bevor** es passiert.

DREI BILDER
-----------

1. Das Angebot - was ist das, was passiert, und der Hinweis, dass
   die bisherige Fassung erhalten bleibt.
2. Der Verlauf - fünf Schritte, der laufende hervorgehoben.
3. Der Abschluss - Willkommen, oder der Grund für den Abbruch.

Geschlossen werden kann der Dialog nur im ersten und im dritten
Bild: mitten im Download ein Fenster zuzuklappen, während im
Hintergrund noch ein Thread läuft, ist genau die Art Zustand, die
später niemand mehr erklären kann.

**Ohne freigegebene Migration gibt es diesen Dialog nicht.**
`show_migration_offer_if_needed()` fragt zuerst den Dienst, und der
antwortet bei ausgeschaltetem Schalter mit `None`.
"""

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

from core.migration.state import MigrationState

from gui.controllers.migration_runner import MigrationRunner
from gui.theme.colors import Colors
from gui.theme.metrics import Metrics
from gui.widgets.hero_banner import HeroButton


#
# Die fünf Schritte, die der Nutzer sieht. Dieselbe Reihenfolge wie
# in `core/migration/service.STEP_LABELS` - dort stehen die Namen
# fürs Protokoll, hier die Zeilen im Fenster; zusammengeführt werden
# sie über den Zustand, nicht über den Text.
#

STEPS = (
    (MigrationState.CONFIRMED, "Release wird abgerufen"),
    (MigrationState.DOWNLOADING, "Download"),
    (MigrationState.VERIFYING, "Prüfung"),
    (MigrationState.INSTALLING, "Installation"),
    (MigrationState.INSTALLED, "Start"),
)


def _title(text: str) -> QLabel:

    label = QLabel(text)

    label.setWordWrap(True)

    label.setStyleSheet(
        f"font-size:18px;font-weight:700;color:{Colors.WHITE};"
    )

    return label


def _body(text: str) -> QLabel:

    label = QLabel(text)

    label.setWordWrap(True)

    label.setStyleSheet(
        f"font-size:14px;color:{Colors.TEXT_SECONDARY};"
    )

    return label


class MigrationDialog(QDialog):

    def __init__(self, service, offer, parent=None):

        super().__init__(parent)

        self.service = service
        self.offer = offer

        self.runner = MigrationRunner(service, self)

        self.runner.progress.connect(self._on_progress)
        self.runner.finished.connect(self._on_finished)

        self._postponed = False

        self.setWindowTitle("WeintCompanion")

        self.setModal(True)

        self.setFixedSize(520, 420)

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

        self._content = QVBoxLayout()

        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(16)

        holder = QWidget()

        holder.setLayout(self._content)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )

        scroll.setWidget(holder)

        root.addWidget(scroll, 1)

        self._footer = QHBoxLayout()

        self._footer.setSpacing(12)

        root.addLayout(self._footer)

        self._step_labels = {}

        self._show_offer()

    # --------------------------------------------------
    # Hilfen
    # --------------------------------------------------

    @staticmethod
    def _clear(layout):

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _reset(self):

        self._clear(self._content)
        self._clear(self._footer)

        self._step_labels = {}

    # --------------------------------------------------
    # 1 - Das Angebot
    # --------------------------------------------------

    def _show_offer(self):

        self._reset()

        offer = self.offer

        self._content.addWidget(_title("Neue Generation verfügbar"))

        self._content.addWidget(
            _body(
                f"<b>{offer.target_label}</b><br>"
                f"Bisher installiert: {offer.current_label}"
            )
        )

        self._content.addWidget(
            _body(
                f"{offer.target_product} ist die nächste Generation des "
                "WeintCompanion. Sie wurde für WoW Forever entwickelt und "
                "ist eine eigenständige Anwendung - kein gewöhnliches "
                "Update."
            )
        )

        self._content.addWidget(
            _body(
                "Was passiert:\n"
                f"  ✓ {offer.target_product} herunterladen\n"
                "  ✓ Download auf Echtheit prüfen\n"
                "  ✓ Installation vorbereiten\n"
                "  ✓ Einstellungen übernehmen\n"
                f"  ✓ {offer.target_product} starten"
            )
        )

        self._content.addWidget(
            _body(
                f"Deine bestehende Fassung {offer.current_label} bleibt "
                "erhalten, falls etwas schiefgeht. Es wird nichts "
                "gelöscht und nichts überschrieben."
            )
        )

        if offer.dry_run:

            self._content.addWidget(
                _body(
                    "Probelauf: der Ablauf wird durchgespielt, "
                    "installiert oder gestartet wird nichts."
                )
            )

        self._content.addStretch()

        self._footer.addStretch()

        later = HeroButton("Später", primary=False)

        later.clicked.connect(self._postpone)

        self._footer.addWidget(later)

        switch = HeroButton("Jetzt wechseln", primary=True)

        switch.clicked.connect(self._start)

        self._footer.addWidget(switch)

    # --------------------------------------------------
    # 2 - Der Verlauf
    # --------------------------------------------------

    def _show_progress(self):

        self._reset()

        self._content.addWidget(_title("Migration läuft"))

        self._content.addWidget(
            _body(
                f"{self.offer.current_label} wechselt auf "
                f"{self.offer.target_label}."
            )
        )

        for state, label in STEPS:

            widget = _body(f"○  {label}")

            self._step_labels[state.value] = (widget, label)

            self._content.addWidget(widget)

        self._content.addStretch()

    def _on_progress(self, state: str, text: str):

        #
        # Alles, was vor dem gemeldeten Schritt liegt, ist erledigt -
        # abgeleitet aus der Reihenfolge und nicht aus einer zweiten
        # Buchführung im Dialog.
        #

        order = [item[0].value for item in STEPS]

        if state not in order:
            return

        reached = order.index(state)

        for index, key in enumerate(order):

            widget, label = self._step_labels.get(key, (None, ""))

            if widget is None:
                continue

            if index < reached:
                widget.setText(f"✓  {label}")
            elif index == reached:
                widget.setText(f"→  {label}")
            else:
                widget.setText(f"○  {label}")

    # --------------------------------------------------
    # 3 - Der Abschluss
    # --------------------------------------------------

    def _on_finished(self, success: bool, message: str):

        self._reset()

        if success:

            self._content.addWidget(
                _title(f"Willkommen bei {self.offer.target_label}")
            )

            self._content.addWidget(
                _body(
                    message
                    or f"{self.offer.target_product} wurde gestartet."
                )
            )

        else:

            self._content.addWidget(_title("Der Wechsel wurde abgebrochen"))

            self._content.addWidget(
                _body(
                    message
                    or "Der Wechsel konnte nicht abgeschlossen werden."
                )
            )

            self._content.addWidget(
                _body(
                    f"{self.offer.current_label} ist unverändert "
                    "installiert und kann weiter benutzt werden. Der "
                    "Wechsel lässt sich später erneut starten."
                )
            )

        self._content.addStretch()

        self._footer.addStretch()

        close = HeroButton("Schließen", primary=True)

        close.clicked.connect(self.accept)

        self._footer.addWidget(close)

    # --------------------------------------------------

    def _start(self):

        self._show_progress()

        self.runner.start()

    def _postpone(self):

        self._postponed = True

        self.service.postpone()

        self.reject()

    @property
    def postponed(self) -> bool:
        return self._postponed

    # --------------------------------------------------

    def closeEvent(self, event):
        """
        Während der Wechsel läuft, bleibt das Fenster stehen.

        Kein `ignore()` mit Erklärungstext, sondern schlicht kein
        Weg hinaus: der Thread läuft weiter, und ein geschlossener
        Dialog hätte niemanden mehr, dem er sein Ergebnis melden
        kann.
        """

        if self.runner.busy():

            event.ignore()

            return

        super().closeEvent(event)


def show_migration_offer_if_needed(manager, parent=None) -> None:
    """
    Wird beim Start aufgerufen (siehe `gui/main_window.py`), nach den
    übrigen Start-Popups.

    Drei Bedingungen, alle im Dienst und keine davon hier: die
    Migration muss freigegeben sein, es muss eine passende Fassung
    geben, und sie darf weder abgeschlossen noch weggeklickt sein.
    Trifft eines davon nicht zu, passiert nichts - insbesondere
    steht dann auch kein Fenster im Weg.
    """

    service = getattr(manager, "migration", None)

    if service is None or not service.enabled():
        return

    offer = service.offer()

    if offer is None:
        return

    MigrationDialog(service, offer, parent).exec()
