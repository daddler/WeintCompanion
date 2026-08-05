"""
Ein Stylesheet nur dann setzen, wenn es sich geändert hat.

`QWidget.setStyleSheet()` ist kein Setter, sondern ein Eingriff: Qt
verwirft die zwischengespeicherte Stilberechnung des Widgets und
seiner Kinder, parst die Regeln neu, führt ein `polish()` durch und
plant ein Neuzeichnen ein - **auch dann, wenn exakt dieselbe
Zeichenkette schon anliegt**. Qt selbst vergleicht nicht.

Genau das trifft dieses Projekt an der empfindlichsten Stelle. Die
Listen und Tabellen unter `gui/widgets/tv/` sind nach dem Muster
"Zeilen einmal anlegen, danach nur noch beschriften" gebaut - aber
jede Beschriftung setzte bisher auch das Stylesheet der Zelle neu,
obwohl sich meist nur der Text ändert und die Farbe gleich bleibt.
Beim Zeichnen eines einzigen WeintTV-Snapshots kamen so rund 280
`setStyleSheet()`-Aufrufe zusammen; gemessen waren das drei Viertel
der gesamten Rechenzeit eines Bildes. Bei laufender Wiedergabe (vier
Bilder je Sekunde) ist das der Unterschied zwischen einer flüssigen
und einer hakeligen Oberfläche.

Deshalb diese Funktion statt eines direkten Aufrufs überall dort, wo
im Takt neu gezeichnet wird. Sie ist absichtlich winzig und
absichtlich zentral: eine eigene Merkvariable je Widget wäre dieselbe
Prüfung, nur siebenmal abgeschrieben.

Verglichen wird gegen `styleSheet()`, also gegen das, was tatsächlich
am Widget hängt, und nicht gegen einen eigenen Zwischenspeicher - so
bleibt die Funktion auch dann richtig, wenn jemand anders das
Stylesheet gesetzt hat.
"""

from __future__ import annotations


def restyle(widget, sheet: str) -> bool:
    """
    Setzt `sheet` auf `widget`, sofern dort nicht bereits genau das
    steht. Gibt zurück, ob tatsächlich gesetzt wurde.
    """

    if widget.styleSheet() == sheet:
        return False

    widget.setStyleSheet(sheet)

    return True
