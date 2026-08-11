"""
Die Vorschaukarten für Akzent und Dichte.

Sie standen bis hierher privat im Einrichtungsassistenten
(`gui/dialogs/setup_wizard.py`) - und damit an der einen Stelle, an der
man sie **genau einmal** sieht, nämlich beim ersten Start. Der
Bereich, dessen Aufgabe das Erscheinungsbild ist (Einstellungen →
Erscheinungsbild), hatte gar kein Bedienelement: wer den Assistenten
einmal durchlaufen hatte, konnte Akzent und Dichte nie wieder ändern,
obwohl `ThemeManager` beides samt Speicherung und Signal längst
beherrscht.

Deshalb liegen die Karten jetzt hier, und mit ihnen die Beschriftungen.
Die Namen der Varianten in zwei Listen zu pflegen wäre genau der
Fehler, den `PageId`/`build_page_specs()` für die Navigation und
`tokens.py` für die Farben vermeiden: eine vierte Akzentvariante wäre
sonst in einem der beiden Bereiche sichtbar und im anderen nicht.

`ACCENT_LABELS` leitet sich aus `tokens.ACCENTS` ab, statt die Namen
noch einmal aufzuzählen: eine neue Variante erscheint damit
automatisch in Assistent und Einstellungen. Fehlt eine Beschriftung,
wird der technische Name gezeigt - sichtbar unfertig, aber nicht
fehlend, und niemals eine stillschweigend verschwundene Variante.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.card import Card
from gui.widgets.chip import Chip


#
# Deutsche Beschriftungen der Akzentvarianten.
#

ACCENT_TEXTS = {
    "amber": "Bernstein",
    "arcane": "Arkan-Violett",
    "jade": "Jade",
}


def accent_labels() -> tuple[tuple[str, str], ...]:
    """
    Alle Akzentvarianten in der Reihenfolge der Token-Tabelle.
    """

    return tuple(
        (name, ACCENT_TEXTS.get(name, name))
        for name in tokens.ACCENTS
    )


DENSITY_TEXTS = {
    "comfortable": "Komfortabel",
    "compact": "Kompakt",
}


def density_labels() -> tuple[tuple[str, str], ...]:

    return tuple(
        (name, DENSITY_TEXTS.get(name, name))
        for name in tokens.DENSITY
    )


class _Swatch(Card):
    """
    Gemeinsames Verhalten: anklickbar, zeigt "GEWÄHLT", hebt sich in
    der Akzentfarbe hervor, wenn sie die aktive Wahl ist.
    """

    chosen = Signal(str)

    def __init__(self, name: str, parent=None):

        super().__init__(parent=parent)

        self._name = name

        self.setCursor(Qt.PointingHandCursor)

    def _add_check(self):

        self.check = Chip("GEWÄHLT", "ok")

        self.check.setVisible(False)

        self.addWidget(self.check)

    def name(self) -> str:

        return self._name

    def set_selected(self, selected: bool):

        self.check.setVisible(selected)

        self.setAccent(selected)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self._apply()

            #
            # Zusätzlich zum Setzen melden, damit eine Seite ihre
            # eigene Auswahlanzeige nachziehen kann, ohne den
            # ThemeManager beobachten zu müssen.
            #

            self.chosen.emit(self._name)

        super().mousePressEvent(event)

    def _apply(self):

        raise NotImplementedError


class AccentSwatch(_Swatch):
    """
    Eine Vorschaukarte für eine Akzentvariante.
    """

    def __init__(self, name: str, label: str = "", parent=None):

        super().__init__(name, parent=parent)

        accent = tokens.ACCENTS[name]

        dot = QLabel()

        dot.setFixedSize(24, 24)

        #
        # Die eigene Farbe der Variante, nicht die aktive: die Karte
        # zeigt, was man WÄHLEN kann. Genau deshalb darf sie hier aus
        # der Token-Tabelle lesen und nicht aus `theme()`.
        #

        restyle(
            dot,
            f"""
            QLabel{{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 {accent["light"]},
                    stop:1 {accent["base"]}
                );
                border-radius:12px;
            }}
            """,
        )

        self.addWidget(dot)

        text = QLabel(label or ACCENT_TEXTS.get(name, name))

        text.setFont(font("small"))

        restyle(
            text,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        self.addWidget(text)

        self._add_check()

    def _apply(self):

        theme().set_accent(self._name)


class DensitySwatch(_Swatch):
    """
    Eine Vorschaukarte für eine Dichte.
    """

    def __init__(self, name: str, label: str = "", parent=None):

        super().__init__(name, parent=parent)

        text = QLabel(label or DENSITY_TEXTS.get(name, name))

        text.setFont(font("card"))

        restyle(
            text,
            f"color:{tokens.WHITE};background:transparent;",
        )

        self.addWidget(text)

        #
        # Was die Wahl bedeutet - ohne diese Zeile ist "Kompakt" ein
        # Wort ohne Folge.
        #

        metrics = tokens.density(name)

        hint = QLabel(
            f"Zeilenhöhe {metrics['row']} px, Knopfhöhe "
            f"{metrics['btn']} px"
        )

        hint.setFont(font("small"))

        restyle(
            hint,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.addWidget(hint)

        self._add_check()

    def _apply(self):

        theme().set_density(self._name)
