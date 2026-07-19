import sys
from pathlib import Path

import PySide6
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.resources import Resources
from core.version import VERSION
from gui.theme.colors import Colors
from gui.widgets.card import Card
from gui.widgets.hero_banner import HeroButton


def _diff_box(eyebrow: str, value: str, meta: str, accent: bool = False):

    box = Card(accent=accent)

    box.root.setContentsMargins(18, 16, 18, 16)
    box.root.setSpacing(6)

    eyebrow_label = QLabel(eyebrow)

    eyebrow_label.setObjectName("eyebrow")

    color = Colors.WARNING if accent else Colors.TEXT_MUTED

    eyebrow_label.setStyleSheet(
        'font-family:"JetBrains Mono";'
        f"font-size:10px;color:{color};letter-spacing:0.1em;"
    )

    box.addWidget(eyebrow_label)

    value_label = QLabel(value)

    value_label.setStyleSheet(
        'font-family:"JetBrains Mono";'
        f"font-size:22px;color:{Colors.WHITE};letter-spacing:-0.02em;"
    )

    box.addWidget(value_label)

    meta_label = QLabel(meta)

    meta_label.setWordWrap(True)

    meta_label.setStyleSheet(
        f"font-size:12px;color:{Colors.TEXT_SECONDARY};"
    )

    box.addWidget(meta_label)

    return box, value_label, meta_label


class AddonPage(QWidget):

    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout(self)

        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # --------------------------------------------------
        # Kopfzeile
        # --------------------------------------------------

        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        eyebrow = QLabel("SOFTWARE · KOMPONENTEN")
        eyebrow.setObjectName("eyebrow")

        title_col.addWidget(eyebrow)

        title = QLabel("Deine Installationen")
        title.setObjectName("title")

        title_col.addWidget(title)

        header.addLayout(title_col)

        header.addStretch()

        self.check_button = HeroButton(
            "Alle prüfen",
            primary=False,
        )

        header.addWidget(self.check_button)

        layout.addLayout(header)

        # --------------------------------------------------
        # Komponente: WeintCodex
        # --------------------------------------------------

        self.addon_card = Card()

        addon_header = QHBoxLayout()
        addon_header.setSpacing(16)

        icon_box = QLabel()

        icon_box.setFixedSize(48, 48)

        icon_box.setStyleSheet(f"""
        QLabel{{
            background:rgba(168,85,247,20);
            border:1px solid {Colors.BORDER_ACCENT};
            border-radius:12px;
        }}
        """)

        icon_layout = QHBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        addon_icon = QSvgWidget(Resources.software())
        addon_icon.setFixedSize(22, 22)

        icon_layout.addWidget(
            addon_icon,
            alignment=Qt.AlignCenter,
        )

        addon_header.addWidget(icon_box)

        addon_title_col = QVBoxLayout()
        addon_title_col.setSpacing(2)

        addon_title = QLabel("WeintCodex")

        addon_title.setStyleSheet(
            f"font-size:17px;font-weight:600;color:{Colors.WHITE};"
        )

        addon_title_col.addWidget(addon_title)

        addon_subtitle = QLabel(
            "github.com/daddler/WeintCodex · MoP Classic"
        )

        addon_subtitle.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        addon_title_col.addWidget(addon_subtitle)

        addon_header.addLayout(addon_title_col, 1)

        self.reinstall_button = HeroButton(
            "Neu installieren",
            primary=False,
        )

        self.update_button = HeroButton(
            "Addon installieren",
            primary=True,
        )

        addon_header.addWidget(self.reinstall_button)
        addon_header.addWidget(self.update_button)

        self.addon_card.addLayout(addon_header)

        #
        # Versions-Diff
        #

        diff_row = QHBoxLayout()
        diff_row.setSpacing(16)

        self.installed_box, self.installed_value, self.installed_meta = _diff_box(
            "INSTALLIERT", "-", "-",
        )

        diff_row.addWidget(self.installed_box, 1)

        arrow = QLabel("→")

        arrow.setAlignment(Qt.AlignCenter)

        arrow.setStyleSheet(
            f"color:{Colors.PRIMARY};font-size:18px;"
        )

        diff_row.addWidget(arrow)

        self.latest_box, self.latest_value, self.latest_meta = _diff_box(
            "NEUESTE", "-", "-", accent=True,
        )

        diff_row.addWidget(self.latest_box, 1)

        self.addon_card.addLayout(diff_row)

        #
        # Changelog
        #

        changelog_label = QLabel("CHANGELOG")

        changelog_label.setObjectName("eyebrow")

        changelog_label.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:10px;color:{Colors.TEXT_MUTED};letter-spacing:0.1em;"
        )

        self.addon_card.addWidget(changelog_label)

        self.changelog = QTextEdit()

        self.changelog.setReadOnly(True)

        self.changelog.setMinimumHeight(110)

        self.changelog.setStyleSheet(f"""
        QTextEdit{{
            background:transparent;
            border:none;
            color:{Colors.TEXT_SECONDARY};
            padding:0px;
            font-size:13px;
        }}
        """)

        self.addon_card.addWidget(self.changelog)

        layout.addWidget(self.addon_card)

        # --------------------------------------------------
        # Weitere Komponenten
        # --------------------------------------------------

        other_grid = QGridLayout()

        other_grid.setHorizontalSpacing(14)
        other_grid.setVerticalSpacing(14)

        self.wow_card = Card()

        wow_row = QHBoxLayout()
        wow_row.setSpacing(14)

        wow_icon = QLabel()
        wow_icon.setFixedSize(40, 40)
        wow_icon.setStyleSheet(f"""
        QLabel{{
            background:rgba(124,192,110,18);
            border-radius:10px;
        }}
        """)

        wow_icon_layout = QHBoxLayout(wow_icon)
        wow_icon_layout.setContentsMargins(0, 0, 0, 0)

        wow_svg = QSvgWidget(Resources.game())
        wow_svg.setFixedSize(18, 18)

        wow_icon_layout.addWidget(
            wow_svg,
            alignment=Qt.AlignCenter,
        )

        wow_row.addWidget(wow_icon)

        wow_text_col = QVBoxLayout()
        wow_text_col.setSpacing(2)

        wow_title = QLabel("WoW Client")

        wow_title.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        wow_text_col.addWidget(wow_title)

        self.wow_path_label = QLabel("-")

        self.wow_path_label.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        wow_text_col.addWidget(self.wow_path_label)

        wow_row.addLayout(wow_text_col, 1)

        self.change_path_button = HeroButton(
            "Pfad ändern",
            primary=False,
        )

        wow_row.addWidget(self.change_path_button)

        self.wow_card.addLayout(wow_row)

        other_grid.addWidget(self.wow_card, 0, 0)

        self.runtime_card = Card()

        runtime_row = QHBoxLayout()
        runtime_row.setSpacing(14)

        runtime_icon = QLabel()
        runtime_icon.setFixedSize(40, 40)
        runtime_icon.setStyleSheet(f"""
        QLabel{{
            background:rgba(168,85,247,18);
            border-radius:10px;
        }}
        """)

        runtime_icon_layout = QHBoxLayout(runtime_icon)
        runtime_icon_layout.setContentsMargins(0, 0, 0, 0)

        runtime_svg = QSvgWidget(Resources.companion())
        runtime_svg.setFixedSize(18, 18)

        runtime_icon_layout.addWidget(
            runtime_svg,
            alignment=Qt.AlignCenter,
        )

        runtime_row.addWidget(runtime_icon)

        runtime_text_col = QVBoxLayout()
        runtime_text_col.setSpacing(2)

        runtime_title = QLabel("Companion Runtime")

        runtime_title.setStyleSheet(
            f"font-size:14px;font-weight:600;color:{Colors.WHITE};"
        )

        runtime_text_col.addWidget(runtime_title)

        python_version = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )

        self.runtime_label = QLabel(
            f"v{VERSION} · Python {python_version} · "
            f"PySide6 {PySide6.__version__}"
        )

        self.runtime_label.setStyleSheet(
            'font-family:"JetBrains Mono";'
            f"font-size:11px;color:{Colors.TEXT_MUTED};"
        )

        runtime_text_col.addWidget(self.runtime_label)

        runtime_row.addLayout(runtime_text_col, 1)

        self.runtime_badge = QLabel("AKTUELL")

        self.runtime_badge.setStyleSheet(f"""
        QLabel{{
            background:rgba(124,192,110,18);
            color:{Colors.SUCCESS};
            border-radius:4px;
            padding:5px 10px;
            font-family:"JetBrains Mono";
            font-size:11px;
            font-weight:700;
        }}
        """)

        runtime_row.addWidget(self.runtime_badge)

        self.runtime_card.addLayout(runtime_row)

        other_grid.addWidget(self.runtime_card, 0, 1)

        other_grid.setColumnStretch(0, 1)
        other_grid.setColumnStretch(1, 1)

        layout.addLayout(other_grid)

        layout.addStretch()

        # --------------------------------------------------
        # Signale
        # --------------------------------------------------

        self.check_button.clicked.connect(self.check_updates)
        self.reinstall_button.clicked.connect(self.install_or_update)
        self.update_button.clicked.connect(self.install_or_update)
        self.change_path_button.clicked.connect(self.choose_folder)

        self.refresh()

    # --------------------------------------------------
    # Oberfläche aktualisieren
    # --------------------------------------------------

    def refresh(self):

        state = self.manager.state

        #
        # Versions-Diff
        #

        self.installed_value.setText(
            state.addon_version if state.addon_found else "-"
        )

        self.installed_meta.setText(
            "installiert"
            if state.addon_found
            else "noch nicht installiert"
        )

        self.latest_value.setText(state.github_version)

        self.latest_meta.setText(
            state.github_release_name or "-"
        )

        self.changelog.setPlainText(
            state.github_changelog or ""
        )

        #
        # Buttons
        #

        if not state.addon_found:

            self.update_button.setText("Addon installieren")
            self.update_button.setEnabled(True)
            self.reinstall_button.setEnabled(False)

        elif state.update_available:

            self.update_button.setText(
                f"Auf {state.github_version} aktualisieren"
            )
            self.update_button.setEnabled(True)
            self.reinstall_button.setEnabled(True)

        else:

            self.update_button.setText("Addon aktuell")
            self.update_button.setEnabled(False)
            self.reinstall_button.setEnabled(True)

        #
        # WoW Client
        #

        if state.wow_found:

            self.wow_path_label.setText(str(state.wow_path))

        else:

            self.wow_path_label.setText(
                "Nicht gefunden - bitte Pfad wählen"
            )

        #
        # Companion Runtime
        #

        if state.companion_update_available:

            self.runtime_badge.setText("UPDATE")

            self.runtime_badge.setStyleSheet(f"""
            QLabel{{
                background:rgba(212,162,74,18);
                color:{Colors.WARNING};
                border-radius:4px;
                padding:5px 10px;
                font-family:"JetBrains Mono";
                font-size:11px;
                font-weight:700;
            }}
            """)

        else:

            self.runtime_badge.setText("AKTUELL")

            self.runtime_badge.setStyleSheet(f"""
            QLabel{{
                background:rgba(124,192,110,18);
                color:{Colors.SUCCESS};
                border-radius:4px;
                padding:5px 10px;
                font-family:"JetBrains Mono";
                font-size:11px;
                font-weight:700;
            }}
            """)

    # --------------------------------------------------
    # GitHub erneut prüfen
    # --------------------------------------------------

    def check_updates(self):

        self.manager.logger.info(
            "Prüfe GitHub auf neue Versionen..."
        )

        self.manager.refresh()
        self.manager.refresh_update_status()

        self.refresh()

        self.manager.logger.success(
            "GitHub erfolgreich geprüft."
        )

    # --------------------------------------------------
    # Installation / Update
    # --------------------------------------------------

    def install_or_update(self):

        try:

            state = self.manager.state

            if state.addon_found:

                self.manager.logger.info(
                    "Starte Addon-Aktualisierung..."
                )

            else:

                self.manager.logger.info(
                    "Starte Addon-Installation..."
                )

            self.manager.install_or_update()

            self.refresh()

            if state.addon_found:

                self.manager.logger.success(
                    "Addon erfolgreich aktualisiert."
                )

            else:

                self.manager.logger.success(
                    "Addon erfolgreich installiert."
                )

        except Exception as e:

            self.manager.logger.error(f"Fehler: {e}")

    # --------------------------------------------------
    # WoW-Ordner auswählen
    # --------------------------------------------------

    def choose_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "MoP Classic auswählen",
        )

        if not folder:
            return

        folder = Path(folder)

        if (
            folder.name == "World of Warcraft"
            and (folder / "_classic_").exists()
        ):
            folder = folder / "_classic_"

        if not (
            (folder / "Interface").exists()
            and (folder / "Interface" / "AddOns").exists()
            and (folder / "WTF").exists()
        ):

            self.manager.logger.error(
                "Kein gültiger MoP-Classic-Ordner."
            )

            return

        self.manager.config.set_classic_path(folder)

        self.manager.refresh()

        self.manager.logger.success(
            f"Classic-Pfad geändert: {folder}"
        )

        self.refresh()
