"""
Die Bruecke von dieser Generation zur naechsten.

    WeintCompanion 4.x  ->  Companion-Forever 5.x

Diese Schicht ist vollstaendig **ausgeschaltet**, solange
`core/migration/target.MIGRATION_ENABLED_DEFAULT` auf `False` steht
(und das ist die Vorgabe). Sie stellt dann keine Anfrage, zeigt
nichts an und schreibt nichts.

Aufbau - jede Datei beantwortet eine Frage:

    target.py      wohin, und darf ich ueberhaupt
    releases.py    was liegt dort (GitHub oder Datei)
    discovery.py   ist davon etwas brauchbar
    assets.py      welche Datei gehoert zu diesem Rechner
    integrity.py   ist es wirklich diese Datei
    payload.py     was nimmt der Nutzer mit
    handover.py    bereitstellen und starten
    state.py       wo stehen wir gerade
    service.py     der Ablauf, der die anderen acht benutzt

Was hier **nicht** hineingehoert: irgendetwas aus Companion-Forever.
Die beiden Anwendungen kennen einander ausschliesslich ueber den
Release-Vertrag (`docs/companion-forever-release-contract.md`) - kein
Quelltext, keine Abhaengigkeit, keine Annahme ueber die
Projektstruktur der anderen Seite.
"""

from core.migration.service import (
    MigrationOffer,
    MigrationResult,
    MigrationService,
)
from core.migration.state import MigrationState
from core.migration.target import (
    MigrationTarget,
    migration_enabled,
    target_for,
)

__all__ = [
    "MigrationOffer",
    "MigrationResult",
    "MigrationService",
    "MigrationState",
    "MigrationTarget",
    "migration_enabled",
    "target_for",
]
