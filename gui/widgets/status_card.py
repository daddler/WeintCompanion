from __future__ import annotations

from PySide6.QtCore import (
    Qt,
    QSize,
    QRectF,
    Signal,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)

from PySide6.QtGui import (
    QColor,
    QCursor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtSvgWidgets import QSvgWidget
from pathlib import Path

CARD_RADIUS = 20


class StatusCard(QFrame):

    HERO_MODE = "hero"
    NORMAL_MODE = "normal"

    clicked = Signal()

    def __init__(
        self,
        icon: str,
        title: str,
        status: str,
        details: str,
        button_text: str = "",
    ):
        super().__init__()

        self._display_mode = self.NORMAL_MODE

        self.setObjectName("statusCard")

        self.setCursor(
            QCursor(Qt.PointingHandCursor)
        )

        self.setMouseTracking(True)

        #
        # immer identische Höhe
        #

        self.setFixedHeight(180)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self._hover = False
        self._state = "normal"
        self._border_alpha = 110

        self.border_animation = QPropertyAnimation(
            self,
            b"borderAlpha",
        )

        self.border_animation.setStartValue(80)
        self.border_animation.setEndValue(170)

        self.border_animation.setDuration(1400)

        self.border_animation.setLoopCount(-1)

        self.border_animation.setEasingCurve(
            QEasingCurve.InOutSine
        )

        shadow = QGraphicsDropShadowEffect(self)

        shadow.setBlurRadius(40)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(0,0,0,120))

        self.setGraphicsEffect(
            shadow
        )

        #
        # Root
        #

        self.root = QVBoxLayout(self)

        self.root.setContentsMargins(
            22,
            18,
            22,
            18,
        )

        self.root.setSpacing(12)

        #
        # ==========================================
        # Header
        # ==========================================
        #

        header = QHBoxLayout()

        header.setSpacing(12)

        self.root.addLayout(header)

        #
        # Icon
        #

        self.icon_container = QFrame()

        self.icon_container.setFixedSize(
            50,
            50,
        )

        self.icon_container.setStyleSheet("""
        QFrame{

            background:#353947;

            border:1px solid rgba(255,255,255,20);

            border-radius:16px;
        }
        """)

        icon_layout = QVBoxLayout(
            self.icon_container
        )

        icon_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.icon_label = QSvgWidget()

        self.icon_label.setFixedSize(
            26,
            26,
        )

        self.set_icon(icon)

        icon_layout.addWidget(
            self.icon_label,
            alignment=Qt.AlignCenter,
        )

        header.addWidget(
            self.icon_container
        )

        #
        # Titel
        #

        title_layout = QVBoxLayout()

        title_layout.setSpacing(2)

        header.addLayout(
            title_layout,
            1,
        )

        self.title_label = QLabel(title)

        self.title_label.setStyleSheet("""
        QLabel{

            color:white;

            font-size:15px;

            font-weight:700;
        }
        """)

        title_layout.addWidget(
            self.title_label
        )

        #
        # Status (groß)
        #

        self.status_label = QLabel(status)

        self.status_label.setStyleSheet("""
        QLabel{

            color:#67D46B;

            font-size:13px;

            font-weight:700;

            background:transparent;
        }
        """)

        title_layout.addWidget(
            self.status_label
        )

        header.addStretch()

        #
        # Badge rechts
        #

        self.badge = QLabel("")

        self.badge.setMinimumHeight(26)

        self.badge.setAlignment(
            Qt.AlignCenter
        )

        self.badge.setStyleSheet("""
        QLabel{

            background:rgba(67,192,122,20);

            color:#73DA7B;

            border:1px solid rgba(67,192,122,60);

            border-radius:13px;

            padding-left:10px;

            padding-right:10px;

            font-size:11px;

            font-weight:700;
        }
        """)

        header.addWidget(
            self.badge,
            alignment=Qt.AlignTop,
        )

                #
        # ==========================================
        # Hauptinhalt
        # ==========================================
        #

        self.value_label = QLabel()

        self.value_label.setStyleSheet("""
        QLabel{

            color:white;

            font-size:26px;

            font-weight:800;

            background:transparent;
        }
        """)

        self.value_label.hide()

        self.root.addWidget(
            self.value_label
        )

        #
        # Details
        #

        self.details_label = QLabel(details)

        self.details_label.setWordWrap(True)

        self.details_label.setStyleSheet("""
        QLabel{

            color:#AEB4C2;

            font-size:12px;

            background:transparent;
        }
        """)

        self.root.addWidget(
            self.details_label
        )

        #
        # Abstand bis Button
        #

        self.root.addStretch()

        #
        # ==========================================
        # Button
        # ==========================================
        #

        bottom = QHBoxLayout()

        bottom.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        bottom.setSpacing(0)

        self.button = QPushButton(
            button_text
        )

        self.button.setMinimumHeight(44)

        self.button.setCursor(
            Qt.PointingHandCursor
        )

        self.button.setStyleSheet("""
        QPushButton{

            background:#D6B04D;

            color:#171717;

            border:none;

            border-radius:12px;

            padding-left:18px;

            padding-right:18px;

            font-size:13px;

            font-weight:700;
        }

        QPushButton:hover{

            background:#E6C15A;
        }

        QPushButton:pressed{

            background:#B8942D;
        }

        QPushButton:disabled{

            background:#3C414C;

            color:#7B808B;
        }
        """)

        if not button_text:

            self.button.hide()

        bottom.addStretch()

        bottom.addWidget(
            self.button
        )

        self.root.addLayout(
            bottom
        )

        #
        # Initialen Status setzen
        #

        self.set_status(status)
    
        # --------------------------------------------------
    # Größe
    # --------------------------------------------------

    def sizeHint(self):

        return QSize(
            320,
            180,
        )

    # --------------------------------------------------
    # Paint
    # --------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        rect = self.rect().adjusted(
            1,
            1,
            -1,
            -1,
        )

        path = QPainterPath()

        path.addRoundedRect(
            QRectF(rect),
            CARD_RADIUS,
            CARD_RADIUS,
        )

        #
        # Hintergrund
        #

        background = QLinearGradient(
            rect.topLeft(),
            rect.bottomLeft(),
        )

        background.setColorAt(
            0,
            QColor(36, 41, 51, 215),
        )

        background.setColorAt(
            0.55,
            QColor(29, 33, 41, 205),
        )

        background.setColorAt(
            1,
            QColor(24, 27, 34, 195),
        )

        painter.fillPath(
            path,
            background,
        )

        #
        # Hover Glow
        #

        if self._hover:

            glow = QLinearGradient(
                rect.topLeft(),
                rect.bottomRight(),
            )

            glow.setColorAt(
                0,
                QColor(175,120,255,55),
            )

            glow.setColorAt(
                1,
                QColor(139, 92, 246, 0),
            )

            painter.fillPath(
                path,
                glow,
            )

            shine = QLinearGradient(
                rect.left(),
                rect.top(),
                rect.right(),
                rect.top(),
            )

            shine.setColorAt(
                0,
                QColor(255,255,255,18),
            )

            shine.setColorAt(
                0.5,
                QColor(255,255,255,4),
            )

            shine.setColorAt(
                1,
                QColor(255,255,255,0),
            )

            painter.fillPath(
                path,
                shine,
            )

        #
        # Rahmen
        #

        border = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )

        alpha = self._border_alpha

        if self._state == "warning":

            border.setColorAt(
                0,
                QColor(214, 176, 77, alpha),
            )

            border.setColorAt(
                1,
                QColor(142, 106, 22, alpha),
            )

        elif self._state == "error":

            border.setColorAt(
                0,
                QColor(228, 106, 106, alpha),
            )

            border.setColorAt(
                1,
                QColor(150, 57, 57, alpha),
            )

        elif self._state == "info":

            border.setColorAt(
                0,
                QColor(95, 170, 255, alpha),
            )

            border.setColorAt(
                1,
                QColor(55, 120, 220, alpha),
            )

        elif self._hover:

            border.setColorAt(
                0,
                QColor(139, 92, 246, 180),
            )

            border.setColorAt(
                1,
                QColor(101, 70, 204, 180),
            )

        else:

            border.setColorAt(
                0,
                QColor(74, 78, 89, 120),
            )

            border.setColorAt(
                1,
                QColor(54, 58, 69, 120),
            )

        painter.setPen(
            QPen(
                border,
                1.5,
            )
        )

        painter.drawRoundedRect(
            QRectF(rect),
            CARD_RADIUS,
            CARD_RADIUS,
        )

        painter.end()

    # --------------------------------------------------
    # Hover
    # --------------------------------------------------

    def enterEvent(self, event):

        self._hover = True

        self.update()

        super().enterEvent(event)

    def leaveEvent(self, event):

        self._hover = False

        self.update()

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.clicked.emit()

        super().mousePressEvent(event)

    def getBorderAlpha(self):

        return self._border_alpha


    def setBorderAlpha(self, value):

        self._border_alpha = value

        self.update()


    borderAlpha = Property(
        int,
        getBorderAlpha,
        setBorderAlpha,
    )
    
    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def set_state(self, state: str):

        self._state = state.lower()

        if self._state in ("warning", "error", "info"):

            self.border_animation.start()

        else:

            self.border_animation.stop()

            self._border_alpha = 110

        self.update()

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(text)

        lower = text.lower()

        #
        # Badge automatisch anpassen
        #

        if (
            "🟢" in text
            or "installiert" in lower
            or "aktuell" in lower
            or "gefunden" in lower
            or "vorhanden" in lower
        ):

            badge = "ONLINE"

            fg = "#7DDB9E"
            bg = "rgba(67,192,122,22)"
            border = "rgba(67,192,122,65)"

        elif (
            "🟡" in text
            or "update" in lower
            or "warn" in lower
        ):

            badge = "UPDATE"

            fg = "#E8C96D"
            bg = "rgba(212,175,55,20)"
            border = "rgba(212,175,55,70)"

        elif (
            "🔴" in text
            or "nicht" in lower
            or "offline" in lower
            or "error" in lower
            or "fehler" in lower
        ):

            badge = "OFFLINE"

            fg = "#F28C8C"
            bg = "rgba(255,87,87,22)"
            border = "rgba(255,87,87,65)"

        else:

            badge = "INFO"

            fg = "#8DBFFF"
            bg = "rgba(63,140,255,20)"
            border = "rgba(63,140,255,65)"

        self.status_label.setStyleSheet(f"""
        QLabel{{
            color:{fg};
            font-size:13px;
            font-weight:700;
            background:transparent;
        }}
        """)

        self.badge.setText(
            badge
        )

        self.badge.setStyleSheet(f"""
        QLabel{{

            background:{bg};

            color:{fg};

            border:1px solid {border};

            border-radius:13px;

            padding-left:10px;

            padding-right:10px;

            font-size:11px;

            font-weight:700;
        }}
        """)

        if badge == "ONLINE":

            self.icon_container.setStyleSheet("""
            QFrame{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(67,192,122,55),
                    stop:1 rgba(67,192,122,20)
                );
                border:1px solid rgba(67,192,122,90);
                border-radius:16px;
            }
            """)

        elif badge == "UPDATE":

            self.icon_container.setStyleSheet("""
            QFrame{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(212,175,55,55),
                    stop:1 rgba(212,175,55,18)
                );
                border:1px solid rgba(212,175,55,90);
                border-radius:16px;
            }
            """)

        elif badge == "OFFLINE":

            self.icon_container.setStyleSheet("""
            QFrame{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(235,90,90,55),
                    stop:1 rgba(235,90,90,18)
                );
                border:1px solid rgba(235,90,90,90);
                border-radius:16px;
            }
            """)

        else:

            self.icon_container.setStyleSheet("""
            QFrame{
                background:qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(80,145,255,45),
                    stop:1 rgba(80,145,255,15)
                );
                border:1px solid rgba(80,145,255,80);
                border-radius:16px;
            }
            """)

    # --------------------------------------------------
    # Value
    # --------------------------------------------------

    def set_value(self, value: str):

        value = str(value).strip()

        self.value_label.setVisible(
            bool(value)
        )

        self.value_label.setText(value)

    # --------------------------------------------------
    # Details
    # --------------------------------------------------

    def set_details(self, text: str):

        self.details_label.setText(text)

    # --------------------------------------------------
    # Title
    # --------------------------------------------------

    def set_title(self, text: str):

        self.title_label.setText(text)

    # --------------------------------------------------
    # Icon
    # --------------------------------------------------

    def set_icon(self, icon: str):

        if Path(icon).exists():
            self.icon_label.load(icon)

    # --------------------------------------------------
    # Tooltip
    # --------------------------------------------------

    def set_tooltip(self, text: str):

        self.setToolTip(text)

        self.details_label.setToolTip(text)

        self.status_label.setToolTip(text)

    # --------------------------------------------------
    # Button
    # --------------------------------------------------

    def set_button_text(self, text: str):

        self.button.setText(text)

        self.button.setVisible(
            bool(text)
        )

    def set_button_enabled(self, enabled: bool):

        self.button.setEnabled(enabled)

    def show_button(self):

        self.button.show()

    def hide_button(self):

        self.button.hide()

    def get_button(self):

        return self.button

    def setDisplayMode(self, mode: str):

        self._display_mode = mode

        shadow = self.graphicsEffect()

        if mode == self.HERO_MODE:

            if shadow:
                shadow.setBlurRadius(8)
                shadow.setOffset(0, 2)

            self.setStyleSheet("""
            QFrame#statusCard{
                background:rgba(28,31,39,150);
                border:none;
            }
            """)

        else:

            if shadow:
                shadow.setBlurRadius(26)
                shadow.setOffset(0,10)

            self.setStyleSheet("")