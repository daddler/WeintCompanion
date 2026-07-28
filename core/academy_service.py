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
        # Aufbau: {"completed": {"<Charaktername>": ["<lesson_id>", ...]}}
        #
        # Der Fortschritt hängt am Charakter, nicht am Konto: ein
        # Zweitcharakter mit anderer Klasse hat einen eigenen
        # Lernpfad.
        #

        self.data: dict = {"completed": {}}

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

                completed = loaded.get("completed")

                if isinstance(completed, dict):

                    self.data["completed"] = {
                        str(name): [str(value) for value in ids]
                        for name, ids in completed.items()
                        if isinstance(ids, list)
                    }

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

            self.data = {"completed": {}}

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

    def build_plan(self, profile: PlayerProfile) -> TrainingPlan:

        return evaluator.build_plan(
            profile,
            self.completed_for(profile.name),
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

        catalog = lessons_for_actor(profile.actor)

        done = self.completed_for(profile.name)

        completed = sum(
            1
            for lesson in catalog
            if lesson.lesson_id in done
        )

        return completed, len(catalog)

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
