from dataclasses import dataclass
from pathlib import Path


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
    # GitHub
    # --------------------------------------------------

    github_version: str = "-"

    github_release_name: str = ""

    github_changelog: str = ""

    github_download_url: str = ""

    github_asset_name: str = ""

    github_published: str = ""

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    update_available: bool = False