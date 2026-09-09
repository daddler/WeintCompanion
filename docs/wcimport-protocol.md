# WCIMPORT-Protokoll: Vertrag zwischen Bot und Codex (Companion als Relais)

Diese Datei beschreibt `WCIMPORT:<TYPE>:<payload>` — die Zeichenkette, die
der **WeintCodex Bot** über Discord-Slash-Commands (`/export boss|raidwed|
raidthu|mat|wa`) erzeugt und die der Spieler in den Import-Dialog von
**WeintCodex** einfügt (`/wc import`, `WeintCodex.Sync.QuickImport(str)`,
Parser in `modules/sync.lua`). Für `RAIDWED`/`RAIDTHU` übernimmt
**WeintCompanion** zusätzlich die Zustellung automatisch: `DiscordRosterSync`
(`core/discord_roster_sync.py`) holt beide Strings über
`GET /companion/raid-roster` (raidlead-gated) und schreibt sie unverändert
als `raid_import`-Inbox-Nachricht in die Addon-SavedVariables — Companion
liest den Inhalt dabei nicht, sie reicht ihn nur durch.

Bot-Seite: `raid_export_manager.build_addon_export(guild, raid_id)` (und die
typspezifischen `/export`-Commands). Codex-Seite: `modules/sync.lua`, je Typ
ein eigener handgeschriebener Parser (`ParseBossImport`, `ParseRaidImport`,
`ParseMatImport`, `ParseWAImport`). **Das ist kein gemeinsames Schema,
sondern zwei unabhängige Implementierungen desselben Formats** — Feldreihenfolge
oder ein neues Feld auf der Bot-Seite verlangt die passende Änderung im
Codex-Parser, sonst driften sie lautlos auseinander.

## Umschlag

`WCIMPORT:<TYPE>:<payload>`, wobei `<TYPE>` optional einen Community-Suffix
trägt: `WCIMPORT:RAIDWED@<id>:<payload>`. Der Suffix wird **nach** dem
Umschlag-Regex und **vor** `:upper()` abgespalten — die Umschlag-Regex fasst
`RAIDWED@1234` als Ganzes, weil `@` kein `:` ist. Eine Nachricht mit fremdem
Community-Suffix wird verworfen; jeder gildeninterne Typ verlangt zusätzlich
das Feature, das seine Anzeige freischaltet (`IMPORT_FEATURE` in
`modules/sync.lua`). `WA` (WeakAuras) und `SW` (Sim-Gewichte) sind frei —
weder gildenintern.

## Mehrere Umschläge in einem Text (seit Codex 3.1.2.0)

Ein eingefügter Text darf **mehrere** Umschläge tragen, je einen pro
Zeile. `Sync.ProcessImportText()` zerlegt ihn an `WCIMPORT:` — nicht an
Zeilenumbrüchen, weil eine Nutzlast selbst welche enthalten darf — und
verarbeitet die Teile der Reihe nach. Ein **einzelner** String verhält
sich unverändert: derselbe Rückgabewert, dieselbe Meldung, derselbe
Fehlertext. **Teilerfolg gilt als Fehler**, damit die Oberfläche das
Eingabefeld stehen lässt (`SW` und `TG` ersetzen beide, ein zweiter
Versuch schadet also nicht).

Genutzt wird das von WeintCompanion nach einem Sim-Lauf: Gewichtung
(`SW`) und Zielausrüstung (`TG`) kommen als zwei Zeilen in einem Zug.

**Ältere Codex-Fassungen dürfen das nicht bekommen.** `SW.ParseTransfer`
zerlegt an `:` und nimmt Feld 6; alles dahinter fällt weg, **ohne**
Fehler — beide Zeilen zusammen ergäben dort eine Erfolgsmeldung, in der
die Zielausrüstung fehlt. Die Companion prüft deshalb die installierte
`.toc`-Fassung (`_combined_allowed()` in `gui/pages/sim.py`,
`COMBINED_SINCE = 3.1.2.0`) und gibt im Zweifel nur eine Zeile aus. Eine
nicht feststellbare Fassung gilt dabei wie eine zu alte.

## Typen

- **`BOSS`** — Bossnotizen/-fortschritt.
- **`RAIDWED` / `RAIDTHU`** (legacy: `RAID`) — die Raid-Anmeldeliste für
  Mittwoch/Donnerstag: `WCIMPORT:RAIDWED:<date>:<HHMM>:<title>:<name>|<ROLE>|
  <CLASS>|<realm>|<note>|<source>|<status>|<lineup>|,...`. Colons und Pipes
  sind Feldtrenner; `_compact_time`/`_sanitize_title` (Bot) bzw. die
  entsprechenden Codex-Parser-Regeln entfernen kollidierende Zeichen vorher.
  Wird von `DiscordRosterSync` automatisch zugestellt (s. o.).
- **`MAT`** — Materialbedarf.
- **`WA`** — WeakAura-Metadaten (älterer Bot-Import, **kein** Importstring,
  eigener SavedVariables-Schlüssel `weakAuras`; nicht zu verwechseln mit der
  neueren `weakaura_library`-Inbox-Brücke, siehe `weakaura-bridge.md`).
- **`SW`** — Sim-Gewichte. Einziger Typ, der **nicht** vom Bot kommt: er wird
  von **WeintCompanion** selbst gebaut (`core/stat_weights.py`, der
  `WCIMPORT:SW:`-String) und über dieselbe Codex-seitige Envelope-Syntax
  geparst (`modules/statweights.lua`). Voller Vertrag: `stat-weights-bridge.md`.

## Die Spieler-Zeile von RAIDWED/RAIDTHU: acht Felder

Format: `name|ROLE|CLASS|realm|note|source|status|lineup|`. Die ersten fünf
Felder existieren seit jeher; die letzten drei kamen additiv dazu — ein
älterer Codex-Parser liest nur bis zu dem Feld, das er kennt, und verhält
sich unverändert; ein neuer Bot, der ein fehlendes Feld schickt, behauptet
damit nichts (leer statt geraten).

### Feld 6: `source` (seit Codex 2.0.1.0)

Sagt, **ob `name` überhaupt ein Charaktername ist**: `raidlead`, `companion`
oder `discord`. Der Bot kennt den echten WoW-Namen eines Mitspielers nur,
wenn dieser Companion verknüpft *und* seine Twinkverwaltung gepflegt hat,
oder wenn die Raidleitung ihn von Hand zugeordnet hat (`/weintcharakter
setzen`, `services/character_links.py`, siehe `character-links-and-admin-
bridge.md`). Für alle anderen schickt der Bot den **Discord-Anzeigenamen** —
der existiert ingame nicht, und `C_Calendar.EventInvite` läuft dort still
ins Leere (kein Fehler, die Einladung zählt trotzdem als gelungen). `source
== "discord"` heißt für Codex: nicht einladen.

`WeintCodex.Raids.IsResolved(p)` ist die eine Stelle, die das im Addon
beantwortet (gelesen von der Anmeldeliste **und** vom Kalender). Zwei Fälle
gelten trotz `source == "discord"` als aufgelöst: eine manuelle Korrektur
über das Stift-Symbol (`rosterNameOverrides`) und ein **fehlendes** Feld
(älterer Bot).

### Felder 7+8: `status` und `lineup` (seit Codex 2.6.1.0)

Entscheiden, wer eine Kalender-Einladung bekommt.

- **`status`** trägt `active`/`tentative`/`bench` — vorher standen alle drei
  im selben Topf und der Kalender-Invite lud sie alle ein; auf der
  Ersatzbank zu sitzen und trotzdem eingeladen zu werden fiel frühestens am
  Raidabend auf. `absent` erscheint nie.
- **`lineup`** trägt die **angekündigte Aufstellung** (`services/
  lineup_manager.py`, Bot-seitig) — drei Werte, nicht zwei: `""` heißt „für
  diesen Tag wurde nichts angekündigt" (Codex fällt auf die Anmeldungen
  zurück), `in`/`out` heißen „doch, und zwar so". Der Unterschied ist der
  Punkt: leer und `out` führen zu entgegengesetztem Verhalten, ein bloßes
  Ja/Nein könnte das nicht ausdrücken (dieselbe Linie wie `stars == 0`).

`WeintCodex.Raids.HasLineup()` / `.ShouldInvite()` / `.StatusLabel()` sind
die eine Codex-seitige Stelle, die „wird dieser Spieler eingeladen"
beantwortet — gelesen von Kalender-Vorschau, Einladungslauf und
Anmeldeliste.

### Sanitisierung

`_sanitize_field()` (Bot) reinigt **Name und Realm**, nicht nur den Titel:
jeder Wert, der nicht aus einer festen Tabelle dieses Repos stammt (ein
handgetippter Name, ein gemeldeter, vor allem der ungefilterte Discord-
Anzeigename), kann einen Trenner tragen. Ein Doppelpunkt verschiebt den
Nachrichtenkopf, ein Komma oder Pipe teilt eine Zeile in zwei Spieler.

## Zwei Fehler, die identisch aussahen (Codex-seitiger Einladungslauf)

Ein Kalender-Eintrag meldete „1 von 25 bestätigt" und listete die übrigen 24
als *nicht gefunden* — bei jedem Versuch. Zwei unabhängige Ursachen im
Codex-seitigen `modules/calendar.lua`, die dasselbe Bild erzeugten:

1. **Der eigene Realm wurde in falscher Schreibweise verglichen** — überall
   ohne Leerzeichen gespeichert, aber gegen das rohe `GetRealmName()`
   verglichen. Auf einem Realm mit Leerzeichen im Namen ging der Vergleich
   nie auf. Verglichen wird jetzt über `WeintCodex.Names.Me()`.
2. **Der Rückgabewert des Einladungsaufrufs wurde weggeworfen.** `pcall` auf
   einen `nil`-Wert liefert `false, "attempt to call a nil value"` und wirft
   nichts — 25 stille Fehlschläge sahen aus wie 25 unbekannte Charaktere.
   `ResolveInviteFunc()` sucht seither unter mehreren Funktionsnamen und
   jeder Aufruf wird auf Erfolg geprüft.

Nach dem Realm-Fix trat ein dritter Fehler zutage: **gewartet wurde nach
fester Frist statt auf Fortschritt** (24 × 0,5 s), und **alle Einladungen
gingen in einem Frame raus**, obwohl der Server Namensauflösung nicht im
Bulk beantwortet. Der Lauf schickt seither alles im ersten Frame (muss am
Klick hängen), fasst danach **einzeln** nach (immer nur eine Anfrage
gleichzeitig, nächste sobald die vorige bestätigt ist oder `RESEND_GAP`
Takte vergangen sind), wartet auf **Fortschritt** statt auf eine feste Frist
(`WATCH_STALL`), und probiert bei Ablehnung die andere Schreibweise
(`Name-Realm` ↔ nackter Name) — nie blind, nur nach einer Ablehnung.

`/wc kalender` druckt Client-Funktionen, verglichenen Realm (roh und
normalisiert) und den angefragten Namen je Spieler — ohne diesen Befehl war
diese Fehlerklasse von außen nicht diagnostizierbar.
