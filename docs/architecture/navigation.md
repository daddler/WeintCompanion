# Navigation: one registry, never raw indices

## Since 4.0: RAID is two entries, not four

`Übersicht` and `Raid Center`. WeintTV, the Academy and the Archive were
three equal nav entries onto the *same* pull — they shared a data source,
a snapshot and an archive selection invisibly, and the user had to know
which one to open when. Getting from an analysed pull to the matching
lesson meant going through the sidebar and starting over there: pick a
character, find the pull again, find the lesson.

They are now four **perspectives** of one page (`gui/pages/raid_center.py`):
`Live`, `Analyse`, `Lernen`, `Quelle`. A perspective is not a `PageId` —
that distinction is the whole point. The context header (boss, pull,
outcome, share, duration, weekday, time, character, source) sits *outside*
the view stack and therefore survives a switch; were the perspectives four
pages, the header would exist four times and would eventually say four
different things (it did: WeintTV's boss name, the Academy's
`encounter_meta()`, the Archive page's `selection_text()`).

`RaidView`/`RaidLink` live in `gui/navigation.py` next to `PageId`
because a deep link onto a pull *is* a navigation target. `RaidLink`
carries view, report code, fight id, player and second; **what it leaves
empty stays untouched**, which is what makes `RaidLink(view=…)` mean "same
fight, different look". `MainWindow.open_raid_center(link)` is the single
entry point, wired duck-typed from a page's `openRaidCenter` signal.

The pure half is `core/raid_context.py` — a **projection** over
`RaidDataService`, holding no state of its own. See
`../systems/raid-center.md`.

## One registry

Pages live in a `QStackedWidget` whose index *is* the position in the
sidebar rail. Both are built from a single source: `PageId` (an
`IntEnum`) and `build_page_specs()` in `gui/navigation.py`. `MainWindow`
iterates the specs to create the stack and hands the same list to
`NavColumn(manager, specs)`, so rail and stack cannot drift apart. Adding
a main area = one enum member + one `PageSpec`.

Never write a bare integer as a navigation target:
`pageRequested.emit(PageId.ADDON)`, not `emit(1)`. `PageId` inherits from
`int`, so it works unchanged with `Signal(int)` and `setCurrentIndex()`.
`build_page_specs()` imports the page classes *inside the function body*
— the pages import `PageId` themselves, so a module-level import would be
circular.

Pages are built **on first entry**, not at startup. The stack is filled
with one empty placeholder per spec so its index still *is* the `PageId`,
and `MainWindow._ensure_page()` swaps the placeholder for the real page
the first time it is needed — `insertWidget(index, …)` then
`removeWidget(placeholder)`, in that order, or everything after it
shifts. Building all ten up front cost about two seconds of a four-second
start for pages the user mostly never opens; the Raid Center dominates it
because its views deliberately pre-create their list and table rows so
later per-second redraws stay flicker-free (right decision, wrong
moment). `RaidCenterPage._ensure_view()` repeats the same pattern one
level down, so opening the Raid Center builds only `Live`. `_ensure_page()` is consequently the single place a page comes
into existence: named attribute (`self.overview`, `self.settings`, …),
scroll wrapper, and the duck-typed cross-page signals (`pageRequested`,
`playerRequested`, `openSettingsSection`) are all wired there. Anything
that reaches for a page directly — `open_settings_section()`,
`open_academy_for()` — must go through it rather than through the
attribute, which may not exist yet.

`MainWindow.change_page()` calls three duck-typed hooks on a page if
present: `on_leave()` on the outgoing page, then `on_enter()` and
`refresh()` on the incoming one. The Raid Center uses
`on_enter`/`on_leave` to subscribe to and release the raid data feed, so
nothing polls while its page is hidden — and it passes both hooks down to
whichever view is visible.

## `PageSpec` also carries duck-typed cross-page wiring

`set_update_runner()`, `pageRequested`, `playerRequested`,
`openSettingsSection` are all checked for with `getattr`/`hasattr` rather
than a shared base class, and wired exactly once in `_ensure_page()` —
never at the attribute-access site. This is why `open_settings_section()`
and `open_academy_for()` must call through `_ensure_page()` rather than
touching `self.settings`/`self.academy` directly: the attribute may not
exist yet if the page was never opened.

## A page's `refresh()` may only draw, never fetch

The AST check covers `gui/pages/**` *and* `gui/widgets/**` since 4.0 —
the Raid Center's context header has a `refresh()` of its own that the
page calls through, and a network round there closes the same loop one
level down.

`ConnectionsPage.refresh()` once began with a blocking
`manager.full_refresh()` — a full network round (GitHub, Discord, sync) on
the main thread, in a method that `change_page()` calls on every entry
and that the page's own constructor calls too, so the window froze
whenever "Verbindungen" was opened. Once `state_changed` was wired up (see
`../systems/update-system.md`) this became an infinite loop: the check
reported its new state, the window redrew the visible page, the page
checked again — 826 GitHub requests in a run that needs seven. The check
moved to `sync_now()` in a short-lived thread; `MainWindow._on_state_changed()`
additionally carries a re-entrancy guard, because that failure starts in
one page and takes the whole window down. `tests/test_update_visibility.py`
holds both halves: the guard, and an AST check that no page's `refresh()`
calls `full_refresh()`/`refresh_update_status()`.

The same rule shows up per-page: `ArchiveBrowser` must not rebuild its
columns unconditionally on every `archiveChanged` (the scroll position
would jump four times a second during a replay — see
`../systems/archive-and-replay.md`), and `gui/pages/sim.py`'s `read_export()`
runs only in `on_enter()`, never in `refresh()`, because reading a file on
every redraw is the same class of cost as a network call in a click
handler.
