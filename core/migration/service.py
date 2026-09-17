"""
Der Generationswechsel, an einer Stelle.

WARUM EIN DIENST UND NICHT EIN PAAR FUNKTIONEN IN DER OBERFLAECHE
-----------------------------------------------------------------

Ein Wechsel auf eine andere Anwendung besteht aus acht Schritten,
von denen jeder scheitern kann, und aus vier Fragen, die vor dem
ersten Schritt zu klaeren sind (Schalter, Plattform, bereits
migriert, verschoben). Verteilt man das auf die Stellen, die es
ausloesen - ein Startdialog, eine Seite, vielleicht spaeter ein
Menuepunkt -, entstehen drei Fassungen derselben Regeln, und die
erste, die eine davon vergisst, laedt eine ungepruefte Datei
herunter.

Deshalb: **diese Datei entscheidet, die Oberflaeche zeigt nur.**
`MigrationService` ist frei von Qt, blockiert (der Aufrufer legt
einen Thread darum, genau wie beim Companion-Update) und meldet
seinen Fortschritt ueber einen gewoehnlichen Rueckruf.

DIE ERSTE FRAGE IST IMMER DIESELBE
----------------------------------

`enabled()`. Ist der Schalter aus - und das ist die Vorgabe -, tut
dieser Dienst **nichts**: keine Anfrage, kein Protokolleintrag, kein
Zustand in der Konfiguration. Eine 4.x-Installation ohne
freigegebene Migration verhaelt sich, als gaebe es diese Datei
nicht.

WAS EIN FEHLSCHLAG BEDEUTET
---------------------------

Nichts, was der Nutzer merkt, ausser einer Meldung. Es wird nichts
ersetzt, nichts geloescht und nichts deinstalliert (siehe
`core/migration/handover.py`); die bestehende Fassung laeuft
unveraendert weiter, und beim naechsten Start steht das Angebot
wieder da.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

from core.downloader import Downloader
from core.migration.assets import AssetChoice, current_profile
from core.migration.discovery import DiscoveryResult, Outcome, ReleaseDiscovery
from core.migration.handover import Handover, HandoverError
from core.migration.integrity import IntegrityError, parse_checksum, verifier_for
from core.migration.payload import build_payload, write_payload
from core.migration.releases import (
    GitHubReleaseSource,
    ReleaseSourceError,
    StaticReleaseSource,
)
from core.migration.state import MigrationRecord, MigrationState, MigrationStore
from core.migration.target import (
    ENV_RELEASES,
    MigrationTarget,
    dry_run_enabled,
    migration_enabled,
    target_for,
)
from core.paths import Paths
from core.version import VERSION


@dataclass(frozen=True)
class MigrationOffer:
    """
    Was die Oberflaeche anzeigt - fertig formuliert, damit kein
    Dialog sich seine eigene Fassung davon ausdenkt.

    Beide Anwendungen stehen ausdruecklich mit **Namen und Fassung**
    nebeneinander: "WeintCompanion 4.9.0" und "Companion-Forever
    5.0.0", nie ein blosses "Update 5.0.0". Der Nutzer soll sehen,
    dass hier eine andere Anwendung anfaengt und nicht dieselbe
    weitergeht.
    """

    current_product: str
    current_version: str
    target_product: str
    target_version: str
    asset_name: str
    asset_size: int = 0
    dry_run: bool = False

    @property
    def current_label(self) -> str:
        return f"{self.current_product} {self.current_version}"

    @property
    def target_label(self) -> str:
        return f"{self.target_product} {self.target_version}"


@dataclass
class MigrationResult:

    success: bool
    state: MigrationState
    message: str = ""
    installed_path: Path | None = None
    dry_run: bool = False


#
# Die Schritte, die der Nutzer sieht. Der Text steht hier und nicht
# im Dialog: dieselbe Reihenfolge landet auch im Protokoll, und zwei
# Formulierungen desselben Schrittes waeren zwei Wahrheiten.
#

STEP_LABELS = {
    MigrationState.CONFIRMED: "Release wird abgerufen",
    MigrationState.DOWNLOADING: "Download",
    MigrationState.DOWNLOADED: "Download abgeschlossen",
    MigrationState.VERIFYING: "Pruefung",
    MigrationState.INSTALLING: "Installation",
    MigrationState.INSTALLED: "Start",
    MigrationState.COMPLETED: "Fertig",
    MigrationState.FAILED: "Abgebrochen",
}


class MigrationService:

    product_name = "WeintCompanion"

    def __init__(
        self,
        config=None,
        logger=None,
        downloader=None,
        source=None,
        target: MigrationTarget | None = None,
        profile=None,
        machine: str | None = None,
        handover=None,
    ):

        self.config = config
        self.logger = logger

        self.target = target or target_for(config)

        self.store = MigrationStore(config)

        self.downloader = downloader or Downloader()

        self.profile = profile or current_profile()
        self.machine = machine

        self._source = source
        self._handover = handover

        self._last_result: DiscoveryResult | None = None

    # --------------------------------------------------
    # Protokoll
    # --------------------------------------------------

    def _log(self, level: str, message: str) -> None:

        if self.logger is None:
            return

        getattr(self.logger, level, self.logger.info)(f"Migration: {message}")

    # --------------------------------------------------
    # Grundfragen
    # --------------------------------------------------

    def enabled(self) -> bool:

        return migration_enabled(self.config)

    def dry_run(self) -> bool:

        return dry_run_enabled(self.config)

    def record(self) -> MigrationRecord:

        return self._store().load()

    def _store(self) -> MigrationStore:
        """
        Der Zustandsspeicher - und im Probelauf **keiner**.

        Ein Probelauf soll den Weg prüfen und nicht den gespeicherten
        Stand verbiegen: er darf weder ein Angebot vermerken noch ein
        "später" noch einen abgeschlossenen Wechsel. Ein
        Zustandsspeicher ohne Konfiguration verhält sich nach aussen
        wie jeder andere und schreibt nirgendwohin.
        """

        return MigrationStore(None) if self.dry_run() else self.store

    @property
    def source(self):
        """
        Die Release-Quelle. Steht eine Datei in `WEINT_FOREVER_RELEASES`,
        wird gegen sie gearbeitet statt gegen GitHub - der Probelauf
        ohne Netz und ohne veroeffentlichtes Release.
        """

        if self._source is None:

            path = os.environ.get(ENV_RELEASES)

            if path:

                self._log("info", f"Release-Liste aus Datei: {path}")

                self._source = StaticReleaseSource.from_file(path)

            else:

                self._source = GitHubReleaseSource(
                    owner=self.target.owner,
                    repo=self.target.repo,
                )

        return self._source

    # --------------------------------------------------
    # Pruefung
    # --------------------------------------------------

    def check(self, force: bool = False) -> DiscoveryResult:
        """
        Fragt nach der naechsten Generation.

        **Nie aus `refresh()` einer Seite aufrufen** - das hier geht
        ins Netz (siehe `docs/architecture/navigation.md`). Der Platz
        dafuer ist `CompanionManager.full_refresh()`, also derselbe
        Hintergrundlauf, der auch die beiden Update-Kanaele prueft.
        """

        if not self.enabled():

            return DiscoveryResult(
                Outcome.NO_RELEASE,
                message="Der Generationswechsel ist nicht freigegeben.",
            )

        if force:

            try:
                self.source.invalidate()
            except Exception:
                pass

        self._log("info", f"Pruefung gestartet (eigene Fassung {VERSION}).")

        self._log(
            "info",
            f"Ziel: {self.target.slug}, Generation {self.target.major}, "
            f"Kanal {self.target.channel}.",
        )

        try:

            result = ReleaseDiscovery(
                source=self.source,
                target=self.target,
                profile=self.profile,
                machine=self.machine,
            ).find()

        except ReleaseSourceError as exc:

            result = DiscoveryResult(Outcome.NETWORK_ERROR, message=str(exc))

        self._last_result = result

        self._note(result)

        return result

    # --------------------------------------------------

    def _note(self, result: DiscoveryResult) -> None:
        """
        Das Ergebnis ins Protokoll und in den gespeicherten Zustand.

        Nur `AVAILABLE` und `NO_RELEASE` veraendern den Zustand. Ein
        Netzfehler darf ein bereits gefundenes Angebot **nicht**
        wegwerfen - sonst verschwindet der Knopf, weil das WLAN kurz
        weg war.
        """

        if result.outcome is Outcome.AVAILABLE:

            self._log(
                "info",
                f"Gefunden: {self.target.product_name} {result.version_text} "
                f"({result.choice.asset.name}).",
            )

            self._store().advance(
                MigrationState.AVAILABLE,
                target=self.target.slug,
                version=result.version_text,
                asset_name=result.choice.asset.name,
                source_version=VERSION,
            )

            return

        if result.outcome is Outcome.NO_RELEASE:

            self._log("info", result.message)

            self._store().advance(MigrationState.NOT_AVAILABLE)

            return

        #
        # Vorabfassung, unvollstaendiges Release, Netzfehler,
        # unbekannte Plattform: gemeldet, aber ohne Zustandswechsel.
        # Ein unvollstaendiges Release ist eine Warnung wert - es ist
        # ein Fehler auf der anderen Seite, und niemand sucht ihn
        # dort, solange er hier nicht steht.
        #

        level = (
            "warning"
            if result.outcome is Outcome.INVALID_RELEASE
            else "info"
        )

        self._log(level, result.message)

    # --------------------------------------------------
    # Angebot
    # --------------------------------------------------

    def offer(self, result: DiscoveryResult | None = None) -> MigrationOffer | None:
        """
        Was der Oberflaeche anzubieten ist - oder `None`.

        `None` in allen Faellen, die der Nutzer nicht sehen soll:
        Schalter aus, nichts gefunden, bereits gewechselt, oder die
        angebotene Fassung wurde weggeklickt.
        """

        if not self.enabled():
            return None

        result = result or self._last_result

        if result is None or not result.available:
            return None

        version = result.version_text

        record = self.record()

        if record.is_completed_for(version) or record.is_postponed_for(version):
            return None

        asset = result.choice.asset

        return MigrationOffer(
            current_product=self.product_name,
            current_version=VERSION,
            target_product=self.target.product_name,
            target_version=version,
            asset_name=asset.name,
            asset_size=asset.size,
            dry_run=self.dry_run(),
        )

    # --------------------------------------------------

    def postpone(self) -> None:

        result = self._last_result

        version = result.version_text if result else ""

        self._log("info", f"Auf spaeter verschoben ({version or 'ohne Fassung'}).")

        self._store().postpone(version)

    # --------------------------------------------------
    # Der Wechsel
    # --------------------------------------------------

    def migrate(self, progress=None, dry_run: bool | None = None) -> MigrationResult:
        """
        Der vollstaendige Ablauf: bestaetigt -> heruntergeladen ->
        geprueft -> installiert -> gestartet.

        `progress(state, text)` wird vor jedem Schritt gerufen (darf
        `None` sein). Der Aufruf blockiert; die Oberflaeche legt
        einen Thread darum.
        """

        dry = self.dry_run() if dry_run is None else bool(dry_run)

        if not self.enabled():

            return MigrationResult(
                False,
                MigrationState.NOT_AVAILABLE,
                "Der Generationswechsel ist nicht freigegeben.",
            )

        result = self._last_result

        if result is None or not result.available:

            result = self.check(force=True)

        if not result.available:

            return MigrationResult(
                False,
                self.record().status,
                result.message or "Es steht keine neue Generation bereit.",
            )

        #
        # Ein Probelauf schreibt **nichts** in die Konfiguration: er
        # soll den Weg pruefen, nicht den gespeicherten Stand
        # verbiegen. Deshalb ein Zustandsspeicher ohne Konfiguration.
        #

        store = MigrationStore(None) if dry else self._store()

        version = result.version_text
        choice = result.choice

        def step(state: MigrationState, text: str = "") -> None:

            store.advance(
                state,
                target=self.target.slug,
                version=version,
                asset_name=choice.asset.name,
                source_version=VERSION,
                dry_run=dry,
            )

            label = text or STEP_LABELS.get(state, state.value)

            if progress is not None:
                progress(state, label)

        if dry:
            self._log("info", "Probelauf - es wird nichts ersetzt.")

        self._log(
            "info",
            f"Wechsel bestaetigt: {self.product_name} {VERSION} -> "
            f"{self.target.product_name} {version}.",
        )

        step(MigrationState.CONFIRMED)

        try:

            expected = self._expected_checksum(choice)

            step(MigrationState.DOWNLOADING)

            downloaded = self._download(choice, version)

            step(MigrationState.DOWNLOADED)

            step(MigrationState.VERIFYING)

            verifier_for(expected).verify(downloaded)

            self._log("success", "Integritaetspruefung bestanden.")

            step(MigrationState.INSTALLING)

            self._write_payload(version)

            handover = self._handover or Handover(
                profile=self.profile,
                logger=self.logger,
                dry_run=dry,
            )

            handover.dry_run = dry

            outcome = handover.run(downloaded)

            step(MigrationState.INSTALLED)

        except (IntegrityError, HandoverError) as exc:

            return self._fail(store, exc.message, version, choice, dry)

        except Exception as exc:

            return self._fail(store, str(exc), version, choice, dry)

        if dry:

            self._log("success", "Probelauf abgeschlossen.")

            return MigrationResult(
                True,
                MigrationState.INSTALLED,
                outcome.detail or "Probelauf abgeschlossen.",
                installed_path=outcome.installed_path,
                dry_run=True,
            )

        step(MigrationState.COMPLETED)

        self._log(
            "success",
            f"Wechsel abgeschlossen - {self.target.product_name} {version} "
            "wurde gestartet.",
        )

        return MigrationResult(
            True,
            MigrationState.COMPLETED,
            outcome.detail
            or f"{self.target.product_name} {version} wurde gestartet.",
            installed_path=outcome.installed_path,
        )

    # --------------------------------------------------

    def _fail(self, store, message, version, choice, dry) -> MigrationResult:

        self._log("error", message)

        self._log(
            "info",
            f"{self.product_name} {VERSION} bleibt unveraendert installiert.",
        )

        store.advance(
            MigrationState.FAILED,
            target=self.target.slug,
            version=version,
            asset_name=choice.asset.name,
            source_version=VERSION,
            error=message,
            dry_run=dry,
        )

        return MigrationResult(
            False,
            MigrationState.FAILED,
            message,
            dry_run=dry,
        )

    # --------------------------------------------------

    def _expected_checksum(self, choice: AssetChoice) -> str | None:
        """
        Holt den Digest aus der `<asset>.sha256`-Datei des Releases.

        Faellt sie aus oder fehlt sie, ist das Ergebnis `None` - und
        `verifier_for(None)` bricht spaeter ab. Der Abbruch passiert
        also bei der *Pruefung* und nicht hier: so steht im Protokoll
        die Reihenfolge, die wirklich stattgefunden hat.
        """

        if choice.checksum is None:

            self._log(
                "warning",
                "Zum Release gibt es keine Pruefsummendatei.",
            )

            return None

        with tempfile.TemporaryDirectory(prefix="weint-migration-") as folder:

            destination = Path(folder) / choice.checksum.name

            try:

                self.downloader.download(choice.checksum.url, destination)

                text = destination.read_text(encoding="utf-8", errors="replace")

            except Exception as exc:

                self._log("warning", f"Pruefsumme nicht abrufbar: {exc}")

                return None

        return parse_checksum(text, choice.asset.name)

    # --------------------------------------------------

    def _download(self, choice: AssetChoice, version: str) -> Path:

        folder = Paths.downloads() / "forever"

        folder.mkdir(parents=True, exist_ok=True)

        destination = folder / choice.asset.name

        self._log("info", f"Download gestartet: {choice.asset.name}")

        path = Path(
            self.downloader.download(choice.asset.url, destination)
        )

        self._log("info", "Download abgeschlossen.")

        return path

    # --------------------------------------------------

    def _write_payload(self, version: str) -> None:
        """
        Die Uebergabe der Daten. Ein Fehlschlag hier bricht den
        Wechsel **nicht** ab: die neue Anwendung ist auch ohne
        uebernommene Einstellungen brauchbar, und eine nicht
        geschriebene Datei ist ein schlechterer Grund zum Abbruch als
        gar keiner.
        """

        try:

            path = write_payload(
                build_payload(self.config, self.target, version)
            )

            self._log("info", f"Einstellungen zur Uebernahme abgelegt ({path}).")

        except Exception as exc:

            self._log("warning", f"Uebergabedatei nicht geschrieben: {exc}")
