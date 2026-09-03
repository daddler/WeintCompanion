"""
Auswertung und Lernpfad ins Addon stellen.

WeintTV und die Academy gibt es seit WeintCodex 1.0.1.0 auch im
Spiel - abgespeckt, für Leute mit nur einem Monitor. Beide Ingame-
Seiten sind reine Anzeigen: sie zeigen genau das, was hier zugestellt
wird, und rechnen nichts nach. Der Zuschnitt ist bewusst so gewählt,
damit Desktop und Addon nicht unterschiedlich urteilen können.

Was zugestellt wird, ist der Snapshot, den der RaidDataService
zuletzt veröffentlicht hat. Der Dienst wird hier ausdrücklich NICHT
angemeldet (attach()): das würde den Poll dauerhaft laufen lassen,
also Netzwerkverkehr erzeugen, solange die Anwendung offen ist -
auch für Nutzer, die weder WeintTV noch die Academy benutzen. Beide
Dienste arbeiten träge, und das soll so bleiben. In der Praxis
bedeutet das: zugestellt wird, was WeintTV oder die Academy zuletzt
ausgewertet haben. Wer die Seiten während des Raids offen hat -
also genau der Fall, für den die Ingame-Ansicht gedacht ist - hat
immer den aktuellen Stand.

Gelesen wird die Zustellung im Addon beim Login bzw. nach /reload
(ProcessInbox in modules/companion.lua) - dieselbe Bedingung wie
beim Raid-Roster-Import, der über denselben Weg läuft.
"""

from __future__ import annotations

import threading

from addon.addon_payloads import (
    build_academy_catalog,
    build_academy_state,
    build_weinttv_report,
)
from analyzer.academy import evaluator
from analyzer.academy.lessons import lessons_for_actor
from core.academy_dummy_sync import practice_payload
from core.lua_table import to_lua


class AddonAnalysisSync:

    def __init__(self, manager, inbox):

        self.manager = manager
        self.inbox = inbox

        #
        # Der zuletzt zugestellte Stand. Die Nutzlast ist einige
        # Dutzend Kilobyte groß und jedes Schreiben fasst WoWs
        # komplette SavedVariables-Datei an - unveränderte Daten
        # jeden Sync-Zyklus erneut hineinzuschreiben wäre
        # Verschwendung und würde die Datei unnötig oft anfassen.
        #

        self._fingerprint = None

        #
        # Der Vergleich und das Schreiben gehören zusammen.
        # AddonInbox sperrt nur seine Kanaltabelle, nicht den
        # Dateizugriff - ohne diese Sperre könnte publish_now() aus
        # dem GUI-Thread mitten in den Schreibvorgang des SyncThread
        # laufen.
        #

        self._lock = threading.Lock()

    # --------------------------------------------------

    def invalidate(self):
        """
        Den Merker verwerfen, damit die nächste Zustellung auch dann
        schreibt, wenn sich am Inhalt nichts geändert hat.

        Nötig überall dort, wo sich etwas geändert hat, das der
        Merker nicht sieht: die Charakterauswahl, der WoW-Pfad (eine
        andere SavedVariables-Datei, in der noch gar nichts steht).
        """

        with self._lock:
            self._fingerprint = None

    def publish_now(self):
        """
        Sofort zustellen, statt auf den Sync-Takt zu warten.

        Wird aus der Oberfläche gerufen (Charakterwechsel). Fehler
        dürfen den Aufrufer nicht mitreißen - er wollte nur einen
        Namen umstellen.
        """

        self.invalidate()

        try:
            self.process()

        except Exception as exc:

            self.manager.logger.error(
                f"WeintTV/Academy: Zustellung fehlgeschlagen: {exc}"
            )

    # --------------------------------------------------

    def process(self):

        snapshot = self.manager.raid_data.current()

        #
        # Noch nichts ausgewertet. Der bereits zugestellte Stand
        # bleibt liegen - er zu löschen wäre falsch: das Addon
        # zeigt weiterhin den letzten Bericht, und der ist besser
        # als gar keiner.
        #

        if not snapshot.has_data:
            return

        academy = self.manager.academy

        #
        # Genau EINMAL auflösen und überall denselben Namen benutzen.
        # Vorher löste build_profile() die Frage ein zweites Mal auf,
        # sodass academy_state.character und weinttv_report.me aus
        # zwei verschiedenen Objekten stammten und auseinanderlaufen
        # konnten.
        #
        # resolve_player_name() rät nicht mehr: ohne Auswahl kommt
        # "" zurück und es wird nichts zugestellt. Eine geratene
        # Identität hat auf der Leitung nichts verloren - festgelegt
        # wird sie in der Oberfläche über ensure_player_name(), wo
        # der Nutzer sie auch sieht.
        #

        player_name = academy.resolve_player_name(snapshot)

        if not player_name:
            return

        profile = evaluator.build_profile(snapshot, player_name)

        #
        # Kein Akteur heißt: dieser Charakter war im ausgewerteten
        # Pull nicht dabei. Zugestellt wird trotzdem - null Sterne
        # heißen bereits "keine Daten", das Addon zeigt also den
        # RICHTIGEN Charakter unbewertet statt eines fremden
        # bewertet. hasActor sagt dem Addon, welcher Fall vorliegt.
        #

        plan = academy.build_plan(profile, snapshot=snapshot, character=player_name)

        #
        # Nur der Katalog dieses Charakters, nicht alle 143 Lektionen:
        # mit den Lektionen fremder Klassen und Bosse könnte das Addon
        # ohnehin nichts anfangen.
        #

        lessons = lessons_for_actor(
            profile.actor,
            profile.encounter_name,
        )

        messages = [
            {
                "type": "academy_catalog",
                "payload": build_academy_catalog(lessons),
            },
            {
                "type": "academy_state",
                "payload": build_academy_state(
                    profile,
                    plan,
                    snapshot,
                    academy.completed_for(player_name),
                    academy.excluded_for(player_name),
                    character=player_name,

                    #
                    # Dieselbe Kurve, die auch der Trainingsplan
                    # gelesen hat (curve_for) und die die
                    # Verlaufskarte zeichnet. Ein zweiter Aufruf mit
                    # anderen Argumenten zeigte im Spiel eine andere
                    # Entwicklung, als die Reihenfolge des Plans
                    # behauptet.
                    #
                    records=academy.curve_for(profile, player_name),

                    practice=practice_payload(academy, player_name),
                ),
            },
            {
                "type": "weinttv_report",
                "payload": build_weinttv_report(snapshot, player_name),
            },
        ]

        #
        # Der Zeitstempel ändert sich bei jedem Poll, auch wenn sich
        # inhaltlich nichts getan hat - er darf deshalb nicht in den
        # Vergleich. Verglichen wird das gerenderte Lua ohne ihn.
        #

        fingerprint = tuple(
            to_lua({
                key: value
                for key, value in message["payload"].items()
                if key != "capturedAt"
            })
            for message in messages
        )

        with self._lock:

            if fingerprint == self._fingerprint:
                return

            #
            # Bei False wurde keine SavedVariables-Datei gefunden. Der
            # Merker bleibt dann ABSICHTLICH unangetastet: sonst
            # gälte die Zustellung als erledigt und würde nie
            # nachgeholt, sobald der Pfad wieder da ist.
            #
            if not self.inbox.publish("analysis", messages):
                return

            self._fingerprint = fingerprint

        self.manager.logger.success(
            f"WeintTV/Academy: Auswertung für {player_name} "
            f"an das Addon übergeben."
        )
