# Qt/PySide6 pitfalls, platform paths, and startup ordering

## Layering

- **`core/`** – all business logic, framework-agnostic where possible (Qt
  is used for `QObject`/`Signal` in a few places like `CompanionManager`,
  `RaidDataService` and `AppState`).
- **`gui/`** – PySide6 UI: `main_window.py` (frameless, own title bar),
  `navigation.py` (see `navigation.md`), `pages/`, `widgets/` (incl.
  `tv/`, `academy/`), `theme/` (see `theming.md`), `layout/breakpoints.py`,
  `motion/pulse_clock.py`, `overlay/` (the small always-on-top window),
  `controllers/`, `dialogs/` (`whats_new_dialog.py`, `setup_wizard.py`).
- **`analyzer/`** – the Raidlog Analyzer. **Contains no Qt import at
  all**, deliberately: it must stay testable without a running UI and
  extractable into its own package later.
- **`addon/`** – reads and writes the WoW addon's Lua `SavedVariables`
  files (`finder.py`, `reader.py`, `sync_reader.py`,
  `inbox_writer.py`/`addon_inbox.py`, `addon_payloads.py`).
- **`discord/`** – `sync_client.py`, a thin HTTP client for the
  material-sync bridge.

## `CompanionManager` is the app's central hub

`core/companion_manager.py` wires together nearly every subsystem
(config, logger, GitHub updater, backup, installer, self-updater,
launcher, sync manager, Discord status/auth/roster-sync) and is owned by
the GUI layer. Its `full_refresh()` is the app's main "check everything"
entry point: detect WoW install → detect addon → check GitHub for addon
updates → check Discord bot status → check for Companion self-updates →
run sync. `refresh_update_status()` is the lighter variant used by the
manual "check for updates" button (skips Discord/sync).

Initialization pattern to preserve: `initialize()` schedules
`_initialize_async` via `QTimer.singleShot` so the window renders before
the background `InitThread` runs `full_refresh()`. Because that thread
has no Qt event loop of its own, it can't reliably reach the main thread
with `QTimer.singleShot(0, ...)` — it signals `_AutoSyncStarter.requested`,
a cross-thread Qt signal, to invoke `start_auto_sync()` back on the main
thread instead. Auto-sync itself runs on a recurring `QTimer`
(`sync_interval` from config) that spawns a new `SyncThread` per tick,
guarded by `_sync_busy` + a lock so overlapping syncs never run
concurrently.

## Never hand one Qt event handler another one's event

`OverlayWindow.closeEvent()` called `self.hideEvent(event)` to reuse the
detach logic, which passed a `QCloseEvent` down to
`QWidget::hideEvent(QHideEvent*)`; Qt reads that pointer as a `QHideEvent`
unchecked, and closing the overlay ended the process with SIGSEGV — **no
Python exception, no traceback**, which is why no amount of "does it
raise?" testing found it. Shared teardown belongs in a plain method that
takes no event (`OverlayWindow._release()`), and that method has to
tolerate being called twice, since `close()` also produces a hide on some
platforms — double-detaching would push the service's reference count
below the number of real subscribers and stop the poll thread while
WeintTV is still watching. `tests/test_overlay_window.py` covers it; that
the process reaches the assertion at all *is* the assertion.

The same class of bug (a callback closure that outlives its window and
gets reached into after the C++ object is gone → SIGSEGV, no traceback)
recurs in `gui/dialogs/archive_dialog.py` (rows hand their click out as a
signal to a bound method rather than a captured callback) and in
`SegmentedControl` (a lambda closing a control → button → connection →
lambda → control cycle the garbage collector can't see). Same fix pattern
each time: a bound method, never a closure holding the window.

## The splash must repaint itself, never run the event loop

`app.py` builds `MainWindow` behind the splash and used
`app.processEvents()` to advance the progress bar between stages.
`MainWindow.__init__` scheduled the startup popups with
`QTimer.singleShot(0, …)`. That did the opposite of the intent ("so the
window becomes visible first"): the 0 ms timer fires in the *next*
`processEvents()` — i.e. **before** `window.show()`.
`show_whats_new_if_needed()` opens a modal dialog after every update,
`exec()` sits in its own event loop, the splash is
`WindowStaysOnTopHint` and its `close()` comes after `show()` — so on
Windows the dialog waited invisibly under the splash and the app hung at
exactly that progress label, with no crash, no log line and no way out
but Escape.

Three things now make that state impossible rather than unlikely:
`_stage()` calls `splash.repaint()` (synchronous paint, runs nothing
else) instead of `processEvents()`, of which exactly one remains — right
after `splash.show()`, before any `MainWindow` exists to queue anything;
the popups hang on `MainWindow.showEvent` (guarded by
`_startup_popups_queued`, since `showEvent` also fires on every restore
from the tray), because "when the window is up" is a question only the
window can answer; and `splash.close()` runs before `_show_main_window()`
hands control back to the loop. `tests/test_startup_popups.py` holds all
three plus the end-to-end order. **A progress bar is there to draw, not
to get work done.**

## Miscellaneous rendering/platform traps

- The global stylesheet sets `QWidget { background: transparent; }`, so
  any widget that must paint its own background needs
  `setObjectName(...)` + `setAttribute(Qt.WA_StyledBackground, True)` +
  an ID-scoped rule.
- At ~10px, `QLabel`'s computed height clips the dots on capital umlauts
  ("NÄCHSTE" renders as "NACHSTE") — small mono eyebrow labels should
  therefore be created with `gui/widgets/eyebrow.py`'s `eyebrow_label()`,
  which measures the real ink extent and sets a minimum height.
- `app.py` sets up crash diagnostics and several Linux/Qt workarounds
  *before* importing PySide6 — read the inline comments there before
  touching Qt platform env vars: `faulthandler` writes native crash
  tracebacks to `cache/logs/crash.log` (a SIGSEGV in Qt's xcb plugin
  never raises a Python exception); `QT_QPA_PLATFORM=wayland;xcb` lets Qt
  itself choose rather than the app guessing from `XDG_SESSION_TYPE`;
  `QT_XCB_NO_XI2`, `QT_ACCESSIBILITY=0`, `QT_XCB_GL_INTEGRATION=none` are
  always-on mitigations for distro-specific xcb SIGSEGVs, each
  individually escape-hatchable via `WEINT_FORCE_*` env vars.

## Platform-specific paths

`core/paths.py` centralizes all on-disk locations
(config/cache/downloads/backups/logs/reports), branching on
`platform.system()`: `~/.local/share/WeintCompanion` on Linux,
`%LOCALAPPDATA%/WeintCompanion` on Windows. Rule of thumb for new files:
anything reproducible goes under `cache()`, anything the user would be
upset to lose goes under `config()`. Atomic-write and backup rules for
what's stored there: `../development/paths-and-storage.md`.

Tests that build a `RaidDataService` must shut it down
(`tests/test_raid_data_service.py` has an autouse fixture). A service left
with a running replay holds an active `QTimer`; when Python later
collects it during a worker thread's allocation, `~QObject` runs on the
wrong thread and the process segfaults. In the app this cannot happen —
`CompanionManager` owns the service and calls `shutdown()`.
