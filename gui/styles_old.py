APP_STYLE = """
/* ============================================================
   Grundlayout
   ============================================================ */

QMainWindow {
    background: #1B1A21;
}

QWidget {
    background: #1B1A21;
    color: #F2F2F2;
    font-family: "Segoe UI";
    font-size: 14px;
}


/* ============================================================
   Labels
   ============================================================ */

QLabel {
    background: transparent;
    color: #F2F2F2;
}

QLabel#title {
    font-size: 30px;
    font-weight: 700;
    color: white;
}

QLabel#subtitle {
    font-size: 16px;
    color: #B5BAC6;
}

QLabel#cardTitle {
    font-size: 18px;
    font-weight: 700;
}

QLabel#cardValue {
    font-size: 16px;
    font-weight: 600;
}

QLabel#statusOk {
    color: #7ED957;
}

QLabel#statusWarn {
    color: #DDB94D;
}

QLabel#statusError {
    color: #E65A5A;
}


/* ============================================================
   Sidebar
   ============================================================ */

QFrame#sidebar {

    background: #17161D;

    border-right: 1px solid #32343E;

}

QLabel#sidebarLogo {

    font-size: 24px;

    font-weight: 700;

    padding: 18px;

    color: white;

}

QLabel#sidebarStatus {

    background: #22242D;

    border: 1px solid #353845;

    border-radius: 14px;

    padding: 14px;

    color: #C3C7D0;

}

QFrame#sidebar QPushButton {

    background: transparent;

    border: none;

    border-radius: 12px;

    text-align: left;

    padding: 14px;

    font-size: 15px;

    color: #DADCE3;

}

QFrame#sidebar QPushButton:hover {

    background: #2A2D37;

}

QFrame#sidebar QPushButton:checked {

    background: #8B5CF6;

    color: white;

}


/* ============================================================
   Karten
   ============================================================ */

QFrame#card {

    background: #272932;

    border-radius: 18px;

    border: 1px solid #3B3E49;

}

QFrame#card:hover {

    border: 1px solid #8B5CF6;

}


/* ============================================================
   Standard Buttons
   ============================================================ */

QPushButton {

    background: #8B5CF6;

    color: white;

    border: none;

    border-radius: 12px;

    padding: 12px 18px;

    min-height: 42px;

    font-size: 15px;

    font-weight: 600;

}

QPushButton:hover {

    background: #9C73FF;

}

QPushButton:pressed {

    background: #7447EB;

}


/* ============================================================
   Hero Button
   ============================================================ */

QPushButton#heroButton {

    background: #8B5CF6;

    font-size: 18px;

    font-weight: 700;

    min-height: 72px;

    border-radius: 18px;

}

QPushButton#heroButton:hover {

    background: #9C73FF;

}

QPushButton#heroButton:pressed {

    background: #7447EB;

}


/* ============================================================
   Gold Button
   ============================================================ */

QPushButton#goldButton {

    background: #D4AF37;

    color: black;

}

QPushButton#goldButton:hover {

    background: #E5C75A;

}


/* ============================================================
   Aktivitäten / Log
   ============================================================ */

QTextEdit {

    background: #22242D;

    border: 1px solid #363945;

    border-radius: 14px;

    padding: 10px;

    color: white;

}


/* ============================================================
   Listen
   ============================================================ */

QListWidget {

    background: #22242D;

    border: 1px solid #363945;

    border-radius: 14px;

    outline: none;

}

QListWidget::item {

    padding: 12px;

    border-radius: 8px;

}

QListWidget::item:selected {

    background: #8B5CF6;

}

QListWidget::item:hover {

    background: #31343E;

}


/* ============================================================
   Eingabefelder
   ============================================================ */

QLineEdit,
QComboBox {

    background: #22242D;

    border: 1px solid #3A3D48;

    border-radius: 10px;

    padding: 8px;

    color: white;

}

QLineEdit:focus,
QComboBox:focus {

    border: 1px solid #8B5CF6;

}


/* ============================================================
   Scrollbars
   ============================================================ */

QScrollBar:vertical {

    width: 10px;

    background: transparent;

}

QScrollBar::handle:vertical {

    background: #494D59;

    border-radius: 5px;

}

QScrollBar::handle:vertical:hover {

    background: #8B5CF6;

}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {

    height: 0px;

}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {

    background: transparent;

}

QProgressBar{

    background:#22242D;

    border:1px solid #3B3E49;

    border-radius:10px;

    min-height:18px;

    text-align:center;

}

QProgressBar::chunk{

    background:#8B5CF6;

    border-radius:8px;

}

#dashboardHeader{

    background:transparent;

}
"""