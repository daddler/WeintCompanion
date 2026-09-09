# Sim-Lauf: die Klammer um Gewichtung und Zielausrüstung

Aus **einem** Sim-Lauf kommen **zwei** Auskünfte, und sie reisen auf
zwei getrennten Wegen:

- die **Gewichtung** → `stat-weights-bridge.md`
- die **Zielausrüstung** → `target-gear-bridge.md`

Diese Datei beschreibt das Einzige, was beide gemeinsam haben: die
Kennung des Laufs, aus dem sie stammen, und den Zeitstempel der
Ausrüstung, mit der gesimmt wurde. Zwei angehängte Felder, kein neues
Format.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, Lauf und Befund | `core/sim_run.py` | WeintCompanion 3.3.0 |
| Companion, Oberfläche | `gui/pages/sim.py` | WeintCompanion 3.3.0 |
| Addon, Handshake | `modules/simexport.lua` (`SE.MatchesOpenRun`, `SE.NoteArrival`) | WeintCodex 3.2.0.0 |
| Addon, lesend | `modules/statweights.lua`, `modules/targetgear.lua` (`ParseTransfer`) | WeintCodex 3.2.0.0 |
| Addon, durchreichend | `modules/companion.lua`, `modules/sync.lua` | WeintCodex 3.2.0.0 |

## Warum es das gibt

**Vier Fehler sahen im Spiel aus wie eine korrekte Empfehlung.** Alle
vier erzeugen keine Fehlermeldung, und drei von ihnen waren gar nicht
feststellbar:

1. **Es wurde nicht optimiert.** Der Sim gibt heraus, was gerade
   eingestellt ist; wer importiert und sofort exportiert, bekommt seinen
   Ausgangszustand. Im Spiel bringt der jede Empfehlung zum Schweigen.
   *(Feststellbar seit 3.1.0 über `compare()`.)*
2. **Es fehlt eine Hälfte.** Eine Gewichtung ohne Zielzustand ist eine
   gültige Auskunft — aber wer beides wollte und nur eins bekam, sah den
   Unterschied nirgends.
3. **Die beiden gehören zu verschiedenen Läufen.** Eine Gewichtung von
   gestern neben einem Zielzustand von heute: beide für sich in Ordnung,
   zusammen eine Aussage über zwei verschiedene Ausrüstungen.
4. **Es gehört nicht zu dem Lauf, auf den das Spiel wartet.**
   Bereitstellen → simmen → ein Teil wechseln → nochmal bereitstellen →
   und dann das Ergebnis des *ersten* Laufs einfügen.

Die Kennung macht 3 sichtbar, der Zeitstempel macht 4 sichtbar. Beides
ohne einen zweiten Kanal.

## Die Kennung

```
SIM-JJJJMMTT-XXXX          z. B.  SIM-20260909-7F4A
```

Gebildet in `sim_run.make_run_id()` aus **Spezialisierung, Charakter,
Realm, Startzeitpunkt und einem Fingerabdruck des Ausgangszustands**.
Der Datumsteil ist für Menschen da (eine Rückfrage lautet „aus welchem
Lauf stammt das"), die vier Hexziffern unterscheiden.

**Sie hängt am Lauf, nicht an der Uhr.** Derselbe Charakter mit
derselben Ausrüstung zum selben gemeldeten Zeitpunkt ergibt dieselbe
Kennung — auch nach einem Neustart der App, auch beim zweiten Einfügen
desselben Ergebnisses. Ohne diese Regel wäre sie eine laufende Nummer
und könnte gar nichts korrelieren: die Gewichtung bekäme eine andere als
der Zielzustand, obwohl beide aus einem Lauf stammen.

**Ein Lauf ohne Ausgangszustand hat keine Kennung — `""`.** Eine zu
erfinden wäre schlimmer als keine: sie hinge an der Uhr dieses Rechners,
wäre bei jedem Betreten der Seite eine andere, und die Frage „gehören
diese beiden zusammen" bekäme jedes Mal ein falsches Nein. Dieselbe
Regel wie `at == -1` und `stars == 0`.

**Genau deshalb gibt es keinen dritten Speicher.** Eine `sim_runs.json`
neben `stat_weights.json` und `target_gear.json` hätte nichts gekonnt,
was diese Rechnung nicht kann — die Kennung lässt sich jederzeit aus dem
neu gelesenen Export **wieder ausrechnen**. Übrig bliebe eine dritte
Datei, die genau dann veraltet, wenn sie gebraucht wird. Die
Korrelation liegt deshalb dort, wo die Daten liegen: als ein Feld auf
den beiden Einträgen, die es ohnehin gibt.

## Der Zeitstempel (`startedAt`)

Der Zeitstempel der Ausrüstung, **mit** der gesimmt wurde — also der,
den der WowSimsExporter in seine SavedVariables geschrieben hat
(`wowsims-exporter-bridge.md`).

**Er stammt aus der Uhr des Spiels, nicht aus der des Rechners.** Das
ist seine ganze Aufgabe: `SE.NoteProvided()` merkt sich beim
*Bereitstellen* dieselbe Uhr, und `SE.MatchesOpenRun()` vergleicht
beide. Ein Wert aus der Desktop-Uhr wäre gegen `awaitingAt` bedeutungslos
— Zeitzone, Drift, andere Maschine.

`0` heisst **„nicht feststellbar"**, nicht „Sekunde 0".

## Auf dem Draht

Beide Übertragungsstrings tragen die zwei Felder **angehängt**, hinter
ihrer bisherigen Nutzlast:

```
WCIMPORT:SW:<spec>:<id>:<created>:<character>:<source>:<stat>|<wert>,…:<run>:<startedAt>
WCIMPORT:TG:<spec>:<id>:<created>:<character>:<source>:<slot>|…,…:<run>:<startedAt>
```

Beide Inbox-Nachrichten tragen sie je Satz:

```lua
{ ["id"] = "…", ["spec"] = "…", …, ["run"] = "SIM-20260909-7F4A",
  ["startedAt"] = 1788185000, … }
```

### Warum Anhängen hier gefahrlos ist — und bei zwei Umschlägen nicht war

`SW.ParseTransfer` und `TG.ParseTransfer` lesen die Felder 1 bis 6 über
**feste Positionen** und ignorieren alles dahinter, ohne zu meckern.
Genau diese Nachsicht war 2026-09 der Grund für die Vorsichtsregel bei
zwei Umschlägen in einer Zeile (`COMBINED_SINCE`): dort fiel eine ganze
**Auskunft** weg, und im Spiel sah das aus wie eine Zielausrüstung, die
es nie gab.

Hier fällt nur ihre **Herkunft** weg. Ein WeintCodex vor 3.2.0.0 liest
denselben Zielzustand und dieselbe Gewichtung wie bisher; `run` bleibt
`""`, `startedAt` bleibt `0`, und daraus wird **nichts behauptet**.

**Die Kennung geht nicht durch `clean_field()`.** Dort fällt der
Bindestrich weg, weil er *innerhalb* eines Datensatzes die Steine trennt
(`76895-0-76639`). In einem eigenen `:`-Abschnitt kann er das nicht.
`clean_run_id()` lässt deshalb `[A-Za-z0-9-]` stehen und entfernt alles
andere — `SIM 20260909 7F4A` wäre eine Kennung, die niemand
wiedererkennt.

## Der Handshake

```
INGAME   Bereitstellen und neu laden
         └─ SE.NoteProvided()          merkt sich awaitingAt = time()
            (der Stups an den Exporter lief unmittelbar davor)

COMPANION liest den Export
         └─ started_at = dessen Zeitstempel   (dieselbe Uhr!)
            run_id      = f(spec, char, realm, started_at, gear)

WOWSIMS  simmen

COMPANION Ergebnis einfügen, übernehmen, übertragen
         └─ run + startedAt reisen in beiden Umschlägen mit

INGAME   Ankunft
         └─ SE.NoteArrival({ run, startedAt, kind })
            └─ SE.MatchesOpenRun(startedAt)
```

`SE.MatchesOpenRun()` gibt **drei** Antworten, und `nil` ist nicht
`false`:

| Antwort | Bedeutung | Folge |
|---|---|---|
| `true` | mindestens so neu wie das Bereitstellen | Warten beendet, kein Satz |
| `false` | mit einer **älteren** Ausrüstung gesimmt | Warten bleibt offen, Satz |
| `nil` | kein offener Lauf, oder kein Zeitstempel dabei | Warten beendet, kein Satz |

**`AWAIT_SLACK = 120` Sekunden rückwärts.** `SE.Provide()` stupst den
Exporter an und merkt sich *danach* die Zeit; der Zeitstempel liegt also
ein bis zwei Sekunden davor. Wer ohne den Knopf auskommt (der Exporter
schreibt von selbst), liegt weiter davor.

**Ein Ergebnis aus einem älteren Lauf beendet das Warten nicht.** Der
Lauf, den der Spieler bereitgestellt hat, ist weiter offen — den Kasten
wegzuräumen und den Irrtum stehenzulassen wäre das Schlechteste von
beidem. Gesagt wird es einmal, im Chat, ohne Dialog.

**Kein Satz ist der Normalfall.** Wer bereitstellt, simmt und einfügt,
braucht keine Bestätigung dafür, dass das Erwartete eingetroffen ist.

## Die sechs Zustände eines Laufs (`sim_run.validate`)

Sechs, und keiner ist ein Unterfall eines anderen — sie führen zu sechs
verschiedenen nächsten Schritten. Ein gemeinsames „Fehler" wäre für fünf
davon der falsche Satz. Die Rangfolge steht in `_RANK`:

| Zustand | Wann | Was der Nutzer tun soll |
|---|---|---|
| `MISMATCH` | die Gewichtung **oder** der Zielzustand gehört zu einer anderen Klasse | prüfen — übernehmen darf er trotzdem |
| `STALE` | ≥ 2 Plätze **und** ≥ die Hälfte tragen ein anderes Teil | im Spiel neu bereitstellen, neu simmen |
| `INCOMPLETE` | eine der beiden Auskünfte fehlt | die andere Ausgabe aus dem Sim holen |
| `UNCHANGED` | vollständig, mindestens ein **vergleichbarer** Platz, und kein Unterschied | nachsehen: schon optimal, oder nie optimiert |
| `READY` | vollständig, und es ändert sich etwas | übertragen |
| `EMPTY` | nichts eingelesen | einfügen |

Drei Dinge passieren dabei **nicht**, und alle drei sind Absicht:

- **Nichts wird verworfen.** Auch ein Lauf mit falscher Klasse bleibt
  benutzbar — vielleicht simmt jemand für seinen Zweitcharakter. Der
  Knopf heisst dann *Trotzdem übernehmen*; gesperrt wird er nicht, denn
  ein toter Knopf beantwortet nicht, warum er tot ist.
- **Nichts wird geraten.** Fehlt der Ausgangszustand, ist `comparable`
  falsch, und die Frage „wurde überhaupt optimiert" bleibt **offen**
  statt mit „ja" beantwortet zu werden.
- **Kein Zustand verdeckt einen anderen.** `missing` und `notes` stehen
  unabhängig vom Zustand da: ein veralteter Lauf, dem auch noch die
  Gewichtung fehlt, sagt beides.

**Ein einzelnes getauschtes Teil ist kein `STALE`.** Das ist der
Normalfall — ein Drop zwischen Simmen und Einfügen —, und dafür gibt es
im Spiel den Rückfall je Platz. Den ganzen Lauf deswegen zu verwerfen
wäre die teure Antwort in die falsche Richtung. Die Zahl steht in
**beiden** Fällen als `notes`-Eintrag `foreign` daneben: wer 15 von 15
fremden Plätzen hat, will die 15 lesen, und wer 1 von 15 hat, ebenfalls.

**Ein fremder Platz zählt nicht als „kein Unterschied".** Dort ist nicht
die Rechnung eine andere, sondern die Ausrüstung — die Frage nach der
Optimierung ist gar nicht gestellt worden. `change_line()` zählt deshalb
**vergleichbare** Plätze (`checked − foreign`), und wenn keiner übrig
bleibt, sagt es genau das statt „möglicherweise ist bereits alles
optimal". Das war der teuerste der vier Fehler, die das Durchspielen des
ganzen Wegs zutage gefördert hat, und er zeigt in die falsche Richtung.

**Eine andere Spezialisierung ist ein Hinweis, eine andere Klasse ein
Missverhältnis.** Die Zweitspec mit laufender Ausrüstung zu simmen ist
der Normalfall (dieselbe Regel wie `fits_spec()` beim Weg *in* den Sim);
ein Zielzustand für eine fremde Klasse nennt dagegen
Gegenstandsnummern, die dieser Charakter nie tragen wird.

**Ein Heiler-Lauf ist ohne Zielzustand vollständig.** QE Live gibt
keinen heraus (`docs/systems/sim-pages.md`); ihn zu vermissen wäre eine
Aufforderung ins Leere. `validate(target_expected=False)`.

## Der Lauf sieht, was für ihn schon abgelegt ist

`sim_run` selbst kennt nur, was eingelesen wurde. Die Seite führt beides
zusammen (`SimPage._effective_run()`), und zwar aus einem Grund, der beim
Durchspielen aufgefallen ist:

> Wer die Gewichtung übernimmt und danach die Zielausrüstung einfügt,
> hat einen **vollständigen** Lauf — die erste Hälfte liegt nur schon im
> Speicher statt im Feld.

Ohne die Zusammenführung stünde dort „Gewichtung fehlt", obwohl sie
bereitliegt, und `next_step()` schickte in den Sim für etwas, das längst
geholt wurde.

**Zusammengeführt wird nur bei gleicher Kennung.** Ein Eintrag aus einem
anderen Lauf ist keine Hälfte dieses Laufs — er ist genau die Mischung,
vor der `mixed_note()` warnt. Ohne Kennung (ältere Ablage, von Hand
getippt) wird nichts behauptet.

Zwei Läufe, zwei Fragen, und die Seite stellt beide getrennt:

| Frage | Grundlage |
|---|---|
| Steht hier etwas? (Knopf aktiv, Befund sichtbar) | der **eingefügte** Lauf |
| Ist es vollständig? (Häkchen, nächster Schritt) | der **zusammengeführte** Lauf |

Übernommen wird nur, was eingelesen wurde — `_apply()` liest `self._run`,
nicht den zusammengeführten. Sonst würde jeder zweite Klick die schon
abgelegte Hälfte mit einem neuen Zeitstempel überschreiben.

## Diagnose

| Frage | Wo |
|---|---|
| Aus welchem Lauf stammt diese Zielausrüstung? | `/wc ziel` |
| Passt die bereitliegende Gewichtung dazu? | `/wc ziel` (rote Zeile, wenn nicht) |
| Was kam zuletzt an, und war beides dabei? | `/wc simmen pruefen`, und die Seite *Simmen* |
| Ist ein Lauf offen, und seit wann? | `/wc simmen pruefen` |
| Welche Kennung tragen die abgelegten Einträge? | Companion, *Simmen*, Schritt 4 |

## Prüfungen

- `tests/test_sim_run.py` — die sechs Zustände, die Kennung (Bestand,
  Wechsel, Fehlen), das Sammeln statt Ersetzen, die Korrelation.
- `tests/test_target_gear.py` / `tests/test_stat_weights.py` — die zwei
  angehängten Abschnitte, und dass ein Eintrag ohne sie gültig bleibt.
- `tests/test_sim_page_target.py` — dass beide Sorten sich im selben
  Lauf sammeln, ein Klick beides ablegt und zwei Läufe nebeneinander
  benannt werden.
- `.github/tests/simexport_test.lua` drüben — der Handshake samt seiner
  drei Antworten.
- `.github/tests/statweights_test.lua` / `targetgear_test.lua` drüben —
  die angehängten Abschnitte, hin und zurück.
- `.github/tests/sync_test.lua` drüben — dass die Angabe den Handshake
  erreicht, und dass bei zwei Umschlägen der Zielzustand entscheidet
  (nach einer Regel, nicht nach der Reihenfolge).
