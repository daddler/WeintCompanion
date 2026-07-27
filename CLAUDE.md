# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

WeintCompanion is the official desktop companion app for the World of Warcraft addon **WeintCodex**. It's a PySide6 (Qt6) desktop application that installs/updates the addon, manages backups, and bridges data between the in-game addon and the **WeintCodex Bot** (Discord bot) via a small HTTP backend. Together these three repos form one ecosystem:

- **WeintCodex** – the WoW addon (Lua)
- **WeintCompanion** – this repo, the desktop app (Python/Qt)
- **WeintCodex Bot** – the Discord bot / backend

UI text, comments, and log messages are in German; code identifiers are in English.

## Commands

```bash
pip install -r requirements.txt   # install dependencies
python app.py                     # run the app
```

There is no test suite, linter, or formatter configured in this repo.

### Building distributables

```bash
./scripts/build_linux.sh          # PyInstaller build -> dist/WeintCompanion
./scripts/build_appimage.sh       # wraps the Linux build into an AppImage (requires linuxdeploy)
./scripts/build_windows.ps1       # PyInstaller + Inno Setup -> dist/WeintCompanion-Setup.exe
```

CI (`.github/workflows/build.yml`) builds Linux (AppImage) and Windows (Inno Setup installer) on every `v*` tag push and publishes a GitHub Release with both artifacts. `WeintCompanion.spec` is the PyInstaller spec (entry point `app.py`, bundles `assets/`, `resources/icons`, and the Linux updater script).

## Architecture

### Layering

- **`core/`** – all business logic, framework-agnostic where possible (Qt is used for `QObject`/`Signal` in a few places like `CompanionManager` and `AppState`).
- **`gui/`** – PySide6 UI: `main_window.py`, `pages/` (Dashboard, Addon, Sync, Settings, Logs), `widgets/`, `theme/` (colors/typography/stylesheet), `controllers/`, `dialogs/` (currently `whats_new_dialog.py` – the onboarding/changelog popup, see below).
- **`addon/`** – reads the WoW addon's Lua `SavedVariables` files (`finder.py` locates the WoW install, `reader.py` reads the addon's own version/state, `sync_reader.py` reads the outbound message queue).
- **`discord/`** – `sync_client.py`, a thin HTTP client for the material-sync bridge.

### `CompanionManager` is the app's central hub

`core/companion_manager.py` wires together nearly every subsystem (config, logger, GitHub updater, backup, installer, self-updater, launcher, sync manager, Discord status/auth/roster-sync) and is owned by the GUI layer. Its `full_refresh()` is the app's main "check everything" entry point: detect WoW install → detect addon → check GitHub for addon updates → check Discord bot status → check for Companion self-updates → run sync. `refresh_update_status()` is the lighter variant used by the manual "check for updates" button (skips Discord/sync).

Initialization pattern to preserve: `initialize()` schedules `_initialize_async` via `QTimer.singleShot` so the window renders before the background `InitThread` runs `full_refresh()`. Because that thread has no Qt event loop of its own, it can't reliably reach the main thread with `QTimer.singleShot(0, ...)` — it signals `_AutoSyncStarter.requested`, a cross-thread Qt signal, to invoke `start_auto_sync()` back on the main thread instead. Auto-sync itself runs on a recurring `QTimer` (`sync_interval` from config) that spawns a new `SyncThread` per tick, guarded by `_sync_busy` + a lock so overlapping syncs never run concurrently.

### Data flow: addon ↔ Companion ↔ Bot

The addon writes outbound messages into its WoW SavedVariables Lua file (`WeintCompanionDB.queue`, parsed by `addon/sync_reader.py` — a hand-rolled line parser, not a full Lua parser, see `core/lua_table.py` for the variable-block extraction helper). `SyncManager.process()` (`core/sync_manager.py`) drains that queue each cycle and, depending on `message["type"]`, dispatches to a different downstream client:
- `"character"` → `CharacterSyncClient` (requires a linked Discord account; silently dropped if unlinked or the "Bridge Card" for it is disabled in settings)
- `"loot"` → dropped unless `loot_sync_enabled` (off by default)
- everything else → the generic `discord.sync_client.SyncClient`

`DiscordRosterSync` (`core/discord_roster_sync.py`) runs the opposite direction: it polls the bot's `/companion/raid-roster` endpoint (bearer-token-authenticated via the stored `companion_token`) and, on new data, writes a `raid_import` message *into* the addon via `InboxWriter` — this is how the addon receives raid-roster/calendar data from Discord. It runs in the same sync cycle as the material sync but is isolated in its own try/except so a roster-sync failure never blocks material sync or vice versa.

The bot backend base URL is centralized as `BOT_BASE_URL` in `core/backend_config.py`, imported by `core/discord_auth.py`, `core/character_sync_client.py`, and `core/discord_roster_sync.py`.

### GitHub-based updates (two independent update channels)

- **Addon updates**: `GitHubUpdater` (`core/github_updater.py`), configured in `CompanionManager` against `daddler/WeintCodex`, polls the GitHub Releases API (15-minute cache) and picks the release asset by OS (`.appimage`/`setup.exe`/`.dmg`, or an explicit `asset_filter`). Version comparison uses `normalize_version()` (case/`v`-prefix-insensitive) between the addon's own reported version and the latest GitHub tag.
- **Companion self-update**: `CompanionUpdater` (`core/companion_updater.py`) checks/updates WeintCompanion itself, with OS-specific runners (`linux_updater.py`, `windows_updater.py`).

### Platform-specific paths and Qt workarounds

`core/paths.py` centralizes all on-disk locations (config/cache/downloads/backups/logs), branching on `platform.system()`: `~/.local/share/WeintCompanion` on Linux, `%LOCALAPPDATA%/WeintCompanion` on Windows.

`app.py` sets up crash diagnostics and several Linux/Qt workarounds *before* importing PySide6 — read the inline comments there before touching Qt platform env vars, they encode hard-won fixes for real crash reports:
- `faulthandler` writes native (non-Python) crash tracebacks to `cache/logs/crash.log`, since a SIGSEGV in Qt's xcb plugin never raises a Python exception.
- `QT_QPA_PLATFORM=wayland;xcb` lets Qt itself choose, rather than the app guessing from `XDG_SESSION_TYPE`.
- `QT_XCB_NO_XI2`, `QT_ACCESSIBILITY=0`, `QT_XCB_GL_INTEGRATION=none` are always-on mitigations for distro-specific xcb SIGSEGVs (libxkbcommon/AT-SPI/Mesa), each individually escape-hatchable via `WEINT_FORCE_*` env vars for users the mitigation itself breaks.

### Config and auth

`core/config.py` is a flat JSON-backed settings store (`config.json` in `Paths.config()`) with a defaults dict merged on load so new settings get backfilled into existing installs. Discord account linking is fully implemented: `core/discord_auth.py`'s `DiscordAuth.login()` runs the real OAuth2 flow (local callback server, system browser to Discord, code exchange against the bot's `/companion/auth/exchange`), and `core/discord_account.py`'s `DiscordAccountStore` persists the resulting identity plus a bot-issued `companion_token` (never the real Discord OAuth token) to `discord_account.json`. That `companion_token` is the bearer credential used everywhere downstream (`CharacterSyncClient`, `DiscordRosterSync`, generic sync) to check "is a Discord account linked" and to authenticate against the bot.

### "What's new" popup

`gui/dialogs/whats_new_dialog.py`'s `show_whats_new_if_needed()` is triggered once via `QTimer.singleShot(0, ...)` at the end of `MainWindow.__init__` (independent of `CompanionManager`'s async init, since its content is local/bundled, not network-fetched). It compares `config.data["onboarding_seen_version"]` against `core.version.VERSION`: empty (fresh install or an upgrade from any pre-1.0 version, since the key never existed before) shows the hardcoded multi-page `TOUR_PAGES` feature walkthrough; any other mismatch shows the changelog entries between the two versions, read from the bundled `CHANGELOG.md` via `core/changelog_reader.py` (must stay listed in `WeintCompanion.spec`'s `datas`). Either way the dialog updates `onboarding_seen_version` on close; its "don't show again" checkbox sets `config.data["whats_new_enabled"] = False`, which short-circuits the whole check on future starts. Both are user-reversible via the "Willkommens-Tour" toggle/button in Settings → Allgemein (`gui/pages/settings_sections/general.py`), which calls `show_tour()` unconditionally (bypassing the seen-version check).
