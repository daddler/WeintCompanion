from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

from gui.theme.colors import Colors

CONTENT_MAX_WIDTH = 640


class SectionContent(QWidget):
    """
    Gemeinsames Grundgerüst für die Settings-Unterseiten: Eyebrow +
    Titel + Untertitel, danach eine schmale Inhaltsspalte
    (max. 640px, wie im Design).
    """

    def __init__(self, eyebrow_text: str, title_text: str, subtitle_text: str = ""):

        super().__init__()

        #
        # Explizit statt transparent: QStackedWidget poliert das
        # "background:transparent" der globalen Stylesheet bei
        # Kindern, die noch nie sichtbar waren, nicht zuverlässig neu
        # (sichtbar als weißer statt dunkler Hintergrund beim ersten
        # Wechsel zu einer Unterseite) - ein expliziter Hintergrund
        # + WA_StyledBackground umgeht das zuverlässig.
        #

        self.setObjectName("sectionContent")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(
            f"QWidget#sectionContent{{background:{Colors.BACKGROUND};}}"
        )

        outer = QHBoxLayout(self)

        outer.setContentsMargins(40, 36, 40, 36)

        column = QVBoxLayout()

        column.setSpacing(18)

        outer.addLayout(column)

        outer.addStretch()

        header = QVBoxLayout()

        header.setSpacing(4)

        eyebrow = QLabel(eyebrow_text)

        eyebrow.setObjectName("eyebrow")

        header.addWidget(eyebrow)

        title = QLabel(title_text)

        title.setStyleSheet(
            f"font-size:22px;font-weight:700;color:{Colors.WHITE};"
            "letter-spacing:-0.01em;"
        )

        header.addWidget(title)

        if subtitle_text:

            subtitle = QLabel(subtitle_text)

            subtitle.setWordWrap(True)

            subtitle.setObjectName("subtitle")

            header.addWidget(subtitle)

        column.addLayout(header)

        self.body = QVBoxLayout()

        self.body.setSpacing(0)

        column.addLayout(self.body)

        column.addStretch()

        for widget in (self, ):
            widget.setMaximumWidth(
                CONTENT_MAX_WIDTH + 80
            )

    def addRow(self, item, divider: bool = True):

        if isinstance(item, QLayout):
            self.body.addLayout(item)
        else:
            self.body.addWidget(item)

        if divider:

            line = QFrame()

            line.setFixedHeight(1)

            line.setStyleSheet(f"background:{Colors.BORDER};")

            self.body.addSpacing(20)
            self.body.addWidget(line)
            self.body.addSpacing(20)


def toggle_row(label_text: str, description_text: str, toggle, enabled: bool = True):
    """
    Eine Zeile mit Label+Beschreibung links, ToggleSwitch rechts -
    wie die Allgemein-Einstellungen im Design.
    """

    row = QWidget()

    layout = QHBoxLayout(row)

    layout.setContentsMargins(0, 0, 0, 0)

    layout.setSpacing(20)

    text_col = QVBoxLayout()

    text_col.setSpacing(4)

    label_color = Colors.WHITE if enabled else Colors.TEXT_MUTED

    label = QLabel(label_text)

    label.setStyleSheet(
        f"font-size:14px;font-weight:600;color:{label_color};"
    )

    text_col.addWidget(label)

    description = QLabel(description_text)

    description.setWordWrap(True)

    description.setStyleSheet(
        f"font-size:13px;color:{Colors.TEXT_MUTED};"
    )

    text_col.addWidget(description)

    layout.addLayout(text_col, 1)

    layout.addWidget(toggle, alignment=Qt.AlignTop)

    return row
