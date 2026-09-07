# WeakAuras eintragen, ohne ein Addon-Release zu bauen

Companion-Seite von `gui/pages/weakauras.py` (`PageId.WEAKAURAS`, Gruppe
*Charakter*). Voller Cross-Repo-Vertrag (beide Nachrichten, Bot-Endpunkte,
Feldformate): `../weakaura-bridge.md`. Diese Datei hält nur die
Companion-lokale Editor-/Sync-Logik.

Die Aufteilung ist die im Haus übliche: `core/weakaura_library.py` ist
die **reine** Hälfte (Modell, Prüfung, ID-Bildung, Lesen der
Katalogmeldung — kein Qt, kein `httpx`, keine Datei),
`core/weakaura_store.py` die Ablage in `Paths.config()/weakauras.json`
und `core/weakaura_sync.py` der Absender mit eigenem Inbox-Kanal.

Sechs Dinge, die nicht Geschmack sind:

- **Zugestellt wird immer die ganze Liste** — eine gelöschte Aura
  verschwindet im Spiel allein dadurch, dass sie fehlt (das Addon leert
  seine Inbox bei jedem Login). Auch eine **leer gewordene** Bibliothek
  wird zugestellt (`_delivered_once`), sonst bliebe die eine Aura, die
  weg sollte, für immer stehen.
- **Die Kennung wird beim Bearbeiten nie neu vergeben** — sie entscheidet
  im Addon, ob eine Zustellung eine neue Aura ist oder eine vorhandene
  ersetzt. Neue bekommen `companion-<slug>`, damit sie keine mitgelieferte
  treffen.
- **Die Liste zeigt auch die mitgelieferten Auren** (das Addon meldet,
  welche es kennt, über `weakaura_catalog`) — `addon_entries()` blendet
  aus, wofür es hier schon eine eigene Fassung gibt. Der Importstring
  wird dabei nicht mitgemeldet (~56 kB fürs Krieger-Paket allein).
- **„Im Spiel nach dem nächsten /reload" steht auf der Seite**, nicht
  nur in der Doku — die Seite ruft nach *Fertig* `publish_now()` statt
  auf den Sync-Takt zu warten.
- **Der Export-String wird von Leerraum befreit, nicht abgewiesen**; ein
  fehlender `!WA:`-Vorspann ist ein **Hinweis** (`warnings()`), keine
  Ablehnung (`validate()`) — ältere WeakAuras-Versionen exportieren so.
- **`_fill_editor()` läuft unter einem Riegel** (`_filling`) —
  `setText()` löst `textChanged` aus, das über `_on_edited()` sonst in
  denselben Eintrag schriebe, aus dem `_fill_editor()` gerade noch liest,
  und beim Wechsel zwischen Auren landete der Importstring der
  vorherigen im neuen Formular.

## Gilde-weite Freigabe (seit 2.2.0)

`core/weakaura_client.py` (HTTP, `/companion/weakauras`),
`core/weakaura_guild_sync.py` (träger Abgleich, 600s). Sechs Regeln:

- **Freigeben ist eine eigene Handlung**, keine Voreinstellung.
- **Ein nicht erreichbarer Bot löscht nichts** — `set_guild_auras()` nur
  bei erfolgreicher Antwort; eine **leere** Antwort (HTTP 200, `[]`) räumt
  dagegen sehr wohl auf (genau so verschwindet eine gelöschte/gesperrte
  Aura).
- **Bei gleicher Kennung gewinnt die eigene Fassung** (speziell vor
  allgemein — `WeakAuraStore.delivery()`), `shadowed_ids()` sagt es an.
- **Eine vergebene Kennung wird benannt, nicht umgangen** — 409 mit dem
  bisherigen Autor, erst auf Knopfdruck `POST` mit `rename: true`.
- **Lokal wird immer zuerst gespeichert**, auch bei einer Freigabe.
- **Die Moderationsknöpfe werden gezeigt, nicht versteckt** — ohne
  Raidlead-Rolle erklärt der 403 sich selbst (*lock, don't hide*).

Der Netzteil der Seite läuft in einem kurzlebigen Thread mit Rückmeldung
über `finished` — `refresh()` darf nur zeichnen.

Nicht zu verwechseln mit dem älteren Bot-Import `WCIMPORT:WA:` (siehe
`../wcimport-protocol.md`): der trägt nur Metadaten, keinen Importstring.
