"""
WeintCompanion 2.0
Der Zustand des Themes zur Laufzeit

`tokens.py` beantwortet "welche Werte gibt es", dieses Modul
beantwortet "welche gelten gerade": welche der drei Akzentvarianten,
welche der beiden Dichten, und ob der Nutzer Bewegung reduziert hat.

Warum ein Singleton und keine Durchreichung durch den Widgetbaum:
gemalte Widgets brauchen die Akzentfarbe in `paintEvent`, also an einer
Stelle, an der sie keine Argumente entgegennehmen. Der Konstruktor ist
dafuer der falsche Ort - ein Ring, der seine Farbe beim Bau merkt,
bleibt nach einem Akzentwechsel in der alten Farbe stehen, und zwar so
lange, bis ihn zufaellig etwas anderes neu aufbaut. Genau diese Art
Fehler ist im laufenden Betrieb kaum zu finden, weil sie erst nach
einer Einstellungsaenderung sichtbar wird.

Deshalb die Regel, die fuer jedes gemalte Widget gilt:

    Die Akzentfarbe wird in paintEvent gelesen, nie im Konstruktor.

Fuer das Neuzeichnen sorgt `accent_changed`; wer nur malt, verbindet
sich damit auf `update()`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from gui.theme import tokens


class ThemeManager(QObject):
    """
    Akzent, Dichte und Bewegungsvorgabe - lesbar von ueberall,
    aenderbar ueber die Einstellungen.
    """

    #
    # Getrennte Signale, weil die Empfaenger verschieden teuer
    # reagieren: auf einen Akzentwechsel genuegt `update()` (neu
    # malen), ein Dichtewechsel aendert Groessen und verlangt ein
    # neues Layout. Ein gemeinsames "irgendwas hat sich geaendert"
    # wuerde jedes Widget zur teuren Antwort zwingen.
    #

    accent_changed = Signal(str)

    density_changed = Signal(str)

    motion_changed = Signal(bool)

    def __init__(self, config=None):

        super().__init__()

        self._config = config

        self._accent = tokens.ACCENT_DEFAULT

        self._density = tokens.DENSITY_DEFAULT

        self._motion_reduced = False

        #
        # Vom System vorgegebene Bewegungsreduktion. Sie wird getrennt
        # gehalten und nicht in `_motion_reduced` hineingerechnet,
        # damit die ausdrueckliche Wahl des Nutzers erkennbar bleibt:
        # wer die Systemeinstellung spaeter abschaltet, soll nicht
        # ploetzlich eine Einstellung vorfinden, die er nie getroffen
        # hat.
        #

        self._system_motion_reduced = False

        if config is not None:
            self.load_from(config)

    # --------------------------------------------------
    # Einlesen
    # --------------------------------------------------

    def load_from(self, config):
        """
        Die gespeicherten Werte uebernehmen.

        Unbekannte Werte fallen still auf die Voreinstellung zurueck -
        `config.json` ist eine Datei, die von Hand bearbeitet werden
        kann, und eine unbekannte Akzentvariante darf die Oberflaeche
        nicht farblos machen.
        """

        self._config = config

        data = getattr(config, "data", {}) or {}

        stored_accent = data.get("accent", tokens.ACCENT_DEFAULT)

        self._accent = (
            stored_accent
            if stored_accent in tokens.ACCENTS
            else tokens.ACCENT_DEFAULT
        )

        stored_density = data.get("density", tokens.DENSITY_DEFAULT)

        self._density = (
            stored_density
            if stored_density in tokens.DENSITY
            else tokens.DENSITY_DEFAULT
        )

        self._motion_reduced = bool(data.get("motion_reduced", False))

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def accent_name(self) -> str:

        return self._accent

    def accent(self) -> dict:
        """
        Die aktive Akzentvariante als {"base", "light", "onBase"}.
        """

        return tokens.accent(self._accent)

    def accent_base(self) -> str:

        return self.accent()["base"]

    def accent_light(self) -> str:

        return self.accent()["light"]

    def accent_on_base(self) -> str:

        return self.accent()["onBase"]

    def accent_pressed(self) -> str:

        return tokens.ACCENT_PRESSED.get(
            self._accent,
            tokens.ACCENT_PRESSED[tokens.ACCENT_DEFAULT],
        )

    def accent_hover(self) -> tuple[str, str]:

        return tokens.ACCENT_HOVER.get(
            self._accent,
            tokens.ACCENT_HOVER[tokens.ACCENT_DEFAULT],
        )

    def density_name(self) -> str:

        return self._density

    def density(self) -> dict:
        """
        Die aktive Dichte als Tabelle (row, pad_v, pad_h, ...).
        """

        return tokens.density(self._density)

    def metric(self, key: str, fallback: int = 0) -> int:
        """
        Ein einzelner Dichtewert.
        """

        return self.density().get(key, fallback)

    def font_size(self, size: int) -> int:
        """
        Eine Schriftgroesse, um den Dichteversatz verschoben.

        Mindestens 9 px: bei `compact` wuerde `type.micro` sonst auf
        9 px fallen, und darunter sind gesperrte Versalien nicht mehr
        lesbar.
        """

        return max(9, size + self.metric("font_delta"))

    def motion_reduced(self) -> bool:
        """
        Ob Bewegung reduziert werden soll - Nutzerwahl **oder**
        Systemvorgabe.

        Das Oder ist die richtige Verknuepfung: beide Quellen sagen
        dasselbe aus ("weniger Bewegung"), und wer die Systemvorgabe
        gesetzt hat, erwartet sie auch hier.
        """

        return self._motion_reduced or self._system_motion_reduced

    def user_motion_reduced(self) -> bool:
        """
        Nur die ausdrueckliche Wahl des Nutzers - das, was der Schalter
        in den Einstellungen anzeigen muss.
        """

        return self._motion_reduced

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def set_accent(self, name: str):

        if name not in tokens.ACCENTS:
            return

        if name == self._accent:
            return

        self._accent = name

        self._store("accent", name)

        #
        # Reihenfolge: erst das Stylesheet neu setzen, dann das Signal.
        # Andersherum malen die gemalten Widgets in der neuen Farbe,
        # waehrend die Flaechen um sie herum noch die alte tragen -
        # fuer einen Wimpernschlag sichtbar.
        #

        self.apply_stylesheet()

        self.accent_changed.emit(name)

    def set_density(self, name: str):

        if name not in tokens.DENSITY:
            return

        if name == self._density:
            return

        self._density = name

        self._store("density", name)

        self.apply_stylesheet()

        self.density_changed.emit(name)

    def set_motion_reduced(self, reduced: bool):

        reduced = bool(reduced)

        if reduced == self._motion_reduced:
            return

        self._motion_reduced = reduced

        self._store("motion_reduced", reduced)

        self.motion_changed.emit(self.motion_reduced())

    def set_system_motion_reduced(self, reduced: bool):
        """
        Die Systemvorgabe uebernehmen. Wird nicht gespeichert - sie
        gehoert dem Betriebssystem, nicht dieser Anwendung.
        """

        reduced = bool(reduced)

        if reduced == self._system_motion_reduced:
            return

        was_reduced = self.motion_reduced()

        self._system_motion_reduced = reduced

        if self.motion_reduced() != was_reduced:

            self.motion_changed.emit(self.motion_reduced())

    # --------------------------------------------------

    def _store(self, key: str, value):

        if self._config is None:
            return

        self._config.data[key] = value

        self._config.save()

    # --------------------------------------------------
    # Stylesheet
    # --------------------------------------------------

    def apply_stylesheet(self):
        """
        Das globale Stylesheet aus den aktuellen Tokens neu erzeugen
        und setzen.

        Der Import steht im Rumpf: `stylesheet.py` liest dieses Modul,
        um die aktive Variante zu erfragen, ein Import auf Modulebene
        waere also ein Zirkelbezug.
        """

        from PySide6.QtWidgets import QApplication

        from gui.theme.stylesheet import build_stylesheet

        app = QApplication.instance()

        if app is None:
            return

        app.setStyleSheet(build_stylesheet(self))


# ==========================================================
# Zugriff
# ==========================================================

_theme: ThemeManager | None = None


def theme() -> ThemeManager:
    """
    Der eine ThemeManager der Anwendung.

    Wird beim Programmstart ueber `init_theme(config)` mit den
    gespeicherten Einstellungen versorgt. Ohne diesen Aufruf - etwa in
    einem Test, der nur ein einzelnes Widget baut - entsteht er hier
    mit den Voreinstellungen, damit nichts abstuerzt, nur weil kein
    vollstaendiges Programm um das Widget herum laeuft.
    """

    global _theme

    if _theme is None:
        _theme = ThemeManager()

    return _theme


def init_theme(config) -> ThemeManager:
    """
    Den ThemeManager mit der Konfiguration verbinden. Einmal beim
    Programmstart, vor dem Bau des Hauptfensters.
    """

    manager = theme()

    manager.load_from(config)

    return manager
