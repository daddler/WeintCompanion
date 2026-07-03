"""
WeintCompanion Theme
Farben
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:

    # -------------------------------------------------
    # Hauptfarben
    # -------------------------------------------------

    BACKGROUND = "#16171D"

    SURFACE = "#1E2028"
    SURFACE_ALT = "#23262F"
    SURFACE_LIGHT = "#2A2E39"

    CARD = "#252833"
    CARD_HOVER = "#2B2F3C"

    SIDEBAR = "#14151B"
    SIDEBAR_HOVER = "#232733"

    # -------------------------------------------------
    # Rahmen
    # -------------------------------------------------

    BORDER = "#363A47"
    BORDER_LIGHT = "#464B5A"
    BORDER_GOLD = "#6E5A2B"

    # -------------------------------------------------
    # Akzentfarben
    # -------------------------------------------------

    PRIMARY = "#8B5CF6"
    PRIMARY_HOVER = "#9D71FF"
    PRIMARY_PRESSED = "#7247E8"

    GOLD = "#D9B347"
    GOLD_LIGHT = "#E8C96D"
    GOLD_HOVER = "#E8C460"

    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    SUCCESS = "#6EDC74"
    SUCCESS_LIGHT = "#7DDB9E"

    WARNING = "#F1B84B"
    WARNING_LIGHT = "#E8C96D"

    ERROR = "#EB5A5A"
    ERROR_LIGHT = "#F18C8C"

    INFO = "#53A8FF"
    INFO_LIGHT = "#8DBFFF"

    # -------------------------------------------------
    # Texte
    # -------------------------------------------------

    TEXT = "#F6F7FA"
    TEXT_SECONDARY = "#B3B8C6"
    TEXT_MUTED = "#868B98"

    # -------------------------------------------------
    # Transparenzen
    # -------------------------------------------------

    OVERLAY = "rgba(0,0,0,110)"
    OVERLAY_LIGHT = "rgba(255,255,255,12)"
    OVERLAY_BORDER = "rgba(255,255,255,24)"

    # -------------------------------------------------
    # Sonstiges
    # -------------------------------------------------

    WHITE = "#FFFFFF"
    BLACK = "#000000"

    TRANSPARENT = "transparent"