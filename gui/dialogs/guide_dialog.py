"""
Der Wegweiser: was ist WeintTV, was die Academy, was das Archiv - und
was muss man selbst tun?

**Warum es ihn gibt.** Gemeldet wurde: "Viele wissen nicht, inwieweit
man alles überhaupt bedienen muss/kann und wo man was findet." Das ist
keine Geschmacksfrage, sondern ein Befund über drei Bereiche, die sich
unsichtbar einen Zustand teilen: dieselbe Datenquelle, denselben
Snapshot, dieselbe Archivauswahl. Wer das nicht weiss, sieht drei
Seiten, von denen zwei "keine Daten" sagen, und hat keinen Anhaltspunkt,
woran das liegt.

Die Einführungstour (`whats_new_dialog.py`) erklärt jeden Bereich
einmal - beim ersten Start, und danach nie wieder von selbst. Das ist
der richtige Ort für "was gibt es hier alles", aber der falsche für
"was mache ich jetzt": eine Tour findet man nicht wieder, wenn man
gerade vor der Frage steht. Dieser Dialog steht deshalb als Knopf auf
jeder der drei Seiten.

Zwei Regeln, beide aus derselben Haltung wie `analysis_gap.py`:

- **Die Texte sind Qt-frei und liegen in `core/analysis_guide.py`.**
  Was die App über sich selbst sagt, ist eine Auskunft und keine
  Darstellung - und drei Seiten, die dieselbe Frage verschieden
  beantworten, sind genau der Zustand, den dieser Dialog beheben soll.
- **Der Dialog behauptet nichts über den eigenen Stand.** Er sagt, was
  ein Bereich beantwortet und was er dafür braucht. Ob die Quelle
  gerade Daten liefert, steht in der Quellenzeile auf der Seite -
  dort, wo man es ändern kann.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.analysis_guide import GUIDE_INTRO, GUIDE_SECTIONS

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.wrapped_label import enable_wrap


class GuideDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Wegweiser")

        self.setModal(True)

        self.resize(720, 640)

        self.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self,
            f"""
            QDialog{{
                background:{tokens.SURFACE["base"]};
                border:1px solid {tokens.BORDER["base"]};
                border-radius:{tokens.RADIUS["lg"]}px;
            }}
            """,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(28, 24, 28, 20)

        root.setSpacing(14)

        # --------------------------------------------------
        # Kopf
        # --------------------------------------------------

        root.addWidget(eyebrow_label("WEGWEISER"))

        title = QLabel("WeintTV, Academy und Archiv")

        title.setFont(font("title"))

        restyle(title, f"color:{tokens.WHITE};background:transparent;")

        root.addWidget(title)

        intro = enable_wrap(QLabel(GUIDE_INTRO))

        intro.setFont(font("body"))

        restyle(
            intro,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(intro)

        # --------------------------------------------------
        # Die Bereiche
        # --------------------------------------------------

        body = QWidget()

        column = QVBoxLayout(body)

        column.setContentsMargins(0, 0, 12, 0)

        column.setSpacing(tokens.SPACE[3])

        for section in GUIDE_SECTIONS:
            column.addWidget(self._section(section))

        column.addStretch(1)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        restyle(scroll, "QScrollArea{background:transparent;border:none;}")

        scroll.setWidget(body)

        root.addWidget(scroll, 1)

        # --------------------------------------------------
        # Fuss
        # --------------------------------------------------

        footer = QHBoxLayout()

        footer.addStretch(1)

        close_button = HeroButton("Verstanden", primary=True)

        close_button.clicked.connect(self.accept)

        footer.addWidget(close_button)

        root.addLayout(footer)

    # --------------------------------------------------

    def _section(self, section) -> QWidget:
        """
        Ein Bereich: Name, wofür er da ist, was man dort tut, was er
        dafür braucht.

        Die drei Zeilen sind bewusst immer dieselben drei Fragen. Ein
        Abschnitt, der einmal "Voraussetzung" nennt und beim nächsten
        nicht, liest sich wie eine Ausnahme, wo keine ist.
        """

        wrap = QWidget()

        layout = QVBoxLayout(wrap)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(4)

        layout.addWidget(eyebrow_label(section.eyebrow))

        name = QLabel(section.title)

        name.setFont(font("section"))

        restyle(name, f"color:{tokens.WHITE};background:transparent;")

        layout.addWidget(name)

        for label, text in (
            ("Wofür", section.purpose),
            ("Was du tust", section.actions),
            ("Was es braucht", section.needs),
        ):

            layout.addWidget(self._line(label, text))

        return wrap

    def _line(self, label: str, text: str) -> QWidget:

        wrap = QWidget()

        layout = QHBoxLayout(wrap)

        layout.setContentsMargins(0, 2, 0, 2)

        layout.setSpacing(tokens.SPACE[2])

        key = QLabel(label)

        key.setFont(font("small"))

        key.setFixedWidth(110)

        key.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        restyle(
            key,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        layout.addWidget(key)

        value = enable_wrap(QLabel(text))

        value.setFont(font("small"))

        restyle(
            value,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        layout.addWidget(value, 1)

        return wrap
