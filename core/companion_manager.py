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


class CompanionManager:

    def __init__(self):

        self.state = AppState()

        self.config = Config()

        self.github = GitHubUpdater(
            owner="daddler",
            repo="WeintCodex",
        )
        self.downloader = Downloader()
        self.backup = BackupManager()
        self.installer = Installer()
        self.workflow = InstallerWorkflow(self)
        self.companion_updater = CompanionUpdater(self)
        self.launcher = Launcher()
        
        # Zentrale Logger-Instanz
        self.logger = Logger()

    # --------------------------------------------------
    # Initialisierung
    # --------------------------------------------------

    def initialize(self):

        self.full_refresh()

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
        self.companion_updater.check_for_update()

    