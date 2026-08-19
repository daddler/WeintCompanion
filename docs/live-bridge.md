# Live-Brücke: die Zustellung, die ein `/reload` überlebt

Diese Datei beschreibt `data/companion_live.lua` — die Lua-Datei, die
**WeintCompanion** in den Addon-Ordner schreibt und die **WeintCodex**
bei jedem Laden ausführt. Sie ist die einzige Richtung
Companion → Addon, die eine *laufende* Spielsitzung erreichen kann.

## Stand

| Seite | Datei | Ab Version |
|-------|-------|------------|
| Companion, schreibend | `addon/live_bridge.py` | WeintCompanion 2.3.0 |
| Companion, bündelnd | `addon/addon_inbox.py` | WeintCompanion 2.3.0 |
| Addon, lesend | `modules/companion.lua` (`ProcessInbox`) | WeintCodex 2.3.0.0 |
| Addon, Auslieferungsstand | `data/companion_live.lua` | WeintCodex 2.3.0.0 |

Der Bot ist **nicht beteiligt**. Die Brücke trägt genau dieselbe
Warteschlange wie `WeintCompanionInboxDB`; sie ist ein zweiter *Weg*,
kein zweites *Format*.

## Warum es sie gibt

Bis dahin lief alles über die SavedVariable `WeintCompanionInboxDB`.
Das funktioniert beim Login und **nie danach**, und der Grund liegt in
WoW selbst:

1. WoW liest die SavedVariables beim Laden **einmal** in den
   Arbeitsspeicher.
2. Bei `/reload` und beim Abmelden schreibt es sie aus dem Speicher
   **zurück in die Datei**.
3. Erst *danach* liest es sie wieder ein.

Schritt 2 vernichtet alles, was wir zwischenzeitlich hineingeschrieben
haben — bevor das Addon es je zu sehen bekommt. Der Knopf
*Anmeldungen abrufen* im Addon löst genau ein `/reload` aus und konnte
deshalb prinzipiell nie neue Daten holen: er las immer den Stand vom
Login zurück.

Schlimmer als "nichts passiert": `DiscordRosterSync` merkt sich in
`_last_delivered`, was es zuletzt zugestellt hat, und schickt einen
unveränderten Roster kein zweites Mal. Die vom `/reload` gelöschte
Zustellung war damit **weg**, bis sich in Discord inhaltlich etwas
änderte. Die Anmeldeliste im Spiel blieb tage- bis wochenalt, ohne
dass irgendwo etwas fehlte.

Eine Lua-Datei **im Addon-Ordner** hat das Problem nicht: WoW führt
Addon-Dateien bei jedem `/reload` neu aus und schreibt sie niemals
zurück.

## Format

`WeintCodex.toc` lädt die Datei als `data/companion_live.lua`. Der
Ablageort ist Teil des Vertrags — liegt sie woanders, wird sie nie
ausgeführt, und das sieht im Spiel exakt aus wie "die Companion stellt
nichts zu".

```lua
WeintCodex_CompanionLive = {
    ["writtenAt"]        = 1755600000,
    ["companionVersion"] = "2.3.0",
    ["queue"]            = {
        {
            ["type"]      = "raid_import",
            ["community"] = "123456789012345678",
            ["payload"]   = "WCIMPORT:RAIDWED@123…:2026-08-19:2000:…",
        },
        …
    },
}
```

`type`, `community` und `payload` sind identisch zu
`WeintCompanionInboxDB.queue`; die Nachrichtentypen und ihre
Nutzlasten stehen im Kopf von `modules/companion.lua`. Gerendert
werden sie von **derselben** Funktion (`render_entries()` in
`addon/inbox_writer.py`) — zwei Renderer wären zwei Formate, sobald
einer erweitert wird, und der Unterschied fiele erst im Spiel auf.

## Regeln

Jede einzelne davon ist der Grund für ein Verhalten, das ohne sie
still danebengeht:

- **Zugestellt wird immer die ganze Warteschlange, nie ein Zuwachs.**
  Das Addon kann die Datei nicht leeren — es schreibt keine Dateien.
  Ihr Inhalt *ist* deshalb der vollständige aktuelle Stand.

- **`writtenAt` wandert nur bei inhaltlicher Änderung.** Das Addon
  merkt sich in `SavedData.companionLive.lastStamp`, welchen Stand es
  zuletzt eingearbeitet hat, und überspringt einen unveränderten.
  Wanderte der Stempel bei jedem Sync-Zyklus, meldete jeder `/reload`
  denselben Import erneut im Chat.

- **Erst schreiben, dann umbenennen** (`os.replace`, atomar auf beiden
  Plattformen). Ein `/reload` kann in den Schreibvorgang fallen; eine
  halb geschriebene Lua-Datei im Addon-Ordner ist ein Ladefehler.

- **Verglichen wird gegen die Datei, nicht gegen ein Gedächtnis.** Ein
  Addon-Update entpackt den leeren Auslieferungsstand darüber. Ein
  reiner Speicher-Vergleich hielte die Zustellung danach für vorhanden
  und schriebe sie nie wieder.

- **`AddonInbox.reassert()` läuft einmal pro Sync-Zyklus** und zieht
  genau diesen Fall nach. Fast immer ein Vergleich ohne
  Schreibvorgang. Ohne belegten Kanal tut sie nichts: eine leere
  Zustellung zu schreiben nähme dem Addon den gültigen Stand des
  vorherigen App-Starts weg, bevor die Absender ihren ersten Zyklus
  hinter sich haben.

- **Die Brücke gewinnt gegen die Inbox.** Liegt eine nicht-leere
  Live-Zustellung vor, arbeitet `ProcessInbox()` diese ein und leert
  die Inbox ungelesen — sie trug denselben Stand, und beides
  einzuarbeiten hieße jeden Import doppelt zu melden. Fehlt die
  Brücke (ältere Companion, Addon frisch entpackt), bleibt es beim
  bisherigen Weg.

- **`companionVersion` steht in beiden.** `CompanionAtLeast()` im
  Addon liest bevorzugt die der Brücke: sie steht in einer Datei, die
  WoW nur liest, während die Marke in der Inbox vom `/reload`
  überschrieben worden sein kann.

## Was die SavedVariable weiterhin tut

Sie bleibt und wird weiter beschrieben. Zwei Gründe:

- Ein Addon-Stand vor 2.3.0.0 kennt die Brücke nicht.
- Die **Gegenrichtung** (`WeintCompanionDB`, Addon → Companion) läuft
  unverändert über SavedVariables und ist davon nicht betroffen: dort
  ist WoW der Schreiber und die Companion die Leserin, also genau
  herum.
