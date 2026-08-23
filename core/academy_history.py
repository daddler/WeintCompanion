"""
Die Ablage der Lernkurve.

Die HTTP-lose Schwester von `core/academy_service.py`: sie hält fest,
wie ein Charakter in vergangenen Pulls bewertet wurde, damit die
Academy nicht länger nur den Kampf kennt, der gerade auf dem
Bildschirm steht. Die Regeln, *welcher* Pull aufgezeichnet wird und
was aus mehreren davon abzulesen ist, stehen in
`analyzer/academy/progression.py` - hier steht nur, wohin es kommt.

**Eigene Datei und nicht `academy_progress.json`.** Dort stehen
erledigte und abgewählte Lektionen: eine kurze Liste, die der Nutzer
selbst füllt. Hier wächst eine Reihe von Messwerten, die das Programm
schreibt. Sie zusammenzulegen hiesse, dass ein defekter Messwert den
Lernfortschritt mitnimmt - und der ist das einzige in der Academy,
das sich nicht wiederherstellen lässt.

**Unter `Paths.config()` und nicht unter `cache()`**, obwohl es
Messwerte sind. Sie lassen sich nicht neu berechnen: der Bericht, aus
dem eine Bewertung stammt, ist bei WarcraftLogs irgendwann nicht mehr
abrufbar, und ein Live-Pull ist ohnehin nur in dem Augenblick zu
sehen, in dem er stattfindet. Was einmal gemessen wurde, ist damit
Nutzerdatum und kein Zwischenergebnis - dieselbe Überlegung wie bei
`characters.json`.
"""

from __future__ import annotations

import json
import os
import time

from datetime import datetime

from analyzer.academy.progression import (
    PullRecord,
    from_dict,
    select,
    sort_records,
    to_dict,
)

from core.paths import Paths


HISTORY_FILE = "academy_history.json"


#
# Wie viele Pulls je Charakter aufgehoben werden. Die Kurve zeigt
# `CURVE_LIMIT` davon; der Rest ist Vorrat, damit ein Filter (Quelle,
# Spezialisierung) nicht sofort auf eine leere Kurve führt. Nach
# oben begrenzt, weil diese Datei bei jedem Schreiben komplett
# ausgetauscht wird und niemand von einer unbegrenzt wachsenden
# Datei etwas hat.
#

LIMIT = 60


class AcademyHistory:
    """
    Aufgezeichnete Pulls je Charakter.

    Aufbau der Datei:

        {"pulls": {"<Charakter>": [<Datensatz>, ...]}}

    Am Charakter und nicht am Konto, wie schon der Lernfortschritt:
    ein Zweitcharakter hat einen eigenen Lernpfad und damit auch eine
    eigene Kurve.
    """

    def __init__(self, manager):

        self.manager = manager

        self.file = Paths.config() / HISTORY_FILE

        self.data: dict[str, list[PullRecord]] = {}

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

        except Exception as exc:

            #
            # Wie beim Lernfortschritt: eine defekte Datei darf die
            # Academy nicht unbenutzbar machen. Sie wird verworfen,
            # der Vorfall steht im Protokoll, und die Aufzeichnung
            # beginnt von vorn.
            #

            self.manager.logger.warning(
                f"Academy-Verlauf konnte nicht gelesen werden "
                f"({exc}) - er wird neu aufgebaut."
            )

            self.data = {}

            return

        rohdaten = (loaded or {}).get("pulls")

        if not isinstance(rohdaten, dict):
            return

        for character, rows in rohdaten.items():

            if not isinstance(rows, list):
                continue

            records = [
                record
                for record in (from_dict(row) for row in rows)
                if record is not None
            ]

            if records:
                self.data[str(character)] = list(sort_records(records))

    def save(self):
        """
        Atomar schreiben - erst temporär, dann ersetzen, wie in
        `core/config.py` und im Lernfortschritt.
        """

        try:

            self.file.parent.mkdir(parents=True, exist_ok=True)

            tmp_path = self.file.with_suffix(self.file.suffix + ".tmp")

            with open(tmp_path, "w", encoding="utf-8") as handle:

                json.dump(
                    {
                        "pulls": {
                            character: [
                                to_dict(record) for record in records
                            ]
                            for character, records in self.data.items()
                        }
                    },
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

            os.replace(tmp_path, self.file)

        except OSError as exc:

            self.manager.logger.error(
                f"Academy-Verlauf konnte nicht gespeichert werden: {exc}"
            )

    # --------------------------------------------------
    # Lesen
    # --------------------------------------------------

    def all_records(self, character: str) -> tuple[PullRecord, ...]:

        return tuple(self.data.get(character, ()))

    def knows(self, character: str, key: str) -> bool:
        """
        Ob dieser Pull schon aufgezeichnet ist.

        Die eine Frage, an der hängt, ob aus einem Pull ein Punkt
        wird oder fünf: die Live-Quelle liefert denselben beendeten
        Kampf minutenlang weiter aus.
        """

        return any(
            record.key == key
            for record in self.data.get(character, ())
        )

    def curve(
        self,
        character: str,
        source: str = "",
        spec: str = "",
        limit: int = 0,
    ) -> tuple[PullRecord, ...]:
        """
        Die Punkte der Kurve - gefiltert und geordnet, siehe
        `progression.select()`.
        """

        records = self.data.get(character, ())

        if limit > 0:
            return select(records, source, spec, limit)

        return select(records, source, spec)

    # --------------------------------------------------
    # Schreiben
    # --------------------------------------------------

    def note(self, character: str, record: PullRecord) -> bool:
        """
        Einen Pull aufzeichnen. Gibt zurück, ob er neu war.

        Ein bereits bekannter Pull wird **nicht** überschrieben: er
        ist derselbe Kampf mit derselben Bewertung, und ein Schreiben
        ohne Änderung wäre eine Datei-Operation je Sekunde, solange
        die Live-Quelle ihn ausliefert.
        """

        if not character or not record.key or not record.rated:
            return False

        records = self.data.setdefault(character, [])

        if any(vorhanden.key == record.key for vorhanden in records):
            return False

        records.append(record)

        #
        # Geordnet halten und begrenzen. Geschnitten wird **vorn**,
        # also am ältesten Ende - `sort_records()` ordnet nach dem
        # Zeitpunkt des Kampfes, nicht dem der Aufzeichnung, sodass
        # ein nachträglich geöffneter alter Pull auch dann als der
        # ältere gilt, wenn er als letzter angesehen wurde.
        #

        geordnet = list(sort_records(records))

        self.data[character] = geordnet[-LIMIT:]

        self.save()

        return True


# --------------------------------------------------
# Der Raidtag
# --------------------------------------------------


def today() -> str:
    """
    Der heutige Tag als "JJJJ-MM-TT" - der Raidtag eines Live-Pulls.

    Eigene Funktion, damit ein Test ihn setzen kann, ohne an der Uhr
    zu drehen.
    """

    return time.strftime("%Y-%m-%d", time.localtime())


def day_from_iso(value: str) -> str:
    """
    Der Raidtag eines Berichts, aus seinem Zeitstempel.

    Der Bot nennt ihn in UTC; gerechnet wird in die **lokale**
    Zeitzone, denn ein Raid, der um 22:30 Ortszeit endet, gehört zum
    Mittwoch und nicht zum Donnerstag - und genau so steht er auch im
    Auswahlfeld des Archivs (`_format_report_date()`).

    Leer bei allem Unlesbaren: ein geratener Tag brächte die Kurve in
    eine Reihenfolge, die nie jemand gespielt hat.
    """

    text = str(value or "").strip()

    if not text:
        return ""

    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))

    except ValueError:
        return ""

    if moment.tzinfo is not None:
        moment = moment.astimezone()

    return moment.strftime("%Y-%m-%d")
