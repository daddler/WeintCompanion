# Gear: "Meine Charaktere" and "Vorbereitung"

Both pages were empty through 2.0.0, and that was honest: the app knew
*nothing* about gear. WeintCodex 1.3.3.1 supplies the measurement as
`character_sheet`, a local message (full wire contract:
`../character-sheet-bridge.md`, dispatched by `core/character_sheet_sync.py`,
never sent to the bot). Four things worth knowing before touching it:

- **The addon judges, the Companion draws** — exactly the reverse of
  WeintTV/Academy, for the same reason (two evaluations of one fact
  drift apart).
- **The addon reports one character, `CharacterStore` builds the list.**
  `character_sheet` is a `STATE_MESSAGE` (at most one queued, always the
  logged-in character). The twink roster across characters only exists on
  this side, in `characters.json` under `Paths.config()`. A newer report
  **replaces** an entry rather than merging — a field the new report no
  longer carries describes a state that no longer exists.
- **`None` is not zero, in three places:** `readiness()` returns `None`
  when nothing was checked; `bis is None` means "no BiS list maintained
  for this spec"; a slot status of `-` means "this slot has no such
  thing". **Open BiS slots deliberately do not count toward the ring** —
  they hang on loot luck, not preparation.
- **Only high-level characters are listed** — both pages and the
  Overview tile read `CharacterStore.characters()`, dropping everything
  below `min_level()` (90, overridable via `characters_min_level`). Hidden
  is not deleted (`all_characters()` still has them); the footer names
  how many are hidden and why; a **missing** level counts as high (0
  means "not reported", reading it as a twink would turn a data gap into
  a finding).
- **The version gate needed a third digit.** `companionVersion` ≥ 2.0.1
  is required because 2.0.0 was already shipped and doesn't know the
  type — `CompanionAtLeast(2, 0)` would have included exactly the version
  that breaks.

The Overview's `PreparationCard.apply()` reads the same
`CharacterStore.preparation_summary()`, so the tile and the page can't
disagree.

**"Meine Charaktere" carries a portrait, and it is the class.** The
addon's character page opens with a 3D `PlayerModel` that has no desktop
equivalent (client art lives in CASC, and `character_sheet` carries
neither race nor gender). `gui/widgets/class_avatar.py` draws the class
emblem in class colour instead, at the same place in the card as the
portrait in the game. The eleven emblems under
`resources/icons/class_*.svg` are **own drawings** (a copy of Blizzard's
would be foreign material in the installer); an unknown class gets the
neutral `charaktere` glyph, never a guessed emblem (`class_icon()`
returns `None`, same line as `stars == 0`). `tests/test_class_avatar.py`
renders every emblem and counts opaque pixels — a broken/missing SVG
makes `QSvgRenderer.isValid()` `False`, and `tinted_pixmap()` then
answers with a fully transparent pixmap: no exception, no log line, just
an empty tile.

## Who is behind a Discord account? (Charakterzuordnung page)

Companion-side of the Bot's `character_links.py`. **The bot decides, this
page only shows.** Which name wins when a report and a manual entry
disagree is decided entirely on the bot side (full contract:
`../character-links-and-admin-bridge.md`); `core/character_links.py` is
the pure half here, `core/character_links_client.py` the HTTP half.

- **Sperren, nicht verstecken.** A 403 (no raidlead role) reaches
  `Overview.forbidden` and becomes an explanation rather than making the
  page vanish — the same *lock, don't hide* rule as `core/access.lua` in
  the addon.
- **"0 offen" is never claimed where nothing was counted**
  (`summary_text()`).
- **After a write, the whole state is refetched** — the bot decides
  precedence, a locally patched row could show something the export
  wouldn't actually use.
- **Every fetch runs in a short-lived thread**, signalling back via
  `loaded`.
- **Which raid is being edited is a choice, not the bot's default.**
  Parallel sign-ups are allowed in Discord (a 25 next to a 10), and the
  endpoint answers about the *next* one unless `?raid=<id>` names one —
  so with two open raids the older one was simply unreachable from this
  page. The picker in the header is filled from `raid_choices()`
  (`core/raid_schedule.py`) over the schedule `RaidScheduleSync` already
  holds; there is no second enumeration of running raids and no second
  fetch. Three rules: a raid **without** an id is dropped rather than
  listed (an entry that loads something else when clicked is worse than
  a missing one); with no choice made, **no** `raid` parameter is sent
  (a `0` would be a selection that matches nothing); and the raid that
  the bot *answered* about is named in its own line above the summary —
  also when only one raid runs and the picker stays hidden. Contract
  side: `../raid-schedule-bridge.md` (`raid_ids`/`others`, `?raid=`).
