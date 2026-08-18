# WeakAura-Brücke: Vertrag zwischen Companion und Addon

Diese Datei beschreibt die beiden Nachrichten, mit denen eine
WeakAura am Schreibtisch eingetragen und im Spiel installierbar wird:

- `weakaura_library` — **Companion → Addon**, verschachtelte Tabelle.
  Die vollständige Liste der hier eingetragenen Auren.
- `weakaura_catalog` — **Addon → Companion**, flache Zeichenkette.
  Welche Auren das Addon kennt.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, Modell und Prüfung | `core/weakaura_library.py` | WeintCompanion 2.1.0 |
| Companion, Ablage | `core/weakaura_store.py` | WeintCompanion 2.1.0 |
| Companion, sendend | `core/weakaura_sync.py` | WeintCompanion 2.1.0 |
| Companion, Oberfläche | `gui/pages/weakauras.py` | WeintCompanion 2.1.0 |
| Addon, lesend | `modules/companion.lua` (`INBOX_HANDLERS.weakaura_library`) | WeintCodex 2.1.0.0 |
| Addon, anzeigend | `modules/weakauras.lua` | WeintCodex 2.1.0.0 |
| Addon, meldend | `modules/companion.lua` (`ReportWeakAuraCatalog`) | WeintCodex 2.1.0.0 |

Der Bot ist **nicht beteiligt**. Beide Nachrichten bleiben auf dem
Rechner des Spielers — genau wie `academy`,
`dummy_practice_session`, `character_report` und `character_sheet`.
`weakaura_catalog` steht deshalb in `LOCAL_MESSAGE_TYPES`
(`core/sync_manager.py`).

Nicht zu verwechseln mit dem älteren Import-Typ **`WCIMPORT:WA:`**
(`modules/sync.lua`): der kommt vom Discord-Bot, trägt nur
Metadaten (Name, Klasse, Autor, Version, Beschreibung) und **keinen
Importstring**. Er bleibt unverändert; die hier beschriebene Brücke
liegt daneben und benutzt einen eigenen Platz in den SavedVariables
(`weakAuraLibrary` statt `weakAuras`).

## Warum das Problem überhaupt bestand

Bis WeintCompanion 2.0.12 gab es genau einen Weg, eine Aura in
WeintCodex zu bekommen: eine Lua-Datei unter `data/weakauras/`
anlegen, sie in die `.toc` eintragen, eine Version schneiden, ein
Release veröffentlichen und warten, bis alle es installiert haben.
Für eine Aura, die zum nächsten Mittwoch gebraucht wird, ist das kein
Weg.

## Warum die Companion die Liste führt und nicht das Addon

Weil eine **Löschung** sonst nicht ausdrückbar wäre. Die Inbox wird
bei jedem Login vollständig geleert; eine Nachricht "diese Aura gibt
es nicht mehr" hätte also keinen Adressaten, sobald sie einmal
gelesen wurde. `weakaura_library` trägt deshalb immer die **ganze**
Bibliothek, und das Addon **ersetzt** seine Ablage damit, statt sie
zu ergänzen. Eine gelöschte Aura verschwindet im Spiel dadurch, dass
sie in der nächsten Zustellung fehlt.

Die Kehrseite steht in `core/weakaura_sync.py`: eine leere
Bibliothek wird zugestellt und nicht übersprungen, sobald einmal
etwas zugestellt wurde. Sonst bliebe genau die eine Aura für immer
stehen, die ausdrücklich weg sollte.

## `weakaura_library` (Companion → Addon)

Verschachtelte Lua-Tabelle, geschrieben von `core/lua_table.to_lua()`
über `AddonInbox` → `InboxWriter`. Ein Trennzeichen-Format wäre für
deutschen Fliesstext (Beschreibungen) nicht eindeutig genug —
dieselbe Begründung wie bei den Academy-Nutzlasten.

```lua
["payload"] = {
    ["version"]   = 1,          -- Formatversion dieser Nutzlast
    ["updatedAt"] = 1755500100, -- Unixzeit der jüngsten Änderung
    ["auras"] = {
        {
            ["id"]          = "companion-sperlingsschlag",
            ["name"]        = "Sperlingsschlag",
            ["category"]    = "class" | "raid" | "utility",
            ["description"] = "Zeigt den Debuff.",
            ["version"]     = "1.2",
            ["string"]      = "!WA:2!...",
            ["updatedAt"]   = 1755500000,
            ["author"]      = "Fabian",                      -- optional
            ["icon"]        = "Interface\\Icons\\...",       -- optional
        },
        ...
    },
}
```

Leere Felder werden **weggelassen**, nicht als `""` geschrieben: im
Addon ist ein fehlendes Feld dasselbe wie ein leeres, und die
Nutzlast landet in einer Datei, die bei jedem Schreiben komplett neu
geschrieben wird.

Brauchbar ist eine Zeile für das Addon, wenn `id`, `name` und
`string` gesetzt sind (`UsableDelivered` in `modules/weakauras.lua`).
Alles andere darf fehlen: ohne Beschreibung ist die Zeile karg, ohne
Importstring wäre sie eine Schaltfläche, die nichts tut.

### `id` ist der Schlüssel — und der ganze Punkt

Beim Zusammenführen der beiden Quellen im Addon **gewinnt die
zugestellte Aura bei gleicher ID**. Genau so wird eine vorhandene
Aura aktualisiert. Ohne diese Regel stünde sie zweimal in der Liste,
und niemand wüsste, welche der beiden die aktuelle ist.

Daraus folgen zwei Regeln auf dieser Seite:

- **Eine neue Aura bekommt `companion-<slug>`** (`make_id()`), damit
  sie nicht versehentlich eine mitgelieferte trifft — die heissen
  `DRUID`, `DUNGEONPACK`, `WARRIOR`, …
- **Beim Bearbeiten wird die ID nie neu vergeben.** Einen Tippfehler
  im Namen zu korrigieren darf keine zweite Aura erzeugen.

### `category`

Genau drei Werte: `class`, `raid`, `utility` — die drei Rubriken der
Ingame-Seitenspalte. Beide Seiten bilden alles andere auf `utility`
ab (`normalize_category()` hier, `NormalizeCategory` dort), statt die
Zeile zu verwerfen: unsichtbar wäre der schlechtere Ausgang.

### Wann es im Spiel ankommt

**Nach dem nächsten `/reload`**, nicht sofort. WoW liest seine
SavedVariables zur Laufzeit nicht erneut; `ProcessInbox()` läuft bei
`ADDON_LOADED`. Das steht auf der Seite selbst und nicht nur hier —
wer es nicht weiss, sucht die Aura und findet einen Fehler, wo keiner
ist.

## `weakaura_catalog` (Addon → Companion)

Flache, positionsbasierte Zeichenkette; die Ausgangsrichtung kann
`addon/sync_reader.py` nur als String lesen.

```
<id>|<name>|<category>|<version>|<origin>;<id>|...
```

`origin` ist `addon` (mit dem Addon geliefert) oder `companion` (von
hier zugestellt und dort übernommen). Fehlende Felder werden
hingenommen, zusätzliche ignoriert — das Addon darf das Format
erweitern, ohne diese Seite zu brechen.

**Wozu die Meldung da ist:** die Companion kann die mitgelieferten
Auren nicht sehen. Sie stecken als Lua-Tabellen in `data/weakauras/`
im Addon-Ordner; sie dort herauszuparsen wäre ein zweiter, stiller
Vertrag über ein Dateiformat, das sich mit jedem Release ändern darf.
Ohne die Meldung könnte die Seite nur die Auren auflisten, die sie
selbst angelegt hat — und "eine vorhandene aktualisieren" wäre genau
darauf beschränkt gewesen, obwohl der häufigste Fall gerade ein
mitgeliefertes Klassenpaket ist.

**Der Importstring ist nicht dabei.** Er ist bei einem Klassenpaket
ein Vielfaches der übrigen Nutzlast (das Krieger-Paket allein sind
rund 56 kB), und zum Auflisten und Ersetzen braucht ihn niemand: wer
eine Aura aktualisiert, bringt die neue Zeichenkette ohnehin mit.
Deshalb bleibt das Feld beim Aktualisieren einer gemeldeten Aura
**leer** und muss ausgefüllt werden — ein geratener oder alter String
wäre das Gegenteil einer Aktualisierung.

### Versionssperre

Das Addon sendet nur, wenn `WeintCompanionInboxDB.companionVersion`
mindestens `2.1.0` ist (`CompanionAtLeast(2, 1)`). Eine ältere
Companion kennt den Typ nicht, gäbe ihn in ihren generischen Zweig,
POSTete ihn an den Bot, scheiterte, liesse die Nachricht liegen und
protokollierte im Sync-Takt einen Fehler — dieselbe Falle wie bei
`character_report` (1.7.0) und `character_sheet` (2.0.1).

`weakaura_catalog` steht in `STATE_MESSAGES`: es liegt immer höchstens
eine in der Warteschlange. Zusätzlich vergleicht das Addon gegen die
zuletzt gesendete Zeichenkette — der Katalog ist über eine
Spielsitzung hinweg konstant.

## Was diese Brücke nicht prüft

Ob eine Zeichenkette wirklich importierbar ist. Das weiss allein
WeakAuras. `validate()` prüft, dass überhaupt etwas dasteht und dass
es lang genug für einen Export ist; ein fehlender `!WA:`-Vorspann ist
ein **Hinweis**, keine Ablehnung — ältere WeakAuras-Versionen
exportieren so, und eine Prüfung, die richtige Eingaben abweist, ist
schlimmer als eine, die eine falsche durchlässt.

## Zugriffsprofil

WeakAuras sind **nicht gildenintern** und tragen deshalb keine
Freigabe — dieselbe Entscheidung wie beim Import-Typ `WA` in
`modules/sync.lua` (`IMPORT_FEATURE` listet ihn absichtlich nicht).
`SavedData.weakAuraLibrary` steht folgerichtig auch nicht in
`GUILD_KEYS` (`core/access.lua`) und überlebt ein
`/wc access reset`.
