"""
Das Sicherheitsnetz vor jeder Aktualisierung.

Bis 2.7.1 sicherte es genau das Falsche: den **Addon-Ordner**, also
Dateien, die jederzeit wieder von GitHub kommen - und nicht die
`SavedVariables`, in denen alles steht, was der Spieler selbst
eingetragen hat: Bossnotizen, Twinkliste, Encounter-Fortschritt,
Lernfortschritt der Academy, WeakAura-Bibliothek. Das ist genau
andersherum als es sein sollte, denn nur eines von beidem ist
unwiederbringlich.

Der Installer fasst die `SavedVariables` nicht an (er tauscht
ausschliesslich `Interface/AddOns/WeintCodex`, siehe
`core/installer.py`), und WoW tut es bei einem Addon-Update auch
nicht. Trotzdem gehören sie ins Backup: eine Aktualisierung ist der
Moment, in dem am meisten gleichzeitig passiert - die Anwendung
schreibt, WoW wird neu geladen, der Spieler startet neu -, und ein
Backup, das den einen Teil auslässt, der sich nicht wiederbeschaffen
lässt, ist kein Backup.

Drei Regeln, die nicht Geschmack sind:

- **Zwei Bereiche in einem Archiv, sauber getrennt.** Der Addon-Ordner
  liegt unter `WeintCodex/…`, der Spielstand unter `WTF/…` - also
  jeweils unter dem Pfad, relativ zu dem er zurückgehört. `restore()`
  packt **nur** den Addon-Teil aus; ein `extractall()` über das ganze
  Archiv würde einen `WTF`-Ordner mitten in `Interface/AddOns` anlegen.
- **Zurückgeholt wird der Spielstand nur, wenn jemand es ausdrücklich
  verlangt.** Er ist beim Update nie verloren gegangen; ihn beim
  nächsten Fehlschlag automatisch mit zurückzuschieben, würde einem
  Spieler unbemerkt eine Woche Fortschritt nehmen.
- **Vor dem Überschreiben wird die vorhandene Datei beiseitegelegt.**
  Eine Wiederherstellung, die selbst nichts hinterlässt, ist eine
  Einbahnstrasse - und wer sie versehentlich auslöst, hätte keinen
  Weg zurück.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import zipfile

from core.paths import Paths


#
# Die beiden Ordnernamen im Archiv. Sie sind zugleich der Pfad,
# relativ zu dem der jeweilige Teil zurückgehört.
#

ADDON_PREFIX = "WeintCodex/"
SAVED_PREFIX = "WTF/"

#
# Die Datei, die beim Zurückholen beiseitegelegt wird.
#

ASIDE_SUFFIX = ".vor-wiederherstellung"


def _safe_members(archive: zipfile.ZipFile, prefix: str) -> list[str]:
    """
    Die Einträge eines Bereichs - ohne alles, was aus ihm herausführt.

    Die Archive stammen aus dieser Datei, aber eine ZIP-Datei liegt im
    Zwischenspeicher des Nutzers und lässt sich austauschen; ein
    Eintrag mit `..` oder absolutem Pfad würde beim Auspacken
    irgendwohin schreiben.
    """

    members = []

    for name in archive.namelist():

        if not name.startswith(prefix):
            continue

        if name.endswith("/"):
            continue

        if name.startswith("/") or ".." in Path(name).parts:
            continue

        members.append(name)

    return members


class BackupManager:

    def __init__(self):

        self.backup_dir = Paths.backups()

    # --------------------------------------------------

    def create_backup(self, addon_path, wow_path=None):
        """
        Sichert den Addon-Ordner und - sofern `wow_path` bekannt ist -
        die `SavedVariables` des Addons.

        `wow_path` ist der WoW-Ordner (der mit `WTF` und `Interface`
        darin). Fehlt er, entsteht dasselbe Archiv wie vor 2.7.1;
        eine Aktualisierung, bei der die Anwendung den WoW-Ordner nicht
        kennt, gibt es nicht - aber ein Backup ohne Spielstand ist
        immer noch besser als keines.
        """

        addon_path = Path(addon_path)

        if not addon_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        archive_path = (
            self.backup_dir
            / f"WeintCodex_{timestamp}.zip"
        )

        with zipfile.ZipFile(
            archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as archive:

            #
            # Addon-Ordner, wie bisher unter "WeintCodex/…" - restore()
            # packt genau diesen Teil neben den Zielordner aus.
            #

            for entry in sorted(addon_path.rglob("*")):

                if not entry.is_file():
                    continue

                archive.write(
                    entry,
                    entry.relative_to(addon_path.parent).as_posix(),
                )

            #
            # Spielstand, unter seinem Pfad relativ zum WoW-Ordner.
            #

            for entry in saved_variable_files(wow_path):

                try:

                    archive.write(
                        entry,
                        entry.relative_to(Path(wow_path)).as_posix(),
                    )

                except (OSError, ValueError):

                    #
                    # Eine Datei, die WoW gerade schreibt, oder ein
                    # Pfad ausserhalb des WoW-Ordners: das Backup des
                    # Addon-Ordners deshalb scheitern zu lassen wäre
                    # der schlechtere Ausgang.
                    #

                    continue

        return archive_path

    # --------------------------------------------------

    def restore(self, backup_zip, addon_path) -> bool:
        """
        Stellt "addon_path" aus einem zuvor mit create_backup()
        erstellten Zip wieder her. Wird als Best-Effort-Rettung
        genutzt, wenn eine Installation fehlschlägt - überschreibt
        einen ggf. vorhandenen Ordner an "addon_path" komplett, da
        das Backup als vertrauenswürdiger Vorzustand gilt.

        Ausgepackt wird **nur** der Addon-Teil des Archivs. Der
        mitgesicherte Spielstand bleibt liegen: er war beim Update nie
        weg, und ihn hier stillschweigend zurückzuschieben, würde
        einen Fehlschlag der Installation in einen Datenverlust
        verwandeln.

        Gibt True bei Erfolg zurück, False wenn das Backup nicht
        existiert oder das Wiederherstellen selbst fehlschlägt (dann
        soll der Aufrufer den ursprünglichen Fehler weiterreichen,
        nicht diesen hier).
        """

        backup_zip = Path(backup_zip)
        addon_path = Path(addon_path)

        if not backup_zip.exists():
            return False

        try:

            with zipfile.ZipFile(backup_zip, "r") as archive:

                members = _safe_members(archive, ADDON_PREFIX)

                if not members:
                    return False

                if addon_path.exists():
                    shutil.rmtree(addon_path)

                archive.extractall(addon_path.parent, members)

            return True

        except Exception:

            return False

    # --------------------------------------------------

    def backups(self) -> list[Path]:
        """
        Alle Backups, das jüngste zuerst.
        """

        if not self.backup_dir.exists():
            return []

        return sorted(
            (
                entry
                for entry in self.backup_dir.iterdir()
                if entry.is_file() and entry.suffix.lower() == ".zip"
            ),
            key=lambda entry: entry.name,
            reverse=True,
        )

    # --------------------------------------------------

    def newest_with_saved_variables(self) -> Path | None:
        """
        Das jüngste Backup, das einen Spielstand enthält - oder None.

        Backups aus einer Fassung vor 2.7.1 tragen keinen; die
        Oberfläche muss das sagen können, statt einen Knopf anzubieten,
        der nichts findet.
        """

        for entry in self.backups():

            if saved_variable_members(entry):
                return entry

        return None

    # --------------------------------------------------

    def restore_saved_variables(self, backup_zip, wow_path) -> list[Path]:
        """
        Holt den mitgesicherten Spielstand zurück in den WoW-Ordner.

        Die jeweils vorhandene Datei wird vorher unter demselben Namen
        plus `ASIDE_SUFFIX` beiseitegelegt - eine Wiederherstellung
        ohne Rückweg wäre eine Einbahnstrasse, und wer sie versehentlich
        auslöst, hätte sonst gar nichts mehr.

        Gibt die zurückgeschriebenen Dateien zurück (leer, wenn das
        Archiv keinen Spielstand enthält).
        """

        backup_zip = Path(backup_zip)
        wow_path = Path(wow_path)

        written: list[Path] = []

        if not backup_zip.exists():
            return written

        with zipfile.ZipFile(backup_zip, "r") as archive:

            for name in _safe_members(archive, SAVED_PREFIX):

                target = wow_path / name

                target.parent.mkdir(parents=True, exist_ok=True)

                if target.exists():

                    aside = target.with_name(target.name + ASIDE_SUFFIX)

                    aside.unlink(missing_ok=True)

                    target.replace(aside)

                with archive.open(name) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)

                written.append(target)

        return written


# --------------------------------------------------
# Freistehend, damit sie ohne BackupManager prüfbar sind
# --------------------------------------------------


def saved_variable_files(wow_path) -> list[Path]:
    """
    Alle `WeintCodex.lua` unter `WTF/Account/*/SavedVariables/`.

    Bewusst **alle** Konten und nicht nur das erste (so wie
    `SyncReader.get_file()` es tut): dort geht es darum, wohin
    geschrieben wird, hier darum, was verloren gehen könnte - und wer
    zwei WoW-Konten hat, hat auf beiden Notizen.
    """

    if wow_path is None:
        return []

    root = Path(wow_path) / "WTF" / "Account"

    if not root.is_dir():
        return []

    found = []

    try:
        accounts = sorted(root.iterdir())

    except OSError:
        return []

    for account in accounts:

        file = account / "SavedVariables" / "WeintCodex.lua"

        if file.is_file():
            found.append(file)

    return found


def saved_variable_members(backup_zip) -> list[str]:
    """
    Die Spielstand-Einträge eines Archivs (leer bei einem Backup aus
    einer Fassung vor 2.7.1).
    """

    backup_zip = Path(backup_zip)

    if not backup_zip.exists():
        return []

    try:

        with zipfile.ZipFile(backup_zip, "r") as archive:
            return _safe_members(archive, SAVED_PREFIX)

    except (OSError, zipfile.BadZipFile):
        return []


def backup_time_text(backup_zip) -> str:
    """
    Der Zeitpunkt eines Backups als Satzbaustein ("2. September 2026,
    14:03 Uhr").

    Gelesen wird der Dateiname, nicht die Änderungszeit: die verschiebt
    sich beim Kopieren auf einen anderen Rechner, der Name nicht.
    Passt er nicht ins Muster, kommt der Name selbst zurück - eine
    erfundene Uhrzeit wäre schlechter als gar keine.
    """

    name = Path(backup_zip).stem

    stamp = name.removeprefix("WeintCodex_")

    try:
        moment = datetime.strptime(stamp, "%Y-%m-%d_%H-%M-%S")

    except ValueError:
        return name

    monate = (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )

    return (
        f"{moment.day}. {monate[moment.month - 1]} {moment.year}, "
        f"{moment:%H:%M} Uhr"
    )
