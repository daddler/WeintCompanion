"""
WeintCompanion Theme
Typografie
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Typography:

    FONT = "Segoe UI"

    #
    # Titel
    #

    HERO_TITLE = 34

    PAGE_TITLE = 28

    SECTION_TITLE = 22

    CARD_TITLE = 17

    #
    # Texte
    #

    BODY = 14

    SMALL = 13

    CAPTION = 12

    #
    # Gewicht
    #

    LIGHT = 300

    NORMAL = 400

    SEMIBOLD = 600

    BOLD = 700