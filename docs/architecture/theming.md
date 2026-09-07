# The 2.0 theme: one token table, one manager

`gui/theme/tokens.py` is **the only place a colour, spacing, radius or
type size exists** (the one exception is `wow_colors.py`, a domain table
like those under `analyzer/data/`). It imports no Qt at all — same reason
`analyzer/` doesn't: `tests/test_tokens.py` checks it without a running
UI. `gui/theme/stylesheet.py` is therefore a function, `build_stylesheet(theme)`,
not a constant.

`gui/theme/theme_manager.py`'s `ThemeManager` is a singleton reached
through `theme()` and initialised once via `init_theme(config)`. It owns
the three user choices — accent (three variants), density
(`comfortable`/`compact`) and reduced motion — and announces each with its
own signal (`accent_changed`, `density_changed`, `motion_changed`). All
three are set in **Settings → Erscheinungsbild**
(`gui/pages/settings_sections/appearance.py`) and, for the first run, in
the setup wizard; the swatches they share live in
`gui/widgets/appearance_picker.py`, and the German labels with them, so a
fourth accent variant cannot appear in one place and be missing in the
other. `ThemeManager.user_motion_reduced()` exists expressly for "what the
switch in Settings has to show" — the switch must show *that* and not
`motion_reduced()`, which is the OR with the system setting: with the
system forcing it, the switch would read "on" and clicking it would
change nothing visible. A line underneath says when the system is the
reason.

## Six rules, each of which was a real defect once

- **A painted widget must read the accent in `paintEvent`, never in
  `__init__`.** A colour captured at construction survives an accent
  switch and the widget keeps the old one — silently, since nothing
  errors. The ring, sparkline, stars, bars and the nav indicator all
  re-read `theme()` while painting.
- **Reading in `paintEvent` is not enough if the value comes from
  `gui/theme/colors.py`.** That module is the documented transition table
  from the old `Colors.*` names to the tokens, and its values are
  **static** — frozen at amber when it is imported. `MeterBar` read
  `Colors.PRIMARY` inside its `paintEvent` and still never changed
  colour; `HeroButton` — the app's main button, in thirteen modules —
  built its stylesheet once in `__init__` from the same table. Both are
  fixed to `theme().accent_base()`/`accent_light()`, and `HeroButton` also
  takes its text colour from the variant's `onBase` instead of a hard
  `color:white`, because jade is lighter than amber. `tests/test_accent_follows.py`
  renders each accent-bearing widget under all three variants and
  compares the images.
- **Connect to `accent_changed` in `__init__`, never inside the handler
  it triggers.** Connecting from the handler doubles the connection on
  every switch (measured 1, 2, 4, 8, 16). It never looks like a bug, only
  like the app getting slower.
- **Never connect a `lambda` to one of the three signals.** `theme()` is
  a singleton and lives as long as the process, so a `lambda _n:
  self.update()` hands it a hard reference to `self` and the widget is
  never freed again — nine widgets did this, among them `ToggleSwitch`,
  `ProgressRing`, `Sparkline` and `SegmentedControl`. If the C++ object
  *is* destroyed anyway because a parent goes away, the lambda then fires
  into it and Qt raises `RuntimeError: Internal C++ object already
  deleted` from inside a slot. A **bound method** fixes both: PySide6
  holds the receiver weakly and Qt drops the connection when it is
  destroyed. `QObject.receivers()` is no way to check this — PySide6 does
  not count it down even when the connection really is gone; `destroyed`
  is. The same trap one level in: `button.toggled.connect(lambda checked,
  b=button: …)` in `SegmentedControl` closed a cycle (control → button →
  connection → lambda → control) the garbage collector cannot see,
  because the lambda sits in the C++ connection; the handler asks
  `sender()` instead. `tests/test_theme_connections.py` holds both
  halves — every such widget must be released after its last reference is
  dropped, and no `theme().…connect(` line may contain a `lambda`.
- **A `font-size` on the `QWidget` rule overrides every `setFont()` in the
  program.** That is why the `QWidget` rule in `build_stylesheet()`
  deliberately carries no font declaration and the base font is set once
  with `QApplication.setFont()` in `apply_stylesheet()`.
- **`QFont(family, size)` sets a *point* size.** `gui/theme/fonts.py` uses
  `setPixelSize()`; the token table is in pixels. `install_fonts()`
  registers the bundled Inter and JetBrains Mono (in
  `WeintCompanion.spec`'s `datas`) — Qt's fallback still supplies glyphs
  those two lack (`●`, `▶`, `★`, `—`), so those characters are safe in UI
  strings, but nothing else about the metrics is.

Qt's stylesheet engine knows no `transition`, no `@keyframes` and no
`letter-spacing`; animation lives in `gui/theme/motion.py`
(`duration()`, `curve()`, `is_reduced()`), the shared blink in
`gui/motion/pulse_clock.py`, and letter spacing is set on the `QFont`.
`gui/layout/breakpoints.py` is Qt-free too: `resolve(width, previous)`
with 40 px of hysteresis, so a window dragged across a threshold doesn't
flicker between two layouts.

**Not every motion token has a consumer, and that is worth knowing before
you go looking for the bug.** `MOTION` in `gui/theme/motion.py` describes
thirteen movements; eight are live (`page`, `bar`, `toast_in`, `toast_out`,
`progress`, `nav`, `toggle`, `expand`, plus `pulse` through
`gui/motion/pulse_clock.py`, whose period *reads* `MOTION["pulse"]`
instead of repeating the 1000 as its own constant). Four describe things
the 2.0 UI does not have yet, aspiration rather than defect: `number` (no
value counts up anywhere), `skeleton` (`gui/widgets/skeleton.py` complete
and used by nobody; loading is said in words), `hover` (Qt's stylesheet
engine has no `transition`, so `:hover` is instant everywhere), and
`drawer` (`LayoutState.drawer` exists and is read — but only as a
*breakpoint* for the Academy's rating grid; the sliding side panel it was
named for does not exist). `expand` was the one genuinely missing: the
Overview's system row jumped from 44 to 132 px, and that row is exactly
where a background check announces itself, so the jump read as a glitch
rather than as something arriving.

**Animations must be stopped and released, not just replaced.** A
`QPropertyAnimation(…, self)` or `QVariantAnimation(self)` is a child of
its widget: reassigning the attribute drops the Python reference but the
C++ object stays. Reuse one animation per widget where the target is
fixed (`BarRow._set_fraction`), or start with `DeleteWhenStopped` and
clear the reference in the `finished` handler
(`MainWindow._animate_page`, `NavColumn._apply_collapsed`) — and stop the
previous one first, or two animations drive the same property at once.
Measured before the fix: 199 objects on a single bar row after 200
relabels.

## `setStyleSheet()` is not a setter

Qt discards the widget's cached style computation, re-parses, re-polishes
and schedules a repaint even when the string is unchanged — it does not
compare. The "build rows once, relabel later" widgets under
`gui/widgets/tv/` were re-setting a cell's stylesheet on every relabel
although only the text changes; that was ~280 calls and three quarters of
the cost of one WeintTV frame (25 ms → 3.5 ms once fixed).
`gui/theme/restyle.py`'s `restyle()` is the one place that check lives,
and per-frame `apply()` paths use it instead. The same trap in another
guise: `ToggleSwitch._animate_to_state()` restarted its animation even
when the thumb was already at the target, so the Academy's catalog ran
dozens of invisible animations per frame.
