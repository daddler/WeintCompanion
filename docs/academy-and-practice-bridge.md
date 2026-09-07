# Academy & Rotationshelfer: lokale Nachrichten zwischen Codex und Companion

Diese Datei bündelt alle Nachrichten, die **nie zum Bot gehen** und
ausschließlich zwischen Codex (Ingame-Addon) und Companion (Desktop)
laufen, rund um WeintTV/Academy im Spiel und die Trainingspuppen-Auswertung.
Bot-seitig gibt es hierzu nichts zu dokumentieren.

## Companion → Codex: das Ingame-WeintTV/Academy füttern

`AddonAnalysisSync` (`core/addon_analysis_sync.py`) veröffentlicht die
zuletzt analysierte `RaidSnapshot` als drei Nachrichten:
`academy_catalog`, `academy_state`, `weinttv_report`. Ihre Nutzlasten sind
**verschachtelte Lua-Tabellen** (`core/lua_table.to_lua()`), nicht flache
Strings — ein Trennzeichenformat wäre für deutschen Lektionstext und
Schadenshinweise nicht eindeutig. Formen definiert in `addon/addon_payloads.py`,
müssen mit dem Header-Kommentar von Codex' `modules/companion.lua`
synchron bleiben. `stars == 0` (keine Daten, nicht „schlecht") und
`at_seconds == -1` (kein bekannter Zeitpunkt, nicht Sekunde 0) reisen
unverändert durch — diese beiden Konventionen dürfen nie normalisiert werden.

Der Dienst ruft **niemals** `RaidDataService.attach()` — das würde die App
für Nutzer, die weder WeintTV noch Academy je öffnen, dauerhaft pollen
lassen. Zugestellt wird also nur, was WeintTV oder Academy zuletzt selbst
analysiert haben.

**Katalog vor Zustand, unsichtbar gekoppelt.** `core/addon_analysis_sync.py`
veröffentlicht den Katalog **vor** dem Zustand in einer geordneten Liste;
Codex' `store.pendingCatalog` übernimmt ihn von der unmittelbar folgenden
`academy_state`-Nachricht. Diese Kopplung ist in beiden Dateien kommentiert
und darf nicht auseinandergerissen werden.

**Eine Identität pro Zustellung.** `AddonAnalysisSync.process()` löst den
Spielernamen **einmal** auf und reicht ihn an `build_profile`,
`build_academy_state(character=…)`, `build_weinttv_report` und
`build_plan(character=…)` weiter — sonst käme `academy_state.character` aus
`PlayerProfile.name` (dort `"-"`, wenn der Spieler nicht im Snapshot steht),
während `weinttv_report.me` den echten Namen trüge. `hasActor` sagt, ob der
Charakter überhaupt im Pull war; `hasActor = false` zusammen mit
`stars == 0` ist die korrekte, vollständige Auskunft „keine Daten", keine
Lücke.

## Codex → Companion: Academy-Rückweg (lokal, `academy`-State-Nachricht)

Im Spiel angehakte/ausgeschlossene Lektionen kommen als
`<char>|<done,…>|<excluded,…>;…` zurück; `SyncManager._apply_academy_progress()`
(Companion) ersetzt damit die lokalen `AcademyService`-Listen. Erreicht den
Bot nie — reine Desktop-lokale Daten.

## Codex → Companion: `dummy_practice_session` (Rotationshelfer)

Der Rotationshelfer im Addon (`modules/rotationtrainer.lua`) meldet eine
Nachricht pro abgeschlossener Übungssitzung an einer Trainingspuppe, lokal
behandelt von `core/academy_dummy_sync.py` (Companion) und **nie** an den
Bot weitergereicht. Sieben feste Positionsfelder — eine Erweiterung
verlangt Änderungen auf beiden Seiten.

**Drei aufeinanderfolgende Kalendertage mit qualifizierender Sitzung** haken
die Lektion `<slug>.rotation.dummy_practice` der Spec ab.

**Qualifizierend heißt mindestens `MIN_SESSION_SECONDS` (180) Kampfzeit**
plus `MIN_COMPLIANCE_PERCENT`. **Diese Zahl (180) muss auf beiden Seiten
identisch bleiben** — Codex-seitig in `modules/rotationtrainer.lua`
(`MIN_SESSION_SECONDS`, das ist, was der Spieler sieht: „noch 1:12 bis zur
Wertung"), Companion-seitig in `core/academy_dummy_sync.py` (das entscheidet,
was von einer älteren Addon-Version noch akzeptiert wird). Damit drei
Minuten überhaupt erreichbar sind, beendet `PLAYER_REGEN_ENABLED` im Addon
die Sitzung nicht sofort, sondern erst nach `RESUME_WINDOW` (20 s) ohne
Kampf — gemessen wird trotzdem nur echte Kampfzeit.

## Verwandt, nicht Teil dieser Datei

- `character_report`/`character_sheet` (Codex → Companion, „wer bin ich" /
  Ausrüstungsstand) → eigene Dateien (`character-sheet-bridge.md` für
  Ausrüstung; Identitätsauflösung ist Companion-intern, siehe
  `CLAUDE.md`-Abschnitt „Who is 'me'?").
- Die sechs Academy-Bewertungsbereiche, Lektionskatalog, Progression-Kurve
  → reine Companion-interne Logik (`analyzer/academy/`), kein Cross-Repo-
  Vertrag, dokumentiert in `systems/weinttv-academy.md`.
