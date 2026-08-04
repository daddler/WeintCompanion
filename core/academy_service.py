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

from analyzer.academy import evaluator
from analyzer.academy.lessons import find_lesson, lessons_for_actor
from analyzer.academy.models import PlayerProfile, TrainingPlan
from analyzer.models import RaidSnapshot

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

    def resolve_player_name(self, snapshot: RaidSnapshot) -> str:
        """
        Der Charakter, für den das Profil gebaut wird.

        Ist noch keiner gewählt, wird der erste Spieler des aktuellen
        Raids genommen - so zeigt die Academy sofort etwas
        Sinnvolles, statt den Nutzer erst konfigurieren zu lassen.
        """

        name = self.player_name()

        if name:
            return name

        names = evaluator.roster_names(snapshot)

        if names:
            return names[0]

        return ""

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
    ) -> TrainingPlan:
        """
        Der Trainingsplan eines Charakters.

        Mit `snapshot` prüft der Plan seine Lektionen zusätzlich gegen
        den gewählten Kampf und markiert sie selbst als erfüllt oder
        nicht erfüllt. Ohne ihn bleibt es beim reinen Lernpfad -
        dasselbe Verhalten wie vorher.
        """

        return evaluator.build_plan(
            profile,
            self.completed_for(profile.name),
            snapshot=snapshot,
            excluded=self.excluded_for(profile.name),
        )

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
