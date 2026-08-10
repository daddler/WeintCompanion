"""
Meine Charaktere.

**Diese Seite hat im Programm noch keine Datenquelle**, und das ist
der Grund, warum sie hier trotzdem steht statt zu fehlen.

Was lokal über Charaktere bekannt ist, ist erstaunlich wenig: die
Twinkliste des Addons (`"character"`, Name | Klasse | Realm) wird von
`SyncManager` an den Bot weitergereicht und **nicht gespeichert** -
sie existiert für die Dauer eines Sync-Zyklus. Dazu kommt der gerade
angemeldete Charakter aus `"character_report"`, den `AcademyService`
für die Frage "wer bin ich" festhält. Gegenstandsstufe, Ausrüstung
oder Spezialisierungshistorie kommen an keiner Stelle vor.

Der Leerzustand ist deshalb hier die **richtige** Anzeige und kein
Platzhalter: er benennt, was fehlt, und wodurch es sich füllt. Eine
Seite, die stattdessen erfundene oder aus der Twinkliste
zusammengeratene Werte zeigte, wäre schlechter als eine leere - sie
wäre falsch, ohne es zu sagen. Das ist dieselbe Regel, nach der der
Analyzer eine fehlende Fähigkeit lieber gar nicht bewertet, als sie
mit 0 % anzunehmen.

Sobald das Addon eine Charakterliste mit Ausrüstung meldet, ist der
Rest reine Verdrahtung: Raster, Karte je Charakter, Klassenfarbe.
"""

from __future__ import annotations

from gui.pages._page import Page
from gui.widgets.empty_state import EmptyState


class CharactersPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            "CHARAKTER",
            "Deine Charaktere sammeln sich hier.",
            parent,
        )

        self.empty = EmptyState(
            eyebrow="NOCH KEINE DATEN",
            title="Das Addon meldet noch keine Charakterliste.",
            explanation=(
                "WeintCodex übergibt beim Anmelden im Spiel, welcher "
                "Charakter gerade gespielt wird. Eine vollständige "
                "Liste mit Ausrüstung und Gegenstandsstufe wird bisher "
                "nicht übertragen - sobald sie es wird, erscheint sie "
                "an dieser Stelle."
            ),
            action="Addon prüfen",
            icon="charaktere",
        )

        self.empty.actionTriggered.connect(self._open_addon)

        self.addWidget(self.empty, 1)

    # --------------------------------------------------

    def _open_addon(self):

        from gui.navigation import PageId

        self.pageRequested.emit(PageId.ADDON)

    def refresh(self):

        #
        # Wenigstens der angemeldete Charakter ist bekannt - ihn zu
        # nennen ist ehrlicher als ein durchgängig leerer Bereich und
        # zeigt zugleich, dass die Verbindung zum Spiel steht.
        #

        academy = getattr(self.manager, "academy", None)

        name = ""

        if academy is not None:

            name = (
                self.manager.config.data.get("academy_ingame_character", "")
                or ""
            )

        if name:

            self.header.setTitle(
                f"Im Spiel angemeldet: {name}."
            )

            return

        self.header.setTitle("Deine Charaktere sammeln sich hier.")
