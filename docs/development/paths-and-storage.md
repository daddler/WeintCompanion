# Paths, atomic writes, and config

`core/paths.py` centralizes all on-disk locations
(config/cache/downloads/backups/logs/reports), branching on
`platform.system()`: `~/.local/share/WeintCompanion` on Linux,
`%LOCALAPPDATA%/WeintCompanion` on Windows. Rule of thumb for new files:
anything reproducible goes under `cache()`, anything the user would be
upset to lose goes under `config()`.

## Config and auth

`core/config.py` is a flat JSON-backed settings store (`config.json` in
`Paths.config()`) with a defaults dict merged on load so new settings get
backfilled into existing installs. Discord account linking:
`core/discord_auth.py`'s `DiscordAuth.login()` runs the OAuth2 flow
(local callback server, system browser, code exchange against
`/companion/auth/exchange`), `core/discord_account.py`'s
`DiscordAccountStore` persists the identity plus a bot-issued
`companion_token`. Full auth contract (why a single 401 must not unlink,
signed tokens surviving a bot deploy): `../companion-auth.md`.

## Writing the account link must survive a hard reboot

`open(..., "w")` truncates before writing; a crash/power-cut/forced
restart in between leaves an empty file, indistinguishable by `load()`
from "never linked" (worse on Btrfs/NTFS, where an unsynced write can be
rolled back outright). `_write_atomic()` writes a sibling file, `fsync`s
it, `os.replace()`s it into place, fsyncs the directory; `save()` also
keeps `discord_account.json.bak`, `load()` falls back to it. `clear()`
removes both.

**"Is an account linked?" has exactly one answer: `is_usable()`.** Four
places once asked "is there anything stored" while seven clients require
a `companion_token` — an entry without one satisfied the first check and
not the second, and the UI claimed "Verbunden als …" while not a single
fetch ran. `DiscordAuth.parse_exchange_response()` (pure) rejects a
response without a token; `DiscordAccountStore.save()` raises rather than
storing one.

## `upsert_variable()`: the one place this app can lose user data

Reads `WeintCodex.lua`, replaces a block, writes back — on a file WoW
itself may rewrite in full at `/reload`/logout. Falling between read and
replace loses everything added that session, replaced by the last-login
state, with no error and no distinguishing symptom from "an update
deleted my notes". Size/mtime are re-checked immediately before
`os.replace()`, repeated up to `WRITE_ATTEMPTS` on mismatch. `False`
(not written) is not an error — retried next sync cycle, and also
travels via the live bridge (`addon/live_bridge.py`); a repeated
delivery costs nothing, an overwritten save is unrecoverable. Same
reasoning covers `SyncReader.remove_message()` — a twice-delivered
message is the far smaller cost.

What this app **cannot** prevent, and is therefore documented rather
than promised away: WoW only writes SavedVariables at logout/`/reload`.
A crashed or force-quit client loses everything since login regardless of
what Companion does.

## Backups: what's saved, and what's returned

`BackupManager.create_backup()` archives both the addon folder
(`WeintCodex/…`) and the SavedVariables game state (`WTF/…`), separately.
`restore()` unpacks **only** the addon part by default — the game state
restores only on explicit request, and a restore **moves the existing
file aside** rather than deleting it (a restore with no way back is a
one-way street). All accounts under `WTF/Account/*` are backed up.
`InstallerWorkflow.run()` checks writability (`probe_writable()`, see
`../systems/update-system.md`) **before** the download — discovering a
permission problem after five megabytes and a backup is the wrong order.

Storage accumulation (download/backup folders growing unbounded, and now
warning about it): `../systems/update-system.md`.
