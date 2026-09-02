# Die Ausrüstung in den Sim: Vertrag mit dem WowSimsExporter

Diese Datei beschreibt den Weg **ins** Sim — das Gegenstück zu
`docs/stat-weights-bridge.md`, das den Weg zurück beschreibt.

Beteiligt sind drei Programme, und die Companion ist das mittlere:

1. **WowSimsExporter** (fremdes Addon, im Spiel) schreibt die eigene
   Ausrüstung als JSON in seine SavedVariables.
2. **WeintCompanion** liest diese Datei und baut daraus die Adresse,
   unter der [wowsims.com/mop](https://www.wowsims.com/mop/) mit
   genau dieser Ausrüstung aufgeht.
3. **WeintCodex** hat damit nichts zu tun — ausser dass es den
   Augenblick liefert, in dem WoW seine Daten überhaupt herausschreibt
   (*Charakter → Simmen*, siehe `modules/simexport.lua` drüben).

Der Bot ist **nicht beteiligt**. Eine Ausrüstung ist die eines
einzelnen Charakters, kein Gildenwissen — dieselbe Einordnung wie bei
`character_sheet` und `stat_weights`.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, Datei findend und lesend | `addon/wse_reader.py` | WeintCompanion 2.6.0 |
| Companion, Export prüfend und zuordnend | `core/wowsims_export.py` | WeintCompanion 2.6.0 |
| Companion, Adresse bauend | `core/wowsims_link.py` | WeintCompanion 2.6.0 |
| Companion, Oberfläche | `gui/pages/sim.py` | WeintCompanion 2.6.0 |
| Addon, bereitstellend | `modules/simexport.lua` | WeintCodex 2.9.0.0 |
| Fremdes Addon | WowSimsExporter | v3.2.4 (Interface 50504) |

## Warum es überhaupt einen Knopf im Spiel braucht

**WoW schreibt seine SavedVariables nur beim Neuladen und beim
Ausloggen.** Was gerade angelegt ist, steht also noch nirgends, wo ein
zweites Programm es sehen könnte. Auslösen kann das Neuladen nur der
Spieler — deshalb die Seite *Charakter → Simmen*: sie sagt, was der
Desktop gerade sieht, ob das noch stimmt, und macht das Neuladen zu
einem Knopf.

Der Exporter selbst schreibt von sich aus, sobald sich Ausrüstung,
Talente oder Glyphen ändern (`autoSaveEnabled`, ab Werk an). Der Knopf
stösst ihn zusätzlich an, aber das ist die Zugabe — der eigentliche
Zweck ist das Neuladen.

## Woher die Datei kommt

```
<WoW>/WTF/Account/<Konto>/SavedVariables/WowSimsExporter.lua
```

Der Dateiname folgt dem **Addon-Ordner**, nicht dem Variablennamen. In
der Datei steht `WSEDB`, über AceDB gegliedert:

```lua
WSEDB = {
	["profileKeys"] = { ["Njiah - Ook Ook"] = "Default", },
	["profiles"] = {
		["Default"] = {
			["autoSaveEnabled"] = true,
			["savedCharacters"] = {
				{
					["timestamp"] = 1787000000,
					["dateString"] = "2026-08-31 19:04:12",
					["name"] = "Njiah-Ook Ook",
					["data"] = "{\"version\":\"v3.2.4\", … }",
				}, -- [1]
			},
		},
	},
}
```

Gelesen wird in **allen** Profilen und in **allen** Konten, und der
neueste Eintrag gewinnt. Die Vorgabe von AceDB ist `Default`, aber wer
sich je ein eigenes Profil angelegt hat, hat mehrere — und dann wäre
ausgerechnet die Vorgabe die veraltete.

`name` trägt den Realm **mit** Leerzeichen (`GetRealmName()`), das JSON
darin **ohne** (`UnitFullName()`). Verglichen wird deshalb über das
JSON, nicht über den Eintragsnamen.

## Was in `data` steht

Ein JSON-Objekt. Für uns tragend sind:

| Feld | Bedeutung |
|------|-----------|
| `version` | Fassung des Exporter-Addons |
| `name`, `realm` | Charakter (Realm ohne Leerzeichen) |
| `class` | englisch, klein: `deathknight`, `mage`, … |
| `spec` | `blood`, `marksman`, `disc`, … — **nicht** immer die volle Schreibweise |
| `level` | gesimmt wird ab 90 |
| `talents` | sechs Ziffern |
| `professions[]` | `{ name, level }` |
| `glyphs.major[]`, `.minor[]` | `{ spellID }` — **Zauber**-Nummern |
| `gear.items[]` | 17 Plätze, ein leerer Platz steht als `null` |

Ein Ausrüstungsplatz trägt `id`, `enchant`, `gems[]`, `reforging`,
`random_suffix`, `upgrade_step`, `tinker`.

**Ein leerer Platz ist ein Platz.** Der Sim vergibt die Plätze der
Reihe nach; fällt das `null` heraus, rückt die Zweitwaffe in die
Waffenhand. `item_from_payload()` macht daraus einen leeren `SimItem`,
und `encode_equipment()` schreibt ihn als leere Nachricht mit.

## Wie die Adresse aussieht

```
https://www.wowsims.com/mop/<klasse>/<spec>/?i=g#<base64(deflate(protobuf))>
```

* Der Pfad kommt aus `core/stat_weights.sim_url()` — dieselbe Tabelle,
  die der Knopf *Nur die Seite* benutzt. Zwei Zuordnungen für dieselbe
  Frage liefen irgendwann auseinander.
* `?i=g` sagt dem Sim, **welche Bereiche** der Lieferung gelten sollen.
  `g` ist *Gear*. Der Sim nennt das „partial link import" und mischt
  die Lieferung in das, was dort schon eingestellt ist.
* Hinter dem `#` steht eine `IndividualSimSettings`-Nachricht
  (Protobuf), mit Deflate im zlib-Rahmen gepackt und Base64
  geschrieben. Der Sim liest sie mit `pako.inflate`.

### Warum nur die Ausrüstung

Der Sim **räumt jeden Bereich vollständig ab**, den die Adresse
benennt. Talente und Glyphen liegen bei ihm in *einem* Bereich, und
Glyphen führt er als **Gegenstands**-Nummern, während der Exporter
**Zauber**-Nummern meldet; diese Übersetzung kennt nur der Sim selbst.
Den Bereich mitzuschicken hiesse also: Talente kommen an, Glyphen sind
weg — lautlos, denn eine leere Glyphenleiste sieht aus wie eine
Einstellung.

**Ein Bereich, den wir nicht vollständig füllen können, wird nicht
geschickt.** Dieselbe Linie wie `stars == 0`.

Für das ganze Bild gibt es den zweiten Weg, und die Seite nennt ihn:
*Export kopieren* legt den JSON-Text in die Zwischenablage, im Sim
unter *Import → Addon* einfügen. Dort löst der Sim die Glyphen selbst
auf und übernimmt auch Volk und Berufe.

### Die Feldnummern

Ein Protobuf trägt keine Feldnamen. Alle Nummern stehen als benannte
Konstanten in `core/wowsims_link.py`, mit der Zeile aus dem
Sim-Repository daneben, aus der sie stammen — abgeschrieben wird
nicht, belegt wird:

```
proto/common.proto   ItemSpec { id=2, enchant=3, gems=4, reforging=5,
                                random_suffix=6, upgrade_step=7, tinker=9 }
                     EquipmentSpec { items=1 }
proto/api.proto      Player { equipment=3, api_version=54 }
proto/ui.proto       IndividualSimSettings { player=3, api_version=15 }
proto/common.proto   ProtoVersion: current_version_number = 3
```

`API_VERSION` ist die Fassung, in deren **Form** wir schreiben. Sie zu
hoch anzugeben wäre der stille Fehler: der Sim überspränge dann seine
eigenen Umbauten und läse alte Zahlen als neue.

`tests/test_wowsims_link.py` baut die Nachricht aus einer echten
Sim-Ausgabe und liest sie mit einem **eigenen** Decoder zurück. Ein
Encoder, der sich selbst bestätigt, beweist nichts.

## Was die Seite sagt, wenn nichts da ist

Vier Gründe, vier Sätze — drei davon verlangen etwas völlig anderes:

| Grund | Antwort |
|-------|---------|
| `NO_WOW` | WoW wurde noch nicht gefunden |
| `NO_ADDON` | Der WowSimsExporter ist nicht installiert (mit Adresse) |
| `NO_EXPORT` | Installiert, aber noch nichts gemeldet — im Spiel bereitstellen |
| `FOUND`, aber leer | Die Meldung enthält keine Ausrüstung (mit Grund) |

Dazu der fünfte Fall, der keiner ist: **gefunden, aber eine andere
Klasse.** Gemeldet wird immer der zuletzt gespielte Charakter, und die
Zweitspec *derselben* Klasse darf mitsimmen — die Rüstung ist
dieselbe. Eine fremde Klasse nicht: der Sim führt je Klasse eine
eigene Seite, und Platten auf einem Magier wären keine Auskunft.

## Was nicht passiert

* **In fremde Daten wird nie geschrieben.** Weder die Companion noch
  WeintCodex fassen `WSEDB` schreibend an.
* **WeintCodex zerlegt den Export nicht.** Es liest daraus nur Name und
  Zeitstempel, um zu sagen, ob der Desktop den aktuellen Stand sieht.
* **Die Companion simmt nicht.** Sie übernimmt den Weg, nicht die
  Rechnung — dieselbe Entscheidung wie in `core/stat_weights.py`.
