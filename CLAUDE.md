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

Tests live in `tests/` and run with pytest (`pip install -r requirements-dev.txt && python -m pytest tests/ -q`). They cover the framework-agnostic parts only — config, installer, Lua/sync parsing, the analyzer and its academy evaluation, and the navigation registry. There is no linter or formatter configured.

### Building distributables

```bash
./scripts/build_linux.sh          # PyInstaller build -> dist/WeintCompanion
./scripts/build_appimage.sh       # wraps the Linux build into an AppImage (requires linuxdeploy)
./scripts/build_windows.ps1       # PyInstaller + Inno Setup -> dist/WeintCompanion-Setup.exe
```

CI (`.github/workflows/build.yml`) builds Linux (AppImage) and Windows (Inno Setup installer) on every `v*` tag push and publishes a GitHub Release with both artifacts. `WeintCompanion.spec` is the PyInstaller spec (entry point `app.py`, bundles `assets/`, `resources/icons`, and the Linux updater script).

## Architecture

### Layering

- **`core/`** – all business logic, framework-agnostic where possible (Qt is used for `QObject`/`Signal` in a few places like `CompanionManager`, `RaidDataService` and `AppState`).
- **`gui/`** – PySide6 UI: `main_window.py`, `navigation.py` (the page registry, see below), `pages/` (Dashboard, Addon, Sync, WeintTV, Academy, Settings, Logs), `widgets/`, `theme/` (colors/typography/metrics/stylesheet/wow_colors), `controllers/`, `dialogs/` (currently `whats_new_dialog.py` – the onboarding/changelog popup, see below).
- **`analyzer/`** – the Raidlog Analyzer. **Contains no Qt import at all**, deliberately: it must stay testable without a running UI and extractable into its own package later. Holds the data models, the combat-log locator, the encounter/lesson reference data, the data providers, and the academy evaluation.
- **`addon/`** – reads the WoW addon's Lua `SavedVariables` files (`finder.py` locates the WoW install, `reader.py` reads the addon's own version/state, `sync_reader.py` reads the outbound message queue).
- **`discord/`** – `sync_client.py`, a thin HTTP client for the material-sync bridge.

### `CompanionManager` is the app's central hub

`core/companion_manager.py` wires together nearly every subsystem (config, logger, GitHub updater, backup, installer, self-updater, launcher, sync manager, Discord status/auth/roster-sync) and is owned by the GUI layer. Its `full_refresh()` is the app's main "check everything" entry point: detect WoW install → detect addon → check GitHub for addon updates → check Discord bot status → check for Companion self-updates → run sync. `refresh_update_status()` is the lighter variant used by the manual "check for updates" button (skips Discord/sync).

Initialization pattern to preserve: `initialize()` schedules `_initialize_async` via `QTimer.singleShot` so the window renders before the background `InitThread` runs `full_refresh()`. Because that thread has no Qt event loop of its own, it can't reliably reach the main thread with `QTimer.singleShot(0, ...)` — it signals `_AutoSyncStarter.requested`, a cross-thread Qt signal, to invoke `start_auto_sync()` back on the main thread instead. Auto-sync itself runs on a recurring `QTimer` (`sync_interval` from config) that spawns a new `SyncThread` per tick, guarded by `_sync_busy` + a lock so overlapping syncs never run concurrently.

### Navigation: one registry, never raw indices

Pages live in a `QStackedWidget` whose index *is* the position in the sidebar rail. Both are built from a single source: `PageId` (an `IntEnum`) and `build_page_specs()` in `gui/navigation.py`. `MainWindow` iterates the specs to create the stack and hands the same list to `Sidebar(manager, entries)`, so rail and stack cannot drift apart. Adding a main area = one enum member + one `PageSpec`.

Never write a bare integer as a navigation target: `pageRequested.emit(PageId.ADDON)`, not `emit(1)`. `PageId` inherits from `int`, so it works unchanged with `Signal(int)` and `setCurrentIndex()`. `build_page_specs()` imports the page classes *inside the function body* — the pages import `PageId` themselves, so a module-level import would be circular.

`MainWindow.change_page()` calls three duck-typed hooks on a page if present: `on_leave()` on the outgoing page, then `on_enter()` and `refresh()` on the incoming one. WeintTV and the Academy use `on_enter`/`on_leave` to subscribe to and release the raid data feed, so nothing polls while its page is hidden.

### WeintTV and WeintAcademy: one service, one snapshot

Both modules read the **same** `RaidSnapshot` (`analyzer/models.py`) — an immutable, complete picture of one moment (boss health, pull timer, deaths, battle-res, heroism, DPS/HPS rankings, tanks, cooldowns, consumables, mechanic errors, warnings). No widget ever sees a combat-log event, and no page computes a metric. That is what structurally prevents WeintTV and the Academy from growing two divergent evaluations.

`core/raid_data_service.py`'s `RaidDataService` is the single place that picks and polls a data source. Key points:
- Sources are registered in `PROVIDER_FACTORIES` keyed by the `raid_data_source` config value, alongside `SOURCE_LABELS`/`SOURCE_DESCRIPTIONS` for the picker in Settings → Module. A new source (live combat log, bot backend) is one entry plus a class implementing `analyzer/providers/base.py`'s `RaidDataProvider` — no change to the service or the pages. Factories are called with no arguments; anything a provider needs is wired in the factory (see `_create_warcraftlogs_provider`). An unknown key logs a warning and falls back to the mock, so the UI always stays usable.
- `attach()`/`detach()` are reference-counted; the `RaidDataThread` (a plain `threading.Thread`, matching the rest of the repo) runs only while at least one page is subscribed, on its own ~1s cadence — deliberately *not* on `CompanionManager`'s 5-second sync timer, which is for HTTP sync.
- Results reach the GUI through the `snapshotChanged = Signal(object)` cross-thread signal; the service is constructed in `CompanionManager.__init__` (main thread) so its thread affinity is right.
- It also owns the pull history (`PullSummary`), so the history view and any later analysis see the same completed pulls.

`analyzer/providers/mock.py` produces a fully deterministic 25-player pull from elapsed time — no randomness, so the same moment always yields the same snapshot. It is what makes WeintTV reviewable outside raid hours and is the proof that the UI really only reads snapshots.

The Academy adds `analyzer/academy/`: `evaluator.py` turns a snapshot into a `PlayerProfile` (star ratings for **six** areas — Rotation/Movement/Cooldowns/Mechaniken/Überleben/Leistung) and a `TrainingPlan`, using the `MECHANIC_*` category on each `MechanicIssue` to attribute errors to a trainable area. Ratings are **relative to the player's own role** — comparing a tank against the damage ranking would permanently score them one star, and for damage *taken* that matters even more (a tank always takes the most, which is the job), so Überleben rates the avoidable **share** against same-role peers, never the absolute sum. `core/academy_service.py` only handles character selection and persistence (`academy_progress.json` in `Paths.config()`, because completed lessons are user data, not cache).

Three rules the Academy lives by, each of which reverses an earlier mistake:

- **Rotation must not read the damage ranking.** That was the original implementation and it measured gear, not play. Rotation is now active time, APM and aura uptimes; the rank moved to its own area, `Leistung`, where it no longer overshadows the question "did I press my buttons right".
- **`stars = 0` means "no data", not "bad".** Without that distinction a gap in the data source outranks every real weakness and hijacks the whole training plan. `PlayerProfile.rated`/`weakest` skip zero-star ratings, and `_combine()` drops parts that have no data instead of averaging them down.
- **Lesson results and the manual checkbox are never merged.** `LessonResult` is evidence from the log, `completed` is the player's own claim. Auto-ticking would assert something a single pull can't support; auto-unticking would destroy the player's own record.

The training plan verifies itself: a `Lesson` carries declarative `LessonCheck`s ("active_percent >= 95"), and **`analyzer/academy/checks.py` is the only place** mapping metric names to snapshot lookups. `tests/test_lesson_catalog.py` asserts every metric used in the catalog resolves there — a typo would otherwise be a permanently silent "keine Daten". Outcomes are three-valued (`passed`/`failed`/`unknown`) because many lessons aren't measurable in principle and many payloads omit blocks; a red cross for a missing field would simply be wrong.

The catalog is a package (`analyzer/academy/lessons/`): `generic.py`, `roles.py`, `classes/<class>.py`, `encounters.py`, merged by `registry.py`, which **raises on a duplicate `lesson_id`** at import — the id is the persistence key, so a duplicate would silently merge two lessons' progress. Selection order is encounter → spec → class-wide → role → generic. Catalog opt-out stores **exclusions, not inclusions**, so a newly shipped lesson is automatically active for everyone with no migration.

`analyzer/analysis/` sits between `data/` (reference knowledge) and `providers/` (ingestion) and holds the derivations both the payload mapper and the replay need: `ranking.py` (extracted so the two can't drift apart on shares and sorting), `movement.py` (the single map-units-to-metres constant), `damage.py` (bucketing damage taken, deriving mechanic issues, merging them with the bot's).

**Whether a hit was avoidable is a judgement, not a measurement**, so it lives in `analyzer/data/avoidable.py` and not in the bot: it must be identical for WeintTV and the Academy, it changes with difficulty and tactics, and it has to stay correctable without a bot deploy. The verdict is deliberately **three-valued** — an ability missing from the table is `unknown`, never `unavoidable`. Treating unknown as unavoidable would hand every boss without reference data a flawless survival rating, and the table covers only a handful of bosses. Below `MIN_CLASSIFIED_SHARE` the Academy declines to rate at all rather than grade the table's gaps. When the bot ships its own hand-written `mechanics[]` rows, `merge_mechanics()` lets **the bot win** per (player, ability) so the same incident isn't counted twice; a small alias table bridges the bot's German texts to English ability names.

The second real source is **WarcraftLogs**, read through the bot rather than directly: the bot sees the Discord webhook the live-logging uploader posts, holds the WarcraftLogs API credentials, and serves the result at `/companion/warcraftlogs/live`. That split keeps credentials off 25 player machines and shares one API quota. Three files, deliberately separated so the analyzer stays dependency-free: `analyzer/providers/warcraftlogs_payload.py` is a pure response → `RaidSnapshot` mapper (no I/O, reads defensively — an incomplete response is never an error); `analyzer/providers/warcraftlogs.py` is the provider, which takes its fetch as an injected callable and runs its **own** 15-second fetch thread so `snapshot()` reads a cache and never blocks the service's 1-second poll; `core/warcraftlogs_client.py` is the HTTP half, wired to the provider in the factory. Unlike the combat log it lags by tens of seconds (the provider advances the pull clock locally between fetches and warns past 45s) but covers the whole raid without this machine logging. **All four bot endpoints now exist** (`services/warcraftlogs.py` in the bot repo) but deliver only **sums** — the only timestamp is `deaths[].at`. Everything the deep analysis, the six Academy areas and the replay need is specified as **v2** in `docs/warcraftlogs-bridge.md`, including one new endpoint (`/timeline`) that does not exist yet. Every v2 field is optional and additive: a missing block degrades to "keine Daten" in the UI and to an unrated (zero-star) area in the Academy, never to a bad rating. `RaidSnapshot.has_analysis` is the single switch the UI uses for that, instead of null-checking each field.

### Archive mode: reviewing a past report instead of the live feed

Both WeintTV and the Academy can also show a single, long-finished WarcraftLogs fight instead of the live feed — pick a report, pick a pull inside it. This is deliberately **not** called "Verlauf" in the UI (that name is already taken by WeintTV's own completed-pulls-this-session tab, backed by `PullSummary`/`history()`); the second, unrelated "past report" concept is called **"Archiv"** everywhere in code and UI to avoid the collision. It's also deliberately global on `RaidDataService`, not per-page state: the same "one snapshot" principle that keeps WeintTV and the Academy from diverging on the live feed applies here too, so switching to Archive on one page switches it on the other.

`RaidDataService` grows a `MODE_LIVE`/`MODE_ARCHIVE` mode plus an `ArchiveState` (reports/fights lists, loading/error flags per step, current selection), exposed via `archive_state()` and mutated through `enter_archive_mode()` → `select_archive_report()` → `select_archive_fight()` → `show_live()`, each step notifying `gui/widgets/tv/archive_picker.py` (shared by both pages) through the `archiveChanged` signal. Each step's HTTP call runs in its own short-lived thread (same pattern as `WarcraftLogsProvider`'s fetch thread) so a slow bot response never freezes the UI; a stale in-flight result (user already picked something else by the time it lands) is detected and dropped. Picking a fight publishes a normal `RaidSnapshot` via `_publish(snapshot, track=False)` — same function the live poll uses, `track=False` just means it doesn't pollute the session's `PullSummary` history, since it isn't a pull that's actually happening now. While pinned to an archived fight, the live poll thread keeps running in the background (harmless — it's either pure computation or reads from an existing cache) but its results are discarded rather than published, so switching back to Live is instant instead of waiting for the next poll tick.

`core/warcraftlogs_archive_client.py` is the HTTP half for three additional bot endpoints (report list, fight list per report, one fight by ID) — same auth/error shape as the live client. The single-fight endpoint deliberately returns the *exact same JSON shape* as the live endpoint's `"ok"` response, so `snapshot_from_payload()` handles both live and archived fights unchanged (just with `live=False` for the latter). Full contract for all three in `docs/warcraftlogs-bridge.md`; **none of the three bot endpoints exist yet either** — same "reports gracefully as unavailable, mock/live stays usable" story as the live endpoint.

### Replay: playing a finished pull back second by second

The Play button in `ArchivePicker` starts a **replay**. `analyzer/replay/` is the one deliberate exception to "the `RaidSnapshot` is the only contract": a replay needs the whole fight, so `FightTimeline` describes the full course of one. It still never reaches a widget — the only reader is `snapshot_at(timeline, seconds)`, which returns an ordinary `RaidSnapshot`. For WeintTV and the Academy a replay is therefore indistinguishable from a live feed.

That is also where the two modules' synergy comes from for free: because every Academy metric reads the snapshot, the Academy automatically rates the state of the second being shown, with no replay code on its side.

All timeline series are **cumulative**. Seeking then costs the same as playing, and interpolation between samples keeps the boss bar smooth at 8×; from per-tick deltas both would need a running sum from the start. `snapshot_at()` is pure and must never raise — it runs four times a second. What can't honestly be reconstructed per second (consumables, the full per-ability damage breakdown) stays **empty** rather than estimated and only appears at the end from `FightTimeline.aggregate`; per-player-per-ability series would be megabytes per fight, and invented numbers are exactly what makes a deep analysis untrustworthy.

`RaidDataService` grows `MODE_REPLAY` as a third value of the **same** `ArchiveState.mode` field — a second "am I suppressed" flag is how the live poll eventually overwrites a replay frame. `_poll_once()` therefore checks `browsing` (not live) rather than naming the archive mode. The clock is a `QTimer` on the main thread, not another thread: reconstruction is pure computation over ≤25 players, and a thread would have to hand its results back through a signal anyway. It ticks through `_advance_replay(delta)` so tests can step a replay without waiting on a real clock. Every replay frame publishes with `track=False` — the pull number never changes during playback, so tracking would append one history entry per tick. Loading the timeline runs in a short-lived thread with the same stale-result check as the archive fetches.

One trap this uncovered: `SegmentedControl.setValue()` silently does nothing for an unknown value, so `ArchivePicker` must map `MODE_REPLAY` back onto the view it was started from, or the Live/Archive switch freezes on its old state.

Live combat-log parsing does not exist yet either: `analyzer/combatlog/` currently contains only `locator.py` (which really does find `Logs/WoWCombatLog*.txt` and is surfaced in Settings → Module). The tailer, event parser and aggregators are the next step; the provider contract is already in place for them.

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

`core/paths.py` centralizes all on-disk locations (config/cache/downloads/backups/logs/reports), branching on `platform.system()`: `~/.local/share/WeintCompanion` on Linux, `%LOCALAPPDATA%/WeintCompanion` on Windows. Rule of thumb for new files: anything reproducible goes under `cache()`, anything the user would be upset to lose goes under `config()`.

One Qt rendering trap worth knowing: the global stylesheet sets `QWidget { background: transparent; }`, so any widget that must paint its own background needs `setObjectName(...)` + `setAttribute(Qt.WA_StyledBackground, True)` + an ID-scoped rule. And at ~10px, QLabel's computed height clips the dots on capital umlauts ("NÄCHSTE" renders as "NACHSTE") — small mono eyebrow labels should therefore be created with `gui/widgets/eyebrow.py`'s `eyebrow_label()`, which measures the real ink extent and sets a minimum height.

`app.py` sets up crash diagnostics and several Linux/Qt workarounds *before* importing PySide6 — read the inline comments there before touching Qt platform env vars, they encode hard-won fixes for real crash reports:
- `faulthandler` writes native (non-Python) crash tracebacks to `cache/logs/crash.log`, since a SIGSEGV in Qt's xcb plugin never raises a Python exception.
- `QT_QPA_PLATFORM=wayland;xcb` lets Qt itself choose, rather than the app guessing from `XDG_SESSION_TYPE`.
- `QT_XCB_NO_XI2`, `QT_ACCESSIBILITY=0`, `QT_XCB_GL_INTEGRATION=none` are always-on mitigations for distro-specific xcb SIGSEGVs (libxkbcommon/AT-SPI/Mesa), each individually escape-hatchable via `WEINT_FORCE_*` env vars for users the mitigation itself breaks.

### Config and auth

`core/config.py` is a flat JSON-backed settings store (`config.json` in `Paths.config()`) with a defaults dict merged on load so new settings get backfilled into existing installs. Discord account linking is fully implemented: `core/discord_auth.py`'s `DiscordAuth.login()` runs the real OAuth2 flow (local callback server, system browser to Discord, code exchange against the bot's `/companion/auth/exchange`), and `core/discord_account.py`'s `DiscordAccountStore` persists the resulting identity plus a bot-issued `companion_token` (never the real Discord OAuth token) to `discord_account.json`. That `companion_token` is the bearer credential used everywhere downstream (`CharacterSyncClient`, `DiscordRosterSync`, generic sync) to check "is a Discord account linked" and to authenticate against the bot.

### "What's new" popup

`gui/dialogs/whats_new_dialog.py`'s `show_whats_new_if_needed()` is triggered once via `QTimer.singleShot(0, ...)` at the end of `MainWindow.__init__` (independent of `CompanionManager`'s async init, since its content is local/bundled, not network-fetched). It compares `config.data["onboarding_seen_version"]` against `core.version.VERSION`: empty (fresh install or an upgrade from any pre-1.0 version, since the key never existed before) shows the hardcoded multi-page `TOUR_PAGES` feature walkthrough; any other mismatch shows the changelog entries between the two versions, read from the bundled `CHANGELOG.md` via `core/changelog_reader.py` (must stay listed in `WeintCompanion.spec`'s `datas`). Either way the dialog updates `onboarding_seen_version` on close; its "don't show again" checkbox sets `config.data["whats_new_enabled"] = False`, which short-circuits the whole check on future starts. Both are user-reversible via the "Willkommens-Tour" toggle/button in Settings → Allgemein (`gui/pages/settings_sections/general.py`), which calls `show_tour()` unconditionally (bypassing the seen-version check).
