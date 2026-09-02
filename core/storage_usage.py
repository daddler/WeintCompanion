"""
Was hier liegen bleibt, und ab wann es jemandem gesagt gehört.

Jede Addon-Aktualisierung legt zwei Dateien an, die danach niemand
mehr anfasst: das heruntergeladene ZIP unter `Paths.downloads()` und
das Sicherheitsnetz unter `Paths.backups()` (siehe
`core/installer_workflow.py`). Gelöscht wird beides nie von selbst -
das ist richtig so, ein Backup, das sich selbst wegräumt, ist keins -
aber es gab auch nichts, das je darauf hingewiesen hätte. Die einzige
Stelle, an der die Zahlen überhaupt stehen, ist *Einstellungen →
Backups*, und dorthin geht niemand, der nichts sucht. Nach einem
halben Jahr Releases liegen dort zwei Dutzend Dateien.

Diese Datei ist die Antwort auf "ist das zu viel", und sie ist
absichtlich **Qt-frei und ohne Netzzugriff** - aus demselben Grund
wie `roster_target()` und `build_profile_payload()`: *welcher Satz
dasteht* ist genau die Stelle, an der etwas falsch sein kann, und ein
Fenster braucht man dafür nicht. Nur `scan()` fasst die Platte an.

Fünf Regeln, die nicht Geschmack sind:

- **Gezählt wird je Ordner, nicht zusammen.** Drei Downloads und vier
  Backups sind nicht sieben Dateien: es sind zwei verschiedene
  Aufräumarbeiten mit zwei verschiedenen Knöpfen, und ein
  gemeinsamer Zähler würde melden, wo in keinem der beiden Ordner
  etwas zu tun ist.
- **Die Menge wird mitgenannt.** Eine Zahl allein sagt nicht, worum
  es geht: sechs Addon-Backups sind wenige Megabyte, sechs
  Companion-Downloads sind fast ein Gigabyte. Wer nur "6 Dateien"
  liest, kann nicht entscheiden, ob es sich lohnt.
- **Ein fehlender Ordner ist leer, kein Fehler.** Vor der ersten
  Aktualisierung gibt es ihn schlicht noch nicht.
- **Gezählt werden Dateien, keine Ordner.** Dieselbe Regel, nach der
  *Einstellungen → Backups* schon immer gezählt und gelöscht hat -
  zwei verschiedene Zählweisen für dieselbe Anzeige wären genau die
  Doppelung, an der zwei Zeilen dieselbe Zahl verschieden nennen.
- **Die Grenze steht hier und nicht in der Oberfläche.** Die Meldung,
  die Zeile auf der Einstellungsseite und der Test lesen dieselbe
  Zahl; drei Fassungen davon liefen auseinander, sobald eine
  angefasst wird.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


#
# "Mehr als fünf" - gemeldet wird also ab der sechsten Datei. Bewusst
# nicht ab der ersten: eine Aktualisierung darf ihr Backup und ihr
# ZIP hinterlassen, ohne dass das gleich ein Befund ist. Und bewusst
# nicht viel später: bis dahin ist der Ordner noch überschaubar genug,
# dass "alle löschen" eine ruhige Entscheidung ist.
#

WARN_COUNT = 5


#
# Anzeigenamen der beiden Ordner. Sie stehen in der Meldung, in der
# Sprechblase und auf der Einstellungsseite - deshalb an einer Stelle.
#

DOWNLOADS = "downloads"
BACKUPS = "backups"

LABELS = {
    DOWNLOADS: "Downloads",
    BACKUPS: "Backups",
}


@dataclass(frozen=True)
class FolderUsage:
    """
    Was in einem der beiden Ordner liegt.

    `key` ist DOWNLOADS oder BACKUPS, `label` der Anzeigename dazu.
    """

    key: str
    count: int = 0
    size: int = 0

    @property
    def label(self) -> str:
        return LABELS.get(self.key, self.key)

    @property
    def over_limit(self) -> bool:
        return self.count > WARN_COUNT


@dataclass(frozen=True)
class StorageReport:

    downloads: FolderUsage
    backups: FolderUsage

    @property
    def folders(self) -> tuple[FolderUsage, ...]:
        return (self.downloads, self.backups)

    @property
    def crowded(self) -> tuple[FolderUsage, ...]:
        """
        Die Ordner über der Grenze, in der Reihenfolge, in der sie auf
        der Einstellungsseite stehen.
        """

        return tuple(
            folder
            for folder in self.folders
            if folder.over_limit
        )

    @property
    def needs_cleanup(self) -> bool:
        return bool(self.crowded)

    @property
    def signature(self) -> tuple[int, int]:
        """
        Woran erkannt wird, dass sich etwas geändert hat.

        Bewusst nur die beiden Zahlen und nicht die Grössen: eine
        halb geschriebene Datei wächst währenddessen und würde sonst
        bei jedem Takt eine Änderung melden.
        """

        return (self.downloads.count, self.backups.count)


def empty_report() -> StorageReport:
    """
    Der Stand vor der ersten Zählung.

    Ausdrücklich nicht `None`: die Oberfläche fragt danach, bevor der
    erste Sync-Takt gelaufen ist, und "noch nichts gezählt" sieht dort
    genauso aus wie "nichts da" - beide verlangen dasselbe, nämlich
    keine Meldung.
    """

    return StorageReport(
        downloads=FolderUsage(DOWNLOADS),
        backups=FolderUsage(BACKUPS),
    )


def count_folder(path: Path | None, key: str) -> FolderUsage:
    """
    Dateien und belegter Platz eines Ordners.

    Ein Ordner, den es nicht gibt, ist leer. Eine Datei, die zwischen
    Auflisten und Messen verschwindet (der Nutzer räumt gerade selbst
    auf), zählt mit, aber mit Grösse 0 - eine Ausnahme aus einer
    reinen Zählung wäre der schlechtere Ausgang.
    """

    count = 0
    size = 0

    if path is not None:

        try:
            entries = list(path.iterdir())

        except OSError:
            entries = []

        for entry in entries:

            try:

                if not entry.is_file():
                    continue

                count += 1
                size += entry.stat().st_size

            except OSError:
                continue

    return FolderUsage(key, count, size)


def scan(download_dir: Path | None, backup_dir: Path | None) -> StorageReport:
    """
    Die einzige Stelle dieser Datei, die die Platte anfasst.

    Die beiden Pfade werden hereingereicht statt hier aus `Paths`
    geholt, damit die Auswertung ohne die Verzeichnisse des Nutzers
    prüfbar bleibt - dieselbe Aufteilung wie zwischen
    `warcraftlogs_payload.py` und `warcraftlogs_client.py`.
    """

    return StorageReport(
        downloads=count_folder(download_dir, DOWNLOADS),
        backups=count_folder(backup_dir, BACKUPS),
    )


def format_size(size: int) -> str:
    """
    Bytes als Satzbaustein, mit deutschem Dezimalkomma.

    Unterhalb eines Megabyte wird auf ganze Zahlen gerundet: eine
    Nachkommastelle bei "0,4 MB" behauptet eine Genauigkeit, die für
    die Frage "lohnt sich das Löschen" niemanden interessiert.
    """

    if size <= 0:
        return "0 MB"

    megabytes = size / (1024 * 1024)

    if megabytes >= 1024:

        gigabytes = megabytes / 1024

        return f"{gigabytes:.1f} GB".replace(".", ",")

    if megabytes < 1:
        return "unter 1 MB"

    if megabytes < 10:
        return f"{megabytes:.1f} MB".replace(".", ",")

    return f"{round(megabytes)} MB"


def folder_text(usage: FolderUsage) -> str:
    """
    Die Zeile unter dem Ordnernamen auf der Einstellungsseite.
    """

    if usage.count == 0:

        if usage.key == DOWNLOADS:
            return "Keine Downloads im Zwischenspeicher"

        return "Keine Backups vorhanden"

    if usage.key == DOWNLOADS:

        head = (
            "1 Datei im Download-Zwischenspeicher"
            if usage.count == 1
            else f"{usage.count} Dateien im Download-Zwischenspeicher"
        )

    else:

        head = (
            "1 Backup vorhanden"
            if usage.count == 1
            else f"{usage.count} Backups vorhanden"
        )

    return f"{head} · {format_size(usage.size)}"


def folder_hint(usage: FolderUsage) -> str:
    """
    Der Zusatz, wenn ein Ordner über der Grenze liegt - und sonst
    nichts.

    Er sagt, warum die Dateien da sind und dass Löschen nichts kaputt
    macht. Ohne diesen Satz liest sich ein Warnhinweis über Backups
    wie eine Aufforderung, sein Sicherheitsnetz wegzuwerfen.
    """

    if not usage.over_limit:
        return ""

    if usage.key == DOWNLOADS:

        return (
            "Jede Aktualisierung lädt ihr Archiv hierher. Nach der "
            "Installation wird es nicht mehr gebraucht."
        )

    return (
        "Vor jeder Aktualisierung wird der Addon-Ordner gesichert. "
        "Das jüngste Backup reicht als Sicherheitsnetz."
    )


def cleanup_text(report: StorageReport) -> str:
    """
    Der eine Satz, der als Meldung und als Sprechblase hinausgeht.

    Er nennt beide Ordner in einem Satz, wenn beide übervoll sind -
    zwei Meldungen übereinander wären zweimal derselbe Weg zu
    demselben Knopf.
    """

    crowded = report.crowded

    if not crowded:
        return ""

    parts = []

    for usage in crowded:

        parts.append(
            f"{usage.count} {usage.label} ({format_size(usage.size)})"
        )

    return (
        "Hier sammelt sich etwas an: "
        + " und ".join(parts)
        + ". Aufräumen?"
    )
