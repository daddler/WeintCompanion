# The Raid Center: one pull, four perspectives

## What this replaced, and why it was not a cosmetic problem

Through 3.6.0 the RAID group had four nav entries: *Übersicht*, *WeintTV*,
*Academy*, *Archiv*. The last three shared a data source, a `RaidSnapshot`
and an `ArchiveState` — **invisibly**. The user had to know:

- when to open WeintTV, when the Academy, when the Archive,
- how to find a past pull,
- how to get from an analysed pull to a matching lesson.

That last path was the worst one, and it went: Analyse → sidebar →
Academy → pick a character → find the pull again → find the lesson. Every
step existed because the *pull* was not the object the interface was built
around; the modules were.

Since 4.0 a **raid/pull is the object** and Live, Analyse, Lernen, Quelle
are four looks at it. `gui/pages/raid_center.py` does exactly four things:
hold the context header, distribute one snapshot, resolve deep links, and
build views on demand. It holds **no** archive state, **no** replay state
and **no** fight selection — those stay on `RaidDataService`, which is
still the single truth (`ArchiveState`, `ReplayState`). A second holder
beside it would be two truths about one pull.

```
            ┌─ RaidContextHeader ────────── outside the stack, never swapped
            │   boss · pull · outcome · % · duration · weekday · time
            │   character · source chip · [▶ Wiedergabe] [Zum laufenden Raid]
            ├─ [ Live | Analyse | Lernen | Quelle ]  + one explaining sentence
            ├─ ReplayBar        (self-hiding, one instance for all four)
            ├─ LoadingCard      (self-hiding, one instance for all four)
            └─ QStackedWidget
                 ├─ scroll(LiveView)        gui/pages/raid/live_view.py
                 ├─ scroll(AnalysisView)    gui/pages/raid/analysis_view.py
                 ├─ scroll(LearnView)       gui/pages/raid/learn_view.py
                 └─ SourceView              gui/pages/raid/source_view.py
```

## `core/raid_context.py` is a projection, not a store

`context_from(service, character)` reads only the existing accessors
(`archive_state()`, `replay_state()`, `current()`, `active_source()`) and
returns a frozen `RaidContext`. Qt-free, like `core/archive_index.py` —
*which sentence stands over the screen* is where something can be wrong,
and you don't need a window for that.

Four rules it must not cross:

- **The snapshot says what runs; the fight list says when it was.** A
  `RaidSnapshot` carries no timestamp of the pull (it describes a moment,
  not a calendar entry); a `FightSummary` does. The context takes each
  field from whichever source knows it rather than inventing a date.
- **`snapshot.encounter_name` is not the boss name.** It answers "Kein
  Kampf" when there is no encounter; adopted as the boss name, the header
  could no longer tell whether a fight exists and would lose its empty
  state (`empty_line()`/`empty_hint()` — three situations, three
  sentences: loading, nobody fighting, nothing picked).
- **`outcome_of()` is the one derivation** of the three-valued outcome.
  `gui/widgets/tv/encounter_meta.outcome_text()` only phrases it. A kill
  carries no boss share beside it — "Kill · 0 %" is the same fact twice
  and the second reads as a defect.
- **`same_pull()` compares the pull, not the labels.** During a replay
  boss share, duration and outcome change four times a second and the pull
  never does. That distinction is what lets the page tell a perspective
  change from a pull change.

## The deep links, and the one entry point

`RaidLink` (in `gui/navigation.py`, next to `PageId`) carries view, report
code, fight id, player and second. **What it leaves empty stays
untouched** — that is what makes `RaidLink(view=…)` mean "same fight,
different look". `RaidCenterPage.open(link)` resolves it in this order,
and the order is the statement: pull → character → view → second.
Otherwise the view would briefly show the old pull under the new
character.

| From | Action | Becomes |
|---|---|---|
| Übersicht, *Pull ansehen* | `openRaidCenter` | `RaidLink(ANALYSIS, report, fight)` |
| Übersicht, *Daraus lernen* | `openRaidCenter` | `RaidLink(LEARN, report, fight)` |
| Analyse, click on a row | `playerRequested` | character + `LEARN`, pull kept |
| Lernen, *Moment mm:ss* | `momentRequested` | replay seek + `LIVE` |
| Lernen, *Zahlen dazu* | `viewRequested` | `ANALYSIS`, pull kept |
| Lernen, empty state | `viewRequested` | `SOURCE` |
| Header, source chip | `sourceRequested` | `SOURCE` |
| Quelle, a pull finishes loading | `archiveChanged` | `ANALYSIS` (see below) |

**Picking a pull switches to the analysis by itself** — the step that was
missing through 3.6.0, where the Archive page selected and then wrote "the
numbers appear in WeintTV" beside it (true, and still a manual page
change). Three rules keep that from becoming a nuisance: it only fires
from `Quelle` (someone reloading a pull while sitting in the analysis
wants to stay there), only for a *different* pull (`same_pull()` —
`archiveChanged` arrives several times per load), and never while the
fetch is still running.

`MainWindow.open_raid_center(link)` is the single entry point, wired
duck-typed from a page's `openRaidCenter` signal.
`open_academy_for(name)` survives as a thin wrapper because
`playerRequested` can hang off any page.

## What each view is, and what it no longer carries

None of the four has a header, a source strip, an archive picker, a replay
bar, a loading card or a tab bar of its own. All of that stands once,
above, and survives a perspective change.

- **`live_view.py`** — the old WeintTV *Live* tab. `LiveHeader(titles=False)`:
  boss name, zone/difficulty and the pull chip are hidden because the
  context header already carries them (two boss names above each other was
  the loudest duplication of the old layout, and the two could briefly
  contradict each other — one came from the snapshot, the other from the
  archive selection). The **hidden 1.7 branch** (a boss card plus four
  metric tiles, all `setVisible(False)`, which `_apply_live()` kept
  labelling) is gone.
- **`analysis_view.py`** — the old WeintTV *Analyse* tab. The player filter
  stays a **display filter**; it does not say who "I" am. What changed is
  the other direction: a click on a row reports the player to the Raid
  Center, which sets the context character and switches to *Lernen*.
- **`learn_view.py`** — the Academy, as **one column** instead of three
  tabs. Order follows the question: biggest weaknesses → all six ratings →
  the numbers behind them → the training plan → progress and curve →
  the catalog (configuration, hence last). The rating logic is untouched:
  profile and plan still come finished from `AcademyService`.
- **`source_view.py`** — the Archive plus WeintTV's *Verlauf*. It resolves
  the one naming trap in this app: "Verlauf" used to mean both "this
  session's pulls" (WeintTV) and nothing else there, while "a past report"
  was called "Archiv" elsewhere. Both now stand under each other, named
  *Raidabende* and *Diese Sitzung*.

## `FocusCard`: what the Academy was missing

`gui/widgets/academy/focus_card.py`. The old Academy answered "which
Academy page do I want" first; the answer to *what should I improve* lay
scattered across a highlighted rating tile, its small print, a lesson card
one tab away, and a button on that card. The focus card joins the four
into **one row per weakness**: area, stars, reason, lesson — and the two
ways one wants from there (the lesson, or the moment in the fight).

Three rules: only *rated* areas are weaknesses (`profile.weakest` runs
through `rated`, so `stars == 0` — "no data" — never tops the list); the
three rows are labelled, not rebuilt (this card runs at 4 Hz during a
replay); and a button that hits nothing is not shown (the replay jump only
with `at_seconds >= 0`, the lesson only with an open plan item for that
area).

## Two behaviours that were changed on purpose

- **`RaidDataService.ensure_reports()`** loads the report list *without*
  touching the mode. `ArchiveBrowser.__init__()` used to call
  `enter_archive_mode()`, which was right while the list lived in a dialog
  someone opened deliberately. As a perspective one click from *Live*,
  merely looking at which evenings exist must not stop the live feed (the
  live poll discards its results as soon as `browsing` holds). The two
  selection steps still set the mode themselves.
- **A disabled module costs one perspective, not the area.** The two
  switches in *Einstellungen · Module* used to empty a whole nav entry.
  `VIEW_MODULES` maps a view to its setting; with the Academy off, Live,
  Analyse and Quelle are unchanged and *Lernen* says where to turn it back
  on. A disabled view is not evaluated either (`_draw()` checks) — a module
  that keeps computing costs what switching it off was meant to save.

## Responsiveness (§14)

The page is `scroll=False` and **each view scrolls for itself** — a scroll
area around the *page* would take the context header along on the first
scroll, giving up the one thing this is about. `SourceView` gets none: its
list already scrolls in two columns, and a scroll area around that is a
wheel inside a wheel.

The header lays identity and controls out in a `QGridLayout`; below
`BREAKPOINT_SINGLE_COLUMN` the controls move under the identity
(`on_layout_changed`) — **re-parented, not rebuilt**, or the combo box
would lose its selection on every drag of the window edge. Side by side
they need roughly 900 px, and the controls are the half that gets clipped.
`tests/test_raid_center.py` checks 1440×900, 1366×768, 1280×720 and the
minimum size against the header's own `minimumSizeHint()`.

## Where the rest is documented

- `archive-and-replay.md` — archive mode, the browser, the replay clock.
- `weinttv-academy.md` — the snapshot contract, the evaluator, the
  progression curve, "who am I".
- `overview-page.md` — the last pull and its focus on the Overview.
- `../architecture/navigation.md` — `PageId`, `RaidView`, `RaidLink`, the
  page lifecycle.
