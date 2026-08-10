"""
Die Übersicht - die neue Startseite.

**Warum sie das Dashboard ablöst.** Bis 1.7 zeigte die Startseite den
Zustand der Installation: WoW gefunden? Addon installiert? Updates?
Sicherungen? Das ist genau einmal interessant, nämlich am ersten Tag.
Danach ist dort alles dauerhaft grün, und der Bereich, den der Nutzer
bei jedem Start als erstes sieht, sagt ihm nichts, was er nicht schon
weiß.

Die Übersicht zeigt stattdessen, **was heute ansteht**: der nächste
Raid mit Countdown und Aufstellung, der letzte Pull mit dem
schwächsten Bereich und einer konkreten Lektion, der Stand der
Vorbereitung.

Der Installationszustand verschwindet dabei nicht, er verliert nur
seinen Rang: er sitzt als **eine einzige Zeile** am Fuß und klappt
sich nur auf, wenn tatsächlich etwas zu tun ist. Sind alle vier Punkte
in Ordnung, bleibt sie geschlossen und trägt nicht einmal einen Knopf -
das ist der ganze Unterschied zwischen "Zustand melden" und "zur
Handlung auffordern".

Zwei der vier Blöcke haben im Programm noch keine Datenquelle und
zeigen deshalb ihren Leerzustand statt erfundener Zahlen; die Gründe
stehen jeweils an Ort und Stelle.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.sparkline import Sparkline
from gui.widgets.status_dot import StatusDot
from gui.widgets.progress_ring import ProgressRing
from gui.widgets.academy.star_rating import Rating


def _divider() -> QFrame:
    """
    Eine 1-px-Trennlinie innerhalb einer Karte.

    Sie ist erlaubt und widerspricht der Regel "keine Rahmen" nicht:
    ein Rahmen umschließt, eine Trennlinie gliedert.
    """

    line = QFrame()

    line.setFixedHeight(1)

    line.setStyleSheet(f"background:{tokens.SURFACE['raised']};border:none;")

    return line


class RosterCard(Card):
    """
    Die Aufstellung des nächsten Raids.

    Der Raid-Roster erreicht die Companion als **zwei undurchsichtige
    Zeichenketten** (`wednesday` / `thursday` in
    `core/discord_roster_sync.py`). Sie werden ungeparst an das Addon
    weitergereicht - dort liegt der Parser. Auf dieser Seite ist
    deshalb weder eine Startzeit noch eine Zahl der Zusagen noch eine
    Rollenverteilung bekannt.

    Die Karte sagt genau das, statt "0 / 25 zugesagt" zu behaupten.
    Eine Null wäre hier keine Untertreibung, sondern eine falsche
    Messung: niemand hat gezählt.
    """

    def __init__(self, parent=None):

        super().__init__(parent=parent)

        self.setMinimumHeight(150)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[1])

        header.addWidget(eyebrow_label("AUFSTELLUNG"))

        header.addStretch(1)

        self.count = Chip("KEINE DATEN", "neutral")

        header.addWidget(self.count)

        self.addLayout(header)

        self.addWidget(_divider())

        body = QHBoxLayout()

        body.setContentsMargins(0, 0, 0, 0)

        body.setSpacing(tokens.SPACE[4])

        text = QVBoxLayout()

        text.setContentsMargins(0, 0, 0, 0)

        text.setSpacing(4)

        self.explanation = QLabel(
            "Der Gildenkalender wird an das Addon durchgereicht, ohne "
            "hier gelesen zu werden - Zusagen und Rollen sind der App "
            "deshalb nicht bekannt."
        )

        self.explanation.setFont(font("small"))

        self.explanation.setWordWrap(True)

        restyle(
            self.explanation,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        text.addWidget(self.explanation)

        text.addStretch(1)

        body.addLayout(text, 1)

        buttons = QVBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[1])

        self.launch = QPushButton("WoW starten")

        self.launch.setCursor(Qt.PointingHandCursor)

        buttons.addWidget(self.launch)

        self.discord = QPushButton("Aufstellung im Discord")

        self.discord.setObjectName("secondary")

        self.discord.setCursor(Qt.PointingHandCursor)

        buttons.addWidget(self.discord)

        buttons.addStretch(1)

        body.addLayout(buttons)

        self.addLayout(body, 1)


class LastPullCard(Card):
    """
    Dein letzter Pull: Ergebnis, schwächster Bereich, eine Lektion.

    Gelesen wird aus `RaidDataService.history()` - denselben
    `PullSummary`-Einträgen, die auch WeintTVs Verlauf speist. Ohne
    einen abgeschlossenen Pull in dieser Sitzung bleibt die Karte
    leer und sagt, woran es liegt.
    """

    academyRequested = Signal()

    def __init__(self, service, parent=None):

        super().__init__(parent=parent)

        self.service = service

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[1])

        header.addWidget(eyebrow_label("DEIN LETZTER PULL"))

        header.addStretch(1)

        self.timestamp = eyebrow_label("", tokens.TEXT["faint"])

        header.addWidget(self.timestamp)

        self.addLayout(header)

        top = QHBoxLayout()

        top.setContentsMargins(0, 0, 0, 0)

        top.setSpacing(tokens.SPACE[3])

        column = QVBoxLayout()

        column.setContentsMargins(0, 0, 0, 0)

        column.setSpacing(2)

        self.boss = QLabel("Noch kein Pull")

        self.boss.setFont(font("section"))

        restyle(
            self.boss,
            f"color:{tokens.WHITE};background:transparent;",
        )

        column.addWidget(self.boss)

        self.result = QLabel(
            "Sobald ein Kampf endet, steht sein Ergebnis hier."
        )

        self.result.setFont(font("small"))

        self.result.setWordWrap(True)

        restyle(
            self.result,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        column.addWidget(self.result)

        top.addLayout(column, 1)

        self.sparkline = Sparkline()

        top.addWidget(self.sparkline, alignment=Qt.AlignTop)

        self.addLayout(top)

        self.addWidget(_divider())

        weakest = QHBoxLayout()

        weakest.setContentsMargins(0, 0, 0, 0)

        weakest.setSpacing(tokens.SPACE[1])

        weakest.addWidget(
            eyebrow_label("SCHWÄCHSTER BEREICH", tokens.STATE_TEXT["error"])
        )

        self.area = QLabel("—")

        self.area.setFont(font("body"))

        restyle(
            self.area,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        weakest.addWidget(self.area)

        weakest.addStretch(1)

        self.rating = Rating(0)

        weakest.addWidget(self.rating)

        self.addLayout(weakest)

        #
        # Die Lektionskarte: der eine konkrete nächste Schritt. Sie
        # sitzt auf `surface.card` statt auf dem Kartenverlauf, damit
        # sie sich als eigene Ebene absetzt.
        #

        self.lesson = QFrame()

        self.lesson.setObjectName("lessonBox")

        self.lesson.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self.lesson,
            f"""
            QFrame#lessonBox{{
                background:{tokens.SURFACE["card"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        lesson_layout = QVBoxLayout(self.lesson)

        lesson_layout.setContentsMargins(14, 12, 14, 12)

        lesson_layout.setSpacing(6)

        self.lesson_eyebrow = eyebrow_label(
            "EINE LEKTION",
            theme().accent_light(),
        )

        lesson_layout.addWidget(self.lesson_eyebrow)

        self.lesson_title = QLabel("Die Academy schlägt sie vor.")

        self.lesson_title.setFont(font("card"))

        restyle(
            self.lesson_title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        lesson_layout.addWidget(self.lesson_title)

        self.lesson_reason = QLabel(
            "Nach dem ersten ausgewerteten Pull steht hier, woran zu "
            "arbeiten sich am meisten lohnt - mit den Messwerten, aus "
            "denen sich das ergibt."
        )

        self.lesson_reason.setFont(font("small"))

        self.lesson_reason.setWordWrap(True)

        restyle(
            self.lesson_reason,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        lesson_layout.addWidget(self.lesson_reason)

        actions = QHBoxLayout()

        actions.setContentsMargins(0, 0, 0, 0)

        actions.setSpacing(tokens.SPACE[1])

        self.open_lesson = QPushButton("Lektion öffnen")

        self.open_lesson.setObjectName("secondaryAccent")

        self.open_lesson.setCursor(Qt.PointingHandCursor)

        self.open_lesson.clicked.connect(self.academyRequested.emit)

        actions.addWidget(self.open_lesson)

        actions.addStretch(1)

        lesson_layout.addLayout(actions)

        self.addWidget(self.lesson)

        self.addStretch(1)

    # --------------------------------------------------

    def refresh(self):

        history = self.service.history()

        if not history:
            return

        last = history[-1]

        boss = getattr(last, "boss", "") or "Kampf"

        self.boss.setText(boss)

        #
        # Die Sparkline zeigt die Bosslebenspunkte der letzten Pulls -
        # die eine Kurve, die "wird es besser?" beantwortet.
        #

        values = []

        for entry in history[-8:]:

            percent = getattr(entry, "boss_percent", None)

            if percent is not None:

                values.append(100.0 - float(percent))

        self.sparkline.setValues(values)


class PreparationCard(Card):
    """
    Der Stand der Vorbereitung über alle Charaktere.

    Ausrüstungsdaten existieren im Programm nicht (siehe
    `gui/pages/preparation.py`). Der Ring steht deshalb auf 0 und wird
    ausdrücklich als "keine Daten" beschriftet - ein Ring ohne diese
    Beschriftung läse sich als "nichts vorbereitet", also als Befund
    über den Spieler statt über die Datenlage.
    """

    def __init__(self, parent=None):

        super().__init__(parent=parent)

        self.setFixedWidth(300)

        self.addWidget(eyebrow_label("VORBEREITUNG"))

        ring_row = QHBoxLayout()

        ring_row.setContentsMargins(0, 0, 0, 0)

        ring_row.addStretch(1)

        self.ring = ProgressRing(96)

        ring_row.addWidget(self.ring)

        ring_row.addStretch(1)

        self.addLayout(ring_row)

        self.chip_row = QHBoxLayout()

        self.chip_row.setContentsMargins(0, 0, 0, 0)

        self.chip_row.addStretch(1)

        self.chip_row.addWidget(Chip("KEINE DATEN", "neutral"))

        self.chip_row.addStretch(1)

        self.addLayout(self.chip_row)

        self.addWidget(_divider())

        self.note = QLabel(
            "Verzauberungen, Sockel und BiS-Plätze werden vom Addon "
            "noch nicht übertragen."
        )

        self.note.setFont(font("small"))

        self.note.setWordWrap(True)

        restyle(
            self.note,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        self.addWidget(self.note)

        self.addStretch(1)

        self.button = QPushButton("Alle Charaktere prüfen")

        self.button.setObjectName("secondary")

        self.button.setCursor(Qt.PointingHandCursor)

        self.addWidget(self.button)


class SystemRow(QFrame):
    """
    Die Systemzeile: Addon, App, Sync, Sicherung.

    **Sie klappt nur bei Handlungsbedarf auf.** Ist alles in Ordnung,
    bleibt sie 44 px hoch und trägt keinen Knopf - vier grüne Punkte
    sind eine Auskunft, kein Angebot. Erst wenn mindestens ein Punkt
    nicht "ok" ist, wächst sie und zeigt je Punkt eine Zeile mit
    Erklärung.
    """

    pageRequested = Signal(int)

    COLLAPSED = 44

    EXPANDED = 132

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.setObjectName("systemRow")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setFixedHeight(self.COLLAPSED)

        restyle(
            self,
            f"""
            QFrame#systemRow{{
                background:{tokens.SURFACE_EXTRA["row"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
                border-top:1px solid rgba(255,255,255,0.040);
            }}
            """,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(16, 0, 12, 0)

        root.setSpacing(0)

        summary = QHBoxLayout()

        summary.setContentsMargins(0, 0, 0, 0)

        summary.setSpacing(tokens.SPACE[3])

        summary.addWidget(eyebrow_label("SYSTEM"))

        self.entries: dict[str, tuple[StatusDot, QLabel]] = {}

        for key, label in (
            ("addon", "Addon"),
            ("app", "App"),
            ("sync", "Sync"),
            ("backup", "Sicherung"),
        ):

            item = QHBoxLayout()

            item.setContentsMargins(0, 0, 0, 0)

            item.setSpacing(6)

            dot = StatusDot("empty")

            item.addWidget(dot)

            text = QLabel(label)

            text.setFont(font("small"))

            restyle(
                text,
                f"color:{tokens.TEXT['secondary']};background:transparent;",
            )

            item.addWidget(text)

            summary.addLayout(item)

            self.entries[key] = (dot, text)

        summary.addStretch(1)

        self.action = QPushButton("Öffnen")

        self.action.setObjectName("secondary")

        self.action.setCursor(Qt.PointingHandCursor)

        self.action.setVisible(False)

        self.action.clicked.connect(self._open_addon)

        summary.addWidget(self.action)

        self.summary_row = QWidget()

        self.summary_row.setFixedHeight(self.COLLAPSED)

        self.summary_row.setLayout(summary)

        root.addWidget(self.summary_row)

        #
        # Der Detailbereich. Er ist immer gebaut und nur verborgen -
        # ihn beim Aufklappen erst zu erzeugen hieße, im Moment des
        # Aufklappens Widgets anzulegen, und das ist genau der Moment,
        # in dem eine Animation läuft.
        #

        self.details = QWidget()

        detail_layout = QVBoxLayout(self.details)

        detail_layout.setContentsMargins(0, 0, 0, 8)

        detail_layout.setSpacing(4)

        self.detail_rows: dict[str, QLabel] = {}

        for key in ("addon", "app", "sync", "backup"):

            row = QHBoxLayout()

            row.setContentsMargins(0, 0, 0, 0)

            row.setSpacing(8)

            label = QLabel()

            label.setFont(font("small"))

            restyle(
                label,
                f"color:{tokens.TEXT['secondary']};background:transparent;",
            )

            row.addWidget(label, 1)

            detail_layout.addLayout(row)

            self.detail_rows[key] = label

        self.details.setVisible(False)

        root.addWidget(self.details)

        root.addStretch(1)

    # --------------------------------------------------

    def _open_addon(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ADDON)

    def refresh(self):

        state = self.manager.state

        #
        # "warn" statt "error", wo der Nutzer selbst etwas tun kann,
        # und "empty" für alles, worüber noch nichts bekannt ist -
        # beim Start ist der GitHub-Abruf noch unterwegs, und ein
        # rotes Zeichen dafür wäre schlicht falsch.
        #

        states = {
            "addon": (
                "warn" if state.update_available
                else "ok" if state.addon_found
                else "error"
            ),
            "app": (
                "warn" if state.companion_update_available else "ok"
            ),
            "sync": (
                "ok" if state.discord_connected else "empty"
            ),
            "backup": "ok" if state.addon_found else "empty",
        }

        details = {
            "addon": (
                f"Addon {state.addon_version} installiert, "
                f"{state.github_version} verfügbar."
                if state.update_available
                else "Addon nicht gefunden - Installation steht aus."
                if not state.addon_found
                else f"Addon {state.addon_version} ist aktuell."
            ),
            "app": (
                f"WeintCompanion {state.companion_latest_version} "
                "steht bereit."
                if state.companion_update_available
                else f"WeintCompanion {state.companion_version} ist aktuell."
            ),
            "sync": (
                f"Mit dem Bot verbunden ({state.discord_name})."
                if state.discord_connected
                else "Kein Discord-Konto verknüpft."
            ),
            "backup": (
                "Sicherungen werden vor jedem Addon-Update angelegt."
                if state.addon_found
                else "Ohne installiertes Addon gibt es nichts zu sichern."
            ),
        }

        needs_action = False

        for key, value in states.items():

            dot, _label = self.entries[key]

            dot.setState(value)

            self.detail_rows[key].setText(details[key])

            if value in ("warn", "error"):
                needs_action = True

        self.action.setVisible(needs_action)

        #
        # Aufklappen nur bei Handlungsbedarf. Vier grüne Punkte sind
        # eine Auskunft und brauchen weder Platz noch Knopf.
        #

        self.details.setVisible(needs_action)

        self.setFixedHeight(
            self.EXPANDED if needs_action else self.COLLAPSED
        )


class OverviewPage(Page):

    playerRequested = Signal(str)

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "HEUTE",
            "Willkommen zurück.",
            parent,
        )

        self.service = manager.raid_data

        #
        # Countdown rechts im Kopf. Ohne Raidtermin trägt er "kein
        # Termin bekannt" statt einer laufenden Uhr auf null.
        #

        self.countdown = Chip("KEIN TERMIN BEKANNT", "neutral")

        self.header.addAction(self.countdown)

        self.roster = RosterCard()

        self.roster.launch.clicked.connect(self._launch_wow)

        self.addWidget(self.roster)

        #
        # Zweispaltige Reihe
        #

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(20)

        self.last_pull = LastPullCard(self.service)

        self.last_pull.academyRequested.connect(self._open_academy)

        row.addWidget(self.last_pull, 1)

        self.preparation = PreparationCard()

        self.preparation.button.clicked.connect(self._open_preparation)

        row.addWidget(self.preparation)

        self.addLayout(row, 1)

        #
        # Systemzeile
        #

        self.system = SystemRow(manager)

        self.system.pageRequested.connect(self.pageRequested.emit)

        self.addWidget(self.system)

    # --------------------------------------------------

    def _launch_wow(self):

        launcher = getattr(self.manager, "launcher", None)

        if launcher is None:
            return

        try:
            launcher.launch()

        except Exception:

            #
            # Unter Linux ist oft noch kein Startbefehl hinterlegt -
            # dann ist der richtige nächste Schritt die Einstellung,
            # nicht eine Fehlermeldung.
            #

            self.openSettingsSection.emit("wow_client")

    def _open_academy(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ACADEMY)

    def _open_preparation(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.PREPARATION)

    # --------------------------------------------------

    def refresh(self):

        self.system.refresh()

        self.last_pull.refresh()

        state = self.manager.state

        if state.update_available:

            self.header.setTitle(
                "Für das Addon liegt eine neue Version bereit."
            )

            return

        if not state.wow_found:

            self.header.setTitle(
                "World of Warcraft wurde noch nicht gefunden."
            )

            return

        self.header.setTitle("Alles bereit für den nächsten Raid.")
