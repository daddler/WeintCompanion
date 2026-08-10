"""
Addon & Updates.

Zwei Komponenten - das Addon und die Companion selbst -, ihr
Sicherungsverlauf und die letzten Meldungen dazu (§6.4).

**Was hier nicht mehr steht**: die WoW-Client-Pfadwahl und die
Laufzeitangaben (Python-/PySide6-Version). Beide gab es bis 1.7 hier
ein zweites Mal - die Pfadwahl liegt bereits vollständig unter
Einstellungen → WoW-Client (`gui/pages/settings_sections/wow_client.py`,
mit derselben Ordnerprüfung), die Laufzeitangaben stehen bereits unter
Einstellungen → Über. Zwei Stellen für dieselbe Angabe laufen
irgendwann auseinander; diese Seite behält nur, was es sonst nirgends
gibt.

**Die Ladeanzeige zeigt keine Bytes und keinen Prozentwert.** Der
Entwurf sieht das vor (§6.4), aber `core/downloader.py` liefert beim
Herunterladen keinen Fortschritt zurück - nur "läuft" oder "fertig".
Eine erfundene Zahl wäre hier keine Ungenauigkeit, sondern eine
Behauptung, die aus reiner Rechenzeit nicht folgt. Gezeigt wird
stattdessen ehrlich, was bekannt ist: dass gerade etwas läuft.
"""

from __future__ import annotations

import threading
from datetime import datetime

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.paths import Paths

from gui.navigation import PageId
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.icons import tinted_pixmap
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.status_dot import StatusDot
from gui.widgets.wrapped_label import enable_wrap


#
# Zustandsfarbe je Protokollstufe - dieselben vier Stufen, die
# core/logger.py kennt (info/success/warning/error).
#

LOG_DOT_STATE = {
    "success": "ok",
    "warning": "warn",
    "error": "error",
    "info": "info",
}


def _divider() -> QFrame:

    line = QFrame()

    line.setFixedHeight(1)

    line.setStyleSheet(f"background:{tokens.SURFACE['raised']};border:none;")

    return line


class _CompanionUpdateBridge(QObject):
    """
    Meldet das Ergebnis des Companion-Updates thread-sicher an den
    Hauptthread zurück - der eigentliche Download/Install-Aufruf läuft
    in einem Hintergrundthread, damit die GUI währenddessen nicht
    einfriert.
    """

    finished = Signal(bool)


class ComponentCard(Card):
    """
    Eine der beiden Komponentenkarten: Symbol, Name, Zustandschip,
    Versionspaar, Änderungsnotizen, Fußknöpfe.

    Rechts fest 420 px oder links dehnbar - welche Rolle eine Karte
    gerade hat, entscheidet `AddonPage._reorder_cards()` anhand dessen,
    welche Komponente Handlungsbedarf hat.
    """

    def __init__(self, icon: str, name: str, subtitle: str, parent=None):

        super().__init__(parent=parent)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[2])

        self.icon_badge = QLabel()

        self.icon_badge.setFixedSize(40, 40)

        self.icon_badge.setAlignment(Qt.AlignCenter)

        self.icon_badge.setPixmap(
            tinted_pixmap(icon, tokens.TEXT["secondary"], 20)
        )

        restyle(
            self.icon_badge,
            f"""
            QLabel{{
                background:{tokens.SURFACE["raised"]};
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        header.addWidget(self.icon_badge)

        title_col = QVBoxLayout()

        title_col.setContentsMargins(0, 0, 0, 0)

        title_col.setSpacing(2)

        self.name_label = QLabel(name)

        self.name_label.setFont(font("card"))

        restyle(
            self.name_label,
            f"color:{tokens.WHITE};background:transparent;",
        )

        title_col.addWidget(self.name_label)

        self.subtitle_label = QLabel(subtitle)

        self.subtitle_label.setFont(font("mono"))

        restyle(
            self.subtitle_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        title_col.addWidget(self.subtitle_label)

        header.addLayout(title_col, 1)

        self.chip = Chip("AKTUELL", "ok")

        header.addWidget(self.chip)

        self.addLayout(header)

        #
        # Versionspaar
        #

        version_row = QHBoxLayout()

        version_row.setContentsMargins(0, 0, 0, 0)

        version_row.setSpacing(tokens.SPACE[2])

        installed_col = QVBoxLayout()

        installed_col.setSpacing(2)

        installed_col.addWidget(eyebrow_label("INSTALLIERT"))

        self.installed_value = QLabel("-")

        self.installed_value.setFont(font("mono"))

        self.installed_value.setStyleSheet(
            f"font-size:18px;color:{tokens.TEXT['primary']};"
            "background:transparent;"
        )

        installed_col.addWidget(self.installed_value)

        version_row.addLayout(installed_col)

        self.arrow = QLabel("→")

        restyle(
            self.arrow,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        version_row.addWidget(self.arrow)

        available_col = QVBoxLayout()

        available_col.setSpacing(2)

        available_col.addWidget(eyebrow_label("VERFÜGBAR"))

        self.available_value = QLabel("-")

        self.available_value.setFont(font("mono"))

        available_col.addWidget(self.available_value)

        version_row.addLayout(available_col)

        version_row.addStretch(1)

        self.addLayout(version_row)

        self.addWidget(_divider())

        #
        # Änderungsnotizen als Punktliste, Zeilenhöhe locker.
        #

        self.changelog = enable_wrap(QLabel(""))

        self.changelog.setFont(font("small"))

        self.changelog.setStyleSheet(
            f"color:{tokens.TEXT['secondary']};background:transparent;"
            "line-height:170%;"
        )

        self.addWidget(self.changelog)

        self.addStretch(1)

        #
        # Ladehinweis - nur sichtbar während eines Vorgangs, siehe
        # `set_loading()`.
        #

        self.loading_note = QLabel("")

        self.loading_note.setFont(font("small"))

        self.loading_note.setWordWrap(True)

        restyle(
            self.loading_note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.loading_note.setVisible(False)

        self.addWidget(self.loading_note)

        #
        # Fußknöpfe
        #

        self.footer = QHBoxLayout()

        self.footer.setContentsMargins(0, 0, 0, 0)

        self.footer.setSpacing(tokens.SPACE[1])

        self.secondary_button = QPushButton("")

        self.secondary_button.setObjectName("secondary")

        self.secondary_button.setCursor(Qt.PointingHandCursor)

        self.secondary_button.setVisible(False)

        self.footer.addWidget(self.secondary_button)

        self.footer.addStretch(1)

        self.primary_button = QPushButton("")

        self.primary_button.setCursor(Qt.PointingHandCursor)

        self.footer.addWidget(self.primary_button)

        self.addLayout(self.footer)

    # --------------------------------------------------

    def set_status(self, text: str, variant: str):

        self.chip.setText(text)

        self.chip.setVariant(variant)

    def set_versions(
        self,
        installed: str,
        available: str,
        available_meta: str = "",
        highlight: bool = False,
    ):

        self.installed_value.setText(installed)

        self.available_value.setText(available)

        restyle(
            self.installed_value,
            f"font-size:18px;color:{tokens.TEXT['primary']};"
            "background:transparent;",
        )

        color = tokens.STATE_TEXT["warn"] if highlight else tokens.TEXT["faint"]

        restyle(
            self.available_value,
            f"font-size:18px;color:{color};background:transparent;",
        )

        self.available_value.setToolTip(available_meta)

    def set_changelog(self, lines: list[str] | None):

        if lines is None:

            self.changelog.setText(
                "Changelog nicht verfügbar - kein passendes Release "
                "gefunden oder GitHub nicht erreichbar."
            )

            return

        if not lines:

            self.changelog.setText("Keine Änderungen gefunden.")

            return

        self.changelog.setText(
            "\n".join(f"•  {line}" for line in lines)
        )

    def set_loading(self, active: bool, note: str = ""):
        """
        Der Zustand „lädt" (§6.4): Chip `LÄDT`, Akzentkarte, die
        Fußknöpfe gesperrt. Bewusst ohne Fortschrittsbalken mit
        Prozentangabe - siehe Modulkommentar.
        """

        self.setAccent(active)

        if active:

            self.set_status("LÄDT", "info")

        self.primary_button.setEnabled(not active)

        self.secondary_button.setEnabled(not active)

        self.loading_note.setText(note)

        self.loading_note.setVisible(active and bool(note))


class BackupList(QWidget):
    """
    Die vorhandenen Sicherungen als schlichte Liste (§6.4): Zeitstempel
    fest 132 px, Bezeichnung dehnbar, Größe rechts.
    """

    ROW_HEIGHT = 34

    def __init__(self, parent=None):

        super().__init__(parent)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(0, 0, 0, 0)

        self.root.setSpacing(0)

        self.placeholder = QLabel("Noch keine Sicherung vorhanden.")

        self.placeholder.setFont(font("small"))

        restyle(
            self.placeholder,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.root.addWidget(self.placeholder)

        #
        # Nur diese - nie der Platzhalter selbst - werden bei einer
        # erneuten Füllung abgebaut. Der Platzhalter lebt dauerhaft;
        # ihn hier mitzulöschen hätte ihn beim zweiten Aufruf als
        # bereits zerstörtes C++-Objekt hinterlassen.
        #

        self._row_widgets: list[QWidget] = []

    # --------------------------------------------------

    def set_backups(self, files: list):
        """
        `files` ist eine Folge von `pathlib.Path`, neueste zuerst.
        """

        for widget in self._row_widgets:

            self.root.removeWidget(widget)

            widget.deleteLater()

        self._row_widgets = []

        self.placeholder.setVisible(not files)

        if not files:
            return

        for index, path in enumerate(files):

            row = QHBoxLayout()

            row.setContentsMargins(0, 0, 0, 0)

            row.setSpacing(tokens.SPACE[2])

            try:
                stamp = datetime.fromtimestamp(path.stat().st_mtime)
                stamp_text = stamp.strftime("%d.%m. %H:%M")

            except OSError:
                stamp_text = "-"

            timestamp = QLabel(stamp_text)

            timestamp.setFixedWidth(132)

            timestamp.setFont(font("mono"))

            restyle(
                timestamp,
                f"color:{tokens.TEXT['muted']};background:transparent;",
            )

            row.addWidget(timestamp)

            name = QLabel(path.stem)

            name.setFont(font("small"))

            restyle(
                name,
                f"color:{tokens.TEXT['primary']};background:transparent;",
            )

            row.addWidget(name, 1)

            try:
                size_mb = path.stat().st_size / (1024 * 1024)
                size_text = f"{size_mb:.1f} MB"

            except OSError:
                size_text = "-"

            size = QLabel(size_text)

            size.setFont(font("mono"))

            restyle(
                size,
                f"color:{tokens.TEXT['faint']};background:transparent;",
            )

            row.addWidget(size)

            row_widget = QWidget()

            row_widget.setFixedHeight(self.ROW_HEIGHT)

            row_widget.setLayout(row)

            if index < len(files) - 1:

                row_widget.setStyleSheet(
                    f"border-bottom:1px solid {tokens.SURFACE['raised']};"
                )

            self.root.addWidget(row_widget)

            self._row_widgets.append(row_widget)


class AddonPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "SOFTWARE · KOMPONENTEN",
            "Deine Installationen.",
            parent,
        )

        self.check_button = QPushButton("Erneut prüfen")

        self.check_button.setObjectName("secondary")

        self.check_button.setCursor(Qt.PointingHandCursor)

        self.header.addAction(self.check_button)

        #
        # Zwei Komponentenkarten. Welche links (dehnbar) und welche
        # rechts (fest 420 px) steht, entscheidet refresh() über
        # _reorder_cards() - links steht, wer Handlungsbedarf hat.
        #

        self.addon_card = ComponentCard(
            "software", "WeintCodex", "daddler/WeintCodex",
        )

        self.companion_card = ComponentCard(
            "companion", "WeintCompanion", "daddler/WeintCompanion",
        )

        self.companion_card.setFixedWidth(420)

        self.cards_row = QHBoxLayout()

        self.cards_row.setContentsMargins(0, 0, 0, 0)

        self.cards_row.setSpacing(20)

        self.cards_row.addWidget(self.addon_card, 1)

        self.cards_row.addWidget(self.companion_card)

        self._left_is_addon = True

        self.addLayout(self.cards_row)

        #
        # Untere Reihe: Sicherungen links, Meldungen rechts fest 420 px.
        #

        bottom_row = QHBoxLayout()

        bottom_row.setContentsMargins(0, 0, 0, 0)

        bottom_row.setSpacing(20)

        backups_card = Card()

        backups_card.addWidget(eyebrow_label("SICHERUNGEN"))

        self.backup_list = BackupList()

        backups_card.addWidget(self.backup_list)

        backups_card.addStretch(1)

        backups_card.addWidget(_divider())

        self.backup_note = QLabel(
            "Vor jedem Addon-Update wird eine Sicherung angelegt und "
            "bleibt bestehen, bis sie hier oder in den Einstellungen "
            "gelöscht wird."
        )

        self.backup_note.setFont(font("small"))

        enable_wrap(self.backup_note)

        restyle(
            self.backup_note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        backups_card.addWidget(self.backup_note)

        bottom_row.addWidget(backups_card, 1)

        notices_card = Card()

        notices_card.setFixedWidth(420)

        notices_card.addWidget(eyebrow_label("MELDUNGEN"))

        self.notice_rows: list[QWidget] = []

        self.notices_layout = QVBoxLayout()

        self.notices_layout.setContentsMargins(0, 0, 0, 0)

        self.notices_layout.setSpacing(tokens.SPACE[1])

        notices_card.addLayout(self.notices_layout)

        notices_card.addStretch(1)

        self.open_logs_button = QPushButton("Protokoll öffnen →")

        self.open_logs_button.setObjectName("ghost")

        self.open_logs_button.setCursor(Qt.PointingHandCursor)

        self.open_logs_button.clicked.connect(
            lambda: self.pageRequested.emit(PageId.LOGS)
        )

        notices_card.addWidget(self.open_logs_button)

        bottom_row.addWidget(notices_card)

        self.addLayout(bottom_row)

        self.body.addStretch(1)

        #
        # Signale
        #

        self._update_bridge = _CompanionUpdateBridge(self)

        self._update_bridge.finished.connect(
            self._on_companion_update_finished
        )

        self.check_button.clicked.connect(self.check_updates)

        self.addon_card.secondary_button.setText("Neu installieren")

        self.addon_card.secondary_button.setVisible(True)

        self.addon_card.secondary_button.clicked.connect(
            self.install_or_update
        )

        self.addon_card.primary_button.clicked.connect(
            self.install_or_update
        )

        self.companion_card.primary_button.clicked.connect(
            self.update_companion
        )

        self.refresh()

    # --------------------------------------------------

    def _reorder_cards(self, addon_needs_action: bool, companion_needs_action: bool):
        """
        Links steht, wer Handlungsbedarf hat (§6.4). Bei keinem oder
        beiden bleibt das Addon links - es ist die primäre Komponente
        dieser App.
        """

        addon_left = not (companion_needs_action and not addon_needs_action)

        if addon_left == self._left_is_addon:
            return

        self._left_is_addon = addon_left

        for card in (self.addon_card, self.companion_card):
            self.cards_row.removeWidget(card)

        left, right = (
            (self.addon_card, self.companion_card)
            if addon_left
            else (self.companion_card, self.addon_card)
        )

        left.setFixedWidth(16777215)

        left.setMinimumWidth(0)

        right.setFixedWidth(420)

        self.cards_row.addWidget(left, 1)

        self.cards_row.addWidget(right)

    # --------------------------------------------------

    def refresh(self):

        state = self.manager.state

        #
        # WeintCodex
        #

        self.addon_card.set_versions(
            state.addon_version if state.addon_found else "-",
            state.github_version,
            state.github_release_name,
            highlight=state.update_available,
        )

        self.addon_card.set_changelog(
            (state.github_changelog or "").splitlines()
            if state.github_changelog
            else []
        )

        if not state.addon_found:

            self.addon_card.set_status("NICHT INSTALLIERT", "neutral")

            self.addon_card.primary_button.setText("Addon installieren")

            self.addon_card.primary_button.setEnabled(True)

            self.addon_card.secondary_button.setEnabled(False)

        elif state.update_available:

            self.addon_card.set_status("UPDATE VERFÜGBAR", "warn")

            self.addon_card.primary_button.setText(
                f"Auf {state.github_version} aktualisieren"
            )

            self.addon_card.primary_button.setEnabled(True)

            self.addon_card.secondary_button.setEnabled(True)

        else:

            self.addon_card.set_status("AKTUELL", "ok")

            self.addon_card.primary_button.setText("Addon aktuell")

            self.addon_card.primary_button.setEnabled(False)

            self.addon_card.secondary_button.setEnabled(True)

        #
        # WeintCompanion
        #

        self.companion_card.set_versions(
            state.companion_version,
            state.companion_latest_version,
            highlight=state.companion_update_available,
        )

        self.companion_card.set_changelog(state.companion_changelog)

        if state.companion_update_available:

            self.companion_card.set_status("UPDATE VERFÜGBAR", "warn")

            self.companion_card.primary_button.setText(
                f"Auf {state.companion_latest_version} aktualisieren"
            )

            self.companion_card.primary_button.setEnabled(True)

        else:

            self.companion_card.set_status("AKTUELL", "ok")

            self.companion_card.primary_button.setText("Companion aktuell")

            self.companion_card.primary_button.setEnabled(False)

        self._reorder_cards(
            state.update_available,
            state.companion_update_available,
        )

        #
        # Sicherungen
        #

        backup_dir = Paths.backups()

        files = []

        if backup_dir.exists():

            files = sorted(
                (f for f in backup_dir.iterdir() if f.suffix == ".zip"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

        self.backup_list.set_backups(files[:8])

        #
        # Meldungen: die drei letzten Protokolleinträge.
        #

        self._apply_notices()

    def _apply_notices(self):

        for row in self.notice_rows:

            self.notices_layout.removeWidget(row)

            row.deleteLater()

        self.notice_rows = []

        entries = self.manager.logger.entries()[-3:]

        entries.reverse()

        if not entries:

            empty = QLabel("Noch keine Meldungen.")

            empty.setFont(font("small"))

            restyle(
                empty,
                f"color:{tokens.TEXT['muted']};background:transparent;",
            )

            self.notices_layout.addWidget(empty)

            self.notice_rows.append(empty)

            return

        for entry in entries:

            row = QFrame()

            row.setObjectName("noticeRow")

            row.setAttribute(Qt.WA_StyledBackground, True)

            restyle(
                row,
                f"""
                QFrame#noticeRow{{
                    background:{tokens.SURFACE["card"]};
                    border:none;
                    border-radius:{tokens.RADIUS["sm"]}px;
                }}
                """,
            )

            row_layout = QHBoxLayout(row)

            row_layout.setContentsMargins(10, 8, 10, 8)

            row_layout.setSpacing(8)

            row_layout.addWidget(
                StatusDot(LOG_DOT_STATE.get(entry.level, "empty")),
                alignment=Qt.AlignTop,
            )

            text = enable_wrap(QLabel(entry.message))

            text.setFont(font("small"))

            restyle(
                text,
                f"color:{tokens.TEXT['secondary']};background:transparent;",
            )

            row_layout.addWidget(text, 1)

            time_label = QLabel(entry.timestamp.strftime("%H:%M"))

            time_label.setFont(font("mono"))

            restyle(
                time_label,
                f"color:{tokens.TEXT['faint']};background:transparent;",
            )

            row_layout.addWidget(time_label, alignment=Qt.AlignTop)

            self.notices_layout.addWidget(row)

            self.notice_rows.append(row)

    # --------------------------------------------------
    # GitHub erneut prüfen
    # --------------------------------------------------

    def check_updates(self):

        self.manager.logger.info("Prüfe GitHub auf neue Versionen...")

        self.manager.refresh()
        self.manager.refresh_update_status()

        self.refresh()

        self.manager.logger.success("GitHub erfolgreich geprüft.")

    # --------------------------------------------------
    # Installation / Update
    # --------------------------------------------------

    def install_or_update(self):

        state = self.manager.state

        #
        # Die Karte zeigt „lädt", bevor der blockierende Aufruf
        # beginnt, und processEvents() zeichnet sie tatsächlich -
        # sonst käme der Aufruf zuerst und Qt bekäme nie die Chance,
        # den neuen Zustand zu malen, bevor der Hauptthread blockiert.
        # Das ändert nichts an der Ausführung selbst, nur daran, dass
        # sie sichtbar wird.
        #

        self.addon_card.set_loading(
            True,
            "Prüfsumme wird nach dem Download verifiziert.",
        )

        QApplication.processEvents()

        try:

            if state.addon_found:
                self.manager.logger.info("Starte Addon-Aktualisierung...")

            else:
                self.manager.logger.info("Starte Addon-Installation...")

            self.manager.install_or_update()

            if state.addon_found:
                self.manager.logger.success("Addon erfolgreich aktualisiert.")

            else:
                self.manager.logger.success("Addon erfolgreich installiert.")

        except Exception as e:

            self.manager.logger.error(f"Fehler: {e}")

        finally:

            self.addon_card.set_loading(False)

            self.refresh()

    # --------------------------------------------------
    # Companion-Update (Download + Installation im Hintergrund)
    # --------------------------------------------------
    # Der eigentliche Download/Install-Aufruf läuft in einem
    # Hintergrundthread, damit die GUI währenddessen nicht einfriert.
    # Das Ergebnis kommt über ein Qt-Signal thread-sicher zurück.

    def update_companion(self):

        self.companion_card.set_loading(
            True,
            "Wird heruntergeladen und installiert - die App startet "
            "danach neu.",
        )

        self.manager.logger.info("Companion-Update wird heruntergeladen...")

        #
        # stop_auto_sync() fasst ein QTimer-Objekt an, das dem
        # Hauptthread gehört - muss deshalb HIER passieren, nicht im
        # Worker.
        #

        self.manager.stop_auto_sync()

        thread = threading.Thread(
            target=self._companion_update_worker,
            daemon=True,
            name="AddonPageCompanionUpdateThread",
        )

        thread.start()

    def _companion_update_worker(self):

        try:

            success = self.manager.companion_updater.install_update()

        except Exception as exc:

            self.manager.logger.error(f"Companion-Update fehlgeschlagen: {exc}")

            success = False

        self._update_bridge.finished.emit(success)

    def _on_companion_update_finished(self, success: bool):

        if success:

            QTimer.singleShot(300, QApplication.quit)

            return

        #
        # Fehlschlag: Auto-Sync wieder anlaufen lassen und die echte
        # Kartenanzeige wiederherstellen.
        #

        self.companion_card.set_loading(False)

        self.manager.start_auto_sync()

        self.refresh()
