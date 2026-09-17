"""
Wo im Wechsel wir gerade stehen - und was davon einen Neustart
ueberlebt.

WARUM EIN ZUSTAND UND NICHT DREI BOOLESCHE WERTE
------------------------------------------------

Ein Generationswechsel ist der einzige Vorgang dieser App, der
mitten im Ablauf abbrechen und den Rechner dabei veraendert
zurueklassen kann: heruntergeladen, aber nicht geprueft; geprueft,
aber nicht installiert. Wer das mit "downloading = True" und
"installed = False" beschreibt, hat spaetestens beim dritten
Abbruchgrund eine Kombination, die es nicht geben darf und trotzdem
in der Datei steht.

Deshalb ein Zustand mit erlaubten Uebergaengen. `advance()` laesst
nur zu, was vorgesehen ist, und der Rest des Systems muss nicht
pruefen, ob "INSTALLED nach DOWNLOADING" gerade Sinn ergibt.

WAS GESPEICHERT WIRD UND WAS NICHT
----------------------------------

Gespeichert wird, was beim naechsten Start gebraucht wird: Ziel,
Fassung, Zustand, Fehler, ob abgeschlossen, und welche Fassung der
Nutzer weggeklickt hat. **Nicht** gespeichert wird der Pfad der
heruntergeladenen Datei - er ist nach einem Neustart ohnehin
fragwuerdig, und ein alter Pfad aus einer Datei ist der bequemste
Weg, beim naechsten Mal die falsche Datei zu starten.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

from core.migration.target import STATE_KEY


class MigrationState(str, Enum):

    NOT_AVAILABLE = "not_available"
    AVAILABLE = "available"
    CONFIRMED = "confirmed"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    INSTALLED = "installed"
    COMPLETED = "completed"
    FAILED = "failed"


#
# Erlaubte Uebergaenge. Aus FAILED geht es zurueck nach AVAILABLE
# (erneut versuchen) - ein Fehlschlag ist kein Endzustand, sondern
# eine Runde, die nicht geklappt hat. Aus COMPLETED geht es nirgends
# mehr hin: wer nach einem abgeschlossenen Wechsel erneut wechseln
# will, faengt bei NOT_AVAILABLE an (`reset()`).
#

TRANSITIONS = {
    MigrationState.NOT_AVAILABLE: (MigrationState.AVAILABLE,),
    MigrationState.AVAILABLE: (
        MigrationState.CONFIRMED,
        MigrationState.NOT_AVAILABLE,
    ),
    MigrationState.CONFIRMED: (
        MigrationState.DOWNLOADING,
        MigrationState.FAILED,
        MigrationState.AVAILABLE,
    ),
    MigrationState.DOWNLOADING: (
        MigrationState.DOWNLOADED,
        MigrationState.FAILED,
    ),
    MigrationState.DOWNLOADED: (
        MigrationState.VERIFYING,
        MigrationState.FAILED,
    ),
    MigrationState.VERIFYING: (
        MigrationState.INSTALLING,
        MigrationState.FAILED,
    ),
    MigrationState.INSTALLING: (
        MigrationState.INSTALLED,
        MigrationState.FAILED,
    ),
    MigrationState.INSTALLED: (
        MigrationState.COMPLETED,
        MigrationState.FAILED,
    ),
    MigrationState.COMPLETED: (),
    MigrationState.FAILED: (
        MigrationState.AVAILABLE,
        MigrationState.NOT_AVAILABLE,
        MigrationState.CONFIRMED,
    ),
}


def can_advance(current: MigrationState, following: MigrationState) -> bool:

    if current is following:
        return True

    return following in TRANSITIONS.get(current, ())


def _now() -> str:

    return datetime.now().isoformat(timespec="seconds")


@dataclass
class MigrationRecord:
    """
    Der gespeicherte Stand. Alle Felder haben eine Vorgabe - eine
    Konfiguration aus einer aelteren Fassung hat sie noch nicht, und
    ein fehlendes Feld darf nie ein Fehler sein.
    """

    state: str = MigrationState.NOT_AVAILABLE.value
    target: str = ""
    target_version: str = ""
    source_version: str = ""
    asset_name: str = ""
    completed: bool = False
    dry_run: bool = False
    error: str = ""
    updated_at: str = ""
    completed_at: str = ""
    postponed_version: str = ""
    postponed_at: str = ""

    @property
    def status(self) -> MigrationState:

        try:
            return MigrationState(self.state)
        except ValueError:
            return MigrationState.NOT_AVAILABLE

    def is_completed_for(self, version: str) -> bool:
        """
        Ist genau diese Fassung schon abgeschlossen?

        Absichtlich fassungsgenau: ein abgeschlossener Wechsel auf
        5.0.0 darf 5.1.0 nicht verschlucken. Fuer "nicht bei jedem
        Start erneut anbieten" reicht das trotzdem, denn nach dem
        Wechsel startet der Nutzer die neue App - und die alte fragt
        ohnehin nach ihrer *naechsten* Generation.
        """

        if not self.completed:
            return False

        return bool(version) and self.target_version == version

    def is_postponed_for(self, version: str) -> bool:

        return bool(version) and self.postponed_version == version


class MigrationStore:
    """
    Der Stand in der bestehenden Konfiguration, unter einem eigenen
    Schluessel (`forever_migration_state`).

    Kein eigener Dateiformat-Zoo: `Config.save()` schreibt bereits
    atomar (siehe `docs/development/paths-and-storage.md`), und eine
    zweite Datei waere eine zweite Stelle, an der ein Absturz etwas
    Halbes hinterlassen kann.
    """

    def __init__(self, config):

        self.config = config

    # --------------------------------------------------

    def load(self) -> MigrationRecord:

        data = {}

        if self.config is not None:

            raw = getattr(self.config, "data", {}).get(STATE_KEY)

            if isinstance(raw, dict):
                data = raw

        known = set(MigrationRecord.__dataclass_fields__)

        return MigrationRecord(
            **{key: value for key, value in data.items() if key in known}
        )

    # --------------------------------------------------

    def save(self, record: MigrationRecord) -> MigrationRecord:

        if self.config is None:
            return record

        record.updated_at = _now()

        self.config.data[STATE_KEY] = asdict(record)

        self.config.save()

        return record

    # --------------------------------------------------

    def advance(
        self,
        state: MigrationState,
        target: str = "",
        version: str = "",
        asset_name: str = "",
        source_version: str = "",
        error: str = "",
        dry_run: bool | None = None,
    ) -> MigrationRecord:
        """
        Einen Schritt weiter - oder gar nicht.

        Ein unerlaubter Uebergang wird nicht gespeichert und wirft
        auch nicht: er gibt den unveraenderten Stand zurueck. Der
        Zustand ist eine Buchfuehrung ueber den Ablauf, nicht sein
        Steuerwerk; ein Buchungsfehler darf den Wechsel nicht mitten
        im Download mit einer Ausnahme zerreissen.
        """

        record = self.load()

        if not can_advance(record.status, state):
            return record

        record.state = state.value

        if target:
            record.target = target

        if version:
            record.target_version = version

        if asset_name:
            record.asset_name = asset_name

        if source_version:
            record.source_version = source_version

        if dry_run is not None:
            record.dry_run = bool(dry_run)

        record.error = error or ""

        if state is MigrationState.COMPLETED:

            record.completed = True
            record.completed_at = _now()

        return self.save(record)

    # --------------------------------------------------

    def postpone(self, version: str) -> MigrationRecord:
        """
        "Spaeter": die angebotene Fassung wird bis auf Weiteres nicht
        mehr angeboten. Fassungsgenau - die naechste fragt erneut.
        """

        record = self.load()

        record.postponed_version = version or ""
        record.postponed_at = _now()

        return self.save(record)

    # --------------------------------------------------

    def reset(self) -> MigrationRecord:

        return self.save(MigrationRecord())
