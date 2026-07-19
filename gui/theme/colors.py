"""
WeintCompanion Theme
Farben

Command-Deck-Palette (dunkles Purple/Indigo-Theme, siehe Claude-Design-
Projekt "WoW MoP Companion App Design" -> "WeintCompanion 1b.dc.html").
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:

    # -------------------------------------------------
    # Hauptfarben
    # -------------------------------------------------

    BACKGROUND = "#0A0A0C"

    SURFACE = "#0F0F12"
    SURFACE_ALT = "#08080A"
    SURFACE_LIGHT = "#17171C"

    CARD = "#0F0F12"
    CARD_HOVER = "#17171C"

    SIDEBAR = "#08080A"
    SIDEBAR_HOVER = "#17171C"

    # -------------------------------------------------
    # Rahmen
    # -------------------------------------------------

    BORDER = "#1E1E24"
    BORDER_LIGHT = "#2A2A34"
    BORDER_ACCENT = "#2A1E3D"

    # -------------------------------------------------
    # Akzentfarben (Gradient Lila -> Indigo)
    # -------------------------------------------------

    PRIMARY = "#A855F7"
    PRIMARY_2 = "#6366F1"
    PRIMARY_HOVER = "#C084FC"
    PRIMARY_PRESSED = "#9333EA"

    GOLD = "#D4A24A"
    GOLD_LIGHT = "#E8C96D"
    GOLD_HOVER = "#E8C460"

    DISCORD = "#8B95F5"

    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    SUCCESS = "#7CC06E"
    SUCCESS_LIGHT = "#8FDA80"

    WARNING = "#D4A24A"
    WARNING_LIGHT = "#E8C96D"

    ERROR = "#E56B6B"
    ERROR_LIGHT = "#F18C8C"

    INFO = "#8B95F5"
    INFO_LIGHT = "#A8B0FF"

    # -------------------------------------------------
    # Texte
    # -------------------------------------------------

    TEXT = "#E8E8EA"
    TEXT_SECONDARY = "#A8A8B0"
    TEXT_MUTED = "#6B6B74"
    TEXT_FAINT = "#4A4A52"

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
