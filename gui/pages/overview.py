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

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.backend_config import TARGET_URL, roster_target
from core.browser import open_url
from core.changelog_reader import format_changelog_body
from core.changelog_source import ADDON, COMPANION, LABELS, latest_entry
from core.platform import is_linux
from core.raid_schedule import countdown_text, day_text, signup_text
from gui.dialogs.changelog_dialog import show_changelog
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.motion import curve, duration
from gui.theme.restyle import restyle
from gui.theme.theme_manager import theme
from gui.widgets.card import Card
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.sparkline import Sparkline
from gui.widgets.status_dot import StatusDot
from gui.widgets.progress_ring import ProgressRing
from gui.widgets.academy.star_rating import Rating
from gui.widgets.wrapped_label import enable_wrap


#
# Wie viele Zeilen der Auszug im Update-Hinweis trägt. Drei sind der
# Punkt, an dem er noch überflogen wird; alles darüber gehört in die
# vollständige Ansicht, die einen Klick entfernt ist.
#

EXCERPT_LINES = 3

EXCERPT_CHARS = 260


def _excerpt(entry) -> str:
    """
    Die ersten Zeilen eines Changelog-Eintrags.

    Ohne Eintrag ein Satz, der sagt, dass es keinen gibt - und nicht
    etwa nichts. Eine leere Fläche unter "Update verfügbar" liest sich
    wie ein Ladefehler.
    """

    if entry is None:

        return (
            "Für diese Fassung liegen keine Änderungsnotizen vor."
        )

    text = format_changelog_body(entry.body)

    lines = [line for line in text.splitlines() if line.strip()]

    excerpt = "\n".join(lines[:EXCERPT_LINES])

    if len(excerpt) > EXCERPT_CHARS:

        excerpt = excerpt[:EXCERPT_CHARS].rstrip() + " …"

    return excerpt or "Für diese Fassung liegen keine Notizen vor."


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
    Der nächste Raid: Termin, Titel, Zusagen.

    **Was sich hier geändert hat.** Bis 2.0.1 stand an dieser Stelle
    "Zusagen und Rollen sind der App nicht bekannt", und das stimmte:
    der Roster erreicht die Companion als zwei undurchsichtige
    WCIMPORT-Zeichenketten (`core/discord_roster_sync.py`), die
    ungeparst ans Addon weitergehen - und die bekommt ohnehin nur, wer
    die Raidlead-Rolle trägt.

    Der Bot beantwortet die Frage jetzt eigens
    (`/companion/raid-schedule`, für jeden verknüpften Nutzer). Was
    weiterhin **nicht** hier steht, ist die Namensliste: dieser
    Endpunkt liefert bewusst nur Termin und Zahlen. Wer sehen will,
    wer zugesagt hat, geht über den Knopf ins Discord.

    Ohne Antwort bleibt die alte Haltung unverändert: die Karte sagt,
    dass nichts bekannt ist, statt "0 von 25" zu behaupten. Eine Null
    wäre keine Untertreibung, sondern eine falsche Messung - niemand
    hat gezählt.
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

        self.title = QLabel("")

        self.title.setFont(font("section"))

        enable_wrap(self.title)

        restyle(
            self.title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        self.title.setVisible(False)

        text.addWidget(self.title)

        self.when = QLabel("")

        self.when.setFont(font("body"))

        restyle(
            self.when,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        self.when.setVisible(False)

        text.addWidget(self.when)

        self.explanation = QLabel(
            "Sobald im Discord ein Termin steht, erscheint er hier - "
            "mit Datum, Uhrzeit und der Zahl der Zusagen."
        )

        self.explanation.setFont(font("small"))

        enable_wrap(self.explanation)

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

    # --------------------------------------------------

    def apply(self, schedule, day):
        """
        `schedule` ist ein `RaidSchedule`, `day` sein nächster Termin.

        Beides kann leer sein - dann steht wieder da, dass nichts
        bekannt ist. Der Zustand "es gibt einen Raid, aber alle
        Termine liegen hinter uns" ist davon nicht zu trennen und
        bekommt deshalb dieselbe Auskunft.
        """

        if not getattr(schedule, "known", False) or day is None:

            self.title.setVisible(False)

            self.when.setVisible(False)

            self.explanation.setText(
                "Sobald im Discord ein Termin steht, erscheint er "
                "hier - mit Datum, Uhrzeit und der Zahl der Zusagen."
            )

            self.count.setText("KEINE DATEN")

            self.count.setVariant("neutral")

            return

        self.title.setText(schedule.title)

        self.title.setVisible(True)

        self.when.setText(day_text(day))

        self.when.setVisible(True)

        self.explanation.setText(
            signup_text(day, schedule.raid_size)
            + (
                " · Anmeldung geschlossen"
                if schedule.signup_status == "locked"
                else ""
            )
        )

        #
        # Der Chip nennt die Zusagen des nächsten Tages. "ok" erst,
        # wenn die Raidgröße erreicht ist - alles darunter ist noch
        # offen, und ein grünes Zeichen bei 12 von 25 würde das
        # Gegenteil sagen.
        #

        if schedule.raid_size:

            self.count.setText(
                f"{day.active} / {schedule.raid_size} ZUGESAGT"
            )

            self.count.setVariant(
                "ok" if day.active >= schedule.raid_size else "warn"
            )

            return

        self.count.setText(f"{day.active} ZUGESAGT")

        self.count.setVariant("info")


class UpdateRow(QFrame):
    """
    Eine Komponente mit wartendem Update: Name, Fassung, Auszug,
    Knopf.
    """

    updateRequested = Signal(str)

    changelogRequested = Signal(str)

    def __init__(self, component: str, parent=None):

        super().__init__(parent)

        self.component = component

        self.setObjectName("updateRow")

        self.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self,
            f"""
            QFrame#updateRow{{
                background:{tokens.SURFACE["card"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(14, 12, 14, 12)

        root.setSpacing(6)

        head = QHBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(tokens.SPACE[1])

        self.title = QLabel("")

        self.title.setFont(font("card"))

        restyle(
            self.title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        head.addWidget(self.title)

        self.versions = QLabel("")

        self.versions.setFont(font("mono"))

        restyle(
            self.versions,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        head.addWidget(self.versions)

        head.addStretch(1)

        root.addLayout(head)

        #
        # Der Auszug ist der eigentliche Grund für diesen Hinweis: ein
        # "Update verfügbar" ohne Inhalt beantwortet die einzige Frage
        # nicht, die man davor hat.
        #

        self.excerpt = QLabel("")

        self.excerpt.setFont(font("small"))

        enable_wrap(self.excerpt)

        restyle(
            self.excerpt,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(self.excerpt)

        actions = QHBoxLayout()

        actions.setContentsMargins(0, 0, 0, 0)

        actions.setSpacing(tokens.SPACE[1])

        self.install = QPushButton("Jetzt aktualisieren")

        self.install.setObjectName("secondaryAccent")

        self.install.setCursor(Qt.PointingHandCursor)

        self.install.clicked.connect(self._request_update)

        actions.addWidget(self.install)

        self.changelog = QPushButton("Alle Änderungen ansehen")

        self.changelog.setObjectName("ghost")

        self.changelog.setCursor(Qt.PointingHandCursor)

        self.changelog.clicked.connect(self._request_changelog)

        actions.addWidget(self.changelog)

        actions.addStretch(1)

        root.addLayout(actions)

    # --------------------------------------------------

    def _request_update(self):

        self.updateRequested.emit(self.component)

    def _request_changelog(self):

        self.changelogRequested.emit(self.component)

    # --------------------------------------------------

    def apply(self, name: str, installed: str, available: str, excerpt: str):

        self.title.setText(f"{name} {available}")

        self.versions.setText(
            f"{installed} → {available}" if installed else available
        )

        self.excerpt.setText(excerpt)

    def set_running(self, running: bool, note: str = ""):

        self.install.setEnabled(not running)

        self.changelog.setEnabled(not running)

        if note:
            self.excerpt.setText(note)


class UpdateCard(Card):
    """
    Der Update-Hinweis auf der Übersicht.

    **Warum er hierher gehört.** Ein wartendes Update war an drei
    Stellen zu sehen (Systemzeile am Fuß, Abzeichen in der Navigation,
    ein Meldungsstreifen beim Start), aber an keiner davon *auslösbar*.
    Jeder Weg endete auf "Addon & Updates", also drei Klicks für eine
    Handlung, die aus einem bestehen kann. Diese Karte ist der eine
    Ort, an dem beides zusammenkommt: was kommt, und der Knopf dafür.

    Sie ersetzt die Seite "Addon & Updates" nicht - wer erst lesen
    will, was eine Fassung bringt, kommt über "Alle Änderungen
    ansehen" an den vollständigen Changelog, und die Seite bleibt für
    Sicherungen, Neuinstallation und Protokoll zuständig.

    **Sie erscheint nur, wenn wirklich etwas ansteht.** Eine dauerhaft
    sichtbare Karte "alles aktuell" wäre genau der Fehler, den die
    Übersicht 2.0 beim Dashboard behoben hat: der Bereich, den man bei
    jedem Start zuerst sieht, sagt sonst etwas, das man schon weiß.
    """

    updateRequested = Signal(str)

    changelogRequested = Signal(str)

    def __init__(self, parent=None):

        super().__init__(accent=True, parent=parent)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[1])

        self.eyebrow = eyebrow_label(
            "UPDATE VERFÜGBAR",
            theme().accent_light(),
        )

        header.addWidget(self.eyebrow)

        header.addStretch(1)

        self.chip = Chip("1 UPDATE", "warn")

        header.addWidget(self.chip)

        self.addLayout(header)

        self.rows: dict[str, UpdateRow] = {}

        for component in (ADDON, COMPANION):

            row = UpdateRow(component)

            row.updateRequested.connect(self.updateRequested.emit)

            row.changelogRequested.connect(self.changelogRequested.emit)

            row.setVisible(False)

            self.rows[component] = row

            self.addWidget(row)

        #
        # Der Akzent färbt die Rubrik ein - gelesen wird er beim
        # Umschalten neu, über eine gebundene Methode statt einer
        # Closure (siehe die Notiz zu den drei Themensignalen in
        # CLAUDE.md).
        #

        theme().accent_changed.connect(self._on_accent)

    # --------------------------------------------------

    def _on_accent(self, _name: str = ""):

        self.eyebrow.setStyleSheet(
            f"color:{theme().accent_light()};background:transparent;"
        )

    def setCount(self, count: int):

        self.chip.setText(
            f"{count} UPDATES" if count != 1 else "1 UPDATE"
        )


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

        enable_wrap(self.result)

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

        enable_wrap(self.lesson_reason)

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

    Seit 2.0.1 gibt es die Daten wirklich: WeintCodex 1.3.3.1 meldet
    Verzauberungen, Sockel und offene BiS-Plätze (`"character_sheet"`,
    siehe `core/character_store.py`). Bis dahin stand der Ring auf 0
    und trug ausdrücklich "keine Daten" - genau diese Beschriftung
    bleibt für den Fall, dass noch nichts geliefert wurde. Ein Ring
    ohne sie läse sich als "nichts vorbereitet", also als Befund über
    den Spieler statt über die Datenlage.
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

        self.chip = Chip("KEINE DATEN", "neutral")

        self.chip_row.addWidget(self.chip)

        self.chip_row.addStretch(1)

        self.addLayout(self.chip_row)

        self.addWidget(_divider())

        self.note = QLabel(
            "Verzauberungen, Sockel und BiS-Plätze meldet das Addon "
            "beim Anmelden im Spiel."
        )

        self.note.setFont(font("small"))

        enable_wrap(self.note)

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

    # --------------------------------------------------

    def apply(self, summary: dict):
        """
        `summary` ist `CharacterStore.preparation_summary()`.

        `ratio is None` heißt "kein Charakter hat eine Prüfung
        gemeldet" - dann bleibt der Ring auf 0 und der Chip sagt
        warum. Eine Null ohne diesen Chip wäre eine Messung, die es
        nicht gab.
        """

        ratio = summary.get("ratio")

        if ratio is None:

            self.ring.setValue(0.0)

            self.chip.setText("KEINE DATEN")

            self.chip.setVariant("neutral")

            self.note.setText(
                "Verzauberungen, Sockel und BiS-Plätze meldet das "
                "Addon beim Anmelden im Spiel."
            )

            return

        self.ring.setValue(ratio)

        self.chip.setText(f"{ratio * 100:.0f} % AUSGERÜSTET")

        self.chip.setVariant("ok" if ratio >= 0.999 else "warn")

        open_count = summary.get("open", 0)

        rated = summary.get("rated", 0)

        if open_count == 0:

            self.note.setText(
                f"Alles verzaubert und gesockelt "
                f"({rated} Charakter{'e' if rated != 1 else ''} geprüft)."
            )

            return

        self.note.setText(
            f"{open_count} fehlende Verzauberung"
            f"{'en' if open_count != 1 else ''} oder leere Sockel über "
            f"{rated} geprüfte{'n' if rated == 1 else ''} "
            f"Charakter{'e' if rated != 1 else ''}."
        )


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

        #
        # Eine Animation je Zeile, wiederverwendet: das Ziel ist immer
        # `minimumHeight` dieses Widgets. Eine neue QPropertyAnimation
        # je Aufklappen wäre ein Kind, das liegen bleibt - siehe die
        # Notiz zu Animationen in CLAUDE.md. Der Zustand, aus dem sie
        # startet, wird in _set_expanded() gesetzt.
        #

        self._height_animation = QPropertyAnimation(
            self,
            b"minimumHeight",
            self,
        )

        self._height_animation.setEasingCurve(
            QEasingCurve(curve("expand"))
        )

        self._expanded: bool | None = None

        #
        # Einmal verbunden, mit einer gebundenen Methode statt einer
        # Closure über `expanded`: eine Closure müsste vor jedem Start
        # wieder getrennt werden (sonst stellt eine ältere den falschen
        # Endzustand her), und `disconnect()` ohne bestehende Verbindung
        # warnt. Den Zustand liest der Handler aus `self._expanded`.
        #

        self._height_animation.finished.connect(
            self._on_height_animation_finished
        )

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

        self._set_expanded(needs_action)

    def _set_expanded(self, expanded: bool):
        """
        Die Zeile auf ihre Höhe bringen - animiert (`motion.expand`).

        Vorher sprang sie über `setFixedHeight()` von 44 auf 132 px.
        Der Auslöser ist meist eine Prüfung, die im Hintergrund fertig
        wird, also kein Klick des Nutzers: ohne Bewegung sieht es aus,
        als hätte die Seite einen Sprung gemacht, statt dass etwas
        dazugekommen ist. `motion.expand` ist genau für diese Zeile
        gedacht und war bis hierher unbenutzt.
        """

        if expanded == self._expanded:
            return

        self._expanded = expanded

        target = self.EXPANDED if expanded else self.COLLAPSED

        #
        # Beim Aufklappen zuerst zeigen, beim Zuklappen erst am Ende
        # verbergen - andernfalls animiert die Zeile auf eine Höhe, in
        # der noch nichts steht bzw. schon nichts mehr.
        #

        if expanded:
            self.details.setVisible(True)

        ms = duration("expand")

        #
        # setFixedHeight() setzt Minimum UND Maximum. Animiert wird
        # `minimumHeight`, das Maximum muss deshalb vorher freigegeben
        # werden, sonst hält es die Zeile auf ihrer alten Höhe fest.
        #

        self.setMaximumHeight(max(target, self.height()))

        self._height_animation.stop()

        if ms <= 0:

            #
            # Bewegung reduziert: setzen statt animieren. Der
            # Endzustand muss hier von Hand hergestellt werden, weil
            # der finished-Zweig unten nicht durchläuft.
            #

            self.setFixedHeight(target)

            self.details.setVisible(expanded)

            return

        self._height_animation.setDuration(ms)

        self._height_animation.setStartValue(self.height())

        self._height_animation.setEndValue(target)

        self._height_animation.start()

    def _on_height_animation_finished(self):
        """
        Am Ziel wieder festnageln, damit das Layout die Zeile nicht
        weiter dehnt, und den Detailbereich erst jetzt verbergen.

        Liest `self._expanded`, statt den Zustand mitzuschleppen: läuft
        das Zuklappen noch, während schon wieder aufgeklappt wird, gilt
        der neueste Stand und nicht der, mit dem die Animation startete.
        """

        expanded = bool(self._expanded)

        self.setFixedHeight(
            self.EXPANDED if expanded else self.COLLAPSED
        )

        self.details.setVisible(expanded)


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

        #
        # Der Countdown zählt in Minuten, also wird er einmal pro
        # Minute nachgezogen. Nicht im Sekundentakt: die Beschriftung
        # ist grobkörnig (siehe `countdown_text()`), und ein Zeichnen
        # pro Sekunde für eine Angabe, die sich alle sechzig ändert,
        # ist reine Arbeit ohne Bild.
        #
        # Der Zeitgeber läuft nur, solange die Seite sichtbar ist -
        # `on_enter`/`on_leave` schalten ihn, wie WeintTV und die
        # Academy es mit dem Datenstrom halten.
        #

        self._clock = QTimer(self)

        self._clock.setInterval(60_000)

        self._clock.timeout.connect(self._refresh_countdown)

        #
        # Der Update-Hinweis steht **über** der Aufstellung, weil er
        # eine Handlung trägt und alles darunter eine Auskunft ist.
        # Sichtbar wird er nur, wenn wirklich etwas aussteht.
        #

        self.updates = UpdateCard()

        self.updates.setVisible(False)

        self.updates.updateRequested.connect(self._start_update)

        self.updates.changelogRequested.connect(self._open_changelog)

        self.addWidget(self.updates)

        self._runner = None

        self.roster = RosterCard()

        self.roster.launch.clicked.connect(self._launch_wow)

        self.roster.discord.clicked.connect(self._open_discord_roster)

        self.addWidget(self.roster)

        #
        # Zweispaltige Reihe
        #

        #
        # Als Raster statt als Reihe: unter 980 px stellt der
        # Haltepunkt die beiden Karten untereinander, und ein
        # QGridLayout kann eine Karte umsetzen, ohne dass sie neu
        # gebaut werden muesste.
        #

        self.row = QGridLayout()

        self.row.setContentsMargins(0, 0, 0, 0)

        self.row.setHorizontalSpacing(20)

        self.row.setVerticalSpacing(20)

        self.last_pull = LastPullCard(self.service)

        self.last_pull.academyRequested.connect(self._open_academy)

        self.row.addWidget(self.last_pull, 0, 0)

        self.preparation = PreparationCard()

        self.preparation.button.clicked.connect(self._open_preparation)

        self.row.addWidget(self.preparation, 0, 1)

        self.row.setColumnStretch(0, 1)

        self._single_column = False

        self.addLayout(self.row, 1)

        #
        # Systemzeile
        #

        self.system = SystemRow(manager)

        self.system.pageRequested.connect(self.pageRequested.emit)

        self.addWidget(self.system)

    # --------------------------------------------------

    def _launch_wow(self):
        """
        WoW über Battle.net starten - derselbe Weg wie bis 1.7.

        `manager.start_wow()` und nicht `manager.launcher`: der
        `Launcher` startet eine *Datei* (er gehört dem Selbstupdate und
        verlangt einen Pfad), Battle.net startet der
        `BattleNetLauncher`. Der Aufruf `launcher.launch()` ohne
        Argument warf deshalb nur einen `TypeError`, den das
        `except Exception` darunter verschluckt hat - der Knopf ist
        stillschweigend immer in den Einstellungen gelandet, statt das
        Spiel zu starten.
        """

        #
        # Unter Linux ist oft noch kein Startbefehl hinterlegt - dann
        # ist der richtige nächste Schritt die Einstellung, nicht eine
        # Fehlermeldung.
        #

        if (
            is_linux()
            and not self.manager.config.get_linux_launch_command()
        ):

            self.manager.logger.warning(
                "Kein Battle.net-Start-Befehl hinterlegt - bitte "
                "zuerst in den Einstellungen (WoW-Client) einrichten."
            )

            self.openSettingsSection.emit("wow_client")

            return

        #
        # Fehler meldet start_wow() selbst ins Protokoll.
        #

        self.manager.start_wow()

    def _open_discord_roster(self):
        """
        Die Aufstellung dort öffnen, wo sie tatsächlich steht.

        Diese Karte kann den Roster nicht anzeigen - er erreicht die
        Companion als zwei undurchsichtige Zeichenketten und wird
        ungeparst an das Addon weitergereicht (siehe RosterCard).
        Der Knopf führt deshalb an die Quelle statt einen Inhalt zu
        versprechen, den es hier nicht gibt.

        Welches der drei möglichen Ziele es ist, entscheidet
        `core.backend_config.roster_target()` - dort ohne Qt und
        deshalb ohne Fenster prüfbar. Hier bleibt nur das Ausführen.
        """

        kind, value = roster_target(
            self.manager.config.data.get("discord_community_id", ""),
            self._discord_linked(),
        )

        if kind == TARGET_URL:

            self._open_url(value)

            return

        self.openSettingsSection.emit(value)

    def _discord_linked(self) -> bool:

        store = getattr(self.manager, "discord_account", None)

        if store is None:
            return False

        try:
            account = store.load()

        except Exception:

            #
            # Eine unlesbare discord_account.json ist kein Grund, den
            # Knopf wirkungslos zu lassen - "nicht verknüpft" führt in
            # die Einstellung, wo das Problem behoben wird.
            #

            return False

        return bool(account and account.get("companion_token"))

    def _open_url(self, url: str):
        """
        Über `core.browser.open_url()` - und nicht mehr über ein
        blankes `webbrowser.open()`.

        Das war die Ursache dafür, dass dieser Knopf nichts tat: im
        AppImage erbt der Browser sonst unser eigenes
        `LD_LIBRARY_PATH` und stirbt beim Start, ohne dass hier eine
        Ausnahme ankommt. Die beiden anderen Aufrufer im Programm
        hatten den Schutz, dieser eine nicht.
        """

        open_url(url, self.manager.logger)

    # --------------------------------------------------
    # Updates
    # --------------------------------------------------

    def set_update_runner(self, runner):
        """
        Duck-getypt vom MainWindow gesetzt (`_ensure_page`).

        **Ein** Läufer für die ganze Anwendung, nicht einer je Seite:
        sonst könnte hier ein Addon-Update starten, während die Seite
        "Addon & Updates" nichts davon weiß und ein zweites anwirft.
        """

        self._runner = runner

        runner.started.connect(self._on_update_started)

        runner.finished.connect(self._on_update_finished)

    def _start_update(self, component: str):

        if self._runner is None:
            return

        if component == ADDON:

            self._runner.install_addon()

            return

        self._runner.update_companion()

    def _open_changelog(self, component: str):

        show_changelog(self.manager.state, component, self)

    def _on_update_started(self, component: str):

        row = self.updates.rows.get(component)

        if row is None:
            return

        row.set_running(
            True,
            "Wird heruntergeladen und installiert …"
            if component == COMPANION
            else "Wird heruntergeladen - vorher wird eine Sicherung "
            "angelegt.",
        )

    def _on_update_finished(self, component: str, success: bool, message: str):

        row = self.updates.rows.get(component)

        if row is not None:

            row.set_running(
                False,
                message if not success else "",
            )

        #
        # Nach einem Addon-Update sind Fassung und Zustand andere -
        # die Seite zeichnet sich deshalb neu, statt auf den nächsten
        # Seitenwechsel zu warten.
        #

        if success:
            self.refresh()

    def _refresh_updates(self):
        """
        Die Karte an den Zustand anlegen.

        Der Auszug kommt aus `core/changelog_source.py` und damit aus
        derselben Quelle wie die vollständige Ansicht - was hier in
        drei Zeilen steht, findet sich dort wieder.
        """

        state = self.manager.state

        pending = []

        if state.update_available:

            pending.append((
                ADDON,
                state.addon_version if state.addon_found else "",
                state.github_version,
            ))

        if state.companion_update_available:

            pending.append((
                COMPANION,
                state.companion_version,
                state.companion_latest_version,
            ))

        self.updates.setVisible(bool(pending))

        if not pending:
            return

        self.updates.setCount(len(pending))

        waiting = {component for component, _i, _a in pending}

        for component, installed, available in pending:

            row = self.updates.rows[component]

            row.setVisible(True)

            entry = latest_entry(component, state)

            row.apply(
                LABELS[component],
                installed,
                available,
                _excerpt(entry),
            )

        for component, row in self.updates.rows.items():

            if component not in waiting:
                row.setVisible(False)

    # --------------------------------------------------

    def _schedule(self):
        """
        Der zuletzt bekannte Raidtermin.

        Über `getattr`, weil `refresh()` auch aus Tests und aus dem
        Aufbau der Seite heraus läuft, wo der Manager ein einfacher
        Platzhalter sein kann.
        """

        sync = getattr(self.manager, "raid_schedule_sync", None)

        if sync is None:
            return None

        return sync.schedule

    def _refresh_countdown(self):
        """
        Nur den Chip - läuft einmal pro Minute.
        """

        schedule = self._schedule()

        day = schedule.next_day() if schedule is not None else None

        text = countdown_text(day)

        self.countdown.setText(text)

        self.countdown.setVariant(
            "neutral"
            if day is None
            else "ok" if day.is_running() else "accent"
        )

    def on_enter(self):

        self._clock.start()

    def on_leave(self):

        self._clock.stop()

    # --------------------------------------------------

    def _open_academy(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ACADEMY)

    def _open_preparation(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.PREPARATION)

    # --------------------------------------------------

    def on_layout_changed(self, state):
        """
        Unter 980 px stehen die beiden Karten untereinander.

        Duck-getypt vom MainWindow aufgerufen, genau wie on_enter und
        on_leave - eine Seite, die nichts umzubauen hat, braucht die
        Methode gar nicht.
        """

        if state.single_column == self._single_column:
            return

        self._single_column = state.single_column

        self.row.removeWidget(self.preparation)

        if state.single_column:

            #
            # Untereinander: die Vorbereitungskarte gibt ihre feste
            # Breite auf, sonst stuende sie schmal und linksbuendig
            # unter einer Karte vollen Ausmasses.
            #

            self.preparation.setMinimumWidth(0)

            self.preparation.setMaximumWidth(16777215)

            self.row.addWidget(self.preparation, 1, 0)

        else:

            self.preparation.setFixedWidth(300)

            self.row.addWidget(self.preparation, 0, 1)

    def refresh(self):

        self.system.refresh()

        self.last_pull.refresh()

        #
        # Der Raidtermin liegt bereits im `RaidScheduleSync` - gelesen
        # wird hier nur, abgerufen wird im Sync-Takt. `refresh()` darf
        # nicht ins Netz gehen (siehe `tests/test_update_visibility.py`).
        #

        schedule = self._schedule()

        day = schedule.next_day() if schedule is not None else None

        self.roster.apply(schedule, day)

        self._refresh_countdown()

        #
        # Der Vorbereitungsstand kommt aus der Charakterliste, nicht
        # aus einem Netzwerkabruf - `refresh()` darf nur zeichnen
        # (siehe `tests/test_update_visibility.py`).
        #

        store = getattr(self.manager, "characters", None)

        if store is not None:
            self.preparation.apply(store.preparation_summary())

        self._refresh_updates()

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
