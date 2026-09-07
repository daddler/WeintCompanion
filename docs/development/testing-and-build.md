# Testing and building

## Commands

```bash
pip install -r requirements.txt   # install dependencies
python app.py                     # run the app
```

Tests live in `tests/` and run with pytest (`pip install -r
requirements-dev.txt && python -m pytest tests/ -q`). They cover the
framework-agnostic parts — config, installer, Lua/sync parsing, the
analyzer and its academy evaluation, the replay reconstruction, and the
navigation registry — plus `RaidDataService`'s live/archive/replay state
machine and the live-update wiring in `tests/test_live_updates.py` (the
update watch, the schedule sync's adaptive interval and change reporting,
and the one `state_changed` the sync cycle makes of it — the last of
those calls the real `_run_sync_worker()` on a `SimpleNamespace` rather
than building a `CompanionManager`), both of which need PySide6 and httpx
and `importorskip` themselves away when missing.

Five files **do** build widgets, all `importorskip("PySide6")` and all
running under `QT_QPA_PLATFORM=offscreen`: `test_overlay_window.py`,
`test_accent_follows.py`, `test_appearance_section.py`,
`test_theme_connections.py`, `test_update_visibility.py`. They exist
because the defects they cover are invisible to every non-visual test —
a colour that silently stops following the accent, a control that's
simply not there, a `lambda` that keeps a widget alive forever, and a
segfault with no Python traceback. Needs the Qt system libraries
(`libegl1`, `libgl1`, `libxkbcommon-x11-0`, `libxcb-cursor0` and friends)
— without them PySide6 fails to import and those files skip themselves.
There is no linter or formatter configured.

## Building distributables

```bash
./scripts/build_linux.sh          # PyInstaller build -> dist/WeintCompanion
./scripts/build_appimage.sh       # wraps the Linux build into an AppImage (requires linuxdeploy)
./scripts/build_windows.ps1       # PyInstaller + Inno Setup -> dist/WeintCompanion-Setup.exe
```

CI (`.github/workflows/build.yml`) builds Linux (AppImage) and Windows
(Inno Setup installer) on every `v*` tag push and publishes a GitHub
Release with both artifacts. `WeintCompanion.spec` is the PyInstaller
spec (entry point `app.py`, bundles `assets/`, `resources/icons`, and the
Linux updater script; also lists `CHANGELOG.md` under `datas` — see
`../systems/update-system.md`).

## Where the tests that matter for each system live

- Theme/accent/lambda-leak tests: `tests/test_accent_follows.py`,
  `tests/test_theme_connections.py` — see `../architecture/theming.md`.
- Overlay teardown SIGSEGV guard: `tests/test_overlay_window.py` — see
  `../architecture/qt-pitfalls.md`.
- Startup popup ordering: `tests/test_startup_popups.py` — see
  `../architecture/qt-pitfalls.md`.
- `install_or_update()` result must never be discarded (AST check):
  `tests/test_install_failure.py` — see `../systems/update-system.md`.
- `RaidDataService` shutdown (segfault guard for a replay `QTimer`
  collected off-thread): autouse fixture in
  `tests/test_raid_data_service.py`.
- Lesson catalog completeness/typos, class-ability spell-ID collisions:
  `tests/test_lesson_catalog.py`, `tests/test_class_abilities.py` — see
  `../systems/weinttv-academy.md`.
- Stat-weights/QE-Live parser parity with the addon's own Lua tests:
  `tests/test_stat_weights.py`, `tests/test_qelive.py` — see
  `../systems/sim-pages.md`.
