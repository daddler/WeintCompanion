"""
WeintCompanion 2.0
Design-Tokens

Die einzige Stelle im Programm, an der ein Farbwert steht.

Der Entwurf zu 2.0 beschreibt jede Fläche, jeden Abstand und jede
Schrift über einen Namen; dieser Name ist hier definiert und wird
danach ausschließlich als Name verwendet - im Stylesheet ebenso wie in
den gemalten Widgets. Vor 2.0 lagen dieselben Werte in `colors.py`,
`metrics.py`, `typography.py`, in `styles_old.py` und zusätzlich als
Literale in einzelnen Widgets. Ein Akzentwechsel zur Laufzeit war
dadurch nicht möglich, denn niemand wusste, wo überall Bernstein steht.

Dieses Modul importiert bewusst **kein Qt**. Es ist reine Datenhaltung
und damit ohne laufende Oberfläche testbar - dieselbe Trennung, die
`analyzer/` von der GUI freihält. Alles, was eine QFont, eine QColor
oder einen QPainter braucht, steht in `fonts.py`, `icons.py` oder im
Widget selbst.

Leitidee des Entwurfs, an der sich die Aufteilung hier ablesen lässt:

    Bernstein trägt die Bedeutung, Violett nur das Licht.

Deshalb sind `ACCENTS` (wählbar, bedeutungstragend) und `SHEEN_VIOLET`
(reines Flächenlicht) zwei getrennte Begriffe und nicht zwei Einträge
derselben Tabelle.
"""

from __future__ import annotations

from dataclasses import dataclass


# ==========================================================
# Flächen, Rahmen, Text
# ==========================================================

#
# Höhe entsteht in diesem Entwurf nicht durch Rahmen und nicht durch
# Schatten, sondern durch Schichtung: eine Fläche steht über der
# nächsten, weil sie heller ist und eine 1 px helle Oberkante trägt.
# Die Reihenfolge base < card < raised ist deshalb keine Willkür,
# sondern die Staffelung selbst - `sunken` liegt unter `base`.
#

SURFACE = {
    "base": "#0A0A0C",      # Fenstergrund, Inhaltsfläche
    "card": "#0F0F12",      # Karte, Kachel
    "sunken": "#08080A",    # Navigationsspalte, Titelleiste, Balkenrinne
    "raised": "#17171C",    # Hover, aktiver Navigationseintrag, Sekundärknopf
}

BORDER = {
    "base": "#1E1E24",
    "strong": "#2A2A34",
}

#
# Die 1-px-Oberkante jeder Karte. Sie ersetzt den Schatten und wird als
# linearer Verlauf von oben gemalt, nicht als Rahmen: ein umlaufender
# Rahmen ist genau das, was der Entwurf vermeiden will.
#

EDGE_TOP = "rgba(255,255,255,0.06)"

#
# Die Kartenfläche selbst ist ein senkrechter Verlauf (oben heller).
# Auch das ersetzt den Schatten - eine gleichmäßig gefüllte Karte wirkt
# flach, sobald ihr der Rahmen fehlt.
#

CARD_GRADIENT = ("#121217", "#0C0C0F")

#
# Variante `accent` derselben Karte (Entwurf §5): nur für die eine
# Karte pro Ansicht, die eine Handlung trägt.
#

CARD_GRADIENT_ACCENT = ("#17141A", "#0D0C10")

TEXT = {
    "primary": "#E8E8EA",
    "secondary": "#A8A8B0",
    "muted": "#6B6B74",
    "faint": "#4A4A52",
    "onAccent": "#0A0A0C",   # Text auf bernsteinfarbenem Knopf
}

WHITE = "#FFFFFF"

BLACK = "#000000"

#
# Einzelne Flaechen, die zwischen den Stufen von SURFACE liegen. Sie
# stehen hier und nicht im jeweiligen Widget, weil sonst genau das
# entstuende, was das Abnahmekriterium verbietet: ein Farbwert
# ausserhalb dieser Datei - und damit eine Flaeche, die bei einer
# Aenderung der Palette uebersehen wird.
#

SURFACE_EXTRA = {
    #
    # Die Systemzeile der Uebersicht: eine Spur unter der Karte, damit
    # sie sich als Fuss und nicht als weitere Karte liest.
    #
    "row": "#0C0C0F",

    #
    # Oberkante des Titelleistenverlaufs (nach `sunken` hin).
    #
    "titleBar": "#0C0C10",

    #
    # Flaeche eines Meldungsstreifens - identisch mit der Oberkante
    # des Kartenverlaufs, damit ein Toast wie eine angehobene Karte
    # wirkt.
    #
    "toast": "#121217",

    #
    # Der helle Punkt im Schimmer eines Skeletts.
    #
    "shimmer": "#1B1B21",

    #
    # Mitte des radialen Verlaufs im Startbildschirm - die einzige
    # Flaeche, die einen Hauch des Violetts als Grundton traegt.
    #
    "splash": "#12101A",
}


# ==========================================================
# Akzent
# ==========================================================

#
# Drei wählbare Varianten. Der Akzent färbt **ausschließlich**: aktiven
# Navigationsindikator und -symbol, Hauptknopf, Fortschrittsbalken und
# -ring, Sterne, Rubriklabel im Handlungskontext, Countdown-Chip und
# Fokusrahmen. Alles andere bleibt neutral - sonst wird aus einem
# Akzent eine zweite Grundfarbe.
#
# `onBase` ist die Textfarbe **auf** der Akzentfläche und gehört
# deshalb zur Variante, nicht zu TEXT: Jade ist dunkler als Bernstein
# und verlangt einen anderen Wert.
#

ACCENTS = {
    "amber": {"base": "#D4A24A", "light": "#E8C96D", "onBase": "#0A0A0C"},
    "arcane": {"base": "#A855F7", "light": "#C084FC", "onBase": "#0A0A0C"},
    "jade": {"base": "#3ABE96", "light": "#6FD9B6", "onBase": "#04120E"},
}

ACCENT_DEFAULT = "amber"

#
# Knopfverläufe je Zustand, abgeleitet aus der Akzentvariante. Der
# Entwurf nennt sie für Bernstein ausdrücklich (§5); für die beiden
# anderen Varianten entstehen sie nach derselben Regel: Ruhe geht von
# `light` nach `base`, Überfahren liegt eine Spur heller, Gedrückt ist
# flach und dunkler.
#

ACCENT_PRESSED = {
    "amber": "#B8862F",
    "arcane": "#7E22CE",
    "jade": "#2A9A78",
}

ACCENT_HOVER = {
    "amber": ("#F2D888", "#DFAE58"),
    "arcane": ("#D0A0FF", "#B466F8"),
    "jade": ("#8CE6C9", "#4ACCA4"),
}

#
# Violett-Indigo, **nur** als Flächenlicht: Titelleistenlicht,
# Markenplakette, Diagrammlinie "Vergleich". Nie Statusfarbe, nie
# Hauptknopf - außer der Nutzer wählt oben "arcane", dann kommt das
# Violett über ACCENTS und nicht über diesen Wert.
#

SHEEN_VIOLET = ("#A855F7", "#6366F1")


def accent(name: str | None = None) -> dict:
    """
    Die Akzentvariante zu `name`, mit Rückfall auf die Voreinstellung.

    Ein unbekannter Name darf die Oberfläche nicht farblos lassen -
    er kann aus einer von Hand bearbeiteten `config.json` stammen.
    """

    return ACCENTS.get(name or "", ACCENTS[ACCENT_DEFAULT])


# ==========================================================
# Bedeutungsfarben
# ==========================================================

#
# In allen drei Akzenten identisch. Das ist der Punkt: der Akzent ist
# Geschmack, die Bedeutung ist es nicht. Wer Jade wählt, soll einen
# Fehler weiterhin an Rot erkennen.
#
# `empty` ist absichtlich None - ein leerer Statuspunkt wird nicht
# gefüllt, sondern nur als 1-px-Kontur gezeichnet. Ein grauer Punkt
# sähe aus wie ein Zustand, "keine Angabe" ist aber keiner.
#

STATE = {
    "ok": "#7CC06E",
    "warn": "#D4A24A",
    "error": "#E56B6B",
    "live": "#E56B6B",     # pulsierend
    "info": "#8B95F5",
    "empty": None,
}

STATE_EMPTY_OUTLINE = "#4A4A52"

#
# Textfarbe auf getönter Fläche. Die Grundfarbe aus STATE ist als
# Schrift auf dunklem Grund zu dunkel; diese Werte sind die aufgehellte
# Entsprechung.
#

STATE_TEXT = {
    "ok": "#8FDA80",
    "warn": "#E8C96D",
    "error": "#F18C8C",
    "info": "#A8B0FF",
}

#
# Getönte Chip-Flächen (§2.3): Grundfarbe mit 12-14 % Deckkraft,
# 1-px-Rahmen mit 34-42 % derselben Farbe. Als Konstanten, damit nicht
# jedes Widget seinen eigenen Wert in diesem Korridor wählt.
#

TINT_SURFACE = 0.13
TINT_BORDER = 0.38


# ==========================================================
# Raum und Radius
# ==========================================================

#
# space.1 ... space.7 - im Code als SPACE[0] ... SPACE[6].
#

SPACE = [4, 8, 12, 16, 24, 32, 48]

RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
    "xl": 20,
    "pill": 999,
}


# ==========================================================
# Dichte
# ==========================================================

#
# Gilt global (eine Einstellung), nicht pro Ansicht: zwei Ansichten mit
# unterschiedlicher Zeilenhöhe nebeneinander lesen sich wie zwei
# Programme.
#
# `font_delta` verschiebt jede Schriftgröße um diesen Betrag. Deshalb
# steht er hier und nicht in TYPE - die Schriftgrößen sind absolut, die
# Dichte verschiebt sie.
#

DENSITY = {
    "comfortable": {
        "row": 24,
        "pad_v": 16,
        "pad_h": 20,
        "gap": 20,
        "btn": 40,
        "btn_sm": 34,
        "nav_item": 40,
        "title_bar": 40,
        "font_delta": 0,
    },
    "compact": {
        "row": 20,
        "pad_v": 12,
        "pad_h": 16,
        "gap": 14,
        "btn": 34,
        "btn_sm": 30,
        "nav_item": 34,
        "title_bar": 36,
        "font_delta": -1,
    },
}

DENSITY_DEFAULT = "comfortable"


def density(name: str | None = None) -> dict:
    """
    Die Dichte zu `name`, mit Rückfall auf die Voreinstellung.
    """

    return DENSITY.get(name or "", DENSITY[DENSITY_DEFAULT])


# ==========================================================
# Typografie
# ==========================================================

FAMILY_SANS = "Inter"

FAMILY_MONO = "JetBrains Mono"


@dataclass(frozen=True)
class TypeToken:
    """
    Eine benannte Schriftrolle.

    `letter_spacing` ist in em angegeben, wie im Entwurf. Qt kennt
    `letter-spacing` im Stylesheet **nicht** und verwirft die Angabe
    wortlos - die Umrechnung in Pixel und das Setzen über
    `QFont.setLetterSpacing` passieren deshalb in `fonts.py`.
    """

    family: str

    size: int

    weight: int

    letter_spacing: float = 0.0

    uppercase: bool = False


TYPE = {
    "title": TypeToken(FAMILY_SANS, 28, 700, -0.02),
    "section": TypeToken(FAMILY_SANS, 18, 600),
    "card": TypeToken(FAMILY_SANS, 15, 600),
    "body": TypeToken(FAMILY_SANS, 14, 400),
    "small": TypeToken(FAMILY_SANS, 13, 400),
    "mono": TypeToken(FAMILY_MONO, 12, 700),
    "monoBig": TypeToken(FAMILY_MONO, 36, 700),
    "eyebrow": TypeToken(FAMILY_MONO, 11, 400, 0.18, uppercase=True),
    "micro": TypeToken(FAMILY_MONO, 10, 400, 0.16, uppercase=True),
}

#
# Gewichte als Namen, damit Widgetcode keine nackten Zahlen setzt.
#

WEIGHT = {
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
}


# ==========================================================
# Fenster
# ==========================================================

#
# Entwurfsgröße 1440 x 900, geprüft 1120 x 720, Minimum 960 x 640.
# Vor 2.0 stand das Minimum auf 1500 x 900 - auf einem 1366er
# Bildschirm ließ sich das Fenster damit nicht vollständig anzeigen.
#

WINDOW_DEFAULT = (1440, 900)

WINDOW_MIN = (960, 640)

NAV_WIDTH_EXPANDED = 232

NAV_WIDTH_COLLAPSED = 72

#
# Haltepunkte (§4). Die Hysterese verhindert, dass ein Fenster, das
# genau auf der Kante steht, bei jedem Pixel Mausbewegung hin- und
# herschaltet.
#

BREAKPOINT_DRAWER = 1280

BREAKPOINT_NAV = 1120

BREAKPOINT_SINGLE_COLUMN = 980

BREAKPOINT_HYSTERESIS = 40


# ==========================================================
# Hilfsfunktionen
# ==========================================================

def rgb(value: str) -> tuple[int, int, int]:
    """
    "#RRGGBB" -> (r, g, b).
    """

    value = value.lstrip("#")

    if len(value) == 3:
        value = "".join(c * 2 for c in value)

    if len(value) != 6:
        raise ValueError(f"Kein sechsstelliger Hex-Wert: {value!r}")

    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def tint(value: str, alpha: float) -> str:
    """
    Eine Farbe mit Deckkraft, als `rgba(...)` für Qt-Stylesheets.

    Die eine Stelle, an der aus einem Hex-Wert eine transparente Farbe
    wird. Ohne sie stünde in jedem Widget, das eine getönte Chip-Fläche
    braucht, eine eigene handgeschriebene rgba-Zeichenkette - und damit
    wieder ein Farbwert außerhalb dieser Datei.
    """

    red, green, blue = rgb(value)

    return f"rgba({red},{green},{blue},{alpha:.3f})"


def mix(foreground: str, background: str, amount: float) -> str:
    """
    Zwei Farben mischen, `amount` ist der Anteil von `foreground`.

    Gebraucht, wo eine transparente Farbe nicht reicht, weil das
    Ergebnis gemalt und nicht überlagert wird (Sparkline auf Karte,
    Balkenfüllung in der Rinne).
    """

    a = rgb(foreground)
    b = rgb(background)

    amount = max(0.0, min(1.0, amount))

    parts = [
        round(a[i] * amount + b[i] * (1.0 - amount))
        for i in range(3)
    ]

    return "#%02X%02X%02X" % tuple(parts)
