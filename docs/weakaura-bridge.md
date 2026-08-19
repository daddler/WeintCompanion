# WeakAura-Brücke: Vertrag zwischen Companion, Addon und Bot

Diese Datei beschreibt, wie eine WeakAura am Schreibtisch eingetragen,
im Spiel installierbar und — seit 2.2.0 — für die ganze Gilde
verfügbar wird.

**Addon-Brücke** (SavedVariables, kein Netz):

- `weakaura_library` — **Companion → Addon**, verschachtelte Tabelle.
  Alles, was ins Spiel geht: eigene *und* Gildenauren.
- `weakaura_catalog` — **Addon → Companion**, flache Zeichenkette.
  Welche Auren das Addon kennt.

**Bot-Brücke** (HTTP, `/companion/weakauras`):

- `GET` — die gemeinsame Bibliothek der Gilde.
- `POST` — eine Aura freigeben oder die eigene ersetzen.
- `PATCH` / `DELETE` — nachträglich richtigstellen bzw. entfernen.

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
| Bot, Bibliothek | `services/weakaura_library.py` | — (wird deployt) |
| Bot, HTTP | `services/sync_server.py` | — |
| Bot, Moderation | `cogs/weakauras.py` (`/weintaura`) | — |
| Companion, Bot-Client | `core/weakaura_client.py` | WeintCompanion 2.2.0 |
| Companion, Abgleich | `core/weakaura_guild_sync.py` | WeintCompanion 2.2.0 |
| Addon, Herkunft „Gilde" | `modules/weakauras.lua` | WeintCodex 2.2.0.0 |

Die **Addon-Brücke** kennt den Bot nicht: beide Nachrichten bleiben
auf dem Rechner des Spielers, genau wie `academy`,
`dummy_practice_session`, `character_report` und `character_sheet`.
`weakaura_catalog` steht deshalb in `LOCAL_MESSAGE_TYPES`
(`core/sync_manager.py`). Was über den Bot kommt, wird in der
Companion mit den eigenen Auren gemischt und geht als *eine* Liste
weiter — das Addon spricht nie mit dem Bot.

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
            ["scope"]       = "guild",                       -- optional
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

### `scope`

Nur bei einer **Gildenaura** gesetzt (`"guild"`). Das Addon zeichnet
daraus „Gilde · <Autor>" statt „Companion · <Autor>": wer eine Aura
nicht selbst eingetragen hat, soll sehen, dass sie aus der Bibliothek
kommt und wen er zu fragen hat.

**Ein fehlendes Feld heißt „vom eigenen Schreibtisch".** Das ist
tragend: eine ältere Companion schickt es nicht, und ohne diese
Annahme trüge nach einem Addon-Update schlagartig jede Aura die
falsche Herkunft. In die andere Richtung gilt dasselbe — ein älteres
Addon liest das Feld nicht und verhält sich unverändert.

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

---

# Die gemeinsame Bibliothek (Companion ↔ Bot)

Bis 2.1.0 half eine eingetragene Aura genau einer Person: der, die sie
getippt hat. Wer sie im Raid brauchte, bekam sie weiterhin als
Zeichenkette in den Chat kopiert. Der Bot schließt das: er ist in
diesem Verbund ohnehin die Stelle, an der Gildenwissen liegt.

## Die Kennung ist überall dieselbe

`id` ist derselbe Schlüssel in Addon, Companion und Bot. Das ist eine
bewusste Entscheidung gegen einen eigenen Bot-Schlüssel: eine Aura,
die auf drei Rechnern drei Namen trägt, ist im Fehlerfall nicht zu
verfolgen — und genau dann sucht man sie.

Daraus folgt, dass zwei Leute dieselbe Kennung beanspruchen können
(gleicher Auraname → gleicher Slug). Das wird **abgewiesen und
benannt**, nicht still aufgelöst: `409` samt Namen des bisherigen
Autors. Die Companion bietet daraufhin „unter neuer Kennung
freigeben" an (`POST` mit `rename: true`). Eine automatisch
umbenannte Kennung wäre die schlechtere Antwort — sie erzeugt eine
zweite Aura, die aussieht wie die erste.

## Wer darf was

| Handlung | Wer |
|----------|-----|
| Bibliothek lesen | jeder verknüpfte Nutzer |
| Freigeben, eigene ändern/entfernen | jeder verknüpfte Nutzer |
| Fremde ändern, sperren, löschen | Raidleitung (Rolle oder Server-Admin) |

Bewusst **ohne** Rollenerfordernis für die ersten beiden Zeilen: eine
Bibliothek, die nur die Raidleitung füllen darf, füllt sich nicht.
Entschieden wird das in `weakaura_library.may_edit()` — an *einer*
Stelle, damit die HTTP-Endpunkte und die Discord-Befehle nicht zwei
Regelmengen haben.

Die Companion versteckt die Moderationsknöpfe **nicht**, sondern zeigt
sie und erklärt einen 403 — dieselbe Regel wie im Addon
(`core/access.lua`: *lock, don't hide*) und auf der Seite
Charakterzuordnung. Ein Bereich, der je nach Rolle verschwindet, lässt
sich weder erklären noch danach fragen.

## `status`: sperren statt löschen

`active` oder `hidden`. Gesperrt heißt: bleibt in der Bibliothek, wird
aber nicht mehr ausgeliefert (`GET` lässt sie weg). Das ist der
mildere Eingriff und meistens der richtige — eine gelöschte Aura ist
weg, auch der Beleg dafür, was da eigentlich schiefging.

## Der Importstring lässt sich nur neu freigeben, nicht moderieren

`PATCH` kennt Rubrik, Name, Beschreibung, Version und Sperre — den
String nicht. Er ist das Einzige, was außer dem Autor niemand
nachprüfen kann; wer ihn ersetzen will, gibt die Aura neu frei und ist
damit als Urheber der neuen Fassung sichtbar.

Aus demselben Grund kommt der String bei `weakaura_catalog` (Addon →
Companion) gar nicht erst mit: das Krieger-Paket allein sind rund
56 kB, und zum Auflisten und Ersetzen braucht ihn niemand.

## Discord: `/weintaura`

Dieselben Handlungen wie `PATCH`/`DELETE`, über dieselbe Funktion:

```
/weintaura liste       [alle]
/weintaura rubrik      kennung, rubrik
/weintaura umbenennen  kennung, name, [beschreibung]
/weintaura sperren     kennung
/weintaura freigeben   kennung
/weintaura loeschen    kennung
```

Sie sind in Discord und nicht nur in der Companion, weil der Anlass in
Discord auffällt („wo ist die Aura, die X freigegeben hat?") und die
Raidleitung zu dem Zeitpunkt dort sitzt.

## Die Bibliothek überlebt einen Neustart nur, weil sie in Discord liegt

`data/raid.db` ist beim Bot nach jedem Neustart leer — der Hoster
stellt keinen persistenten Datenträger bereit. Für die Raidanmeldung
löst das ein JSON-Anhang an der Anmeldenachricht; hier hängt derselbe
Anhang (`weakaura_library.json`, spoilered) an einer eigenen Nachricht
im WeakAura-Channel. `restore_library()` liest ihn beim Start zurück,
`save_library()` schreibt ihn nach **jeder** Änderung neu.

Ohne diese Sicherung wäre die Bibliothek nach jedem Deploy leer, und
zwar lautlos: die Endpunkte antworten weiterhin mit HTTP 200 und einer
leeren Liste, und in den Companions verschwinden die Auren einfach.

Vier Regeln daran:

- **Gesperrte Einträge sind im Snapshot mit dabei.** Ohne sie stünde
  die abgestellte Aura nach einem Neustart wieder aktiv da.
- **Der jüngere Eintrag gewinnt je Kennung** (`updated_at`). Eine
  Sicherung darf eine gerade vorgenommene Korrektur nicht
  zurückdrehen.
- **Mehrere gefundene Kopien werden nach `exported_at` sortiert**,
  nicht nach Reihenfolge im Channel — dieselbe Regel wie bei den
  Raid-Snapshots.
- **Eine misslungene Sicherung lässt die Änderung stehen.** Sie ist
  bereits in der Datenbank; sie zurückzurollen wäre schlimmer als
  eine Sicherung, die der nächste Schreibvorgang nachholt.

## Was die Companion daraus macht

`core/weakaura_guild_sync.py` holt die Bibliothek alle
`REFRESH_SECONDS` (600) ab und legt sie in `weakauras.json` ab. Vier
Regeln:

- **Ein Fehlschlag löscht nichts.** `set_guild_auras()` wird nur mit
  einer *erfolgreichen* Antwort gerufen — sonst verschwänden bei jeder
  Netzstörung alle Gildenauren aus dem Spiel.
- **Eine leere Antwort räumt sehr wohl.** HTTP 200 mit `auras: []`
  heißt „die Bibliothek ist leer", und genau so verschwindet eine
  gelöschte oder gesperrte Aura. Der Unterschied zur Zeile darüber ist
  der ganze Punkt.
- **Ohne verknüpftes Discord-Konto passiert nichts**, ohne eine
  einzige Fehlermeldung — Normalzustand für jeden, der die Companion
  ohne Discord benutzt. Wer sein Konto *trennt*, räumt über
  `clear_guild()` auf: die Auren gehören der Gilde, nicht diesem
  Rechner.
- **Bei gleicher Kennung gewinnt die eigene Fassung** (`delivery()`).
  Von speziell nach allgemein, dieselbe Ordnung, mit der das Addon
  eine zugestellte Aura über eine mitgelieferte legt. Die Seite sagt
  es an der Zeile, sonst wäre nicht zu erklären, warum die
  freigegebene Fassung ingame anders aussieht.

## Was der Bot nicht bekommt

Den Rest. Diese Endpunkte tragen WeakAuras und den Namen dessen, der
sie freigegeben hat — sonst nichts. Insbesondere geht **keine**
Nachricht der Addon-Brücke an den Bot: `weakaura_catalog` beschreibt
die eigene Installation und bleibt lokal.
