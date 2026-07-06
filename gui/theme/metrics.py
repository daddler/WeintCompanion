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
    WINDOW_MIN_HEIGHT = 860

    SIDEBAR_WIDTH = 305

    # -------------------------------------------------
    # Rundungen
    # -------------------------------------------------

    RADIUS_SMALL = 8
    RADIUS_MEDIUM = 14
    RADIUS_LARGE = 20

    RADIUS_CARD = 20
    RADIUS_PANEL = 20
    RADIUS_HERO = 24
    RADIUS_SIDEBAR = 26

    # -------------------------------------------------
    # Seitenlayout
    # -------------------------------------------------

    PAGE_MARGIN = 32

    PAGE_SPACING = 24

    SECTION_SPACING = 26

    CARD_SPACING = 20

    INNER_PADDING = 22

    # -------------------------------------------------
    # Hero
    # -------------------------------------------------

    HERO_HEIGHT = 560

    HERO_BUTTON_HEIGHT = 46

    HERO_IMAGE_WIDTH = 430

    HERO_IMAGE_HEIGHT = 300

    # -------------------------------------------------
    # Cards
    # -------------------------------------------------

    STATUS_CARD_HEIGHT = 175

    CARD_ICON_SIZE = 58

    CARD_VALUE_SIZE = 30

    CARD_BADGE_HEIGHT = 28

    # -------------------------------------------------
    # Navigation
    # -------------------------------------------------

    NAV_ITEM_HEIGHT = 60

    LOGO_SIZE = 118

    STATUS_BOX_HEIGHT = 145

    # -------------------------------------------------
    # Buttons
    # -------------------------------------------------

    BUTTON_HEIGHT = 46

    BUTTON_RADIUS = 14

    # -------------------------------------------------
    # LogWidget
    # -------------------------------------------------

    LOG_HEADER_HEIGHT = 34

    LOG_ITEM_HEIGHT = 38

    # -------------------------------------------------
    # TopBar
    # -------------------------------------------------

    TOPBAR_HEIGHT = 68

    # -------------------------------------------------
    # Schatten
    # -------------------------------------------------

    SHADOW_BLUR = 28

    SHADOW_OFFSET = 10