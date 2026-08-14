# Termin-Brücke: Vertrag zwischen Bot und Companion

Diese Datei beschreibt `GET /companion/raid-schedule` — den Endpunkt,
aus dem die **Übersicht** ihren Countdown, den Raidtitel und die Zahl
der Zusagen zieht. Bot-Seite: `services/raid_schedule.py` und
`services/sync_server.py` im Repo *WeintCodex Bot*. Companion-Seite:
`core/raid_schedule.py` (rein) und `core/raid_schedule_sync.py`
(HTTP), gezeichnet in `gui/pages/overview.py`.

## Stand

**Der Endpunkt ist im Bot vorhanden** (seit derselben Änderung, die
diese Datei angelegt hat). Ältere Bot-Fassungen antworten mit 404;
das ist ausdrücklich kein Fehler, sondern der Zustand von vorher: die
Companion schweigt dann und die Übersicht sagt weiterhin „kein Termin
bekannt". Dasselbe Muster wie bei der WarcraftLogs- und der
Zugriffsprofil-Brücke.

## Wozu das Ganze

Die Übersicht trug rechts oben dauerhaft **„KEIN TERMIN BEKANNT"**,
auch wenn im Discord ein Termin stand. Das war keine Vorsicht,
sondern der Stand der Dinge:

- Vom Gildenkalender kannte die App nur die beiden undurchsichtigen
  `WCIMPORT`-Zeichenketten aus `/companion/raid-roster`, die
  `core/discord_roster_sync.py` **ungeparst** an das Addon
  weiterreicht — dort sitzt der Parser, nicht hier.
- Und `/companion/raid-roster` verlangt die Raidlead-Rolle. Selbst
  mit einem Parser hätte den Termin also genau eine Person gesehen.

## Was der Endpunkt liefert — und was bewusst nicht

**Termin, Zahlen und die Zusammensetzung — niemals Namen.** All das
steht ohnehin im Anmelde-Beitrag, den jeder im Kanal lesen kann
(Rolle und Klasse dort als Symbol), deshalb genügt ein verknüpftes
Konto ohne jede Rolle. Die Namensliste mit den echten Charakternamen
bleibt hinter `RAIDLEAD_ROLE_ID`, wo sie war.

> Diese Grenze ist der Kern des Vertrags. Wer die Antwort später um
> Namen erweitert, verschiebt eine rollengeschützte Auskunft
> unbemerkt in eine ungeschützte. `roster[]` trägt deshalb `role` und
> `class` und **kein** `name` — auch nicht als Discord-Anzeigename,
> auch nicht gekürzt.

## Anfrage

```
GET /companion/raid-schedule
Authorization: Bearer <companion_token>
```

## Antwort — laufender Raid

```json
{
  "status": "ok",
  "raid_id": 7,
  "title": "Siege of Orgrimmar",
  "description": "Vollclear",
  "raid_type": "standard",
  "signup_status": "open",
  "raid_size": 25,
  "composition": { "tank": 2, "healer": 6, "dps": 17 },
  "timezone": "Europe/Berlin",
  "days": [
    {
      "key": "wednesday",
      "label": "Mittwoch",
      "date": "2026-08-12",
      "time": "20:00",
      "starts_at": "2026-08-12T20:00:00+02:00",
      "signups": {
        "active": 18,
        "tentative": 2,
        "bench": 1,
        "absent": 3
      },
      "roster": [
        { "role": "tank",   "class": "Warrior" },
        { "role": "healer", "class": "Priest" },
        { "role": "dps",    "class": "Mage" }
      ]
    },
    {
      "key": "thursday",
      "label": "Donnerstag",
      "date": "2026-08-13",
      "time": "20:00",
      "starts_at": "2026-08-13T20:00:00+02:00",
      "signups": { "active": 20, "tentative": 0, "bench": 0, "absent": 2 }
    }
  ],
  "discord": {
    "guild_id": "1311060525555257364",
    "channel_id": "1311325324008751225",
    "message_id": "1400000000000000000"
  }
}
```

| Feld | Bedeutung |
| --- | --- |
| `status` | `"ok"` oder `"idle"` |
| `raid_type` | `"standard"` (Mi/Do) oder `"special"` (ein Termin) |
| `signup_status` | `"open"` oder `"locked"` |
| `raid_size` | Sollstärke; `0`/fehlend heißt „unbekannt" |
| `days[].key` | `wednesday`, `thursday` oder `special` |
| `days[].starts_at` | ISO-8601 **mit Offset** |
| `days[].signups` | `active` / `tentative` / `bench` / `absent` |
| `days[].roster` | **optional**: je Zusage `role` und `class`, ohne Namen |
| `days[].signups.roles` | **optional**: Ersatzform, nur Zahlen je Rolle |
| `composition` | **optional**: Sollstärke je Rolle |
| `discord` | Fundort der Anmeldung; optional, alle IDs als **Zeichenkette** |

## Die Aufstellung (`roster`, `composition`)

Die Übersicht zeichnet daraus die Aufstellung: je Rolle eine Reihe
Plätze, gefüllte in Klassenfarbe, offene als Lücke, darunter ein Satz
wie „Vier offene Plätze · 1 Heiler, 3 Schaden". Das ist die Frage, wegen
der man vor einem Raid ins Discord sieht — „21 von 25" beantwortet sie
nicht, denn ob die vier fehlenden Heiler oder Schaden sind, entscheidet,
ob der Abend stattfindet.

- `role` ist `tank`, `healer` oder `dps`; `heiler`, `heal`, `damage`,
  `dd`, `melee`, `ranged` werden ebenfalls erkannt. Ein **unbekannter**
  Wert lässt den Eintrag weg, statt ihn unter „Schaden" abzulegen: eine
  falsche Rolle gibt sich nicht als Lücke zu erkennen.
- `class` ist der englische Klassenname wie im Combat-Log
  (`Death Knight`, `Warrior`, …). Fehlt er, ist der Platz in
  Akzentfarbe statt in Klassenfarbe — die Aufstellung stimmt, nur das
  Bild ist ärmer.
- `roster` beschreibt genau die **aktiven** Zusagen. „Vielleicht" und
  „Ersatzbank" gehören nicht hinein; sie stehen weiterhin als Zahl
  daneben.
- `signups.roles` (`{ "tank": 2, "healer": 5, "dps": 14 }`) ist die
  billigere Form, falls die Klassen dem Bot nicht vorliegen. Sie wird
  nur gelesen, wenn `roster` fehlt.
- `composition` ist die **Sollstärke** je Rolle. Ohne sie bleibt es bei
  „Vier offene Plätze", ohne zu behaupten, welche — ein geratenes Soll
  (2 Tanks, 5 Heiler) wäre für die halbe Gilde falsch. Bleibt nach den
  fehlenden Rollen noch etwas offen, heißt es „frei wählbar": das Soll
  sagt, wie viele Heiler gebraucht werden, nicht wie der letzte Platz
  zu besetzen ist.

**Fehlt beides, ändert sich nichts an der bisherigen Anzeige** außer
der Form: ein einziger Streifen „zugesagt" mit den gefüllten und den
offenen Plätzen. Drei Reihen aus einer Gesamtzahl zu schätzen wäre in
der Anzeige von drei gemeldeten nicht zu unterscheiden — dieselbe Linie
wie `stars == 0` im Analyzer.

Der `discord`-Block ist der Ort, an dem die Anmeldung wirklich steht —
gefunden über `locate_signup()` im Bot, also die Zusammenfassung, sonst
die Mittwochs-, sonst die Donnerstagsnachricht. Er ist keine Auskunft
über Personen, sondern der Beitrag selbst, den jeder im Kanal sieht.
Die Companion macht daraus das Ziel des Knopfes **„Aufstellung im
Discord"**; fehlt er (ältere Bot-Fassung), fällt sie auf den
Anmelde-Kanal der Projektgilde zurück (`DISCORD_RAID_CHANNEL_ID` in
`core/backend_config.py`).

## Antwort — kein Raid

```json
{ "status": "idle", "detail": "Kein aktiver Raid." }
```

**HTTP 200, nicht 404.** Die Companion fragt im Sync-Takt; ein ruhiger
Mittwoch darf nicht als Störung ankommen — dieselbe Haltung wie bei
`/companion/warcraftlogs/live`.

## Antwort — Raid nur noch in der Datenbank

```json
{
  "status": "idle",
  "detail": "Zu diesem Raid gibt es im Anmelde-Kanal keine Nachricht mehr."
}
```

**Die Datenbank des Bots entscheidet nicht allein, ob es einen Raid
gibt.** Wird die Anmeldenachricht in Discord von Hand gelöscht
(Rechtsklick → Nachricht löschen) statt über „Raid löschen", merkt der
Bot davon nichts: der Datensatz bleibt liegen und gilt weiter als
laufende Anmeldung. In Discord fällt das nicht auf — dort ist die
Nachricht ja weg. In der Companion dagegen stand so ein längst
entfernter Testraid dauerhaft als nächster Termin, nach jedem Neustart
aufs Neue.

Der Endpunkt sieht deshalb vor jeder Antwort in Discord nach. Zwei
Regeln dazu:

- **Der Zweifelsfall gilt als „vorhanden".** Nur wenn Discord für
  *jede* bekannte Nachricht ausdrücklich `NotFound` liefert, ist die
  Anmeldung weg. Ein leerer Cache, ein Rate-Limit oder ein fehlendes
  Leserecht sind kein Beleg — und eine kurz nicht erreichbare API darf
  keinen laufenden Raid ausblenden.
- **Die Antwort gilt eine Minute** (`SIGNUP_PRESENCE_SECONDS`), je
  Raid. Sonst wäre das bei 25 Installationen eine Discord-Anfrage alle
  paar Sekunden für eine Auskunft, die sich höchstens einmal am Tag
  ändert.

Der Bot räumt denselben Fall beim Start zusätzlich auf: findet
`recover_raid_state()` zu einem Datensatz keine Anmeldung in Discord,
wird er entfernt (`drop_orphaned_raid()`).

## Regeln, die beide Seiten einhalten müssen

- **`starts_at` trägt den Offset.** Die Companion rechnet die Restzeit
  gegen die lokale Uhr. Ohne Offset müsste sie die Zeitzone des Bots
  raten und läge für jeden im Ausland spielenden Raider daneben; die
  Sommerzeit ist damit ebenfalls erledigt, weil `ZoneInfo` sie bereits
  angewandt hat.
- **Ein laufender Raid bleibt „der nächste".** Ein Termin, der vor
  weniger als vier Stunden begonnen hat (`RUNNING_HOURS` im Bot,
  `RUNNING_MINUTES` in der Companion), springt nicht auf die kommende
  Woche. „In 6 Tagen" ist die eine Auskunft, die um 21:30 sicher
  falsch ist.
- **Kein Datum heißt kein Termin.** Ein Sonderraid ohne lesbares
  Datum liefert `days: []`, statt den heutigen Tag zu setzen. Eine
  erfundene Uhrzeit ist in der Anzeige von einer echten nicht zu
  unterscheiden — dieselbe Linie wie `stars == 0` im Analyzer.
- **Zugesagt ist `active`.** „Vielleicht" und „Ersatzbank" stehen
  daneben, nicht mittendrin.
- **Die Raidtage stehen an zwei Stellen im Bot**
  (`raid_schedule.STANDARD_DAYS` und
  `raid_export_manager._next_weekday_date()`). Ändern sie sich, müssen
  beide angefasst werden.

## Abrufverhalten der Companion

Im gewöhnlichen Sync-Zyklus, aber höchstens alle **fünf Minuten**
(`REFRESH_SECONDS`) — der Termin ändert sich einmal pro Woche, eine
Anfrage alle fünf Sekunden wäre reine Last. Die letzte Antwort liegt
als `raid_schedule.json` unter `Paths.cache()`, damit ein Start ohne
erreichbaren Bot nicht mit „kein Termin bekannt" beginnt. **Ein
Fehlschlag löscht nichts**: nur eine ausdrückliche `"idle"`-Antwort
räumt den Termin weg.
