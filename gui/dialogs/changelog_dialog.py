"""
Die Änderungsansicht: was sich in welcher Fassung geändert hat.

**Warum sie gebraucht wurde.** Der Changelog war in der App an drei
Stellen zu ahnen und an keiner zu lesen. Auf "Addon & Updates" stand
für WeintCodex "Keine Änderungen gefunden." (die Release-Notes des
Tags waren leer) und für die Companion eine Handvoll Commit-Betreffs -
Text, der für Entwickler geschrieben ist. Das "Was ist neu"-Fenster
zeigt nur die Spanne seit dem letzten Start und ist danach weg. Wer
vor einem Update wissen wollte, was es überhaupt bringt, hatte keinen
Ort dafür.

Diese Ansicht ist dieser Ort: **beide** Komponenten, **alle**
Fassungen, umschaltbar. Die Quellen und ihre Reihenfolge stehen in
`core/changelog_source.py`; hier wird nur gezeichnet.

Ein Dialog und keine Seite in der Navigation: der Changelog wird
gelesen, wenn ein Update ansteht, nicht als eigener Aufenthaltsort.
Er hängt deshalb dort, wo diese Frage entsteht - am Update-Hinweis
der Übersicht und an den beiden Karten unter "Addon & Updates".
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

from core.changelog_reader import format_changelog_body
from core.changelog_source import (
    ADDON,
    COMPANION,
    LABELS,
    entries_for,
    installed_version,
)
from core.version import parse_version

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.chip import Chip
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.wrapped_label import enable_wrap


class _VersionBlock(QFrame):
    """
    Eine Fassung: Nummer, Datum, Zustand, Text.

    Der Zustand ist die eigentliche Auskunft dieser Ansicht - "das ist
    die, die du hast" bzw. "das ist die, die du bekommst". Ohne ihn
    wäre die Liste nur eine Chronik.
    """

    def __init__(self, entry, state_label: str, variant: str, parent=None):

        super().__init__(parent)

        self.setObjectName("versionBlock")

        self.setAttribute(Qt.WA_StyledBackground, True)

        restyle(
            self,
            f"""
            QFrame#versionBlock{{
                background:{tokens.SURFACE["card"]};
                border:none;
                border-radius:{tokens.RADIUS["md"]}px;
            }}
            """,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(16, 14, 16, 16)

        root.setSpacing(8)

        header = QHBoxLayout()

        header.setContentsMargins(0, 0, 0, 0)

        header.setSpacing(tokens.SPACE[1])

        number = QLabel(entry.version)

        number.setFont(font("card"))

        restyle(
            number,
            f"color:{tokens.WHITE};background:transparent;",
        )

        header.addWidget(number)

        if entry.date:

            date = QLabel(entry.date)

            date.setFont(font("mono"))

            restyle(
                date,
                f"color:{tokens.TEXT['faint']};background:transparent;",
            )

            header.addWidget(date)

        header.addStretch(1)

        if state_label:
            header.addWidget(Chip(state_label, variant))

        root.addLayout(header)

        body = QLabel(format_changelog_body(entry.body) or "—")

        body.setFont(font("small"))

        enable_wrap(body)

        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        restyle(
            body,
            f"color:{tokens.TEXT['secondary']};background:transparent;",
        )

        root.addWidget(body)


class ChangelogDialog(QDialog):
    """
    Beide Komponenten, alle Fassungen.
    """

    def __init__(self, state, component: str = COMPANION, parent=None):

        super().__init__(parent)

        self.state = state

        self.setWindowTitle("Änderungen")

        self.setModal(True)

        self.resize(680, 640)

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

        root.setSpacing(16)

        head = QVBoxLayout()

        head.setContentsMargins(0, 0, 0, 0)

        head.setSpacing(2)

        head.addWidget(eyebrow_label("SOFTWARE · ÄNDERUNGEN"))

        title = QLabel("Was sich geändert hat.")

        title.setFont(font("title"))

        restyle(
            title,
            f"color:{tokens.WHITE};background:transparent;",
        )

        head.addWidget(title)

        root.addLayout(head)

        self.switch = SegmentedControl([
            (LABELS[COMPANION], COMPANION),
            (LABELS[ADDON], ADDON),
        ])

        self.switch.valueChanged.connect(self._on_component)

        root.addWidget(self.switch, alignment=Qt.AlignLeft)

        #
        # Der Inhalt wird bei jedem Umschalten neu gebaut. Das ist
        # hier erlaubt, wo es in WeintTV verboten wäre: der Wechsel
        # kommt von einem Klick, nicht viermal pro Sekunde von einer
        # Wiedergabe.
        #

        self.body = QWidget()

        self.body_layout = QVBoxLayout(self.body)

        self.body_layout.setContentsMargins(0, 0, 8, 0)

        self.body_layout.setSpacing(12)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )

        scroll.setWidget(self.body)

        self.scroll = scroll

        root.addWidget(scroll, 1)

        footer = QHBoxLayout()

        footer.setSpacing(12)

        self.note = QLabel("")

        self.note.setFont(font("small"))

        restyle(
            self.note,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        footer.addWidget(self.note)

        footer.addStretch(1)

        close = HeroButton("Schließen", primary=True)

        close.clicked.connect(self.accept)

        footer.addWidget(close)

        root.addLayout(footer)

        self.switch.setValue(component)

        self._fill(component)

    # --------------------------------------------------

    def _on_component(self, value):

        self._fill(str(value))

    def _clear(self):

        while self.body_layout.count():

            item = self.body_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _fill(self, component: str):

        self._clear()

        entries = entries_for(component, self.state)

        if not entries:

            self._add_placeholder(component)

            return

        installed = parse_version(
            installed_version(component, self.state)
        )

        has_install = bool(installed_version(component, self.state))

        for entry in entries:

            version = parse_version(entry.version)

            if has_install and version == installed:

                label, variant = "INSTALLIERT", "ok"

            elif has_install and version > installed:

                label, variant = "NEU", "warn"

            else:

                label, variant = "", "neutral"

            self.body_layout.addWidget(
                _VersionBlock(entry, label, variant)
            )

        self.body_layout.addStretch(1)

        self.note.setText(
            f"{len(entries)} Fassung"
            f"{'en' if len(entries) != 1 else ''} · neueste zuerst"
        )

        #
        # Nach dem Umschalten wieder nach oben: der Bildlauf bliebe
        # sonst auf der Höhe stehen, die für die andere Komponente
        # galt, und die Ansicht öffnete mitten in einer alten Fassung.
        #

        self.scroll.verticalScrollBar().setValue(0)

    def _add_placeholder(self, component: str):
        """
        Kein Changelog gefunden - und dazu, warum.

        Beim Addon ist die häufige Ursache eine andere als bei der
        Companion, und das ist der Unterschied zwischen "da fehlt
        etwas" und "installier es erst einmal".
        """

        if component == ADDON and not getattr(
            self.state, "addon_found", False
        ):

            text = (
                "Für WeintCodex liegen keine Änderungsnotizen vor - "
                "das Addon ist noch nicht installiert. Nach der "
                "Installation liegt die Liste im Addon-Ordner und "
                "steht hier vollständig."
            )

        elif component == ADDON:

            text = (
                "Die installierte Addon-Fassung bringt noch keine "
                "Änderungsliste mit, und das Release auf GitHub trägt "
                "keinen Text. Ab der nächsten Fassung steht sie hier."
            )

        else:

            text = (
                "Die mitgelieferte CHANGELOG.md wurde nicht gefunden."
            )

        label = QLabel(text)

        label.setFont(font("small"))

        enable_wrap(label)

        restyle(
            label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.body_layout.addWidget(label)

        self.body_layout.addStretch(1)

        self.note.setText("")


def show_changelog(state, component: str = COMPANION, parent=None):
    """
    Die Ansicht öffnen - der eine Einstiegspunkt für alle Aufrufer.
    """

    dialog = ChangelogDialog(state, component, parent)

    dialog.exec()

    return dialog
