# Simmen: wowsims and QE Live

## Wertegewichte von wowsims.com/mop ins Addon (`core/stat_weights.py`)

Voller Vertrag, beide Lesewege, Skalierung, Envelope-Format:
`../stat-weights-bridge.md`. Diese Datei hält nur die Companion-lokale
Seite (Seite, Ablage, Fehler-Sichtbarkeit), die dort nicht steht.

**Die Companion simmt nicht selbst** — dieselbe Entscheidung wie im
Addon: ein Sim, der nur so aussieht, wäre schlimmer als keiner.
`gui/pages/sim.py` (`PageId.SIM`) übernimmt den **Weg**, nicht die
Rechnung: Sim auf der Seite der gewählten Spec öffnen, Ausgabe
entgegennehmen, ins Addon bringen.

Sieben Dinge nicht Geschmack:

- **Der Parser ist die Übersetzung von `modules/statweights.lua`, keine
  zweite Idee.** `tests/test_stat_weights.py` und
  `../../../WeintCodex/.github/tests/statweights_test.lua` drüben prüfen
  **dieselbe echte Sim-Ausgabe gegen dieselben Zahlen**.
- **Die Sim-Ausgabe muss laut scheitern** — Positionsformat, keine Namen,
  Längenprüfung vor jeder Übernahme.
- **Zwei Wege ins Spiel**: Addon-Brücke (erst beim nächsten Laden) und
  `WCIMPORT:SW:`-Zwischenablage (wirkt ohne Reload).
- **Was ankommt, ist ein Vorschlag, keine Einstellung** — füllt Felder im
  Spiel, wird erst auf Klick wirksam.
- **Die Kennung hängt am Inhalt, nicht an der Uhr** — je Spec die zuletzt
  erledigte Kennung.
- **Die Grenzen (7,5 % Treffer, 15 % Waffenkunde) reisen nicht mit** —
  die Seite **nennt** sie, wendet sie nicht an.
- **Was in der Liste fehlt, bekommt seinen eigenen Satz** (seit 2.5.1):
  mit Null gewichtet / hier nicht verwertbar / nicht erkannt / zu klein
  für die Skala — vier verschiedene Antworten statt einem pauschalen
  „kennt WeintCodex nicht".
- **Die Zuordnung Spec → Sim-Seite ist eine Tabelle** (`sim_url()`), ein
  unbekannter Schlüssel wird nicht geraten.

`refresh()` zeichnet ausschliesslich und fasst das Einfügefeld **nie**
an — dieselbe Falle wie beim Adressfeld in Einstellungen → Discord.

## Die Ausrüstung an den Sim (seit 2.6.0)

Geschrieben vom **WowSimsExporter** (fremdes Addon im Spiel), gelesen von
`addon/wse_reader.py` (`WSEDB`, alle AceDB-Profile, neuester Eintrag
gewinnt, nie geschrieben). `core/wowsims_export.py` prüft/ordnet zu,
`core/wowsims_link.py` baut die Adresse. Voller Vertrag:
`../wowsims-exporter-bridge.md`.

- **Geschickt wird nur die Ausrüstung** (`?i=g`) — Talente/Glyphen liegen
  beim Sim in einem gemeinsamen Bereich mit einer Übersetzung
  (Zauber-ID ↔ Gegenstands-ID), die nur der Sim kennt; mitschicken hieße
  Glyphen kämen leer an, unbemerkt.
- **`core/wowsims_link.py` schreibt ein fremdes Binärformat (Protobuf)
  und muss laut scheitern** — jede Feldnummer als benannte Konstante mit
  Zeile aus `proto/*.proto`; `tests/test_wowsims_link.py` liest mit einem
  **eigenen** Decoder zurück.
- **Ein leerer Platz ist ein Platz** — ein unbesetzter Slot wird als
  leere `SimItem`-Nachricht mitgeschrieben, sonst rückt die Zweitwaffe in
  die Waffenhand.
- **Klasse+Spec → Profilschlüssel ist eine Tabelle**, keine Ableitung.
- **Massstab für „passt das zusammen" ist die Klasse, nicht die Spec** —
  die Zweitspec mit laufender Ausrüstung zu simmen ist der Normalfall.
- **`fits_spec()`/`age_text()`/`gap_text()` liegen im Qt-freien Modul.**

`refresh()` zeichnet ausschliesslich; `read_export()` läuft nur in
`on_enter()`, nie in `refresh()`.

## Heiler simmen woanders: QE Live (`core/qelive.py`, seit 2.7.0)

Für Heiler ist wowsims die falsche Adresse — geplant wird auf
questionablyepic.com/live. *Simmen* ist eine Seite mit zwei Zweigen;
`qelive.spec(key)` entscheidet welchen (gefragt wird „führt QE Live diese
Spec", nicht „ist das ein Heiler").

Zwei Dinge kann QE Live nicht, und die Seite sagt beide statt sie wie
einen Fehler aussehen zu lassen: **keine Gewichtung je Charakter**
(Einfügefeld bleibt für Heiler leer und sagt das, `paste_gap`, statt
leer und stumm zu wirken); **keine Adresse, die eine Ausrüstung trägt**
(`_gear_link()` antwortet `""` für eine QE-Spec — der Importtext kommt
vom **Addon**, `modules/qelive.lua`, über die Zwischenablage, keine
zweite Fassung durch diese App hindurch, die veraltet, wenn sie gebraucht
wird).

*Nur die Seite* und *Export kopieren* sind im Heiler-Zweig entsprechend
ausgeblendet — kein Rollenschutz, ein Weg mit nur einer Tür.

**Die Zahlen sind dieselben wie im Addon** (`SPECS`, dieselbe Skalierung
wie `modules/qelive.lua`); `tests/test_qelive.py` und
`../../../WeintCodex/.github/tests/qelive_test.lua` prüfen dieselben Werte.
**Ein Null-Gewicht ist eine Lücke, keine Aussage** (`gaps`) —
`weights_note()` benennt sie, ebenso dass QE Live zwei Modelle selbst als
Beta führt.

Kein Qt, kein `httpx`, keine Datei — dieselbe Aufteilung wie
`roster_target()`/`build_profile_payload()`.
