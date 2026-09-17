"""
Der Ablauf des Generationswechsels von Anfang bis Ende.

Hier laufen die anderen Bausteine zusammen, und hier stehen die drei
Zusicherungen, an denen die ganze Schicht haengt:

1. **Ausgeschaltet heisst ausgeschaltet.** Ohne freigegebene
   Migration wird nichts gefragt, nichts geladen, nichts angezeigt.
2. **Ein Fehlschlag laesst die bestehende Anwendung in Ruhe.** Bei
   falscher Pruefsumme wird nicht installiert - und nichts an 4.x
   angefasst.
3. **Ein Probelauf hinterlaesst nichts** - weder eine Installation
   noch einen Eintrag in der Konfiguration.
"""

import hashlib

import pytest

from core.migration.assets import LINUX, ReleaseAsset
from core.migration.handover import HandoverError, HandoverResult
from core.migration.releases import Release, StaticReleaseSource
from core.migration.service import MigrationService
from core.migration.state import MigrationState
from core.migration.target import STATE_KEY, MigrationTarget


CONTENT = b"Companion-Forever 5.0.0 (Testdatei)"

DIGEST = hashlib.sha256(CONTENT).hexdigest()


APPIMAGE = "Companion-Forever-5.0.0-x86_64.AppImage"


class FakeConfig:

    def __init__(self, enabled=True, **settings):

        self.data = {
            "forever_migration": {"enabled": enabled, **settings},
        }

        self.saves = 0

    def save(self):
        self.saves += 1


class FakeLogger:

    def __init__(self):
        self.lines = []

    def _add(self, level, message):
        self.lines.append((level, message))

    def info(self, message):
        self._add("info", message)

    def success(self, message):
        self._add("success", message)

    def warning(self, message):
        self._add("warning", message)

    def error(self, message):
        self._add("error", message)

    def text(self):
        return "\n".join(message for _, message in self.lines)


class FakeDownloader:
    """
    Schreibt feste Inhalte statt zu laden. `bodies` bildet URL auf
    Bytes ab; eine unbekannte URL ist ein Verbindungsfehler.
    """

    def __init__(self, bodies):

        self.bodies = bodies
        self.urls = []

    def download(self, url, destination, expected_sha256=None):

        self.urls.append(url)

        if url not in self.bodies:
            raise OSError("Verbindung fehlgeschlagen")

        destination.parent.mkdir(parents=True, exist_ok=True)

        destination.write_bytes(self.bodies[url])

        return destination


class FakeHandover:

    def __init__(self, error=None):

        self.error = error
        self.dry_run = False
        self.calls = []

    def run(self, downloaded):

        self.calls.append(downloaded)

        if self.error is not None:
            raise self.error

        return HandoverResult(
            installed_path=downloaded,
            launched=not self.dry_run,
            detail="Die neue Anwendung wurde gestartet.",
        )


def url(name):

    return f"https://example.invalid/{name}"


def asset(name):

    return ReleaseAsset(name=name, url=url(name), size=len(CONTENT))


def releases(names=(APPIMAGE, APPIMAGE + ".sha256")):

    return [Release(tag="v5.0.0", assets=tuple(asset(name) for name in names))]


def bodies(digest=DIGEST, content=CONTENT):

    return {
        url(APPIMAGE): content,
        url(APPIMAGE + ".sha256"): f"{digest}  {APPIMAGE}\n".encode("utf-8"),
    }


def service(
    config=None,
    logger=None,
    source=None,
    downloader=None,
    handover=None,
):

    return MigrationService(
        config=config if config is not None else FakeConfig(),
        logger=logger,
        downloader=downloader if downloader is not None else FakeDownloader(bodies()),
        source=source if source is not None else StaticReleaseSource(releases()),
        target=MigrationTarget(
            owner="daddler",
            repo="Companion-Forever",
            product_name="Companion-Forever",
            major=5,
        ),
        profile=LINUX,
        machine="x86_64",
        handover=handover if handover is not None else FakeHandover(),
    )


@pytest.fixture(autouse=True)
def _own_folders(tmp_path, monkeypatch):
    """
    Nichts in echten Nutzerordnern ablegen: Download-Ziel und
    Uebergabedatei zeigen im Test auf tmp_path.
    """

    monkeypatch.setattr(
        "core.migration.service.Paths.downloads",
        staticmethod(lambda: tmp_path / "downloads"),
    )

    written = []

    monkeypatch.setattr(
        "core.migration.service.write_payload",
        lambda data: written.append(data) or (tmp_path / "migration.json"),
    )

    return written


# --------------------------------------------------
# Der Schalter
# --------------------------------------------------


def test_without_the_switch_nothing_is_asked():

    source = StaticReleaseSource(releases())

    keeper = service(config=FakeConfig(enabled=False), source=source)

    result = keeper.check()

    assert not result.available

    assert keeper.offer() is None


def test_without_the_switch_nothing_is_downloaded():

    downloader = FakeDownloader(bodies())

    keeper = service(config=FakeConfig(enabled=False), downloader=downloader)

    outcome = keeper.migrate()

    assert not outcome.success

    assert downloader.urls == []


def test_without_the_switch_nothing_is_written_to_the_configuration():

    config = FakeConfig(enabled=False)

    keeper = service(config=config)

    keeper.check()

    assert STATE_KEY not in config.data


# --------------------------------------------------
# Das Angebot
# --------------------------------------------------


def test_an_offer_names_both_applications():
    """
    "Update 5.0.0" waere die falsche Auskunft - es faengt eine
    andere Anwendung an.
    """

    keeper = service()

    keeper.check()

    offer = keeper.offer()

    assert offer.current_label.startswith("WeintCompanion ")

    assert offer.target_label == "Companion-Forever 5.0.0"

    assert offer.asset_name == APPIMAGE


def test_later_removes_the_offer_for_this_version():

    keeper = service()

    keeper.check()

    assert keeper.offer() is not None

    keeper.postpone()

    assert keeper.offer() is None


def test_a_completed_migration_is_not_offered_again():

    config = FakeConfig()

    keeper = service(config=config)

    keeper.check()

    keeper.migrate()

    assert config.data[STATE_KEY]["completed"] is True

    keeper.check()

    assert keeper.offer() is None


# --------------------------------------------------
# Der Wechsel
# --------------------------------------------------


def test_the_whole_way_through(tmp_path):

    config = FakeConfig()

    handover = FakeHandover()

    keeper = service(config=config, handover=handover)

    seen = []

    outcome = keeper.migrate(progress=lambda state, text: seen.append(state))

    assert outcome.success

    assert outcome.state is MigrationState.COMPLETED

    assert handover.calls

    assert [
        MigrationState.CONFIRMED,
        MigrationState.DOWNLOADING,
        MigrationState.DOWNLOADED,
        MigrationState.VERIFYING,
        MigrationState.INSTALLING,
        MigrationState.INSTALLED,
        MigrationState.COMPLETED,
    ] == seen

    assert config.data[STATE_KEY]["state"] == "completed"


def test_the_settings_are_handed_over(_own_folders):

    keeper = service()

    keeper.migrate()

    assert _own_folders, "Es wurde keine Uebergabedatei geschrieben."

    assert _own_folders[0]["target"]["version"] == "5.0.0"


def test_the_log_tells_the_whole_story():
    """
    Ohne Zugangsdaten, aber mit jedem Schritt - siehe
    Aufgabenstellung: eine Migration, die man im Nachhinein nicht
    nachvollziehen kann, ist eine, die man nicht reparieren kann.
    """

    logger = FakeLogger()

    keeper = service(logger=logger)

    keeper.check()

    keeper.migrate()

    text = logger.text()

    for fragment in (
        "daddler/Companion-Forever",
        "Generation 5",
        "Kanal stable",
        APPIMAGE,
        "Download gestartet",
        "Integritaetspruefung bestanden",
    ):
        assert fragment in text


# --------------------------------------------------
# Wenn etwas schiefgeht
# --------------------------------------------------


def test_a_wrong_checksum_stops_before_the_installation():

    handover = FakeHandover()

    keeper = service(
        downloader=FakeDownloader(bodies(digest="a" * 64)),
        handover=handover,
    )

    outcome = keeper.migrate()

    assert not outcome.success

    assert outcome.state is MigrationState.FAILED

    assert handover.calls == [], "Trotz falscher Pruefsumme installiert."


def test_a_missing_checksum_stops_the_migration():

    keeper = service(
        source=StaticReleaseSource(releases(names=(APPIMAGE,))),
        downloader=FakeDownloader({url(APPIMAGE): CONTENT}),
    )

    outcome = keeper.migrate()

    assert not outcome.success

    assert "Pruefsumme" in outcome.message


def test_a_failed_download_is_not_a_crash():

    keeper = service(downloader=FakeDownloader({}))

    outcome = keeper.migrate()

    assert not outcome.success

    assert outcome.state is MigrationState.FAILED


def test_a_failed_installation_says_that_v4_is_untouched():

    logger = FakeLogger()

    keeper = service(
        logger=logger,
        handover=FakeHandover(
            error=HandoverError("INSTALL_FAILED", "Installer abgebrochen")
        ),
    )

    outcome = keeper.migrate()

    assert not outcome.success

    assert "unveraendert" in logger.text()


def test_a_failure_can_be_tried_again():

    config = FakeConfig()

    keeper = service(config=config, downloader=FakeDownloader({}))

    keeper.migrate()

    assert config.data[STATE_KEY]["state"] == "failed"

    keeper = service(config=config, handover=FakeHandover())

    assert keeper.migrate().success


def test_nothing_available_is_not_a_failure():

    keeper = service(source=StaticReleaseSource([]))

    outcome = keeper.migrate()

    assert not outcome.success

    assert outcome.state is not MigrationState.FAILED


# --------------------------------------------------
# Probelauf
# --------------------------------------------------


def test_a_dry_run_walks_the_whole_way():

    handover = FakeHandover()

    keeper = service(config=FakeConfig(dry_run=True), handover=handover)

    seen = []

    outcome = keeper.migrate(progress=lambda state, text: seen.append(state))

    assert outcome.success

    assert outcome.dry_run

    assert MigrationState.VERIFYING in seen

    assert handover.dry_run is True


def test_a_dry_run_leaves_no_trace_in_the_configuration():

    config = FakeConfig(dry_run=True)

    keeper = service(config=config)

    keeper.migrate()

    assert STATE_KEY not in config.data


def test_a_dry_run_does_not_report_a_completed_migration():

    keeper = service(config=FakeConfig(dry_run=True))

    outcome = keeper.migrate()

    assert outcome.state is MigrationState.INSTALLED

    assert outcome.state is not MigrationState.COMPLETED
