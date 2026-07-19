"""
WeintCompanion Theme
Typografie
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Typography:

    FONT = "Inter"

    MONO_FONT = "JetBrains Mono"

    #
    # Titel
    #

    HERO_TITLE = 28

    PAGE_TITLE = 28

    SECTION_TITLE = 18

    CARD_TITLE = 15

    #
    # Texte
    #

    BODY = 14

    SMALL = 13

    CAPTION = 12

    MICRO = 11

    TINY = 10

    #
    # Gewicht
    #

    LIGHT = 300

    NORMAL = 400

    SEMIBOLD = 600

    BOLD = 700

    HEAVY = 800
