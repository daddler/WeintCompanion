# Navigation: one registry, never raw indices

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
start for pages the user mostly never opens; WeintTV and the Academy
dominate it because they deliberately pre-create their list and table
rows so later per-second redraws stay flicker-free (right decision, wrong
moment). `_ensure_page()` is consequently the single place a page comes
into existence: named attribute (`self.overview`, `self.settings`, …),
scroll wrapper, and the duck-typed cross-page signals (`pageRequested`,
`playerRequested`, `openSettingsSection`) are all wired there. Anything
that reaches for a page directly — `open_settings_section()`,
`open_academy_for()` — must go through it rather than through the
attribute, which may not exist yet.

`MainWindow.change_page()` calls three duck-typed hooks on a page if
present: `on_leave()` on the outgoing page, then `on_enter()` and
`refresh()` on the incoming one. WeintTV and the Academy use
`on_enter`/`on_leave` to subscribe to and release the raid data feed, so
nothing polls while its page is hidden.

## `PageSpec` also carries duck-typed cross-page wiring

`set_update_runner()`, `pageRequested`, `playerRequested`,
`openSettingsSection` are all checked for with `getattr`/`hasattr` rather
than a shared base class, and wired exactly once in `_ensure_page()` —
never at the attribute-access site. This is why `open_settings_section()`
and `open_academy_for()` must call through `_ensure_page()` rather than
touching `self.settings`/`self.academy` directly: the attribute may not
exist yet if the page was never opened.

## A page's `refresh()` may only draw, never fetch

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

The same rule shows up per-page: `ArchivePicker` must not rebuild its
combo boxes unconditionally on every `archiveChanged` (an open dropdown
would snap shut four times a second during a replay — see
`../systems/archive-and-replay.md`), and `gui/pages/sim.py`'s `read_export()`
runs only in `on_enter()`, never in `refresh()`, because reading a file on
every redraw is the same class of cost as a network call in a click
handler.
