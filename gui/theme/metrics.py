"""
WeintCompanion Theme
Abstände / Größen
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:

    # -------------------------------------------------
    # Fenster
    # -------------------------------------------------

    WINDOW_MIN_WIDTH = 1500
    WINDOW_MIN_HEIGHT = 900

    # -------------------------------------------------
    # Rail-Sidebar
    # -------------------------------------------------

    RAIL_WIDTH = 72

    SETTINGS_NAV_WIDTH = 220

    ACTIVITY_PANEL_WIDTH = 360

    # -------------------------------------------------
    # Rundungen
    # -------------------------------------------------

    RADIUS_SMALL = 8

    RADIUS_MEDIUM = 10

    RADIUS_LARGE = 12

    RADIUS_CARD = 12

    RADIUS_PANEL = 12

    RADIUS_PILL = 999

    # -------------------------------------------------
    # Seitenlayout
    # -------------------------------------------------

    PAGE_MARGIN = 32

    PAGE_SPACING = 24

    SECTION_SPACING = 20

    CARD_SPACING = 14

    INNER_PADDING = 20

    # -------------------------------------------------
    # Cards
    # -------------------------------------------------

    STATUS_CARD_HEIGHT = 150

    CARD_ICON_SIZE = 32

    CARD_VALUE_SIZE = 22

    CARD_BADGE_HEIGHT = 22

    # -------------------------------------------------
    # Navigation
    # -------------------------------------------------

    RAIL_ITEM_SIZE = 44

    NAV_ITEM_HEIGHT = 40

    LOGO_SIZE = 40

    # -------------------------------------------------
    # Buttons
    # -------------------------------------------------

    BUTTON_HEIGHT = 40

    BUTTON_RADIUS = 8

    # -------------------------------------------------
    # LogWidget
    # -------------------------------------------------

    LOG_HEADER_HEIGHT = 34

    LOG_ITEM_HEIGHT = 30

    # -------------------------------------------------
    # TopBar
    # -------------------------------------------------

    TOPBAR_HEIGHT = 56

    # -------------------------------------------------
    # Schatten
    # -------------------------------------------------

    SHADOW_BLUR = 30

    SHADOW_OFFSET = 12
