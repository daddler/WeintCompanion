# Ausrüstungsbrücke: Vertrag zwischen Addon und Companion

Diese Datei beschreibt die Nachricht `character_sheet`, mit der
**WeintCodex** den Ausrüstungsstand des angemeldeten Charakters an
**WeintCompanion** meldet. Sie ist die Datengrundlage der Seiten
"Meine Charaktere" und "Vorbereitung" und der Vorbereitungskachel auf
der Übersicht.

## Stand

Vollständig umgesetzt auf beiden Seiten:

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Addon, sendend | `modules/companion.lua` (`ReportCharacterSheet`) | WeintCodex 1.3.3.1 |
| Companion, lesend | `core/character_sheet_sync.py` | WeintCompanion 2.0.1 |
| Companion, ablegend | `core/character_store.py` | WeintCompanion 2.0.1 |

Der Bot ist **nicht beteiligt**. Die Nachricht wird von `SyncManager`
lokal verarbeitet und verlässt den Rechner nie - genau wie `academy`,
`dummy_practice_session` und `character_report`. Es ist die eigene
Ausrüstung, kein Gildenwissen; sie steht deshalb in
`LOCAL_MESSAGE_TYPES`.

## Warum ein eigener Nachrichtentyp

`character` (die Twinkliste) läuft über den `CharacterSyncClient`
weiter an den Discord-Bot. Alles, was an jene Nachricht angehängt
würde, wäre damit ein **Bot-Vertrag** und ließe sich nicht mehr
ändern, ohne den Bot mitzuziehen. Dieselbe Begründung wie bei
`character_report` in 1.7.0.

## Wann gesendet wird

Nicht bei `PLAYER_LOGIN`: dort ist weder die Spezialisierung
verlässlich abfragbar noch stehen die Item-Daten im Client-Cache - ein
Scan zu diesem Zeitpunkt meldete eine halb leere Ausrüstung als
**Befund**. Gesendet wird bei `PLAYER_ENTERING_WORLD` (nach 8 s) und
danach entprellt (3 s) bei `PLAYER_EQUIPMENT_CHANGED`,
`SKILL_LINES_CHANGED` und den Spec-Wechsel-Ereignissen.

Zwei Sperren davor:

- **Versionsprüfung.** Das Addon sendet nur, wenn
  `WeintCompanionInboxDB.companionVersion` mindestens `2.0.1` ist.
  Eine ältere Companion kennt den Typ nicht, gäbe ihn in ihren
  generischen Zweig, POSTete ihn an den Bot, scheiterte, ließe die
  Nachricht liegen und protokollierte im Sync-Takt einen Fehler. Für
  diese dritte Stelle wurde `CompanionAtLeast()` um einen
  `patch`-Parameter erweitert - 2.0.0 war bereits draußen, "mindestens
  2.0" hätte also genau die Version eingeschlossen, die den Typ nicht
  kennt.
- **Fingerabdruck.** Gesendet wird nur, wenn sich die Nutzlast
  gegenüber der letzten geändert hat. Der Scan läuft bei jedem
  Ausrüstungswechsel, die Nachricht nicht - sonst schriebe jeder
  Ringtausch dieselbe Zeichenkette erneut in die SavedVariables.

`character_sheet` steht in `STATE_MESSAGES`: es liegt immer höchstens
eine in der Warteschlange, und sie beschreibt den **gerade
angemeldeten** Charakter. Die Liste über mehrere Twinks entsteht erst
auf der Companion-Seite, indem `CharacterStore` die Meldungen mehrerer
Anmeldungen einsammelt.

## Format

Ausgangsnachrichten kann `addon/sync_reader.py` nur **zeilenweise als
Zeichenkette** lesen (verschachtelte Lua-Tabellen gibt es nur in der
Gegenrichtung, siehe `core/lua_table.py`). Die Nutzlast ist deshalb
flach und positionsbasiert:

```
<KOPF> ~ <ZÄHLER> ~ <BIS> ~ <SLOTS> ~ <MÄNGEL>
```

Abschnitte mit `~`, Datensätze mit `;`, Felder mit `|`. Das Addon
ersetzt diese drei Zeichen (sowie `"`, `\` und Zeilenumbrüche) im
Inhalt durch ein Leerzeichen — Itemnamen kommen aus dem Client und
könnten sonst die Struktur zerlegen; ein Backslash würde zusätzlich
den Lua-String zerbrechen, in den `sync_reader.remove_message()` die
verbleibenden Nachrichten zurückschreibt.

### KOPF (ein Datensatz)

| # | Feld | Bedeutung |
|---|------|-----------|
| 0 | `name` | Charaktername (**Pflicht** — ohne ihn wird die Meldung verworfen) |
| 1 | `realm` | Realm, darf leer bleiben |
| 2 | `class` | `classFile` aus `UnitClass()`, z. B. `PALADIN` |
| 3 | `level` | Stufe (entscheidet ab Companion 2.3.1 über die Anzeige, siehe unten) |
| 4 | `spec_key` | Profilschlüssel, z. B. `PALADIN_RETRIBUTION` |
| 5 | `spec` | Anzeigename der Spezialisierung, z. B. `Vergeltung` |
| 6 | `item_level_equipped` | Gegenstandsstufe angelegt |
| 7 | `item_level_overall` | Gegenstandsstufe gesamt |
| 8 | `score` | Ausrüstungspunkte 0–100 |
| 9 | `grade` | Note `S`/`A`/`B`/`C`/`D`/`F` |
| 10 | `completeness` | Anteil belegter Plätze in Prozent |
| 11 | `quality` | Güte der belegten Plätze in Prozent |
| 12 | `updated` | Unix-Zeitstempel |

### ZÄHLER (zwei Datensätze)

`Art|optimal|ok|falsch|überCap|fehlt|gesamt`, Art ist `ench` oder
`gem`. Die Statuswerte sind dieselben wie in `modules/charakter.lua`
(Tabelle `STATUS`).

### BIS (null bis zwei Datensätze)

- Datensatz 1: `getragen|Variante|offen|gesamt`, gezählt **je Slot**,
  nicht je Eintrag: eine BiS-Liste führt für Finger und Schmuck
  mehrere Einträge, und wer einen davon trägt, hat den Platz nicht
  halb offen.
- Datensatz 2: die Namen der offenen Plätze, mit `|` getrennt.

**Der Abschnitt fehlt ganz, wenn für die Spezialisierung keine
BiS-Liste gepflegt ist.** Das ist der Kern dieses Blocks: „0 offen"
behauptete dort eine geprüfte Vollständigkeit, die es nicht gab. Die
Companion zeigt in diesem Fall „keine Liste" statt einer Null.

### SLOTS (ein Datensatz je Ausrüstungsplatz)

`slotId|Slotname|Itemname|Ilvl|Verzauberung|Sockel`

Die beiden Statusfelder tragen `optimal`, `ok`, `wrong`, `overcap`,
`missing` oder `-`. **`-` heißt „dieser Platz kennt so etwas nicht"** —
ein Hals hat keine Verzauberung, das ist kein Mangel. Hat ein Item
mehrere Sockel, steht der **schlechteste** von ihnen: die
Vorbereitungsansicht fragt, wo noch etwas zu tun ist, und ein leerer
Sockel neben zwei perfekten ist genau das.

Ein leerer Platz meldet Ilvl `0` und wird nicht ausgelassen — die
Companion soll „hier hängt nichts" zeigen können.

### MÄNGEL (ein Datensatz je Hinweis)

`prio|status|Text`, bereits nach Dringlichkeit sortiert (1 = etwas
fehlt, 4 = etwas ist nicht ideal). Der Text ist fertig formuliert und
enthält die Empfehlung; die Companion zeigt ihn unverändert.

## Wer bewertet

**Das Addon.** Welche Verzauberung optimal ist, welcher Stein falsch
sitzt und welcher Wert über dem Cap liegt, entscheidet
`modules/charakter.lua` im Spiel — dort sind Spec-Profile
(`data/spec_profiles.lua`), Caps, Sockelboni und die
Verzauberungs-/Steintabellen bekannt, und dort steht der echte
Item-Tooltip zur Verfügung.

Die Companion ist eine **reine Anzeige**, dieselbe Rollenteilung wie
bei WeintTV und der Academy in der Gegenrichtung: dort rechnet die
Companion und das Addon zeichnet nur. Beide Male ist der Grund
derselbe — zwei Bewertungen desselben Sachverhalts laufen
auseinander, und dann widersprechen sich Spiel und Desktop.

## Toleranzregeln

Beide Seiten dürfen sich unabhängig aktualisieren, deshalb:

- **Fehlende Abschnitte, fehlende Felder und zusätzliche Felder sind
  kein Fehler.** Nur ohne Namen ist die Meldung wertlos — sie ließe
  sich keinem Charakter zuordnen, und einen zu raten ist genau der
  Fehler, den 1.7.0 abgestellt hat (siehe „Wer ist ‚ich'" in
  `CLAUDE.md`).
- **Eine fehlende Angabe ist `None`, keine Null.** `bis is None` heißt
  „für diese Spec ist keine Liste gepflegt", `bis["open"] == 0` heißt
  „nichts offen". `readiness()` liefert `None`, wenn nichts geprüft
  wurde. Wer beides zusammenzieht, macht aus einer Datenlücke einen
  Befund — dieselbe Regel wie `stars == 0` im Analyzer.
- **Offene BiS-Plätze zählen nicht in den Vorbereitungsring.** Sie
  hängen an Würfelglück, nicht an Vorbereitung, und färbten den Ring
  eines frisch ausgestatteten Charakters dauerhaft rot für etwas, das
  er nicht abstellen kann. Sie stehen als eigene Zeile daneben.

`tests/test_character_sheet.py` hält diese Regeln fest.

## Ablage

`characters.json` in `Paths.config()`, **nicht** in `Paths.cache()`:
Wer seit zwei Wochen nicht auf dem Zweitcharakter war, soll ihn in
„Meine Charaktere" trotzdem sehen. Im Cache wäre er beim ersten
Aufräumen weg, und die Seite behauptete, es gäbe ihn nicht.

Schlüssel ist `Name-Realm` — zwei Realms dürfen denselben Namen
führen. Beim Lesen findet der blanke Name den qualifizierten Eintrag,
weil der Client nur den nackten Namen kennt; ein fehlender Realm ist
im ganzen Projekt ein Platzhalter und kein Widerspruch (siehe
`analyzer/names.py` und `core/names.lua`).

Eine neue Meldung **ersetzt** den Eintrag, sie ergänzt ihn nicht. Ein
Feld, das die neue Meldung nicht mehr trägt, beschriebe einen Zustand,
den es nicht mehr gibt — wer eine Verzauberung entfernt, soll sie
nicht deshalb weiter als vorhanden angezeigt bekommen, weil die vorige
Meldung sie noch kannte.

## Stufe und Anzeige (ab Companion 2.3.1)

`CharacterStore` speichert **jede** Meldung, zeigt aber nur
Charaktere ab `min_level()` (Vorgabe 90, die Höchststufe von MoP
Classic; `characters_min_level` in der `config.json` setzt den Wert
herunter). "Meine Charaktere", "Vorbereitung" und die Kachel auf der
Übersicht lesen dieselbe gefilterte Liste, damit sie nicht
auseinanderlaufen.

Für das Addon ändert sich dadurch nichts: es meldet weiterhin jeden
angemeldeten Charakter, und ein **fehlendes** Feld 3 gilt als hohe
Stufe. Eine 0 heisst dort "nicht gemeldet" und nicht "Stufe 0" - ein
Addon-Stand, der das Feld noch nicht trägt, lässt seinen Charakter
deshalb nicht verschwinden.
