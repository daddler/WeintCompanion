from PySide6.QtCore import Qt

from PySide6.QtSvgWidgets import QSvgWidget

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)

from gui.theme.colors import Colors

CARD_RADIUS = 12


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
            background:{Colors.CARD};
            border:1px solid {Colors.BORDER};
            border-radius:{CARD_RADIUS}px;
        }}
        """)

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(22, 20, 22, 20)

        self.root.setSpacing(14)

        #
        # --------------------------------------------------
        # Titel
        # --------------------------------------------------
        #

        header = QHBoxLayout()

        header.setSpacing(10)

        self.icon = QSvgWidget(icon)

        self.icon.setFixedSize(18, 18)

        header.addWidget(
            self.icon,
            alignment=Qt.AlignVCenter,
        )

        self.title = QLabel(title)

        self.title.setStyleSheet(f"""
        QLabel{{
            color:{Colors.WHITE};
            font-size:15px;
            font-weight:600;
            background:transparent;
            border:none;
        }}
        """)

        header.addWidget(self.title)

        header.addStretch()

        self.root.addLayout(header)

        #
        # Optionaler Untertitel
        #

        if subtitle:

            self.subtitle = QLabel(subtitle)

            self.subtitle.setWordWrap(True)

            self.subtitle.setStyleSheet(f"""
            QLabel{{
                color:{Colors.TEXT_SECONDARY};
                font-size:13px;
                background:transparent;
                border:none;
            }}
            """)

            self.root.addWidget(self.subtitle)

        #
        # Dünne Trennlinie
        #

        line = QFrame()

        line.setFixedHeight(1)

        line.setStyleSheet(f"""
        QFrame{{
            background:{Colors.BORDER};
            border:none;
        }}
        """)

        self.root.addWidget(line)

        #
        # Inhalt
        #

        self.content = QVBoxLayout()

        self.content.setSpacing(14)

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
