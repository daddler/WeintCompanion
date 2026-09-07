# The Overview page: greeting, raid schedule, roster, last pull

## The next raid on the Overview

The countdown chip used to read "KEIN TERMIN BEKANNT" permanently — the
app only ever received two opaque `WCIMPORT` strings via
`/companion/raid-roster`, which needs the raidlead role. `GET
/companion/raid-schedule` answers separately for **any** linked user,
carrying the appointment and sign-up counts but deliberately no names.
Full wire contract: `../raid-schedule-bridge.md`.

`core/raid_schedule.py` is the pure half (parse, compute, label; no Qt,
no `httpx`), `core/raid_schedule_sync.py` the HTTP half, caching under
`Paths.cache()` so a start without a reachable bot still shows the last
known date. Three rules: a missing date stays missing; the **offset comes
from the bot** in `starts_at` (countdown computed against the local clock,
not a guessed timezone); "zugesagt" counts `active` only, with
"vielleicht"/"Ersatzbank" named beside it.

**Fetching it is not showing it, and the interval belongs to the
sign-ups rather than the date.** `process()` returns whether the answer
changed; `_run_sync_worker()` collects that (with `UpdateWatch`'s) into
one `dirty` flag → `state_changed` once at the end.
`refresh_interval(schedule)` (pure) answers 60s from `SOON_MINUTES`
before the pull until `is_running()` stops being true, 300s otherwise —
sign-ups change by the minute on raid day, exactly when someone looks.
The comparison is against the **whole** frozen `RaidSchedule`, so a
closed sign-up, changed composition, changed raid size or a second
parallel raid all reach the screen. The log line stays on the
*appointment* only (`_appointment_keys()`), or raid evening would log
"Raidtermin übernommen" once per sign-up.

**The bot's base URL is overridable** (`resolve_bot_base_url()`:
`WEINTCODEX_BOT_URL` env → `bot_url.txt` in config dir → built-in
default; an unusable value is ignored, not adopted) because the hosting
platform writes the machine name into the hostname, and a forced host
move otherwise costs a release everyone must install first before the
bot is reachable at all. It does not use `Paths.config()` (that creates
the directory; a module import must not). **Settings → Discord has a
field for it** (`write_bot_url_override()` refuses an unusable address)
— the override used to be readable but not settable, so the one escape
hatch for a broken address required creating a file by hand in a
directory nobody knows, at the exact moment the app can't tell you where
that directory is. `core/net_errors.py` (pure) distinguishes a DNS
resolution failure from a refused connection with different sentences —
"the bot isn't running" vs. "this address doesn't exist any more" send
someone to different next steps.

## The greeting header

Until 2.0.7 the head was two fixed strings about the *installation*, the
same mistake the old dashboard had one storey up: the spot everyone reads
first said something already known, identically for every user at every
hour. `core/greeting.py` (pure) replaces it — daypart + name in the
eyebrow, next raid in the title. Five rules: **the name is never
guessed** (from `academy_ingame_character`, then Discord username, then
"-" for unknown — deliberately **not** `academy_player_name`, the
Academy's own possibly-stale selection); **days are calendar days**
(`days_until()` subtracts dates — 23:00 the night before is *morgen*
though 21 hours away), and beyond `MENTION_DAYS` (6) the head says
nothing; **the title is one line, cut off at `WINDOW_MIN` (960px)**, so a
pending update only rides along within two days of the raid; **the raid
outranks the update in the title** (the update card sits right beneath
and already names both channels); **the minute tick redraws it** so
"Morgen ist Raid" becomes "Heute" at midnight.

**"Erneut prüfen" also sits on the Overview**, next to the countdown,
running the same `refresh_update_status()` as *Addon & Updates* in a
short-lived thread — drops both release caches first, since the 15-minute
background cache is wrong for a button someone just clicked.

## The roster strip and composition

**"21 von 25" is a number, not the answer** — the question people open
Discord for is *who* is missing. `days[].roster` carries role and class
per sign-up, never a name (both already visible as symbols in the public
sign-up post). Three fallbacks in the same "never guess" spirit: without
`roster`, **one** strip labelled "ZUGESAGT" instead of three estimated
ones; without `composition`, the sentence stops at "Vier offene Plätze"
without claiming which roles; what's left after per-role gaps is "frei
wählbar". `gui/widgets/roster_strip.py` paints the whole strip in one
`paintEvent` (25 slots as 25 widgets would rebuild 25 layout objects on
every sign-up) and reads the accent while painting; a row is never
narrower than its own caption. `normalize_class()` understands the German
class spelling as a third route (alongside English display name and
`UnitClass()` token) since the bot's sign-ups are stored in German.
`tests/test_roster_strip.py` renders the strip and checks actual pixel
colours — this defect was only ever visible as a picture.

**The card shows every upcoming day**, not just the next one (Wed *and*
Thu are two separate sign-ups). `RaidSchedule.upcoming_days()` (pure) is
the single answer; `next_day()` is its first element. `CYCLE_DAYS` cuts
anything more than five days out, distinguishing "the other day of this
raid" from "a day that already happened" (the bot dates each weekday as
its *next* occurrence, so on Thursday the Wednesday in the same response
already sits a week ahead).

**Am I signed up?** `days[].me` answers per-day (Wed and Thu are separate
answers) from the Discord id inside the Companion token — a statement
about the asker only. `absent` and `none` (never answered) are kept
apart: only the missing sign-up (`none`) warns; a cancellation is
neutral. A missing field says nothing at all (no chip), never
"NICHT ANGEMELDET" for an older bot's silence.

## Multiple raids at once (since Companion 2.0.11)

The response shape didn't change for this — every top-level field still
describes the soonest raid, the rest arrive as `others` (same fields
minus `status`). `_parse_others()` reruns each entry through
`parse_schedule()` rather than rebuilding it. `others_text()` renders the
one line the Overview shows for a parallel raid.

## "Dein letzter Pull" survives a restart

`RaidDataService.history()` only fills with pulls completed **in this
session** — the morning after a raid it said "Noch kein Pull", a wrong
statement, not caution. `core/last_pull.py` (pure) + `core/last_pull_sync.py`
(HTTP) add the newest WarcraftLogs report with a boss fight, every 20
minutes, cached under `Paths.cache()`. The **session wins** over the
archive; the **fight list is enough** (no rating estimated — the card
says outright an archived pull carries none); the trend line holds only
pulls of the **same** boss; `time.monotonic()` uses `None` for "never
fetched" (a raw `0.0` would suppress the first fetch on a machine that
just booted).

## The bot's database is not the authority on whether a raid exists

Delete the sign-up message by hand instead of through "Raid löschen" and
the bot's record survives — the endpoint therefore checks Discord
presence first before answering (`locate_signup()`/
`SIGNUP_PRESENCE_SECONDS` on the bot side, full detail:
`../../../WeintCodex-Bot/docs/systems/raid-persistence.md`). The doubtful
case counts as *present* — a briefly unreachable API must not hide a
running raid.

## Discord deep-links

**A Discord link goes to the Discord app first, the browser second.**
`open_url()` takes an optional `app_url`
(`backend_config.app_url()` rewrites `https://discord.com/channels/…` to
`discord://-/channels/…`) and tries it before the browser — otherwise the
button lands in a second, usually logged-out browser view while the app
sits open next to it.

**The system opener's exit code is not the answer to "is there a program
for this scheme?" — on Linux.** `xdg-open` hands an unregistered
`discord:` scheme to the **default browser** and still reports 0, which
then mangles it into `http://discord//-/channels/…` — a link that exists
nowhere. `core/discord_app.py` asks *before* launching: reads the
registered handler's `.desktop` file and checks its **`Exec`** line names
a Discord client (the file *name* proves nothing — Firefox writes
`userapp-Discord-XXXX.desktop` with Firefox as Exec); otherwise locates
the app directly (PATH binary, Flatpak, known `.desktop` entries, an
AppImage in the usual folders including the one this AppImage started
from). Found nothing → `False`, browser gets the **https** address. Launch
is `Popen(start_new_session=True)`, never `run()` (Discord is a window,
not a command).

**Opening a URL always goes through `core/browser.py`**, never a bare
`webbrowser.open()` — in an AppImage/PyInstaller bundle the browser
inherits our own `LD_LIBRARY_PATH` and dies with a symbol lookup error;
`Runtime.clean_environ()` exists for exactly that. A rule followed at two
of three call sites is a reminder, not a rule — hence the function.
`roster_target()` decides where the "Aufstellung im Discord" button goes
(pure, no Qt/`httpx`): a guild named by the access profile wins, then the
project's own guild, then Settings → Discord if nothing is linked.
