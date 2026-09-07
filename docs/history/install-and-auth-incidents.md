# Incident history: an index, not a duplicate

Full detail for each of these lives in the linked system doc — this file
exists as a fast chronological overview.

## Install/update incidents

- **A failed install logged `SUCCESS` right after `ERROR`.**
  `install_or_update()` returns a `WorkflowResult` that two call sites
  discarded, reporting success on "no exception thrown" alone. Fixed with
  a structural AST test forbidding a bare statement call anywhere in
  `gui/`/`core/`. Detail: `../systems/update-system.md`.
- **"Zugriff verweigert" had two causes needing opposite fixes**
  (permissions vs. WoW still running) and looked identical from outside.
  Fixed with a writability probe instead of a platform-dependent process
  check. Detail: `../systems/update-system.md`.
- **The backup archived the wrong half** — the addon folder (already on
  GitHub) instead of the SavedVariables (genuinely unrecoverable). Fixed
  by backing up both, separately. Detail: `../development/paths-and-storage.md`.
- **Startup could hang invisibly under the splash on Windows** — a `0ms`
  `QTimer.singleShot` in `__init__` fired *before* `window.show()` because
  of how `processEvents()` advances timers, so a modal "What's new"
  dialog waited under an always-on-top splash with no crash, no log line.
  Fixed by moving the popup trigger to `showEvent` and replacing
  `processEvents()` with `repaint()` in the splash's progress stages.
  Detail: `../architecture/qt-pitfalls.md`.
- **A closeEvent handed to a hideEvent handler segfaulted with no Python
  traceback.** `OverlayWindow.closeEvent()` called
  `self.hideEvent(event)` directly; Qt reads the `QCloseEvent*` as a
  `QHideEvent*` unchecked. Fixed with a plain, event-free teardown method
  tolerant of being called twice. Detail: `../architecture/qt-pitfalls.md`.

## Auth incidents

- **Every bot deploy invalidated every Companion link at once** — "I have
  to reconnect Discord again" was the most-reported complaint, caused by
  the bot's pairing token being a key into a database wiped on every
  restart. Fixed on the bot side with self-verifying signed tokens.
  Detail: `../companion-auth.md`.
- **A single 401 unlinked the account**, and a retry loop could
  manufacture three "rejections" from one incident in fifteen seconds.
  Fixed with a rejection-count threshold plus a cooldown window. Detail:
  `../companion-auth.md`.
- **A login that couldn't open a browser waited two minutes before
  failing.** `login()` discarded `open_url()`'s return value. Fixed to
  fail immediately with the address to open by hand. Detail:
  `../companion-auth.md`.

## Update-visibility incidents

- **`state_changed` didn't exist at all past startup** — the update
  display was only ever right immediately after `full_refresh()`
  finished, since nothing re-asked afterward. Fixed with `UpdateWatch`
  riding the sync cycle. Detail: `../systems/update-system.md`.
- **A page's `refresh()` calling `full_refresh()` created an infinite
  redraw loop** once `state_changed` existed — 826 GitHub requests in a
  run that needs seven. Fixed by moving the network call into a
  short-lived thread plus a re-entrancy guard, with a structural AST test
  against recurrence. Detail: `../architecture/navigation.md`.

## Identity/data-gap incidents

- **"Who is me" had four independent, disagreeing answers** across the
  Academy combo box, config, `PlayerProfile.name`, and the in-game
  character. Fixed with one resolution function and a single point of
  persistence. Detail: `../systems/weinttv-academy.md` ("Who is 'me'?").
- **WarcraftLogs v2 fields silently produced nothing**, three independent
  times (localized ability names, wrong Buffs/Debuffs table shape,
  missing self-buff split) — each looked in the UI exactly like "the bot
  doesn't send this yet". Detail:
  `../../../WeintCodex-Bot/docs/systems/warcraftlogs-ingestion.md`.
- **A memory crash on some bosses but not others** was actually driven
  by pull length, not the boss, on a 0.15 GB host loading full event
  streams concurrently. Detail:
  `../../../WeintCodex-Bot/docs/systems/warcraftlogs-ingestion.md`.
