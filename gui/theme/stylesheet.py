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

    border:1px solid {Colors.BORDER_LIGHT};

    border-radius:6px;

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
    background:{Colors.BORDER_LIGHT};
    border-radius:5px;
    min-height:24px;
}}

QScrollBar::handle:vertical:hover {{
    background:{Colors.TEXT_MUTED};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height:0px;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background:transparent;
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

    letter-spacing:-0.02em;
}}

QLabel#subtitle {{

    font-size:{Typography.BODY}px;

    color:{Colors.TEXT_SECONDARY};
}}

QLabel#eyebrow {{

    font-family:"{Typography.MONO_FONT}";

    font-size:{Typography.MICRO}px;

    color:{Colors.TEXT_MUTED};

    letter-spacing:0.15em;
}}

QLabel#cardTitle {{

    font-size:{Typography.CARD_TITLE}px;

    font-weight:{Typography.SEMIBOLD};

    color:{Colors.WHITE};
}}

QLabel#cardValue {{

    font-family:"{Typography.MONO_FONT}";

    font-size:{Typography.BODY}px;

    color:{Colors.TEXT};
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

    padding:0px 18px;

    font-size:13px;

    font-weight:{Typography.SEMIBOLD};
}}

QPushButton:hover{{

    background:{Colors.PRIMARY_HOVER};
}}

QPushButton:pressed{{

    background:{Colors.PRIMARY_PRESSED};
}}

QPushButton:disabled{{

    background:{Colors.SURFACE_LIGHT};

    color:{Colors.TEXT_MUTED};
}}


/* ==========================================================
   LINE EDIT
========================================================== */

QLineEdit{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:8px;

    padding:8px 12px;
}}

QLineEdit:hover{{

    border:1px solid {Colors.BORDER_LIGHT};
}}

QLineEdit:focus{{

    border:1px solid {Colors.PRIMARY};

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

    border-radius:8px;

    padding:12px;
}}

QPlainTextEdit:focus,
QTextEdit:focus{{

    border:1px solid {Colors.PRIMARY};
}}


/* ==========================================================
   COMBOBOX
========================================================== */

QComboBox{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:8px;

    min-height:36px;

    padding-left:12px;
}}

QComboBox:hover{{

    border:1px solid {Colors.BORDER_LIGHT};
}}

QComboBox:focus{{

    border:1px solid {Colors.PRIMARY};
}}

QComboBox::drop-down{{

    border:none;

    width:28px;

    background:transparent;
}}

QComboBox QAbstractItemView{{

    background:{Colors.SURFACE};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER_LIGHT};

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

    width:16px;

    height:16px;

    border-radius:4px;

    border:1px solid {Colors.BORDER_LIGHT};

    background:{Colors.SURFACE_ALT};
}}

QCheckBox::indicator:checked{{

    background:{Colors.PRIMARY};

    border:1px solid {Colors.PRIMARY};
}}


/* ==========================================================
   SPINBOX
========================================================== */

QSpinBox{{

    background:{Colors.SURFACE_ALT};

    color:{Colors.TEXT};

    border:1px solid {Colors.BORDER};

    border-radius:8px;

    min-height:34px;

    padding-left:10px;
}}

QSpinBox:focus{{

    border:1px solid {Colors.PRIMARY};
}}


/* ==========================================================
   GROUPBOX
========================================================== */

QGroupBox{{

    border:1px solid {Colors.BORDER};

    border-radius:12px;

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
