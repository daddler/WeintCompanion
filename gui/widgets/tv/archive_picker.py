"""
Die Quellenzeile: was wird gerade gezeigt, und wie kommt man an etwas
anderes.

Geteilt von WeintTV und der Academy. Das Widget kennt keine eigene
Auswertungslogik - es liest ausschliesslich
`RaidDataService.archive_state()` und ruft dessen Methoden auf.
Dieselbe Regel wie beim RaidSnapshot: eine Seite rechnet nichts, sie
zeigt nur an. Weil beide Seiten denselben Service ansprechen, sehen
sie beim Blick ins Archiv immer denselben Pull.

**Bis 2.8.0 standen hier zwei Ausklapplisten**, und sie waren der
Grund für "es ist ziemlich kompliziert, archivierte Logs zu finden":
zwanzig gleich aussehende Berichte in der einen, sechzig ungeordnete
Pulls in der anderen. Beides ist in den Archivbrowser gewandert
(gui/dialogs/archive_dialog.py), wo genug Platz für Gruppen, Suche und
Filter ist. Übrig bleibt hier die Frage, die eine Zeile beantworten
kann: **was ist gerade geladen** - und ein Knopf, der zum Browser
führt.

Diese Zeile sagt bewusst, was **geladen** ist, und nicht, was
ausgewählt wurde. Die alten Ausklapplisten zeigten die Auswahl; nach
einem fehlgeschlagenen Abruf stand dort weiter der Pull, den man gar
nicht vor sich hatte. Formuliert wird der Satz in
`core/archive_index.py`, damit beide Seiten denselben Sachverhalt
nicht verschieden benennen.

Die Wiedergabe ist ein dritter Modus des Service, aber bewusst kein
dritter Knopf am Umschalter: man spielt immer einen Pull ab, den man
vorher ausgewählt hat. Der Umschalter zeigt während der Wiedergabe
deshalb weiter die Ansicht, aus der sie gestartet wurde.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from core import archive_index as index
from core.raid_data_service import (
    ArchiveState,
    MODE_ARCHIVE,
    MODE_LIVE,
    MODE_REPLAY,
)

from gui.dialogs.archive_dialog import ArchiveDialog
from gui.theme.colors import Colors
from gui.theme.restyle import restyle
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl


class ArchivePicker(QWidget):

    def __init__(self, service, parent=None):

        super().__init__(parent)

        self.service = service

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(10)

        self.mode_switch = SegmentedControl([
            ("Live", MODE_LIVE),
            ("Archiv", MODE_ARCHIVE),
        ])

        self.mode_switch.valueChanged.connect(
            self._on_mode_changed
        )

        layout.addWidget(self.mode_switch)

        #
        # Der Weg in den Archivbrowser. Er steht auch im Live-Modus da
        # und ist dort nicht ausgegraut: "einen vergangenen Pull
        # ansehen" ist eine Absicht, kein Zustand, und ein Knopf, der
        # erst nach dem Umschalten erscheint, verlangt zu wissen, dass
        # es ihn gibt (*lock, don't hide*, wie in core/access.lua).
        #

        self.browse_button = HeroButton("Log wählen …", primary=False)

        self.browse_button.clicked.connect(self.open_browser)

        layout.addWidget(self.browse_button)

        #
        # Der Einstieg in die Wiedergabe. Bewusst hier und nicht in
        # der ReplayBar: solange nichts abgespielt wird, gibt es
        # nichts zu steuern - nur etwas zu starten.
        #

        self.play_button = HeroButton("▶  Wiedergabe")

        self.play_button.clicked.connect(
            self.service.start_replay
        )

        layout.addWidget(self.play_button)

        self.status_label = QLabel("")

        self.status_label.setStyleSheet(
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        layout.addWidget(self.status_label, 1)

        service.archiveChanged.connect(
            self._refresh
        )

        service.replayChanged.connect(
            self._refresh
        )

        self._refresh()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def open_browser(self):
        """
        Den Archivbrowser öffnen.

        Er wird je Aufruf neu gebaut und schliesst mit `exec()` an -
        er ist eine Auswahl, kein Aufenthaltsort, und ein
        weiterlebendes Fenster hinge dauerhaft an `archiveChanged`,
        das während einer Wiedergabe viermal je Sekunde kommt.
        """

        ArchiveDialog(self.service, self).exec()

    def _on_mode_changed(self, value: str):

        if value == MODE_LIVE:

            self.service.show_live()

        else:

            self.service.enter_archive_mode()

            #
            # Der Wechsel auf "Archiv" *ist* die Absicht, einen Pull
            # zu suchen. Ohne diesen Sprung stünde man vor einer
            # leeren Seite und müsste den Knopf daneben erst finden.
            # Nur, wenn noch nichts geladen ist - wer aus der
            # Wiedergabe zurückkommt, will seinen Pull sehen und
            # nicht wieder wählen.
            #

            if self.service.archive_state().selected_fight is None:
                self.open_browser()

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _refresh(self):

        state = self.service.archive_state()

        self.mode_switch.blockSignals(True)

        #
        # Die Wiedergabe ist ein eigener Modus, aber keine eigene
        # Schaltfläche - sie wird immer aus einer der beiden Ansichten
        # heraus gestartet. Ohne diese Zuordnung bliebe der Schalter
        # auf seinem alten Stand stehen: SegmentedControl.setValue()
        # tut bei einem unbekannten Wert stillschweigend nichts.
        #

        self.mode_switch.setValue(
            MODE_LIVE
            if state.mode == MODE_LIVE
            else MODE_ARCHIVE
        )

        self.mode_switch.blockSignals(False)

        self._update_play_button(state)

        self._update_status(state)

    def _update_play_button(self, state: ArchiveState):
        """
        Die Schaltfläche verschwindet, sobald abgespielt wird - ab
        dann übernimmt die ReplayBar. Sie erscheint überhaupt nur,
        wenn es etwas abzuspielen gibt.
        """

        replaying = state.mode == MODE_REPLAY

        #
        # `starting`, nicht `loading`: die Zeitleiste wird schon beim
        # Wählen eines Pulls im Hintergrund geholt. Am ausgegrauten
        # Knopf abzulesen, dass irgendwo etwas lädt, wäre in dem
        # Moment nur irreführend - gedrückt werden darf er trotzdem,
        # der Dienst merkt sich den Start dann vor.
        #

        starting = self.service.replay_state().starting

        self.play_button.setVisible(
            not replaying
            and self.service.replay_available()
        )

        self.play_button.setEnabled(not starting)

        self.play_button.setText(
            "Wird geladen …"
            if starting
            else "▶  Wiedergabe"
        )

    def _update_status(self, state: ArchiveState):

        reason = state.fight_error or state.fights_error or state.reports_error

        if reason and state.mode != MODE_LIVE:

            self.status_label.setText(reason)

            restyle(
                self.status_label,
                f"font-size:11px;color:{Colors.WARNING_LIGHT};",
            )

            return

        if state.fight_loading:
            text = "Pull wird geladen … (bei großen Pulls dauert das etwas)"

        elif state.mode == MODE_LIVE:

            #
            # Im Live-Modus sagt die Kopfzeile der Seite ohnehin,
            # welche Quelle läuft; hier stünde es ein zweites Mal.
            #

            text = ""

        else:

            text = index.selection_text(state) or (
                "Kein Pull gewählt \u2014 \u201eLog w\u00e4hlen \u2026\u201c "
                "\u00f6ffnet das Archiv."
            )

        self.status_label.setText(text)

        restyle(
            self.status_label,
            f"font-size:11px;color:{Colors.TEXT_MUTED};",
        )
