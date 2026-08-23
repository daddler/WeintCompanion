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

import threading

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

from core.backend_config import TARGET_URL, app_url, roster_target
from core.browser import open_url
from core.changelog_reader import format_changelog_body
from core.changelog_source import ADDON, COMPANION, LABELS, latest_entry
from core.greeting import greeting, headline
from core.last_pull import (
    LastPull,
    from_history,
    result_text,
    source_text,
    when_text,
)
from core.platform import is_linux
from core.raid_schedule import (
    ROLE_LABELS,
    ROLE_ORDER,
    composition_text,
    count_text,
    countdown_text,
    day_text,
    open_slots,
    others_text,
    own_signup_label,
    own_signup_text,
    own_signup_variant,
    signup_text,
)
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
from gui.widgets.roster_strip import RosterStrip, SlotGroup
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


def _slot_groups(schedule, day) -> list[SlotGroup]:
    """
    Die Reihen des Aufstellungsstreifens.

    Drei Fälle, und sie unterscheiden sich in dem, was der Bot
    geliefert hat - nicht in dem, was die Karte gerne hätte:

    - **Rollen gemeldet**: eine Reihe je Rolle, gefüllt mit den
      Klassen der Zusagen, dahinter die fehlenden Plätze dieser Rolle
      (nur wenn eine Sollstärke gemeldet ist). Was danach noch offen
      ist, steht als eigene Reihe "FREI" - die Sollstärke sagt, wie
      viele Heiler gebraucht werden, nicht, wie der letzte Platz zu
      besetzen ist.
    - **Nur Zahlen**: ein einziger Streifen "ZUGESAGT". Drei Reihen
      aus einer Gesamtzahl zu schätzen wäre in der Anzeige von einer
      gemeldeten Aufstellung nicht zu unterscheiden.
    - **Keine Raidgröße und keine Zusage**: gar kein Streifen. Ein
      leerer Rahmen ohne einen einzigen Platz ist kein Bild, sondern
      ein Ladefehler.
    """

    if day is None:
        return []

    size = int(getattr(schedule, "raid_size", 0) or 0)

    total_open, missing, free = open_slots(schedule, day)

    if day.has_roles():

        groups = []

        for role in ROLE_ORDER:

            filled = [
                slot.class_name
                for slot in day.roster
                if slot.role == role
            ]

            gap = missing.get(role, 0)

            if not filled and not gap:
                continue

            groups.append(
                SlotGroup(
                    label=ROLE_LABELS[role],
                    filled=filled,
                    open_slots=gap,
                )
            )

        if free:

            groups.append(SlotGroup(label="FREI", open_slots=free))

        return groups

    if not day.active and not size:
        return []

    #
    # Ohne Rollen: ein Streifen. Die gefüllten Plätze tragen keine
    # Klasse und erscheinen deshalb in Akzentfarbe.
    #

    return [
        SlotGroup(
            label="ZUGESAGT",
            filled=[""] * day.active,
            open_slots=total_open,
        )
    ]


class DayBlock(QWidget):
    """
    Ein Termin des Raids: Zeile, Zahl, Streifen, Satz.

    **Warum es diesen Block gibt.** Der Standardraid laeuft Mittwoch
    *und* Donnerstag, und die beiden Anmeldungen sind zwei verschiedene
    Listen - wer am Mittwoch zusagt, muss am Donnerstag nicht koennen.
    Die Karte nannte aber nur den naechsten Termin: am Dienstag also
    den Mittwoch, waehrend der Donnerstag daneben leer sein konnte,
    ohne dass es in der App zu sehen war. Der Bot schickt beide Tage in
    derselben Antwort, sie standen nur nie auf dem Bildschirm.

    Die Zahl sitzt in der Zeile ueber *ihrem* Streifen und nicht mehr
    im Kopf der Karte: mit zwei Tagen gehoert "21 / 25" zu einem von
    beiden, und im Kopf waere nicht zu sehen, zu welchem.

    Aus demselben Grund steht auch die **eigene Anmeldung** hier und
    nicht im Kopf: der Chip neben dem Datum sagt, ob man selbst fuer
    diesen Tag zugesagt, abgesagt oder noch gar nicht geantwortet hat.
    "21 von 25 zugesagt" beantwortet diese Frage nicht - die Antwort
    des Bots nennt bewusst keine Namen, es ist aus ihr also gar nicht
    zu erkennen, wer von den 21 man selbst ist. Sie kommt deshalb als
    eigenes Feld je Tag (`days[].me`, siehe `core/raid_schedule.py`).
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(4)

        head = QHBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(tokens.SPACE[1])

        self.when = QLabel("")

        self.when.setFont(font("body"))

        restyle(
            self.when,
            f"color:{tokens.TEXT['primary']};background:transparent;",
        )

        head.addWidget(self.when)

        #
        # Der eigene Anmeldezustand, direkt neben dem Datum: er
        # gehört zu **diesem** Tag und nicht zum Raid. Mittwoch und
        # Donnerstag sind zwei Anmeldungen, und ein Hinweis im Kopf
        # der Karte müsste offenlassen, welchen der beiden er meint -
        # dieselbe Überlegung, die die Zahl der Zusagen aus dem Kopf
        # in die Tageszeile geholt hat.
        #
        # Unsichtbar, solange der Bot nichts dazu meldet: kein Chip
        # heisst "dazu ist nichts bekannt", und das ist etwas anderes
        # als "nicht angemeldet".
        #

        self.own = Chip("", "neutral")

        self.own.setVisible(False)

        head.addWidget(self.own)

        head.addStretch(1)

        self.count = QLabel("")

        self.count.setFont(font("small"))

        restyle(
            self.count,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        head.addWidget(self.count)

        root.addLayout(head)

        self.strip = RosterStrip()

        self.strip.setVisible(False)

        root.addSpacing(tokens.SPACE[0])

        root.addWidget(self.strip)

        self.note = QLabel("")

        self.note.setFont(font("small"))

        enable_wrap(self.note)

        restyle(
            self.note,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(self.note)

    # --------------------------------------------------

    def apply(self, schedule, day):

        self.when.setText(day_text(day))

        label = own_signup_label(day)

        self.own.setText(label)

        self.own.setVariant(own_signup_variant(day))

        #
        # Der ganze Satz hängt am Chip: "NICHT ANGEMELDET" ist die
        # kurze Fassung, "Deine Anmeldung für diesen Tag fehlt noch."
        # die, in der die Frage gestellt wird.
        #

        self.own.setToolTip(own_signup_text(day))

        self.own.setVisible(bool(label))

        self.count.setText(count_text(day, schedule.raid_size))

        groups = _slot_groups(schedule, day)

        self.strip.setGroups(groups)

        self.strip.setVisible(bool(groups))

        text = _day_note(schedule, day, bool(groups))

        self.note.setText(text)

        self.note.setVisible(bool(text))


def _day_note(schedule, day, has_strip: bool) -> str:
    """
    Der Satz unter einem Streifen.

    Mit Streifen sagt er, **was** fehlt (die Zahl steht schon in der
    Zeile darueber); ohne Streifen bleibt es bei der alten Zeile mit
    der Zahl, sonst stuende unter dem Termin gar nichts. "Vielleicht"
    und "Ersatzbank" haengen in beiden Faellen hinten dran - sie
    gehoeren neben die Zusagen, nicht hinein.

    Dass die Anmeldung geschlossen ist, steht hier **nicht**: das gilt
    fuer den Raid und nicht fuer einen seiner Tage, und zweimal
    untereinander gelesen sieht es aus wie zwei verschiedene Auskuenfte.
    Es steht im Kopf der Karte.
    """

    parts = []

    if has_strip:

        parts.append(composition_text(schedule, day))

        if day.tentative:
            parts.append(f"{day.tentative} vielleicht")

        if day.bench:
            parts.append(f"{day.bench} Ersatzbank")

    else:

        parts.append(signup_text(day, schedule.raid_size))

    return " · ".join(part for part in parts if part)


class RosterCard(Card):
    """
    Der nächste Raid: Termin, Titel, **Aufstellung**.

    **Was sich hier geändert hat.** Bis 2.0.1 stand an dieser Stelle
    "Zusagen und Rollen sind der App nicht bekannt", und das stimmte:
    der Roster erreicht die Companion als zwei undurchsichtige
    WCIMPORT-Zeichenketten (`core/discord_roster_sync.py`), die
    ungeparst ans Addon weitergehen - und die bekommt ohnehin nur, wer
    die Raidlead-Rolle trägt.

    Der Bot beantwortet die Frage jetzt eigens
    (`/companion/raid-schedule`, für jeden verknüpften Nutzer). Seit
    2.0.7 steht hier die Aufstellung so, wie sie im Entwurf der
    Übersicht stand: je Rolle eine Reihe Plätze, gefüllte in
    Klassenfarbe, offene als Lücke, darunter ein Satz, was noch fehlt.
    "10 von 25" ist die Zahl; die Frage vor einem Raid ist aber, *wer*
    fehlt - vier offene Plätze sind harmlos, wenn es Schaden ist, und
    ein Abend ohne Raid, wenn es der zweite Tank ist.

    Was weiterhin **nicht** hier steht, ist die Namensliste: der
    Endpunkt liefert Rolle und Klasse, niemals einen Namen. Beides
    steht als Symbol im Anmelde-Beitrag, den jeder im Kanal lesen
    kann; die Namen bleiben hinter der Raidlead-Rolle. Wer sie sehen
    will, geht über den Knopf ins Discord.

    Seit 2.3.4 zeigt sie **jeden noch bevorstehenden Termin**, nicht
    nur den naechsten: der Standardraid laeuft Mittwoch und
    Donnerstag, und das sind zwei Anmeldungen - wer am Mittwoch zusagt,
    muss am Donnerstag nicht koennen. Der Bot schickte beide Tage von
    Anfang an in derselben Antwort; hier stand nur einer davon, und ob
    der zweite ueberhaupt Leute hatte, war in der App nicht zu sehen.
    Jeder Tag ist ein `DayBlock` mit eigener Zahl, eigenem Streifen und
    eigenem Satz.

    Ohne Antwort bleibt die alte Haltung unverändert: die Karte sagt,
    dass nichts bekannt ist, statt "0 von 25" zu behaupten. Eine Null
    wäre keine Untertreibung, sondern eine falsche Messung - niemand
    hat gezählt. Und meldet der Bot den Termin, aber keine Rollen
    (ältere Fassung), steht dort ein einziger Streifen "zugesagt"
    statt drei geschätzter.
    """

    def __init__(self, parent=None):

        super().__init__(parent=parent)

        self.setMinimumHeight(170)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[1])

        header.addWidget(eyebrow_label("AUFSTELLUNG"))

        header.addStretch(1)

        #
        # Rechts im Kopf steht, was fuer den **Raid** gilt und nicht
        # fuer einen seiner Tage: dass die Anmeldung geschlossen ist.
        # Die Zahl der Zusagen sass hier, solange die Karte einen
        # einzigen Termin zeigte; mit Mittwoch und Donnerstag
        # untereinander gehoert sie in die Zeile ihres Tages, sonst
        # ist nicht zu sehen, welchen von beiden sie meint.
        #

        self.status = QLabel("")

        self.status.setFont(font("small"))

        restyle(
            self.status,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        self.status.setVisible(False)

        header.addWidget(self.status)

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

        #
        # Je Termin ein Block. Sie werden einmal gebaut und danach nur
        # noch beschriftet - dieselbe Regel wie bei den Zeilen unter
        # `gui/widgets/tv/`: ein Neubau bei jedem `refresh()` waere
        # Arbeit fuer ein Bild, das sich meist gar nicht aendert.
        #

        self.days = QVBoxLayout()

        self.days.setContentsMargins(0, 0, 0, 0)

        self.days.setSpacing(tokens.SPACE[3])

        self._blocks: list[DayBlock] = []

        text.addSpacing(tokens.SPACE[1])

        text.addLayout(self.days)

        self.explanation = QLabel(
            "Sobald im Discord ein Termin steht, erscheint er hier - "
            "mit Datum, Uhrzeit und der Aufstellung."
        )

        self.explanation.setFont(font("small"))

        enable_wrap(self.explanation)

        restyle(
            self.explanation,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        text.addWidget(self.explanation)

        #
        # Die weiteren gleichzeitig laufenden Raids. Eigene Zeile und
        # nicht angehängt an die Erklärung darüber: die spricht über
        # DIESEN Termin (was fehlt, wie viele zugesagt haben), und ein
        # zweiter Raid gehört nicht in denselben Satz. Unsichtbar,
        # solange nur einer läuft - das ist der Normalfall.
        #

        self.parallel = QLabel("")

        self.parallel.setFont(font("small"))

        enable_wrap(self.parallel)

        restyle(
            self.parallel,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.parallel.setVisible(False)

        text.addWidget(self.parallel)

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

    def apply(self, schedule, days):
        """
        `schedule` ist ein `RaidSchedule`, `days` seine noch
        bevorstehenden Termine (`upcoming_days()`), der naechste zuerst.

        Beim Standardraid sind das **zwei**: Mittwoch und Donnerstag
        stehen untereinander, jeder mit seiner eigenen Zahl, seinem
        eigenen Streifen und seinem eigenen Satz. Sie sind zwei
        Anmeldungen und keine zwei Ansichten derselben - eine
        gemeinsame Zahl haette den Donnerstag hinter dem Mittwoch
        verschwinden lassen, und genau darum geht es hier.

        Beides kann leer sein - dann steht wieder da, dass nichts
        bekannt ist. Der Zustand "es gibt einen Raid, aber alle
        Termine liegen hinter uns" ist davon nicht zu trennen und
        bekommt deshalb dieselbe Auskunft.
        """

        days = list(days or [])

        if not getattr(schedule, "known", False) or not days:

            self.title.setVisible(False)

            self._show_days(0)

            self.explanation.setText(
                "Sobald im Discord ein Termin steht, erscheint er "
                "hier - mit Datum, Uhrzeit und der Aufstellung."
            )

            self.explanation.setVisible(True)

            self.status.setVisible(False)

            self.parallel.setVisible(False)

            return

        self.title.setText(schedule.title)

        self.title.setVisible(True)

        for block, day in zip(self._blocks_for(len(days)), days):
            block.apply(schedule, day)

        self._show_days(len(days))

        #
        # Die Erklaerung darunter ist jetzt allein der Platzhalter fuer
        # "nichts bekannt" - was zu einem Termin zu sagen ist, sagt
        # sein eigener Block.
        #

        self.explanation.setVisible(False)

        geschlossen = schedule.signup_status == "locked"

        self.status.setText("Anmeldung geschlossen" if geschlossen else "")

        self.status.setVisible(geschlossen)

        weitere = others_text(schedule)

        self.parallel.setText(weitere)

        self.parallel.setVisible(bool(weitere))

    # --------------------------------------------------

    def _blocks_for(self, count: int) -> list[DayBlock]:
        """
        So viele Bloecke, wie Termine anstehen - fehlende werden
        angelegt, ueberzaehlige bleiben stehen und werden versteckt.

        Weggeworfen wird keiner: ein Raid hat heute zwei Termine, und
        morgen wieder, und ein Widget je Durchgang neu zu bauen kostet
        Layout fuer ein Bild, das gleich bleibt.
        """

        while len(self._blocks) < count:

            block = DayBlock()

            self._blocks.append(block)

            self.days.addWidget(block)

        return self._blocks

    def _show_days(self, count: int):

        for index, block in enumerate(self._blocks):
            block.setVisible(index < count)


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

    **Woher er kommt, und warum das eine Korrektur war.** Bis 2.0.6
    las diese Karte allein `RaidDataService.history()`. Die füllt sich
    aber ausschließlich mit Pulls, die *in dieser Sitzung* endeten,
    während WeintTV oder die Academy offen waren - nach jedem Neustart
    ist sie leer. Am Tag nach einem Raidabend stand hier deshalb "Noch
    kein Pull", und das war keine vorsichtige Auskunft, sondern eine
    falsche: der Kampf hat stattgefunden, die App hat nur an der
    falschen Stelle nachgesehen.

    Seit 2.0.7 ist die Sitzung nur noch die erste von zwei Quellen.
    Findet sich dort nichts, tritt der letzte Pull aus dem
    WarcraftLogs-Archiv an ihre Stelle (`core/last_pull_sync.py`),
    abgeholt im gewöhnlichen Sync-Takt und zwischengespeichert. Die
    Reihenfolge ist Absicht: ein Pull, der gerade eben endete, ist der
    letzte, auch wenn WarcraftLogs ihn noch nicht kennt.

    Was ein Pull aus dem Archiv **nicht** mitbringt, ist die
    Bewertung: dafür müsste der ganze Kampf geladen werden, und das
    kostet den Bot Minuten. Die Sternreihe bleibt dann leer und die
    Lektionskarte sagt, wo die Auswertung zu haben ist - statt einen
    schwächsten Bereich zu nennen, den niemand gemessen hat.
    """

    academyRequested = Signal()

    def __init__(self, parent=None):

        super().__init__(parent=parent)

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

    def apply(self, pull):
        """
        `pull` ist ein `LastPull` - aus der Sitzung oder aus dem
        Archiv, die Karte behandelt beide gleich.

        Der Leerzustand ist der Fall "es gibt wirklich keinen": kein
        Pull in dieser Sitzung, kein Bericht beim Bot, kein
        Zwischenspeicher. Er sagt weiterhin, woran es liegt.
        """

        if pull is None or not pull.known:

            self.timestamp.setText("")

            self.boss.setText("Noch kein Pull")

            self.result.setText(
                "Sobald ein Kampf endet, steht sein Ergebnis hier."
            )

            self.sparkline.setValues([])

            self.lesson_title.setText("Die Academy schlägt sie vor.")

            self.lesson_reason.setText(
                "Nach dem ersten ausgewerteten Pull steht hier, woran "
                "zu arbeiten sich am meisten lohnt - mit den "
                "Messwerten, aus denen sich das ergibt."
            )

            return

        self.timestamp.setText(when_text(pull))

        self.boss.setText(pull.boss or "Kampf")

        self.result.setText(result_text(pull))

        #
        # Die Kurve zeigt den geschafften Bossanteil der letzten
        # Versuche an demselben Boss - die eine Linie, die "wird es
        # besser?" beantwortet.
        #

        self.sparkline.setValues(list(pull.trend))

        if pull.live:

            self.lesson_title.setText("Die Academy schlägt sie vor.")

            self.lesson_reason.setText(
                "Der Pull ist ausgewertet - in der Academy steht, "
                "woran zu arbeiten sich am meisten lohnt, mit den "
                "Messwerten, aus denen sich das ergibt."
            )

            return

        #
        # Ein Pull aus dem Archiv ist nicht ausgewertet, und das steht
        # hier auch so. Ein "schwächster Bereich" ohne Auswertung wäre
        # geraten, und die leere Sternreihe daneben sähe ohne diesen
        # Satz wie ein Urteil aus.
        #

        source = source_text(pull)

        self.lesson_title.setText("Dieser Pull ist noch nicht bewertet.")

        self.lesson_reason.setText(
            f"Er stammt aus dem Archiv ({source}). Öffne ihn in der "
            "Academy unter \"Archiv\", um Bewertung und Lektion dazu "
            "zu bekommen - die vollständige Auswertung eines Pulls "
            "holt der Bot erst auf Anforderung."
        )


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

            #
            # Gemeldet, aber nur Twinks: dann fehlt keine Meldung,
            # sondern eine Höchststufe. Der allgemeine Satz schickte
            # hier jemanden das Addon prüfen, an dem nichts ist.
            #

            hidden = summary.get("hidden", 0)

            if hidden and not summary.get("characters"):

                self.note.setText(
                    f"Bisher {'hat' if hidden == 1 else 'haben'} sich "
                    f"nur {hidden} Charakter{'e' if hidden != 1 else ''} "
                    f"unter Höchststufe gemeldet - geprüft werden die, "
                    f"mit denen du in den Raid gehst."
                )

                return

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

    #
    # Das Ende der Update-Prüfung kommt aus einem Hintergrund-Thread
    # zurück in den Hauptthread - der Knopf ist ein Widget und darf
    # von dort nicht angefasst werden (dieselbe Regel wie bei
    # `CompanionManager.state_changed`).
    #

    checkFinished = Signal()

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            greeting(),
            "Willkommen zurück.",
            parent,
        )

        self.service = manager.raid_data

        #
        # "Erneut prüfen" - derselbe Knopf wie unter "Addon &
        # Updates". Er steht hier, weil die Übersicht die Seite ist,
        # auf der ein wartendes Update angekündigt wird (Karte,
        # Systemzeile, Abzeichen): wer dort nachsehen will, ob
        # inzwischen etwas dazugekommen ist, musste dafür bisher die
        # Seite wechseln.
        #

        self.check_button = QPushButton("Erneut prüfen")

        self.check_button.setObjectName("secondary")

        self.check_button.setCursor(Qt.PointingHandCursor)

        self.check_button.clicked.connect(self.check_updates)

        self.header.addAction(self.check_button)

        self._check_thread = None

        self.checkFinished.connect(self._on_check_finished)

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
        # Derselbe Takt trägt die Begrüßung: "Morgen ist Raid" wird um
        # Mitternacht zu "Heute", und "Guten Tag" um 18 Uhr zu "Guten
        # Abend". Beides ohne Zutun - eine Anwendung, die den ganzen
        # Abend offen steht, soll nicht mit dem Nachmittag im Kopf
        # dastehen.
        #
        # Der Zeitgeber läuft nur, solange die Seite sichtbar ist -
        # `on_enter`/`on_leave` schalten ihn, wie WeintTV und die
        # Academy es mit dem Datenstrom halten.
        #

        self._clock = QTimer(self)

        self._clock.setInterval(60_000)

        self._clock.timeout.connect(self._tick)

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

        self.last_pull = LastPullCard()

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

        Welches der möglichen Ziele es ist, entscheidet
        `core.backend_config.roster_target()` - dort ohne Qt und
        deshalb ohne Fenster prüfbar. Hier bleibt nur das Ausführen.

        Den Fundort der Anmeldung nennt der Bot mit dem Termin
        (`/companion/raid-schedule`); damit landet der Knopf im
        Anmelde-Beitrag statt auf dem Standardkanal des Servers.
        """

        schedule = self._schedule()

        kind, value = roster_target(
            self.manager.config.data.get("discord_community_id", ""),
            self._discord_linked(),
            getattr(schedule, "signup", None),
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

        Ein Discord-Link geht zuerst an die Discord-Anwendung: im
        Browser landete man in einer zweiten, meist abgemeldeten
        Ansicht desselben Servers, während die Anwendung daneben
        offen stand. Gibt es für das Schema kein Programm, übernimmt
        weiterhin der Browser (siehe `core/browser.py`).
        """

        open_url(url, self.manager.logger, app_url(url))

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

    def _tick(self):
        """
        Der Minutentakt: Countdown und Begrüßung.

        Beides hängt allein an der Uhr und liest keine neuen Daten -
        was hier passiert, ist Zeichnen und nichts sonst.
        """

        self._refresh_countdown()

        self._refresh_greeting()

    def _user_name(self) -> str:
        """
        Wen die Anwendung grüßt.

        Erste Wahl ist der **im Spiel angemeldete Charakter**: den
        meldet das Addon seit WeintCodex 1.3.3.0 von sich aus (siehe
        `core/character_report_sync.py`) und er ist die einzige
        Antwort, die niemand geraten hat. Bewusst *nicht*
        `academy_player_name` - das ist die Auswahl der Academy und
        kann auf einem Kollegen stehen, dessen Zahlen man sich einmal
        angesehen hat.

        Danach der Discord-Name, der ohnehin unten in der Navigation
        steht. Ist auch der nicht bekannt, grüßt die App ohne Namen,
        statt sich einen zu suchen.
        """

        config = getattr(self.manager, "config", None)

        if config is not None:

            name = str(
                config.data.get("academy_ingame_character", "") or ""
            ).strip()

            if name:
                return name

        store = getattr(self.manager, "discord_account", None)

        if store is not None:

            try:
                account = store.load()

            except Exception:

                #
                # Eine unlesbare discord_account.json ist kein Grund,
                # gar nicht mehr zu grüßen.
                #

                account = None

            if account:

                name = str(account.get("username", "") or "").strip()

                if name:
                    return name

        state = getattr(self.manager, "state", None)

        name = str(getattr(state, "discord_name", "") or "").strip()

        #
        # "-" ist der Anfangswert von `AppState.discord_name` und
        # heißt "nicht bekannt", nicht "so heißt der Nutzer".
        #

        return "" if name in ("", "-") else name

    def _refresh_greeting(self):
        """
        Rubrik und Titel - die beiden Zeilen im Kopf.

        Welcher Satz dasteht, entscheidet `core/greeting.py`; hier
        wird er nur gesetzt. Die Trennung ist dieselbe wie bei
        `roster_target()`: die Entscheidung ist prüfbar, ohne ein
        Fenster zu bauen.
        """

        schedule = self._schedule()

        day = schedule.next_day() if schedule is not None else None

        state = self.manager.state

        self.header.setEyebrow(greeting(self._user_name()))

        self.header.setTitle(
            headline(
                day,
                addon_update=state.update_available,
                app_update=state.companion_update_available,
                wow_found=state.wow_found,
            )
        )

    # --------------------------------------------------
    # Erneut nach Updates sehen
    # --------------------------------------------------

    def check_updates(self):
        """
        Beide Update-Kanäle noch einmal gegen GitHub prüfen.

        In einem eigenen kurzlebigen Thread - wie bei
        `ConnectionsPage.sync_now()` und den Archiv-Abrufen. Die
        Prüfung geht zweimal ins Netz, und das gehört nicht in einen
        Klick-Handler: das Fenster stünde für die Dauer still.

        Die Anzeige zieht danach von selbst nach, weil
        `refresh_update_status()` am Ende `state_changed` meldet und
        das Fenster daraufhin die sichtbare Seite neu zeichnet - hier
        wird deshalb nichts direkt aktualisiert.
        """

        if self._check_thread is not None and self._check_thread.is_alive():

            #
            # Zweimal drücken soll nicht zwei Durchgänge starten.
            #

            return

        self.manager.logger.info("Prüfe GitHub auf neue Versionen...")

        self.check_button.setEnabled(False)

        self.check_button.setText("Wird geprüft …")

        self._check_thread = threading.Thread(
            target=self._check_worker,
            daemon=True,
            name="OverviewUpdateCheck",
        )

        self._check_thread.start()

    def _check_worker(self):

        try:

            self.manager.refresh_update_status()

            self.manager.logger.success("GitHub erfolgreich geprüft.")

        except Exception as exc:

            self.manager.logger.error(
                f"Update-Prüfung fehlgeschlagen: {exc}"
            )

        finally:

            self.checkFinished.emit()

    def _on_check_finished(self):

        self.check_button.setEnabled(True)

        self.check_button.setText("Erneut prüfen")

    # --------------------------------------------------

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

    def _last_pull(self) -> LastPull:
        """
        Der letzte Pull - erst die Sitzung, dann das Archiv.

        Die Reihenfolge ist die Aussage: was gerade eben endete, ist
        der letzte Kampf, auch wenn WarcraftLogs ihn noch nicht kennt.
        Das Archiv ist der Rückfall für alles davor - und der Grund,
        warum hier nicht mehr "Noch kein Pull" steht, nur weil die App
        seit dem Raid einmal neu gestartet wurde.

        Über `getattr`, wie `_schedule()`: `refresh()` läuft auch aus
        Tests und aus dem Aufbau der Seite heraus, wo der Manager ein
        einfacher Platzhalter sein kann.
        """

        live = from_history(self.service.history())

        if live.known:
            return live

        sync = getattr(self.manager, "last_pull_sync", None)

        pull = getattr(sync, "pull", None)

        return pull if pull is not None else LastPull()

    def refresh(self):

        self.system.refresh()

        self.last_pull.apply(self._last_pull())

        #
        # Der Raidtermin liegt bereits im `RaidScheduleSync` - gelesen
        # wird hier nur, abgerufen wird im Sync-Takt. `refresh()` darf
        # nicht ins Netz gehen (siehe `tests/test_update_visibility.py`).
        #

        schedule = self._schedule()

        #
        # Alle noch bevorstehenden Termine, nicht nur der naechste:
        # Mittwoch und Donnerstag sind zwei Anmeldungen, und wer am
        # Dienstag hinsieht, will beide sehen. Der Countdown im Kopf
        # bleibt beim naechsten - er hat genau einen Platz.
        #

        days = schedule.upcoming_days() if schedule is not None else ()

        self.roster.apply(schedule, days)

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

        #
        # Zuletzt der Kopf: er fasst zusammen, was die Karten darunter
        # im einzelnen zeigen, und liest dafür denselben Zustand.
        #

        self._refresh_greeting()
