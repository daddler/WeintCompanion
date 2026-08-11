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

**Termin und Zahlen, niemals Namen.** Beides steht ohnehin im
Anmelde-Beitrag, den jeder im Kanal lesen kann, deshalb genügt ein
verknüpftes Konto ohne jede Rolle. Die Namensliste mit den echten
Charakternamen bleibt hinter `RAIDLEAD_ROLE_ID`, wo sie war.

> Diese Grenze ist der Kern des Vertrags. Wer die Antwort später um
> Namen erweitert, verschiebt eine rollengeschützte Auskunft
> unbemerkt in eine ungeschützte.

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
      }
    },
    {
      "key": "thursday",
      "label": "Donnerstag",
      "date": "2026-08-13",
      "time": "20:00",
      "starts_at": "2026-08-13T20:00:00+02:00",
      "signups": { "active": 20, "tentative": 0, "bench": 0, "absent": 2 }
    }
  ]
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

## Antwort — kein Raid

```json
{ "status": "idle", "detail": "Kein aktiver Raid." }
```

**HTTP 200, nicht 404.** Die Companion fragt im Sync-Takt; ein ruhiger
Mittwoch darf nicht als Störung ankommen — dieselbe Haltung wie bei
`/companion/warcraftlogs/live`.

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
