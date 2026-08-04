# Zugriffsprofil-Brücke: Vertrag zwischen Bot und Companion

Diese Datei beschreibt den Endpunkt, den der **WeintCodex Bot**
bereitstellen muss, damit die Companion-App dem Addon ein
Zugriffsprofil zustellen kann. Die Addon-Seite steht in WeintCodex ab
**1.2.0.0** (`core/access.lua`), die Companion-Seite in
`core/access_profile_sync.py` und `core/access_roles.py`.

## Stand

**Der Endpunkt existiert im Bot noch nicht.** Solange er mit 404
antwortet, stellt die Companion kein Profil zu, schreibt genau einmal
eine Zeile ins Log und ist danach still. Im Addon bleiben dann alle
Bereiche offen — also exakt das Verhalten vor WeintCodex 1.2.0.0.
Dasselbe Muster wie bei der WarcraftLogs-Brücke: ein fehlender
Endpunkt ist kein Fehler, sondern ein noch nicht vorhandenes Feature.

## Wozu das Ganze

Es raiden Leute mit, die nicht in der Gilde sind. Bekommen sie die
Companion, würden zwei Dinge passieren, die beide unerwünscht sind:

1. Ihre Companion schreibt die Daten *ihrer* Gilde in dieselbe
   `SavedVariables`-Datei wie unsere — die Bestände vermischen sich.
2. Sie sehen eine Oberfläche voller gildeninterner Zahlen, die sie
   nichts angehen, und ihr Client meldet Loot und Gildenbankdaten
   nach außen.

Das Zugriffsprofil löst beides: das Addon verknüpft sich mit **genau
einer** Community und weist Daten anderer Communities ab, und die
Freigaben bestimmen, welche Bereiche offenstehen.

> **Das ist keine Sicherheitsgrenze.** Die Zuordnungstabelle liegt in
> der Companion, also auf dem Rechner des Spielers, genauso wie die
> `SavedVariables` des Addons — beide sind editierbar. Der Nutzen ist
> zweierlei: die Community-Bindung verhindert das Vermischen, die
> Freigaben halten die Oberfläche ehrlich. **Vertraulichkeit leistet
> das nicht.** Dafür müsste der Bot eine unberechtigte Nutzlast gar
> nicht erst ausliefern — siehe „Was der Bot zusätzlich könnte" unten.

## Der Endpunkt

```
GET /companion/access-profile
Authorization: Bearer <companion_token>
```

Dasselbe Token wie bei `/companion/raid-roster` — das vom Bot beim
Discord-Login ausgestellte Pairing-Token, nicht das Discord-OAuth-Token.

### Antwort 200

```json
{
  "community": {
    "id": "123456789012345678",
    "name": "Bis Einer Weint"
  },
  "identity": {
    "discordId": "987654321098765432",
    "discordName": "njiah"
  },
  "roles": ["Raider", "Verzauberer"],
  "expiresAt": 0,
  "notice": ""
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `community.id` | ja | Discord-Guild-ID **als Zeichenkette**. Siehe Fallstrick 1. |
| `community.name` | nein | Anzeigename der Gilde, erscheint im Addon unter `/wc access`. |
| `identity.discordId` | nein | Nur zur Anzeige/Support. |
| `identity.discordName` | nein | Nur zur Anzeige/Support. |
| `roles` | ja | Rollennamen des Nutzers, wie sie im Discord heißen. |
| `expiresAt` | nein | Unix-Zeit, ab der das Profil erneuert werden muss. `0` oder fehlend = läuft nie ab (Empfehlung für Gildenmitglieder). |
| `notice` | nein | Freier Text, den das Addon auf der Sperrseite zeigt, z. B. „Rolle »Raider« gibt es in #raidorga". Ohne Addon-Release änderbar. |
| `tier` | nein | Siehe „Zuordnung später in den Bot ziehen". |

### Andere Antworten

| Status | Bedeutung in der Companion |
|---|---|
| `401`, `403` | Kein verknüpfter Account bzw. keine Berechtigung. Kein Profil, keine Meldung. |
| `404` | Endpunkt nicht vorhanden. Einmal eine Info-Zeile im Log, danach still. |
| alles andere | Fehlerzeile im Log, kein Profil. |

Wichtig: in **allen** Fehlerfällen wird kein Profil zugestellt, und im
Addon bleibt alles offen. Ein Bot-Ausfall darf niemandem sein Addon
sperren.

## Zuordnung Rolle → Rang → Freigaben

Die Companion bildet die Rollennamen auf einen von vier Rängen ab
(`core/access_roles.py`, überschreibbar über die Einstellung
`access_role_map`). Trägt jemand mehrere zugeordnete Rollen, **gewinnt
der höchste** — sonst würde ein Offizier, der zusätzlich „Raidgast"
trägt, auf Gast zurückfallen. Passt **keine** Rolle, wird gar kein
Profil zugestellt und eine Fehlerzeile geschrieben: eine im Discord
umbenannte Rolle ist ein Konfigurationsfehler und soll nicht wie eine
bewusste Sperre aussehen.

```
                    gast  extern  mitglied  offizier
raids.view            -      X        X         X
raids.edit            -      -        -         X
calendar.view         -      X        X         X
calendar.invite       -      -        -         X
materials.view        -      -        X         X
materials.scan        -      -        X         X
bossguides.tips       -      X        X         X
weinttv.raid          -      -        X         X
loot.report           -      -        X         X
```

`extern` bekommt genau das, was man zum Mitraiden braucht: Roster,
Termine, Taktiken. Nicht: eine fremde Gildenbank in unsere Auswertung
scannen, Auswertungen des ganzen Raids, Loot-Meldungen in unseren
Discord.

Die Companion schickt `features` **vollständig** mit (alle neun
Schlüssel, jeweils `true`/`false`). Das Addon führt dieselbe Tabelle
als Rückfall, braucht sie dadurch aber nie — so kann ein
Auseinanderlaufen der beiden Tabellen nicht unbemerkt bleiben.

### Zuordnung später in den Bot ziehen

Schickt die Antwort ein `tier` mit (`"gast"`, `"extern"`, `"mitglied"`
oder `"offizier"`), **gewinnt es** gegenüber der lokalen Zuordnung. Die
Logik lässt sich damit später in den Bot verlagern, ohne die Companion
neu auszuliefern. Ein unbekannter Wert wird ignoriert und fällt auf die
lokale Zuordnung zurück.

## Zwei Fallstricke, die beide still schiefgehen

**1. `community.id` muss eine Zeichenkette sein.** Eine
Discord-Snowflake ist zu groß für die Zahlen von Lua 5.1. Als Zahl
geschrieben landet sie in der `SavedVariables`-Datei als `1.23e+18` und
vergleicht sich im Addon nie gleich gegen die Dezimaldarstellung — jede
Nachricht gälte dort als „fremde Community" und würde verworfen. Die
Companion normalisiert mit `str()`, aber wenn der Bot die ID als
JSON-Zahl sendet, hat sie in Python bereits Genauigkeit verloren.
**Also im Bot `str(guild.id)` senden.**

**2. Die Freigaben müssen echte Wahrheitswerte sein.** Das Addon zählt
nur echte Booleans; `"true"` oder `1` gelten dort absichtlich als
*nicht gesetzt* und fallen auf die Rangtabelle durch. Das betrifft nur
ein optionales bot-seitiges `features` — die Companion baut sie selbst
und schreibt sie korrekt.

Beides ist in `tests/test_access_profile.py` gegen einen echten
Lua-Interpreter abgesichert, nicht nur gegen die Python-Struktur.

## Was der Bot zusätzlich könnte

Der Bot kennt die Rollen des Anfragenden und ist die **einzige** Stelle
im Dreiergespann, an der eine Sperre nicht umgehbar ist. Zwei
Ergänzungen wären deshalb mehr als Kosmetik:

- **`/export`-Befehle verweigern**, wenn die Rolle den Typ nicht
  freigibt: `boss` → `bossguides.tips`, `raidwed`/`raidthu`/`raid` →
  `raids.view`, `mat` → `materials.view`; `wa` bleibt frei.
- **Community-Kennung an den Typ-Tag hängen**, damit ein weitergegebener
  Import-String nicht in der falschen Gilde landet:

  ```
  WCIMPORT:<TYP>@<COMMUNITY-ID>:<Nutzlast>
  z. B. WCIMPORT:RAIDWED@123456789012345678:2026-06-14:2000:Titel:…
  ```

  Nur das **Typfeld** wird erweitert, die Nutzlast bleibt Zeichen für
  Zeichen unverändert — die Trennzeichen aller fünf Formate (`:` Felder,
  `,` Listen, `|` Unterfelder, `::` Boss-Blöcke) sind davon nicht
  betroffen. Strings ohne `@` gelten im Addon weiter als Alt-Format und
  werden angenommen, der Tag kann also schrittweise eingeführt werden.
  `WA` braucht ihn nicht.

## Prüfen, ob es funktioniert

1. Companion einmal laufen lassen und die erzeugte
   `WeintCodex.lua` **von Hand ansehen**: steht `["community"]` unter
   `["id"]` in Anführungszeichen? Sind die Werte unter `["features"]`
   `true`/`false` und nicht `1`/`0`?
2. Im Spiel `/wc access` aufrufen — die Ausgabe nennt Community, Rang,
   Discord-Rollen, Gültigkeit und jede einzelne Freigabe. Das ist das
   gemeinsame Prüfwerkzeug beider Seiten.
3. Rolle im Discord ändern, Companion neu laufen lassen, `/reload` —
   `/wc access` muss den neuen Rang zeigen.
4. Gegenprobe: ein Nutzer ohne verknüpften Account muss ein Addon
   haben, das sich wie vor 1.2.0.0 verhält, ohne Rangmarke und ohne
   zusätzliche Chat-Ausgabe.
