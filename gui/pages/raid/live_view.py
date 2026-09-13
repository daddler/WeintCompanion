"""
LIVE - was gerade passiert.

Die erste der vier Perspektiven des Raid Centers und die einzige, die
sich im Sekundentakt bewegt: Bossleben, Pulldauer, Schaden und Heilung
je Spieler, Tanks, Tode, Kampf-Rezz, Heldentum, Phasen.

Diese Datei enthält bewusst KEINE Auswertungslogik. Sie bekommt vom
RaidDataService fertige `RaidSnapshot`-Objekte und schreibt deren
Werte in Widgets. Alles, was gerechnet wird, passiert im Analyzer -
dadurch läuft die Ansicht gegen die Simulation und gegen echte
Combat-Log-Daten identisch.

**Was hier nicht mehr steht**, und das ist der Umbau auf 4.0: kein
Reiterumschalter (Live/Analyse/Verlauf), keine Quellenzeile, kein
Archiv-Wähler, keine Wiedergabeleiste, keine Wartekarte, kein
Bossname. All das stand bis 3.6.0 auf dieser Seite und steht seit 4.0
**einmal** im Raid Center darüber, wo es beim Wechsel der Perspektive
stehen bleibt. Was der Kopfblock des Raid Centers schon sagt - welcher
Boss, welcher Pull, wie er ausging -, sagt `LiveHeader` deshalb nicht
noch einmal (`titles=False`): zwei Bossnamen übereinander waren die
häufigste Doppelung des alten Aufbaus.

Ebenfalls entfallen ist der **verborgene Zweig aus 1.7** (eine
Boss-Karte samt vier Kennzahlkacheln, alle auf `setVisible(False)`),
den `_apply_live()` weiter beschriftete. Er war als Übergang gedacht,
bis der Kopfblock steht; der steht seit 2.0.

Aktualisiert wird nur, solange die Ansicht auch sichtbar ist -
`on_enter()`/`on_leave()` ruft das Raid Center durch, das sie
seinerseits von `MainWindow.change_page()` bekommt.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from analyzer.models import SUPPORT_INTERRUPT, RaidSnapshot

from core.resources import Resources

from gui.theme.colors import Colors
from gui.theme.wow_colors import role_label, class_color

from gui.widgets.bar_table import BarTable, format_per_second
from gui.widgets.section_card import SectionCard
from gui.widgets.tv.entry_list import EntryData, EntryList
from gui.widgets.tv.live_header import LiveHeader
from gui.widgets.tv.meter_row_list import MeterRowData, MeterRowList


#
# Beschriftung der Ereignisarten aus `CombatEvent.kind`. Die Liste
# ist bewusst NICHT vollständig und darf es nicht sein: eine
# unbekannte Art wird unverändert angezeigt, statt verworfen zu
# werden - sonst müsste der Companion jedes Mal nachziehen, wenn der
# Bot eine neue Art mitschickt.
#

EVENT_KIND_LABELS = {
    "phase": "Phase",
    "cast": "Ansage",
    "add": "Add",
    "wipe": "Wipe",
    "kill": "Kill",
}


class LiveView(QWidget):
    """
    Der laufende Kampf. Eine Ansicht, kein Ort - sie trägt keinen
    eigenen Kopf und keine eigene Datenquelle.
    """

    def __init__(self, manager, parent=None):

        super().__init__(parent)

        self.manager = manager

        self.service = manager.raid_data

        root = QVBoxLayout(self)

        #
        # Ohne eigene Seitenränder: die stehen am Raid Center. Der
        # Abstand zwischen den Blöcken ist hier enger als auf den
        # übrigen Seiten - diese Ansicht lebt von Dichte, und jeder
        # eingesparte Abstand ist eine weitere Zeile Rangliste.
        #

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(14)

        self._build(root)

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _build(self, layout: QVBoxLayout):

        #
        # Kopfblock: 96 px für Boss, Zustand, Balken und Pull-Uhr.
        #
        # Bis 1.7 standen hier eine Boss-Karte mit Symbol, Titel und
        # Untertitel und darunter vier Kennzahlkacheln - zusammen über
        # 300 px, bevor die erste Ranglistenzeile begann. Genau das war
        # der Grund, warum dort nur fünf Plätze passten. Die Kennzahlen
        # sind nicht verschwunden, sie stehen als Chips neben dem
        # Bossnamen: eine Zahl, die man im Vorbeisehen braucht,
        # verlangt keine eigene Kachel mit Rubrik und Fußzeile.
        #

        self.live_header = LiveHeader(titles=False)

        layout.addWidget(self.live_header)

        #
        # Rankings
        #

        rankings = QHBoxLayout()

        rankings.setSpacing(16)

        #
        # Die Ranglisten zeigen seit 2.0 den **ganzen** Raid statt der
        # besten fünf.
        #
        # Bis 1.7 ging das nicht: eine Zeile bestand aus fünf Widgets
        # (Platz, Name, Spezialisierung, Wert und darunter ein eigener
        # Balken) und brauchte mit ihren Abständen rund 40 px. 25 davon
        # sind 1.000 px und passen in kein Fenster, das 900 px hoch ist -
        # deshalb hörte die Liste nach Platz fünf auf. Für zwanzig von
        # fünfundzwanzig Leuten beantwortete sie damit die einzige
        # Frage nicht, die sie haben: wo stehe ich.
        #
        # `BarRow` legt den Balken in den Zeilenhintergrund statt unter
        # die Zeile und malt den Text selbst. Damit kommt eine Zeile mit
        # 24 px aus, und die Rechnung des Entwurfs geht auf:
        # 25 x (24 + 2) = 650 px.
        #

        #
        # Ohne SectionCard-Hülle. Die trug Symbol, Titel und
        # Untertitel - also rund 90 px, die genau das wiederholten,
        # was die Kopfzeile der Tabelle ohnehin sagt ("SCHADEN" plus
        # Raidsumme). Der Entwurf setzt die Listen deshalb direkt auf
        # die Inhaltsfläche: die Klassenfarbe der Balken trägt die
        # Gliederung, dafür braucht es keinen Kasten.
        #

        self.damage_list = BarTable("SCHADEN", rows=25)

        rankings.addWidget(self.damage_list, 1)

        self.healing_list = BarTable("HEILUNG", rows=25)

        rankings.addWidget(self.healing_list, 1)

        layout.addLayout(rankings)

        #
        # Tanks
        #

        tank_card = SectionCard(
            Resources.companion(),
            "Tank-Übersicht",
            "Lebenspunkte und aktive Schadensminderung.",
        )

        self.tank_list = MeterRowList(
            capacity=4,
            placeholder="Keine Tanks erkannt.",
        )

        tank_card.addWidget(self.tank_list)

        layout.addWidget(tank_card)

        #
        # Kampfereignisse
        #
        # Tode, Kampf-Wiederbelebungen und Heldentum in einer
        # gemeinsamen, zeitlich sortierten Liste. Bisher war nur
        # ablesbar, DASS Heldentum lief und WIE VIELE Rezz-Ladungen
        # übrig sind - nicht wann und auf wen. Drei getrennte, meist
        # fast leere Karten dafür wären verschenkter Platz; die
        # gemeinsame Zeitachse erzählt zudem den Verlauf des Pulls.
        #

        events_card = SectionCard(
            Resources.logs(),
            "Kampfereignisse",
            (
                "Tode, Kampf-Rezz, Heldentum, Unterbrechungen und "
                "Phasen in zeitlicher Folge."
            ),
        )

        self.events_list = EntryList(
            capacity=20,
            placeholder="Noch nichts passiert.",
        )

        events_card.addWidget(self.events_list)

        layout.addWidget(events_card)

        layout.addStretch()

    # --------------------------------------------------
    # Snapshot anwenden
    # --------------------------------------------------

    def apply(self, snapshot: RaidSnapshot):

        #
        # Kopfblock
        #

        self.live_header.apply(snapshot)

        history = self.service.history()

        self.live_header.set_best_attempt(
            min(
                (h.boss_percent for h in history
                 if getattr(h, "boss_percent", None) is not None),
                default=None,
            )
        )

        #
        # Rankings
        #

        #
        # Die eigene Zeile wird hervorgehoben, und wer gefallen ist,
        # trägt statt seiner Spezialisierung den Todeszeitpunkt.
        # Beides kommt aus dem Snapshot, den beide Listen ohnehin
        # bekommen - eine zweite Quelle für "wer bin ich" gäbe es hier
        # nicht (siehe analyzer/names.py).
        #

        me = self.manager.academy.player_name()

        deaths = {
            death.actor_name: int(death.at_seconds)
            for death in snapshot.deaths
            if death.at_seconds >= 0
        }

        #
        # Während einer laufenden Wiedergabe (4 Hz) wird nicht
        # animiert: ein Balken mit 220 ms Laufzeit wäre dauerhaft
        # unterwegs und nie am Ziel. Gefragt wird nach `playing` und
        # nicht nach dem Modus - eine angehaltene Wiedergabe darf
        # ihren Balken durchaus laufen lassen, etwa beim Springen mit
        # dem Regler.
        #

        animate = not self.service.replay_state().playing

        self.damage_list.set_entries(
            snapshot.top_damage,
            me=me,
            deaths=deaths,
            animate=animate,
        )

        self.damage_list.setTotal(
            f"RAID {format_per_second(sum(e.value for e in snapshot.top_damage))} DPS"
            if snapshot.top_damage
            else ""
        )

        self.healing_list.set_entries(
            snapshot.top_healing,
            me=me,
            deaths=deaths,
            animate=animate,
        )

        self.healing_list.setTotal(
            f"RAID {format_per_second(sum(e.value for e in snapshot.top_healing))} HPS"
            if snapshot.top_healing
            else ""
        )

        #
        # Tanks
        #

        self.tank_list.setRows(
            MeterRowData(
                title=tank.actor.name,
                detail=(
                    f"{role_label(tank.actor.role)} · "
                    f"{'Mitigation aktiv' if tank.active_mitigation else 'ungeschützt'}"
                ),
                value=f"{tank.health_percent:.0f} %",
                ratio=tank.health_percent / 100.0,
                color=(
                    Colors.ERROR
                    if tank.health_percent < 35.0
                    else class_color(tank.actor.class_name)
                ),
            )
            for tank in snapshot.tanks
        )

        self.events_list.setEntries(self._event_rows(snapshot))

    def _event_rows(self, snapshot: RaidSnapshot):
        """
        Alles, was zu einem Zeitpunkt passiert ist, auf einer
        gemeinsamen Zeitachse - neueste zuerst, damit das Jüngste ohne
        Scrollen sichtbar ist.

        Zusammengeführt wird hier und nicht in der Auswertung: der
        Snapshot hält die Ereignisarten getrennt, weil die Academy sie
        getrennt braucht (ein Dispel bewertet einen anderen Bereich
        als ein Tod). Für den Verlauf eines Pulls zählt dagegen nur
        die Reihenfolge - drei fast leere Karten nebeneinander würden
        sie nicht erzählen.
        """

        rows = []

        #
        # Was die Quelle zusätzlich erzählt (Phasenwechsel, angesagte
        # Bossfähigkeiten). Unbekannte Arten laufen ohne
        # Fallunterscheidung mit - genau dafür ist `kind` eine freie
        # Zeichenkette.
        #

        for event in snapshot.events:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=event.detail or event.ability or event.kind,
                    detail=(
                        event.clock
                        + (
                            f" · {event.actor_name}"
                            if event.actor_name
                            else ""
                        )
                    ),
                    level=event.severity,
                    trailing=EVENT_KIND_LABELS.get(event.kind, event.kind),
                ),
            ))

        for event in snapshot.interrupts + snapshot.dispels:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=(
                        f"{event.actor_name} → {event.target}"
                        if event.target
                        else event.actor_name
                    ),
                    detail=(
                        f"{int(event.at_seconds) // 60:02d}:"
                        f"{int(event.at_seconds) % 60:02d}"
                        + (f" · {event.ability}" if event.ability else "")
                    ),
                    level="success",
                    trailing=(
                        "Unterbrechung"
                        if event.kind == SUPPORT_INTERRUPT
                        else "Dispel"
                    ),
                ),
            ))

        #
        # Mechanikfehler nur, wenn sie sich an einer Sekunde
        # festmachen lassen - ein Eintrag ohne Zeitpunkt (at_seconds
        # < 0) hätte auf einer Zeitachse keinen Platz und steht
        # ohnehin in der Analyse.
        #

        for issue in snapshot.mechanics:

            if issue.at_seconds < 0:
                continue

            rows.append((
                issue.at_seconds,
                EntryData(
                    title=f"{issue.actor_name}: {issue.mechanic}",
                    detail=(
                        f"{int(issue.at_seconds) // 60:02d}:"
                        f"{int(issue.at_seconds) % 60:02d}"
                    ),
                    level=issue.severity,
                    trailing=f"{issue.count}×",
                ),
            ))

        for window in snapshot.heroism_windows:

            rows.append((
                window.start,
                EntryData(
                    title=f"{window.label} eingesetzt",
                    detail=(
                        f"{window.clock}"
                        + (f" · von {window.source}" if window.source else "")
                    ),
                    level="info",
                    trailing=f"{int(window.duration)}s",
                ),
            ))

        for event in snapshot.resurrections:

            rows.append((
                event.at_seconds,
                EntryData(
                    title=f"Kampf-Rezz auf {event.target}",
                    detail=(
                        f"{event.clock}"
                        + (f" · von {event.caster}" if event.caster else "")
                    ),
                    level="success",
                    trailing=event.ability,
                ),
            ))

        for death in snapshot.deaths:

            clock = max(0, int(death.at_seconds))

            rows.append((
                death.at_seconds,
                EntryData(
                    title=f"{death.actor_name} gestorben",
                    detail=(
                        f"{clock // 60:02d}:{clock % 60:02d}"
                        + (f" · {death.cause}" if death.cause else "")
                    ),
                    level="error",
                ),
            ))

        rows.sort(key=lambda row: row[0], reverse=True)

        return [entry for _at, entry in rows]
