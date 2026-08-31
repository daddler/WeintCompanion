# Sim-Gewichte: Vertrag zwischen Companion und Addon

Diese Datei beschreibt, wie ein Sim-Ergebnis von wowsims.com/mop in
WeintCodex landet — auf **zwei** Wegen, die beide gebraucht werden:

- `stat_weights` — **Companion → Addon**, verschachtelte Tabelle über
  die Addon-Brücke. Gelesen beim Login bzw. nach `/reload`.
- `WCIMPORT:SW:…` — **Companion → Zwischenablage → Import-Dialog**, eine
  flache Zeichenkette. Wirkt **ohne** Neuladen.

Der Bot ist **nicht beteiligt**. Eine Gewichtung ist das Ergebnis eines
Sims für einen einzelnen Charakter, kein Gildenwissen — dieselbe
Einordnung wie bei `character_sheet` und `academy`.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, lesend (Sim-Ausgabe) | `core/stat_weights.py` | WeintCompanion 2.5.0 |
| Companion, ablegend | `core/stat_weights_store.py` | WeintCompanion 2.5.0 |
| Companion, zustellend | `core/stat_weights_sync.py` | WeintCompanion 2.5.0 |
| Companion, Oberfläche | `gui/pages/sim.py` | WeintCompanion 2.5.0 |
| Addon, empfangend | `modules/companion.lua` (`INBOX_HANDLERS.stat_weights`) | WeintCodex 2.8.0.0 |
| Addon, Import von Hand | `modules/sync.lua` (`SW`) | WeintCodex 2.8.0.0 |
| Addon, ablegend + zerlegend | `modules/statweights.lua` | WeintCodex 2.8.0.0 |
| Addon, anzeigend | `modules/charakter.lua` (*Priorisierung*) | WeintCodex 2.8.0.0 |

## Warum es zwei Wege gibt

WoW liest seine SavedVariables zur Laufzeit **nicht** erneut. Die
Addon-Brücke kommt deshalb frühestens beim nächsten Laden an — und wer
gerade im Raid steht, lädt nicht neu. Der `WCIMPORT`-String ist der
zweite Weg: er wird im Spiel eingefügt und wirkt sofort.

Beide tragen dieselben Angaben und landen in derselben Ablage. Was sie
unterscheidet, ist ausschliesslich der Zeitpunkt.

## Wer rechnet was

**Der Sim rechnet, die Companion liest, das Addon entscheidet.** Diese
Aufteilung ist die Fortsetzung der schon bestehenden:

- Die **Companion simmt nicht**. Ein Sim wäre eine eigene
  Spielsimulation; einer, der nur so aussieht, wäre schlimmer als
  keiner, weil seine Zahlen aussehen wie echte. Sie öffnet die Seite der
  richtigen Spezialisierung und nimmt das Ergebnis entgegen.
- Das **Addon rechnet die Gewichte nicht nach**. Es bekommt sie fertig
  auf seiner eigenen Skala (siehe unten).
- Die **Grenzen** (7,5 % Treffer, 15 % Waffenkunde) reisen **nicht**
  mit. Eine Grenze ist eine Aussage über das Spiel und gilt für alle
  dieser Spezialisierung; sie steht in `data/spec_profiles.lua`. Die
  Companion **nennt** die Grenzen der Sim-Ausgabe und wendet sie nicht
  an — weicht der Sim ab, ist das eine Datenfrage für einen Menschen.
  Dasselbe gilt für die **Schwellen** (`breakpointLimits`): die
  Tempo-Treppe rechnet das Addon aus Laufzeit und Grundtickabstand
  selbst aus, eine abgeschriebene Wunschzahl gilt immer nur für eine
  Ausrüstungsstufe. Genannt werden sie trotzdem — ein Block, den
  niemand liest, fällt sonst still unter den Tisch.
- **Was in der Liste fehlt, bekommt seinen eigenen Satz** (seit 2.5.1).
  Vier Fälle, vier Antworten: mit null gewichtet, hier nicht
  verwertbar (Angriffskraft, Waffenschaden — kein Stein, keine
  Verzauberung, keine Umschmiedung bewegt sie), nicht erkannt, zu klein
  für die Skala. Bis dahin stand alles unter „kennt WeintCodex nicht",
  und das war für den häufigsten Fall unwahr.

## Die Skala

Sims geben Gewichte relativ heraus (Primärwert 1.0, alles andere
darunter). Die Spec-Profile führen denselben Gedanken mit **100** für
den grössten Wert, und die Eingabefelder im Spiel nehmen ganze Zahlen
von 0 bis 999.

`core/stat_weights.normalize()` rechnet deshalb auf „grösstes Gewicht =
100" um. Das ist ein **Maßstabswechsel und keine Wertung**: die
Verhältnisse bleiben, und alle drei Seiten im Spiel (Sockel,
Verzauberungen, Umschmieden) vergleichen Gewichte ohnehin nur
untereinander. Negative Gewichte werden 0 und **benannt** — die Skala
des Addons kennt kein „meiden", nur „egal".

Übertragen werden immer die **skalierten ganzen Zahlen**, nie die rohen
Sim-Werte: sonst gäbe es zwei Stellen, die skalieren, und die liefen
irgendwann auseinander.

## Nachricht `stat_weights` (Companion → Addon)

Verschachtelte Lua-Tabelle, geschrieben über `core/lua_table.to_lua()`:

```lua
{
    ["version"] = 1,
    ["sets"] = {
        {
            ["id"]        = "84474e371e1f",
            ["spec"]      = "DEATHKNIGHT_BLOOD",
            ["weights"]   = { ["strength"] = 56, ["hit"] = 100, … },
            ["character"] = "Aldrin",
            ["realm"]     = "Everlook",
            ["source"]    = "sim",
            ["created"]   = 1788186037,
        },
        …
    },
}
```

| Feld | Bedeutung |
|------|-----------|
| `id` | Kennung des Vorschlags. Hängt am **Inhalt** (Spec + Gewichte), nicht an der Uhrzeit |
| `spec` | Profilschlüssel wie in `data/spec_profiles.lua` (**Pflicht**) |
| `weights` | Wertschlüssel → ganze Zahl 1…999 (**Pflicht**, mindestens einer) |
| `character` / `realm` | Nur zur Anzeige („aus dem Sim vom … für Aldrin") |
| `source` | `sim` oder `pairs` — woher die Zahlen gelesen wurden |
| `created` | Unix-Zeitstempel des Einlesens |

Die zwölf Wertschlüssel: `strength`, `agility`, `intellect`, `stamina`,
`spirit`, `hit`, `expertise`, `crit`, `haste`, `mastery`, `dodge`,
`parry`.

## Zeichenkette `WCIMPORT:SW:` (Companion → Zwischenablage → Spiel)

```
WCIMPORT:SW:<spec>:<id>:<created>:<character>:<source>:<stat>|<wert>,<stat>|<wert>,…
```

Abschnitte mit `:`, Datensätze mit `,`, Felder mit `|` — dieselbe Form
wie die fünf übrigen Importe, damit im Addon kein zweiter Parser
entsteht. Alles, was diese drei Zeichen in einem Namen zerlegen könnte,
wird beim Bauen ersetzt (`clean_field()`), denn der Charaktername kommt
aus dem Spiel.

Der Typ steht **nicht** in `IMPORT_FEATURE` des Addons: eine Gewichtung
ist nichts Gildeninternes, gleiche Entscheidung wie beim Typ `WA`.

## Vier Regeln, die beide Wege teilen

- **Zugestellt wird immer die ganze Liste.** Eine gelöschte Gewichtung
  verschwindet im Spiel dadurch, dass sie in der nächsten Zustellung
  fehlt — eine Einzelnachricht könnte „es gibt mich nicht mehr" gar
  nicht ausdrücken, weil das Addon seine Inbox bei jedem Login leert.
  Der Handler dort räumt entsprechend weg, was nicht mehr geliefert
  wird.
- **Was ankommt, ist ein Vorschlag und keine Einstellung.** Er füllt die
  Felder auf *Charakter → Priorisierung* und wird erst auf Klick
  wirksam. Eine Gewichtung, die sich nach einem Login von selbst
  geändert hätte, wäre von einem Fehler nicht zu unterscheiden: die
  Steinempfehlungen sähen anders aus als gestern, und niemand wüsste
  warum.
- **Erledigt bleibt erledigt.** Das Addon merkt sich je Spec die
  Kennung des zuletzt übernommenen *oder* verworfenen Vorschlags
  (`SavedData.statWeights.seen`). Ohne dieses Gedächtnis stünde
  derselbe Vorschlag nach jedem Login wieder da, denn die Companion
  schickt bei jedem Takt dieselbe Liste. Weil die Kennung am Inhalt
  hängt, ist dieselbe Gewichtung derselbe Vorschlag und eine geänderte
  ein neuer.
- **Von Hand eingefügt wird immer angeboten.** Der `WCIMPORT`-Weg
  übergeht das Gedächtnis: wer den String selbst einsetzt, hat ihn
  gerade angefasst, und „kenne ich schon, passiert nichts" wäre dort ein
  toter Knopf.

## Toleranzregeln

Beide Seiten dürfen sich unabhängig aktualisieren, deshalb:

- **Fehlende und zusätzliche Felder sind kein Fehler.** Streng geprüft
  werden nur zwei Dinge: ein Profilschlüssel muss dastehen (sonst liesse
  sich die Gewichtung keinem Profil zuordnen), und mindestens ein
  Gewicht muss grösser null sein (sonst hätte sie nichts zu sagen).
- **Ein unbekannter Profilschlüssel wird nicht verworfen.** Das Addon
  legt den Vorschlag ab; gesehen wird er, sobald es das Profil kennt.
  Er ist ein Vorschlag für später und kein Fehler.
- **Ein unbekannter Wertschlüssel fällt weg**, der Rest gilt. Additiv
  wie überall: eine fehlende Zuordnung kostet einen Wert, sie erfindet
  keinen.

## Wohin der Knopf führt

`core/stat_weights.SPECS` ordnet jedem der 34 Profile (plus den fünf
`*_OFFENSIVE`-Varianten der Tanks) seine Seite im Sim zu —
`https://www.wowsims.com/mop/<klasse>/<spec>/`.

Die Zuordnung ist eine **Tabelle** und wird nicht aus dem
Profilschlüssel abgeleitet: `HUNTER_BEASTMASTERY` hiesse abgeleitet
`beastmastery` und heisst dort `beast_mastery`, `DEATHKNIGHT` heisst
`death_knight`. Eine Ableitung, die für zwei von 34 Einträgen daneben
greift, führt genau dort ins Leere — und ein toter Knopf ist von einer
nicht simmbaren Spezialisierung nicht zu unterscheiden. Ein unbekannter
Schlüssel wird deshalb nicht geraten (`sim_url()` antwortet `None`).

Die fünf `*_OFFENSIVE`-Profile zeigen auf die Seite ihrer Basis-Spec:
der Sim kennt keine zwei Haltungen, die Gewichte dieses Profils sind
aber eigene.

## Prüfungen

`tests/test_stat_weights.py` hält die Companion-Seite fest — die
Positionen der Sim-Ausgabe (gegen eine **echte** Ausgabe unter
`tests/data/`, nicht gegen ein nachgebautes Beispiel), das Komma
zwischen Ziffern, die Skalierung, die Kennung und die Form des
Übertragungsstrings.

`.github/tests/statweights_test.lua` drüben hält die andere Hälfte: es
zerlegt genau den String, den `build_transfer()` erzeugt, und prüft das
Hinlegen, das Erledigen und die Regel, dass ein Vorschlag **nichts**
speichert.

Beide Seiten prüfen ausserdem dieselbe Sim-Ausgabe gegen dieselben
erwarteten Zahlen (Treffer 100, Stärke 56, Waffenkunde 85). Laufen die
zwei Leser auseinander, widersprechen sich Spiel und Desktop bei einer
Frage, die nur eine Antwort hat.
