"""
WeintCompanion Theme
Typografie

**Uebergangsmodul** wie `colors.py` und `metrics.py`: die Namen
bleiben, die Werte kommen aus `gui/theme/tokens.py`.

Was hier fehlt und auch nicht nachgereicht werden kann, ist die
**Laufweite**. Der Entwurf sperrt die kleinen Rubriklabels weit
(0.18em bzw. 0.16em) - Qt kennt `letter-spacing` im Stylesheet aber
nicht und verwirft die Angabe wortlos. Bis 1.7 stand sie trotzdem in
`gui/widgets/eyebrow.py` und hat nie gewirkt. Richtig gesetzt wird sie
seit 2.0 ueber `QFont.setLetterSpacing`, siehe `gui/theme/fonts.py`.

Neuer Code nimmt deshalb `fonts.font("eyebrow")` statt Groesse und
Familie einzeln.
"""

from dataclasses import dataclass

from gui.theme import tokens


@dataclass(frozen=True)
class Typography:

    FONT = tokens.FAMILY_SANS

    MONO_FONT = tokens.FAMILY_MONO

    #
    # Titel
    #

    HERO_TITLE = tokens.TYPE["title"].size

    PAGE_TITLE = tokens.TYPE["title"].size

    SECTION_TITLE = tokens.TYPE["section"].size

    CARD_TITLE = tokens.TYPE["card"].size

    #
    # Texte
    #

    BODY = tokens.TYPE["body"].size

    SMALL = tokens.TYPE["small"].size

    CAPTION = tokens.TYPE["mono"].size

    MICRO = tokens.TYPE["eyebrow"].size

    TINY = tokens.TYPE["micro"].size

    #
    # Werte und Zeiten
    #

    MONO = tokens.TYPE["mono"].size

    MONO_BIG = tokens.TYPE["monoBig"].size

    #
    # Gewicht
    #

    LIGHT = 300

    NORMAL = tokens.WEIGHT["normal"]

    MEDIUM = tokens.WEIGHT["medium"]

    SEMIBOLD = tokens.WEIGHT["semibold"]

    BOLD = tokens.WEIGHT["bold"]

    HEAVY = 800
