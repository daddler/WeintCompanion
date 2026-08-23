"""
Die WeintAcademy auf Anwendungsebene.

Der Service macht drei Dinge und sonst nichts:

* er merkt sich, für welchen Charakter das Lernprofil gilt,
* er speichert den Lernfortschritt dauerhaft,
* er reicht Snapshots an die Auswertung im Analyzer weiter.

Die eigentliche Bewertungslogik liegt bewusst NICHT hier, sondern in
analyzer/academy/ - dort ist sie ohne laufende Oberfläche testbar und
kann später unverändert auch vom Discord-Bot genutzt werden.

Der Fortschritt landet in Paths.config() und nicht in Paths.cache():
erledigte Lektionen sind Nutzerdaten, kein Zwischenergebnis, und
dürfen beim Leeren des Caches nicht verschwinden.
"""

from __future__ import annotations

import json
import os
import time

from analyzer.academy import evaluator
from analyzer.academy.lessons import find_lesson, lessons_for_actor
from analyzer.academy.models import PlayerProfile, TrainingPlan
from analyzer.academy.progression import (
    CURVE_LIMIT,
    PullRecord,
    pull_key,
    qualifies,
    record_from_profile,
)
from analyzer.models import RaidSnapshot
from analyzer.names import match_name, names_equal

from core.academy_history import AcademyHistory, today
from core.paths import Paths


PROGRESS_FILE = "academy_progress.json"


class AcademyService:

    def __init__(self, manager):

        self.manager = manager

        self.file = Paths.config() / PROGRESS_FILE

        #
        # Aufbau:
        #
        #   {"completed": {"<Charakter>": ["<lesson_id>", ...]},
        #    "excluded":  {"<Charakter>": ["<lesson_id>", ...]}}
        #
        # Beides hängt am Charakter, nicht am Konto: ein
        # Zweitcharakter mit anderer Klasse hat einen eigenen
        # Lernpfad.
        #
        # Bei der Abwahl werden bewusst die AUSGESCHLOSSENEN Lektionen
        # gespeichert und nicht die gewählten. Damit ist jede neu
        # hinzugefügte Lektion automatisch für alle aktiv - ohne
        # Migration bestehender Dateien und ohne Nachfrage beim
        # Nutzer. Andersherum wäre jeder Katalogausbau für
        # Bestandsnutzer unsichtbar geblieben.
        #
        # "dummy_practice" (seit WeintCodex 1.3.0.0) hält pro Charakter
        # und Spec-Schlüssel die letzte gültige Übungssitzung am
        # Trainingsdummy fest ({"lastDate": "YYYYMMDD", "streak": int}) -
        # siehe core/academy_dummy_sync.py. Erreicht die Serie drei
        # Tage, wird die passende Lektion automatisch über
        # set_completed() abgehakt.
        #

        self.data: dict = {"completed": {}, "excluded": {}, "dummy_practice": {}}

        self.load()

        #
        # Die Lernkurve liegt in einer **eigenen** Datei: hier stehen
        # Angaben des Nutzers (erledigt, abgewählt), dort Messwerte
        # des Programms. Ein Defekt in der einen darf die andere nicht
        # mitnehmen - siehe core/academy_history.py.
        #

        self.history = AcademyHistory(manager)

    # --------------------------------------------------
    # Persistenz
    # --------------------------------------------------

    def load(self):

        if not self.file.exists():
            return

        try:

            with open(self.file, "r", encoding="utf-8") as handle:

                loaded = json.load(handle)

            if isinstance(loaded, dict):

                for key in ("completed", "excluded"):

                    section = loaded.get(key)

                    if isinstance(section, dict):

                        self.data[key] = {
                            str(name): [str(value) for value in ids]
                            for name, ids in section.items()
                            if isinstance(ids, list)
                        }

                dummy_section = loaded.get("dummy_practice")

                if isinstance(dummy_section, dict):

                    parsed: dict = {}

                    for character, specs in dummy_section.items():

                        if not isinstance(specs, dict):
                            continue

                        parsed_specs = {}

                        for spec_key, record in specs.items():

                            if not isinstance(record, dict):
                                continue

                            last_date = record.get("lastDate")
                            streak = record.get("streak")

                            if not isinstance(last_date, str) or not isinstance(streak, int):
                                continue

                            parsed_specs[str(spec_key)] = {
                                "lastDate": last_date,
                                "streak": streak,
                            }

                        if parsed_specs:
                            parsed[str(character)] = parsed_specs

                    self.data["dummy_practice"] = parsed

        except Exception as exc:

            #
            # Ein defekter Fortschritt darf die Academy nicht
            # unbenutzbar machen - er wird verworfen und der Vorfall
            # protokolliert, statt die Anwendung scheitern zu lassen.
            #

            self.manager.logger.warning(
                f"Academy-Fortschritt konnte nicht gelesen werden "
                f"({exc}) - es wird neu begonnen."
            )

            self.data = {"completed": {}, "excluded": {}, "dummy_practice": {}}

    def save(self):
        """
        Atomar schreiben (erst temporär, dann ersetzen) - dasselbe
        Vorgehen wie in core/config.py, damit ein Absturz mitten im
        Schreiben keine halbe Datei hinterlässt.
        """

        try:

            self.file.parent.mkdir(parents=True, exist_ok=True)

            tmp_path = self.file.with_suffix(
                self.file.suffix + ".tmp"
            )

            with open(tmp_path, "w", encoding="utf-8") as handle:

                json.dump(
                    self.data,
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

            os.replace(tmp_path, self.file)

        except OSError as exc:

            self.manager.logger.error(
                f"Academy-Fortschritt konnte nicht gespeichert "
                f"werden: {exc}"
            )

    # --------------------------------------------------
    # Charakterauswahl
    # --------------------------------------------------

    def player_name(self) -> str:

        return self.manager.config.data.get(
            "academy_player_name",
            "",
        )

    def set_player_name(self, name: str):

        current = self.player_name()

        if current == name:
            return

        self.manager.config.data["academy_player_name"] = name

        self.manager.config.save()

        if name:

            self.manager.logger.info(
                f"Academy: Lernprofil auf {name} umgestellt."
            )

        #
        # Sofort ins Addon stellen. Vorher wartete der Wechsel auf den
        # nächsten Sync-Takt - und weil AddonAnalysisSync ohne
        # ausgewerteten Snapshot vorzeitig abbricht, blieb im
        # Regelfall die ALTE Auswahl im Addon stehen. Genau das war
        # der "im Spiel steht ein anderer Charakter als hier".
        #
        # getattr ist tragend, nicht kosmetisch: AcademyService
        # entsteht in CompanionManager.__init__ VOR AddonAnalysisSync.
        #
        sync = getattr(self.manager, "addon_analysis_sync", None)

        if sync is not None:
            sync.publish_now()

    def resolve_player_name(self, snapshot: RaidSnapshot) -> str:
        """
        Der Charakter, für den das Profil gebaut wird - oder `""`.

        **Rät nicht.** Bis 1.6.2 lieferte diese Funktion beim leeren
        Feld den alphabetisch ersten Spieler des Raids zurück, und
        zwar bei jedem Snapshot neu, ohne ihn je festzuschreiben. Die
        Oberfläche zeigte damit einen anderen Namen als die Nutzlast,
        die ins Addon ging, und im Spiel stand ein wildfremder
        Raider als "mein Charakter".

        Die Rate gibt es weiterhin - aber ausdrücklich, unter eigenem
        Namen und nur für den Desktop: `suggest_player_name()`, über
        `ensure_player_name()` festgeschrieben. Was hier
        herauskommt, ist immer etwas, das der Nutzer auch sieht.
        """

        return self.player_name()

    def suggest_player_name(self, snapshot: RaidSnapshot) -> str:
        """
        Wer ist vermutlich gemeint?

        Erste Wahl ist der ingame angemeldete Charakter - das Addon
        meldet ihn seit WeintCodex 1.3.3.0 (siehe
        `core/character_report_sync.py`), und er ist die einzige
        verlässliche Antwort auf diese Frage. Er zählt nur, wenn er
        auch wirklich im Raid steht; sonst bliebe eine Auswahl
        stehen, zu der es keine Daten gibt.

        Erst danach der alphabetisch erste Raider, damit die Academy
        sofort etwas Sinnvolles zeigt, statt den Nutzer erst
        konfigurieren zu lassen.
        """

        return self.suggest_player_name_from(
            evaluator.roster_names(snapshot)
        )

    def ensure_player_name(self, snapshot: RaidSnapshot) -> str:
        """
        Eine Auswahl sicherstellen und **festschreiben**.

        Der einzige Ort, an dem aus einer Vermutung eine Auswahl
        wird. Dass sie festgeschrieben wird, ist der Punkt: eine nur
        angezeigte Vermutung wäre wieder ein Name, den die Oberfläche
        kennt und die Nutzlast nicht.
        """

        current = self.player_name()

        if current:
            return current

        suggestion = self.suggest_player_name(snapshot)

        if suggestion:
            self.set_player_name(suggestion)

        return suggestion

    def reconcile_selection(self, names) -> str:
        """
        Die gespeicherte Auswahl gegen ein neues Roster abgleichen und
        zurückgeben, was die Auswahlliste anzeigen soll.

        Steht die gespeicherte Auswahl nicht (mehr) im Roster, wird
        auf den ersten Eintrag gewechselt **und das gespeichert**.
        Genau hier lag der Hauptfehler: `_sync_roster()` in
        `gui/pages/academy.py` füllte die Auswahlbox neu und setzte
        die Auswahl nur, *wenn* der gespeicherte Name noch vorkam.
        Fehlte er, stand die Box sichtbar auf dem ersten Namen,
        während die Config den alten behielt - und die Nutzlast
        entsteht aus der Config. Anzeige und Zustellung liefen
        auseinander, ohne dass irgendwo etwas fehlschlug.

        Bewusst hier und nicht in der Seite: ohne Widget testbar
        (kein Test dieses Projekts baut eines).
        """

        names = tuple(names or ())

        current = self.player_name()

        if current and match_name(current, names):
            #
            # Auf die Schreibweise des Rosters normieren - "Aldrin"
            # und "Aldrin-Everlook" sind derselbe Charakter, aber nur
            # eine der beiden Schreibweisen findet den Akteur wieder.
            #
            resolved = match_name(current, names)

            if resolved != current:
                self.set_player_name(resolved)

            return resolved

        replacement = self.suggest_player_name_from(names)

        self.set_player_name(replacement)

        return replacement

    def suggest_player_name_from(self, names) -> str:
        """
        Wie `suggest_player_name()`, aber gegen eine fertige
        Namensliste statt gegen einen Snapshot.
        """

        names = tuple(names or ())

        ingame = self.ingame_character()

        if ingame:

            match = match_name(ingame, names)

            if match:
                return match

        return names[0] if names else ""

    # --------------------------------------------------
    # Der ingame angemeldete Charakter
    # --------------------------------------------------
    # Das Addon meldet ihn seit WeintCodex 1.3.3.0 einmal pro Login
    # (Nachricht "character_report", siehe
    # core/character_report_sync.py). Er ist die einzige verlässliche
    # Antwort auf "wer bin ich" - alles andere in dieser Datei war
    # bisher geraten.
    # --------------------------------------------------

    def ingame_character(self) -> str:

        return self.manager.config.data.get(
            "academy_ingame_character",
            "",
        )

    def note_ingame_character(self, name: str, realm: str = ""):
        """
        Das Spiel hat gemeldet, wer angemeldet ist.

        Die Vorrangregel in einem Satz: **eine Auswahl von Hand
        schlägt die Spielmeldung für den Charakter, auf dem sie
        getroffen wurde - und hört auf zu schlagen, sobald das Spiel
        einen anderen meldet.** "Ich habe als Alice kurz Bobs Werte
        angesehen" darf nicht noch gelten, wenn ich als Carol
        einlogge; das wäre dieselbe Art Identitätsleiche, gegen die
        diese ganze Umstellung gebaut ist.
        """

        if not name:
            return

        config = self.manager.config

        changed = (
            config.data.get("academy_ingame_character") != name
            or config.data.get("academy_ingame_realm") != realm
        )

        if changed:
            config.data["academy_ingame_character"] = name
            config.data["academy_ingame_realm"] = realm
            config.save()

        if not config.data.get("academy_follow_game", True):
            return

        #
        # Eine Auswahl von Hand gilt weiter, solange derselbe
        # Charakter angemeldet ist wie damals.
        #
        if config.data.get("academy_player_source") == "manual":

            if names_equal(config.data.get("academy_manual_for", ""), name):
                return

        roster = self.roster(self.manager.raid_data.current())

        match = match_name(name, roster)

        if not match:
            #
            # Noch kein Raid ausgewertet, in dem dieser Charakter
            # vorkommt. Nichts umstellen - die Meldung ist gespeichert
            # und suggest_player_name() greift beim nächsten
            # ensure_player_name() darauf zu.
            #
            return

        if match == self.player_name():
            return

        config.data["academy_player_source"] = "game"
        config.data["academy_manual_for"] = ""
        config.save()

        self.set_player_name(match)

        self.manager.logger.info(
            f"Academy: folgt dem angemeldeten Charakter ({match})."
        )

    def note_manual_choice(self, name: str):
        """
        Der Nutzer hat selbst gewählt.

        Festgehalten wird nicht nur *dass*, sondern *wobei*: der
        ingame angemeldete Charakter zum Zeitpunkt der Wahl. Ohne den
        könnte die Regel oben nicht unterscheiden, ob eine alte
        Handauswahl noch gemeint ist.
        """

        config = self.manager.config

        config.data["academy_player_source"] = "manual"
        config.data["academy_manual_for"] = self.ingame_character()
        config.save()

        self.set_player_name(name)

    def roster(self, snapshot: RaidSnapshot) -> tuple[str, ...]:

        return evaluator.roster_names(snapshot)

    # --------------------------------------------------
    # Auswertung
    # --------------------------------------------------

    def build_profile(self, snapshot: RaidSnapshot) -> PlayerProfile:

        return evaluator.build_profile(
            snapshot,
            self.resolve_player_name(snapshot),
        )

    def build_plan(
        self,
        profile: PlayerProfile,
        snapshot: RaidSnapshot | None = None,
        character: str = "",
    ) -> TrainingPlan:
        """
        Der Trainingsplan eines Charakters.

        Mit `snapshot` prüft der Plan seine Lektionen zusätzlich gegen
        den gewählten Kampf und markiert sie selbst als erfüllt oder
        nicht erfüllt. Ohne ihn bleibt es beim reinen Lernpfad -
        dasselbe Verhalten wie vorher.
        """

        #
        # `character` schlägt `profile.name`, weil letzteres wörtlich
        # "-" ist, sobald der Spieler im Pull nicht gefunden wurde -
        # der Fortschritt würde dann unter diesem Unnamen gesucht und
        # der Plan zeigte alle Lektionen wieder als offen.
        #
        name = character or profile.name

        return evaluator.build_plan(
            profile,
            self.completed_for(name),
            snapshot=snapshot,
            excluded=self.excluded_for(name),
        )

    # --------------------------------------------------
    # Lernkurve
    # --------------------------------------------------

    def note_snapshot(
        self,
        snapshot: RaidSnapshot,
        *,
        origin: str = "",
        day: str = "",
        sequence: int = 0,
        source: str = "",
    ) -> bool:
        """
        Einen **beendeten** Pull für die Lernkurve aufzeichnen. Gibt
        zurück, ob dabei ein neuer Punkt entstanden ist.

        Die Regeln, welcher Pull überhaupt zählt, stehen in
        `analyzer/academy/progression.py`; hier steht die Reihenfolge,
        in der gefragt wird - und die ist der Punkt: die teuren
        Schritte (Profil bauen) kommen **nach** den billigen
        (beendet? schon bekannt?). Diese Funktion hängt am
        Snapshot-Strom und läuft damit im Sekundentakt, in der
        Wiedergabe viermal je Sekunde.

        Zwei Dinge werden hier bewusst **nicht** getan:

        - **Kein Raten des Charakters.** `resolve_player_name()`
          liefert die getroffene Auswahl oder "". Eine Kurve unter
          einem geratenen Namen wäre die Kurve eines Fremden, und sie
          fiele erst Wochen später auf.
        - **Kein Aufzeichnen ohne Bewertung.** Ist der Spieler im Pull
          gar nicht enthalten (er war nicht dabei, oder die Quelle
          liefert ihn nicht), entsteht ein leeres Profil - und ein
          Punkt daraus wäre eine Null, wo nichts gemessen wurde.
        """

        if not qualifies(snapshot):
            return False

        character = self.resolve_player_name(snapshot)

        if not character:
            return False

        key = pull_key(snapshot, origin, day or today())

        if self.history.knows(character, key):
            return False

        profile = self.build_profile(snapshot)

        if not profile.has_data:
            return False

        record = record_from_profile(
            profile,
            snapshot,
            key=key,
            day=day or today(),
            sequence=sequence,
            source=source,
            recorded_at=time.time(),
        )

        if not self.history.note(character, record):
            return False

        self.manager.logger.info(
            f"Academy: {record.label} für {character} aufgezeichnet."
        )

        return True

    def curve(
        self,
        character: str = "",
        source: str = "",
        spec: str = "",
        limit: int = CURVE_LIMIT,
    ) -> tuple[PullRecord, ...]:
        """
        Die Punkte der Lernkurve eines Charakters.

        Ohne Namen die des gewählten Charakters - dieselbe Auswahl,
        aus der auch das Profil entsteht.
        """

        return self.history.curve(
            character or self.player_name(),
            source,
            spec,
            limit,
        )

    # --------------------------------------------------

    def progress_for(self, profile: PlayerProfile) -> tuple[int, int]:
        """
        (erledigt, gesamt) gemessen am kompletten Lektionskatalog
        dieses Charakters.

        Bewusst nicht am Trainingsplan gemessen: der Plan zeigt nur
        die nächsten Schritte, seine Länge ändert sich also mit jeder
        erledigten Lektion. Als Fortschrittsanzeige wäre das
        irreführend - "1 von 7" nach "0 von 6" sähe nach Rückschritt
        aus.
        """

        catalog = self.active_lessons(profile)

        done = self.completed_for(profile.name)

        completed = sum(
            1
            for lesson in catalog
            if lesson.lesson_id in done
        )

        return completed, len(catalog)

    def active_lessons(self, profile: PlayerProfile) -> tuple:
        """
        Der Katalog dieses Charakters ohne die abgewählten Lektionen.

        Die abgewählten müssen hier heraus, sonst könnte die
        Fortschrittsanzeige nie 100 Prozent erreichen: der Nenner
        enthielte Lektionen, die der Spieler ausdrücklich nicht
        bearbeiten will.
        """

        hidden = self.excluded_for(profile.name)

        return tuple(
            lesson
            for lesson in lessons_for_actor(
                profile.actor,
                profile.encounter_name,
            )
            if lesson.lesson_id not in hidden
        )

    # --------------------------------------------------
    # Fortschritt
    # --------------------------------------------------

    def completed_for(self, player_name: str) -> frozenset[str]:

        if not player_name:
            return frozenset()

        return frozenset(
            self.data["completed"].get(player_name, [])
        )

    def is_completed(self, player_name: str, lesson_id: str) -> bool:

        return lesson_id in self.completed_for(player_name)

    def set_completed(
        self,
        player_name: str,
        lesson_id: str,
        completed: bool,
    ):
        """
        Markiert eine Lektion als erledigt bzw. wieder offen.
        """

        if not player_name or not lesson_id:
            return

        entries = list(
            self.data["completed"].get(player_name, [])
        )

        changed = False

        if completed and lesson_id not in entries:

            entries.append(lesson_id)

            changed = True

        elif not completed and lesson_id in entries:

            entries.remove(lesson_id)

            changed = True

        if not changed:
            return

        self.data["completed"][player_name] = entries

        self.save()

        lesson = find_lesson(lesson_id)

        title = lesson.title if lesson else lesson_id

        if completed:

            self.manager.logger.success(
                f"Academy: \"{title}\" abgeschlossen."
            )

        else:

            self.manager.logger.info(
                f"Academy: \"{title}\" wieder geöffnet."
            )

    def reset(self, player_name: str):
        """
        Setzt den Lernpfad eines Charakters zurück.
        """

        if player_name not in self.data["completed"]:
            return

        del self.data["completed"][player_name]

        self.save()

        self.manager.logger.info(
            f"Academy: Lernpfad von {player_name} zurückgesetzt."
        )

    # --------------------------------------------------
    # Abwahl von Lektionen
    # --------------------------------------------------
    #
    # Standardmäßig ist jede Lektion aktiv. Gespeichert werden
    # deshalb nur die Ausnahmen - siehe die Begründung im
    # Konstruktor.
    #

    def excluded_for(self, player_name: str) -> frozenset[str]:

        if not player_name:
            return frozenset()

        return frozenset(
            self.data["excluded"].get(player_name, [])
        )

    def is_enabled(self, player_name: str, lesson_id: str) -> bool:

        return lesson_id not in self.excluded_for(player_name)

    def set_enabled(
        self,
        player_name: str,
        lesson_id: str,
        enabled: bool,
    ):
        """
        Wählt eine Lektion für den Trainingsplan ab oder wieder an.
        """

        if not player_name or not lesson_id:
            return

        entries = list(
            self.data["excluded"].get(player_name, [])
        )

        changed = False

        if not enabled and lesson_id not in entries:

            entries.append(lesson_id)

            changed = True

        elif enabled and lesson_id in entries:

            entries.remove(lesson_id)

            changed = True

        if not changed:
            return

        self.data["excluded"][player_name] = entries

        self.save()

        lesson = find_lesson(lesson_id)

        title = lesson.title if lesson else lesson_id

        self.manager.logger.info(
            f"Academy: \"{title}\" "
            + ("wieder aufgenommen." if enabled else "abgewählt.")
        )

    def set_category_enabled(
        self,
        profile: PlayerProfile,
        category: str,
        enabled: bool,
    ):
        """
        Einen ganzen Bereich auf einmal an- oder abwählen.
        """

        for lesson in lessons_for_actor(
            profile.actor,
            profile.encounter_name,
        ):

            if lesson.category == category:

                self.set_enabled(profile.name, lesson.lesson_id, enabled)

    def reset_selection(self, player_name: str):
        """
        Alle Abwahlen aufheben - vom Zurücksetzen des Fortschritts
        bewusst getrennt: das eine ist "ich fange neu an", das andere
        "zeig mir wieder alles".
        """

        if player_name not in self.data["excluded"]:
            return

        del self.data["excluded"][player_name]

        self.save()

        self.manager.logger.info(
            f"Academy: Lektionsauswahl von {player_name} zurückgesetzt."
        )
