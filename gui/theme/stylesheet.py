"""
WeintCompanion
Globales Stylesheet
"""

from .colors import Colors
from .metrics import Metrics
from .typography import Typography


APP_STYLE = f"""

/* ==========================================================
   GLOBAL
========================================================== */

QMainWindow {{
    background: {Colors.BACKGROUND};
}}

QWidget {{
    background: transparent;
    color: {Colors.TEXT};

    font-family: "{Typography.FONT}";
    font-size: {Typography.BODY}px;
}}

QToolTip {{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER_GOLD};

    border-radius:8px;

    padding:8px;
}}

/* ==========================================================
   LABELS
========================================================== */

QLabel {{

    background:transparent;

    color:{Colors.TEXT};
}}

QLabel#title {{

    font-size:{Typography.PAGE_TITLE}px;

    font-weight:{Typography.BOLD};

    color:{Colors.WHITE};
}}

QLabel#subtitle {{

    font-size:{Typography.BODY}px;

    color:{Colors.TEXT_SECONDARY};
}}

QLabel#cardTitle {{

    font-size:{Typography.CARD_TITLE}px;

    font-weight:{Typography.BOLD};

    color:{Colors.WHITE};
}}

QLabel#cardValue {{

    font-size:{Typography.BODY}px;

    color:{Colors.TEXT};
}}

QLabel#heroTitle {{

    font-size:{Typography.HERO_TITLE}px;

    font-weight:{Typography.BOLD};

    color:{Colors.WHITE};
}}

QLabel#heroSubtitle {{

    font-size:16px;

    color:{Colors.TEXT_SECONDARY};
}}

QLabel#sidebarLogo {{

    color:{Colors.WHITE};

    font-size:22px;

    font-weight:{Typography.BOLD};

    letter-spacing:1px;
}}

/* ==========================================================
   BUTTONS
========================================================== */

QPushButton{{

    background:{Colors.PRIMARY};

    color:{Colors.WHITE};

    border:none;

    border-radius:{Metrics.RADIUS_MEDIUM}px;

    min-height:{Metrics.BUTTON_HEIGHT}px;

    padding:0px 20px;

    font-size:15px;

    font-weight:{Typography.SEMIBOLD};
}}

QPushButton:hover{{

    background:{Colors.PRIMARY_HOVER};
}}

QPushButton:pressed{{

    background:{Colors.PRIMARY_PRESSED};
}}

QPushButton:disabled{{

    background:{Colors.CARD};

    color:{Colors.TEXT_MUTED};
}}


/* ==========================================================
   LINE EDIT
========================================================== */

QLineEdit{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:12px;

    padding:10px 14px;
}}

QLineEdit:hover{{

    border:1px solid {Colors.BORDER_LIGHT};
}}

QLineEdit:focus{{

    border:1px solid {Colors.GOLD};

    selection-background-color:{Colors.PRIMARY};
}}


/* ==========================================================
   TEXT EDIT
========================================================== */

QPlainTextEdit,
QTextEdit{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:12px;

    padding:12px;
}}

QPlainTextEdit:focus,
QTextEdit:focus{{

    border:1px solid {Colors.GOLD};
}}


/* ==========================================================
   COMBOBOX
========================================================== */

QComboBox{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:12px;

    min-height:40px;

    padding-left:12px;
}}

QComboBox:hover{{

    border:1px solid {Colors.BORDER_LIGHT};
}}

QComboBox:focus{{

    border:1px solid {Colors.GOLD};
}}

QComboBox::drop-down{{

    border:none;

    width:32px;

    background:transparent;
}}

QComboBox QAbstractItemView{{

    background:{Colors.SURFACE};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER_GOLD};

    selection-background-color:{Colors.PRIMARY};

    selection-color:white;
}}


/* ==========================================================
   CHECKBOX
========================================================== */

QCheckBox{{

    spacing:10px;

    color:{Colors.TEXT};
}}

QCheckBox::indicator{{

    width:18px;

    height:18px;

    border-radius:5px;

    border:1px solid {Colors.BORDER};

    background:{Colors.SURFACE_ALT};
}}

QCheckBox::indicator:checked{{

    background:{Colors.GOLD};

    border:1px solid {Colors.GOLD};
}}


/* ==========================================================
   GROUPBOX
========================================================== */

QGroupBox{{

    border:1px solid {Colors.BORDER};

    border-radius:16px;

    margin-top:18px;

    padding:18px;

    font-weight:{Typography.BOLD};
}}

QGroupBox::title{{

    subcontrol-origin:margin;

    left:14px;

    padding:0px 8px;
}}

"""