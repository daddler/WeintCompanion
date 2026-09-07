# Archive mode: reviewing a past report instead of the live feed

Both WeintTV and the Academy can also show a single, long-finished
WarcraftLogs fight instead of the live feed — pick a report, pick a pull
inside it. This is deliberately **not** called "Verlauf" in the UI (that
name is already taken by WeintTV's own completed-pulls-this-session tab,
backed by `PullSummary`/`history()`); the second, unrelated "past report"
concept is called **"Archiv"** everywhere in code and UI. It's also
deliberately global on `RaidDataService`, not per-page state — switching
to Archive on one page switches it on the other.

`RaidDataService` grows a `MODE_LIVE`/`MODE_ARCHIVE` mode plus an
`ArchiveState` (reports/fights lists, loading/error flags per step,
current selection), exposed via `archive_state()` and mutated through
`enter_archive_mode()` → `select_archive_report()` →
`select_archive_fight()` → `show_live()`, each step notifying
`gui/widgets/tv/archive_picker.py` (shared by both pages) through the
`archiveChanged` signal. Each step's HTTP call runs in its own
short-lived thread; a stale in-flight result is detected and dropped.
Picking a fight publishes via `_publish(snapshot, track=False)` — same
function the live poll uses, `track=False` just means it doesn't pollute
`PullSummary` history. While pinned to an archived fight, the live poll
thread keeps running in the background (harmless) but its results are
discarded rather than published, so switching back to Live is instant.

`core/warcraftlogs_archive_client.py` is the HTTP half for three
additional bot endpoints (report list, fight list per report, one fight
by ID) — full contract: `../warcraftlogs-bridge.md`. **Trash is not a
pull**: `build_fight_list()` skips `encounter_id <= 0`, mirroring the
bot's own filter (belt-and-suspenders — the list comes from a server not
updated together with the app). The single-fight endpoint returns the
*exact same JSON shape* as the live endpoint's `"ok"` response.

## Finding an archived pull: the browser, not two dropdowns

Through 2.8.0 the archive was two combo boxes — twenty identical-looking
reports, sixty pulls, all shaped "Pull 14 · Garrosh · 42% · 06:31" in no
order but the evening's. Reported as "quite complicated to find archived
logs" — the data was all there and it found nothing.
`gui/dialogs/archive_dialog.py` replaces it: evenings on the left, that
evening's pulls grouped by boss on the right, a search field, a *Nur
Kills* switch, time of day on every pull.

`core/archive_index.py` is the pure half (grouping, search, best try,
labels) — no Qt, no `httpx`. Six rules that are not taste:

- **Pulls are grouped in the order of the evening, never alphabetically.**
- **`best_try()`**: a kill beats every wipe, among wipes the lowest boss
  share wins, at equal share the longer fight. An empty list answers
  `None`; a lone wipe is not marked (no distinction without competition);
  next to a kill it's not marked either.
- **A report without a readable date lands under "Ohne Datum" at the
  end** — same line as `stars == 0`. A pull whose time the bot doesn't
  know shows no time rather than "00:00".
- **The rows hand their click out as a Signal to a bound method** — a
  callback closure holding the window builds a cycle the collector can't
  see (see `../architecture/qt-pitfalls.md`). `tests/test_archive_dialog.py`
  builds the window repeatedly and collects in between.
- **Both columns compare a signature before rebuilding**
  (`archiveChanged` arrives several times per load).
- **The window closes only for the pull clicked *in it*** (`_awaiting`).
  An error closes nothing; a click doesn't close either (one archived
  pull costs the bot minutes).

`ArchivePicker` in the page itself is deliberately small: the mode
switch, the button into the browser, one line saying **what is loaded**
(not what is selected — the old combo boxes showed the selection, which
after a failed fetch still named a pull the user did not have in front of
them). `archive_index.selection_text()` formats that sentence once for
both pages.

## Replay: playing a finished pull back second by second

The Play button in `ArchivePicker` starts a **replay**.
`analyzer/replay/` is the one deliberate exception to "the `RaidSnapshot`
is the only contract": a replay needs the whole fight, so `FightTimeline`
describes the full course of one. It still never reaches a widget — the
only reader is `snapshot_at(timeline, seconds)`, which returns an
ordinary `RaidSnapshot`. For WeintTV and the Academy a replay is therefore
indistinguishable from a live feed — the Academy rates whichever second
is shown, with **no replay code on its side**.

All timeline series are **cumulative** (seeking costs the same as
playing; interpolation keeps the boss bar smooth at 8×). `snapshot_at()`
is pure and must never raise — it runs four times a second. What can't
honestly be reconstructed per second (consumables, full per-ability
damage breakdown) stays **empty** rather than estimated, appearing only
at the end from `FightTimeline.aggregate`.

`RaidDataService` grows `MODE_REPLAY` as a third value of the **same**
`ArchiveState.mode` field. `_poll_once()` checks `browsing` (not live)
rather than naming the archive mode. The clock is a `QTimer` on the main
thread (reconstruction is pure computation over ≤25 players); it ticks
through `_advance_replay(delta)` so tests can step it without a real
clock. Every replay frame publishes with `track=False`. Loading the
timeline runs in a short-lived thread with the same stale-result check as
the archive fetches.

**The clock is never touched directly.** Every state change calls
`_sync_replay_clock()`, which emits the private `_clockRequested` signal;
`_apply_replay_clock()` then **derives** from the state whether the timer
should run. A `QTimer` may only be driven from its owning thread —
`QTimer.start()` from a worker is refused by Qt *with a message on stderr
and no exception*, so the replay used to sit silently at 00:00 while the
state and the UI both claimed it was playing. The signal must carry no
"start/stop" payload: queued from a worker it arrives later, and a stale
"start" would wind the clock up for a replay that had already ended.

## Five things the Play button needs, each once missing

- **`replay_available()` creates the provider instead of only inspecting
  it.** Reading `self._provider` while a page is being built (before the
  poll thread exists) always answered "no" and nothing re-asked.
- **The question is whether the class *overrides* `timeline`**, not
  `hasattr` — `RaidDataProvider` defines it and returns `None`, so
  `hasattr` is always true.
- **Changing report, pull or data source calls `_discard_replay()`.**
  `start_replay()` treats an already-loaded timeline as "just rewind"; a
  leftover one meant Play replayed the *wrong* fight. Returns to
  `ReplayState.origin`, not blindly to the archive.
- **The timeline is prefetched, but *after* the fight, not beside it.**
  `_fetch_fight_worker()` starts `prefetch_timeline()` only once the
  fight has arrived — running the two in parallel had both compete for
  the same 0.15 vCPU host request the user was waiting for, causing "Bot
  nicht erreichbar" timeouts. `ReplayState.starting` records a click
  during the fetch and honours it when the data lands (one fetch, not
  two); `loading` and `starting` are different questions —
  `ArchivePicker` greys the button only for `starting`.
- **Every archive endpoint gets the timeout its work deserves** —
  `TIMEOUT` 40s for the two lists, `FIGHT_TIMEOUT` 180s, `TIMELINE_TIMEOUT`
  240s. `_get()` translates `httpx.TimeoutException` into a German
  sentence naming the next step, and carries the bot's `detail` into the
  message for non-200 answers.

`SegmentedControl.setValue()` silently does nothing for an unknown value,
so `ArchivePicker` must map `MODE_REPLAY` back onto the view it was
started from, or the Live/Archive switch freezes on its old state.

## Replay ticks at 4 Hz — three consequences that were once real defects

- **`ArchivePicker` must not rebuild its combo boxes on every tick.**
  `_fill_reports`/`_fill_fights` compare a content signature first — an
  open dropdown used to snap shut four times a second during playback.
- **A hidden page must not draw.** `_on_snapshot()` on both pages returns
  unless `self._attached`; `on_enter()` draws once directly.
- **`setStyleSheet()` is not a setter** — see `../architecture/theming.md`
  ("`setStyleSheet()` is not a setter").
