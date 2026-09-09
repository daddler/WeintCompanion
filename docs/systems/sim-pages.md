# Simmen: wowsims and QE Live

## Ein Lauf, vier Schritte (seit 3.3.0)

Die Klammer um beide Auskünfte — Kennung, Zeitstempel, Handshake im
Spiel, die sechs Zustände — steht in `../sim-run.md`. Diese Datei hält
nur die Companion-lokale Seite.

**Der Nutzer denkt in einem Vorgang.** *„Ich simme meinen Charakter und
will danach die Empfehlungen im WeintCodex haben."* Technisch sind es
zwei Auskünfte mit zwei Speichern, zwei Kanälen und zwei
Übertragungsstrings, und das bleibt so — die Gründe stehen in den
beiden Verträgen. Was sich geändert hat: die Trennung ist nicht mehr
die Sorge des Nutzers.

Die Seite bildet den Weg ab, den man geht:

| Schritt | Hauptaktion | Beantwortet |
|---|---|---|
| 1 Charakter vorbereiten | *keine* | Ist mein Charakter richtig erkannt? Sieht die Companion meinen Stand? |
| 2 Sim öffnen und rechnen lassen | *Sim mit meiner Ausrüstung öffnen* | Was habe ich jetzt zu tun? |
| 3 Sim-Ergebnis einfügen | *Sim-Ergebnis übernehmen* | Ist es vollständig? Wurde wirklich optimiert? |
| 4 Ins Spiel übertragen | *Ins Spiel übertragen* | Was wird übertragen? Muss ich noch etwas tun? |

Fünf Dinge daran sind nicht Geschmack:

- **Schritt 1 hat keinen Knopf.** Er beantwortet zwei Fragen, bevor
  irgendetwas passiert. Bis 3.2.0 standen die Antworten zwischen den
  Knöpfen von Schritt 2, und dort liest sie niemand: wer einen Knopf
  sieht, drückt ihn.
- **„Im Sim rechnen lassen" ist keine eigene Karte.** Eine Karte ohne
  Bedienelement wäre eine Überschrift mit einem Absatz — und gelesen
  wird dieser Absatz ohnehin genau in dem Moment, in dem der Knopf
  gedrückt wird. `SIM_STEPS` steht deshalb direkt darüber. Inhaltlich
  ist er der wichtigste Satz der Seite (siehe unten).
- **Ein Knopf zum Übernehmen, nicht zwei.** Bis 3.2.0 hatte jede der
  beiden Auskünfte eine eigene Karte mit eigenem Knopf; wer den zweiten
  vergaß, bekam im Spiel eine halbe Auskunft, der man das nicht ansieht.
  `_apply()` legt ab, was im Lauf liegt.
- **Ein Knopf zum Verwerfen, nicht zwei.** Zwei Entfernen-Knöpfe waren
  die Möglichkeit, eine Hälfte stehenzulassen — und genau diese Hälfte
  ergibt später die Mischung aus zwei Läufen, vor der Schritt 4 warnt.
- **`_read()` sammelt, es ersetzt nicht.** Das zweite Einfügen ergänzt
  den ersten Befund. Genau das war die „zweite Runde durch dasselbe
  Feld", die den Nutzer zwang, sich die technische Trennung zu merken.

**Die Sätze stehen in `core/sim_run.py`, nicht auf der Seite**
(`headline()`, `parts_line()`, `change_line()`, `next_step()`,
`source_line()`, `class_note()`, `mixed_note()`). Sie sind die Antwort
auf eine Rechnung, und der Testlauf muss sie ohne Qt prüfen können —
dieselbe Aufteilung wie `gap_text()`/`age_text()` in
`core/wowsims_export.py`. Zwei Fassungen desselben Satzes liefen ab der
ersten Änderung auseinander, und die falsche stünde dann bei dem, der
einen Fehler sucht.

**Der Befund kennt zwei Läufe, und das ist kein Versehen.** „Steht hier
etwas?" beantwortet der **eingefügte** Lauf (`self._run`) — sonst stünde
nach jedem Übernehmen ein Befund über ein leeres Feld. „Ist es
vollständig?" beantwortet `_effective_run()`, also derselbe Lauf plus dem,
was für **genau ihn** schon abgelegt ist. Übernommen wird nur das
Eingefügte; wäre es der zusammengeführte, überschriebe jeder zweite Klick
die schon abgelegte Hälfte mit einem neuen Zeitstempel. Warum es das
braucht: `../sim-run.md`, Abschnitt *Der Lauf sieht, was für ihn schon
abgelegt ist*.

**Ein Lesefehler wirft nicht weg, was schon gelesen wurde** (`_fail()`).
Wer nach der Gewichtung Unsinn einfügt, hat die Gewichtung nicht
zurückgenommen. *Feld leeren* dagegen vergisst den Lauf — das ist der
Sinn des Knopfes, und es ist sichtbar: die Häkchenzeile springt auf
„Gewichtung fehlt".

`tests/test_sim_run.py` prüft das Rechnende ohne Qt,
`tests/test_sim_page_target.py` baut die Seite offscreen auf.


## Die Zielausrüstung aus dem Sim (`core/target_gear.py`, Schritt 3)

Voller Vertrag (drei Gestalten, Feldbedeutungen, Zuordnung über die
Plätze, die 0-Regel, die Rangfolge im Spiel): `../target-gear-bridge.md`.
Diese Datei hält nur die Companion-lokale Seite.

**Der Rückweg aus dem Sim.** Die Gewichtung sagt, *wie* zu bewerten ist;
das Ergebnis sagt, *was herauskam*. Bis 3.0.1 kam nur das Erste ins
Spiel, und WeintCodex hat aus den Gewichten selbst noch einmal
ausgerechnet, welcher Stein in welchen Sockel gehört — zwei Rechnungen
für dieselbe Frage.

Vier Dinge sind hier nicht Geschmack:

- **Dasselbe Eingabefeld für beide Sorten.** Schritt 3 heisst
  „Sim-Ergebnis einfügen", und was aus dem Sim kommt, gehört dorthin.
  `_read()`
  probiert `parse_target()` **zuerst**, weil es die strengere der beiden
  Lesarten ist: es erkennt nur eine Adresse, einen Base64-Rumpf ab 40
  Zeichen oder JSON. Eine getippte Gewichtung („Hit 1.77") ist keins
  davon und fällt sicher an `parse()` durch — andersherum wäre es nicht
  so. Zwei Felder nebeneinander wären die Frage, in welches man einfügt,
  und die Antwort steht dem Nutzer nirgends zur Verfügung.
- **`SimItem` bleibt die einzige Struktur für einen Ausrüstungsplatz.**
  Sie trägt schon `item_id`, `gems`, `reforging` und `enchant`; eine
  zweite daneben liefe ab der ersten Änderung auseinander. Der
  Protobuf-**Decoder** steht deshalb auch in `core/wowsims_link.py`
  neben dem Encoder — dieselben Feldnummern, eine Datei.
- **Die Seite sagt, ob überhaupt optimiert wurde.** Ein Sim-Export
  enthält immer das, was gerade eingestellt ist. `compare()` stellt ihn
  je Platz neben das, was der WowSimsExporter als **angelegt** meldet,
  `sim_run.validate()` zählt es aus (Plätze, **Sockel**, Umschmiedungen)
  und `change_line()` schreibt das Ergebnis hin — auch und gerade den Fall
  „ändert sich nichts", der zwei Erklärungen hat (schon optimal, oder
  gar nicht optimiert). Ohne diesen Satz brächte ein
  Ausgangszustand-als-Ziel im Spiel jede Empfehlung zum Schweigen, und
  das wäre von einer fertigen Ausrüstung nicht zu unterscheiden.
- **Eigener Speicher, eigener Kanal — aber eine Karte** (seit 3.3.0).
  Gewichtung und Zielzustand bleiben zwei Auskünfte: die eine gilt für
  jede Ausrüstung, die andere für genau die, mit der gesimmt wurde.
  Getrennt bleiben deshalb Ablage und Zustellung; getrennt *angezeigt*
  wurden sie bis 3.2.0, und das war die Trennung, die der Nutzer
  mitdenken musste. Welche von beiden gerade fehlt, beantwortet jetzt
  `parts_line()` in einer Zeile.

`tests/test_target_gear.py` prüft das Rechnende ohne Qt,
`tests/test_sim_page_target.py` baut die Seite offscreen auf.

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

## Der Weg im Sim, und die zwei Klicks weniger (seit 3.1.1)

**`SIM_STEPS` ist der Satz, der in den Sim schickt — einmal im
Quelltext.** Er stand wörtlich zweimal da (Kartenaufbau und
Zurückschalten aus dem Heiler-Zweig); die falsche Fassung hätte danach
genau der gesehen, der zwischen zwei Spezialisierungen gewechselt hat.

Inhaltlich trägt er eine Auskunft, ohne die der ganze Schritt 4 leerläuft:
**`Suggest Reforges` optimiert von sich aus nur die Umschmiedungen.** Für
die Sockelsteine muss im Sim das Zahnrad neben dem Knopf angeklickt und
*Include gems* angehakt werden — ein Schalter an der einen Stelle, an der
man ihn nicht sucht. Ohne ihn kommt ein Export zurück, der vollständig
aussieht und an den Steinen nichts gerechnet hat, und im Spiel folgt
WeintCodex dann genau diesen unveränderten Steinen. Derselbe Satz steht
deshalb auch in Schritt 4 und in der Fehlermeldung „erkannt, aber darin
steht kein Sockelstein".

**Gelesen wird beim Einfügen** (`input.textChanged` → einmaliger `QTimer`,
250 ms → `_read(quiet=True)`). *Einlesen* war ein Klick ohne eigene
Entscheidung; der Knopf bleibt für den einen Fall, in dem er etwas kann,
was das Lesen nebenher nicht darf: **einen Fehler sagen.** Genau das
unterscheidet `quiet` — ein *Befund* erscheint in beiden Fällen, eine
*Fehlermeldung* nur auf Klick. Wer mitten im Tippen ist, hat noch nichts
falsch gemacht, und eine rote Zeile nach jedem Zeichen erzieht dazu, rote
Zeilen zu übersehen.

Zwei Dinge hängen daran und sind kein Geschmack:

- **`_clear_input()` schreibt selbst ins Feld** und schaltet den
  Zeitgeber über `_suppress_read` ab. Ohne das liefe nach jedem
  Übernehmen ein Lesevorgang über ein leeres Feld.
- **Ein leeres Feld ist der Ausgangszustand, kein Fehler.** `_read()`
  bricht bei leerem Text über `_forget_reading()` ab — sonst stünde
  „nicht erkannt" da, sobald jemand seinen Text herauslöscht.

## Ein Ausgang statt zwei (seit 3.2.0)

**Die Karten stehen in der Reihenfolge, in der man sie läuft** — seit
3.3.0: Charakter → Sim öffnen → Einfügen → Übertragen. Bis 3.1.1 stand
*Ins Spiel bringen* in der Mitte, und das war eine Treppe, die man als
Schleife geht: einlesen, rüberbringen, zurück in den Sim, wieder
einlesen, nochmal rüberbringen. Zwei Strings, zweimal einfügen im Spiel
— und der zweite blieb regelmäßig liegen, was man einer Empfehlung im
Spiel nicht ansieht.

Die Zielkarte hat deshalb ihr eigenes String-Feld, *String kopieren*,
*Entfernen* und `copy_state` verloren — und seit 3.3.0 gibt es sie gar
nicht mehr: zwei Auskünfte heißt **ein** Befund über einen Lauf, nicht
zwei Karten. `_draw_delivery()` besitzt Feld, Warnung, Hinweis und
Knöpfe und liest beide Speicher; `_draw_stored()` schreibt nur noch
seine Zeile.

**`_delivery_lines()` ist die eine Stelle, die entscheidet, was ins Feld
kommt** — und `_combined_allowed()` das Sicherheitsnetz davor
(`state.addon_found` plus `_version_tuple(state.addon_version) >=
COMBINED_SINCE`, also WeintCodex 3.1.2.0).

**Warum das ein Netz braucht und nicht bloß Vorsicht ist:**
`SW.ParseTransfer` drüben zerlegt an `:` und nimmt Feld 6; alles dahinter
— also die ganze zweite Zeile — fällt weg, **ohne** Fehler. Beide Zeilen
zusammen ergäben auf einem älteren Addon eine *Erfolgsmeldung*, in der
die Zielausrüstung schlicht fehlt. Genau diese Sorte Fehler ist die
schlimmste: nichts bricht, nichts meldet sich, und im Spiel folgt
WeintCodex weiter seiner eigenen Rechnung, obwohl auf dem Desktop längst
entschieden wurde.

**Nicht feststellbar zählt wie zu alt.** Der Preis der vorsichtigen
Antwort ist ein zweiter Einfügevorgang, der Preis der unvorsichtigen ein
stilles Verschlucken — dieselbe Rangfolge wie bei `stars == 0`. Der
Warnsatz nennt beides: den Grund und den Ausweg (`/reload` holt ohnehin
beides, denn zugestellt ist es längst).

Codex-Seite des Vertrags — Zerlegung an `WCIMPORT:`, Verhalten bei einem
einzelnen String, Teilerfolg als Fehler:
`../../../WeintCodex/docs/systems/wcimport-sync.md`.

**Übernehmen kopiert mit.** *Übernehmen* und *String kopieren* waren zwei
Klicks für eine Absicht: wer übernimmt, will es ins Spiel bringen. Der
Zeitpunkt ist auch der einzige, an dem die Frage „welcher der beiden
Strings ist meiner" gar nicht erst entsteht. Kopiert wird **nach**
`refresh()` (erst dort wird das Feld gefüllt) und über **dieselben**
Methoden wie die Knöpfe, damit ein System ohne Zwischenablage denselben
Satz bekommt statt eines stillen Nichts. Die Knopfbeschriftung nennt es,
weil ein stiller Griff in die Zwischenablage eine Überraschung wäre.

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

**Ein Heiler-Lauf ist ohne Zielzustand vollständig.** `_validation()`
gibt `target_expected=False` weiter, wenn `qelive.spec()` die Spec
führt; sonst stünde dort dauerhaft „Optimierte Ausrüstung fehlt" —
eine Aufforderung ins Leere.

**Die Zahlen sind dieselben wie im Addon** (`SPECS`, dieselbe Skalierung
wie `modules/qelive.lua`); `tests/test_qelive.py` und
`../../../WeintCodex/.github/tests/qelive_test.lua` prüfen dieselben Werte.
**Ein Null-Gewicht ist eine Lücke, keine Aussage** (`gaps`) —
`weights_note()` benennt sie, ebenso dass QE Live zwei Modelle selbst als
Beta führt.

Kein Qt, kein `httpx`, keine Datei — dieselbe Aufteilung wie
`roster_target()`/`build_profile_payload()`.
