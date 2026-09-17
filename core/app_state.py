from dataclasses import dataclass
from pathlib import Path

from core.version import VERSION
from core.wow_clients import DEFAULT_CLIENT_ID


@dataclass
class AppState:

    # --------------------------------------------------
    # World of Warcraft
    # --------------------------------------------------

    #
    # Welche Spielversion gerade bedient wird
    # (core/wow_clients.py). Steht hier und nicht nur in der
    # Konfiguration, damit die Oberfläche sie beim Zeichnen zur Hand
    # hat, ohne dafür die Konfiguration zu befragen - eine Seite darf
    # in `refresh()` nichts holen (docs/architecture/navigation.md).
    #

    wow_client_id: str = DEFAULT_CLIENT_ID

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

    github_sha256: str = ""

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

    companion_sha256: str = ""

    companion_update_available: bool = False

    companion_changelog: list[str] | None = None

    # --------------------------------------------------
    # Generationswechsel (Companion-Forever)
    # --------------------------------------------------
    #
    # Steht neben den Companion-Feldern und nicht darin: ein Update
    # bleibt dieselbe Anwendung, ein Generationswechsel ist eine
    # andere. Die Oberfläche soll beides nie in denselben Satz
    # packen (siehe `core/migration/service.MigrationOffer`).
    #
    # Solange die Migration nicht freigegeben ist, bleiben diese
    # Felder auf ihren Vorgaben - es wird dann gar nicht geprüft.
    #

    forever_migration_available: bool = False

    forever_target_version: str = ""

    forever_target_product: str = ""

    # --------------------------------------------------
    # Discord Bot
    # --------------------------------------------------

    discord_connected: bool = False

    discord_name: str = "-"

    discord_guilds: int = 0

    discord_latency: int | None = None