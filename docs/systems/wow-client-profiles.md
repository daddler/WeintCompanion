# Game versions: switching the client

*Which* World of Warcraft this app serves is a table entry
(`core/wow_clients.py`), not an assumption spread across the code. This
page explains what is in that table, what reads it, and — the point of
the whole thing — **what exactly has to change when Forever ships.**

## Why this exists

Until 4.0 "WoW" meant Mists of Pandaria Classic, and the folder name
`_classic_` was written into six places: the folder check, the disk
search, the config key, three labels. A game version was not an object
in this app; it was a premise.

*World of Warcraft: Forever* was announced at BlizzCon, MoP Classic will
die out, and the switch has to be a **data change, not a rebuild**.
4.1 is the preparation: everything that differs between two game
versions is now a field on one record.

## The table

`core/wow_clients.py` holds one `WowClient` per game version:

| Field | Meaning |
|---|---|
| `id` | Key in `config.json` (`"mop_classic"`, `"forever"`) |
| `name` / `short_name` | Headings and dialogs / status lines |
| `folder_names` | Installation folder under the Battle.net root. **Empty means "not known yet"** |
| `max_level` | Level cap, or `None` while unknown |
| `released` | Offered during setup? |
| `hint` | One line shown under the picker |
| `markers` | What identifies an installation (default: `Interface/`, `Interface/AddOns/`, `WTF/`) |

`FOREIGN_FLAVOR_FOLDERS` lists every folder name Blizzard hands out to a
game version (`_retail_`, `_classic_`, `_classic_era_`, PTR/beta
variants). It is irrelevant for a client whose own folder name is known,
and it is the difference between "some installation" and "the right one"
for a client whose name is not.

## Two unknowns about Forever, deliberately left unknown

Nobody outside Blizzard knows what Forever's install folder is called or
where its level cap sits. The table says so rather than guessing:

- **`folder_names=()`** switches the folder check from "find this name"
  to "find the one folder carrying the markers, and exclude any folder
  belonging to another game version."
- **`max_level=None`** means *unknown*, not *none*.
  `character_store.default_min_level()` answers `1` for it: while the
  cap is unknown, no character disappears from "Meine Charaktere"
  because of an invented number. Same line as `stars == 0` and
  `at == -1` — a gap in the data never becomes a finding.

## Resolving a folder

`core/wow_folder.py`'s `check_client_folder()` returns a `FolderCheck`
(`path` plus a German `reason`, same shape as `CombatLogLocation`), in
this order:

1. The chosen folder itself carries the markers → it is the one.
2. A known `folder_names` entry directly below it — most users pick the
   `World of Warcraft` root, not the subfolder.
3. **Exactly one** subfolder carrying the markers and not named after
   another game version.

Step 3 is what carries Forever before its folder name is known. Several
candidates are **not guessed between**: a wrong guess would install the
addon into a copy of the game that is never launched, and nothing about
that failure would be visible — so the reason says "pick the subfolder
yourself" instead.

`addon/finder.py` (the automatic search at first start) follows the same
split: exact name match for a known client, markers-only for an unknown
one, foreign flavor folders skipped and never descended into. That
search is convenience; the manual pick is the reliable answer.

## One path per game version

`config.json` carries `wow_client` (the active id) and `wow_paths`
(`{id: path}`). Two versions, two paths — switching there and back
forgets nothing, which is the whole reason the switch is a toggle and
not a second folder button.

`classic_path` stays in the file as the pre-4.1 spelling. It is read
once on load (migrating into `wow_paths["mop_classic"]`) and afterwards
mirrors *only* MoP Classic's path, so a user who rolls back to an older
Companion still finds their folder — and never finds another game
version's path under a key that claims to be Classic.

`Config.set_wow_client()` also carries `characters_min_level` along
**when it was never a deliberate choice**: every pre-4.1 config carries
`90` from the defaults backfill, which is MoP's cap, and would silently
become the wrong number under Forever. A value equal to the old client's
cap resets to `0` ("use the version's cap"); a user's own `85` stays
`85`.

## What reads the client

| Reads | For |
|---|---|
| `core/wow_folder.py` | Which folder is valid |
| `addon/finder.py` | What to search for |
| `core/config.py` | Active id, per-version paths, level-cap migration |
| `core/companion_manager.py` | `detect_wow()`; a version change invalidates the sync markers exactly like a path change |
| `core/character_store.py` | Default minimum level |
| `gui/pages/settings_sections/wow_client.py` | The picker itself |
| `gui/dialogs/setup_wizard.py` | Step 1 — asks for the version **only** when more than one is released |
| `gui/pages/connections.py`, `.../about.py` | Labels |

## When Forever ships: the checklist

**In this table** (`core/wow_clients.py`) — this is the part the
preparation was for:

1. `folder_names=("_forever_",)` — whatever Blizzard calls it.
2. `max_level=<cap>`.
3. `released=True` — setup step 1 starts asking for the version by
   itself; no UI change needed.
4. `DEFAULT_CLIENT_ID = FOREVER.id` once MoP is gone, and drop
   `MOP_CLASSIC` from `CLIENTS` when it should no longer be selectable.

**Outside this table** — the client switch does *not* make the app
Forever-ready, and pretending otherwise would be the real trap. Each of
these hangs on what is *played*, not on where it is installed, and none
of them can be written before the game exists:

- `analyzer/data/encounters.py` — raid encounters, still Siege of
  Orgrimmar.
- `analyzer/data/specs.py`, `gui/theme/wow_colors.py` — classes and
  specs.
- `analyzer/academy/lessons/` — the lesson catalog references MoP
  encounters.
- `core/qelive.py`, `core/wowsims_link.py`, `core/wowsims_export.py` —
  both sim sites address MoP (`wowsims.com/mop`, QE Live "Classic");
  neither will keep that address.
- `analyzer/providers/warcraftlogs_payload.py` — zone/encounter ids.
- The addon itself (`../WeintCodex`) needs a new `## Interface:` in its
  `.toc`, which is the sibling repo's business.

These are not prepared here on purpose: a placeholder for a raid tier
nobody has seen would be a guess pretending to be a plan.
