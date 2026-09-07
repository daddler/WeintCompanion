# Einführung und "What's new" popup

## Der Ablauf des Popups

`gui/dialogs/whats_new_dialog.py`'s `show_whats_new_if_needed()` runs
once from `MainWindow.showEvent` (**not** `QTimer.singleShot(0, …)` in
`__init__` — see `../architecture/qt-pitfalls.md`, "The splash must
repaint itself"), and its content is local/bundled rather than
network-fetched. Three outcomes, in order:

1. `onboarding_tour_edition` is below `TOUR_EDITION` — the full
   `TOUR_PAGES` walkthrough, with a *Später* button. Covers a fresh
   install **and** every long-time user whose last tour is out of date.
2. Otherwise `onboarding_seen_version` already equals `core.version.VERSION`
   — nothing.
3. Otherwise the changelog entries between the two versions, read via
   `core/changelog_reader.py` (see `update-system.md`).

Either way the dialog writes `onboarding_seen_version` on close; the tour
additionally writes `onboarding_tour_edition` when **shown** (not when
finished — vermerkt wird beim Zeigen, nicht beim Durchklicken, sonst käme
sie bei jedem Start wieder). The "don't show again" checkbox sets
`whats_new_enabled = False`. Both reversible via the *Einführung* row in
Settings → Allgemein.

## Since 3.0: a complete, chaptered tour

Reason: the tour dated from 1.0 (five pages); by 2.8 WeintTV, Academy,
Archive+Replay, Meine Charaktere, Vorbereitung, Simmen, WeakAuras and
Charakterzuordnung had all shipped and the tour mentioned none of them.
Six things not taste:

- **`TOUR_EDITION` (`onboarding_tour_edition`) stands NEXT TO
  `onboarding_seen_version`, not inside it** — raising it re-shows the
  tour to everyone, including long-time users; merged with the version
  field, *every* version would trigger the full tour.
- **`TourPage` carries the icon *name*, not a rendered path** — the page
  tints it itself via `tinted_pixmap()`, read at build time as the one
  deliberate exception to "read the accent in `paintEvent`" (the dialog is
  modal and can't experience an accent switch). A missing SVG produces a
  silently transparent image — `tests/test_tour.py` counts opaque pixels,
  same check as `test_class_avatar.py`.
  `tests/test_tour.py` also asserts every page label from
  `build_page_specs()` appears in the tour text, so a new page shows up
  as a test failure rather than a silent omission.
- **Colours come from `gui/theme/tokens.py`, not `gui/theme/colors.py`**
  — exactly the bug 3.0 fixed elsewhere: the progress dots read the
  frozen `Colors.PRIMARY` and stayed amber under Arcane/Jade.
  See `../architecture/theming.md`.
- **Body text is left-aligned**, not centered (fine for two sentences,
  unreadable for a five-line paragraph).
- **`_render_emphasis()` escapes before formatting** (Rich Text — an
  unescaped `<` would eat the rest of the page). Exactly two markers:
  `**bold**` for emphasis, `*italic*` for something the app literally
  calls that way (page/button names) — same split as the addon's
  Bernstein/Weiss convention. Unpaired stars never leave an open tag.
- **The stack height matches the shown page, not the tallest**
  (`_PageStack`) — `QStackedWidget` reports the maximum across all pages
  by default, which inside a `QScrollArea` gave every short page a
  170px-tall scrollbar leading nowhere. Height is **set** on page turn,
  not measured (`sizeHint()`/`QSizePolicy.Ignored` don't survive the
  `QStackedLayout`).
- **The *Später* button asks the stored intent, not its own state** — it
  is hidden on the last page (where the main button reads "Los geht's");
  asking itself would make it not reappear on paging back.

Text follows the same player-facing style rules as the addon's patch
notes: `../../../WeintCodex/docs/development/releases.md`.
