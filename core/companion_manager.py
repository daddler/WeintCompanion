import threading

from addon.finder import WoWFinder
from addon.reader import AddonReader

from core.app_state import AppState
from core.backup import BackupManager
from core.config import Config
from core.downloader import Downloader
from core.github_updater import GitHubUpdater
from core.installer import Installer
from core.logger import Logger
from core.installer_workflow import InstallerWorkflow
from core.companion_updater import CompanionUpdater
from core.launcher import Launcher
from core.battlenet_launcher import BattleNetLauncher
from addon.sync_reader import SyncReader
from core.sync_manager import SyncManager
from PySide6.QtCore import QObject, QTimer, Signal
from core.discord_status import DiscordStatus
from core.discord_account import DiscordAccountStore
from core.discord_auth import DiscordAuth
from core.discord_roster_sync import DiscordRosterSync


class _AutoSyncStarter(QObject):
    """
    Stößt start_auto_sync() garantiert im Hauptthread an, egal von
    welchem Thread aus emittiert wird.

    QTimer.singleShot(0, callback) aus einem Thread OHNE eigene
    laufende Qt-Event-Loop (wie unser InitThread - ein reiner
    threading.Thread, der nie .exec() aufruft) ist dafür nicht
    zuverlässig: der Callback braucht eine Event-Loop, die ihn
    abarbeitet, und die des aufrufenden Threads gibt es hier gar
    nicht. Eine Signal/Slot-Verbindung über Thread-Grenzen wird
    dagegen immer über die Event-Loop des EMPFÄNGER-Threads
    zugestellt (hier: der Hauptthread, der mit app.exec() läuft) -
    unabhängig davon, ob der Sender-Thread selbst eine Event-Loop hat.
    """

    requested = Signal()


class CompanionManager:

    def __init__(self):

        self.state = AppState()

        self.config = Config()

        self.logger = Logger()

        self.github = GitHubUpdater(
            owner="daddler",
            repo="WeintCodex",
            asset_filter=".zip",
        )
        self.downloader = Downloader()
        self.backup = BackupManager()
        self.installer = Installer()
        self.workflow = InstallerWorkflow(self)
        self.companion_updater = CompanionUpdater(self)
        self.launcher = Launcher()
        self.battlenet_launcher = BattleNetLauncher(self.config)
        self.sync = SyncManager(self)
        self.discord = DiscordStatus()
        self.discord_account = DiscordAccountStore()
        self.discord_auth = DiscordAuth()
        self.discord_roster_sync = DiscordRosterSync(self)
        self.sync_timer = QTimer()

        self.sync_timer.timeout.connect(
            self.run_auto_sync
        )

        #
        # _AutoSyncStarter wird hier im Hauptthread erzeugt (Companion-
        # Manager selbst lebt im Hauptthread) - seine Thread-Affinität
        # ist damit korrekt gesetzt, bevor _initialize_worker im
        # Hintergrund-Thread emit() darauf aufruft.
        #

        self._auto_sync_starter = _AutoSyncStarter()

        self._auto_sync_starter.requested.connect(
            self.start_auto_sync
        )

        self._sync_busy = False
        self._sync_lock = threading.Lock()

    # --------------------------------------------------
    # Initialisierung
    # --------------------------------------------------

    def initialize(self):

        #
        # full_refresh verzögert starten, damit das Fenster
        # zuerst gerendert wird und der Qt-Hauptthread frei bleibt
        #

        QTimer.singleShot(
            100,
            self._initialize_async,
        )

    def _initialize_async(self):

        thread = threading.Thread(
            target=self._initialize_worker,
            daemon=True,
            name="InitThread",
        )

        thread.start()

    def _initialize_worker(self):

        #
        # full_refresh() darf den Start von Auto-Sync niemals verhindern:
        # Ohne dieses try/except würde eine einzelne fehlgeschlagene
        # Anfrage (Netzwerk-Hänger, Discord/GitHub down, defekte
        # SavedVariables, ...) diesen Thread lautlos beenden - in einer
        # AppImage/EXE ohne sichtbares Terminal sieht das für Nutzer wie
        # ein Absturz aus, obwohl nur dieser Hintergrund-Thread stirbt
        # und Auto-Sync danach nie mehr anläuft.
        #

        try:

            self.full_refresh()

        except Exception as exc:

            self.logger.error(
                f"Initialisierung fehlgeschlagen: {exc}"
            )

        finally:

            #
            # Siehe _AutoSyncStarter-Docstring: garantiert im
            # Hauptthread zugestellt, unabhängig von der (fehlenden)
            # Event-Loop dieses Threads.
            #

            self._auto_sync_starter.requested.emit()

    # --------------------------------------------------
    # Automatische Synchronisation
    # --------------------------------------------------

    def start_auto_sync(self):

        if not self.config.data.get(
            "auto_sync",
            True,
        ):

            self.logger.info(
                "Automatische Synchronisation deaktiviert."
            )

            return

        interval = self.config.data.get(
            "sync_interval",
            5,
        )

        #
        # Sekunden -> Millisekunden
        #

        self.sync_timer.start(
            interval * 1000
        )

        self.logger.success(
            f"Automatische Synchronisation aktiviert ({interval} Sekunde(n))."
        )

    def run_auto_sync(self):

        #
        # Verhindert, dass ein neuer Sync startet,
        # während der vorherige noch läuft
        #

        with self._sync_lock:

            if self._sync_busy:
                return

            self._sync_busy = True

        thread = threading.Thread(
            target=self._run_sync_worker,
            daemon=True,
            name="SyncThread",
        )

        thread.start()

    def _run_sync_worker(self):

        try:

            self.sync.process()

        except Exception as exc:

            self.logger.error(
                f"Sync fehlgeschlagen: {exc}"
            )

        #
        # Eigener try/except: ein Fehler beim Raid-Roster-Abruf
        # (z. B. Bot nicht erreichbar) darf den Material-Sync oben
        # nicht mit runterreißen und umgekehrt.
        #

        try:

            if self.config.data.get(
                "roster_sync_enabled",
                True,
            ):

                self.discord_roster_sync.process()

        except Exception as exc:

            self.logger.error(
                f"Discord-Raid-Roster-Sync fehlgeschlagen: {exc}"
            )

        finally:

            with self._sync_lock:

                self._sync_busy = False

    # --------------------------------------------------
    # Automatische Synchronisation stoppen
    # --------------------------------------------------

    def stop_auto_sync(self):

        if self.sync_timer.isActive():

            self.sync_timer.stop()

            self.logger.info(
                "Automatische Synchronisation gestoppt."
            )

    # --------------------------------------------------
    # Classic Installation
    # --------------------------------------------------

    def detect_wow(self):

        classic_path = self.config.get_classic_path()

        if classic_path is None:

            finder = WoWFinder()
            classic_path = finder.find()

            if classic_path:
                self.config.set_classic_path(classic_path)

        self.state.wow_path = classic_path
        self.state.wow_found = classic_path is not None

        if self.state.wow_found:

            self.state.addons_path = (
                classic_path
                / "Interface"
                / "AddOns"
            )

        else:

            self.state.addons_path = None

    # --------------------------------------------------
    # Addon
    # --------------------------------------------------

    def detect_addon(self):

        self.state.addon_found = False
        self.state.addon_version = "-"

        if not self.state.addons_path:
            self.state.addon_path = None
            return

        self.state.addon_path = (
            self.state.addons_path
            / "WeintCodex"
        )

        reader = AddonReader(self.state.wow_path)

        if not reader.exists():
            return

        self.state.addon_found = True
        self.state.addon_version = (
            reader.get_version() or "-"
        )

        #
        # Companion Queue prüfen
        #

        sync = SyncReader(
            self.state.wow_path
        )

        if sync.exists():

            count = sync.queue_size()

            if count:

                self.logger.info(
                    f"Companion: {count} Nachricht(en) in der Warteschlange."
                )

            else:

                self.logger.success(
                    "Companion: Warteschlange leer."
                )

        else:

            self.logger.info(
                "Companion: Keine SavedVariables gefunden."
            )

    # --------------------------------------------------
    # GitHub
    # --------------------------------------------------

    def normalize_version(self, version):

        if not version:
            return ""

        return (
            version
            .strip()
            .lower()
            .removeprefix("v")
        )

    def check_github(self):

        release = self.github.get_latest_release()

        if release is None:

            self.state.github_version = "-"
            self.state.github_release_name = ""
            self.state.github_changelog = ""
            self.state.github_download_url = ""
            self.state.github_asset_name = ""
            self.state.github_published = ""
            self.state.update_available = False

            self.logger.error(
                "GitHub konnte nicht erreicht werden."
            )

            return

        self.state.github_version = release.version
        self.state.github_release_name = release.name
        self.state.github_changelog = release.changelog
        self.state.github_download_url = release.download_url
        self.state.github_asset_name = release.asset_name
        self.state.github_published = release.published_at

        github = self.normalize_version(
            self.state.github_version
        )

        addon = self.normalize_version(
            self.state.addon_version
        )

        self.state.update_available = (
            github != addon
        )

        if self.state.update_available:

            self.logger.info(
                f"Neue Version gefunden ({release.version})."
            )

        else:

            self.logger.success(
                "WeintCodex ist aktuell."
            )

    # --------------------------------------------------
    # Discord
    # --------------------------------------------------

    def check_discord(self):

        data = self.discord.fetch()

        if data is None:

            self.state.discord_connected = False
            self.state.discord_name = "-"
            self.state.discord_guilds = 0
            self.state.discord_latency = None

            return

        if not data.get("online", False):

            self.state.discord_connected = False
            self.state.discord_name = "-"
            self.state.discord_guilds = 0
            self.state.discord_latency = None

            return

        bot = data.get("bot", {})

        self.state.discord_connected = True
        self.state.discord_name = bot.get("name", "-")
        self.state.discord_guilds = bot.get("guilds", 0)
        self.state.discord_latency = bot.get("latency")

    # --------------------------------------------------
    # Installation / Update
    # --------------------------------------------------

    def install_or_update(self):

        return self.workflow.run()

    # --------------------------------------------------
    # WoW starten (Battle.net)
    # --------------------------------------------------

    def start_wow(self):

        try:

            self.battlenet_launcher.launch(
                self.state.wow_path
            )

            self.logger.success(
                "Battle.net wird gestartet..."
            )

        except Exception as exc:

            self.logger.error(
                f"Battle.net konnte nicht gestartet werden: {exc}"
            )

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def has_wow(self):

        return self.state.wow_found

    def has_addon(self):

        return self.state.addon_found

    # --------------------------------------------------
    # Refresh
    # --------------------------------------------------

    def refresh(self):

        self.detect_wow()
        self.detect_addon()

    # --------------------------------------------------
    # Vollständige Aktualisierung
    # --------------------------------------------------

    def full_refresh(self):

        self.detect_wow()
        self.detect_addon()
        self.check_github()
        self.check_discord()
        self.companion_updater.check_for_update()
        self.sync.process()

    # --------------------------------------------------
    # Manuelle Update-Prüfung (Button im Dashboard)
    # --------------------------------------------------

    def refresh_update_status(self):
        """
        Prüft erneut gegen GitHub, ob ein Addon- oder Companion-Update
        verfügbar ist - ohne die App neu zu starten. Macht dieselben
        Anfragen wie full_refresh(), aber ohne Discord-Status/Sync,
        die für eine reine "nach Updates suchen"-Aktion irrelevant sind.
        """

        self.detect_addon()
        self.check_github()
        self.companion_updater.check_for_update()

