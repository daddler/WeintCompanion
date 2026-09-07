# Charakteridentität & Notfall-Backup: Vertrag zwischen Bot, Companion und WeintAdmin

Diese Datei bündelt drei verwandte, aber getrennte Bot-Endpunkt-Familien, die
alle die Frage "wer ist wer" oder "was stand gerade im Sign-up" beantworten:
`/companion/raid-roster`, `/companion/character-links`, `/companion/raid-
signups` (WeintAdmin). Bot-Seite: `services/character_links.py`,
`services/admin_sync.py`, `services/raid_export_manager.py`,
`services/sync_server.py`. Companion-Seite: `core/character_links.py` (rein),
`core/character_links_client.py` (HTTP), `gui/pages/character_links.py`.

## Wer steckt hinter einem Discord-Konto? (`character_links.py`, Bot)

Der Kalender-Invite braucht einen echten Charakternamen (siehe
`wcimport-protocol.md`). Der Bot kannte ihn bisher nur über
`companion_characters` (gefüllt von `POST /companion/characters`, jeder
verlinkte Spieler meldet seine eigenen Twinks) — für alle anderen ging der
Discord-Anzeigename raus, der ingame nicht existiert.

`services/character_links.py` fügt eine **zweite, von Hand gesetzte** Quelle
hinzu und ist die eine Stelle, an der beide Quellen versöhnt werden. Die
Rangfolge (in `tests/test_character_links.py` gepinnt, ein Fehler hier wirft
keinen Fehler — er lädt die falsche Person ein):

1. manueller Eintrag, der zur Klasse passt
2. der eigene Bericht des Spielers, der zur Klasse passt
3. manueller Eintrag ohne Klasse (der Platzhalter)
4. → nichts, Rückfall auf den Discord-Namen

Die spezifischere Antwort gewinnt immer, gleich aus welcher Quelle; bei
gleicher Spezifität gewinnt die Raidleitung (die aktuellste Korrektur schlägt
einen möglicherweise wochenalten Bericht). Zwei strukturelle Punkte: eine
**eigene Tabelle**, nicht eine `source`-Spalte auf `companion_characters`
(das wird bei jedem Sync komplett ersetzt — ein manueller Eintrag dort würde
beim nächsten Sync des Spielers gelöscht); `class_token` ist immer `''`,
nie `NULL` (SQLite behandelt NULLs in einem zusammengesetzten Primärschlüssel
als paarweise verschieden — „Platzhalter ersetzen" würde sonst lautlos zu
„zweiten Platzhalter hinzufügen").

Zwei Frontends, beide raidlead-gated, beide über dieselbe Regel:
- `/weintcharakter setzen|entfernen|liste` (Discord, `cogs/character_links.py`)
- `GET/POST/DELETE /companion/character-links` (Companion-Seite
  `gui/pages/character_links.py`, `PageId.CHARACTER_LINKS`)

`liste`/die Companion-Seite zeigen **vor** dem Einladungslauf, welcher Name
für wen benutzt würde und woher er kommt — `build_link_overview(guild,
raid_id)` liegt bewusst in `raid_export_manager.py` und läuft durch dieselbe
Auflösung wie der Export, damit Übersicht und tatsächlicher Export nie
auseinanderlaufen.

**Companion-Seite: sperren, nicht verstecken.** Ohne Raidlead-Rolle
antwortet der Bot mit 403; das reist als eigenes Feld (`Overview.forbidden`)
und erklärt, wofür die Seite da wäre, statt sie unsichtbar zu machen (*lock,
don't hide*, wie `core/access.lua` im Addon). „0 offen" wird nie behauptet,
wo nichts gezählt wurde (`summary_text()`, dieselbe Linie wie `stars == 0`).
Nach jedem Schreiben wird der **ganze** Stand neu geholt statt eine Zeile
lokal nachzuziehen — der Bot entscheidet über den Vorrang. Jeder Abruf läuft
in einem kurzlebigen Thread mit Rückmeldung über ein Signal (`loaded`).

## WeintAdmin-Brücke (`services/admin_sync.py`, Bot)

Ein viertes, unabhängiges Backup der laufenden Anmeldung — für den Fall, dass
sowohl die Discord-Snapshot-Mechanik (siehe unten) **als auch** alle drei
Nachrichten-Kopien gleichzeitig verschwinden (Summary-Nachricht und beide
Tages-Threads von Hand gelöscht, bevor der Bot neu startet). WeintAdmin ist
ein kleines Desktop-Tool, das der Raidlead selbst bedient: holt die laufende
Anmeldung per HTTP, cached sie lokal, und schreibt sie — nachdem der Raidlead
den Raid in Discord neu erstellt hat (`/weintraid`) — in den neuen Raid
zurück.

`GET /companion/raid-signups` und `POST /companion/raid-signups/restore`
(beide raidlead-gated wie `/companion/raid-roster`) sind dünne
HTTP-Wrapper um `services/admin_sync.py`. Bei parallelen Raids ist das Ziel
eine Wahl, kein Automatismus: `?raid=<id>` bzw. `raid_id` im Body wählen
einen; weggelassen bedeutet „der nächste Raid" (genau das Verhalten des
ausgelieferten WeintAdmin).

- `export_current_signups(raid_id)` gibt jede Anmeldungszeile **so wie sie
  ist** zurück (Klasse/Spec, beide Tagesstatus, `signup_time`); das
  JSON-Feld heißt weiterhin `users`, damit ein bereits ausgeliefertes
  WeintAdmin seine eigenen Backups lesen kann — anders als das
  WCIMPORT-formatierte `/companion/raid-roster`, das nur die aktiven Zusagen
  trägt, nicht den rohen Pro-Tag-Status, den eine Wiederherstellung braucht.
- `restore_signups_into_current_raid()` nutzt **absichtlich nicht**
  `raid_manager.import_raid_snapshot()` (das ersetzt `raid`/`raid_message`
  komplett — richtig bei der Wiederherstellung in eine leere DB, falsch
  hier: der Ziel-Raid wurde gerade frisch erstellt, mit eigener frischer
  Nachricht). Stattdessen schreibt es zeilenweise über
  `user_manager.save_user_signup()` — denselben Weg wie ein Spieler-Klick —
  und lässt Raid-Identität und Nachrichtenbindung unangetastet. Nur Zeilen
  mit `signup_time` werden übernommen (derselbe Filter wie bei
  `import_raid_snapshot()`).

Der Restore-Endpunkt schreibt die DB und ruft danach **synchron**
`cogs.raid.refresh_raid_message()` auf dem Discord-Loop auf
(`run_coroutine_threadsafe` + `future.result(timeout=15)`); das Feld
`message_refreshed` in der Antwort sagt ehrlich, ob die Discord-Embeds den
wiederhergestellten Stand schon zeigen oder noch einen manuellen Anstoß
brauchen — statt `"ok"` zu melden, während die Nachricht still veraltet ist.

## Verwandt, aber nicht Teil dieser Datei

- `/companion/raid-roster` selbst → siehe `wcimport-protocol.md` (der
  WCIMPORT-Inhalt) und `raid-schedule-bridge.md` (die Discord-Präsenzprüfung,
  die auch dieser Endpunkt vor dem Export durchführt: 404, wenn das Sign-up
  in Discord nicht mehr gefunden wird).
- Die Discord-Snapshot-Mechanik (`export_raid_snapshot`/`recover_raid_state`
  im Bot) selbst ist kein Companion-Vertrag — sie ist reine Bot-interne
  Ausfallsicherheit gegen den fehlenden persistenten Speicher des Hosts.
  Dokumentiert in `../../WeintCodex-Bot/docs/systems/raid-persistence.md`.
