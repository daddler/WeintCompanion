# WeintTV and WeintAcademy: one service, one snapshot

Both modules read the **same** `RaidSnapshot` (`analyzer/models.py`) — an
immutable, complete picture of one moment (boss health, pull timer,
deaths, battle-res, heroism, DPS/HPS rankings, tanks, cooldowns,
consumables, mechanic errors, warnings). No widget ever sees a combat-log
event, and no page computes a metric. That is what structurally prevents
WeintTV and the Academy from growing two divergent evaluations.

Uptimes come in three lists, not two: `dot_uptimes`, `hot_uptimes` and
`buff_uptimes` (effects on the player themselves — `UPTIME_BUFF`). The
third exists because a tank's active mitigation is neither: filed under
HoTs it would only ever be read for healers, and left out entirely it
took the whole tank contribution with it. `uptimes_of(name, kind)` is the
single accessor, `players[].buffs[]` the (optional) bridge field, and
WeintTV shows it as its own card next to the DoT and HoT cards.

The one thing the snapshot carries *without* evaluating it is `events:
tuple[CombatEvent, ...]` — phase changes, announced boss casts, adds.
`CombatEvent.kind` is a free string on purpose: an unknown kind must land
in WeintTV's event list unchanged rather than be dropped, so a new kind
from the bot needs no Companion release. Everything the analyzer actually
*reasons about* (deaths, resurrects, interrupts, dispels, mechanic
issues) keeps its own typed field, because the Academy needs those
separated — a dispel and a death train different areas. They are merged
onto one time axis only in `WeintTvPage._event_rows()`, i.e. in the
presentation. `analyzer/replay/models.TimelineEvent` is an alias of
`CombatEvent`, not a second class.

## Finding your way around: the guide and the source strip (3.5.0)

Reported as: *"Viele wissen nicht, inwieweit man alles überhaupt
bedienen muss/kann und wo man was findet."* Three nav entries share one
data source, one snapshot and one archive selection — invisibly. Someone
who doesn't know that sees three pages, two of them saying "keine
Daten", with no clue why.

- **`core/analysis_guide.py`** holds the words (Qt-free, like
  `analysis_gap.py`): an intro plus four sections, each answering the
  *same three questions* — what it's for, what you do there, what it
  needs. `gui/dialogs/guide_dialog.py` draws them; a *Was ist das hier?*
  button on all three pages opens it. The onboarding tour explains each
  area once, at first start — the right place for "what exists", the
  wrong one for "what do I do now", because a tour can't be found again
  when the question comes up.
- **`gui/widgets/tv/source_strip.py`** is the one line on all three
  pages: which source is set, what that means, a picker to change it,
  and the way into the guide. It reads `active_source()` (what *runs*,
  not what is configured — an unknown key falls back to the mock in
  `_create_provider()`), and warns in `STATE["warn"]` when
  `is_demo_source()` says the numbers belong to nobody. **A demo source
  being mistaken for the reader's own raid was the single most common
  confusion in this area.**
- **Switching goes through `RaidDataService.set_source()`** — the one
  place that stores, tears the old provider down and logs. Four copies
  of that sequence (Settings plus three pages) would clean up
  differently after the first change. It emits `sourceChanged` so a
  switch made in Settings doesn't leave a stale strip behind.
- **WeintTV's `source_chip` is gone.** It answered "where do the numbers
  come from" a second time and from a different source (the snapshot's
  label rather than the setting), so the two contradicted each other
  briefly while switching. `feed_chip` stays — it answers the other
  question, whether data is flowing at all.
- **Every tab carries one explaining sentence** (`TAB_HINTS` in both
  pages). *Verlauf* needs its own for a second reason: the word means
  two different things in this app (this session's pulls here, any past
  report in the Archiv).
- **The default source is `warcraftlogs` since 3.5.0**, with a one-time
  migration in `core/config.py` (`raid_data_source_migrated`) that moves
  an existing `mock` over exactly once. The simulation was the safe
  fallback — it needs no setup at all — and that was the problem: a
  first-time user saw a complete pull with 25 names that don't exist.
  Without a linked account there is now an honest "keine Daten", and the
  simulation is one click away in the strip.

## `RaidDataService`: the single place that picks and polls a data source

`core/raid_data_service.py`. Key points:
- Sources are registered in `PROVIDER_FACTORIES` keyed by the
  `raid_data_source` config value, alongside `SOURCE_LABELS`/
  `SOURCE_DESCRIPTIONS` for the picker in Settings → Module. A new source
  is one entry plus a class implementing `analyzer/providers/base.py`'s
  `RaidDataProvider`. An unknown key logs a warning and falls back to the
  mock.
- `attach()`/`detach()` are reference-counted; the `RaidDataThread` (a
  plain `threading.Thread`) runs only while at least one page is
  subscribed, on its own ~1s cadence — deliberately *not* on
  `CompanionManager`'s 5-second sync timer.
- Results reach the GUI through the `snapshotChanged = Signal(object)`
  cross-thread signal.
- It also owns the pull history (`PullSummary`).

`analyzer/providers/mock.py` produces a fully deterministic 25-player pull
from elapsed time — no randomness. Its roster and schedules live in
`mock_schedule.py`, which *derives* every player's uptimes and cooldowns
from their spec via `class_abilities` — hand-written rows (specific
stories: Krallenwut leaves his Berserk unused) always win, derived ones
fill the rest, deliberately carrying the **German** name while
hand-written ones stay English, so the simulation exercises both paths
through `spec_reference` and a broken match shows up as a duplicated row.

## The Academy: `analyzer/academy/`

`evaluator.py` turns a snapshot into a `PlayerProfile` (star ratings for
**six** areas — Rotation/Movement/Cooldowns/Mechaniken/Überleben/Leistung)
and a `TrainingPlan`, using the `MECHANIC_*` category on each
`MechanicIssue` to attribute errors to a trainable area. Ratings are
**relative to the player's own role** — for damage *taken* especially (a
tank always takes the most, which is the job), so Überleben rates the
avoidable **share** against same-role peers, never the absolute sum.
Relative alone rewards conformity and degenerates for the only player of
a role — Überleben therefore takes the **stricter** of the relative and
an absolute rating (`ABSOLUTE_AVOIDABLE_SHARE`). `core/academy_service.py`
only handles character selection and persistence
(`academy_progress.json` in `Paths.config()` — completed lessons are user
data, not cache).

Three rules, each reversing an earlier mistake:

- **Rotation must not read the damage ranking.** The rank moved to its
  own area, `Leistung`. *Which* uptimes count is role-dependent
  (`_uptime_parts`): DoTs for damage, HoTs for healers, tank **active
  mitigation** from `buff_uptimes` — rated there and *not* under
  Überleben (which asks about the outcome), or the same incident would be
  charged twice.
- **No comparison group, no rating.** Being the only player of your role
  means the ratio is always 1.0. `Leistung`, the movement average and
  Überleben all require at least one other player of the same role with
  data, otherwise "keine Daten".
- **`stars = 0` means "no data", not "bad".** `PlayerProfile.rated`/
  `weakest` skip zero-star ratings, `_combine()` drops parts with no data
  instead of averaging them down. **Lesson results and the manual
  checkbox are never merged** — `LessonResult` is log evidence,
  `completed` is the player's own claim.

**An empty Academy has to say so, and a strich is not a zero.**
`academy_empty_text()`, `academy_empty_action()`, `next_lesson_placeholder()`
live in `gui/widgets/tv/analysis_gap.py` (shared with WeintTV so the two
pages can't describe one situation differently). The six metric tiles
under the stars: **a dash means "not delivered", never "zero"** — each
tile first asks whether the source delivered that kind of event at all.

**`_apply_overview()`/`_apply_metric_tiles()` take the snapshot as an
argument** rather than asking `service.current()` beside it — a second
source for the same answer is provably different during a replay.

`gui/widgets/tv/encounter_meta.py` says which fight is being rated —
boss, difficulty, pull, outcome, average — Qt-free like
`analysis_gap.py`. `addon/addon_payloads.py` ships the finished sentence
as `encounterText` rather than letting the addon reassemble it. Its
`outcome_text()` has **three** answers: while running, the outcome is
*open*.

## Progression: a curve across pulls, since 2.3.5

**A single pull cannot answer "am I getting better?"**
`analyzer/academy/progression.py` is the pure half, `core/academy_history.py`
the store (`academy_history.json` under `Paths.config()` — measurements
that cannot be recomputed once a WarcraftLogs report ages out are user
data, not cache). Six rules, each the `stars == 0` line in another guise:

- **Only finished pulls, from `MIN_PULL_SECONDS`.** `qualifies()`
  requires `in_combat == False` (covers live/archive/replay paths at
  once).
- **An unrated area is not a point.** `record_from_profile()` drops
  `stars == 0`.
- **One pull, one point.** `pull_key()` is `<report>#<fight>` when known,
  else `live:<day>:<boss>:<pull>` (day included — pull numbers repeat on
  the next raid night).
- **The order comes from the fight, not the click.** `sort_records()`
  orders by raid day, then fight id, then recording time.
- **Simulation and real reports never share a curve**, nor do two specs
  (`select()`).
- **Recording happens in `CompanionManager`**, not on the Academy page —
  the snapshot stream runs whenever *either* page is attached.

`evaluator.plan_order()` reads that curve too: with a `focus` (from
`progression.build_focus()`) an area with enough recorded points is judged
by its **average over the curve**; three lines it must not cross: it
changes order only, never a `SkillRating`; needs `MIN_POINTS` before a
category counts as a pattern; and the status sort (failed → unknown →
passed) still decides the visible card order.

`HistoryCard` draws two lines — overall in the accent, weakest area
dashed — and hides the second when it would cover the first.
`ProgressionChart` fixes its axis at 0…`MAX_STARS` (an auto-scaled axis
would make a 4.1→4.3 wobble look like a 1→5 climb).

## The training plan verifies itself

A `Lesson` carries declarative `LessonCheck`s ("active_percent >= 95"),
and **`analyzer/academy/checks.py` is the only place** mapping metric
names to snapshot lookups (`tests/test_lesson_catalog.py` asserts every
metric resolves). Outcomes are three-valued (`passed`/`failed`/`unknown`)
— a red cross for a missing field would simply be wrong.

The catalog is a package (`analyzer/academy/lessons/`): `generic.py`,
`roles.py`, `classes/<class>.py`, `encounters.py`, merged by
`registry.py`, which **raises on a duplicate `lesson_id`** at import.
Selection order: encounter → spec → class-wide → role → generic. Catalog
opt-out stores **exclusions, not inclusions**.

Two reference tables under `analyzer/data/` exist because the catalog is
written in one language and the data source answers in another, and both
failures were silent:

- **`specs.py`** — all 34 specs with German name, English name and role.
  Before this table no spec key ever matched WarcraftLogs' English
  spelling in production. It also derives **the role from the spec** —
  without it a missing `role` field was guessed from damage vs. healing,
  which can never yield "tank".
- **`player_abilities.py`** — German ↔ English for ability names checks
  reference. Additive by design (a missing entry costs a match, never
  invents one). `_all_names()` merges `class_abilities.translations()`
  into it.
- **`class_abilities.py`** — every spec's DoTs/HoTs/self-buffs/cooldowns
  with spell IDs, English *and* German name, target uptime, category.
  Recognised by **spell ID, English name or German name** (any one
  suffices). A diff against the bot's own catalogues found **35 spell IDs
  carrying a different German name on each side** — the structural fix is
  on the wire: the bot sends `spell_id` on every ability row, and
  `match()` reads the ID first. Two entries were plain wrong (a real
  number under the wrong ability — `31842` filed as Avenging Wrath is
  Divine Favor; `123040` filed as Shadowfiend is Mindbender, 60s not
  180s). `tests/test_class_abilities.py` asserts no spell ID is claimed
  twice.

`analyzer/analysis/spec_reference.py` — `apply_spec_reference(snapshot)`
runs at the end of every snapshot-producing path (payload mapper, mock,
replay's `snapshot_at()`), fixing three failures that all looked
identical in the UI ("Keine Angaben zu …"): wrong-language report, aura
filed in the wrong list, ability simply not reported. **The line it must
never cross is between a finding and a data gap**: a missing ability is
filled with 0% only when the source demonstrably delivers that kind of
uptime for *someone*. `reference_hint()`/`cooldown_hint()` say what
*would* be shown when the source delivers nothing of that kind. Same
restraint on `possible` for cooldowns: only `CD_PERSONAL` gets an upper
bound (an unused Shield Wall is a fight that didn't need it, not a wasted
use).

Recognised rows are also **renamed to their German name** — which
language a report arrives in is an accident of who uploaded it, and
"Rallying Cry" next to "Sammelschrei" would be the same ability twice.
`match()` takes a `prefer` argument for abilities that are both an aura
and a cooldown under one spell ID.

`analyzer/analysis/` holds derivations both the payload mapper and the
replay need: `ranking.py`, `movement.py` (the single map-units-to-metres
constant), `damage.py` (bucketing, mechanic issues, merging with the
bot's).

## Whether a hit was avoidable is a judgement, not a measurement

Lives in `analyzer/data/avoidable.py`, **not in the bot** — must be
identical for WeintTV and the Academy, changes with difficulty/tactics,
stays correctable without a bot deploy. Deliberately **three-valued** —
missing from the table is `unknown`, never `unavoidable` (treating unknown
as unavoidable would hand every boss without reference data a flawless
survival rating). Covers all fourteen Siege of Orgrimmar encounters plus
Horridon; not every ability of every boss, only the ones where the
verdict is unambiguous. Below `MIN_CLASSIFIED_SHARE` the Academy declines
to rate rather than grade the table's gaps. `merge_mechanics()` lets **the
bot win** per (player, ability) when it ships its own hand-written
`mechanics[]` rows, via an alias table **derived from the rules' own
labels** rather than hand-maintained.

## WarcraftLogs as the second real source

Read through the bot rather than directly (`/companion/warcraftlogs/live`)
— credentials off 25 player machines, one shared API quota. Three files:
`analyzer/providers/warcraftlogs_payload.py` (pure mapper, no I/O),
`analyzer/providers/warcraftlogs.py` (provider, own 15s fetch thread so
`snapshot()` never blocks the 1s poll), `core/warcraftlogs_client.py`
(HTTP half). Full wire contract: `../warcraftlogs-bridge.md`.
`RaidSnapshot.has_analysis` is the single switch the UI uses for the
whole deep-analysis block; what it does *not* say is **why** a block is
missing (no raid / no pull / source only sends sums) —
`gui/widgets/tv/analysis_gap.py` is the one place that decides which,
shared by both pages. `block_gap_text(snapshot, block)` closes the case
where the source delivers *part* of the block and not the rest (silent
when the block has rows or the deep analysis is entirely missing,
otherwise names the source and states that block specifically wasn't
delivered) — covers `movement`, `cooldown_usage`, `raid_cooldowns`,
`heal_cooldowns`.

## Who is "me"? (`analyzer/names.py` + `core/character_report_sync.py`)

Had **four independent answers** that nothing reconciled: the Academy
combo box, `config["academy_player_name"]`, `PlayerProfile.name`,
`UnitName("player")` in-game.

- **The selection never guesses.** `resolve_player_name()` returns what
  is stored, or `""`. The guess (`suggest_player_name()`) is reachable
  only through `ensure_player_name()`, which **persists** it — a guessed
  identity must never reach the wire unseen.
- **`reconcile_selection()` decides *and* stores.** Deliberately on the
  service rather than in the page, so it's testable. The original defect
  was a missing `else`: the page refilled the combo but only restored the
  selection *if* the stored name still occurred, leaving the box on
  `names[0]` while the config kept the old name.
- **The roster's spelling wins.** `match_name()` returns the *list's*
  spelling. `analyzer/names.py` holds the three comparison rules; a
  **missing realm is a wildcard, not a mismatch**. The addon carries the
  same three rules in `core/names.lua` — they must stay identical.
- **One identity per delivery.** `AddonAnalysisSync.process()` resolves
  the name **once** for `build_profile`, `build_academy_state`,
  `build_weinttv_report`, `build_plan` — see
  `../academy-and-practice-bridge.md` for the wire side. `hasActor` says
  whether the character was in the pull at all.
- **A selection change publishes immediately** (`set_player_name()` →
  `addon_analysis_sync.publish_now()`). The `getattr` guard there is
  load-bearing: `AcademyService` is constructed before `AddonAnalysisSync`.
- **The game reports who is logged in** — Codex sends `character_report`
  (never reaches the bot, handled like `academy`/`dummy_practice_session`).
  `note_ingame_character()` follows it, with one rule: **a manual pick
  beats the game report for the character it was made on, and stops
  beating it the moment the game reports a different one**
  (`academy_manual_for`).
- **The WeintTV player picker stays a display filter.** Its
  `ALL_PLAYERS` value has no Academy equivalent. Explicit path:
  `playerRequested` → `open_academy_for()` → `show_player()` →
  `note_manual_choice()`. A muted line next to the picker names the
  current Academy character.
