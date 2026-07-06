from PySide6.QtCore import Qt

from gui.widgets.status_card import CARD_RADIUS

from PySide6.QtSvgWidgets import QSvgWidget

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)


class SectionCard(QFrame):

    def __init__(
        self,
        icon: str,
        title: str,
        subtitle: str = "",
    ):
        super().__init__()

        self.setObjectName("sectionCard")

        self.setStyleSheet(f"""
        QFrame#sectionCard{{
            background:#20242D;
            border:1px solid #353B47;
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            24,
            22,
            24,
            22,
        )

        self.root.setSpacing(18)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        header.setSpacing(12)

        self.icon = QSvgWidget(icon)

        self.icon.setFixedSize(
            22,
            22,
        )

        header.addWidget(
            self.icon,
            alignment=Qt.AlignVCenter,
        )

        self.title = QLabel(title)

        self.title.setStyleSheet("""
        QLabel{
            color:white;
            font-size:20px;
            font-weight:700;
            background:transparent;
            border:none;
        }
        """)

        header.addWidget(
            self.title,
        )

        header.addStretch()

        self.root.addLayout(header)

        #
        # Optionaler Untertitel
        #

        if subtitle:

            self.subtitle = QLabel(subtitle)

            self.subtitle.setWordWrap(True)

            self.subtitle.setStyleSheet("""
            QLabel{
                color:#AEB4C2;
                font-size:13px;
                background:transparent;
                border:none;
            }
            """)

            self.root.addWidget(self.subtitle)

        #
        # Dünne Trennlinie
        #

        line = QFrame()

        line.setFixedHeight(1)

        line.setStyleSheet("""
        QFrame{
            background:#343945;
            border:none;
        }
        """)

        self.root.addWidget(line)

        #
        # Inhalt
        #

        self.content = QVBoxLayout()

        self.content.setSpacing(16)

        self.root.addLayout(self.content)

    # --------------------------------------------------
    # API
    # --------------------------------------------------

    def addWidget(self, widget):

        self.content.addWidget(widget)

    def addLayout(self, layout):

        self.content.addLayout(layout)

    def addSpacing(self, value):

        self.content.addSpacing(value)

    def addStretch(self):

        self.content.addStretch()