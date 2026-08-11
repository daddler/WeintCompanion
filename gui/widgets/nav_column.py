"""
WeintCompanion 2.0
Die Navigationsspalte

Sie löst die 72-px-Rail aus 1.7 ab. Der Unterschied ist nicht nur die
Breite: die Rail zeigte zehn Symbole ohne Beschriftung und ohne
Gliederung, und welches davon "Sync" und welches "Software" war, musste
man sich merken oder ertasten. 2.0 gliedert dieselben Bereiche in drei
Gruppen (RAID / CHARAKTER / SYSTEM) und schreibt sie aus - einklappbar
auf die alten 72 px, wenn der Platz gebraucht wird.

Drei Dinge, die hier Sorgfalt verlangen:

**Der Indikator wandert.** Der aktive Eintrag trägt links einen
gemalten Balken 3 x 22 px, der beim Wechsel an seine neue Stelle
gleitet (180 ms). Er gehört deshalb nicht zum Eintrag, sondern zur
Spalte - ein Balken je Eintrag könnte nur ein- und ausgeblendet
werden, und aus einer Bewegung würde ein Blinken. Gemalt wird er
**außerhalb** der Eintragsfläche, damit er nicht als Rahmen gelesen
wird.

**Eingeklappt ist nicht dasselbe wie erzwungen eingeklappt.** Unter
1120 px klappt die Spalte selbsttätig ein, und WeintTV verlangt es
unabhängig von der Breite. Beides darf die **Wahl des Nutzers** nicht
überschreiben: wer die Spalte ausgeklappt haben will, findet sie
ausgeklappt vor, sobald der Zwang endet. Deshalb zwei getrennte
Merker.

**Die Beschriftung verschwindet vor der Spalte.** Beim Einklappen wird
zuerst der Text ausgeblendet und dann die Breite animiert; andernfalls
schiebt sich der Text während der Animation sichtbar unter den rechten
Rand.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

#
# Nur `PageId`, nicht `build_page_specs()`: dieses Modul auf Ebene der
# Seitenklassen zu binden wäre ein Zirkelbezug. `gui/navigation.py`
# importiert die Seiten selbst erst im Funktionsrumpf, der Enum-Import
# hier ist deshalb unbedenklich (main_window macht denselben).
#

from gui.navigation import PageId
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.icons import tinted_pixmap
from gui.theme.motion import curve, duration
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.status_dot import StatusDot


#
# Der gemalte Indikator am aktiven Eintrag (§4). Er steht links
# **außerhalb** der Eintragsfläche - läge er innerhalb, würde er als
# Rahmen gelesen statt als Markierung.
#

INDICATOR_WIDTH = 3

INDICATOR_HEIGHT = 22


class NavItem(QFrame):
    """
    Ein Eintrag: Symbol, Beschriftung, optionales Abzeichen.
    """

    clicked = Signal(int)

    def __init__(self, spec, parent=None):

        super().__init__(parent)

        self.setObjectName("navItem")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setCursor(Qt.PointingHandCursor)

        self.spec = spec

        self._active = False

        self._collapsed = False

        self.setFixedHeight(theme().metric("nav_item", 40))

        root = QHBoxLayout(self)

        root.setContentsMargins(11, 0, 10, 0)

        root.setSpacing(10)

        self.icon = QLabel()

        self.icon.setFixedSize(18, 18)

        root.addWidget(self.icon)

        self.label = QLabel(spec.label)

        self.label.setFont(font("body"))

        root.addWidget(self.label, 1)

        #
        # Abzeichen rechts: entweder ein Statuspunkt oder eine Zahl.
        # Beides ist selten belegt, aber beides muss Platz haben, ohne
        # die Beschriftung zu verschieben, wenn es erscheint.
        #

        self.badge_dot = StatusDot("empty")

        self.badge_dot.setVisible(False)

        root.addWidget(self.badge_dot)

        self.badge_text = QLabel()

        self.badge_text.setFont(font("micro"))

        self.badge_text.setVisible(False)

        root.addWidget(self.badge_text)

        self._apply()

    # --------------------------------------------------

    def setActive(self, active: bool):

        if active == self._active:
            return

        self._active = active

        self._apply()

    def isActive(self) -> bool:

        return self._active

    def setCollapsed(self, collapsed: bool):

        if collapsed == self._collapsed:
            return

        self._collapsed = collapsed

        self.label.setVisible(not collapsed)

        self.badge_text.setVisible(
            not collapsed and bool(self.badge_text.text())
        )

        #
        # Eingeklappt trägt der Tooltip die Beschriftung - sonst wäre
        # die Spalte wieder das Symbolraten aus 1.7.
        #

        self.setToolTip(self.spec.label if collapsed else "")

        layout = self.layout()

        if collapsed:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(self.icon, Qt.AlignCenter)

        else:
            layout.setContentsMargins(11, 0, 10, 0)

        self._apply()

    def setBadge(self, state: str | None = None, text: str = ""):
        """
        Ein Abzeichen setzen: `state` für einen Punkt, `text` für eine
        Zahl. Beides leer entfernt es.
        """

        self.badge_dot.setVisible(bool(state))

        if state:
            self.badge_dot.setState(state)

        self.badge_text.setText(text)

        self.badge_text.setVisible(
            bool(text) and not self._collapsed
        )

        if text:

            restyle(
                self.badge_text,
                f"color:{theme().accent_light()};background:transparent;",
            )

    # --------------------------------------------------

    def _apply(self):

        #
        # Das Symbol wird in Themefarbe eingefärbt und im aktiven
        # Zustand in Akzentfarbe - eine der wenigen Stellen, an denen
        # der Akzent Bedeutung trägt (§2.2).
        #

        color = (
            theme().accent_base()
            if self._active
            else tokens.TEXT["muted"]
        )

        self.icon.setPixmap(
            tinted_pixmap(self.spec.icon, color, 18)
        )

        if self._active:

            surface = tokens.SURFACE["raised"]

            text_color = tokens.WHITE

        else:

            surface = "transparent"

            text_color = tokens.TEXT["secondary"]

        restyle(
            self,
            f"""
            QFrame#navItem{{
                background:{surface};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        restyle(
            self.label,
            f"color:{text_color};background:transparent;border:none;",
        )

    def enterEvent(self, event):

        super().enterEvent(event)

        if not self._active:

            restyle(
                self,
                f"""
                QFrame#navItem{{
                    background:{tokens.SURFACE["raised"]};
                    border:none;
                    border-radius:{tokens.RADIUS["md"]}px;
                }}
                """,
            )

    def leaveEvent(self, event):

        super().leaveEvent(event)

        if not self._active:
            self._apply()

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.clicked.emit(int(self.spec.page_id))

        super().mousePressEvent(event)


class NavColumn(QFrame):
    """
    Die Spalte selbst.
    """

    pageChanged = Signal(int)

    avatarClicked = Signal()

    toggled = Signal(bool)

    def __init__(self, manager, specs, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.setObjectName("navColumn")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        #
        # Die Wahl des Nutzers und der von außen auferlegte Zwang -
        # getrennt, damit der Zwang die Wahl nicht überschreibt.
        #

        self._user_collapsed = bool(
            manager.config.data.get("nav_collapsed", False)
        )

        self._forced_collapsed = False

        self._indicator_y = 0.0

        self._indicator_animation: QPropertyAnimation | None = None

        self._width_animation: QPropertyAnimation | None = None

        self.items: dict[int, NavItem] = {}

        self._group_labels: list[QLabel] = []

        self._build(specs)

        self._apply_surface()

        width = (
            tokens.NAV_WIDTH_COLLAPSED
            if self.is_collapsed()
            else tokens.NAV_WIDTH_EXPANDED
        )

        self.setFixedWidth(width)

        self._apply_collapsed(animate=False)

        #
        # Gebundene Methode statt Lambda: eine Lambda hält eine harte
        # Referenz auf `self`, und der ThemeManager ist ein Singleton -
        # die Spalte würde damit nie mehr freigegeben.
        #

        theme().accent_changed.connect(self._on_accent)

    # --------------------------------------------------

    def _build(self, specs):

        root = QVBoxLayout(self)

        root.setContentsMargins(12, 12, 12, 12)

        root.setSpacing(2)

        last_group = None

        for spec in specs:

            if spec.group != last_group:

                if last_group is not None:
                    root.addSpacing(tokens.SPACE[3])

                label = eyebrow_label(spec.group, tokens.TEXT["faint"])

                label.setContentsMargins(11, 0, 0, 4)

                root.addWidget(label)

                self._group_labels.append(label)

                last_group = spec.group

            item = NavItem(spec)

            item.clicked.connect(self._on_item_clicked)

            root.addWidget(item)

            self.items[int(spec.page_id)] = item

        root.addStretch(1)

        #
        # Fuß: das Discord-Konto. Eingeklappt bleibt nur die Plakette.
        #

        self.account = _AccountButton()

        self.account.clicked.connect(self.avatarClicked.emit)

        root.addWidget(self.account)

        self.refresh()

    def _apply_surface(self):

        restyle(
            self,
            f"""
            QFrame#navColumn{{
                background:{tokens.SURFACE["sunken"]};
                border:none;
                border-right:1px solid {tokens.SURFACE["raised"]};
            }}
            """,
        )

    def _on_accent(self, _name: str = ""):

        for item in self.items.values():
            item._apply()

        self.update()

    # --------------------------------------------------
    # Auswahl
    # --------------------------------------------------

    def _on_item_clicked(self, page_id: int):

        self.pageChanged.emit(page_id)

    def setCurrentPage(self, page_id: int):

        target = None

        for key, item in self.items.items():

            active = key == int(page_id)

            item.setActive(active)

            if active:
                target = item

        if target is not None:
            self._move_indicator(target)

    # --------------------------------------------------
    # Indikator
    # --------------------------------------------------

    def _indicator_target(self, item: NavItem) -> float:
        """
        Die Oberkante des Balkens, sodass er auf der Höhe des
        Eintrags zentriert steht.
        """

        return (
            item.y()
            + (item.height() - INDICATOR_HEIGHT) / 2.0
        )

    def _move_indicator(self, item: NavItem):

        target = self._indicator_target(item)

        ms = duration("nav")

        if ms <= 0 or self._indicator_y == 0.0:

            #
            # Beim ersten Setzen nicht animieren: der Balken käme
            # sonst von der Oberkante des Fensters hereingefahren.
            #

            self.indicatorY = target

            return

        if self._indicator_animation is not None:
            self._indicator_animation.stop()

        animation = QPropertyAnimation(self, b"indicatorY", self)

        animation.setDuration(ms)

        animation.setEasingCurve(QEasingCurve(curve("nav")))

        animation.setStartValue(self._indicator_y)

        animation.setEndValue(target)

        animation.start()

        self._indicator_animation = animation

    def _get_indicator_y(self) -> float:

        return self._indicator_y

    def _set_indicator_y(self, value: float):

        self._indicator_y = value

        self.update()

    indicatorY = Property(float, _get_indicator_y, _set_indicator_y)

    def paintEvent(self, event):

        super().paintEvent(event)

        if self._indicator_y <= 0:
            return

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing, True)

        gradient = QLinearGradient(
            0.0,
            self._indicator_y,
            0.0,
            self._indicator_y + INDICATOR_HEIGHT,
        )

        gradient.setColorAt(0.0, QColor(theme().accent_light()))
        gradient.setColorAt(1.0, QColor(theme().accent_base()))

        painter.setPen(Qt.NoPen)

        painter.setBrush(gradient)

        painter.drawRoundedRect(
            QRectF(0.0, self._indicator_y, INDICATOR_WIDTH, INDICATOR_HEIGHT),
            2.0,
            2.0,
        )

    # --------------------------------------------------
    # Ein- und Ausklappen
    # --------------------------------------------------

    def is_collapsed(self) -> bool:

        return self._user_collapsed or self._forced_collapsed

    def toggle(self):
        """
        Die Wahl des Nutzers umschalten.
        """

        self.set_user_collapsed(not self._user_collapsed)

    def set_user_collapsed(self, collapsed: bool):

        collapsed = bool(collapsed)

        if collapsed == self._user_collapsed:
            return

        self._user_collapsed = collapsed

        self.manager.config.data["nav_collapsed"] = collapsed

        self.manager.config.save()

        self._apply_collapsed()

        self.toggled.emit(self.is_collapsed())

    def set_forced_collapsed(self, forced: bool):
        """
        Von außen erzwungenes Einklappen (Haltepunkt, WeintTV).

        Die Wahl des Nutzers bleibt gespeichert und gilt wieder,
        sobald der Zwang endet.
        """

        forced = bool(forced)

        if forced == self._forced_collapsed:
            return

        was = self.is_collapsed()

        self._forced_collapsed = forced

        if self.is_collapsed() != was:

            self._apply_collapsed()

            self.toggled.emit(self.is_collapsed())

    def _apply_collapsed(self, animate: bool = True):

        collapsed = self.is_collapsed()

        target = (
            tokens.NAV_WIDTH_COLLAPSED
            if collapsed
            else tokens.NAV_WIDTH_EXPANDED
        )

        #
        # Beim Einklappen zuerst den Text weg, dann die Breite. Beim
        # Ausklappen umgekehrt - sonst erscheint die Beschriftung in
        # einer Spalte, die noch zu schmal für sie ist, und wird
        # sichtbar abgeschnitten.
        #

        if collapsed:
            self._set_items_collapsed(True)

        for label in self._group_labels:
            label.setVisible(not collapsed)

        self.account.setCollapsed(collapsed)

        ms = duration("nav") if animate else 0

        if ms <= 0:

            self.setFixedWidth(target)

            if not collapsed:
                self._set_items_collapsed(False)

            self._reposition_indicator()

            return

        previous = self._width_animation

        self._width_animation = None

        if previous is not None:

            try:
                previous.stop()

            except RuntimeError:
                #
                # Von Qt bereits gelöscht (DeleteWhenStopped, s.u.).
                #
                pass

        start = self.width()

        #
        # Animiert wird `maximumWidth`. Damit die Spalte der Animation
        # überhaupt folgen kann, muss `minimumWidth` ihr aus dem Weg
        # sein: beim Einklappen sofort auf den (kleineren) Zielwert,
        # beim Ausklappen bleibt es auf dem Startwert und zieht erst
        # am Ende nach. Bliebe stattdessen eine feste Breite gesetzt
        # (setFixedWidth setzt beide Grenzen), würde jeder Schritt der
        # Animation sofort wieder überschrieben - die Spalte spränge.
        #

        self.setMinimumWidth(min(start, target))

        animation = QPropertyAnimation(self, b"maximumWidth", self)

        animation.setDuration(ms)

        animation.setEasingCurve(QEasingCurve(curve("nav")))

        animation.setStartValue(start)

        animation.setEndValue(target)

        def done():

            self.setFixedWidth(target)

            #
            # Die Beschriftung erst einblenden, wenn die Spalte breit
            # genug ist - andernfalls steht sie sichtbar abgeschnitten
            # in einer noch schmalen Spalte.
            #

            if not collapsed:
                self._set_items_collapsed(False)

            self._reposition_indicator()

            self._width_animation = None

        animation.finished.connect(done)

        #
        # `DeleteWhenStopped`: die Animation gehört sonst als Kind der
        # Spalte und bliebe nach jedem Ein- und Ausklappen liegen,
        # samt der Schließung `done`. Deshalb räumt `done()` oben auch
        # die Referenz - nach dem Löschen zeigte sie auf ein nicht
        # mehr vorhandenes C++-Objekt, und der nächste Aufruf würde
        # darauf `stop()` rufen (dafür der Schutz weiter oben).
        #

        animation.start(QPropertyAnimation.DeleteWhenStopped)

        self._width_animation = animation

    def _set_items_collapsed(self, collapsed: bool):

        for item in self.items.values():
            item.setCollapsed(collapsed)

    def _reposition_indicator(self):

        for item in self.items.values():

            if item.isActive():

                self.indicatorY = self._indicator_target(item)

                return

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self._reposition_indicator()

    # --------------------------------------------------

    def refresh(self):

        state = self.manager.state

        self._refresh_update_badge(state)

        account = self.manager.discord_account.load()

        if account:

            username = account.get("username", "Discord")

            self.account.setState(True, username, "verbunden")

        elif state.discord_connected:

            self.account.setState(
                True,
                state.discord_name or "Discord",
                "Bot online",
            )

        else:

            self.account.setState(False, "Nicht verbunden", "")

    # --------------------------------------------------

    def _refresh_update_badge(self, state):
        """
        Das Abzeichen an "Addon & Updates".

        Der einzige Hinweis auf ein wartendes Update, der **außerhalb
        der Übersicht** sichtbar ist. Ohne ihn musste man entweder auf
        der Übersicht stehen oder von sich aus in den Addon-Bereich
        gehen - `NavItem.setBadge()` gab es seit 2.0, aufgerufen hat es
        niemand.

        Eine Zahl und kein Punkt, weil es zwei voneinander unabhängige
        Update-Kanäle gibt (Addon und Companion) und "2" die
        Nachfrage erspart, ob beide gemeint sind. Eingeklappt zeigt die
        Spalte nur Symbole; `setBadge()` blendet die Zahl dann aus, und
        der Punkt bleibt - deshalb wird beides gesetzt.

        Ein fehlendes Addon ist **kein** Update: dort steht die
        Installation aus, und das sagt die Systemzeile der Übersicht mit
        ihrem eigenen Wortlaut. Ein Abzeichen "1" daneben würde eine
        Aktualisierung behaupten, wo noch nichts installiert ist.
        """

        item = self.items.get(PageId.ADDON)

        if item is None:
            return

        pending = 0

        if getattr(state, "update_available", False):
            pending += 1

        if getattr(state, "companion_update_available", False):
            pending += 1

        if not pending:

            item.setBadge(None, "")

            return

        item.setBadge("warn", str(pending))


class _AccountButton(QFrame):
    """
    Der Fuß der Spalte: Plakette, Name, Zustand.
    """

    clicked = Signal()

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName("navAccount")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setCursor(Qt.PointingHandCursor)

        self.setFixedHeight(44)

        self._connected = False

        root = QHBoxLayout(self)

        root.setContentsMargins(8, 0, 8, 0)

        root.setSpacing(10)

        self.badge = QLabel()

        self.badge.setFixedSize(28, 28)

        self.badge.setAlignment(Qt.AlignCenter)

        self.badge.setFont(font("mono"))

        root.addWidget(self.badge)

        column = QVBoxLayout()

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(0)

        self.name = QLabel()

        self.name.setFont(font("small"))

        column.addWidget(self.name)

        self.state = eyebrow_label("", tokens.STATE_TEXT["ok"])

        column.addWidget(self.state)

        root.addLayout(column, 1)

        self._apply()

    def setCollapsed(self, collapsed: bool):

        self.name.setVisible(not collapsed)

        self.state.setVisible(not collapsed)

        self.layout().setContentsMargins(
            0 if collapsed else 8,
            0,
            0 if collapsed else 8,
            0,
        )

        if collapsed:
            self.layout().setAlignment(self.badge, Qt.AlignCenter)

    def setState(self, connected: bool, name: str, state: str):

        self._connected = connected

        self.name.setText(name)

        self.state.setText(state.upper())

        self.state.setVisible(bool(state) and self.name.isVisible())

        initial = (name or "?").strip()[:1].upper()

        self.badge.setText(initial)

        self.setToolTip(
            f"Discord: {name}" if connected else "Nicht mit Discord verbunden"
        )

        self._apply()

    def _apply(self):

        if self._connected:

            background = (
                "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                f"stop:0 {tokens.SHEEN_VIOLET[0]},"
                f"stop:1 {tokens.SHEEN_VIOLET[1]})"
            )

            color = tokens.WHITE

        else:

            background = tokens.SURFACE["raised"]

            color = tokens.TEXT["muted"]

        restyle(
            self.badge,
            f"""
            QLabel{{
                background:{background};
                color:{color};
                border-radius:14px;
            }}
            """,
        )

        restyle(
            self.name,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

    def enterEvent(self, event):

        super().enterEvent(event)

        restyle(
            self,
            f"""
            QFrame#navAccount{{
                background:{tokens.SURFACE["raised"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

    def leaveEvent(self, event):

        super().leaveEvent(event)

        restyle(self, "")

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)
