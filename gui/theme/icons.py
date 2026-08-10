"""
WeintCompanion 2.0
Symbole in Themefarbe

Die Symbole sind einfarbige SVGs unter `resources/icons/`. Der Entwurf
verlangt, dass sie ihre Farbe aus dem Theme beziehen - ein aktiver
Navigationseintrag traegt sein Symbol in Akzentfarbe, derselbe Eintrag
inaktiv in `text.muted`, und beim Wechsel der Akzentvariante aendert
sich das mit.

Das Faerben passiert deshalb zur Laufzeit ueber
`CompositionMode_SourceIn`: die Deckfarbe wird ueber das gerenderte
Symbol gelegt und nur dort behalten, wo das Symbol deckend ist. Die
Alternative - je Farbe eine eigene SVG-Datei - waere bei drei Akzenten
mal zwei Zustaenden mal siebzehn Symbolen unhaltbar.

**Der Zwischenspeicher ist nicht optional.** Ein Navigationseintrag
faerbt sein Symbol bei jedem Zeichnen neu ein; ohne Cache waere das je
Bild ein SVG-Parse plus eine Rasterung. Der Schluessel enthaelt
deshalb alles, was das Ergebnis bestimmt - Name, Farbe, Groesse und
das Geraeteverhaeltnis, denn auf einem HiDPI-Bildschirm ist dasselbe
Symbol in derselben logischen Groesse eine andere Pixmap.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from core.resources import Resources


_cache: dict[tuple, QPixmap] = {}


def _device_ratio() -> float:

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        return 1.0

    return float(app.devicePixelRatio())


def tinted_pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    """
    Ein Symbol als Pixmap in der gewuenschten Farbe.

    `name` ist der Dateiname ohne Endung unter `resources/icons/`.
    """

    ratio = _device_ratio()

    key = (name, color, size, ratio)

    cached = _cache.get(key)

    if cached is not None:
        return cached

    path = Resources.path(f"resources/icons/{name}.svg")

    pixels = max(1, int(round(size * ratio)))

    pixmap = QPixmap(pixels, pixels)

    pixmap.fill(Qt.transparent)

    renderer = QSvgRenderer(path)

    if renderer.isValid():

        painter = QPainter(pixmap)

        painter.setRenderHint(QPainter.Antialiasing, True)

        renderer.render(
            painter,
            QRectF(0, 0, pixels, pixels),
        )

        #
        # Die eigentliche Einfaerbung: die Deckfarbe bleibt nur dort
        # stehen, wo das Symbol deckend gezeichnet wurde.
        #

        painter.setCompositionMode(
            QPainter.CompositionMode_SourceIn
        )

        painter.fillRect(
            pixmap.rect(),
            QColor(color),
        )

        painter.end()

    pixmap.setDevicePixelRatio(ratio)

    _cache[key] = pixmap

    return pixmap


def tinted(name: str, color: str, size: int = 18) -> QIcon:
    """
    Dasselbe als QIcon - fuer alles, was ein Icon erwartet
    (Knoepfe, Tray, Fensterzeichen).
    """

    return QIcon(tinted_pixmap(name, color, size))


def clear_cache():
    """
    Den Zwischenspeicher leeren.

    Noetig nach einem Wechsel des Geraeteverhaeltnisses (Fenster auf
    einen anderen Bildschirm gezogen). Ein Akzentwechsel braucht das
    **nicht**: die Farbe steht im Schluessel, die neue Farbe ergibt
    schlicht einen neuen Eintrag.
    """

    _cache.clear()
