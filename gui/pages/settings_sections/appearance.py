"""
Einstellungen -> Erscheinungsbild.

Dieser Bereich zeigte bis hierher **vier Farbfelder und einen Satz über
den Dunkelmodus** - und sonst nichts. Das war der grösste Blindgänger
des 2.0-Umbaus: `ThemeManager` verwaltet drei Wahlmöglichkeiten des
Nutzers (Akzent, Dichte, reduzierte Bewegung), speichert sie in
`config.json` und kündigt jede mit einem eigenen Signal an - aber die
einzige Stelle, an der man sie setzen konnte, war der
Einrichtungsassistent beim ersten Start. Wer ihn einmal durchlaufen
hatte, kam nie wieder an die Wahl heran.

Dass die Schalter vorgesehen waren, steht im ThemeManager selbst:
`user_motion_reduced()` existiert ausdrücklich für "das, was der
Schalter in den Einstellungen anzeigen muss" - es gab nur keinen
Schalter.

Zwei Feinheiten, die beide eine falsche Anzeige verhindern:

- Die Farbfelder lesen den **aktiven** Akzent und werden bei
  `accent_changed` neu gesetzt. Vorher standen sie auf `Colors.PRIMARY`,
  also auf dem statischen Bernstein des Übergangsmoduls - auf genau der
  Seite, auf der man den Akzent wechselt, blieb die Vorschau damit
  falsch.
- Der Bewegungsschalter zeigt `user_motion_reduced()` und nicht
  `motion_reduced()`. Letzteres ist die Oder-Verknüpfung mit der
  Systemvorgabe: hätte das System sie gesetzt, stünde der Schalter auf
  "ein", und ein Klick darauf würde nichts sichtbar ändern - er sähe
  kaputt aus. Stattdessen sagt eine Zeile darunter, wenn das System
  mitredet.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme.colors import Colors
from gui.theme.theme_manager import theme
from gui.widgets.appearance_picker import (
    AccentSwatch,
    DensitySwatch,
    accent_labels,
    density_labels,
)
from gui.widgets.toggle_switch import ToggleSwitch

from ._common import SectionContent, toggle_row


def _label(text: str) -> QLabel:

    label = QLabel(text)

    label.setStyleSheet(
        f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
    )

    return label


def _description(text: str) -> QLabel:

    label = QLabel(text)

    label.setWordWrap(True)

    label.setStyleSheet(
        f"font-size:13px;color:{Colors.TEXT_MUTED};"
    )

    return label


class AppearanceSection(SectionContent):

    def __init__(self, manager):

        super().__init__(
            "EINSTELLUNGEN · ERSCHEINUNGSBILD",
            "Erscheinungsbild",
            "Akzentfarbe, Dichte und Bewegung. WeintCompanion nutzt "
            "ausschließlich ein dunkles Farbschema - ein Hell-Modus ist "
            "nicht geplant.",
        )

        self.manager = manager

        #
        # --------------------------------------------------
        # Akzentfarbe
        # --------------------------------------------------
        #

        accent_col = QVBoxLayout()

        accent_col.setSpacing(10)

        accent_col.addWidget(_label("Akzentfarbe"))

        accent_col.addWidget(
            _description(
                "Trägt die Bedeutung: Hauptknöpfe, Ringe, Balken und "
                "die aktive Seite in der Navigation."
            )
        )

        accent_row = QHBoxLayout()

        accent_row.setContentsMargins(0, 0, 0, 0)

        accent_row.setSpacing(12)

        self.accent_swatches: dict[str, AccentSwatch] = {}

        for name, label in accent_labels():

            swatch = AccentSwatch(name, label)

            accent_row.addWidget(swatch)

            self.accent_swatches[name] = swatch

        accent_row.addStretch(1)

        accent_col.addLayout(accent_row)

        self.addRow(accent_col)

        #
        # --------------------------------------------------
        # Dichte
        # --------------------------------------------------
        #

        density_col = QVBoxLayout()

        density_col.setSpacing(10)

        density_col.addWidget(_label("Dichte"))

        density_col.addWidget(
            _description(
                "Wie viel Luft zwischen den Zeilen steht. Kompakt "
                "bringt mehr auf einen Bildschirm - für WeintTV mit "
                "25 Zeilen der Unterschied zwischen Scrollen und nicht."
            )
        )

        density_row = QHBoxLayout()

        density_row.setContentsMargins(0, 0, 0, 0)

        density_row.setSpacing(12)

        self.density_swatches: dict[str, DensitySwatch] = {}

        for name, label in density_labels():

            swatch = DensitySwatch(name, label)

            density_row.addWidget(swatch)

            self.density_swatches[name] = swatch

        density_row.addStretch(1)

        density_col.addLayout(density_row)

        self.addRow(density_col)

        #
        # --------------------------------------------------
        # Bewegung
        # --------------------------------------------------
        #

        self.motion_toggle = ToggleSwitch()

        self.motion_toggle.toggled.connect(self._save_motion)

        self.addRow(
            toggle_row(
                "Bewegung reduzieren",
                "Blendet Seitenübergänge, Pulsieren und Balken-"
                "Animationen aus. Statusfarben und Text bleiben "
                "unverändert.",
                self.motion_toggle,
            ),
            divider=False,
        )

        #
        # Wenn das Betriebssystem "weniger Bewegung" vorgibt, gilt das
        # ohnehin - ohne diesen Hinweis sähe ein ausgeschalteter
        # Schalter bei ruhender Oberfläche wie ein Fehler aus.
        #

        self.motion_hint = _description("")

        self.motion_hint.setVisible(False)

        self.addRow(self.motion_hint, divider=False)

        #
        # --------------------------------------------------
        # Palette
        # --------------------------------------------------
        #

        palette_col = QVBoxLayout()

        palette_col.setSpacing(10)

        palette_col.addWidget(_label("Palette"))

        palette_col.addWidget(
            _description(
                "Hintergrund, Karte und die beiden Akzenttöne der "
                "aktuellen Wahl."
            )
        )

        swatch_row = QWidget()

        layout = QHBoxLayout(swatch_row)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(8)

        self._palette: list[QLabel] = []

        for _ in range(4):

            swatch = QLabel()

            swatch.setFixedSize(40, 40)

            layout.addWidget(swatch)

            self._palette.append(swatch)

        layout.addStretch()

        palette_col.addWidget(swatch_row)

        self.addRow(palette_col, divider=False)

        #
        # Im Konstruktor verbinden, nicht im Handler, den sie auslöst -
        # sonst verdoppelt sich die Verbindung bei jedem Wechsel.
        #

        theme().accent_changed.connect(self._on_theme_changed)

        theme().density_changed.connect(self._on_theme_changed)

        theme().motion_changed.connect(self._on_theme_changed)

        self.refresh()

    # --------------------------------------------------

    def _save_motion(self, reduced: bool):

        theme().set_motion_reduced(bool(reduced))

    def _on_theme_changed(self, *_args):

        self.refresh()

    # --------------------------------------------------

    def refresh(self):

        manager = theme()

        for name, swatch in self.accent_swatches.items():

            swatch.set_selected(name == manager.accent_name())

        for name, swatch in self.density_swatches.items():

            swatch.set_selected(name == manager.density_name())

        #
        # Die ausdrückliche Wahl des Nutzers, nicht die Oder-
        # Verknüpfung mit der Systemvorgabe (siehe Modulkommentar).
        #

        self.motion_toggle.blockSignals(True)

        self.motion_toggle.setChecked(manager.user_motion_reduced())

        self.motion_toggle.blockSignals(False)

        forced_by_system = (
            manager.motion_reduced()
            and not manager.user_motion_reduced()
        )

        self.motion_hint.setVisible(forced_by_system)

        if forced_by_system:

            self.motion_hint.setText(
                "Das Betriebssystem gibt bereits \"weniger Bewegung\" "
                "vor - die Oberfläche bewegt sich deshalb ohnehin "
                "nicht, unabhängig von diesem Schalter."
            )

        self._apply_palette()

    def _apply_palette(self):

        manager = theme()

        colors = (
            Colors.BACKGROUND,
            Colors.SURFACE,
            manager.accent_base(),
            manager.accent_light(),
        )

        for swatch, color in zip(self._palette, colors):

            swatch.setStyleSheet(
                f"""
                QLabel{{
                    background:{color};
                    border:1px solid {Colors.BORDER_LIGHT};
                    border-radius:8px;
                }}
                """
            )
