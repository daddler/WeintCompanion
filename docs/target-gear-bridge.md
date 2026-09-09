# Zielausrüstung: Vertrag zwischen Companion und Addon

Diese Datei beschreibt, wie das **Ergebnis eines wowsims-Optimierungs-
laufs** in WeintCodex landet — auf **zwei** Wegen, die beide gebraucht
werden:

- `target_gear` — **Companion → Addon**, verschachtelte Tabelle über die
  Addon-Brücke. Gelesen beim Login bzw. nach `/reload`.
- `WCIMPORT:TG:…` — **Companion → Zwischenablage → Import-Dialog**, eine
  flache Zeichenkette. Wirkt **ohne** Neuladen.

Der Bot ist **nicht beteiligt**. Eine Ausrüstung gehört einem einzelnen
Charakter, nicht der Gilde — dieselbe Einordnung wie bei
`character_sheet` und `stat_weights`.

Das Gegenstück zu dieser Datei ist `stat-weights-bridge.md`: dort reisen
die **Gewichte**, hier das **Ergebnis**. Beide kommen aus demselben Sim
und aus demselben Eingabefeld der Seite *Charakter → Simmen*, und sie
sind trotzdem zwei verschiedene Auskünfte — siehe unten.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, lesend (drei Gestalten) | `core/target_gear.py` | WeintCompanion 3.1.0 |
| Companion, Protobuf zurücklesend | `core/wowsims_link.py` (`decode_*`) | WeintCompanion 3.1.0 |
| Companion, ablegend | `core/target_gear_store.py` | WeintCompanion 3.1.0 |
| Companion, zustellend | `core/target_gear_sync.py` | WeintCompanion 3.1.0 |
| Companion, Oberfläche | `gui/pages/sim.py` (Schritt 4) | WeintCompanion 3.1.0 |
| Addon, empfangend | `modules/companion.lua` (`INBOX_HANDLERS.target_gear`) | WeintCodex 3.0.2.0 |
| Addon, Import von Hand | `modules/sync.lua` (`TG`) | WeintCodex 3.0.2.0 |
| Addon, ablegend + zerlegend | `modules/targetgear.lua` | WeintCodex 3.0.2.0 |
| Addon, anwendend | `modules/charakter.lua` (`PlanItem`), `modules/reforge_engine.lua` (`ItemOptions`) | WeintCodex 3.0.2.0 |

## Warum es das gibt

**WeintCodex hat die Optimierung ein zweites Mal gerechnet.** Aus den
`statWeights` eines Spec-Profils leitet es ab, welcher Stein in welchen
Sockel gehört und was wohin umgeschmiedet wird. Das ist eine
vollständige Optimierung — und damit die zweite Antwort auf eine Frage,
die im Sim längst beantwortet war. Fast jede gemeldete Fehlempfehlung
bei Sockelsteinen ist von dieser Sorte: nicht „die Rechnung ist
falsch", sondern „es wird überhaupt gerechnet".

Der Weg **in** den Sim gab es schon (`wowsims-exporter-bridge.md`).
Was fehlte, war der Rückweg. Seit dieser Brücke gilt:

> **wowsims trifft die Optimierungsentscheidung. WeintCodex
> interpretiert sie, vergleicht sie mit dem Iststand und stellt sie
> verständlich dar.**

Die eigene Rechnung bleibt — als **Rückfall** für jeden Sockel und
jeden Platz, zu dem der Zielzustand nichts sagt.

## Was der Sim herausgibt — die drei Gestalten

Alle drei landen in **demselben** Eingabefeld (*Charakter → Simmen*,
Schritt 2) und werden an ihrer Gestalt erkannt, nicht daran, in welches
Feld jemand eingefügt hat.

| Gestalt | Woher | Erkennung | `source` |
|---|---|---|---|
| Adresse | *Export → Link* | `wowsims.com` im Text, oder ein reiner Base64-Rumpf ab 40 Zeichen | `wowsims_link` |
| Sim-JSON | *Export → JSON* | `player.equipment.items` | `wowsims_json` |
| Addon-Form | *Export → Addon* | `gear.items` an der Wurzel | `wowsims_addon` |

Alle drei tragen je Platz **Gegenstandsnummer, Steine, Umschmiedung und
Verzauberung** — das ist der Befund, wegen dem diese Brücke überhaupt
gebaut werden konnte. Nachgeprüft an einer echten Ausgabe
(`tests/data/wowsims_mop_output.json`, ein Blut-Todesritter):

```json
{"id":86920,"gems":[76895,76639],"reforging":161,"upgradeStep":"UpgradeStepTwo"}
```

* **Gem-IDs sind enthalten**, als Gegenstandsnummern, in
  Sockelreihenfolge.
* **Der Meta-Stein steht ganz normal in `gems`**, an der Position
  seines Sockels (beim Kopf also zuerst).
* **Reforge-Daten sind enthalten**, als der Umschmiedewert des Clients
  (113…168, `data/reforge.lua` drüben rechnet ihn aus `TABLE_BASE + n`).
  Ein Wert ausserhalb dieser 56 Paare wird **verworfen**: im Spiel würde
  daraus eine laufende Nummer im Umschmieder, die es nicht gibt.
* **Verzauberungen sind enthalten**, aber nur, wenn im Sim eine
  eingestellt war. Sie reisen mit und werden im Spiel bislang **nicht**
  ausgewertet — die bestehende Verzauberungslogik von WeintCodex
  funktioniert, und sie zu ersetzen war nicht das Problem.
* **Sockelboni stehen nicht drin.** Sie sind im Ergebnis bereits
  *verrechnet*: welche Steine der Sim gesetzt hat, sagt implizit, ob er
  den Bonus halten wollte. Das Addon liest daraus, ob der Zielzustand
  den Bonus hält (`plan.match`), statt die Abwägung noch einmal zu
  führen.

### Der eine Punkt, den keine der drei Gestalten beantwortet

**Ob wirklich ein Optimierungslauf gelaufen ist.** Der Sim schreibt
heraus, was gerade in seiner Oberfläche eingestellt ist. Wer
importiert und sofort exportiert, bekommt seinen **Ausgangszustand**
zurück — und der sähe hier aus wie ein Ergebnis.

Nachsehen lässt sich das an genau einer Stelle: neben dem, was der
WowSimsExporter als **angelegt** meldet (`core/wowsims_export.py`).
`compare()` tut das je Platz, und die Seite sagt das Ergebnis:

- Unterscheidet sich etwas → „N Ausrüstungsplätze geprüft · N
  Sockeländerungen · N Umschmiedungen — es ändert sich etwas an N
  Teilen (Kopf, …)". `SlotDiff.gem_changes` zählt dabei **Sockel**,
  nicht Teile; eine 0 im Ziel zählt nicht mit (siehe unten).
- Unterscheidet sich **nichts** → „Achtung: das ist Stück für Stück
  dasselbe, was du gerade trägst. Entweder ist bereits alles optimal —
  oder im Sim lief noch kein Optimierungslauf."

Beide Möglichkeiten stehen da, weil beide zutreffen können. Eine
Zielausrüstung, die in Wahrheit der Iststand ist, brächte im Spiel
**jede** Empfehlung zum Schweigen („alles schon richtig") — und das
wäre von einer wirklich fertigen Ausrüstung nicht zu unterscheiden.
Dieselbe Linie wie `stars == 0`.

Ein Platz, auf dem inzwischen ein **anderer** Gegenstand steckt, zählt
dabei nicht als Unterschied: dann ist nicht die Optimierung eine
andere, sondern die Ausrüstung. Das steht als eigene Zeile daneben.

## Zuordnung: über den Platz und die Position, nie über einen Namen

**Der Sim führt die Ausrüstung als Liste, und die Position ist der
Platz.** Die Reihenfolge stammt aus `proto/common.proto`
(`enum ItemSlot`); `SLOT_IDS` in `core/target_gear.py` bildet sie auf
die Plätze des Spiels ab:

| # | Sim | Platz | | # | Sim | Platz |
|---|---|---|---|---|---|---|
| 0 | Head | 1 | | 9 | Feet | 8 |
| 1 | Neck | 2 | | 10 | Finger1 | 11 |
| 2 | Shoulder | 3 | | 11 | Finger2 | 12 |
| 3 | Back | 15 | | 12 | Trinket1 | 13 |
| 4 | Chest | 5 | | 13 | Trinket2 | 14 |
| 5 | Wrist | 9 | | 14 | MainHand | 16 |
| 6 | Hands | 10 | | 15 | OffHand | 17 |
| 7 | Waist | 6 | | 16 | Ranged | 18 |
| 8 | Legs | 7 | | | | |

Daraus folgen drei Regeln, und keine davon ist Geschmack:

- **Ring 1 / Ring 2, Schmuck 1 / Schmuck 2, Haupt- / Nebenhand werden
  über den Platz getrennt.** Zwei gleiche Ringe sind zwei Ringe; über
  die Gegenstandsnummer allein wäre nicht zu entscheiden, welcher
  welche Steine bekommt.
- **Ein leerer Platz ist ein Platz.** Fällt er aus der Liste, rückt die
  Zweitwaffe in die Waffenhand. Er bleibt deshalb bis zur Zustellung
  erhalten und wird erst dort weggelassen (über einen Platz ohne
  Gegenstand sagt das Ziel nichts).
- **Die Position in `gems` ist der Sockel.** `gems[0]`, `gems[1]`,
  `gems[2]` sind keine Menge. Eine **0 zwischen** zwei Steinen bleibt
  stehen; würde sie verdichtet, rutschte der dritte Stein in den
  zweiten Sockel. Die Zählung ist dieselbe wie die der Steinfelder im
  Item-Link des Spiels, also **einschliesslich Zusatzsockel**
  (Gürtelschnalle, Schmiedekunst) — im Addon `socket.index`.

### Was eine 0 in `gems` bedeutet

**„Das Ziel sagt zu diesem Sockel nichts"** — ausdrücklich nicht „dieser
Sockel soll leer bleiben". Eine 0 entsteht auch dann, wenn im Sim
schlicht kein Stein eingestellt war, und aus ihr eine Empfehlung „nimm
deinen Stein wieder heraus" abzuleiten wäre der teure Irrtum in der
falschen Richtung. Für diesen einen Sockel rechnet das Addon dann selbst
weiter; die übrigen bleiben beim Ziel. Dieselbe Linie wie
`headroom == nil`.

Im **Draht** bleibt die 0 trotzdem stehen — sie hält die Position.

## Nachricht `target_gear` (Companion → Addon)

Verschachtelte Lua-Tabelle, geschrieben über `core/lua_table.to_lua()`:

```lua
{
    ["version"] = 1,
    ["sets"] = {
        {
            ["id"]        = "0b8b4470b25f",
            ["spec"]      = "DEATHKNIGHT_BLOOD",
            ["character"] = "Aldrin",
            ["realm"]     = "Everlook",
            ["source"]    = "wowsims_json",
            ["created"]   = 1788186037,
            ["items"] = {
                {
                    ["slot"]    = 1,
                    ["itemId"]  = 86920,
                    ["gems"]    = { 76895, 76639 },
                    ["reforge"] = 161,
                    ["enchant"] = 0,
                },
                …
            },
        },
    },
}
```

| Feld | Bedeutung |
| --- | --- |
| `id` | Kennung des Zielzustands. Hängt am **Inhalt** (Spec + belegte Plätze), nicht an der Uhrzeit |
| `spec` | Profilschlüssel wie in `data/spec_profiles.lua` (**Pflicht**) |
| `items[].slot` | Ausrüstungsplatz des Spiels (**Pflicht**) |
| `items[].itemId` | Gegenstandsnummer (**Pflicht**) — der Prüfstein, ob das Ziel noch gilt |
| `items[].gems` | Steine **in Sockelreihenfolge**, 0 = keine Angabe |
| `items[].reforge` | Umschmiedewert 113…168, 0 = ausdrücklich keine Umschmiedung |
| `items[].enchant` | Verzauberung, 0 = keine Angabe. Reist mit, wird im Spiel noch nicht ausgewertet |
| `character` / `realm` | Wem der Zielzustand gehört. Leer heisst „dem, der ihn angenommen hat" |
| `source` | Aus welcher Gestalt gelesen (siehe Tabelle oben) |
| `created` | Unix-Zeitstempel des Einlesens |
| `run` | Kennung des Sim-Laufs, `""` = keine. Vertrag: `sim-run.md` |
| `startedAt` | Zeitstempel der Ausrüstung, mit der gesimmt wurde — aus der Uhr des **Spiels**. `0` = nicht feststellbar. Vertrag: `sim-run.md` |

Ein Platz ohne Gegenstand steht **nicht** in der Nachricht.

## Zeichenkette `WCIMPORT:TG:` (Companion → Zwischenablage → Spiel)

```
WCIMPORT:TG:<spec>:<id>:<created>:<character>:<source>:
    <slot>|<itemId>|<gem1>-<gem2>-<gem3>|<reforge>|<enchant>,…
    :<run>:<startedAt>
```

Die beiden letzten Abschnitte sind **angehängt** (Companion 3.3.0,
Addon 3.2.0.0) und stehen als Einzige nicht in dieser Datei: ihr
Vertrag ist `sim-run.md`. `TG.ParseTransfer` liest die Felder 1 bis 6
über feste Positionen, ein älterer String liefert dort `""` und `0` —
und daraus wird nichts behauptet.

Abschnitte mit `:`, Datensätze mit `,`, Felder mit `|` — dieselbe Form
wie die übrigen Importe, damit im Addon kein zweiter Parser entsteht.
Die Steine eines Gegenstands hängen mit `-` aneinander, weil die drei
übrigen Zeichen vergeben sind; sie sind Ziffern, ein Bindestrich kann
darin nicht vorkommen. `clean_field()` entfernt alle vier aus jedem
freien Text (der Charaktername kommt aus dem Spiel).

Ein Gegenstand mit drei Sockeln, dessen mittlerer keine Angabe hat,
schreibt `1234-0-5678`. **Die 0 muss bleiben.**

Der Typ steht **nicht** in `IMPORT_FEATURE` des Addons: ein
Sim-Ergebnis ist nichts Gildeninternes, gleiche Entscheidung wie bei
`WA` und `SW`.

## Vier Regeln, die beide Wege teilen

- **Zugestellt wird immer die ganze Liste.** Ein gelöschter Zielzustand
  verschwindet im Spiel dadurch, dass er in der nächsten Zustellung
  fehlt — dieselbe Regel wie bei `stat_weights` und der
  WeakAura-Bibliothek.
- **Ein Zielzustand je Spezialisierung.** Ein zweiter für dieselbe Spec
  wäre eine zweite Antwort auf eine Frage, die eine hat. Ein neuer
  ersetzt den alten.
- **Was ankommt, GILT — anders als eine Gewichtung.** Das ist der eine
  Unterschied zu `stat-weights-bridge.md`, und er hat einen Grund: eine
  Gewichtung gilt für *jede* Ausrüstung und überlebt damit ihren
  Zusammenhang; eine, die sich nach einem Login von selbst geändert
  hätte, wäre von einem Fehler nicht zu unterscheiden. Ein Zielzustand
  kann das nicht — er wirkt nur dort, wo noch **genau das** Teil
  steckt, mit dem gesimmt wurde, und fällt von selbst weg, sobald das
  nicht mehr stimmt. Entschieden hat der Spieler ausserdem bereits: auf
  dem Desktop, mit dem Knopf, der die Zustellung auslöst.
- **Jede Zeile sagt, woher sie kommt.** Im Spiel steht an einer
  Sockelempfehlung aus dem Ziel „so steht es in deinem Sim-Ergebnis",
  an einer Umschmiedung „So steht es in deinem Sim-Ergebnis". Ohne
  diesen Satz wäre eine geänderte Empfehlung von einem Fehler nicht zu
  unterscheiden — das ist der Ersatz für die Bestätigungsfrage, die es
  bei den Gewichten gibt.

## Die Rangfolge im Spiel

```
1. Handauswahl des Spielers   (nur Umschmieden, RE.SetManual)
2. Zielzustand aus dem Sim    (diese Brücke)
3. eigene Rechnung            (PlanItem / der Umschmiede-Suchlauf)
```

Die Handauswahl steht **vor** dem Sim, und das ist keine Inkonsequenz:
wer im Umschmiede-Fenster „hier will ich Meisterschaft" gesagt hat, hat
das *nach* dem Simmen gesagt. Bei den Sockeln gibt es keine
Handauswahl; dort ist der Sim die oberste Instanz.

Zurück auf Stufe 3 fällt genau das, was Stufe 2 nicht abdeckt:

| Fall | Folge |
|---|---|
| Kein Zielzustand für diese Spec | alles wie bisher |
| Zielzustand gehört einem anderen Charakter | gilt nicht, mit Begründung |
| Anderer Gegenstand im Platz | dieser **Platz** rechnet selbst |
| Ziel nennt diesen Platz nicht | dieser **Platz** rechnet selbst |
| Ziel nennt weniger Sockel als das Teil hat | dieser **Sockel** rechnet selbst |
| 0 an dieser Sockelposition | dieser **Sockel** rechnet selbst |
| Umschmiedung am Teil nicht zulässig | dieser **Platz** rechnet selbst, und die Zeile sagt es |
| `/wc ziel aus` | alles wie bisher |

**Nie das ganze Teil wegen eines Sockels**, und nie die ganze Ausrüstung
wegen eines Teils.

## Toleranzregeln

- **Fehlende und zusätzliche Felder sind kein Fehler.** Streng geprüft
  wird dreierlei: ein Profilschlüssel muss dastehen, mindestens ein
  Platz mit Gegenstandsnummer, und mindestens ein Stein **oder** eine
  Umschmiedung. Das Letzte ist der Punkt: ein Zielzustand ohne beides
  sähe im Spiel aus wie „alles ist schon richtig".
- **Ein unbekannter Profilschlüssel wird nicht verworfen**, er liegt
  ab. Dieselbe Regel wie bei den Gewichten.
- **Ein Zielzustand für die Basis-Spec gilt auch für die
  `*_OFFENSIVE`-Haltung eines Tanks.** Der Sim kennt keine zwei
  Haltungen — er führt je Spec eine Seite —, und ein Zielzustand
  beschreibt Steine und Umschmiedungen, keine Spielweise.

## Diagnose

`/wc ziel` im Spiel druckt alles: was geliefert wurde, für wen es gilt,
und Platz für Platz den Iststand gegen das Ziel samt Umschmiedung.
`/wc ziel aus` schaltet die Übernahme ab (die erste Frage bei jeder
Rückmeldung zu einer Steinempfehlung), `/wc ziel an` wieder ein,
`/wc ziel weg` verwirft alles.

`/wc sockel` nennt an jeder Zeile die Quelle der Empfehlung — „AUS DEM
SIM-ZIEL", „aus der Profilliste" oder „nach Wertung". Die drei raten zu
Verschiedenem, wenn etwas nicht stimmt: beim ersten sieht man im Sim
nach, beim zweiten in `data/spec_profiles.lua`, beim dritten in den
Gewichten.

## Prüfungen

`tests/test_target_gear.py` hält die Companion-Seite fest — den
Protobuf-Rückweg gegen eine **echte** Sim-Ausgabe, die Gleichheit der
drei Gestalten, die Platzzuordnung (zwei gleiche Ringe, leerer Platz,
Loch zwischen zwei Steinen), die Verwerfung unmöglicher Umschmiedewerte
und den Vergleich Ziel gegen Ist. `tests/test_sim_page_target.py` baut
die Seite offscreen auf und prüft, dass **dasselbe** Eingabefeld beide
Textsorten auseinanderhält.

`.github/tests/targetgear_test.lua` drüben hält die andere Hälfte: die
Sockelreihenfolge, den Meta-Sockel, die Lücke im Ziel, das veraltete
Ziel, Ring 1 gegen Ring 2, die vier Umschmiede-Fälle und den
Übertragungsstring hin und zurück.

## Woher der Zielzustand kommt

Er ist die eine Hälfte eines **Sim-Laufs**; die andere ist die
Gewichtung (`stat-weights-bridge.md`). Was beide verbindet — die
Kennung, der Zeitstempel, der Handshake im Spiel und die sechs Zustände
eines Laufs — steht in `sim-run.md` und ausdrücklich nicht hier.
