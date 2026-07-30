# WarcraftLogs-Brücke: Vertrag zwischen Bot und Companion

Diese Datei beschreibt den Endpunkt, den der **WeintCodex Bot**
bereitstellen muss, damit die Companion-App den laufenden
WarcraftLogs-Livelog als Raid-Datenquelle nutzen kann.

## Stand

**Vier der fünf Endpunkte gibt es bereits.** Live, Reportliste,
Fightliste und Einzel-Fight sind im Bot umgesetzt
(`services/warcraftlogs.py`, Routen in `services/sync_server.py`) und
liefern Daten. Diese Datei beschrieb sie früher als „noch nicht
vorhanden" — das ist überholt.

Was der Bot heute liefert, sind **Summen**: Schaden, Heilung,
erhaltener Schaden, Tode. Zeitstempel gibt es ausschließlich bei
`deaths[].at`. Dazu drei bekannte Lücken:

- `consumables[].missing` bleibt immer leer (die Buff-Tabelle liefert
  nur Gesamtzahlen, keine Spielerliste).
- `mechanics[]` enthält genau eine handverlesene Regel (Immerseus).
- `fight` sendet weder `battle_res_charges`/`battle_res_max` noch
  `heroism_remaining`.

Neu in **v2** ist alles, was Zeitstempel braucht — und damit alles,
was WeintTVs Tiefenanalyse, die sechs Bewertungsbereiche der Academy
und die Wiedergabe erst möglich macht. Jedes neue Feld ist optional
und additiv; die Companion-Seite ist bereits vollständig darauf
vorbereitet und zeigt „keine Daten", solange ein Block fehlt. Der Bot
darf die Blöcke also einzeln und in beliebiger Reihenfolge
nachliefern, ohne dass etwas kaputtgeht.

Der fünfte Endpunkt (`/timeline`, für die Wiedergabe) existiert noch
nicht.

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

#### `dots[]` / `hots[]`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `aura` | String | Name der Fähigkeit, Pflicht |
| `uptime_percent` | Float | 0–100 |
| `applications` | Int | Zahl der Anwendungen |
| `target` | String | Ziel (optional) |
| `expected_percent` | Float | Richtwert, ab dem die Uptime als gut gilt (optional) |

Quelle: `table(dataType: Debuffs, hostilityType: Enemies)` für DoTs,
`table(dataType: Buffs)` für HoTs.

#### `cooldowns[]`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `name` | String | Fähigkeit, Pflicht |
| `casts` | Float[] | Zeitpunkte in Sekunden seit Kampfbeginn |
| `cooldown` | Float | Abklingzeit in Sekunden |
| `category` | String | `raid`, `heal`, `personal` oder `defensive` (optional) |

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

---

## v2: Zeitleiste eines Fights (Wiedergabe)

```
GET /companion/warcraftlogs/reports/{code}/fights/{fight_id}/timeline
Authorization: Bearer <companion_token>
```

**Dieser Endpunkt existiert noch nicht.** Er ist die Grundlage für
den Wiedergabe-Knopf in WeintTV: einen abgeschlossenen Pull Sekunde
für Sekunde abspielen, mit Schieberegler und 1× bis 8×.

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

  "avoidable_hits": [
    { "player": "Dolchtanz", "ability": "Double Swipe", "at": 34.0,
      "amount": 96000 }
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

**`avoidable_hits`** sind Einzelereignisse mit Zeitpunkt. Während der
Wiedergabe ist das der einzige exakt bekannte Teil der
Schadensaufschlüsselung — deshalb zeigt die App nur ihn und
extrapoliert den Rest nicht.

**Größenordnung:** 25 Spieler × 6 Reihen × 360 Stützpunkte ist
unproblematisch. Reihen **je Spieler und Fähigkeit** werden
ausdrücklich **nicht** verlangt — das wären Megabyte pro Kampf.
Deshalb kommt die vollständige Aufschlüsselung aus `aggregate`.

Quellen: `graph(dataType: DamageDone|Healing|DamageTaken)` für die
Reihen, `events(...)` für die Ereignislisten.


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
| `gui/pages/settings_sections/modules.py` | Auswahl der Live-Quelle und Statusanzeige |
| `tests/test_warcraftlogs_payload.py` | Mapping und Robustheit, auch der v2-Blöcke |
| `tests/test_warcraftlogs_provider.py` | Lebenszyklus und Fehlerfälle (Live) |
| `tests/test_raid_data_service.py` | Live/Archiv/Wiedergabe-Zusammenspiel |
| `tests/test_replay.py` | Rekonstruktion und Zeitleisten-Mapping |
| `tests/test_damage_analysis.py` | Einordnung und Entdopplung der Mechanikfehler |

Zum Ausprobieren ohne fertigen Bot genügt es, in
`core/backend_config.py` `BOT_BASE_URL` auf einen lokalen Server zu
zeigen, der obiges JSON zurückgibt.
