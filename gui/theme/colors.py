"""
WeintCompanion Theme
Farben

**Uebergangsmodul.** Seit 2.0 stehen alle Farbwerte in
`gui/theme/tokens.py`; hier steht kein einziger Hex-Wert mehr, sondern
nur noch die Zuordnung der alten Namen auf die neuen Tokens.

Der Grund fuer diesen Zwischenschritt: `Colors.*` wird an mehreren
hundert Stellen unter `gui/` gelesen. Die Datei ersatzlos zu loeschen
haette bedeutet, saemtliche Seiten und Widgets in einem einzigen
Schritt umzustellen - ein Umbau, bei dem ein uebersehener Aufruf erst
zur Laufzeit auffaellt, und zwar auf der Seite, die man gerade nicht
geoeffnet hat. Stattdessen bleibt der Name bestehen und liefert den
neuen Wert, waehrend die Seiten nacheinander auf `theme()` umziehen.

Eine Einschraenkung, die dieses Modul nicht aufloesen kann: die Werte
hier sind **statisch**. Sie werden beim Import festgelegt und folgen
deshalb keinem Akzentwechsel zur Laufzeit. Wer die Akzentfarbe braucht,
liest sie ueber `gui.theme.theme_manager.theme()` - im `paintEvent`,
nicht im Konstruktor. Was hier steht, ist die Voreinstellung
(Bernstein) und damit fuer neutrale Flaechen richtig, fuer
bedeutungstragende Akzente nur so lange, bis die betreffende Stelle
umgestellt ist.
"""

from dataclasses import dataclass

from gui.theme import tokens


_ACCENT = tokens.ACCENTS[tokens.ACCENT_DEFAULT]


@dataclass(frozen=True)
class Colors:

    # -------------------------------------------------
    # Hauptfarben
    # -------------------------------------------------

    BACKGROUND = tokens.SURFACE["base"]

    SURFACE = tokens.SURFACE["card"]
    SURFACE_ALT = tokens.SURFACE["sunken"]
    SURFACE_LIGHT = tokens.SURFACE["raised"]

    CARD = tokens.SURFACE["card"]
    CARD_HOVER = tokens.SURFACE["raised"]

    SIDEBAR = tokens.SURFACE["sunken"]
    SIDEBAR_HOVER = tokens.SURFACE["raised"]

    # -------------------------------------------------
    # Rahmen
    # -------------------------------------------------

    BORDER = tokens.BORDER["base"]
    BORDER_LIGHT = tokens.BORDER["strong"]

    #
    # Frueher ein eigener violetter Rahmenton. Karten haben seit 2.0
    # ueberhaupt keinen umlaufenden Rahmen mehr, sondern eine
    # 1-px-Oberkante; die Akzentkarte bekommt sie in Akzentfarbe.
    #

    BORDER_ACCENT = tokens.tint(_ACCENT["base"], tokens.TINT_BORDER)

    # -------------------------------------------------
    # Akzent
    # -------------------------------------------------
    #
    # PRIMARY war bis 1.7 der Violett-Indigo-Verlauf. Seit 2.0 gilt
    # "Bernstein traegt die Bedeutung, Violett nur das Licht": der
    # Hauptakzent ist die gewaehlte Akzentvariante, das Violett bleibt
    # als SHEEN uebrig und ist reines Flaechenlicht.
    #

    PRIMARY = _ACCENT["base"]
    PRIMARY_2 = _ACCENT["light"]
    PRIMARY_HOVER = _ACCENT["light"]
    PRIMARY_PRESSED = tokens.ACCENT_PRESSED[tokens.ACCENT_DEFAULT]

    SHEEN = tokens.SHEEN_VIOLET[0]
    SHEEN_2 = tokens.SHEEN_VIOLET[1]

    GOLD = tokens.ACCENTS["amber"]["base"]
    GOLD_LIGHT = tokens.ACCENTS["amber"]["light"]
    GOLD_HOVER = tokens.ACCENTS["amber"]["light"]

    DISCORD = tokens.STATE["info"]

    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    SUCCESS = tokens.STATE["ok"]
    SUCCESS_LIGHT = tokens.STATE_TEXT["ok"]

    WARNING = tokens.STATE["warn"]
    WARNING_LIGHT = tokens.STATE_TEXT["warn"]

    ERROR = tokens.STATE["error"]
    ERROR_LIGHT = tokens.STATE_TEXT["error"]

    INFO = tokens.STATE["info"]
    INFO_LIGHT = tokens.STATE_TEXT["info"]

    # -------------------------------------------------
    # Texte
    # -------------------------------------------------

    TEXT = tokens.TEXT["primary"]
    TEXT_SECONDARY = tokens.TEXT["secondary"]
    TEXT_MUTED = tokens.TEXT["muted"]
    TEXT_FAINT = tokens.TEXT["faint"]
    TEXT_ON_ACCENT = tokens.TEXT["onAccent"]

    # -------------------------------------------------
    # Transparenzen
    # -------------------------------------------------

    OVERLAY = "rgba(0,0,0,0.430)"
    OVERLAY_LIGHT = "rgba(255,255,255,0.047)"
    OVERLAY_BORDER = "rgba(255,255,255,0.094)"

    #
    # Die 1-px-Oberkante, die seit 2.0 den Schatten ersetzt.
    #

    EDGE_TOP = tokens.EDGE_TOP

    # -------------------------------------------------
    # Sonstiges
    # -------------------------------------------------

    WHITE = tokens.WHITE
    BLACK = tokens.BLACK

    TRANSPARENT = "transparent"
