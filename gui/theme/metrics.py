"""
WeintCompanion Theme
Abstaende / Groessen

**Uebergangsmodul**, aus demselben Grund wie `colors.py`: die Namen
bleiben, die Werte kommen seit 2.0 aus `gui/theme/tokens.py`.

Was dieses Modul grundsaetzlich nicht leisten kann, ist die **Dichte**.
`Metrics.*` sind Klassenattribute und stehen beim Import fest; die
Umschaltung zwischen "komfortabel" und "kompakt" aendert aber genau
diese Zahlen. Wer eine dichteabhaengige Groesse braucht, fragt deshalb
`theme().metric("row")` statt `Metrics.LOG_ITEM_HEIGHT`. Die Werte hier
sind die der Voreinstellung.
"""

from dataclasses import dataclass

from gui.theme import tokens


@dataclass(frozen=True)
class Metrics:

    # -------------------------------------------------
    # Fenster
    # -------------------------------------------------
    #
    # Bis 1.7 stand das Minimum auf 1500 x 900. Das war keine
    # Gestaltungsentscheidung, sondern ein Ausweg: das Dashboard
    # brauchte diese Hoehe, um ohne Scrollen zu passen. Auf einem
    # 1366-px-Bildschirm liess sich das Fenster dadurch nicht
    # vollstaendig anzeigen. 2.0 loest das ueber Haltepunkte statt
    # ueber ein grosses Minimum.
    #

    WINDOW_DEFAULT_WIDTH = tokens.WINDOW_DEFAULT[0]
    WINDOW_DEFAULT_HEIGHT = tokens.WINDOW_DEFAULT[1]

    WINDOW_MIN_WIDTH = tokens.WINDOW_MIN[0]
    WINDOW_MIN_HEIGHT = tokens.WINDOW_MIN[1]

    # -------------------------------------------------
    # Navigationsspalte
    # -------------------------------------------------

    NAV_WIDTH = tokens.NAV_WIDTH_EXPANDED

    RAIL_WIDTH = tokens.NAV_WIDTH_COLLAPSED

    SETTINGS_NAV_WIDTH = 220

    ACTIVITY_PANEL_WIDTH = 360

    DRAWER_WIDTH = 320

    DRAWER_HANDLE = 44

    # -------------------------------------------------
    # Rundungen
    # -------------------------------------------------

    RADIUS_SMALL = tokens.RADIUS["sm"]

    RADIUS_MEDIUM = tokens.RADIUS["md"]

    RADIUS_LARGE = tokens.RADIUS["lg"]

    RADIUS_CARD = tokens.RADIUS["lg"]

    RADIUS_PANEL = tokens.RADIUS["lg"]

    RADIUS_XL = tokens.RADIUS["xl"]

    RADIUS_PILL = tokens.RADIUS["pill"]

    # -------------------------------------------------
    # Raumskala
    # -------------------------------------------------
    #
    # space.1 ... space.7 aus dem Entwurf, zusaetzlich unter ihren
    # bisherigen Namen.
    #

    SPACE_1 = tokens.SPACE[0]
    SPACE_2 = tokens.SPACE[1]
    SPACE_3 = tokens.SPACE[2]
    SPACE_4 = tokens.SPACE[3]
    SPACE_5 = tokens.SPACE[4]
    SPACE_6 = tokens.SPACE[5]
    SPACE_7 = tokens.SPACE[6]

    # -------------------------------------------------
    # Seitenlayout
    # -------------------------------------------------

    PAGE_MARGIN = tokens.SPACE[5]          # 32, seitlich

    PAGE_MARGIN_TOP = tokens.SPACE[4]      # 24, oben

    PAGE_SPACING = tokens.SPACE[4]

    SECTION_SPACING = 20

    CARD_SPACING = tokens.SPACE[2]

    INNER_PADDING = 20

    # -------------------------------------------------
    # Karten
    # -------------------------------------------------

    STATUS_CARD_HEIGHT = 150

    CARD_ICON_SIZE = 32

    CARD_VALUE_SIZE = 22

    CARD_BADGE_HEIGHT = 22

    # -------------------------------------------------
    # Navigation
    # -------------------------------------------------

    RAIL_ITEM_SIZE = 44

    NAV_ITEM_HEIGHT = tokens.DENSITY["comfortable"]["nav_item"]

    NAV_ICON_SIZE = 18

    #
    # Der gemalte Indikator links am aktiven Eintrag - ausserhalb der
    # Flaeche, damit er nicht wie ein Rahmen wirkt.
    #

    NAV_INDICATOR_WIDTH = 3

    NAV_INDICATOR_HEIGHT = 22

    LOGO_SIZE = 40

    # -------------------------------------------------
    # Titelleiste
    # -------------------------------------------------

    TITLE_BAR_HEIGHT = tokens.DENSITY["comfortable"]["title_bar"]

    TITLE_BRAND_SIZE = 22

    WINDOW_BUTTON_WIDTH = 28

    WINDOW_BUTTON_HEIGHT = 24

    #
    # Breite der Zonen an den Fensterkanten, in denen der Zeiger die
    # Groesse aendert. 6 px sind schmal genug, um nicht mit Inhalt zu
    # kollidieren, und breit genug, um sie zu treffen.
    #

    RESIZE_MARGIN = 6

    # -------------------------------------------------
    # Knoepfe
    # -------------------------------------------------

    BUTTON_HEIGHT = tokens.DENSITY["comfortable"]["btn"]

    BUTTON_HEIGHT_SMALL = tokens.DENSITY["comfortable"]["btn_sm"]

    BUTTON_RADIUS = tokens.RADIUS["sm"]

    # -------------------------------------------------
    # Zeilen und Tabellen
    # -------------------------------------------------

    ROW_HEIGHT = tokens.DENSITY["comfortable"]["row"]

    ROW_GAP = 2

    LOG_HEADER_HEIGHT = 34

    LOG_ITEM_HEIGHT = 30

    # -------------------------------------------------
    # Altlasten
    # -------------------------------------------------
    #
    # TOPBAR gab es bis 1.7 als eigene Leiste ueber dem Inhalt. Seit
    # 2.0 traegt die Titelleiste diese Rolle mit. Der Name bleibt, bis
    # die letzte Seite umgestellt ist.
    #

    TOPBAR_HEIGHT = 56

    #
    # Schatten sind in diesem Entwurf ausdruecklich kein Mittel mehr:
    # Hoehe entsteht ueber Flaechenhelligkeit und die 1-px-Oberkante.
    # Die Werte bleiben nur stehen, damit bestehender Code laeuft.
    #

    SHADOW_BLUR = 30

    SHADOW_OFFSET = 12
