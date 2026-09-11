"""
Der Cooldown-Zeitstrahl: eine Zeile je Fähigkeit, der Kampf als
Achse.

Warum es ihn gibt. Bis 3.6.0 stand die Cooldown-Nutzung als Tabelle
da: "4 von 6", daneben eine Reihe Uhrzeiten als Text
("00:12, 02:44, 05:10"). Beides beantwortet die Frage nicht, die man
davor hat - **wann war die Lücke**. Uhrzeiten im Fliesstext muss man
im Kopf voneinander abziehen und gegen eine Abklingzeit halten, die
nirgends steht.

Hier ist dieselbe Auskunft ein Bild:

* **Ein Balken je Einsatz**, an seiner Stelle im Kampf, so breit wie
  die Abklingzeit lang ist - man sieht auf einen Blick, wie viel vom
  Kampf der Cooldown gedeckt hat.
* **Die Lücken dazwischen** sind die Strecken, auf denen er bereit
  war und nicht kam. Sie kommen aus `analyzer/analysis/cooldowns.py`
  und nicht aus dieser Datei: eine Zeichnung darf nichts ausrechnen,
  was eine Bewertung ebenfalls braucht, sonst gibt es die Lücke
  zweimal und irgendwann verschieden.
* **Das Heldentum-Fenster** liegt als getönte Fläche darüber - die
  Frage "hätte der grosse Cooldown dort hingehört" beantwortet sich
  damit selbst.

Drei Regeln, die nicht Geschmack sind:

* **Ohne bekannte Abklingzeit keine Lücke.** Dann bleibt der Einsatz
  ein schmaler Strich ohne Deckung; eine geschätzte Abklingzeit wäre
  eine erfundene Aussage über verschenkte Zeit.
* **Ein Defensivcooldown bekommt nie eine Lückenmarkierung.** Er
  wartet auf seinen Moment; "bereit und nicht genutzt" ist bei ihm
  kein Befund. Er steht trotzdem hier, weil *wann* er kam die
  interessante Auskunft ist.
* **Akzent und Zustandsfarben werden im `paintEvent` gelesen**, nie
  im Konstruktor, und der ThemeManager bekommt einen gebundenen Slot
  statt einer Lambda (siehe CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import QWidget

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.theme_manager import theme


#
# Masse. Die Zeilenhöhe trägt zwei Zeilen Text (Name, Kennzahl)
# neben dem Strahl; darunter wird die Schrift beschnitten.
#

ROW_HEIGHT = 34

BAR_HEIGHT = 10

LABEL_WIDTH = 168

VALUE_WIDTH = 96

PAD_TOP = 6

AXIS_HEIGHT = 16


#
# Höhe ohne Zeilen: Platz für drei Zeilen Erklärtext.
#

EMPTY_HEIGHT = 72


def clock(seconds: float) -> str:
    """
    Sekunden als MM:SS. Dieselbe Schreibweise wie überall sonst in
    WeintTV.
    """

    seconds = max(0.0, seconds)

    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


@dataclass(frozen=True)
class TimelineRow:
    """
    Eine Zeile des Zeitstrahls.

    Bewusst ein eigener, Qt-freier Wert und nicht der `CooldownUsage`
    selbst: die Zeile trägt bereits die fertige Auskunft (Lücken,
    Beschriftung, ob sie bewertet wird), damit die Seite entscheidet,
    **was** gezeigt wird, und dieses Widget nur noch, **wie**.
    """

    label: str

    casts: tuple[float, ...] = ()

    cooldown: float = 0.0

    gaps: tuple[tuple[float, float], ...] = ()

    value: str = ""

    #
    # `judged` heisst: für diese Zeile gibt es eine Nutzungsquote.
    # Nur dort dürfen Lücken als Versäumnis aussehen.
    #

    judged: bool = True

    tone: str = ""


class CooldownTimeline(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self._rows: tuple[TimelineRow, ...] = ()

        self._duration: float = 0.0

        self._windows: tuple[tuple[float, float], ...] = ()

        self._placeholder = ""

        self.setMinimumHeight(EMPTY_HEIGHT)

        #
        # Gebundener Slot, keine Lambda - der ThemeManager lebt so
        # lange wie das Programm.
        #

        theme().accent_changed.connect(self.update)

    # --------------------------------------------------

    def setPlaceholder(self, text: str):

        if text == self._placeholder:
            return

        self._placeholder = text

        self.update()

    def setTimeline(
        self,
        rows,
        duration: float,
        windows=(),
    ):
        """
        Den ganzen Strahl auf einmal setzen.

        Auf einmal und nicht Zeile für Zeile: die Achse hängt an der
        Kampfdauer, und eine Zeile mit einer anderen Dauer als ihre
        Nachbarn wäre stillschweigend falsch.
        """

        rows = tuple(rows or ())

        windows = tuple(
            (float(start), float(end))
            for start, end in (windows or ())
        )

        duration = max(0.0, float(duration or 0.0))

        unveraendert = (
            rows == self._rows
            and duration == self._duration
            and windows == self._windows
        )

        if unveraendert:
            return

        self._rows = rows

        self._duration = duration

        self._windows = windows

        #
        # Ohne Zeilen steht hier der Erklärtext, und der braucht
        # mehr Platz als eine Zeile Strahl - sonst wird genau die
        # Auskunft abgeschnitten, die sagt, warum nichts da ist.
        #

        self.setMinimumHeight(
            PAD_TOP + AXIS_HEIGHT + len(rows) * ROW_HEIGHT
            if rows
            else EMPTY_HEIGHT
        )

        self.updateGeometry()

        self.update()

    # --------------------------------------------------

    def _x(self, seconds: float, left: float, width: float) -> float:

        if self._duration <= 0:
            return left

        share = max(0.0, min(1.0, seconds / self._duration))

        return left + share * width

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        painter.setFont(font("small"))

        if not self._rows or self._duration <= 0:

            if self._placeholder:

                painter.setPen(QColor(tokens.TEXT["muted"]))

                painter.drawText(
                    QRectF(0, 0, self.width(), self.height()),
                    Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                    self._placeholder,
                )

            return

        left = LABEL_WIDTH

        width = max(1.0, self.width() - LABEL_WIDTH - VALUE_WIDTH)

        akzent = QColor(theme().accent_base())

        #
        # Die Burstfenster zuerst und über die volle Höhe: sie sind
        # der Massstab, an dem die Zeilen gelesen werden, nicht ein
        # Befund je Zeile.
        #

        #
        # Die Höhe kommt aus der Zahl der Zeilen und nicht aus der
        # des Widgets: in einem Layout, das mehr Platz hergibt als
        # gebraucht wird, liefe die getönte Fläche sonst unter der
        # Achse weiter und sähe aus wie ein zweiter Bereich.
        #

        inhalt = len(self._rows) * ROW_HEIGHT

        for start, end in self._windows:

            x1 = self._x(start, left, width)

            x2 = self._x(end, left, width)

            fenster = QColor(tokens.STATE["info"])

            fenster.setAlphaF(0.16)

            painter.fillRect(
                QRectF(x1, PAD_TOP, max(2.0, x2 - x1), inhalt),
                fenster,
            )

        y = PAD_TOP

        for row in self._rows:

            self._paint_row(painter, row, y, left, width, akzent)

            y += ROW_HEIGHT

        self._paint_axis(painter, y, left, width)

    # --------------------------------------------------

    def _paint_row(
        self,
        painter: QPainter,
        row: TimelineRow,
        y: float,
        left: float,
        width: float,
        akzent: QColor,
    ):

        mitte = y + (ROW_HEIGHT - BAR_HEIGHT) / 2

        #
        # Beschriftung links
        #

        painter.setPen(QColor(tokens.TEXT["primary"]))

        painter.drawText(
            QRectF(0, y, LABEL_WIDTH - 10, ROW_HEIGHT),
            Qt.AlignLeft | Qt.AlignVCenter,
            row.label,
        )

        #
        # Die Schiene - der Kampf als Ganzes.
        #

        schiene = QColor(tokens.BORDER["base"])

        painter.fillRect(
            QRectF(left, mitte, width, BAR_HEIGHT),
            schiene,
        )

        #
        # Lücken: bereit und nicht genutzt. Nur dort, wo es eine
        # Quote gibt - sonst sähe Umsicht wie ein Versäumnis aus.
        #

        if row.judged:

            #
            # Schraffiert und nicht einfarbig. Der Grund ist nicht
            # Zierat: der Akzent des Programms ist standardmässig
            # bernsteinfarben, und eine einfarbige Warnfläche daneben
            # war von einem Einsatzbalken nicht zu unterscheiden - man
            # sah zwei gelbe Balken und wusste nicht, welcher wofür
            # steht. Ein Muster unterscheidet sich in *jeder*
            # Akzentfarbe.
            #

            luecke = QColor(tokens.STATE["warn"])

            luecke.setAlphaF(0.75)

            muster = QBrush(luecke, Qt.BDiagPattern)

            grund = QColor(tokens.STATE["warn"])

            grund.setAlphaF(0.14)

            for start, end in row.gaps:

                x1 = self._x(start, left, width)

                x2 = self._x(end, left, width)

                feld = QRectF(x1, mitte, max(2.0, x2 - x1), BAR_HEIGHT)

                painter.fillRect(feld, grund)

                painter.fillRect(feld, muster)

        #
        # Die Einsätze. Breite = Abklingzeit: der Teil des Kampfes,
        # den dieser Einsatz abgedeckt hat. Ohne bekannte Abklingzeit
        # bleibt ein Strich - "gedrückt, Deckung unbekannt".
        #

        farbe = (
            QColor(tokens.STATE[row.tone])
            if row.tone in tokens.STATE and tokens.STATE[row.tone]
            else akzent
        )

        for cast in row.casts:

            x1 = self._x(cast, left, width)

            x2 = (
                self._x(cast + row.cooldown, left, width)
                if row.cooldown > 0
                else x1 + 3
            )

            painter.fillRect(
                QRectF(x1, mitte, max(3.0, x2 - x1), BAR_HEIGHT),
                farbe,
            )

            #
            # Der Anschlag am Einsatzzeitpunkt selbst: bei einer
            # langen Abklingzeit ist der Balken breit, und ohne diese
            # Kante wäre nicht abzulesen, an welchem Ende er beginnt.
            #

            painter.fillRect(
                QRectF(x1, y + 4, 2.0, ROW_HEIGHT - 8),
                farbe,
            )

        #
        # Die Kennzahl rechts.
        #

        if row.value:

            painter.setPen(QColor(tokens.TEXT["secondary"]))

            painter.drawText(
                QRectF(
                    left + width + 8,
                    y,
                    VALUE_WIDTH - 8,
                    ROW_HEIGHT,
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                row.value,
            )

    def _paint_axis(
        self,
        painter: QPainter,
        y: float,
        left: float,
        width: float,
    ):
        """
        Anfang, Mitte, Ende - drei Marken reichen. Eine vollständige
        Achsenbeschriftung würde bei 25 Zeilen mehr Platz kosten, als
        sie an Auskunft bringt.
        """

        painter.setPen(QColor(tokens.TEXT["muted"]))

        painter.setFont(font("micro"))

        for share, ausrichtung in (
            (0.0, Qt.AlignLeft),
            (0.5, Qt.AlignHCenter),
            (1.0, Qt.AlignRight),
        ):

            painter.drawText(
                QRectF(left, y, width, AXIS_HEIGHT),
                ausrichtung | Qt.AlignVCenter,
                clock(self._duration * share),
            )
