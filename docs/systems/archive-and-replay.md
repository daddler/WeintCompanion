# Archive mode: reviewing a past report instead of the live feed

The Raid Center can also show a single, long-finished WarcraftLogs fight
instead of the live feed — pick a report, pick a pull inside it. Its
*Quelle* perspective is where that happens (`gui/pages/raid/source_view.py`,
see `raid-center.md`).

The word **"Archiv"** means "a past report" everywhere in code and UI.
Through 3.6.0 the other concept — *this session's* completed pulls,
backed by `PullSummary`/`history()` — was called "Verlauf" in WeintTV's own
tab, one word for two unrelated things in two different areas. Since 4.0
both stand under each other in *Quelle* and are named what they are:
**Raidabende** and **Diese Sitzung**.

The state is deliberately global on `RaidDataService`, not per-view —
every perspective reads the same selection, which is why switching from
*Quelle* to *Analyse* shows the pull you just picked rather than asking
again.

`RaidDataService` grows a `MODE_LIVE`/`MODE_ARCHIVE` mode plus an
`ArchiveState` (reports/fights lists, loading/error flags per step,
current selection), exposed via `archive_state()` and mutated through
`enter_archive_mode()` → `select_archive_report()` →
`select_archive_fight()` → `show_live()`, each step notifying its readers
(the Raid Center's context header and *Quelle* view) through the
`archiveChanged` signal.

**`ensure_reports()` is the fifth entry point, added in 4.0**: it loads
the report list *without* touching the mode. `ArchiveBrowser.__init__()`
used to call `enter_archive_mode()`, which was right while the list lived
in a dialog someone opened deliberately. As a perspective one click from
*Live*, merely looking at which evenings exist must not stop the live feed
(the poll discards its results as soon as `browsing` holds). The two
selection steps still set the mode themselves. Each step's HTTP call runs in its own
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
`gui/widgets/raid/archive_browser.py` replaces it: evenings on the left,
that evening's pulls grouped by boss on the right, a search field, a *Nur
Kills* switch, time of day on every pull.

**Since 4.0 there is no window around it at all.** It was a widget from
3.5.0 on, but wrapped in `ArchiveDialog` for WeintTV and the Academy
(reached through a *Log wählen …* button) *and* embedded on the Archiv
page — two ways to the same list, one laying itself over the other. The
dialog is gone; the list is the *Quelle* perspective, so it is a place and
not a curtain. `fightLoaded` is what the closing used to be: the Raid
Center switches to *Analyse* on it. The three rules that were about the
window still hold for the signal — it fires only for the pull clicked *in
the list* (`_awaiting`), never while the fetch is still running, and never
on an error.

Two things about the list that are not taste: there is exactly **one**
implementation (a second would group differently after the first change),
and the status line says what is **loaded**, not what was clicked —
`archive_index.selection_text()` formats that sentence once for everyone
who shows it.

**The quick selection above it** (`Letzter Raid` / `Letzter Kill` /
`Bester Versuch`) is `latest_report()`/`last_kill()`/`best_attempt()` in
`core/archive_index.py`, decided there and not in the view for the same
reason as `best_try()`. A button that would hit nothing is disabled, not
hidden (*lock, don't hide*), and `best_attempt()` reuses `best_try()` so
the button and the marking in the list can never point at different rows.

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
  callback closure holding the widget builds a cycle the collector can't
  see (see `../architecture/qt-pitfalls.md`). `tests/test_archive_browser.py`
  builds the browser repeatedly and collects in between.
- **Both columns compare a signature before rebuilding**
  (`archiveChanged` arrives several times per load).
- **`fightLoaded` fires only for the pull clicked *in the list***
  (`_awaiting`). An error reports nothing; neither does the click itself
  (one archived pull costs the bot minutes).

The Live/Archive switch lives once, in *Quelle*, next to that line —
through 3.6.0 it was an `ArchivePicker` on all three pages. The way
*back* is a button in the context header rather than the other half of a
switch: while something other than the live feed is shown, "back to the
running raid" is the most common next intention, and it sat buried in a
two-way control you had to find first.

## Replay: playing a finished pull back second by second

The Play button in the context header starts a **replay**.
`analyzer/replay/` is the one deliberate exception to "the `RaidSnapshot`
is the only contract": a replay needs the whole fight, so `FightTimeline`
describes the full course of one. It still never reaches a widget — the
only reader is `snapshot_at(timeline, seconds)`, which returns an
ordinary `RaidSnapshot`. For every perspective a replay is therefore
indistinguishable from a live feed — *Lernen* rates whichever second is
shown, with **no replay code on its side**.

All timeline series are **cumulative** (seeking costs the same as
playing; interpolation keeps the boss bar smooth at 8×). `snapshot_at()`
is pure and must never raise — it runs four times a second. What can't
honestly be reconstructed per second (consumables, full per-ability
damage breakdown) stays **empty** rather than estimated, appearing only
at the end from `FightTimeline.aggregate`.

`RaidDataService` grows `MODE_REPLAY` as a third value of the **same**
`ArchiveState.mode` field. The Play button sits in the Raid Center's
context header, and the seek deep link (*Moment mm:ss* on a weakness under
*Lernen*) goes through `RaidCenterPage.show_moment()` — see
`raid-center.md`. `_poll_once()` checks `browsing` (not live)
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
  the context header greys the button only for `starting`.
- **Every archive endpoint gets the timeout its work deserves** —
  `TIMEOUT` 40s for the two lists, `FIGHT_TIMEOUT` 180s, `TIMELINE_TIMEOUT`
  240s. `_get()` translates `httpx.TimeoutException` into a German
  sentence naming the next step, and carries the bot's `detail` into the
  message for non-200 answers.

`SegmentedControl.setValue()` silently does nothing for an unknown value,
so *Quelle*'s mode switch must map `MODE_REPLAY` back onto `MODE_ARCHIVE`,
or it freezes on its old state.

## Replay ticks at 4 Hz — three consequences that were once real defects

- **`ArchiveBrowser` must not rebuild its columns on every tick.**
  `_fill_days`/`_fill_fights` compare a content signature first — the
  scroll position used to jump four times a second during playback, and
  the old combo boxes' dropdowns used to snap shut.
- **A hidden page must not draw.** `RaidCenterPage._on_snapshot()` returns
  unless `self._attached`; `on_enter()` draws once directly. And only the
  *visible* view is drawn — `_draw()` picks one, because a learn view that
  nobody sees still builds a full profile and training plan per frame.
- **`setStyleSheet()` is not a setter** — see `../architecture/theming.md`
  ("`setStyleSheet()` is not a setter").
