from dataclasses import dataclass
from pathlib import Path

from core.version import VERSION


@dataclass
class AppState:

    # --------------------------------------------------
    # World of Warcraft
    # --------------------------------------------------

    wow_found: bool = False

    wow_path: Path | None = None

    addons_path: Path | None = None

    # --------------------------------------------------
    # Addon
    # --------------------------------------------------

    addon_found: bool = False

    addon_path: Path | None = None

    addon_version: str = "-"

    # --------------------------------------------------
    # GitHub (Addon)
    # --------------------------------------------------

    github_version: str = "-"

    github_release_name: str = ""

    github_changelog: str = ""

    github_download_url: str = ""

    github_asset_name: str = ""

    github_published: str = ""

    # --------------------------------------------------
    # Addon Update
    # --------------------------------------------------

    update_available: bool = False

    # --------------------------------------------------
    # Companion
    # --------------------------------------------------

    companion_version: str = VERSION

    companion_latest_version: str = VERSION

    companion_download_url: str = ""

    companion_asset_name: str = ""

    companion_update_available: bool = False

    # --------------------------------------------------
    # Discord Bot
    # --------------------------------------------------

    discord_connected: bool = False

    discord_name: str = "-"

    discord_guilds: int = 0

    discord_latency: int | None = None