"""
Vorbereitung.

Wie `characters.py` bis 2.0.0 eine Seite **ohne Datenquelle im
Programm** - der Entwurf sah hier ein Raster aus Charakterkarten vor,
je Karte ein Fortschrittsring und die Mängel darunter (fehlende
Verzauberungen, leere Sockel, offene BiS-Plätze), und keiner dieser
drei Werte kam irgendwo vor. Ein Ring bei 0 % wäre die falsche Antwort
gewesen: er behauptet eine Messung ("nichts vorbereitet"), wo es gar
keine gab.

Seit WeintCodex 1.3.3.1 liefert das Addon genau diese drei Werte
(`"character_sheet"`, siehe `core/character_sheet_sync.py`) - und
zwar bereits **bewertet**: welche Verzauberung optimal ist, welcher
Stein falsch sitzt und welcher Wert über dem Cap liegt, entscheidet
`modules/charakter.lua` im Spiel, wo Spec-Profile, Caps und
Sockelboni bekannt sind. Diese Seite ist deshalb wie WeintTV und die
Academy eine **reine Anzeige**: sie rechnet nichts nach, und damit
können Spiel und Desktop nicht auseinanderlaufen.

Die alte Unterscheidung bleibt trotzdem tragend, sie steht nur an
einer anderen Stelle:

* Ein Ring **ohne** Wert (`readiness() is None`) heißt "das Addon hat
  hier nichts geprüft" und wird als solcher beschriftet.
* Offene **BiS-Plätze** zählen bewusst nicht in den Ring. Sie hängen
  an Würfelglück, nicht an Vorbereitung - sie färbten den Ring eines
  frisch ausgestatteten Charakters dauerhaft rot für etwas, das er
  nicht abstellen kann. Sie stehen als eigene Zeile daneben.
* Ist für eine Spezialisierung gar keine BiS-Liste gepflegt, sagt die
  Zeile das, statt "0 offen" zu zeigen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.character_sheet_sync import readiness
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.wow_colors import class_color, class_label
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.empty_state import EmptyState
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.progress_ring import ProgressRing
from gui.widgets.wrapped_label import enable_wrap


COLUMNS = 2


#
# Wie viele Mängel eine Karte zeigt. Das Addon liefert sie bereits
# nach Dringlichkeit sortiert (prio 1 = fehlt, 4 = nicht ideal); mehr
# als vier Zeilen machen aus einer Karte eine Liste, und die
# dringendste steht dann nicht mehr oben, sondern irgendwo.
#

MAX_ISSUES = 4


#
# Farbe je Mangelart. `overcap` ist bewusst nicht rot: ein Wert über
# dem Cap ist verschenkte Wertung, kein fehlendes Teil.
#

ISSUE_COLORS = {
    "missing": tokens.STATE["error"],
    "wrong": tokens.STATE["warn"],
    "overcap": tokens.STATE["info"],
    "ok": tokens.TEXT["secondary"],
}


def _divider() -> QFrame:

    line = QFrame()

    line.setFixedHeight(1)

    line.setStyleSheet(f"background:{tokens.SURFACE['raised']};border:none;")

    return line


class PreparationCard(Card):
    """
    Eine Karte je Charakter: Ring links, Mängel rechts.
    """

    def __init__(self, sheet: dict, parent=None):

        super().__init__(parent=parent)

        color = class_color(sheet.get("class", ""))

        self.setEdgeColor(tokens.tint(color, 0.34))

        #
        # Kopf
        #

        head = QVBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(2)

        name = QLabel(sheet.get("name", ""))

        name.setFont(font("h2"))

        restyle(name, f"color:{color};background:transparent;")

        head.addWidget(name)

        subtitle = QLabel(
            " · ".join(
                part
                for part in (
                    sheet.get("spec", ""),
                    class_label(sheet.get("class", "")),
                )
                if part
            )
        )

        subtitle.setFont(font("small"))

        restyle(
            subtitle,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        head.addWidget(subtitle)

        self.addLayout(head)

        self.addSpacing(tokens.SPACE[1])

        #
        # Ring und Kennzahlen
        #

        body = QHBoxLayout()

        body.setContentsMargins(0, 0, 0, 0)

        body.setSpacing(tokens.SPACE[4])

        ring_column = QVBoxLayout()

        ring_column.setContentsMargins(0, 0, 0, 0)

        ring_column.setSpacing(tokens.SPACE[1])

        self.ring = ProgressRing(88)

        ring_column.addWidget(self.ring, alignment=Qt.AlignHCenter)

        ratio = readiness(sheet)

        if ratio is None:

            #
            # Der Ring bleibt auf 0 - aber der Chip darunter sagt,
            # dass das keine Messung ist. Ohne ihn läse sich der leere
            # Ring als "nichts vorbereitet".
            #

            ring_column.addWidget(
                Chip("KEINE PRÜFUNG", "neutral"),
                alignment=Qt.AlignHCenter,
            )

        else:

            self.ring.setValue(ratio)

            ring_column.addWidget(
                Chip(
                    "VOLLSTÄNDIG" if ratio >= 0.999 else f"{ratio * 100:.0f} %",
                    "ok" if ratio >= 0.999 else "warn",
                ),
                alignment=Qt.AlignHCenter,
            )

        body.addLayout(ring_column)

        #
        # Rechts: Verzauberungen, Sockel, BiS
        #

        numbers = QVBoxLayout()

        numbers.setContentsMargins(0, 0, 0, 0)

        numbers.setSpacing(tokens.SPACE[1])

        numbers.addLayout(
            _counter_row("Verzauberungen", sheet.get("enchants"))
        )

        numbers.addLayout(
            _counter_row("Sockel", sheet.get("gems"))
        )

        numbers.addLayout(_bis_row(sheet.get("bis")))

        numbers.addStretch(1)

        body.addLayout(numbers, 1)

        self.addLayout(body)

        #
        # Mängel
        #

        issues = (sheet.get("issues") or [])[:MAX_ISSUES]

        if issues:

            self.addWidget(_divider())

            for issue in issues:

                self.addWidget(_issue_label(issue))

            rest = len(sheet.get("issues") or []) - len(issues)

            if rest > 0:

                more = QLabel(
                    f"… und {rest} weitere{'r' if rest == 1 else ''} "
                    f"Hinweis{'' if rest == 1 else 'e'} im Spiel "
                    f"(Charakter → Ausrüstung)."
                )

                more.setFont(font("small"))

                enable_wrap(more)

                restyle(
                    more,
                    f"color:{tokens.TEXT['muted']};background:transparent;",
                )

                self.addWidget(more)

        elif ratio is not None:

            self.addWidget(_divider())

            done = QLabel("Keine offenen Punkte - alles verzaubert und gesockelt.")

            done.setFont(font("small"))

            enable_wrap(done)

            restyle(
                done,
                f"color:{tokens.STATE['ok']};background:transparent;",
            )

            self.addWidget(done)

        self.addStretch(1)


def _counter_row(label: str, counts: dict | None) -> QHBoxLayout:
    """
    Eine Zeile "Verzauberungen   9 / 10".

    Ohne Zähler steht dort "keine Angaben" und keine Null - der
    Unterschied zwischen einem Befund und einer Datenlücke, derselbe
    wie bei `stars == 0` im Analyzer.
    """

    row = QHBoxLayout()

    row.setContentsMargins(0, 0, 0, 0)

    row.setSpacing(tokens.SPACE[2])

    caption = QLabel(label)

    caption.setFont(font("small"))

    restyle(
        caption,
        f"color:{tokens.TEXT['secondary']};background:transparent;",
    )

    row.addWidget(caption)

    row.addStretch(1)

    if not counts or counts.get("total", 0) <= 0:

        value = QLabel("keine Angaben")

        color = tokens.TEXT["muted"]

    else:

        total = counts.get("total", 0)

        filled = total - counts.get("missing", 0)

        value = QLabel(f"{filled} / {total}")

        color = (
            tokens.STATE["ok"]
            if filled >= total
            else tokens.STATE["warn"]
        )

    value.setFont(font("body"))

    restyle(value, f"color:{color};background:transparent;")

    row.addWidget(value)

    return row


def _bis_row(bis: dict | None) -> QHBoxLayout:

    row = QHBoxLayout()

    row.setContentsMargins(0, 0, 0, 0)

    row.setSpacing(tokens.SPACE[2])

    caption = QLabel("Offene BiS-Plätze")

    caption.setFont(font("small"))

    restyle(
        caption,
        f"color:{tokens.TEXT['secondary']};background:transparent;",
    )

    row.addWidget(caption)

    row.addStretch(1)

    if not bis or bis.get("total", 0) <= 0:

        #
        # Für diese Spezialisierung ist keine BiS-Liste gepflegt. "0
        # offen" behauptete hier eine geprüfte Vollständigkeit.
        #

        value = QLabel("keine Liste")

        color = tokens.TEXT["muted"]

    else:

        open_count = bis.get("open", 0)

        value = QLabel(f"{open_count} von {bis.get('total', 0)}")

        color = (
            tokens.STATE["ok"]
            if open_count == 0
            else tokens.TEXT["primary"]
        )

    value.setFont(font("body"))

    restyle(value, f"color:{color};background:transparent;")

    row.addWidget(value)

    return row


def _issue_label(issue: dict) -> QLabel:

    label = QLabel(issue.get("text", ""))

    label.setFont(font("small"))

    enable_wrap(label)

    restyle(
        label,
        "color:"
        + ISSUE_COLORS.get(issue.get("status", ""), tokens.TEXT["secondary"])
        + ";background:transparent;",
    )

    return label


class PreparationPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "VORBEREITUNG",
            "Vor dem Raid steht die Ausrüstung.",
            parent,
        )

        self.empty = EmptyState(
            eyebrow="NOCH KEINE DATEN",
            title="Das Addon hat noch keine Ausrüstung gemeldet.",
            explanation=(
                "Verzauberungen, Sockel und offene BiS-Plätze kommen "
                "aus dem Spiel. WeintCodex prüft sie beim Anmelden und "
                "nach jedem Ausrüstungswechsel - melde dich einmal an, "
                "danach steht der Stand hier."
            ),
            action="Addon prüfen",
            icon="vorbereitung",
        )

        self.empty.actionTriggered.connect(self._open_addon)

        self.addWidget(self.empty, 1)

        self.grid_host = QWidget()

        self.grid = QGridLayout(self.grid_host)

        self.grid.setContentsMargins(0, 0, 0, 0)

        self.grid.setSpacing(tokens.SPACE[3])

        self.grid.setAlignment(Qt.AlignTop)

        self.addWidget(self.grid_host, 1)

        self.grid_host.hide()

        self._signature = None

    # --------------------------------------------------

    def _open_addon(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ADDON)

    # --------------------------------------------------

    def refresh(self):

        store = getattr(self.manager, "characters", None)

        sheets = store.characters() if store is not None else []

        signature = tuple(
            (
                sheet.get("name"),
                sheet.get("realm"),
                sheet.get("updated"),
            )
            for sheet in sheets
        )

        if signature != self._signature:

            self._signature = signature

            self._fill(sheets)

        self._apply_title(sheets, store)

    # --------------------------------------------------

    def _apply_title(self, sheets: list[dict], store):

        if not sheets or store is None:

            self.header.setTitle("Vor dem Raid steht die Ausrüstung.")

            return

        summary = store.preparation_summary()

        if summary["ratio"] is None:

            self.header.setTitle(
                "Für keinen Charakter liegt eine Prüfung vor."
            )

            return

        open_count = summary["open"]

        if open_count == 0:

            self.header.setTitle("Alles verzaubert und gesockelt.")

            return

        self.header.setTitle(
            f"{open_count} offene Stelle{'n' if open_count != 1 else ''} "
            f"in deiner Ausrüstung."
        )

    def _fill(self, sheets: list[dict]):

        while self.grid.count():

            item = self.grid.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if not sheets:

            self.grid_host.hide()

            self.empty.show()

            return

        self.empty.hide()

        #
        # Der schlechteste Stand zuerst: die Seite fragt, wo noch etwas
        # zu tun ist. Ein Charakter ohne Prüfung steht ganz hinten - er
        # ist kein Mangel, sondern eine Lücke.
        #

        def order(sheet):

            ratio = readiness(sheet)

            return (1, 0.0) if ratio is None else (0, ratio)

        for index, sheet in enumerate(sorted(sheets, key=order)):

            self.grid.addWidget(
                PreparationCard(sheet),
                index // COLUMNS,
                index % COLUMNS,
            )

        for column in range(COLUMNS):
            self.grid.setColumnStretch(column, 1)

        #
        # Der freie Platz gehört unter die Karten, nicht in sie hinein.
        # Ohne diese Zeile zieht das Raster die letzte Zeile über die
        # ganze Resthöhe, und eine Karte mit vier Zeilen Inhalt ist
        # 600 px hoch.
        #

        self.grid.setRowStretch(self.grid.rowCount(), 1)

        self.grid_host.show()
