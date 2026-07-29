# WarcraftLogs-Brücke: Vertrag zwischen Bot und Companion

Diese Datei beschreibt den Endpunkt, den der **WeintCodex Bot**
bereitstellen muss, damit die Companion-App den laufenden
WarcraftLogs-Livelog als Raid-Datenquelle nutzen kann.

Die Companion-Seite ist vollständig umgesetzt und wartet nur noch auf
diesen Endpunkt. Solange er fehlt, meldet die Quelle in den
Einstellungen „Zurzeit läuft kein Livelog" und WeintTV bleibt auf der
Simulation bedienbar — es geht also nichts kaputt, solange die
Bot-Seite noch aussteht.

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

### `warnings` (optional)

Freie Hinweistexte für die Raidleitung, die WeintTV unverändert
anzeigt.

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

---

## Gegenstellen in diesem Repo

| Datei | Rolle |
|-------|-------|
| `core/warcraftlogs_client.py` | HTTP-Aufruf, Statuscodes, Token |
| `analyzer/providers/warcraftlogs.py` | Abruf-Thread, Zwischenspeicher, Snapshot |
| `analyzer/providers/warcraftlogs_payload.py` | Übersetzung Antwort → `RaidSnapshot` |
| `core/raid_data_service.py` | Registrierung der Quelle |
| `gui/pages/settings_sections/modules.py` | Auswahl und Statusanzeige |
| `tests/test_warcraftlogs_payload.py` | Mapping und Robustheit |
| `tests/test_warcraftlogs_provider.py` | Lebenszyklus und Fehlerfälle |

Zum Ausprobieren ohne fertigen Bot genügt es, in
`core/backend_config.py` `BOT_BASE_URL` auf einen lokalen Server zu
zeigen, der obiges JSON zurückgibt.
