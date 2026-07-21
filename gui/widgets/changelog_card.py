from PySide6.QtWidgets import QLabel, QTextEdit

from gui.theme.colors import Colors
from gui.widgets.card import Card


class ChangelogCard(Card):
    """
    Zeigt, was in der aktuell installierten Companion-Version
    committed wurde - siehe CHANGELOG-Panel im Addon-Tab, hier
    aber auf Basis der Commits zwischen dem vorherigen und dem
    aktuellen GitHub-Release statt der (bei Direkt-Pushes oft
    leeren) Release-Notes.
    """

    def __init__(self):
        super().__init__()

        eyebrow = QLabel("CHANGELOG · AKTUELLE VERSION")

        eyebrow.setObjectName("eyebrow")

        eyebrow.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_MUTED};"
            "letter-spacing:0.1em;"
        )

        self.addWidget(eyebrow)

        self.version_label = QLabel("-")

        self.version_label.setStyleSheet(
            f"font-size:14px;font-weight:700;color:{Colors.WHITE};"
        )

        self.addWidget(self.version_label)

        self.text = QTextEdit()

        self.text.setReadOnly(True)

        self.text.setMinimumHeight(90)
        self.text.setMaximumHeight(140)

        self.text.setStyleSheet(f"""
        QTextEdit{{
            background:transparent;
            border:none;
            color:{Colors.TEXT_SECONDARY};
            padding:0px;
            font-size:13px;
        }}
        """)

        self.addWidget(self.text)

    # --------------------------------------------------

    def refresh(self, state):

        self.version_label.setText(
            f"Version {state.companion_version}"
        )

        commits = state.companion_changelog

        if commits is None:

            self.text.setPlainText(
                "Changelog nicht verfügbar (kein passendes "
                "Release gefunden oder GitHub nicht erreichbar)."
            )

            return

        if not commits:

            self.text.setPlainText(
                "Keine Änderungen gefunden."
            )

            return

        self.text.setPlainText(
            "\n".join(
                f"• {commit}" for commit in commits
            )
        )
