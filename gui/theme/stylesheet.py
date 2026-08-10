"""
WeintCompanion 2.0
Globales Stylesheet

Bis 1.7 war das eine Modulkonstante: ein f-String, der beim Import
ausgerechnet und in `app.py` einmalig gesetzt wurde. Damit war jede
Farbe fuer die Laufzeit des Programms festgelegt - ein Akzentwechsel
haette einen Neustart gebraucht.

Seit 2.0 ist es eine Funktion ueber dem `ThemeManager`. `set_accent()`
und `set_density()` rufen sie erneut auf und setzen das Ergebnis; alles,
was ueber Qt-Stylesheets gestaltet ist, folgt dadurch sofort. Gemalte
Widgets (Ring, Sparkline, Sterne, Balken) erreicht das **nicht** - sie
lesen ihre Farbe in `paintEvent` und werden ueber `accent_changed`
neu gezeichnet.

Was hier bewusst **nicht** steht: die Karten. Eine Karte traegt seit
2.0 einen senkrechten Verlauf und eine 1-px-Oberkante statt eines
umlaufenden Rahmens; beides ist widget-eigen (siehe
`gui/widgets/card.py`), weil ein globales `QFrame`-Regelwerk jede
beliebige Flaeche im Programm mitgestalten wuerde.
"""

from __future__ import annotations

from gui.theme import tokens


def build_stylesheet(theme) -> str:
    """
    Das globale Stylesheet fuer den uebergebenen Themezustand.
    """

    accent = theme.accent()

    accent_base = accent["base"]
    accent_light = accent["light"]
    accent_on = accent["onBase"]

    accent_pressed = theme.accent_pressed()
    hover_light, hover_base = theme.accent_hover()

    surface = tokens.SURFACE
    border = tokens.BORDER
    text = tokens.TEXT

    radius_sm = tokens.RADIUS["sm"]
    radius_md = tokens.RADIUS["md"]

    btn_height = theme.metric("btn", 40)
    btn_small = theme.metric("btn_sm", 34)

    body = theme.font_size(tokens.TYPE["body"].size)
    small = theme.font_size(tokens.TYPE["small"].size)
    section = theme.font_size(tokens.TYPE["section"].size)
    card_title = theme.font_size(tokens.TYPE["card"].size)
    title = theme.font_size(tokens.TYPE["title"].size)
    mono = theme.font_size(tokens.TYPE["mono"].size)
    eyebrow = theme.font_size(tokens.TYPE["eyebrow"].size)

    sans = tokens.FAMILY_SANS
    mono_family = tokens.FAMILY_MONO

    #
    # Der Fokusrahmen ist eine der wenigen Stellen, an denen der Akzent
    # eine Bedeutung traegt (§2.2) - deshalb Akzent und nicht
    # border.strong.
    #

    focus_border = accent_base

    return f"""

/* ==========================================================
   GLOBAL
========================================================== */

QMainWindow {{
    background: {surface["base"]};
}}

QWidget {{
    background: transparent;
    color: {text["primary"]};

    font-family: "{sans}";
    font-size: {body}px;
}}

QToolTip {{

    background:{surface["sunken"]};

    color:{text["primary"]};

    border:1px solid {border["strong"]};

    border-radius:{radius_sm}px;

    padding:6px 10px;
}}

/* ==========================================================
   SCROLLBAR
========================================================== */

QScrollBar:vertical {{
    background:transparent;
    width:10px;
    margin:0px;
}}

QScrollBar::handle:vertical {{
    background:{border["strong"]};
    border-radius:5px;
    min-height:24px;
}}

QScrollBar::handle:vertical:hover {{
    background:{text["muted"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height:0px;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background:transparent;
}}

QScrollBar:horizontal {{
    background:transparent;
    height:10px;
    margin:0px;
}}

QScrollBar::handle:horizontal {{
    background:{border["strong"]};
    border-radius:5px;
    min-width:24px;
}}

QScrollBar::handle:horizontal:hover {{
    background:{text["muted"]};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width:0px;
}}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background:transparent;
}}

/* ==========================================================
   LABELS

   Die Laufweite der gesperrten Rubriklabels steht hier bewusst
   NICHT: Qt kennt letter-spacing im Stylesheet nicht und verwirft
   die Angabe wortlos. Sie wird ueber QFont.setLetterSpacing gesetzt,
   siehe gui/theme/fonts.py und gui/widgets/eyebrow.py.
========================================================== */

QLabel {{

    background:transparent;

    color:{text["primary"]};
}}

QLabel#title {{

    font-size:{title}px;

    font-weight:{tokens.WEIGHT["bold"]};

    color:{tokens.WHITE};
}}

QLabel#sectionTitle {{

    font-size:{section}px;

    font-weight:{tokens.WEIGHT["semibold"]};

    color:{tokens.WHITE};
}}

QLabel#subtitle {{

    font-size:{body}px;

    color:{text["secondary"]};
}}

QLabel#eyebrow {{

    font-family:"{mono_family}";

    font-size:{eyebrow}px;

    color:{text["muted"]};
}}

QLabel#cardTitle {{

    font-size:{card_title}px;

    font-weight:{tokens.WEIGHT["semibold"]};

    color:{tokens.WHITE};
}}

QLabel#cardValue {{

    font-family:"{mono_family}";

    font-size:{mono}px;

    font-weight:{tokens.WEIGHT["bold"]};

    color:{text["primary"]};
}}

QLabel#muted {{

    color:{text["muted"]};

    font-size:{small}px;
}}

/* ==========================================================
   KNOEPFE

   Der Hauptknopf traegt den Akzent als senkrechten Verlauf
   (hell -> Grundton). Gedrueckt wird er flach und dunkler - eine
   flache Flaeche liest sich als "eingedrueckt", ohne dass dafuer
   ein Schatten noetig waere.
========================================================== */

QPushButton{{

    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {accent_light},
        stop:1 {accent_base}
    );

    color:{accent_on};

    border:none;

    border-radius:{radius_sm}px;

    min-height:{btn_height}px;

    padding:0px 18px;

    font-size:{small}px;

    font-weight:{tokens.WEIGHT["semibold"]};
}}

QPushButton:hover{{

    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {hover_light},
        stop:1 {hover_base}
    );
}}

QPushButton:pressed{{

    background:{accent_pressed};
}}

QPushButton:disabled{{

    background:{surface["raised"]};

    color:{text["faint"]};
}}

/*
   Sekundaerknopf: angehobene Flaeche statt Akzent. Fuer alles, was
   neben dem einen Hauptknopf steht.
*/

QPushButton#secondary{{

    background:{surface["raised"]};

    color:{text["primary"]};

    border:none;

    min-height:{btn_small}px;
}}

QPushButton#secondary:hover{{

    background:{tokens.mix(tokens.WHITE, surface["raised"], 0.06)};
}}

QPushButton#secondary:pressed{{

    background:{surface["card"]};
}}

QPushButton#secondary:disabled{{

    background:{surface["card"]};

    color:{text["faint"]};
}}

/*
   Betonter Sekundaerknopf: getoente Akzentflaeche mit 1-px-Rahmen.
   Der Zustand "aktiv/getoggelt" aus §5 benutzt dieselbe Darstellung.
*/

QPushButton#secondaryAccent{{

    background:{tokens.tint(accent_base, 0.14)};

    color:{accent_light};

    border:1px solid {tokens.tint(accent_base, 0.60)};

    min-height:{btn_small}px;
}}

QPushButton#secondaryAccent:hover{{

    background:{tokens.tint(accent_base, 0.22)};
}}

QPushButton#ghost{{

    background:transparent;

    color:{text["secondary"]};

    border:none;

    min-height:{btn_small}px;
}}

QPushButton#ghost:hover{{

    background:{surface["raised"]};

    color:{text["primary"]};
}}

/*
   Fehlerzustand eines Knopfes (§5): getoente Fehlerflaeche, kein Rot
   als Vollflaeche - der Knopf bleibt bedienbar und soll nicht wie
   eine Warnung schreien.
*/

QPushButton#danger{{

    background:{tokens.tint(tokens.STATE["error"], 0.14)};

    color:{tokens.STATE_TEXT["error"]};

    border:1px solid {tokens.tint(tokens.STATE["error"], 0.50)};
}}

QPushButton#danger:hover{{

    background:{tokens.tint(tokens.STATE["error"], 0.22)};
}}

/* ==========================================================
   EINGABEFELDER

   Eingabefelder sind neben dem Fenster selbst die einzigen Elemente,
   die einen echten umlaufenden Rahmen behalten: hier traegt er
   Bedeutung ("hier kann ich schreiben") statt nur Abgrenzung.
========================================================== */

QLineEdit{{

    background:{surface["sunken"]};

    color:{text["primary"]};

    border:1px solid {border["base"]};

    border-radius:{radius_sm}px;

    min-height:{btn_small}px;

    padding:0px 12px;

    selection-background-color:{accent_base};

    selection-color:{accent_on};
}}

QLineEdit:hover{{

    border:1px solid {border["strong"]};
}}

QLineEdit:focus{{

    border:1px solid {focus_border};
}}

QLineEdit:disabled{{

    color:{text["faint"]};
}}

QPlainTextEdit,
QTextEdit{{

    background:{surface["sunken"]};

    color:{text["primary"]};

    border:1px solid {border["base"]};

    border-radius:{radius_sm}px;

    padding:12px;

    selection-background-color:{accent_base};

    selection-color:{accent_on};
}}

QPlainTextEdit:focus,
QTextEdit:focus{{

    border:1px solid {focus_border};
}}

/* ==========================================================
   REGLER

   Die Wiedergabe-Leiste im Archiv. Ohne eigene Regel zeichnet Qt
   den Stil des Betriebssystems, der zwischen den dunklen Flaechen
   wie ein Fremdkoerper wirkt.
========================================================== */

QSlider::groove:horizontal{{

    height:6px;

    border-radius:3px;

    background:{surface["sunken"]};
}}

QSlider::sub-page:horizontal{{

    height:6px;

    border-radius:3px;

    background:{accent_base};
}}

QSlider::handle:horizontal{{

    width:14px;

    height:14px;

    margin:-4px 0;

    border-radius:7px;

    background:{tokens.WHITE};
}}

QSlider::handle:horizontal:hover{{

    background:{accent_light};
}}

/* ==========================================================
   AUSWAHLFELD
========================================================== */

QComboBox{{

    background:{surface["sunken"]};

    color:{text["primary"]};

    border:1px solid {border["base"]};

    border-radius:{radius_sm}px;

    min-height:{btn_small}px;

    padding-left:12px;
}}

QComboBox:hover{{

    border:1px solid {border["strong"]};
}}

QComboBox:focus,
QComboBox:on{{

    border:1px solid {focus_border};
}}

QComboBox:disabled{{

    color:{text["faint"]};
}}

QComboBox::drop-down{{

    border:none;

    width:28px;

    background:transparent;
}}

QComboBox QAbstractItemView{{

    background:{surface["card"]};

    color:{text["primary"]};

    border:1px solid {border["strong"]};

    border-radius:{radius_sm}px;

    padding:4px;

    outline:none;

    selection-background-color:{surface["raised"]};

    selection-color:{accent_light};
}}

/* ==========================================================
   KONTROLLKAESTCHEN
========================================================== */

QCheckBox{{

    spacing:10px;

    color:{text["primary"]};
}}

QCheckBox::indicator{{

    width:16px;

    height:16px;

    border-radius:4px;

    border:1px solid {border["strong"]};

    background:{surface["sunken"]};
}}

QCheckBox::indicator:hover{{

    border:1px solid {text["muted"]};
}}

QCheckBox::indicator:checked{{

    background:{accent_base};

    border:1px solid {accent_base};
}}

/* ==========================================================
   ZAHLENFELD
========================================================== */

QSpinBox{{

    background:{surface["sunken"]};

    color:{text["primary"]};

    border:1px solid {border["base"]};

    border-radius:{radius_sm}px;

    min-height:{btn_small}px;

    padding-left:10px;
}}

QSpinBox:focus{{

    border:1px solid {focus_border};
}}

/* ==========================================================
   GRUPPENRAHMEN
========================================================== */

QGroupBox{{

    border:1px solid {border["base"]};

    border-radius:{radius_md}px;

    margin-top:18px;

    padding:18px;

    font-weight:{tokens.WEIGHT["bold"]};
}}

QGroupBox::title{{

    subcontrol-origin:margin;

    left:14px;

    padding:0px 8px;
}}

/* ==========================================================
   MENUE (Systemabschnitt im Tray)
========================================================== */

QMenu{{

    background:{surface["card"]};

    color:{text["primary"]};

    border:1px solid {border["strong"]};

    border-radius:{radius_sm}px;

    padding:6px;
}}

QMenu::item{{

    padding:6px 18px;

    border-radius:4px;
}}

QMenu::item:selected{{

    background:{surface["raised"]};

    color:{accent_light};
}}

"""
