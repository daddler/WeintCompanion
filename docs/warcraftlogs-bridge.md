# WarcraftLogs-Brücke: Vertrag zwischen Bot und Companion

Diese Datei beschreibt den Endpunkt, den der **WeintCodex Bot**
bereitstellen muss, damit die Companion-App den laufenden
WarcraftLogs-Livelog als Raid-Datenquelle nutzen kann.

## Stand

**Alle fünf Endpunkte gibt es jetzt** (`services/warcraftlogs.py`,
`services/warcraftlogs_timeline.py`, Routen in
`services/sync_server.py`). Der fünfte, `/timeline`, war der Grund,
warum der Wiedergabe-Knopf in WeintTV ausnahmslos „Für diesen Pull
liefert der Bot keine Zeitleiste" meldete: die Route existierte nicht,
und ein 404 ist im Vertrag genau diese Meldung.

Grundlage der ersten vier sind **Summen**: Schaden, Heilung,
erhaltener Schaden, Tode. Dazu drei bekannte Lücken:

- `consumables[].missing` bleibt immer leer (die Buff-Tabelle liefert
  nur Gesamtzahlen, keine Spielerliste).
- `mechanics[]` enthält genau eine handverlesene Regel (Immerseus).
- `fight` sendet weder `battle_res_charges`/`battle_res_max` noch
  `heroism_remaining`.

### Warum die v2-Felder leer ankamen

Ein erster Teil von v2 war im Bot umgesetzt, lieferte aber in der
Praxis nichts. Zwei Ursachen, beide inzwischen behoben — sie sind hier
festgehalten, weil sie sich bei jeder Erweiterung wiederholen können:

- **Die Sprache.** Cooldowns wurden über ihren **englischen Namen**
  erkannt (`"Tranquility"`, `"Rallying Cry"`). WarcraftLogs liefert
  Fähigkeitsnamen aber in der Sprache des Clients, der den Bericht
  hochgeladen hat — bei einer deutschen Gilde steht dort „Seelenruhe"
  und „Sammelschrei", und kein einziger Vergleich hat gepasst.
  `raid_cooldowns`, `heal_cooldowns` und `players[].cooldowns` kamen
  deshalb dauerhaft leer an, ohne dass irgendwo ein Fehler auftauchte.
  Derselbe Fehler steckte in der Heldentum-Erkennung und im
  `"Flask of"`-Präfix der Verbrauchsgüter.

  Jetzt erkennt `services/warcraftlogs_spells.py` jede Fähigkeit über
  **drei unabhängige Wege** — Spell-ID, englischer Name, deutscher
  Name —, und einer genügt. Die drei sind bewusst additiv: eine falsch
  erinnerte ID macht den Eintrag nicht kaputt, solange ein Name passt.
  Ohne Zugriff auf die echte API ist das die einzige ehrliche Antwort
  auf „ungetestet".

- **Die Tabellenform.** `players[].dots`/`hots` lasen `entries` aus der
  Buffs-/Debuffs-Tabelle. Die antwortet aber mit `auras` (eine Liste je
  Fähigkeit, nicht je Spieler), also kam immer `{}` heraus — in der
  Oberfläche nicht von „der Spieler hat keine DoTs" zu unterscheiden.
  Gelesen werden jetzt **beide** Formen; die eigentliche Zuordnung
  „wer hat den DoT gelegt" kommt aus rohen `events(dataType:
  Debuffs/Buffs)`, weil nur die eine `sourceID` haben.

Dazu zwei kleinere Ursachen derselben Art: alle Ereignisströme hingen
in **einem** `gather()` mit **einem** `try/except` — ein einziger
unbekannter `dataType` ließ damit auch die intakten Ströme
verschwinden (jetzt pro Strom abgesichert); und `events()` lief mit
der Voreinstellung von 300 Ereignissen je Seite, viel zu wenig für
einen 25-Mann-Kampf, sodass spät gezündete Cooldowns schlicht nicht
mehr in der Antwort waren.

### Und warum sie danach *immer noch* leer ankamen

Nach all dem meldete die Praxis unverändert „keine DoTs, keine eigenen
Buffs, keine Cooldown-Nutzung, keine Unterbrechungen". Drei weitere
Ursachen, alle vom selben Schlag — jede erzeugt ein leeres Feld, und
ein leeres Feld ist in der Oberfläche nicht von „hat der Spieler eben
nicht gemacht" zu unterscheiden:

- **Der Live-Endpunkt hat die Aura-Ströme gar nicht geladen.**
  `LIVE_EVENT_TYPES` enthielt nur `Casts`, `Interrupts` und `Dispels`.
  Weggelassen waren `Debuffs`/`Buffs` aus einem guten Grund (es sind
  die größten Ströme, und `/live` wird alle 15 s je Zuschauer
  abgefragt) — nur eben mit der Folge, dass `players[].dots`/`hots`
  live **strukturell** leer waren, unabhängig von jedem Katalog. Beide
  kommen jetzt mit, aber **serverseitig gefiltert**: die
  `filterExpression` schränkt sie auf die Spell-IDs des Aurenkatalogs
  ein, typisch ein bis zwei Prozent des Rohstroms. Das Archiv lädt
  weiterhin ungefiltert — dort zählt Vollständigkeit, und eine
  unbekannte Aura soll im Diagnose-Log auftauchen statt vorher
  weggeschnitten zu werden.

- **`events(dataType: Debuffs)` fragte die falsche Seite des Kampfes
  ab.** Ohne `hostilityType` liefert WarcraftLogs die
  Schwächungszauber auf **Freundlichen** — also das, was der Boss auf
  den Raid legt. Die DoTs, um die es geht, liegen auf dem Gegner. Die
  Debuffs-*Tabelle* im selben Modul fragte seit jeher korrekt mit
  `hostilityType: Enemies`; nur der Ereignisweg tat es nicht.

- **`players[].buffs` hat der Bot nie gebaut.** Der Vertrag kennt drei
  Uptime-Listen, geliefert wurden zwei. Es fehlte schlicht die
  Grundlage: ohne einen Katalog, der weiß, *welche* Aura ein Selbstbuff
  ist, lässt sich der Buff-Strom nicht aufteilen — `sourceID ==
  targetID` allein würde jeden Klassenbuff, jedes Trinket-Proc und
  jedes Essen mitzählen. Den Katalog gibt es jetzt
  (`services/warcraftlogs_auras.py`, gleiche Drei-Wege-Erkennung wie
  bei den Cooldowns); für die aktive Schadensminderung der Tanks war
  das die einzige fehlende Zutat.

### Sprache: warum die Oberfläche gemischt aussah

„Viele Fähigkeiten auf Englisch, einige auf Deutsch" hatte eine
einfache Ursache: die beiden Wege in dieselbe Oberfläche haben
verschieden übersetzt. Auren kamen als **Rohname aus dem Bericht**
(bei einer deutschen Gilde also deutsch), Cooldowns als **englischer
Katalogschlüssel** — „Flammenschock" und „Rallying Cry" nebeneinander.

Der Bot liefert jetzt durchgehend den **deutschen** Anzeigenamen
(`name`) und behält den englischen Katalogschlüssel daneben als `key`.

Wichtiger noch: **jede Fähigkeitszeile trägt jetzt ihre `spell_id`** —
`dots`, `hots`, `buffs`, `cooldowns`, `raid_cooldowns`,
`heal_cooldowns`, `interrupts`, `dispels`. Damit erkennt die Companion
über die ID statt über den Namen, und die beiden Repos dürfen sich
beim deutschen Namen unterscheiden, ohne dass eine Zeile unerkannt
liegen bleibt. Das war kein theoretisches Risiko: ein Abgleich der
beiden Kataloge fand **35 Spell-IDs mit verschiedenen deutschen
Namen** (Zerfleischen/Hauen, Aufstieg/Aszendenz, Seelenruhe/
Gelassenheit …). Über den Namen gematcht wäre jede davon eine
dauerhaft unerkannte Zeile gewesen.

### Speicher: warum der Bot bei manchen Bossen abstürzte

Der Zielhost hat **0,15 vCPU und 0,15 GB** für den ganzen Prozess;
allein die Importe (discord.py, FastAPI, uvicorn, httpx, aiosqlite)
belegen davon rund 63 MB. Die Brücke lud ihre Ereignisströme
**gleichzeitig und vollständig** in Listen — bei der Zeitleiste acht
Stück. Ein 25-Mann-Pull von sechs Minuten kommt auf grob 180 000
Ereignisse; gemessen sind das ~63 MB allein für die Listen, und damit
war der Prozess weg. Genau das erklärt „einige Bosse kann ich
abfragen, bei anderen stürzt der Bot ab": es hing an Länge und Größe
des Pulls, nicht am Boss.

Die Ströme werden jetzt **nacheinander geladen und Seite für Seite
gefaltet** (`_iter_event_pages` + die Falter in `services/
warcraftlogs.py`, `TimelineFold` in `services/
warcraftlogs_timeline.py`). Was bleibt, sind Zähler; der Spitzenbedarf
hängt an der Seitengröße statt an der Kampflänge. Derselbe Testfall:
**62,8 MB → 2,2 MB** (Faktor 28). Dazu ein wiederverwendeter
`httpx.AsyncClient` statt eines neuen je Abfrage — bei 0,15 vCPU ist
ein TLS-Handschlag je GraphQL-Aufruf ein spürbarer Posten.

Zwei Rechnungen mussten dafür umgestellt werden, und beide sind es
wert, gemerkt zu werden:

- Die **Vereinigung der Aura-Fenster** wird fortlaufend gebildet, ohne
  die Fenster aufzuheben. Das geht, weil Ereignisse zeitlich geordnet
  ankommen: Fenster schließen in der Reihenfolge ihres *Endes*, und
  dann genügt je Fähigkeit ein „bis hierher schon abgedeckt"-Zeitpunkt.
- Die **Bosserkennung der Zeitleiste** brauchte einen zweiten Durchgang
  über den Schadensstrom, um erst die Zielsummen zu bilden. Jetzt wird
  der Verlauf je Gegner mitgeführt (begrenzt) und der Boss am Ende
  ausgewählt.

### Was jetzt geliefert wird

`players[].dots`/`hots`/**`buffs`** (aus rohen Buff-/Debuff-Ereignissen,
Uptime als Vereinigung der aktiven Fenster, nie über 100 %) — **in Live
und Archiv**, nicht mehr nur im Archiv. `players[].cooldowns`
(Zeitpunkte aus `events(dataType: Casts)`, über die Spell-ID erkannt),
`players[].movement_units` (Summe der Abstände zwischen
aufeinanderfolgenden Positionsangaben, auf eine Probe je Spieler und
Sekunde ausgedünnt), die top-level `interrupts[]`/`dispels[]`, sowie
der komplette `/timeline`-Endpunkt.

Jede dieser Zeilen trägt ihre `spell_id` und einen deutschen
Anzeigenamen.

Weiterhin offen (noch nicht im Bot umgesetzt): `active_time`/`casts`
im Einzel-Fight (in der Zeitleiste gibt es sie), `resurrects[]`,
`battle_res_charges`/`battle_res_max`/`heroism_remaining`, sowie die
vollständige `mechanics[]`-Neufassung für weitere Bosse. Jedes
fehlende Feld degradiert weiterhin sauber zu „keine Daten"
(Companion-seitig getestet).

Ein Diagnose-Log in `get_live_report`, `get_report_fight` und
`get_report_timeline` zeigt bei jedem Abruf die rohen Ereigniszahlen
und Beispielwerte im Bot-Terminal. Die Zahlen beantworten die Frage,
die zweimal geraten werden musste: **null Rohereignisse** heißt
„WarcraftLogs hat nichts geliefert", **Zahl bei den Rohereignissen und
trotzdem leeres Feld** heißt „der Katalog kennt die Fähigkeit nicht" —
zwei völlig verschiedene Baustellen. Der Archiv-Log listet dazu die
nicht erkannten Auren nach Häufigkeit; das ist der Weg, über den eine
Lücke in `services/warcraftlogs_auras.py` auffällt, bevor sie als
fehlende Zeile in der App auffällt.

---

## Warum der Umweg über den Bot

Die Companion-App spricht bewusst **nicht** selbst mit WarcraftLogs:

- Die API-Zugangsdaten liegen an einer Stelle statt auf
  fünfundzwanzig Spielerrechnern.
- Alle Anfragen teilen sich ein gemeinsames Punktekontingent, statt
  dass jedes Raidmitglied ein eigenes verbraucht.
- Niemand muss eine eigene WarcraftLogs-Anwendung registrieren.
- Der Bot sieht den Discord-Webhook, mit dem der Livelog-Uploader den
  Bericht meldet — er kennt den Report-Code also ohnehin als Erster.

---

## Der Endpunkt

```
GET /companion/warcraftlogs/live
Authorization: Bearer <companion_token>
```

Das `companion_token` ist dasselbe, das der Bot beim OAuth-Austausch
(`/companion/auth/exchange`) ausstellt und das bereits
`/companion/characters` und `/companion/raid-roster`
authentifiziert. Es wird in `discord_account.json` gespeichert; die
Companion-App sendet nie ein echtes Discord-OAuth-Token.

Aufgerufen wird der Endpunkt alle **15 Sekunden**, aber nur solange
WeintTV oder die WeintAcademy tatsächlich geöffnet sind (der
`RaidDataService` zählt Abonnenten). Ein Raidabend erzeugt damit
größenordnungsmäßig ein paar hundert Anfragen pro aktivem Nutzer.

### Statuscodes

| Code | Bedeutung | Verhalten der Companion-App |
|------|-----------|------------------------------|
| `200` | Antwort mit `status: "ok"` oder `status: "idle"` | siehe unten |
| `204` | Kein laufender Bericht | „Zurzeit läuft kein Livelog." |
| `401` | Token unbekannt/abgelaufen | Verknüpfung wird **lokal aufgehoben**, Nutzer wird zum erneuten Verbinden aufgefordert |
| `403` | Kein Zugriff (Rolle fehlt) | Hinweis auf die fehlende Discord-Rolle |
| `404` | Kein laufender Bericht | wie `204` |
| alles andere | Störung | „Der Bot antwortete mit HTTP `<code>`." |

> **Achtung bei `401`:** die App löscht daraufhin die lokale
> Discord-Verknüpfung (dasselbe Verhalten wie im
> `CharacterSyncClient`). Ein `401` darf deshalb **nur** bei einem
> wirklich ungültigen Token kommen — nicht bei fehlenden Rechten
> (dafür `403`) und nicht bei fehlendem Bericht (dafür `204`).

---

## Antwortformat

### Kein laufender Bericht

Entweder `204`, oder:

```json
{
  "status": "idle",
  "detail": "Kein Livelog seit 18:42."
}
```

`detail` ist optional und erscheint unverändert in den Einstellungen.

### Laufender Bericht

```json
{
  "status": "ok",

  "report": {
    "code": "aBcDeF12",
    "title": "Mittwochsraid",
    "zone": "Thron des Donners",
    "url": "https://www.warcraftlogs.com/reports/aBcDeF12"
  },

  "fight": {
    "id": 12,
    "encounter_id": 1640,
    "name": "Horridon",
    "difficulty_id": 6,
    "raid_size": 25,
    "duration": 187.4,
    "in_progress": true,
    "kill": false,
    "boss_percentage": 42.5,
    "pull_number": 7,
    "battle_res_charges": 2,
    "battle_res_max": 3,
    "heroism_used": true,
    "heroism_remaining": 12.0
  },

  "players": [
    {
      "name": "Bramborn",
      "class": "Warrior",
      "spec": "Protection",
      "role": "tank",
      "damage_total": 3600000,
      "healing_total": 0,
      "damage_taken": 8200000,
      "health_percent": 71.0,
      "active_mitigation": true
    },
    {
      "name": "Pyrothal",
      "class": "Mage",
      "spec": "Fire",
      "role": "dps",
      "damage_total": 24000000
    },
    {
      "name": "Elvenne",
      "class": "Druid",
      "spec": "Restoration",
      "role": "healer",
      "healing_total": 12000000,
      "damage_total": 900000
    }
  ],

  "deaths": [
    { "name": "Krallenwut", "at": 63.0, "ability": "Verheerender Schlag" }
  ],

  "mechanics": [],
  "consumables": [],
  "raid_cooldowns": [],
  "heal_cooldowns": [],
  "warnings": []
}
```

---

## Feldreferenz

Alle Felder sind **optional**. Der Mapper
(`analyzer/providers/warcraftlogs_payload.py`) liest defensiv und
fällt auf neutrale Werte zurück; eine unvollständige Antwort ist
ausdrücklich kein Fehlerfall. Es ist also völlig in Ordnung, in einer
ersten Fassung nur `fight` und `players` zu liefern.

### `report`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `code` | String | Report-Code aus der URL |
| `title` | String | Titel des Berichts |
| `zone` | String | Instanzname; erscheint mit dem Code in der Statuszeile |
| `url` | String | Volle URL (derzeit nicht ausgewertet, für später) |

### `fight`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `id` | Int | Fight-ID im Bericht |
| `encounter_id` | Int | WarcraftLogs-Encounter-ID |
| `name` | String | **Englischer** Bossname, z. B. `Horridon` |
| `difficulty_id` | Int | 3 = 10N, 4 = 25N, 5 = 10HC, 6 = 25HC, 7 = LFR |
| `raid_size` | Int | Gruppengröße |
| `duration` | Float | **Sekunden**, nicht Millisekunden |
| `in_progress` | Bool | Läuft der Kampf gerade? |
| `kill` | Bool | Reserviert (derzeit nicht ausgewertet) |
| `boss_percentage` | Float | **0–100**, nicht 0–10000 |
| `pull_number` | Int | Fortlaufende Versuchsnummer an diesem Boss |
| `battle_res_charges` / `battle_res_max` | Int | Kampfwiederbelebungen |
| `heroism_used` | Bool | Heldentum bereits eingesetzt |
| `heroism_remaining` | Float | Restlaufzeit in Sekunden |

**Wichtig — der Bossname muss englisch sein.** Instanz und
Schwierigkeit werden Companion-seitig über
`analyzer/data/encounters.py` nachgeschlagen, und diese Tabelle ist
mit englischen Namen indiziert. Ein deutscher Name ist kein
Absturz, aber die Instanzzuordnung bleibt dann leer.

**Zwei Einheiten, die WarcraftLogs anders liefert als wir sie
brauchen:** die API gibt Zeiten in Millisekunden relativ zum
Berichtsstart und `bossPercentage` je nach Endpunkt skaliert. Beides
bitte **im Bot** umrechnen — `duration` in Sekunden, `boss_percentage`
auf 0–100.

### `players`

Eine **flache Liste**, ein Eintrag pro Spieler — nicht getrennt nach
Schaden und Heilung. Das ist Absicht: so gibt es pro Spieler genau
eine Identität, und die Companion-App teilt anhand von `role` auf.

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Charaktername (**Pflicht** — Einträge ohne Namen werden verworfen) |
| `class` | String | Englischer Klassenname |
| `spec` | String | Spezialisierung |
| `role` | String | `tank`, `healer` oder `dps` |
| `damage_total` | Number | **Gesamtschaden** des Kampfes, nicht DPS |
| `healing_total` | Number | Gesamtheilung des Kampfes |
| `damage_taken` | Number | Erlittener Schaden (für die Tank-Übersicht) |
| `health_percent` | Float | Aktuelles Leben in Prozent (für die Tank-Übersicht) |
| `active_mitigation` | Bool | Aktive Schadensreduktion aktiv |

`damage_total` und `healing_total` sind **Summen**. Die App rechnet
selbst `Summe / duration` und zeigt beides an — Gesamtwert und Wert
pro Sekunde. Bitte keine bereits geteilten Werte senden.

`class` darf in der WarcraftLogs-Schreibweise kommen
(`DeathKnight`); die App normalisiert auf die Schreibweise des
Combat-Logs (`Death Knight`), die Klassenfarben und deutsche
Bezeichnungen benutzen.

`role` sollte gesetzt sein. Fehlt es, rät die App: mehr Heilung als
Schaden ⇒ Heiler, sonst Schadensausteiler. **Tanks lassen sich so
nicht erkennen** — ohne `role` fehlen sie in der Tank-Übersicht, und
die Academy vergleicht sie mit der falschen Gruppe.

### `deaths`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Charaktername (**Pflicht**) |
| `at` | Float | Sekunden seit Kampfbeginn |
| `ability` | String | Auslösende Fähigkeit |

### `mechanics` (optional, für später)

WarcraftLogs liefert das nicht von selbst — es muss dort aus
Ereignissen abgeleitet werden. Das Feld ist im Vertrag **jetzt schon**
vorgesehen, damit der Bot es später nachliefern kann, ohne dass die
Companion-App geändert werden muss.

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Charaktername (**Pflicht**) |
| `mechanic` | String | Beschreibung, deutsch (**Pflicht**) |
| `count` | Int | Anzahl, Standard 1 |
| `severity` | String | `info`, `warning` oder `error` |
| `category` | String | `movement`, `positioning`, `interrupt`, `defensive` oder `other` |

`category` ist der Schlüssel für die **WeintAcademy**: sie ordnet
darüber jeden Fehler einem trainierbaren Bereich zu. Ohne diese
Kategorien bewertet die Academy Bewegung und Mechaniken pauschal als
fehlerfrei — die Auswertung funktioniert, sagt aber wenig aus.

### `consumables` (optional)

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `label` | String | z. B. `Flask`, `Bufffood`, `Kampftrank` (**Pflicht**) |
| `used` / `total` | Int | Wie viele von wie vielen |
| `missing` | String[] | Namen der Spieler ohne diesen Buff |

### `raid_cooldowns` / `heal_cooldowns` (optional)

Anders als `CooldownState.progress` (Restzeit-Balken) es nahelegt, hat
ein bereits beendeter WarcraftLogs-Pull kein sinnvolles "noch X
Sekunden" - der Bot liefert deshalb nur, OB und WIE OFT ein Cooldown
genutzt wurde, keinen echten Live-Countdown.

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Fähigkeitsname (**Pflicht**) |
| `actor_name` | String | Charaktername, ggf. mit Nutzungszähler wie `Kaldrun (2×)` (**Pflicht**) |
| `ready` | Bool | Vom Bot immer `true` gesendet - kein erfundener Countdown |
| `remaining` / `duration` | Float | Vom Bot derzeit nicht gesendet, Standard 0 |

`raid_cooldowns` sind raidweite Cooldowns/Externals (z. B. `Rallying
Cry`, `Anti-Magic Zone`, `Spirit Link Totem`), `heal_cooldowns`
speziell Heiler-Cooldowns (z. B. `Tranquility`, `Divine Hymn`).

### `warnings` (optional)

Freie Hinweistexte für die Raidleitung, die WeintTV unverändert
anzeigt.

---

## v2: Felder für die Tiefenauswertung

Alle folgenden Felder sind **optional**. Fehlen sie, bleibt die
entsprechende Karte in WeintTV leer und die entsprechende Bewertung in
der Academy ausdrücklich unbewertet („keine Daten", null Sterne) —
nicht schlecht bewertet. Der Bot kann sie also einzeln nachliefern.

### `fight` — Ergänzungen

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `heroism_windows` | Array | Heldentum-Fenster, siehe unten. Alternativ auf oberster Ebene. |

Weiterhin gebraucht, aber bisher nicht gesendet:
`battle_res_charges`, `battle_res_max`, `heroism_remaining`.

### `heroism_windows[]` (oberste Ebene oder in `fight`)

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `start` | Float | Sekunden seit Kampfbeginn, **Pflicht** |
| `end` | Float | Sekunden seit Kampfbeginn, **Pflicht**, ≥ `start` |
| `source` | String | Wer es gewirkt hat |
| `label` | String | Bezeichnung, Standard „Heldentum" |

Ohne die Fenster kann die Academy Cooldown-Einsätze nicht bewerten:
„genutzt" ist die halbe Antwort, „zum richtigen Zeitpunkt genutzt" die
eigentliche Frage. Ist `heroism_used` nicht gesetzt, leitet die App es
aus der Existenz eines Fensters ab.

WarcraftLogs-Quelle: `table(dataType: Buffs)`, die `bands` der
Heldentum-Auren (`Heroism`, `Bloodlust`, `Time Warp`,
`Ancient Hysteria`).

### `players[]` — Ergänzungen

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `active_time` | Float | **Sekunden**, in denen der Spieler tatsächlich gewirkt hat. Die App rechnet daraus den Prozentwert. |
| `casts` | Int | Zahl der Wirkvorgänge; daraus entstehen die Aktionen pro Minute. |
| `longest_gap` | Float | Längste Pause in Sekunden (optional) |
| `movement_units` | Float | Summierte **Karteneinheiten**, nicht Meter — siehe unten. |
| `damage_taken_abilities` | Array | Erhaltener Schaden je Fähigkeit, siehe unten. |
| `dots` | Array | Wirkungsdauern auf Gegnern, siehe unten. |
| `hots` | Array | Wirkungsdauern auf Verbündeten, gleiche Form. |
| `cooldowns` | Array | Einsätze mit Zeitpunkten, siehe unten. |

`active_time` ist **die** Rotationsmetrik. Bisher bewertete die
Academy „Rotation" anhand des Schadensrangs — das ist eine
Ausrüstungsbewertung, keine Aussage über die Spielweise. Quelle:
`activeTime` aus `table(dataType: DamageDone)`.

#### `movement_units` — bewusst keine Meter

Der Bot summiert die Abstände zwischen den `x`/`y`-Angaben
aufeinanderfolgender Ereignisse desselben Spielers und schickt diese
Rohsumme. Die Umrechnung in Meter macht die App
(`analyzer/analysis/movement.py`, eine einzige Konstante), damit ein
falscher Faktor ohne Bot-Deploy korrigierbar ist.

Zwei Dinge, die im Vertrag festgehalten sein sollen, weil sie die
Aussagekraft begrenzen: zwischen zwei Ereignissen wird der Weg als
Gerade angenommen, echtes Ausweichen wird also **unterschätzt**; und
ohne Ereignisse gibt es keine Position, wer währenddessen läuft taucht
nicht auf. Die App beschriftet den Wert deshalb überall als Schätzung.

Quelle: `events(dataType: Casts)` bzw. `DamageTaken`, Felder `x`/`y`.

#### `damage_taken_abilities[]`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `ability` | String | **Englischer** Name, Pflicht |
| `amount` | Number | Schadenssumme dieser Fähigkeit |
| `hits` | Int | Zahl der Treffer |
| `source` | String | Verursachender NPC (optional) |

**Der Bot ordnet nicht ein.** Ob ein Treffer vermeidbar war, ist eine
Wertung und keine Messung — sie liegt in
`analyzer/data/avoidable.py`, weil sie für WeintTV und die Academy
identisch sein muss, sich mit Schwierigkeitsgrad und Taktik ändert und
ohne Bot-Deploy korrigierbar bleiben soll. Der Bot liefert also nur
Rohzeilen; die App macht daraus vermeidbar / unvermeidbar / nicht
eingeordnet.

Die Einordnung ist **dreiwertig**. Was in der Tabelle fehlt, bleibt
„nicht eingeordnet" — und liegt der eingeordnete Anteil zu niedrig,
gibt die Academy für „Überleben" gar keine Bewertung ab, statt eine,
die nur die Lücken der Tabelle abbildet.

Quelle: `table(dataType: DamageTaken, hostilityType: Friendlies)`,
Feld `abilities` je Spieler.

#### `dots[]` / `hots[]` / `buffs[]`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `aura` | String | Name der Fähigkeit, Pflicht (entfällt, wenn `spell_id` steht) |
| `spell_id` | Int | Spell-ID der Fähigkeit (optional, aber **empfohlen**) |
| `uptime_percent` | Float | 0–100 |
| `applications` | Int | Zahl der Anwendungen |
| `target` | String | Ziel (optional) |
| `expected_percent` | Float | Richtwert, ab dem die Uptime als gut gilt (optional) |

`spell_id` ist die einzige Angabe an einer Fähigkeit, die keine
Sprache hat, und deshalb der sicherste Weg: die Companion erkennt eine
Zeile seit 1.6.0 über **Spell-ID, englischen oder deutschen Namen** -
einer genügt (`analyzer/data/class_abilities.py`). Gelesen werden
`spell_id`, `guid`, `ability_id` und `abilityGameID`, damit ein
durchgereichtes WarcraftLogs-Feld nicht extra umbenannt werden muss.
Wird die ID mitgeschickt, ist der Anzeigename beliebig; erkannt wird
die Fähigkeit trotzdem, und in der Oberfläche steht ihr deutscher
Name.

Die Einordnung in DoT/HoT/Buff korrigiert die Companion bei bekannten
Fähigkeiten selbst: ein HoT, der in `buffs[]` steht, landet trotzdem
in der HoT-Karte. Das ist kein Freibrief für falsche Einsortierung -
für unbekannte Fähigkeiten bleibt die des Bots stehen -, sondern
verhindert, dass eine ganze Karte leer aussieht, obwohl die Zahl
geliefert wurde.

Quelle: `events(dataType: Debuffs, hostilityType: Enemies)` für DoTs,
`events(dataType: Buffs)` für HoTs und eigene Buffs — nur rohe
Ereignisse kennen mit `sourceID` den Auslöser. Die Tabellenform
(`table(...)`) bleibt als Rückfallebene für DoTs und HoTs; für
`buffs[]` gibt es sie bewusst **nicht**: die Buffs-Tabelle kennt den
Auslöser nicht, und ein Raidbuff, den jemand anders gegeben hat, ist
kein eigener Buff. Lieber leer als falsch zugeordnet.

`buffs[]` sind Effekte auf dem Spieler **selbst**: die aktive
Schadensminderung eines Tanks (Schildblock, Mischen, Schild des
Rechtschaffenen, Knochenschild) und die Selbstbuffs, die zur Rotation
gehören (Schnetzeln, Wildes Brüllen, Inquisition). Dieselbe Form wie
`hots[]`, aber ausdrücklich eine eigene Liste - ein Schildblock liegt
nicht auf dem Raid, und in `hots[]` geschrieben würde er nur bei
Heilern ausgewertet. Für Tanks ist das die einzige Kennzahl, die ihre
eigentliche Aufgabe misst: ohne sie werden sie in „Rotation" allein an
ihrer Aktivzeit gemessen, also an der einen Zahl, die über einen Tank
am wenigsten aussagt.

Welche Aura ein eigener Buff ist, entscheidet der **Aurenkatalog** des
Bots (`services/warcraftlogs_auras.py`), nicht `sourceID == targetID`:
sonst stünden Essen, Fläschchen, Klassenbuffs und jedes Trinket-Proc
in dieser Liste. Umgekehrt gilt für **Debuffs auf Gegnern** die andere
Regel — was der Katalog nicht kennt, zählt trotzdem als DoT, denn ein
Spieler-Debuff auf dem Boss ist per Konstruktion Rotationsarbeit. Eine
Katalog­lücke kostet dort die Übersetzung, nicht die Zeile.

#### `cooldowns[]`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Fähigkeit, Pflicht (entfällt, wenn `spell_id` steht) |
| `spell_id` | Int | Spell-ID der Fähigkeit (optional, aber **empfohlen**) |
| `casts` | Float[] | Zeitpunkte in Sekunden seit Kampfbeginn |
| `cooldown` | Float | Abklingzeit in Sekunden |
| `category` | String | `raid`, `heal`, `personal` oder `defensive` (optional) |

Fehlen `cooldown` oder `category`, ergänzt die Companion sie seit
1.6.0 aus der Spec-Tabelle. Eine **Obergrenze** ("X von Y möglichen
Einsätzen") entsteht dabei nur für `personal`: ein ungenutzter
Schildwall ist kein verschenkter Einsatz, sondern ein Kampf, in dem er
nicht gebraucht wurde.

**Möglich-Zahl und Burst-Ausrichtung rechnet die App selbst** aus
Kampfdauer, Abklingzeit und den Heldentum-Fenstern. Der Bot liefert
nur die Tatsachen.

Nicht zu verwechseln mit `raid_cooldowns`/`heal_cooldowns`: die
beschreiben den Live-Countdown, diese Liste die Rückschau über den
ganzen Kampf.

Quelle: `events(dataType: Casts)`, gefiltert auf bekannte Cooldowns.

### `resurrects[]` (oberste Ebene)

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `target` | String | Wiederbelebter Spieler, **Pflicht** |
| `caster` | String | Wer gewirkt hat |
| `at` | Float | Sekunden seit Kampfbeginn |
| `ability` | String | Fähigkeit |

Beantwortet, was die reine Ladungsanzeige offenlässt: auf wen, von
wem, wann. Fehlt `battle_res_charges`, leitet die App die
verbleibenden Ladungen daraus ab.

Quelle: `events(dataType: Resurrects)`.

### `interrupts[]` / `dispels[]` (oberste Ebene)

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `actor` | String | Wer eingegriffen hat, **Pflicht** |
| `at` | Float | Sekunden seit Kampfbeginn |
| `target` | String | Ziel |
| `ability` | String | Fähigkeit |

Als Einzelereignisse und nicht als Zähler: daraus lässt sich beides
ableiten, umgekehrt nicht — und nur der Zeitpunkt erlaubt den Sprung
aus der Academy in die Wiedergabe.

Quelle: `events(dataType: Interrupts)` bzw. `Dispels`.

### `mechanics[]` — Neufassung

`category` ist ab v2 **Pflicht** (`movement`, `positioning`,
`interrupt`, `defensive`, `other`). Ohne sie kann die Academy den
Fehler keinem trainierbaren Bereich zuordnen.

Neu ist `at` (Float, Sekunden) — der Zeitpunkt, an dem der Fehler
passierte. Er ist das Sprungziel in die Wiedergabe.

**Zusammenführung:** Die App leitet zusätzlich eigene Mechanikfehler
aus dem vermeidbaren Schaden ab. Beschreiben eine Bot-Regel und eine
abgeleitete Zeile denselben Vorfall, **gewinnt der Bot** — seine
Zeilen sind handverlesen und stehen zuoberst. Die Erkennung läuft je
Spieler über den Fehlertext und über eine Alias-Tabelle, die deutsche
Bot-Texte auf englische Fähigkeitsnamen abbildet. Der Bot muss dafür
nichts tun; er kann seine Regeln behalten oder mit der Zeit zugunsten
der Rohzeilen abbauen.

### `events[]` (optional, oberste Ebene)

Alles, was den Verlauf eines Kampfes erzählt, ohne dass die App es
auswerten müsste: Phasenwechsel, angesagte Bossfähigkeiten, Adds.
Die App zeigt sie in WeintTVs Karte "Kampfereignisse" auf derselben
Zeitachse wie Tode, Kampf-Rezz und Heldentum — und während einer
Wiedergabe jeweils nur bis zur laufenden Sekunde.

```json
"events": [
  { "at": 45.0, "kind": "phase", "detail": "Gurubashi-Tor offen" },
  { "at": 72.0, "kind": "cast", "actor": "Horridon",
    "ability": "Double Swipe", "detail": "Doppelhieb angesagt",
    "severity": "warning" }
]
```

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `at` | Float | – | Sekunde im Kampf |
| `kind` | String | **ja** | Art des Ereignisses |
| `actor` | String | – | Verursacher |
| `target` | String | – | Ziel |
| `ability` | String | – | Fähigkeit |
| `detail` | String | – | Anzeigetext |
| `severity` | String | – | `info` (Vorgabe), `success`, `warning`, `error` |

**`kind` wird bewusst nicht gegen eine feste Liste geprüft.** Eine
neue Ereignisart erscheint ohne Companion-Update in der Liste; der
Companion beschriftet nur die ihm bekannten Arten schöner. Deshalb
gehört alles, was die App *auswerten* soll (Tode, Rezz, Heldentum,
Unterbrechungen, Dispels, Mechanikfehler), weiterhin in seinen
eigenen, typisierten Block und **nicht** hierher — sonst wäre es
doppelt gezählt.

Derselbe Block ist auch in der Zeitleisten-Antwort erlaubt und wird
dort identisch gelesen.

---

## v2: Zeitleiste eines Fights (Wiedergabe)

```
GET /companion/warcraftlogs/reports/{code}/fights/{fight_id}/timeline
Authorization: Bearer <companion_token>
```

Die Grundlage für den Wiedergabe-Knopf in WeintTV: einen
abgeschlossenen Pull Sekunde für Sekunde abspielen, mit Schieberegler
und 1× bis 8×. Umgesetzt in `services/warcraftlogs_timeline.py`.

Bewusst ein eigener Endpunkt und kein Zusatzfeld am Einzel-Fight: die
Antwort enthält Zeitreihen für jeden Spieler und ist deutlich größer
als das Gesamtbild. Sie wird nur beim Druck auf Wiedergabe gebraucht
und soll nicht jeden Archiv-Klick verteuern.

Statuscodes wie beim Einzel-Fight; `404`, wenn es für diesen Pull
keine Zeitleiste gibt.

```json
{
  "status": "ok",
  "interval": 1.0,

  "fight": { "…wie beim Einzel-Fight…" },

  "boss_health": [100.0, 98.2, 95.1, "…"],

  "players": [
    {
      "name": "Pyrothal",
      "class": "Mage",
      "spec": "Fire",
      "role": "dps",
      "damage":       [0, 120000, 260000, "…"],
      "healing":      [0, 0, 0, "…"],
      "damage_taken": [0, 0, 54000, "…"],
      "movement":     [0, 480, 1020, "…"],
      "activity":     [0, 0.9, 1.9, "…"],
      "casts":        [0, 2, 4, "…"]
    }
  ],

  "deaths":     [{ "name": "Krallenwut", "at": 63.0, "ability": "…" }],
  "resurrects": [{ "target": "Krallenwut", "caster": "Elvenne", "at": 78.0 }],
  "heroism_windows": [{ "start": 96.0, "end": 136.0, "source": "Kaldrun" }],

  "damage_taken_hits": [
    { "player": "Dolchtanz", "ability": "Double Swipe", "at": 34.0,
      "amount": 96000, "hits": 1 }
  ],

  "interrupts": [], "dispels": [], "mechanics": [], "events": [],

  "aggregate": { "…exakt die Form des Einzel-Fights…" }
}
```

### Regeln, die für die Wiedergabe zwingend sind

**Alle Reihen sind kumulativ**, nicht als Zuwachs je Takt. Das ist
keine Geschmacksfrage: die App liest daraus Summen bis zum Zeitpunkt X
und interpoliert zwischen zwei Stützpunkten. Aus Zuwächsen müsste sie
bei jedem Sprung von vorn aufsummieren, und die Bossleiste würde bei
achtfacher Geschwindigkeit sichtbar ruckeln.

**`interval`** ist der Abstand der Stützpunkte in Sekunden. Empfohlen
1.0; bei sehr langen Kämpfen sind 2 bis 5 vertretbar. Fehlt der Wert,
nimmt die App 1.0 an.

**`activity`** ist die kumulative aktive Zeit **in Sekunden**, nicht in
Prozent — den Prozentwert bildet die App gegen die verstrichene Zeit.

**`aggregate`** ist der Gesamtstand des fertigen Kampfes in exakt der
Form des Einzel-Fight-Endpunkts. Er ist die Rückfallebene für alles,
was sich pro Sekunde nicht ehrlich rekonstruieren lässt
(Verbrauchsgüter, die vollständige Fähigkeitsaufschlüsselung des
erhaltenen Schadens). Am Ende der Wiedergabe zeigt die App denselben
Stand wie im Archiv.

**`damage_taken_hits`** sind Einzeltreffer mit Zeitpunkt, je Spieler,
Fähigkeit und Sekunde zusammengefasst. Während der Wiedergabe ist das
der einzige exakt bekannte Teil der Schadensaufschlüsselung — deshalb
zeigt die App nur ihn und extrapoliert den Rest nicht.

**Der Bot schickt hier bewusst kein Urteil.** Ob ein Treffer
vermeidbar war, entscheidet die Companion-App über
`analyzer/data/avoidable.py`: diese Wertung ändert sich mit
Schwierigkeitsgrad und Taktik, muss für WeintTV und die Academy
identisch sein und ohne Bot-Deploy korrigierbar bleiben. Eine
Fähigkeit ohne Tabelleneintrag ergibt `unknown` und damit **keinen**
Eintrag — lieber eine Lücke als ein Vorwurf gegen jemanden, der nichts
falsch gemacht hat. Das ältere Feld `avoidable_hits` (bereits als
vermeidbar gemeldete Treffer) wird weiterhin akzeptiert und
unverändert übernommen.

**`interval`** wird bei langen Kämpfen gestreckt statt die Antwort
wachsen zu lassen: ab `MAX_SAMPLES` Stützpunkten geht der Takt auf 2,
3, … Sekunden hoch. Die App liest den Wert ohnehin aus der Antwort.

**`boss_health`** wird aus dem Schaden am Boss abgeleitet — die
maximale Trefferpunktzahl steht in keiner API-Antwort. Sie ergibt sich
aus Gesamtschaden und Endprozentwert (ein Kill endet bei 0 %, ein Wipe
bei 42,5 % bedeutet, dass der Gesamtschaden 57,5 % entsprach). Ist der
Endwert unbekannt und war es kein Kill, bleibt die Reihe **leer**:
eine Leiste, die einfach bis 0 läuft, würde einen Kill behaupten, den
es nicht gab. Welcher Gegner der Boss ist, kommt aus
`masterData.actors[].subType == "Boss"`; fehlt die Rolle, entscheidet
der Schadensanteil, und nur wenn er deutlich genug ist — sonst gibt es
lieber keine Bossleiste als eine, die die Adds einer Phase anzeigt.

**Leere Reihen werden weggelassen**, nicht als Nullreihe geschickt:
die App unterscheidet „keine Daten" von „nachweislich null", und eine
Nullreihe wäre die falsche der beiden Aussagen.

**Größenordnung:** 25 Spieler × 6 Reihen × 360 Stützpunkte ist
unproblematisch. Reihen **je Spieler und Fähigkeit** werden
ausdrücklich **nicht** verlangt — das wären Megabyte pro Kampf.
Deshalb kommt die vollständige Aufschlüsselung aus `aggregate`.

Quellen: rohe `events(dataType: DamageDone|Healing|DamageTaken|Casts)`
für Reihen *und* Ereignislisten. Bewusst nicht `graph()`: dieselben
Ereignisse liefern zugleich den Verlauf, die Positionsangaben für die
Laufwege und die Einzeltreffer — ein zweiter Abruf mit einem zweiten
Antwortformat wäre eine zusätzliche Fehlerquelle ohne zusätzlichen
Nutzen. Es ist der teuerste Abruf der ganzen Brücke und passiert genau
einmal je Druck auf „Wiedergabe", nicht im Poll-Takt.


---

## Was die Companion-App selbst ergänzt

Damit auf Bot-Seite nichts doppelt gebaut wird:

- **Alter der Daten.** Die App misst selbst, wie lange der letzte
  Abruf her ist, lässt die Pull-Uhr währenddessen weiterlaufen und
  blendet ab 45 Sekunden einen Hinweis ein. Ein Feld dafür ist nicht
  nötig.
- **Instanz und Schwierigkeitsname** aus `encounter_id`/`name` bzw.
  `difficulty_id`.
- **Ranglisten, Anteile und Werte pro Sekunde** aus den Summen.
- **Pull-Historie.** Der `RaidDataService` erkennt am Wechsel der
  `pull_number` das Ende eines Versuchs und legt ihn ab.
- **Verwerfen veralteter Berichte.** Kommen drei Minuten lang keine
  neuen Daten, zeigt die App keinen eingefrorenen Pull weiter.

Ab v2 zusätzlich:

- **Die Einordnung „war das vermeidbar".** Sie ist eine Wertung, keine
  Messung, und liegt in `analyzer/data/avoidable.py` — siehe die
  Begründung bei `damage_taken_abilities`.
- **Die Umrechnung von Karteneinheiten in Meter**, samt der
  Kennzeichnung als Schätzung.
- **Möglich-Zahl und Burst-Ausrichtung der Cooldowns** aus Kampfdauer,
  Abklingzeit und Heldentum-Fenstern.
- **Die Ableitung von Mechanikfehlern aus vermeidbarem Schaden** und
  das Zusammenführen mit den Regeln des Bots.
- **Die Rekonstruktion jeder Sekunde** aus der Zeitleiste.
- **Die gemeinsame Zeitachse** in WeintTVs "Kampfereignisse": Tode,
  Kampf-Rezz, Heldentum, Unterbrechungen, Dispels, Mechanikfehler und
  `events[]` werden erst in der Oberfläche zusammengeführt. Der Bot
  liefert sie getrennt weiter — die Academy braucht sie getrennt.

---

## Archiv: vergangene Reports ansehen

Zusätzlich zum Live-Endpunkt oben kann WeintTV/die WeintAcademy einen
**Archiv-Modus** anbieten: Report auswählen, Pull darin auswählen,
dessen Daten ansehen - unabhängig davon, ob gerade ein Livelog läuft.
Das ist companion-seitig bereits vollständig umgesetzt
(`core/warcraftlogs_archive_client.py`,
`core/raid_data_service.py`'s Archiv-Zustandsmaschine,
`gui/widgets/tv/archive_picker.py`) und wartet auf die drei folgenden
Endpunkte.

Alle drei verwenden dieselbe Authentifizierung wie der Live-Endpunkt
(`Authorization: Bearer <companion_token>`) und dasselbe
401/403-Verhalten (401 hebt die lokale Verknüpfung auf, 403 bedeutet
"eingeloggt, aber keine Berechtigung").

### Reportliste

```
GET /companion/warcraftlogs/reports
```

```json
{
  "status": "ok",
  "reports": [
    {
      "code": "aBcDeF12",
      "title": "Mittwochsraid",
      "zone": "Thron des Donners",
      "start": "2026-07-23T19:05:00Z"
    }
  ]
}
```

**Die Reihenfolge ist Teil des Vertrags: neueste zuerst.** Seit 2.0.7
liest nicht nur der Archivmodus diese Liste, sondern auch die
Übersicht - sie nimmt den ersten Bericht, der einen Bosskampf enthält,
und dessen letzten Pull als „Dein letzter Pull"
(`core/last_pull_sync.py`, alle 20 Minuten, zwischengespeichert). Der
teure Einzel-Fight wird dafür ausdrücklich **nicht** abgerufen: Boss,
Ausgang, Dauer und Pullnummer stehen bereits in der Fightliste, und
was ohne ihn fehlt - Bewertung und Lektion - sagt die Karte
ausdrücklich, statt es zu schätzen.

Eine sinnvolle Grenze (z. B. die letzten 20-30 Reports der Gilde,
neueste zuerst) reicht aus - die Companion-App zeigt sie in einem
Dropdown, kein endloses Scrollen. `code` ist das einzige Pflichtfeld
(ohne ihn ist ein Eintrag nicht abrufbar und wird verworfen); `title`
und `zone` bilden zusammen die Anzeigebeschriftung, `start` wird
aktuell nicht ausgewertet (für eine spätere Sortierung/Anzeige
vorgesehen).

### Fight-Liste eines Reports

```
GET /companion/warcraftlogs/reports/{code}/fights
```

```json
{
  "status": "ok",
  "fights": [
    {
      "id": 12,
      "encounter_id": 1640,
      "name": "Horridon",
      "difficulty_id": 6,
      "kill": false,
      "boss_percentage": 42.5,
      "duration": 187.4,
      "pull_number": 7
    }
  ]
}
```

Ein `404` bedeutet "dieser Report-Code existiert nicht" und wird von
der Companion-App entsprechend angezeigt. `id` ist das einzige
Pflichtfeld (Einträge ohne nutzbare ID werden verworfen); `name`,
`kill`, `boss_percentage`, `duration` und `pull_number` bilden
zusammen die Zeilenbeschriftung im Dropdown (z. B.
"Pull 7 · Horridon · 42 % · 03:07").

**Nur Bosskämpfe.** WarcraftLogs führt Trash in derselben
`fights`-Liste und unterscheidet es über `encounterID == 0`. Der Bot
lässt Trash hier weg: eine Trashgruppe ist kein Pull — kein
Bossanteil, keine Pull-Nummer, die etwas bedeutet, keine Taktik, gegen
die sich etwas bewerten ließe —, in der Auswahlliste standen davon
aber Dutzende zwischen den paar Kämpfen, die man ansehen will. Die
Encounter-ID ist dafür das einzige verlässliche Merkmal: `name` trägt
bei Trash den Namen irgendeines Mobs, und `difficulty` fehlt dort zwar
meist, aber nicht nur dort.

Die App verwirft Trash **zusätzlich selbst** (`build_fight_list()`
überspringt `encounter_id <= 0`). Das ist keine doppelte Arbeit,
sondern der Grund, aus dem `encounter_id` überhaupt im Vertrag steht:
die Liste kommt von einem Server, der nicht mit der App zusammen
aktualisiert wird, und ohne diese Zeile hinge die Auswahl davon ab,
wann jemand den Bot neu ausrollt.

Die `pull_number` zählt weiterhin gegen die **vollständige**
`fights`-Liste — sie zählt die Pulls desselben Encounters, und Trash
dazwischen darf sie nicht verschieben.

Dieselbe Unterscheidung gilt für den Live-Endpunkt: dort galt bis
1.6.1 schlicht der jüngste Eintrag als aktueller Pull, und das ist an
einem Raidabend überwiegend eine Trashgruppe. Jetzt gilt der jüngste
**Bosskampf**; enthält der Bericht noch keinen, antwortet `/live` mit
`"idle"` und "Bericht liegt vor, aber noch kein Bosskampf" — ehrlicher
als eine Trashgruppe mit Pull-Nummer, Bossleiste und
Academy-Bewertung.

### Einzelner Fight

```
GET /companion/warcraftlogs/reports/{code}/fights/{fight_id}
```

**Liefert bewusst exakt dieselbe JSON-Form wie die
`"ok"`-Antwort des Live-Endpunkts weiter oben** (`report`/`fight`/
`players`/`deaths`/`mechanics`/`consumables`/`raid_cooldowns`/
`heal_cooldowns`/`warnings`) - nur eben für einen längst
abgeschlossenen Fight statt den gerade laufenden.
Das ist Absicht: die Companion-App verwendet für beide Wege
(live und Archiv) dieselbe Übersetzungsfunktion
(`snapshot_from_payload()`), ein separates Format hier würde nur
doppelten Code auf beiden Seiten erzeugen. Ein `404` bedeutet
"dieser Pull existiert in diesem Report nicht".

Ein Unterschied zum Live-Endpunkt: `fight.in_progress` sollte bei
einem archivierten Fight `false` sein (der Pull ist ja beendet) -
die Companion-App verlässt sich hier ohnehin nicht darauf und
markiert archivierte Fights immer explizit als "nicht live", aber ein
korrektes `false` vermeidet trotzdem einen irreführenden Pull-Timer.

---

## Umsetzungsskizze für den Bot

1. **Webhook mitlesen:** im Livelog-Kanal auf Nachrichten mit einer
   `warcraftlogs.com/reports/<code>`-URL achten und den Code mit
   Zeitstempel und Gilde ablegen.
2. **Alternative ohne Webhook:** die WarcraftLogs-API kann den
   jüngsten Bericht einer Gilde direkt liefern
   (`reportData.reports(guildName:, guildServerSlug:, guildServerRegion:)`).
   Das ist der robustere Weg, falls der Webhook mal ausfällt — beide
   Wege können sich ergänzen.
3. **Bericht abfragen:** WarcraftLogs API v2 (GraphQL,
   `https://www.warcraftlogs.com/api/v2/client`, OAuth2
   `client_credentials`). Gebraucht werden `reportData.report(code:)`
   mit `fights` sowie `table(dataType: DamageDone)` und
   `table(dataType: Healing)` für den letzten Kampf.
4. **Zwischenspeichern:** die Antwort etwa 10–15 Sekunden im Speicher
   halten. Der Livelog wird ohnehin nur in Abständen ergänzt, und das
   Punktekontingent der API ist begrenzt — ohne Cache multipliziert
   sich jede Companion-Instanz auf echte API-Anfragen.
5. **Umrechnen und ausliefern** wie oben beschrieben.

Für das Archiv oben kommt derselbe `reportData.reports(guildName:, ...)`-
Aufruf wie in Schritt 2 zur Anwendung, nur ohne ihn auf den jüngsten
Eintrag zu beschränken - die Liste selbst ist bereits die Antwort auf
`GET /companion/warcraftlogs/reports`. Die Fight-Liste eines Reports
kommt aus demselben `reportData.report(code:){ fights }`-Aufruf wie in
Schritt 3; ein einzelner Fight braucht zusätzlich `table(dataType: ...)`
mit dem jeweiligen `fightIDs: [id]`-Filter, exakt wie beim Live-Fight,
nur eben für einen bestimmten statt den letzten Kampf.

---

## Gegenstellen in diesem Repo

| Datei | Rolle |
|-------|-------|
| `core/warcraftlogs_client.py` | Live-Endpunkt: HTTP-Aufruf, Statuscodes, Token |
| `core/warcraftlogs_archive_client.py` | Archiv-Endpunkte: Report-/Fight-Listen, einzelner Fight |
| `analyzer/providers/warcraftlogs.py` | Live-Provider: Abruf-Thread, Zwischenspeicher, Snapshot |
| `analyzer/providers/warcraftlogs_payload.py` | Übersetzung Antwort → `RaidSnapshot`, Report-/Fight-Listen |
| `analyzer/replay/payload.py` | Übersetzung Zeitleisten-Antwort → `FightTimeline` |
| `analyzer/replay/reconstruct.py` | `snapshot_at()`: aus der Zeitleiste der Stand einer Sekunde |
| `analyzer/data/avoidable.py` | Einordnung „vermeidbar / unvermeidbar / unbekannt" je Boss |
| `analyzer/analysis/damage.py` | Aufteilung des erhaltenen Schadens, Ableitung und Zusammenführung der Mechanikfehler |
| `analyzer/analysis/movement.py` | Karteneinheiten → Meter, eine einzige Konstante |
| `analyzer/academy/checks.py` | Auflösung der Metriknamen für den automatischen Trainingsplan |
| `core/raid_data_service.py` | Registrierung der Quelle, Live/Archiv/Wiedergabe-Zustandsmaschine |
| `gui/widgets/tv/archive_picker.py` | Live/Archiv-Umschalter und Wiedergabe-Start (WeintTV + Academy) |
| `gui/widgets/tv/replay_bar.py` | Steuerung der Wiedergabe |
| `gui/widgets/tv/analysis_gap.py` | Begründung, wenn die Quelle keine Tiefenauswertung liefert (WeintTV + Academy) |
| `gui/pages/settings_sections/modules.py` | Auswahl der Live-Quelle und Statusanzeige |
| `tests/test_warcraftlogs_payload.py` | Mapping und Robustheit, auch der v2-Blöcke |
| `tests/test_warcraftlogs_provider.py` | Lebenszyklus und Fehlerfälle (Live) |
| `tests/test_raid_data_service.py` | Live/Archiv/Wiedergabe-Zusammenspiel |
| `tests/test_replay.py` | Rekonstruktion und Zeitleisten-Mapping |
| `tests/test_damage_analysis.py` | Einordnung und Entdopplung der Mechanikfehler |

Zum Ausprobieren ohne fertigen Bot genügt es, in
`core/backend_config.py` `BOT_BASE_URL` auf einen lokalen Server zu
zeigen, der obiges JSON zurückgibt.
