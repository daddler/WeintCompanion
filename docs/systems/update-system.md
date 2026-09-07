# Updates, storage, and the "a finished check reaches the screen" chain

## GitHub-based updates (two independent channels)

- **Addon updates**: `GitHubUpdater` (`core/github_updater.py`),
  configured against `daddler/WeintCodex`, polls the GitHub Releases API
  (15-minute cache) and picks the release asset by OS. Version comparison
  uses `normalize_version()` (case/`v`-prefix-insensitive) between the
  addon's own reported version and the latest GitHub tag.
- **Companion self-update**: `CompanionUpdater`
  (`core/companion_updater.py`) checks/updates WeintCompanion itself, with
  OS-specific runners (`linux_updater.py`, `windows_updater.py`).

Both channels are triggered through **one** `UpdateRunner`
(`gui/controllers/update_runner.py`), owned by `MainWindow` and handed to
any page that exposes `set_update_runner()` (duck-typed in
`_ensure_page()`). One runner exists because the Overview's update banner
and the Addon page both start the same two flows and each carries a
detail easy to get wrong twice: the addon install is deliberately
blocking on the main thread with a `processEvents()` in front so the
"lädt" state actually paints; the Companion update runs in a thread, must
call `stop_auto_sync()` **before** it, has to restart auto-sync on
failure, and quits the process on success. One runner also means one busy
flag — two pages cannot start two installs into the same folder.

## A finished check has to reach the screen by itself

`CompanionManager.state_changed` is emitted at the end of `full_refresh()`
and `refresh_update_status()` — in a `finally`, so a failed step still
reports what earlier ones already changed. Since 2.3.3 it is also emitted
at the end of `_run_sync_worker()`, but **only when a step reports an
actual change**. `MainWindow._on_state_changed()` redraws the **visible**
page and the navigation column.

Without it the update display was, in practice, never right on first
sight: `refresh()` hung solely off `change_page()`, while `full_refresh()`
runs in `InitThread` and finishes about a second *after* the Overview has
been drawn. The signal is deliberately emitted from the worker thread —
delivered through the receiver's event loop (same reasoning as
`_AutoSyncStarter`); calling `page.refresh()` from the thread would touch
widgets from the wrong one.

**A page's `refresh()` may only draw** — see
`../architecture/navigation.md` for the `ConnectionsPage` incident this
rule comes from.

### Three places say an update is waiting

- **The Overview's update card** (`UpdateCard`/`UpdateRow`) — the one
  place that *offers the action*. Painted with an accent rail, tinted
  surface, 1-px accent border, download glyph on an accent tile, the
  app's primary `HeroButton`, plus a **breathing accent ring** around the
  card. All read in `paintEvent`. The ring hangs on
  `gui/motion/pulse_clock.py` (in phase with the nav item's warn dot); it
  stands still while a LIVE source is visible; `ring_alpha()` asks
  `is_reduced()` itself (the clock only re-decides on subscribe/
  unsubscribe); reduced motion leaves the ring at **full** strength
  (`RING_ALPHA_MAX`) rather than hiding it. Its tick repaints only the
  `RING_BAND` at the edge.
- **The Overview's system row** — `addon`/`app` go to `warn`, the row
  grows (`motion.expand`), offers "Öffnen".
- **A badge on "Addon & Updates"** in the navigation column — carries a
  **number** because the two update channels are independent (a missing
  addon isn't counted, since the system row already says that in its own
  words).
- **A toast**, once per version per channel (`_announced_updates` stores
  the version, not a bare "already told" — the *next* version is
  announced again).
- **A tray balloon**, only while the window isn't on screen
  (`_announce_in_tray`, checks more than `isVisible()` — a
  minimized-to-taskbar window still counts as visible to Qt).
  `messageClicked` restores the window and opens *Addon & Updates*.

**Nobody asks, so the app has to.** Until 2.3.2 the check happened only
at startup and on "Erneut prüfen" — after startup `state_changed` simply
stopped arriving. `core/update_watch.py`'s `UpdateWatch` rides the
ordinary sync cycle, checking only every `REFRESH_SECONDS` (900, same
span `GitHubUpdater` caches for). Four rules: **it reports the change,
not the check** (signature compare before/after); **it drops both
release caches first**; **it counts checks made elsewhere**
(`full_refresh()`/`refresh_update_status()` call `note_checked()`); **it
re-reads the installed addon version** (an update can disappear because
the addon was updated from outside).

## Ein Fehlschlag, der sich Erfolg nannte

Gemeldet: „Update lässt sich nicht installieren, *Jetzt aktualisieren*
startet normal, bricht dann aber ab." Im Protokoll standen `ERROR
Installation fehlgeschlagen: [WinError 5] Zugriff verweigert` direkt über
`SUCCESS Addon erfolgreich aktualisiert.`

**`install_or_update()` wirft nicht, es gibt einen `WorkflowResult`
zurück.** `UpdateRunner.install_addon()` und `setup_wizard._install_addon()`
warfen ihn beide weg und meldeten Erfolg, sobald keine Ausnahme flog —
eine Erfolgsmeldung, die nichts geprüft hat, ist schlimmer als gar keine.
`tests/test_install_failure.py` prüft **strukturell** (AST-Ebene): in
`gui/` und `core/` darf ein Aufruf von `install_or_update()` nirgends als
blosse Anweisung dastehen — dieselbe Lehre wie bei `core/browser.py`, wo
eine an nur einer von zwei Stellen befolgte Regel keine Regel ist.

**„Zugriff verweigert" hat zwei Ursachen, verlangt Entgegengesetztes.**
WoW unter `Program Files`: Admin-Rechte nötig. WoW läuft noch: Ordner
lässt sich nicht umbenennen, Spiel beenden nötig. Von aussen identisch.
`core/install_errors.py` — rein rechnend, kein Qt/Netz —
`is_permission_error()` läuft die Ausnahmekette ab (`errno` **und** beide
Sprachen des OS-Texts, da `shutil`/`zipfile` denselben Fehler unter
verschiedenen Klassen verpacken), `permission_message()` formuliert.
`probe_writable()` unterscheidet über eine Probe statt einer
plattformabhängigen Prozessliste: lässt sich schreiben, aber nicht
umbenennen, hält jemand den Ordner offen. Zurückhaltend: nur
`EACCES`/`EPERM` heissen „nein".

Drei Folgen: `InstallerWorkflow.run()` prüft das Schreibrecht **vor dem
Download**; `WorkflowResult.message` trägt den Satz aus der Ausnahme; die
Einblendung hängt an `UpdateRunner.finished` in `MainWindow`, nicht an
einer Seite (**ein** Läufer, beide Seiten lösen ihn aus).

## Every release ships its changelog — this is not optional

Same rule as the addon (see `../../../WeintCodex/docs/development/releases.md`),
enforced on this repo's own release process too: `scripts/check_version.py`
fails a tag whose `CHANGELOG.md` section is missing;
`scripts/release_notes.py` prints that section as the GitHub release
body. The addon's `CHANGELOG.md` additionally travels **inside its
release ZIP**, so `core/changelog_source.py` reads the addon's *full*
history offline rather than depending on release text.
`core/changelog_reader.py` understands both this repo's headings
(`## 2.0.1`) and the addon's (`## [1.3.3.1] – 2026-08-11`) —
`tests/test_changelog.py` holds both, because a parser that silently
stops matching produces an empty list indistinguishable from "nothing
changed". Three consumers read from `core/changelog_source.py` and none
may grow its own parser: the "Was ist neu" popup
(`read_changelog_sections()`), the two component cards under *Addon &
Updates* (`update_note()`), and `gui/dialogs/changelog_dialog.py`.

**Über dem Update-Knopf steht die Fassung, die man hat, nicht die
angebotene.** `update_note()` liest den Eintrag zur **installierten**
Fassung (beschriftet: „Das steckt in deiner Fassung 2.4.0:"); gibt es
dazu keinen Eintrag, ist die Antwort `None` — der Text einer anderen
Fassung darf nie einspringen. Was das Update mitbringt, steht vollständig
hinter „Alle Änderungen ansehen".

`format_changelog_body()` strips Markdown rather than rendering it
(`QLabel` rich text would need `<`/`&` escaped everywhere) — handles
`### Neu` subheadings, `- ` bullets with indented continuations, and free
paragraphs.

## Patchnotes werden für Spieler geschrieben — see the shared style rules

Full rule set (kein Dateiname/Funktionsname/Konfigurationsschlüssel,
Wirkung vor Ursache, `### Technisch` als letzte Überschrift) is documented
once, identically for both repos, in
`../../../WeintCodex/docs/development/releases.md` — this repo follows the
same five rules for `CHANGELOG.md`, the update card, and the "Was ist
neu"/onboarding dialog (`../systems/whats-new-and-onboarding.md` covers
that dialog's own mechanics).

## Storage: downloads and backups accumulate, and now say so

`InstallerWorkflow` never deletes the downloaded archive or the backup it
creates on every addon update — correct (a self-deleting backup isn't
one), but the counts lived only under *Einstellungen → Backups*, where
nobody goes without already looking for it. `core/storage_usage.py` is
the Qt-free half (only `scan()` touches disk), `core/storage_watch.py`
the watcher, built like `UpdateWatch`. Four rules: **counted per
folder** (downloads vs. backups are two separate cleanups); **size
travels with the count**; **the change is reported, not the count**
(`process()` compares before/after); `MainWindow._announce_storage()`
**remembers the count last announced** and only re-announces after
`WARN_COUNT` more files — a notification after every single update would
be dismissed unread.

**And the backup once saved the wrong thing.**
`BackupManager.create_backup()` archived the **addon folder**, not the
`SavedVariables` — exactly backwards, since only the SavedVariables data
(Bossnotizen, Twinkliste, Encounter-Fortschritt, Academy, WeakAura-
Bibliothek) is unrecoverable; the addon folder is on GitHub. The archive
now carries both, cleanly separated (`WeintCodex/…` and `WTF/…`). Three
rules: `restore()` unpacks **only** the addon part; the game-state part
restores **only on explicit request**; the existing file is **moved
aside**, never deleted, on restore. All accounts under `WTF/Account/*`
are backed up (unlike `SyncReader.get_file()`, which only needs the
first — that's about where to *write*, this is about what could be
*lost*).

**`upsert_variable()` is the one place this app can lose user data.** It
reads `WeintCodex.lua`, replaces a block, writes back — on a file WoW
itself may rewrite in full at `/reload`/logout at any moment. Falling
between our read and our replace loses everything added in that session,
replaced by the last-login state — indistinguishable from "an update
deleted my notes". Size/mtime are re-checked immediately before
`os.replace()`, repeated up to `WRITE_ATTEMPTS` on mismatch. `False`
(not-written) is not an error — the same delivery retries next cycle and
also travels via the live bridge (`addon/live_bridge.py`); a repeated
delivery costs nothing, an overwritten save is unrecoverable.

Full atomic-write and path rules: `../development/paths-and-storage.md`.
