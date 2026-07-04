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
from addon.sync_reader import SyncReader
from core.sync_manager import SyncManager
from PySide6.QtCore import QTimer
from core.discord_status import DiscordStatus


class CompanionManager:

    def __init__(self):

        self.state = AppState()

        self.config = Config()

        # Zentrale Logger-Instanz
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
        self.sync = SyncManager(self)
        self.discord = DiscordStatus()
        self.sync_timer = QTimer()

        self.sync_timer.timeout.connect(
            self.run_auto_sync
        )
        
    # --------------------------------------------------
    # Initialisierung
    # --------------------------------------------------

    def initialize(self):

        self.full_refresh()

        self.start_auto_sync()

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

        self.sync.process()

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

    