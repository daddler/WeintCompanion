"""
Die Quellenzeile: woher kommen diese Zahlen - und wie komme ich an
andere?

**Warum es sie gibt.** WeintTV trug bis 3.5.0 einen kleinen grauen
Chip "Simulation", die Academy und das Archiv gar nichts. Umstellen
liess sich die Quelle ausschliesslich in *Einstellungen · Module* -
also an einer Stelle, die niemand aufsucht, der gerade vor einem
Dashboard voller Zahlen sitzt und wissen will, warum sein Raid nicht
darin vorkommt. Die häufigste Verwechslung war genau die: erfundene
Beispieldaten für den eigenen Abend zu halten.

Diese Zeile steht deshalb auf allen drei Seiten und sagt drei Dinge:
welche Quelle eingestellt ist, was das bedeutet, und - direkt daneben -
wie man sie wechselt. Dazu der Weg in den Wegweiser
(`gui/dialogs/guide_dialog.py`).

Vier Dinge, die nicht Geschmack sind:

- **Eine Beispielquelle wird als solche benannt**, in Warnfarbe. Nicht
  weil die Simulation ein Fehler wäre - sie ist genau richtig, um die
  Ansichten außerhalb der Raidzeiten anzusehen - sondern weil "das
  gehört niemandem" die Auskunft ist, ohne die die Zahlen falsch
  gelesen werden. Welche Quelle das ist, entscheidet
  `core/raid_data_service.is_demo_source()` und nicht ein
  `== SOURCE_MOCK` in drei Seiten.
- **Gewechselt wird über `RaidDataService.set_source()`**, dieselbe
  Stelle wie in den Einstellungen. Vier Fassungen desselben Ablaufs
  würden ab der ersten Änderung verschieden aufräumen.
- **Die Zeile hört auf `sourceChanged`**, damit ein Wechsel in den
  Einstellungen hier nicht als alter Stand stehen bleibt.
- **Der Auswahlkasten wird beim Setzen stummgeschaltet.** Ohne das
  löste das Nachziehen des Standes einen weiteren Wechsel aus -
  derselbe Kreis wie beim Moduswähler im `ArchivePicker`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel

from core.raid_data_service import (
    SOURCE_LABELS,
    SOURCE_MOCK,
    SOURCE_SHORT,
    SOURCE_WARCRAFTLOGS,
    is_demo_source,
)

from gui.dialogs.guide_dialog import GuideDialog
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.select import Select
from gui.widgets.wrapped_label import enable_wrap


#
# Reihenfolge des Auswahlkastens - dieselbe wie in den Einstellungen:
# die Simulation zuletzt, weil sie der Rückfall ist und nicht das Ziel.
#

SOURCE_ORDER = (
    SOURCE_WARCRAFTLOGS,
    SOURCE_MOCK,
)


class SourceStrip(Card):

    def __init__(self, service, parent=None):

        super().__init__(parent=parent)

        self.service = service

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        # --------------------------------------------------
        # Links: was gerade gilt
        # --------------------------------------------------

        #
        # Eine Zeile und keine zwei. WeintTV lebt von Dichte - jeder
        # eingesparte senkrechte Abstand ist dort eine weitere Zeile
        # Rangliste - und diese Auskunft passt in eine.
        #

        row.addWidget(eyebrow_label("DATENQUELLE"))

        self.headline = QLabel("")

        self.headline.setFont(font("card"))

        row.addWidget(self.headline)

        self.detail = enable_wrap(QLabel(""))

        self.detail.setFont(font("small"))

        restyle(
            self.detail,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        row.addWidget(self.detail, 1)

        # --------------------------------------------------
        # Rechts: umschalten und nachlesen
        # --------------------------------------------------

        self.picker = Select()

        self.picker.setMinimumWidth(170)

        self.picker.currentIndexChanged.connect(self._on_picked)

        row.addWidget(self.picker)

        self.guide_button = HeroButton("Was ist das hier?", primary=False)

        self.guide_button.clicked.connect(self.open_guide)

        row.addWidget(self.guide_button)

        self.addLayout(row)

        service.sourceChanged.connect(self._refresh)

        self._refresh()

    # --------------------------------------------------
    # Nutzeraktionen
    # --------------------------------------------------

    def open_guide(self):
        """
        Der Wegweiser wird je Aufruf neu gebaut und mit `exec()`
        angeschlossen - er ist eine Auskunft, kein Aufenthaltsort.
        Dieselbe Überlegung wie beim Archivbrowser.
        """

        GuideDialog(self).exec()

    def _on_picked(self, index: int):

        source = self.picker.itemData(index)

        if not source:
            return

        #
        # `set_source()` meldet selbst, ob sich etwas geändert hat, und
        # sendet dann `sourceChanged` - das Nachziehen der Zeile
        # passiert also über denselben Weg wie bei einem Wechsel in den
        # Einstellungen und nicht daneben.
        #

        self.service.set_source(str(source))

    # --------------------------------------------------
    # Zustand übernehmen
    # --------------------------------------------------

    def _refresh(self):

        source = self.service.active_source()

        demo = is_demo_source(source)

        self.headline.setText(
            SOURCE_LABELS.get(source, source) or "Keine Datenquelle"
        )

        restyle(
            self.headline,
            "color:%s;background:transparent;" % (
                tokens.STATE["warn"] if demo else tokens.TEXT["primary"]
            ),
        )

        self.detail.setText(
            SOURCE_SHORT.get(source, "")
            or "Diese Quelle kennt die Companion nicht."
        )

        self.picker.blockSignals(True)

        self.picker.set_items(
            [(SOURCE_LABELS.get(key, key), key) for key in SOURCE_ORDER],
            current=self.service.configured_source(),
        )

        self.picker.blockSignals(False)
